import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.models import Tenant, AtendimentoPedido, ClientePaciente, ServicoProduto, EstadoConversa, LogMensagem, Aprovacao, ItemAtendimento
from app.utils.mensagens import get_message
from app.services.tenant_settings import get_evolution_instance_name
from app.services.whatsapp_service import enviar_mensagem

logger = logging.getLogger(__name__)

async def processar_confirmacoes(db: Optional[AsyncSession] = None):
    """
    Scheduled task that runs 2x daily.
    """
    logger.info("Iniciando processamento de confirmações de 48h...")
    if db is None:
        async with AsyncSessionLocal() as session:
            try:
                await _run_confirmacoes(session)
                await session.commit()
            except Exception as e:
                logger.exception(f"Erro ao processar confirmações: {e}")
                await session.rollback()
    else:
        await _run_confirmacoes(db)

async def _run_confirmacoes(db: AsyncSession):
    # 1. Fetch all active tenants
    await db.execute(text("SET LOCAL app.bypass_rls = 'true'"))
    res_tenants = await db.execute(select(Tenant).where(Tenant.sistema_ativo == True))
    tenants = res_tenants.scalars().all()
    await db.execute(text("SET LOCAL app.bypass_rls = 'false'"))
    
    for tenant in tenants:
        # Enforce RLS context for this tenant
        await db.execute(text("SELECT set_tenant_id(:tenant_id)"), {"tenant_id": tenant.id})
        
        # Fetch clinic appointments only (stores don't have consultation scheduling)
        if tenant.tipo != "clinica":
            continue
        
        now = datetime.now(timezone.utc)
        min_time = now + timedelta(hours=44)
        max_time = now + timedelta(hours=52)
        
        # Query unconfirmed appointments in the 48h window and join with ClientePaciente (1-to-1 relationship)
        stmt = (
            select(AtendimentoPedido, ClientePaciente)
            .join(ClientePaciente, AtendimentoPedido.cliente_id == ClientePaciente.id)
            .where(
                AtendimentoPedido.tenant_id == tenant.id,
                AtendimentoPedido.status == "aguardando",
                AtendimentoPedido.confirmado == False,
                AtendimentoPedido.data_agendamento >= min_time,
                AtendimentoPedido.data_agendamento <= max_time
            )
        )
        res_appts = await db.execute(stmt)
        appointments_rows = res_appts.all()
        
        # Batch query all items for these appointments to find associated service names
        appt_ids = [row[0].id for row in appointments_rows]
        items_by_appt = {}
        if appt_ids:
            items_query = (
                select(ItemAtendimento.atendimento_id, ServicoProduto.nome)
                .join(ServicoProduto, ItemAtendimento.servico_id == ServicoProduto.id)
                .where(ItemAtendimento.atendimento_id.in_(appt_ids))
            )
            items_rows = (await db.execute(items_query)).all()
            for appt_id, service_name in items_rows:
                if appt_id not in items_by_appt:
                    items_by_appt[appt_id] = []
                items_by_appt[appt_id].append(service_name)

        for appt, client in appointments_rows:
            services_list = items_by_appt.get(appt.id, [])
            service_name = ", ".join(services_list) if services_list else "Consulta"
            
            # Formatted date/time
            formatted_dt = appt.data_agendamento.astimezone(timezone(timedelta(hours=-3))).strftime("%d/%m às %H:%M")
            
            # Check if there is an active conversational state
            stmt_state = select(EstadoConversa).where(EstadoConversa.cliente_id == client.id)
            res_state = await db.execute(stmt_state)
            state = res_state.scalar_one_or_none()
            
            if not state:
                # Initiate confirmation flow
                state = EstadoConversa(
                    id=uuid.uuid4(),
                    tenant_id=tenant.id,
                    cliente_id=client.id,
                    etapa_atual="confirmacao_48h",
                    dados_acumulados=json.dumps({
                        "atendimento_id": str(appt.id),
                        "sent_at": now.isoformat(),
                        "reminder_sent": False
                    })
                )
                db.add(state)
                await db.flush()
                
                reply = get_message(
                    "ask_confirmacao_48h",
                    nome=client.nome,
                    servico=service_name,
                    data_hora=formatted_dt
                )
                
                # Send WhatsApp
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
                db.add(log)
                await db.flush()
                
            elif state.etapa_atual == "confirmacao_48h":
                dados = json.loads(state.dados_acumulados) if state.dados_acumulados else {}
                if dados.get("atendimento_id") != str(appt.id):
                    continue # Belongs to a different appointment
                    
                sent_at = datetime.fromisoformat(dados["sent_at"])
                elapsed_hours = (now - sent_at).total_seconds() / 3600.0
                
                if elapsed_hours >= 8.0:
                    # 8 hours elapsed: escalate to aprovacoes
                    aprv = Aprovacao(
                        id=uuid.uuid4(),
                        tenant_id=tenant.id,
                        tipo="confirmacao_48h",
                        atendimento_id=appt.id,
                        cliente_id=client.id,
                        detalhes=f"Paciente {client.nome} não respondeu à confirmação de 48h para o agendamento em {formatted_dt}.",
                        status="pendente"
                    )
                    db.add(aprv)
                    
                    # Clean conversational state
                    await db.delete(state)
                    await db.flush()
                    
                    # Send final notification
                    reply = "Não conseguimos confirmar sua consulta de forma automática. Nossa equipe entrará em contato em breve para alinhar os detalhes! 📞"
                    await enviar_mensagem(
                        str(tenant.id),
                        client.whatsapp,
                        reply,
                        instance_name=get_evolution_instance_name(tenant.id, tenant),
                    )
                    
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
                    
                elif elapsed_hours >= 4.0 and not dados.get("reminder_sent"):
                    # 4 hours elapsed: send final reminder
                    dados["reminder_sent"] = True
                    state.dados_acumulados = json.dumps(dados)
                    await db.flush()
                    
                    reply = get_message(
                        "lembrete_final_48h",
                        nome=client.nome,
                        servico=service_name,
                        data_hora=formatted_dt
                    )
                    
                    await enviar_mensagem(
                        str(tenant.id),
                        client.whatsapp,
                        reply,
                        instance_name=get_evolution_instance_name(tenant.id, tenant),
                    )
                    
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
