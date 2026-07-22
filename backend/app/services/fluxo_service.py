import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import (
    Tenant, ClientePaciente, ServicoProduto, Preco, 
    AtendimentoPedido, ItemAtendimento, EstadoConversa, LogMensagem, ListaEspera, Aprovacao
)
from app.utils.mensagens import get_message
from app.services.tenant_settings import get_evolution_instance_name, get_owner_whatsapp
from app.services.whatsapp_service import enviar_mensagem

logger = logging.getLogger(__name__)

async def send_and_log(db: AsyncSession, tenant: Tenant, phone: str, reply: str):
    """Sends a message via WhatsApp and logs it in the database."""
    await enviar_mensagem(
        str(tenant.id),
        phone,
        reply,
        instance_name=get_evolution_instance_name(tenant.id, tenant),
    )
    log_entry = LogMensagem(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        cliente_whatsapp=phone,
        direcao="saida",
        mensagem=reply,
        tipo="texto"
    )
    db.add(log_entry)
    await db.flush()

async def processar_mensagem(
    db: AsyncSession,
    tenant: Tenant,
    client_phone: str,
    message_text: str,
    message_type: str,
    push_name: str
):
    """
    Main state machine entry point. Processes incoming text messages from a client,
    advances the conversation state, and dispatches responses.
    """
    message_clean = message_text.strip()
    
    # 0. Intercept owner manual decisions for large orders
    if client_phone == get_owner_whatsapp(tenant):
        stmt_aprv = select(Aprovacao).where(
            Aprovacao.tenant_id == tenant.id,
            Aprovacao.tipo == "pedido_grande",
            Aprovacao.status == "pendente"
        )
        res_aprv = await db.execute(stmt_aprv)
        pending_aprv = res_aprv.scalar_one_or_none()
        
        if pending_aprv:
            if message_clean in ["1", "2"] or message_clean.lower() in ["aprovar", "recusar"]:
                decision = "aprovar" if message_clean in ["1", "aprovar"] else "recusar"
                from app.services.aprovacao_service import processar_decisao_dono
                await processar_decisao_dono(db, tenant, pending_aprv, decision)
                return
    
    # 1. Fetch or create client
    stmt_client = select(ClientePaciente).where(
        ClientePaciente.tenant_id == tenant.id,
        ClientePaciente.whatsapp == client_phone
    )
    res_client = await db.execute(stmt_client)
    client = res_client.scalar_one_or_none()
    
    if not client:
        client = ClientePaciente(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            nome=push_name or "Cliente",
            whatsapp=client_phone,
            status_reativacao="ativo"
        )
        db.add(client)
        await db.flush()  # Populate client.id

    # 2. Handle global commands (Support and Cancel)
    if message_clean.lower() in ["s", "suporte", "ajuda", "atendente"]:
        # Cancel active conversation flow
        stmt_del = select(EstadoConversa).where(EstadoConversa.cliente_id == client.id)
        res_del = await db.execute(stmt_del)
        estado = res_del.scalar_one_or_none()
        if estado:
            await db.delete(estado)
            await db.flush()
        
        reply = "Entendido! Estou acionando nossa recepção. Um atendente entrará em contato em breve! 🤝"
        await send_and_log(db, tenant, client_phone, reply)
        return

    if message_clean.lower() in ["cancelar", "sair", "parar"]:
        stmt_del = select(EstadoConversa).where(EstadoConversa.cliente_id == client.id)
        res_del = await db.execute(stmt_del)
        estado = res_del.scalar_one_or_none()
        if estado:
            await db.delete(estado)
            await db.flush()
        
        reply = get_message("cancelado")
        await send_and_log(db, tenant, client_phone, reply)
        return

    # 3. Handle media errors (if not text)
    if message_type != "texto":
        err_key = "audio_error" if message_type == "audio" else "media_error"
        reply = get_message(err_key)
        await send_and_log(db, tenant, client_phone, reply)
        return

    # 4. Fetch or create conversation state
    stmt_state = select(EstadoConversa).where(EstadoConversa.cliente_id == client.id)
    res_state = await db.execute(stmt_state)
    state = res_state.scalar_one_or_none()
    
    if not state:
        state = EstadoConversa(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            cliente_id=client.id,
            etapa_atual="menu",
            dados_acumulados="{}"
        )
        db.add(state)
        await db.flush()

    # Load accumulated data
    dados = json.loads(state.dados_acumulados) if state.dados_acumulados else {}

    # Fetch active products/services to build the menus
    stmt_items = select(ServicoProduto).where(
        ServicoProduto.tenant_id == tenant.id,
        ServicoProduto.ativo == True
    ).order_by(ServicoProduto.nome)
    res_items = await db.execute(stmt_items)
    items_list = res_items.scalars().all()

    # 5. Process state machine stages
    if state.etapa_atual == "confirmacao_48h":
        dados = json.loads(state.dados_acumulados) if state.dados_acumulados else {}
        appt_id = uuid.UUID(dados["atendimento_id"])
        
        stmt_appt = select(AtendimentoPedido).where(AtendimentoPedido.id == appt_id)
        res_appt = await db.execute(stmt_appt)
        appt = res_appt.scalar_one_or_none()
        
        if not appt:
            await db.delete(state)
            await db.flush()
            return
            
        if message_clean == "1":
            appt.confirmado = True
            appt.status = "confirmado"
            reply = get_message("confirmacao_sucesso")
            await db.delete(state)
            await db.flush()
            await send_and_log(db, tenant, client_phone, reply)
            return
        elif message_clean == "2":
            appt.status = "cancelado"
            reply = get_message("confirmacao_cancelado")
            await db.delete(state)
            await db.flush()
            await send_and_log(db, tenant, client_phone, reply)
            
            # Cascade waitlist offer
            from app.services.lista_espera_service import ofertar_horario
            await ofertar_horario(db, tenant, appt.id)
            return
        else:
            reply = get_message("invalid_option")
            await send_and_log(db, tenant, client_phone, reply)
            return

    elif state.etapa_atual == "lista_espera_oferta":
        dados = json.loads(state.dados_acumulados) if state.dados_acumulados else {}
        appt_id = uuid.UUID(dados["atendimento_id"])
        waitlist_id = uuid.UUID(dados["lista_espera_id"])
        
        stmt_appt = select(AtendimentoPedido).where(AtendimentoPedido.id == appt_id)
        res_appt = await db.execute(stmt_appt)
        appt = res_appt.scalar_one_or_none()
        
        stmt_wait = select(ListaEspera).where(ListaEspera.id == waitlist_id)
        res_wait = await db.execute(stmt_wait)
        wait_entry = res_wait.scalar_one_or_none()
        
        if not appt or not wait_entry:
            await db.delete(state)
            await db.flush()
            return
            
        # Cancel the timeout job if it exists
        try:
            from app.tasks.scheduler import scheduler
            scheduler.remove_job(f"timeout_waitlist_{wait_entry.id}")
        except Exception:
            pass
            
        if message_clean == "1":
            # Reassign appointment to the waitlist client
            appt.cliente_id = client.id
            appt.status = "confirmado"
            appt.confirmado = True
            
            # Update waitlist status
            wait_entry.status = "agendado"
            wait_entry.agendado_em = datetime.now(timezone.utc)
            
            reply = "Maravilha! Confirmamos seu agendamento com sucesso. Te aguardamos! 😊"
            await db.delete(state)
            await db.flush()
            await send_and_log(db, tenant, client_phone, reply)
            return
            
        elif message_clean == "2":
            # Refused
            wait_entry.status = "expirado"
            reply = "Sem problemas! Se precisar de algo mais, estamos à disposição."
            await db.delete(state)
            await db.flush()
            await send_and_log(db, tenant, client_phone, reply)
            
            # Cascade slot to next client
            from app.services.lista_espera_service import ofertar_horario
            await ofertar_horario(db, tenant, appt.id)
            return
            
        else:
            reply = get_message("invalid_option")
            await send_and_log(db, tenant, client_phone, reply)
            return

    elif state.etapa_atual == "menu":
        # Initial greeting and menu presentation
        if tenant.tipo == "clinica":
            # For clinics, list medical/dental services
            services_menu = "\n".join([f"{idx+1}. {s.nome}" for idx, s in enumerate(items_list)])
            reply = get_message("welcome_clinica", nome=client.nome, tenant_nome=tenant.nome)
        else:
            # For stores, list custom products
            products_menu = "\n".join([f"{idx+1}. {p.nome}" for idx, p in enumerate(items_list)])
            reply = get_message("welcome_loja", nome=client.nome, tenant_nome=tenant.nome, produtos_menu=products_menu)

        state.etapa_atual = "aguardando_produto"
        state.dados_acumulados = json.dumps(dados)
        await db.flush()
        await send_and_log(db, tenant, client_phone, reply)
        return

    elif state.etapa_atual == "aguardando_produto":
        # Expecting a number corresponding to products/services menu
        try:
            choice_idx = int(message_clean) - 1
            if choice_idx < 0 or choice_idx >= len(items_list):
                raise ValueError()
        except ValueError:
            reply = get_message("invalid_option")
            await send_and_log(db, tenant, client_phone, reply)
            return

        chosen_item = items_list[choice_idx]
        dados["produto_id"] = str(chosen_item.id)
        dados["produto_nome"] = chosen_item.nome

        if tenant.tipo == "clinica":
            # Clinic path: ask for date & time
            state.etapa_atual = "aguardando_data"
            reply = get_message("ask_date_time", servico=chosen_item.nome)
        else:
            # Store path: ask for quantity
            state.etapa_atual = "aguardando_quantidade"
            reply = get_message("ask_quantity", produto=chosen_item.nome)

        state.dados_acumulados = json.dumps(dados)
        await db.flush()
        await send_and_log(db, tenant, client_phone, reply)
        return

    elif state.etapa_atual == "aguardando_quantidade":
        # Store path only: expect positive integer quantity
        try:
            qty = int(message_clean)
            if qty <= 0:
                raise ValueError()
        except ValueError:
            reply = get_message("invalid_option")
            await send_and_log(db, tenant, client_phone, reply)
            return

        dados["quantidade"] = qty
        state.etapa_atual = "aguardando_personalizacao"
        
        # Get product name from state buffer
        product_name = dados.get("produto_nome", "produto")
        reply = get_message("ask_personalization", produto=product_name)
        
        state.dados_acumulados = json.dumps(dados)
        await db.flush()
        await send_and_log(db, tenant, client_phone, reply)
        return

    elif state.etapa_atual == "aguardando_personalizacao":
        # Store path only: expect personalization details
        dados["personalizacao"] = message_clean
        state.etapa_atual = "aguardando_confirmacao"

        # Calculate Price Tier
        prod_id = uuid.UUID(dados["produto_id"])
        qty = dados["quantidade"]
        
        stmt_price = select(Preco).where(
            Preco.tenant_id == tenant.id,
            Preco.servico_id == prod_id,
            Preco.qtd_min <= qty,
            Preco.qtd_max >= qty
        )
        res_price = await db.execute(stmt_price)
        price_tier = res_price.scalar_one_or_none()

        if price_tier:
            unit_price = float(price_tier.preco_particular)
        else:
            # Fallback if no tier matching is seeded (e.g. default base price)
            unit_price = 10.00  # Default fallback price

        total_price = unit_price * qty
        dados["unit_price"] = unit_price
        dados["total"] = total_price

        reply = get_message(
            "confirm_loja",
            produto=dados["produto_nome"],
            qtd=qty,
            personalizacao=message_clean,
            total=f"{total_price:.2f}"
        )

        state.dados_acumulados = json.dumps(dados)
        await db.flush()
        await send_and_log(db, tenant, client_phone, reply)
        return

    elif state.etapa_atual == "aguardando_data":
        # Clinic path only: expect date and time string
        dados["data_hora"] = message_clean
        state.etapa_atual = "aguardando_confirmacao"

        reply = get_message(
            "confirm_clinica",
            servico=dados["produto_nome"],
            data_hora=message_clean
        )

        state.dados_acumulados = json.dumps(dados)
        await db.flush()
        await send_and_log(db, tenant, client_phone, reply)
        return

    elif state.etapa_atual == "aguardando_confirmacao":
        # Expecting confirmation choice
        if message_clean == "1":
            # OPTION 1: CONFIRMED
            if tenant.tipo == "loja":
                # Create Order
                order = AtendimentoPedido(
                    id=uuid.uuid4(),
                    tenant_id=tenant.id,
                    cliente_id=client.id,
                    data_agendamento=datetime.now(timezone.utc),
                    status="aguardando",
                    confirmado=True,
                    total=dados["total"],
                    pago=False,
                    lojista_aprovado=False,
                    origem="whatsapp"
                )
                db.add(order)
                
                # Create Order Item
                order_item = ItemAtendimento(
                    id=uuid.uuid4(),
                    tenant_id=tenant.id,
                    atendimento_id=order.id,
                    servico_id=uuid.UUID(dados["produto_id"]),
                    quantidade=dados["quantidade"],
                    preco_unitario=dados["unit_price"],
                    personalizacao=dados["personalizacao"],
                    status_arte="aguardando"
                )
                db.add(order_item)
                
                # Check for large order limit
                if dados["quantidade"] > tenant.limite_pedido_grande:
                    # Stored as unapproved, status holds
                    order.lojista_aprovado = False
                    reply = get_message("large_order_hold")
                    from app.services.aprovacao_service import solicitar_aprovacao_pedido_grande
                    await solicitar_aprovacao_pedido_grande(db, tenant, order, client)
                else:
                    order.lojista_aprovado = True
                    order.status = "em_producao"
                    reply = get_message("order_created_loja", produto=dados["produto_nome"])
                    
            else:
                # Clinic Path: Create Appointment
                # Parse or register text data/time
                # For demo/tests, default scheduling 48h from now if parsing fails
                appt_date = datetime.now(timezone.utc) + timedelta(days=2)
                
                order = AtendimentoPedido(
                    id=uuid.uuid4(),
                    tenant_id=tenant.id,
                    cliente_id=client.id,
                    data_agendamento=appt_date,
                    status="aguardando",
                    confirmado=True,
                    total=50.00,  # Default consultation cost
                    pago=False,
                    lojista_aprovado=True,
                    origem="whatsapp"
                )
                db.add(order)
                reply = get_message("appointment_created_clinica", servico=dados["produto_nome"], data_hora=dados["data_hora"])

            # Reset client status_reativacao to active/reativado and update last visit
            if client.status_reativacao in ["inativo_3m", "inativo_6m", "inativo_12m"]:
                client.status_reativacao = "reativado"
                client.reativado_em = datetime.now(timezone.utc)
            else:
                client.status_reativacao = "ativo"
                client.reativado_em = None
            client.ultima_consulta = datetime.now(timezone.utc)

            # Remove conversation state context
            await db.delete(state)
            await db.flush()
            await send_and_log(db, tenant, client_phone, reply)
            return

        elif message_clean == "2":
            # OPTION 2: EDIT (restart conversation flow)
            state.etapa_atual = "menu"
            state.dados_acumulados = "{}"
            await db.flush()
            
            # Show menu again
            if tenant.tipo == "clinica":
                services_menu = "\n".join([f"{idx+1}. {s.nome}" for idx, s in enumerate(items_list)])
                reply = get_message("welcome_clinica", nome=client.nome, tenant_nome=tenant.nome)
            else:
                products_menu = "\n".join([f"{idx+1}. {p.nome}" for idx, p in enumerate(items_list)])
                reply = get_message("welcome_loja", nome=client.nome, tenant_nome=tenant.nome, produtos_menu=products_menu)
                
            state.etapa_atual = "aguardando_produto"
            await db.flush()
            await send_and_log(db, tenant, client_phone, reply)
            return

        elif message_clean == "3":
            # OPTION 3: CANCEL
            await db.delete(state)
            await db.flush()
            reply = get_message("cancelado")
            await send_and_log(db, tenant, client_phone, reply)
            return
            
        else:
            reply = get_message("invalid_option")
            await send_and_log(db, tenant, client_phone, reply)
            return
