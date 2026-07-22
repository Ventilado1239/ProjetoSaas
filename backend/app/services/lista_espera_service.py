import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.models import Tenant, AtendimentoPedido, ClientePaciente, ServicoProduto, ItemAtendimento, ListaEspera, EstadoConversa, LogMensagem
from app.services.tenant_settings import get_evolution_instance_name
from app.services.whatsapp_service import enviar_mensagem

logger = logging.getLogger(__name__)

async def ofertar_horario(db_session: AsyncSession, tenant: Tenant, cancelled_appt_id: uuid.UUID):
    """
    Looks for the next client in the waitlist for the service category of the cancelled appointment,
    and dispatches a slot offer.
    """
    logger.info(f"Ofertando horário para agendamento cancelado {cancelled_appt_id}...")
    
    # 1. Fetch the cancelled appointment details
    stmt_appt = select(AtendimentoPedido).where(AtendimentoPedido.id == cancelled_appt_id)
    res_appt = await db_session.execute(stmt_appt)
    appt = res_appt.scalar_one_or_none()
    if not appt:
        logger.warning("Agendamento cancelado não encontrado.")
        return
        
    # Find the service category/id associated with this appointment
    stmt_item = select(ItemAtendimento).where(ItemAtendimento.atendimento_id == cancelled_appt_id)
    res_item = await db_session.execute(stmt_item)
    item = res_item.scalar_one_or_none()
    service_id = item.servico_id if item else None
    
    # 2. Query the oldest waiting list entry for this service in 'aguardando' status
    stmt_wait = (
        select(ListaEspera)
        .where(
            ListaEspera.tenant_id == tenant.id,
            ListaEspera.status == "aguardando",
            ListaEspera.servico_id == service_id
        )
        .order_by(ListaEspera.data_preferida.asc()) # oldest first
    )
    res_wait = await db_session.execute(stmt_wait)
    wait_entry = res_wait.scalars().first()
    
    if not wait_entry:
        logger.info("Nenhum cliente aguardando na lista de espera para este serviço.")
        return
        
    # Fetch waiting list client details
    stmt_client = select(ClientePaciente).where(ClientePaciente.id == wait_entry.cliente_id)
    res_client = await db_session.execute(stmt_client)
    client = res_client.scalar_one_or_none()
    if not client:
        return
        
    # Fetch service details
    stmt_serv = select(ServicoProduto).where(ServicoProduto.id == service_id)
    res_serv = await db_session.execute(stmt_serv)
    service = res_serv.scalar_one_or_none()
    service_name = service.nome if service else "Consulta"
    
    # Update waitlist status to notified
    wait_entry.status = "notificado"
    
    # Formatted date/time
    formatted_dt = appt.data_agendamento.astimezone(timezone(timedelta(hours=-3))).strftime("%d/%m às %H:%M")
    
    # Create conversation state for the waitlist client
    stmt_state = select(EstadoConversa).where(EstadoConversa.cliente_id == client.id)
    res_state = await db_session.execute(stmt_state)
    state = res_state.scalar_one_or_none()
    if state:
        await db_session.delete(state)
        await db_session.flush()
        
    state = EstadoConversa(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        cliente_id=client.id,
        etapa_atual="lista_espera_oferta",
        dados_acumulados=json.dumps({
            "atendimento_id": str(cancelled_appt_id),
            "lista_espera_id": str(wait_entry.id)
        })
    )
    db_session.add(state)
    await db_session.flush()
    
    reply = (
        f"Olá, {client.nome}! Um horário de atendimento para {service_name} surgiu para o dia {formatted_dt}.\n\n"
        f"Você tem interesse em ficar com essa vaga?\n"
        f"1. Sim, quero agendar\n"
        f"2. Não tenho interesse\n\n"
        f"⏳ Atenção: Esta oferta expira em 15 minutos!"
    )
    
    await enviar_mensagem(
        str(tenant.id),
        client.whatsapp,
        reply,
        instance_name=get_evolution_instance_name(tenant.id, tenant),
    )
    
    # Log message
    log = LogMensagem(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        cliente_whatsapp=client.whatsapp,
        direcao="saida",
        mensagem=reply,
        tipo="texto"
    )
    db_session.add(log)
    await db_session.flush()
    
    # Schedule the 15-minute expiration job using APScheduler
    try:
        from app.tasks.scheduler import scheduler
        run_time = datetime.now(timezone.utc) + timedelta(minutes=15)
        scheduler.add_job(
            processar_timeout_waitlist,
            trigger="date",
            run_date=run_time,
            args=[tenant.id, wait_entry.id, cancelled_appt_id],
            id=f"timeout_waitlist_{wait_entry.id}",
            replace_existing=True
        )
        logger.info(f"Job de timeout agendado para lista_espera {wait_entry.id} em {run_time}.")
    except Exception as e:
        logger.error(f"Erro ao agendar job de timeout para lista de espera: {e}")

async def processar_timeout_waitlist(
    tenant_id: uuid.UUID, 
    wait_entry_id: uuid.UUID, 
    appt_id: uuid.UUID, 
    db: Optional[AsyncSession] = None
):
    """
    Executes if the 15 minutes expire without client response.
    """
    logger.info(f"Processando timeout de 15 minutos para lista de espera {wait_entry_id}...")
    if db is None:
        async with AsyncSessionLocal() as session:
            try:
                await _run_timeout_waitlist(session, tenant_id, wait_entry_id, appt_id)
                await session.commit()
            except Exception as e:
                logger.exception(f"Erro ao processar timeout da lista de espera: {e}")
                await session.rollback()
    else:
        await _run_timeout_waitlist(db, tenant_id, wait_entry_id, appt_id)

