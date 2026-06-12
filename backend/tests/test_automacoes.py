import pytest
import uuid
import json
import asyncio
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, text

from app.models.models import Tenant, ClientePaciente, ServicoProduto, Preco, AtendimentoPedido, ItemAtendimento, ListaEspera, EstadoConversa, LogMensagem, Aprovacao
from app.services.whatsapp_service import SENT_MESSAGES, clear_sent_messages
from app.tasks.confirmacao_task import processar_confirmacoes
from app.tasks.reativacao_task import processar_reativacoes
from app.services.lista_espera_service import processar_timeout_waitlist
from app.services import aprovacao_service
from tests.conftest import SuperuserSession
import app.services.whatsapp_service as ws

ws.SIMULATE_DELAY = False

async def post_webhook(client, payload):
    response = await client.post("/whatsapp/webhook", json=payload)
    await asyncio.sleep(0.1)
    return response

# Helper to setup clinic tenant and clients
async def setup_clinic_for_automations(admin_session):
    tenant = Tenant(
        id=uuid.uuid4(),
        nome="Clinica de Automacoes",
        tipo="clinica",
        whatsapp_numero="5511855555555",
        plano="pro",
        sistema_ativo=True,
        horario_abertura="00:00",
        horario_fechamento="23:59",
        limite_pedido_grande=5,
        cor_primaria="#10b981"
    )
    admin_session.add(tenant)
    await admin_session.flush()

    service = ServicoProduto(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        nome="Consulta Automática",
        categoria="Clinico Geral",
        duracao_minutos=30,
        ativo=True
    )
    admin_session.add(service)
    await admin_session.flush()

    client_a = ClientePaciente(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        nome="Paciente A",
        whatsapp="5511991111111",
        status_reativacao="ativo"
    )
    client_b = ClientePaciente(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        nome="Paciente B Fila",
        whatsapp="5511992222222",
        status_reativacao="ativo"
    )
    admin_session.add_all([client_a, client_b])
    await admin_session.flush()

    # Seed pricing
    p1 = Preco(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        servico_id=service.id,
        qtd_min=1,
        qtd_max=1,
        preco_particular=150.00
    )
    admin_session.add(p1)
    await admin_session.flush()

    await admin_session.commit()
    return tenant, service, client_a, client_b

@pytest.fixture(autouse=True)
def clean_whatsapp_queue():
    clear_sent_messages()

