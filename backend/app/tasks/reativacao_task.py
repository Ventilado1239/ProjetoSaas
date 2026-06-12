import asyncio
import logging
import uuid
import random
from datetime import datetime, timezone, timedelta
from typing import Optional
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.models import Tenant, ClientePaciente, LogMensagem
from app.utils.mensagens import get_message
from app.services.whatsapp_service import enviar_mensagem
import app.services.whatsapp_service as ws

logger = logging.getLogger(__name__)

async def processar_reativacoes(db: Optional[AsyncSession] = None):
    """
    Weekly task that runs on Mondays at 09:00.
    """
    logger.info("Iniciando CRM de reativação de clientes inativos...")
    if db is None:
        async with AsyncSessionLocal() as session:
            try:
                await _run_reativacoes(session)
                await session.commit()
            except Exception as e:
                logger.exception(f"Erro no processamento de reativações: {e}")
                await session.rollback()
    else:
        await _run_reativacoes(db)

async def _run_reativacoes(db: AsyncSession):
    # 1. Fetch all active tenants
    await db.execute(text("SET LOCAL app.bypass_rls = 'true'"))
    res_tenants = await db.execute(select(Tenant).where(Tenant.sistema_ativo == True))
    tenants = res_tenants.scalars().all()
    await db.execute(text("SET LOCAL app.bypass_rls = 'false'"))
    
    for tenant in tenants:
        # Enforce RLS context
        await db.execute(text("SELECT set_tenant_id(:tenant_id)"), {"tenant_id": tenant.id})
        
        # Fetch all clients of this tenant who have an 'ultima_consulta' timestamp
        stmt = select(ClientePaciente).where(
            ClientePaciente.tenant_id == tenant.id,
            ClientePaciente.ultima_consulta != None
        )
        res_clients = await db.execute(stmt)
        clients = res_clients.scalars().all()
        
        now = datetime.now(timezone.utc)
        first_dispatch = True
        
        for client in clients:
            # Convert to utc time for comparison
            last_visit = client.ultima_consulta.replace(tzinfo=timezone.utc) if client.ultima_consulta.tzinfo is None else client.ultima_consulta.astimezone(timezone.utc)
            days_inactive = (now - last_visit).days
            
            target_status = None
            msg_key = None
            
            # 12 months inatividade (>= 365 days)
            if days_inactive >= 365:
                if client.status_reativacao != "inativo_12m":
                    target_status = "inativo_12m"
                    msg_key = "crm_reactivate_12m"
                    
            # 6 months inatividade (>= 180 days and < 365 days)
            elif days_inactive >= 180:
                if client.status_reativacao not in ["inativo_6m", "inativo_12m"]:
                    target_status = "inativo_6m"
                    msg_key = "crm_reactivate_6m"
                    
            # 3 months inatividade (>= 90 days and < 180 days)
            elif days_inactive >= 90:
                if client.status_reativacao not in ["inativo_3m", "inativo_6m", "inativo_12m"]:
                    target_status = "inativo_3m"
                    msg_key = "crm_reactivate_3m"
                    
            if target_status and msg_key:
                # Human-like delay between dispatches (45-60s), mock in tests
                if not first_dispatch:
                    sleep_duration = random.randint(45, 60) if ws.SIMULATE_DELAY else 0.01
                    logger.info(f"Aguardando {sleep_duration}s antes do próximo envio de reativação...")
                    await asyncio.sleep(sleep_duration)
                else:
                    first_dispatch = False
                    
                # Update status
                client.status_reativacao = target_status
                await db.flush()
                
                reply = get_message(
                    msg_key,
                    nome=client.nome,
                    tenant_nome=tenant.nome
                )
                
                # Dispatch message
                await enviar_mensagem(str(tenant.id), client.whatsapp, reply)
                
                # Log message history
                log = LogMensagem(
                    id=uuid.uuid4(),
                    tenant_id=tenant.id,
                    cliente_whatsapp=client.whatsapp,
                    direcao="saida",
                    mensagem=reply,
                    tipo="texto"
                )
                db.add(log)
                await db.flush()
