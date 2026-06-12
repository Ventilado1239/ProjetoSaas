import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.models import Tenant, EstadoConversa, ClientePaciente, LogMensagem
from app.services.whatsapp_service import enviar_mensagem

logger = logging.getLogger(__name__)

# If a client has been in a mid-flow state for > 30 minutes, we consider it abandoned
ABANDONO_TIMEOUT_MINUTES = 30

# Stages that indicate the client is mid-flow (not yet completed)
ETAPAS_MID_FLOW = [
    "aguardando_produto",
    "aguardando_quantidade",
    "aguardando_personalizacao",
    "aguardando_confirmacao",
    "aguardando_data",
]


async def processar_abandonos(db: Optional[AsyncSession] = None):
    """
    Scheduled task that runs every 15 minutes.
    Detects clients who abandoned a conversation mid-flow
    and sends them a follow-up nudge message.
    """
    logger.info("Verificando conversas abandonadas...")
    if db is None:
        async with AsyncSessionLocal() as session:
            try:
                await _run_abandonos(session)
                await session.commit()
            except Exception as e:
                logger.exception(f"Erro ao processar abandonos: {e}")
                await session.rollback()
    else:
        await _run_abandonos(db)


async def _run_abandonos(db: AsyncSession):
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=ABANDONO_TIMEOUT_MINUTES)

    # 1. Fetch all active tenants (bypass RLS on tenants table)
    await db.execute(text("SET LOCAL app.bypass_rls = 'true'"))
    res_tenants = await db.execute(select(Tenant).where(Tenant.sistema_ativo == True))
    tenants = res_tenants.scalars().all()
    await db.execute(text("SET LOCAL app.bypass_rls = 'false'"))

    for tenant in tenants:
        # Enforce RLS context for this tenant
        await db.execute(text("SELECT set_tenant_id(:tenant_id)"), {"tenant_id": tenant.id})

        # Query mid-flow states that are stale for this tenant and join with ClientePaciente (1-to-1 relationship)
        stmt = (
            select(EstadoConversa, ClientePaciente)
            .join(ClientePaciente, EstadoConversa.cliente_id == ClientePaciente.id)
            .where(
                EstadoConversa.tenant_id == tenant.id,
                EstadoConversa.etapa_atual.in_(ETAPAS_MID_FLOW),
                EstadoConversa.atualizado_em < cutoff,
            )
        )
        res = await db.execute(stmt)
        abandoned_rows = res.all()

        for state, client in abandoned_rows:
            try:
                if not client:
                    await db.delete(state)
                    continue

                # Send nudge message
                nudge_msg = (
                    f"Oi, {client.nome}! Percebi que nossa conversa ficou parada. "
                    f"Ainda precisa de ajuda? Se quiser continuar, basta enviar uma mensagem. "
                    f"Se preferir, digite 'cancelar' para encerrar. 😊"
                )

                await enviar_mensagem(str(tenant.id), client.whatsapp, nudge_msg)

                log = LogMensagem(
                    id=uuid.uuid4(),
                    tenant_id=tenant.id,
                    cliente_whatsapp=client.whatsapp,
                    direcao="saida",
                    mensagem=nudge_msg,
                    tipo="texto"
                )
                db.add(log)

                # Mark as "abandono_notificado" so we don't nudge again
                state.etapa_atual = "abandono_notificado"
                await db.flush()

                logger.info(f"Notificação de abandono enviada para {client.nome} ({client.whatsapp}).")

            except Exception as e:
                logger.exception(f"Erro ao processar abandono para state {state.id}: {e}")

        # Clean up states that were notified more than 2 hours ago (permanent abandonment) for this tenant
        cleanup_cutoff = datetime.now(timezone.utc) - timedelta(hours=2)
        stmt_cleanup = (
            select(EstadoConversa)
            .where(
                EstadoConversa.tenant_id == tenant.id,
                EstadoConversa.etapa_atual == "abandono_notificado",
                EstadoConversa.atualizado_em < cleanup_cutoff,
            )
        )
        res_cleanup = await db.execute(stmt_cleanup)
        stale_states = res_cleanup.scalars().all()

        for s in stale_states:
            await db.delete(s)

        if stale_states:
            logger.info(f"Removidos {len(stale_states)} estados de conversa abandonados definitivamente para o tenant {tenant.nome}.")

    await db.flush()
    logger.info("Processamento de abandonos concluído.")
