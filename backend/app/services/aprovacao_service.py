import logging
import uuid
import json
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, text

from app.database import AsyncSessionLocal
from app.models.models import Tenant, AtendimentoPedido, ClientePaciente, ServicoProduto, ItemAtendimento, Aprovacao, LogMensagem
from app.services.whatsapp_service import enviar_mensagem
from app.utils.mensagens import get_message

logger = logging.getLogger(__name__)

# Owner phone fallback (normally configured in tenant settings, but default to this for testing/demo)
DEFAULT_OWNER_PHONE = "5511999999999"

async def solicitar_aprovacao_pedido_grande(db_session, tenant: Tenant, order: AtendimentoPedido, client: ClientePaciente):
    """
    Initiates the large order approval flow:
    1. Creates a record in the 'aprovacoes' table.
    2. Sends a notification message to the owner's WhatsApp.
    3. Schedules reminder and critical timeout escalation jobs.
    """
    logger.info(f"Iniciando solicitação de aprovação de pedido grande para o pedido {order.id}...")
    
    # Fetch order item details
    stmt_item = select(ItemAtendimento).where(ItemAtendimento.atendimento_id == order.id)
    res_item = await db_session.execute(stmt_item)
    item = res_item.scalar_one_or_none()
    
    stmt_serv = select(ServicoProduto).where(ServicoProduto.id == item.servico_id) if item else None
    res_serv = await db_session.execute(stmt_serv) if stmt_serv is not None else None
    service = res_serv.scalar_one_or_none() if res_serv is not None else None
    product_name = service.nome if service else "Personalizado"
    
    qty = item.quantidade if item else 0
    total_val = float(order.total)
    
    # 1. Create entry in aprovacoes
    aprv = Aprovacao(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        tipo="pedido_grande",
        atendimento_id=order.id,
        cliente_id=client.id,
        detalhes=json.dumps({
            "cliente_nome": client.nome,
            "produto_nome": product_name,
            "quantidade": qty,
            "total": total_val,
            "sent_at": datetime.now(timezone.utc).isoformat()
        }),
        status="pendente"
    )
    db_session.add(aprv)
    await db_session.flush()
    
    # 2. Dispatch WhatsApp message to owner
    owner_phone = DEFAULT_OWNER_PHONE # In production, query owner's profile phone or setting
    
    reply = (
        f"🚨 *ALERTA DE PEDIDO GRANDE* 🚨\n\n"
        f"Um pedido acima do limite automático foi recebido e aguarda aprovação:\n\n"
        f"👤 *Cliente*: {client.nome}\n"
        f"📦 *Produto*: {product_name}\n"
        f"🔢 *Quantidade*: {qty} unidades\n"
        f"💵 *Valor Total*: R$ {total_val:.2f}\n\n"
        f"Responda com o número correspondente:\n"
        f"👉 *1* para *APROVAR* o pedido\n"
        f"👉 *2* para *RECUSAR* o pedido"
    )
    
    await enviar_mensagem(str(tenant.id), owner_phone, reply)
    
    # Log message
    log = LogMensagem(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        cliente_whatsapp=owner_phone,
        direcao="saida",
        mensagem=reply,
        tipo="texto"
    )
    db_session.add(log)
    await db_session.flush()
    
    # Schedule timeout jobs (2h warning, 4h escalation)
    try:
        from app.tasks.scheduler import scheduler
        now = datetime.now(timezone.utc)
        
        # 2h reminder
        scheduler.add_job(
            processar_timeout_aprovacao,
            trigger="date",
            run_date=now + timedelta(hours=2),
            args=[tenant.id, aprv.id, "lembrete"],
            id=f"timeout_aprovacao_reminder_{aprv.id}",
            replace_existing=True
        )
        
        # 4h critical warning escalation
        scheduler.add_job(
            processar_timeout_aprovacao,
            trigger="date",
            run_date=now + timedelta(hours=4),
            args=[tenant.id, aprv.id, "escalar"],
            id=f"timeout_aprovacao_escalate_{aprv.id}",
            replace_existing=True
        )
        logger.info(f"Agendado timeout jobs de 2h e 4h para aprovação {aprv.id}.")
    except Exception as e:
        logger.error(f"Erro ao agendar jobs de timeout para aprovação de pedido grande: {e}")