@pytest.mark.asyncio
async def test_48h_confirmation_and_waitlist_cascading(client, admin_session, db_session):
    tenant, service, client_a, client_b = await setup_clinic_for_automations(admin_session)
    
    tenant_id = tenant.id
    service_id = service.id
    client_a_id = client_a.id
    client_b_id = client_b.id
    client_a_whatsapp = client_a.whatsapp
    client_b_whatsapp = client_b.whatsapp
    
    # 1. Create appointment for Client A scheduled exactly 48h from now
    now = datetime.now(timezone.utc)
    appt_time = now + timedelta(hours=48)
    
    appt = AtendimentoPedido(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        cliente_id=client_a_id,
        data_agendamento=appt_time,
        status="aguardando",
        confirmado=False,
        total=150.00,
        lojista_aprovado=True,
        origem="whatsapp"
    )
    admin_session.add(appt)
    await admin_session.flush()
    
    appt_id = appt.id
    
    item = ItemAtendimento(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        atendimento_id=appt_id,
        servico_id=service_id,
        quantidade=1,
        preco_unitario=150.00
    )
    admin_session.add(item)
    
    # Add Client B to waiting list
    wait_list = ListaEspera(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        cliente_id=client_b_id,
        servico_id=service_id,
        data_preferida=now,
        status="aguardando"
    )
    admin_session.add(wait_list)
    await admin_session.commit()
    await db_session.commit()
    
    wait_list_id = wait_list.id

    # 2. Run confirmation task
    await processar_confirmacoes(db_session)
    await db_session.commit()
    
    # Assert state was created and message sent to Client A
    db_session.expire_all()
    await db_session.execute(text("SELECT set_tenant_id(:tenant_id)"), {"tenant_id": tenant_id})
    stmt_state = select(EstadoConversa).where(EstadoConversa.cliente_id == client_a_id)
    res_state = await db_session.execute(stmt_state)
    state = res_state.scalar_one()
    assert state.etapa_atual == "confirmacao_48h"
    
    assert len(SENT_MESSAGES) == 1
    assert client_a_whatsapp in SENT_MESSAGES[0]["numero"]
    msg_lower = SENT_MESSAGES[0]["mensagem"].lower()
    assert any(word in msg_lower for word in ["confirm", "horário", "horario", "agendamento", "marcado"])

    # 3. Simulate Client A replying '2' (Cancel) via webhook
    payload = {
        "event": "messages.upsert",
        "instance": f"saas_tenant_{tenant_id}",
        "data": {
            "key": {
                "remoteJid": f"{client_a_whatsapp}@s.whatsapp.net",
                "fromMe": False,
                "id": "MSG_CANCEL"
            },
            "message": {
                "conversation": "2"
            },
            "messageType": "conversation",
            "pushName": "Paciente A"
        }
    }
    
    await post_webhook(client, payload)
    await db_session.commit()
    db_session.expire_all()
    await db_session.execute(text("SELECT set_tenant_id(:tenant_id)"), {"tenant_id": tenant_id})
    
    # Assert appointment cancelled and Client A state cleaned
    appt_res = await db_session.execute(select(AtendimentoPedido).where(AtendimentoPedido.id == appt_id))
    db_appt = appt_res.scalar_one()
    assert db_appt.status == "cancelado"
    
    res_state = await db_session.execute(select(EstadoConversa).where(EstadoConversa.cliente_id == client_a_id))
    assert res_state.scalar_one_or_none() is None
    
    # Assert waitlist cascaded slot to Client B!
    # Waitlist item status should be 'notificado'
    wait_res = await db_session.execute(select(ListaEspera).where(ListaEspera.id == wait_list_id))
    db_wait = wait_res.scalar_one()
    assert db_wait.status == "notificado"
    
    # Client B should have waitlist state and message sent
    res_state_b = await db_session.execute(select(EstadoConversa).where(EstadoConversa.cliente_id == client_b_id))
    state_b = res_state_b.scalar_one()
    assert state_b.etapa_atual == "lista_espera_oferta"
    
    assert len(SENT_MESSAGES) == 3  # (1: Confirm invitation A, 2: Cancel confirmation A, 3: Waitlist Offer B)
    assert client_b_whatsapp in SENT_MESSAGES[-1]["numero"]
    assert "vaga" in SENT_MESSAGES[-1]["mensagem"].lower() or "surgiu" in SENT_MESSAGES[-1]["mensagem"].lower()

    # 4. Simulate Client B replying '1' (Accept offer) via webhook
    payload_b = {
        "event": "messages.upsert",
        "instance": f"saas_tenant_{tenant_id}",
        "data": {
            "key": {
                "remoteJid": f"{client_b_whatsapp}@s.whatsapp.net",
                "fromMe": False,
                "id": "MSG_ACCEPT"
            },
            "message": {
                "conversation": "1"
            },
            "messageType": "conversation",
            "pushName": "Paciente B"
        }
    }
    
    await post_webhook(client, payload_b)
    await db_session.commit()
    db_session.expire_all()
    await db_session.execute(text("SELECT set_tenant_id(:tenant_id)"), {"tenant_id": tenant_id})
    
    # Assert appointment reassigned to Client B and confirmed
    appt_res2 = await db_session.execute(select(AtendimentoPedido).where(AtendimentoPedido.id == appt_id))
    db_appt2 = appt_res2.scalar_one()
    assert db_appt2.cliente_id == client_b_id
    assert db_appt2.status == "confirmado"
    assert db_appt2.confirmado is True
    
    # Assert waitlist record status is 'agendado'
    wait_res2 = await db_session.execute(select(ListaEspera).where(ListaEspera.id == wait_list_id))
    db_wait2 = wait_res2.scalar_one()
    assert db_wait2.status == "agendado"
    
    # Assert Client B's state deleted
    res_state_b_post = await db_session.execute(select(EstadoConversa).where(EstadoConversa.cliente_id == client_b_id))
    assert res_state_b_post.scalar_one_or_none() is None