async def _run_timeout_waitlist(db: AsyncSession, tenant_id: uuid.UUID, wait_entry_id: uuid.UUID, appt_id: uuid.UUID):
    # Set RLS Context
    await db.execute(text("SELECT set_tenant_id(:tenant_id)"), {"tenant_id": tenant_id})
    
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        return
        
    stmt_wait = select(ListaEspera).where(ListaEspera.id == wait_entry_id)
    res_wait = await db.execute(stmt_wait)
    wait_entry = res_wait.scalar_one_or_none()
    
    if wait_entry and wait_entry.status == "notificado":
        # Mark waitlist slot as expired
        wait_entry.status = "expirado"
        
        # Retrieve client to clean conversation state and notify them
        stmt_client = select(ClientePaciente).where(ClientePaciente.id == wait_entry.cliente_id)
        res_client = await db.execute(stmt_client)
        client = res_client.scalar_one_or_none()
        
        if client:
            # Clean conversation state
            stmt_state = select(EstadoConversa).where(EstadoConversa.cliente_id == client.id)
            res_state = await db.execute(stmt_state)
            state = res_state.scalar_one_or_none()
            if state:
                await db.delete(state)
                await db.flush()
                
            # Notify expiration
            reply = "Infelizmente, o tempo para confirmation da vaga expirou e o horário foi oferecido para o próximo da fila. Caso deseje um novo agendamento, entre em contato! 🤝"
            await enviar_mensagem(
                str(tenant_id),
                client.whatsapp,
                reply,
                instance_name=get_evolution_instance_name(tenant_id, tenant),
            )
            
            log = LogMensagem(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                cliente_whatsapp=client.whatsapp,
                direcao="saida",
                mensagem=reply,
                tipo="texto"
            )
            db.add(log)
            
        await db.flush()
        
        # Cascade offer to next client in list
        if appt_id:
            await ofertar_horario(db, tenant, appt_id)

async def oferecer_vaga_lista_espera(db_session: AsyncSession, entry: ListaEspera) -> bool:
    """
    Manually triggers a slot offer via WhatsApp for a specific waitlist entry.
    Updates the entry's status to 'notificado', sets the conversation state,
    sends the WhatsApp message, and schedules the 15-minute timeout.
    """
    try:
        tenant = await db_session.get(Tenant, entry.tenant_id)
        if not tenant:
            logger.warning("Tenant nÃ£o encontrado para oferecer vaga.")
            return False

        # Fetch client details
        stmt_client = select(ClientePaciente).where(ClientePaciente.id == entry.cliente_id)
        res_client = await db_session.execute(stmt_client)
        client = res_client.scalar_one_or_none()
        if not client:
            logger.warning("Cliente não encontrado para oferecer vaga.")
            return False

        # Fetch service details if any
        service_name = "Consulta"
        if entry.servico_id:
            stmt_serv = select(ServicoProduto).where(ServicoProduto.id == entry.servico_id)
            res_serv = await db_session.execute(stmt_serv)
            service = res_serv.scalar_one_or_none()
            if service:
                service_name = service.nome

        # Update waitlist status to notified
        entry.status = "notificado"

        # Formatted preferred date if available, or default
        if entry.data_preferida:
            formatted_dt = entry.data_preferida.astimezone(timezone(timedelta(hours=-3))).strftime("%d/%m às %H:%M")
        else:
            formatted_dt = "um horário em breve"

        # Clear existing conversation state and create a new one
        stmt_state = select(EstadoConversa).where(EstadoConversa.cliente_id == client.id)
        res_state = await db_session.execute(stmt_state)
        state = res_state.scalar_one_or_none()
        if state:
            await db_session.delete(state)
            await db_session.flush()

        state = EstadoConversa(
            id=uuid.uuid4(),
            tenant_id=entry.tenant_id,
            cliente_id=client.id,
            etapa_atual="lista_espera_oferta",
            dados_acumulados=json.dumps({
                "lista_espera_id": str(entry.id)
            })
        )
        db_session.add(state)
        await db_session.flush()

        reply = (
            f"Olá, {client.nome}! Um horário de atendimento para {service_name} surgiu para {formatted_dt}.\n\n"
            f"Você tem interesse em ficar com essa vaga?\n"
            f"1. Sim, quero agendar\n"
            f"2. Não tenho interesse\n\n"
            f"⏳ Atenção: Esta oferta expira em 15 minutos!"
        )

        await enviar_mensagem(
            str(entry.tenant_id),
            client.whatsapp,
            reply,
            instance_name=get_evolution_instance_name(entry.tenant_id, tenant),
        )

        # Log message
        log = LogMensagem(
            id=uuid.uuid4(),
            tenant_id=entry.tenant_id,
            cliente_whatsapp=client.whatsapp,
            direcao="saida",
            mensagem=reply,
            tipo="texto"
        )
        db_session.add(log)
        await db_session.flush()

        # Schedule the 15-minute expiration job using APScheduler
        try:
            from app.tasks.scheduler import scheduler
            run_time = datetime.now(timezone.utc) + timedelta(minutes=15)
            scheduler.add_job(
                processar_timeout_waitlist,
                trigger="date",
                run_date=run_time,
                args=[entry.tenant_id, entry.id, None],
                id=f"timeout_waitlist_{entry.id}",
                replace_existing=True
            )
            logger.info(f"Job de timeout manual agendado para lista_espera {entry.id} em {run_time}.")
        except Exception as e:
            logger.error(f"Erro ao agendar job de timeout para lista de espera: {e}")

        return True
    except Exception as e:
        logger.exception(f"Erro ao processar oferta manual de vaga: {e}")
        return False