async def processar_decisao_dono(db_session, tenant: Tenant, aprv: Aprovacao, decisao: str):
    """
    Processes the owner's manual decision (APPROVE/REJECT) and advances the client order state.
    """
    logger.info(f"Processando decisão '{decisao}' do dono para a aprovação {aprv.id}...")
    
    # Cancel any scheduled timeout jobs
    try:
        from app.tasks.scheduler import scheduler
        scheduler.remove_job(f"timeout_aprovacao_reminder_{aprv.id}")
        scheduler.remove_job(f"timeout_aprovacao_escalate_{aprv.id}")
    except Exception:
        pass
        
    stmt_order = select(AtendimentoPedido).where(AtendimentoPedido.id == aprv.atendimento_id)
    res_order = await db_session.execute(stmt_order)
    order = res_order.scalar_one_or_none()
    
    stmt_client = select(ClientePaciente).where(ClientePaciente.id == aprv.cliente_id)
    res_client = await db_session.execute(stmt_client)
    client = res_client.scalar_one_or_none()
    
    if not order or not client:
        return
        
    if decisao == "aprovar":
        order.lojista_aprovado = True
        order.status = "em_producao"
        aprv.status = "aprovado"
        
        # Notify owner of success
        await enviar_mensagem(str(tenant.id), DEFAULT_OWNER_PHONE, "Pedido aprovado com sucesso! Iniciando produção. 👍")
        
        # Notify client
        client_reply = get_message("order_created_loja", produto="seu pedido")
        await enviar_mensagem(str(tenant.id), client.whatsapp, client_reply)
        
        # Log client message
        log = LogMensagem(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            cliente_whatsapp=client.whatsapp,
            direcao="saida",
            mensagem=client_reply,
            tipo="texto"
        )
        db_session.add(log)
        
    elif decisao == "recusar":
        order.status = "cancelado"
        aprv.status = "recusado"
        
        # Notify owner
        await enviar_mensagem(str(tenant.id), DEFAULT_OWNER_PHONE, "Pedido recusado e cancelado. ❌")
        
        # Notify client
        client_reply = "Olá! Infelizmente não pudemos aprovar seu pedido neste momento por limitações de estoque ou capacidade. Agradecemos a compreensão!"
        await enviar_mensagem(str(tenant.id), client.whatsapp, client_reply)
        
        log = LogMensagem(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            cliente_whatsapp=client.whatsapp,
            direcao="saida",
            mensagem=client_reply,
            tipo="texto"
        )
        db_session.add(log)
        
    await db_session.flush()

async def processar_timeout_aprovacao(tenant_id: uuid.UUID, aprv_id: uuid.UUID, acao: str):
    """
    APScheduler job running in a separate database session.
    Triggers renotifies after 2h or logs critical alerts after 4h.
    """
    logger.info(f"Processando timeout acao={acao} para aprovação {aprv_id}...")
    async with AsyncSessionLocal() as db:
        try:
            # Set RLS Context
            await db.execute(text("SELECT set_tenant_id(:tenant_id)"), {"tenant_id": tenant_id})
            
            stmt = select(Aprovacao).where(Aprovacao.id == aprv_id)
            res = await db.execute(stmt)
            aprv = res.scalar_one_or_none()
            
            if aprv and aprv.status == "pendente":
                details = json.loads(aprv.detalhes) if aprv.detalhes else {}
                cliente_nome = details.get("cliente_nome", "Cliente")
                
                if acao == "lembrete":
                    # Send warning renotification
                    reply = f"⚠️ *LEMBRETE PENDENTE* ⚠️\n\nO pedido do cliente {cliente_nome} ainda aguarda sua aprovação. Responda 1 para APROVAR ou 2 para RECUSAR."
                    await enviar_mensagem(str(tenant_id), DEFAULT_OWNER_PHONE, reply)
                elif acao == "escalar":
                    # Escalation: Log a critical warning or update details
                    # (In production, this triggers dashboard notification banners)
                    logger.warning(f"CRITICAL: Aprovação {aprv_id} não respondida em 4h!")
                    
            await db.commit()
        except Exception as e:
            logger.exception(f"Erro no timeout de aprovação: {e}")
            await db.rollback()