@pytest.mark.asyncio
async def test_waitlist_timeout_cascading(client, admin_session, db_session):
    tenant, service, client_a, client_b = await setup_clinic_for_automations(admin_session)
    
    tenant_id = tenant.id
    service_id = service.id
    client_a_id = client_a.id
    client_b_id = client_b.id
    
    # Seed Client C in waitlist
    client_c = ClientePaciente(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        nome="Paciente C Fila",
        whatsapp="5511993333333",
        status_reativacao="ativo"
    )
    admin_session.add(client_c)
    await admin_session.flush()
    
    client_c_id = client_c.id
    
    appt = AtendimentoPedido(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        cliente_id=client_a_id,
        data_agendamento=datetime.now(timezone.utc) + timedelta(hours=48),
        status="aguardando",
        confirmado=False,
        total=150.00,
        lojista_aprovado=True,
        origem="whatsapp"
    )
    admin_session.add(appt)
    await admin_session.flush()
    
    appt_id = appt.id
    
    item = ItemAtendimento(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        atendimento_id=appt_id,
        servico_id=service_id,
        quantidade=1,
        preco_unitario=150.00
    )
    admin_session.add(item)
    
    wait_b = ListaEspera(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        cliente_id=client_b_id,
        servico_id=service_id,
        data_preferida=datetime.now(timezone.utc) - timedelta(minutes=5),
        status="aguardando"
    )
    wait_c = ListaEspera(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        cliente_id=client_c_id,
        servico_id=service_id,
        data_preferida=datetime.now(timezone.utc),
        status="aguardando"
    )
    admin_session.add_all([wait_b, wait_c])
    await admin_session.commit()
    await db_session.commit()
    
    wait_b_id = wait_b.id
    wait_c_id = wait_c.id

    # Cancel appt to trigger waitlist notification to B
    async with SuperuserSession() as session:
        await session.execute(
            text("UPDATE atendimentos_pedidos SET status = 'cancelado' WHERE id = :id"),
            {"id": appt_id}
        )
        await session.commit()
        
    db_session.expire_all()
    await db_session.execute(text("SELECT set_tenant_id(:tenant_id)"), {"tenant_id": tenant_id})
    from app.services.lista_espera_service import ofertar_horario
    await ofertar_horario(db_session, tenant, appt_id)
    await db_session.commit()
    
    # Assert B is notified
    await db_session.commit()
    db_session.expire_all()
    await db_session.execute(text("SELECT set_tenant_id(:tenant_id)"), {"tenant_id": tenant_id})
    wait_b_res = await db_session.execute(select(ListaEspera).where(ListaEspera.id == wait_b_id))
    db_wait_b = wait_b_res.scalar_one()
    assert db_wait_b.status == "notificado"
    
    # Trigger timeout manually for B
    await processar_timeout_waitlist(tenant_id, wait_b_id, appt_id, db_session)
    await db_session.commit()
    db_session.expire_all()
    await db_session.execute(text("SELECT set_tenant_id(:tenant_id)"), {"tenant_id": tenant_id})
    
    # Assert B expired and state deleted
    wait_b_res2 = await db_session.execute(select(ListaEspera).where(ListaEspera.id == wait_b_id))
    db_wait_b2 = wait_b_res2.scalar_one()
    assert db_wait_b2.status == "expirado"
    
    res_state_b = await db_session.execute(select(EstadoConversa).where(EstadoConversa.cliente_id == client_b_id))
    
    # Assert C is notified next
    await db_session.commit()
    db_session.expire_all()
    await db_session.execute(text("SELECT set_tenant_id(:tenant_id)"), {"tenant_id": tenant_id})
    wait_c_res = await db_session.execute(select(ListaEspera).where(ListaEspera.id == wait_c_id))
    db_wait_c = wait_c_res.scalar_one()
    assert db_wait_c.status == "notificado"
    
    res_state_c = await db_session.execute(select(EstadoConversa).where(EstadoConversa.cliente_id == client_c_id))
    state_c = res_state_c.scalar_one()
    assert state_c.etapa_atual == "lista_espera_oferta"

