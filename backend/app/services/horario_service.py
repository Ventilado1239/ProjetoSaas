import logging
import uuid
from datetime import datetime
from zoneinfo import ZoneInfo
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Tenant, LogMensagem, EstadoConversa, ClientePaciente
from app.services.tenant_settings import get_evolution_instance_name, get_owner_whatsapp
from app.services.whatsapp_service import enviar_mensagem

logger = logging.getLogger(__name__)

SP_TZ = ZoneInfo("America/Sao_Paulo")


def is_within_opening_window(tenant: Tenant, now_sp: datetime, window_minutes: int = 5) -> bool:
    """
    Returns True if the current time is within `window_minutes` of the tenant's opening hour.
    Used by retomada_task to detect tenants that just opened.
    """
    try:
        h_open, m_open = map(int, tenant.horario_abertura.split(":"))
        open_minutes = h_open * 60 + m_open
        current_minutes = now_sp.hour * 60 + now_sp.minute
        return 0 <= (current_minutes - open_minutes) < window_minutes
    except Exception:
        return False


async def registrar_mensagem_noturna(
    db: AsyncSession,
    tenant: Tenant,
    client_phone: str,
    message_text: str,
    push_name: str
):
    """
    Called by the webhook router when a message arrives outside working hours.
    Saves the conversation state as 'aguardando_abertura' so it can be resumed later.
    """
    # Find or create client
    stmt = select(ClientePaciente).where(
        ClientePaciente.tenant_id == tenant.id,
        ClientePaciente.whatsapp == client_phone
    )
    res = await db.execute(stmt)
    client = res.scalar_one_or_none()

    if not client:
        client = ClientePaciente(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            nome=push_name or "Cliente",
            whatsapp=client_phone,
            status_reativacao="ativo"
        )
        db.add(client)
        await db.flush()

    # Check if there's already a conversation state for this client
    stmt_state = select(EstadoConversa).where(EstadoConversa.cliente_id == client.id)
    res_state = await db.execute(stmt_state)
    state = res_state.scalar_one_or_none()

    import json
    if state:
        # Preserve the previous conversation stage in dados_acumulados
        dados = json.loads(state.dados_acumulados) if state.dados_acumulados else {}
        dados["etapa_antes_noturna"] = state.etapa_atual
        dados["mensagem_noturna"] = message_text
        state.etapa_atual = "aguardando_abertura"
        state.dados_acumulados = json.dumps(dados)
    else:
        state = EstadoConversa(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            cliente_id=client.id,
            etapa_atual="aguardando_abertura",
            dados_acumulados=json.dumps({
                "mensagem_noturna": message_text,
                "etapa_antes_noturna": None
            })
        )
        db.add(state)

    await db.flush()
    logger.info(f"Mensagem noturna registrada para cliente {client.nome} no tenant {tenant.nome}.")


async def retomar_conversas_abertura(db: AsyncSession, tenant: Tenant):
    """
    Called by retomada_task when a tenant just opened.
    Resumes conversations that arrived outside working hours.
    """
    import json

    # Join EstadoConversa with ClientePaciente to avoid N+1 queries entirely!
    stmt = (
        select(EstadoConversa, ClientePaciente)
        .join(ClientePaciente, EstadoConversa.cliente_id == ClientePaciente.id)
        .where(
            EstadoConversa.tenant_id == tenant.id,
            EstadoConversa.etapa_atual == "aguardando_abertura"
        )
    )
    res = await db.execute(stmt)
    results = res.all()

    if not results:
        return

    # Notify owner about overnight messages
    owner_phone = get_owner_whatsapp(tenant)
    instance_name = get_evolution_instance_name(tenant.id, tenant)
    nocturnal_count = len(results)
    owner_msg = (
        f"🌅 *BOM DIA!* Você recebeu {nocturnal_count} mensagem(ns) fora do horário.\n\n"
    )

    client_lines = []
    for state, client in results:
        dados = json.loads(state.dados_acumulados) if state.dados_acumulados else {}
        msg_preview = dados.get("mensagem_noturna", "")[:50]
        client_lines.append(f"• {client.nome} ({client.whatsapp}): \"{msg_preview}...\"")

    if client_lines:
        owner_msg += "\n".join(client_lines)
        await enviar_mensagem(str(tenant.id), owner_phone, owner_msg, instance_name=instance_name)

        log = LogMensagem(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            cliente_whatsapp=owner_phone,
            direcao="saida",
            mensagem=owner_msg,
            tipo="texto"
        )
        db.add(log)
        await db.flush()

    # Resume each client conversation
    for state, client in results:
        dados = json.loads(state.dados_acumulados) if state.dados_acumulados else {}
        etapa_anterior = dados.get("etapa_antes_noturna")

        # Send resumption message to client
        resume_msg = (
            f"Olá, {client.nome}! Bom dia! 🌞 Acabamos de abrir e vimos sua mensagem. "
            f"Como posso te ajudar?"
        )
        await enviar_mensagem(str(tenant.id), client.whatsapp, resume_msg, instance_name=instance_name)

        log_client = LogMensagem(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            cliente_whatsapp=client.whatsapp,
            direcao="saida",
            mensagem=resume_msg,
            tipo="texto"
        )
        db.add(log_client)

        # Reset conversation state: if they had an active flow, restore it; otherwise delete state
        if etapa_anterior and etapa_anterior != "menu":
            state.etapa_atual = etapa_anterior
            # Remove nocturnal metadata
            if "mensagem_noturna" in dados:
                del dados["mensagem_noturna"]
            if "etapa_antes_noturna" in dados:
                del dados["etapa_antes_noturna"]
            state.dados_acumulados = json.dumps(dados)
        else:
            await db.delete(state)

    await db.flush()
    logger.info(f"Retomadas {nocturnal_count} conversas noturnas para o tenant {tenant.nome}.")
