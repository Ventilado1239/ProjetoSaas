import logging
import uuid
from typing import Optional
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import AsyncSessionLocal
from app.models.models import Tenant, AtendimentoPedido, ClientePaciente, LogMensagem
from app.services.whatsapp_service import enviar_mensagem

logger = logging.getLogger(__name__)

def agendar_pos_atendimento(tenant_id: uuid.UUID, appointment_id: uuid.UUID):
    """
    Schedules a post-appointment follow-up task 30 minutes in the future.
    """
    try:
        from app.tasks.scheduler import scheduler
        now = datetime.now(timezone.utc)
        run_time = now + timedelta(minutes=30)
        
        job_id = f"pos_atendimento_{appointment_id}"
        scheduler.add_job(
            enviar_agradecimento_pos_atendimento,
            trigger="date",
            run_date=run_time,
            args=[tenant_id, appointment_id],
            id=job_id,
            replace_existing=True
        )
        logger.info(f"Agendado follow-up pós-atendimento para o agendamento {appointment_id} às {run_time}.")
    except Exception as e:
        logger.error(f"Erro ao agendar pós-atendimento para agendamento {appointment_id}: {e}")

async def enviar_agradecimento_pos_atendimento(
    tenant_id: uuid.UUID, appointment_id: uuid.UUID, db: Optional[AsyncSession] = None
):
    """
    Background job that executes after 30 minutes.
    Verifies that the appointment status remains 'realizado' or 'entregue' and dispatches follow-up.
    """
    logger.info(f"Executando pós-atendimento para o agendamento {appointment_id}...")
    if db is None:
        async with AsyncSessionLocal() as session:
            try:
                await _run_agradecimento(session, tenant_id, appointment_id)
                await session.commit()
                logger.info(f"Agradecimento pós-atendimento enviado com sucesso para o agendamento {appointment_id}.")
            except Exception as e:
                logger.exception(f"Erro ao processar pós-atendimento para {appointment_id}: {e}")
                await session.rollback()
    else:
        await _run_agradecimento(db, tenant_id, appointment_id)

async def _run_agradecimento(db: AsyncSession, tenant_id: uuid.UUID, appointment_id: uuid.UUID):
    # Set RLS Context
    await db.execute(text("SELECT set_tenant_id(:tenant_id)"), {"tenant_id": tenant_id})
    
    # Fetch tenant details
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        logger.error(f"Tenant {tenant_id} não encontrado.")
        return
        
    # Fetch appointment
    appt = await db.get(AtendimentoPedido, appointment_id)
    if not appt:
        logger.error(f"Agendamento {appointment_id} não encontrado.")
        return
        
    # Only trigger follow-up if status is still 'realizado' or 'entregue'
    if appt.status not in ["realizado", "entregue"]:
        logger.info(f"Agendamento {appointment_id} mudou de status para {appt.status}. Cancelando envio de pós-atendimento.")
        return
        
    # Fetch client details
    client = await db.get(ClientePaciente, appt.cliente_id)
    if not client:
        logger.error(f"Cliente {appt.cliente_id} não encontrado.")
        return
        
    # 1. Update client's last visit timestamp
    client.ultima_consulta = datetime.now(timezone.utc)
    db.add(client)
    await db.flush()
    
    # 2. Build message based on tenant type
    if tenant.tipo == "clinica":
        message = (
            f"Olá, {client.nome}! Agradecemos pela sua visita hoje. "
            f"Para manter a sua saúde em dia, sugerimos um retorno em breve. "
            f"Como podemos te ajudar com o seu próximo agendamento?"
        )
    else:  # loja
        message = (
            f"Olá, {client.nome}! Seu pedido foi entregue. "
            f"Poderia avaliar nosso atendimento em apenas uma palavra? 😊"
        )
        
    # 3. Send message to customer
    await enviar_mensagem(str(tenant_id), client.whatsapp, message)
    
    # 4. Log message in database
    log = LogMensagem(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        cliente_whatsapp=client.whatsapp,
        direcao="saida",
        mensagem=message,
        tipo="texto"
    )
    db.add(log)
    await db.flush()