@pytest.mark.asyncio
async def test_crm_reactivation_scheduler(admin_session, db_session):
    # Setup clinic
    tenant, service, client_a, client_b = await setup_clinic_for_automations(admin_session)
    
    now = datetime.now(timezone.utc)
    
    # Client A: last visit 4 months ago (120 days)
    client_a.ultima_consulta = now - timedelta(days=120)
    # Client B: last visit 7 months ago (210 days)
    client_b.ultima_consulta = now - timedelta(days=210)
    
    await admin_session.commit()
    await db_session.commit()
    
    # Run reactivation task
    await processar_reativacoes(db_session)
    await db_session.commit()
    db_session.expire_all()
    
    # Verify status transitions and messages sent
    await db_session.execute(text("SELECT set_tenant_id(:tenant_id)"), {"tenant_id": tenant.id})
    res_a = await db_session.execute(select(ClientePaciente).where(ClientePaciente.id == client_a.id))
    db_client_a = res_a.scalar_one()
    assert db_client_a.status_reativacao == "inativo_3m"
    
    res_b = await db_session.execute(select(ClientePaciente).where(ClientePaciente.id == client_b.id))
    db_client_b = res_b.scalar_one()
    assert db_client_b.status_reativacao == "inativo_6m"
    
    assert len(SENT_MESSAGES) == 2
    # Verify randomized templates triggered
    assert any(any(word in msg["mensagem"].lower() for word in ["agendar", "consulta", "atendimento", "visita", "horário", "horario"]) for msg in SENT_MESSAGES)

@pytest.mark.asyncio
async def test_large_order_owner_interception_flow(client, admin_session, db_session):
    # Setup store tenant
    from tests.test_whatsapp import setup_store_tenant
    tenant, product = await setup_store_tenant(admin_session)
    
    tenant_id = tenant.id
    phone_number = "5511977777777"
    jid = f"{phone_number}@s.whatsapp.net"
    owner_jid = "5511999999999@s.whatsapp.net"
    
    def make_payload(sender_jid, text_content):
        return {
            "event": "messages.upsert",
            "instance": f"saas_tenant_{tenant_id}",
            "data": {
                "key": {
                    "remoteJid": sender_jid,
                    "fromMe": False,
                    "id": str(uuid.uuid4())
                },
                "message": {
                    "conversation": text_content
                },
                "messageType": "conversation",
                "pushName": "Teste"
            }
        }

    # Run customer flow with large qty (12 un)
    await post_webhook(client, make_payload(jid, "Olá"))
    await post_webhook(client, make_payload(jid, "1"))
    await post_webhook(client, make_payload(jid, "12")) # exceeds limit
    await post_webhook(client, make_payload(jid, "Brinde"))
    await post_webhook(client, make_payload(jid, "1")) # Confirm
    await db_session.commit()
    db_session.expire_all()
    
    # Assert order requires approval and Owner received notification
    await db_session.execute(text("SELECT set_tenant_id(:tenant_id)"), {"tenant_id": tenant_id})
    client_res = await db_session.execute(select(ClientePaciente).where(ClientePaciente.whatsapp == phone_number))
    db_client = client_res.scalar_one()
    order_res = await db_session.execute(select(AtendimentoPedido).where(AtendimentoPedido.cliente_id == db_client.id))
    db_order = order_res.scalar_one()
    assert db_order.lojista_aprovado is False
    assert db_order.status == "aguardando"
    
    order_id = db_order.id
    
    # Owner must have a pending approval record
    aprv_res = await db_session.execute(select(Aprovacao).where(Aprovacao.atendimento_id == order_id))
    aprv = aprv_res.scalar_one()
    assert aprv.status == "pendente"
    assert aprv.tipo == "pedido_grande"
    
    aprv_id = aprv.id
    
    # Simulate Owner replying '1' (APPROVE) via webhook from owner_jid
    await post_webhook(client, make_payload(owner_jid, "1"))
    await db_session.commit()
    db_session.expire_all()
    await db_session.execute(text("SELECT set_tenant_id(:tenant_id)"), {"tenant_id": tenant_id})
    
    # Verify order is approved and in production
    db_order_post = (await db_session.execute(select(AtendimentoPedido).where(AtendimentoPedido.id == order_id))).scalar_one()
    assert db_order_post.lojista_aprovado is True
    assert db_order_post.status == "em_producao"
    
    # Approval record updated
    aprv_post = (await db_session.execute(select(Aprovacao).where(Aprovacao.id == aprv_id))).scalar_one()
    assert aprv_post.status == "aprovado"

@pytest.mark.asyncio
async def test_asaas_kill_switch_blocking_workflow(client, admin_session, db_session):
    # Setup clinic
    tenant, service, client_a, client_b = await setup_clinic_for_automations(admin_session)
    
    # Calculate overdue due date: 6 days ago
    overdue_date = (datetime.now(timezone.utc) - timedelta(days=6)).strftime("%Y-%m-%d")
    
    # 1. Post overdue webhook payload from Asaas
    overdue_payload = {
        "event": "payment.overdue",
        "payment": {
            "id": "pay_test123",
            "customer": "cus_test123",
            "value": 397.00,
            "externalReference": str(tenant.id),
            "dueDate": overdue_date,
            "invoiceUrl": "https://asaas.com/pay/pay_test123"
        }
    }
    
    res = await client.post("/webhooks/asaas", json=overdue_payload)
    assert res.status_code == 200
    assert res.json()["status"] == "blocked"
    
    # Assert tenant disabled in database (Kill Switch triggered!)
    await db_session.execute(text("SELECT set_tenant_id(:tenant_id)"), {"tenant_id": tenant.id})
    db_session.expire_all()
    db_tenant = await db_session.get(Tenant, tenant.id)
    assert db_tenant.sistema_ativo is False
    
    # Attempting to interact via client webhook triggers out of service reply
    payload_client = {
        "event": "messages.upsert",
        "instance": f"saas_tenant_{tenant.id}",
        "data": {
            "key": {
                "remoteJid": f"{client_a.whatsapp}@s.whatsapp.net",
                "fromMe": False,
                "id": "MSG_KILL_TRY"
            },
            "message": {
                "conversation": "Olá"
            },
            "messageType": "conversation",
            "pushName": "Paciente A"
        }
    }
    
    clear_sent_messages()
    await post_webhook(client, payload_client)
    assert len(SENT_MESSAGES) == 1
    assert "indisponível" in SENT_MESSAGES[0]["mensagem"].lower()
    
    # 2. Post payment received webhook from Asaas
    received_payload = {
        "event": "payment.received",
        "payment": {
            "id": "pay_test123",
            "customer": "cus_test123",
            "value": 397.00,
            "externalReference": str(tenant.id)
        }
    }
    
    res_rec = await client.post("/webhooks/asaas", json=received_payload)
    assert res_rec.status_code == 200
    assert res_rec.json()["status"] == "reactivated"
    
    # Assert tenant re-enabled in database
    db_session.expire_all()
    db_tenant_post = await db_session.get(Tenant, tenant.id)
    assert db_tenant_post.sistema_ativo is True
    
    # Client request works again
    clear_sent_messages()
    await post_webhook(client, payload_client)
    assert len(SENT_MESSAGES) == 1
    assert "indisponível" not in SENT_MESSAGES[0]["mensagem"].lower()
