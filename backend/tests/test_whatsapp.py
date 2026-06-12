import pytest
import uuid
import json
import asyncio
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, text

from app.models.models import Tenant, ServicoProduto, Preco, ClientePaciente, AtendimentoPedido, ItemAtendimento, EstadoConversa, LogMensagem
from app.services.whatsapp_service import SENT_MESSAGES, clear_sent_messages
from tests.conftest import SuperuserSession
import app.services.whatsapp_service as ws

ws.SIMULATE_DELAY = False

async def post_webhook(client, payload):
    """Helper to post to webhook and yield event loop to let FastAPI BackgroundTasks finish."""
    response = await client.post("/whatsapp/webhook", json=payload)
    await asyncio.sleep(0.1)  # Allow BackgroundTasks to fully execute and commit
    return response

# Helper to seed a Store Tenant and Product with Tiered Pricing
async def setup_store_tenant(admin_session):
    tenant = Tenant(
        id=uuid.uuid4(),
        nome="Loja de Personalizados Teste",
        tipo="loja",
        whatsapp_numero="5511999999999",
        plano="starter",
        sistema_ativo=True,
        horario_abertura="00:00",
        horario_fechamento="23:59",
        limite_pedido_grande=10,
        cor_primaria="#2563eb"
    )
    admin_session.add(tenant)
    await admin_session.flush()

    # Product
    product = ServicoProduto(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        nome="Caneca Personalizada",
        categoria="Canecas",
        ativo=True
    )
    admin_session.add(product)
    await admin_session.flush()

    # Pricing Tiers
    # 1 - 5 units: R$ 20.00 each
    p1 = Preco(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        servico_id=product.id,
        qtd_min=1,
        qtd_max=5,
        preco_particular=20.00
    )
    # 6 - 20 units: R$ 15.00 each
    p2 = Preco(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        servico_id=product.id,
        qtd_min=6,
        qtd_max=20,
        preco_particular=15.00
    )
    admin_session.add_all([p1, p2])
    await admin_session.commit()

    return tenant, product

# Helper to seed a Clinic Tenant and Service
async def setup_clinic_tenant(admin_session):
    tenant = Tenant(
        id=uuid.uuid4(),
        nome="Clinica Dentaria Teste",
        tipo="clinica",
        whatsapp_numero="5511888888888",
        plano="pro",
        sistema_ativo=True,
        horario_abertura="00:00",
        horario_fechamento="23:59",
        limite_pedido_grande=5,
        cor_primaria="#10b981"
    )
    admin_session.add(tenant)
    await admin_session.flush()

    # Service
    service = ServicoProduto(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        nome="Limpeza Dental",
        categoria="Dentística",
        duracao_minutos=30,
        ativo=True
    )
    admin_session.add(service)
    await admin_session.commit()

    return tenant, service

@pytest.fixture(autouse=True)
def clean_whatsapp_queue():
    clear_sent_messages()

@pytest.mark.asyncio
async def test_webhook_returns_quickly(client, admin_session):
    tenant, product = await setup_store_tenant(admin_session)

    # Webhook payload representation from Evolution API
    payload = {
        "event": "messages.upsert",
        "instance": f"saas_tenant_{tenant.id}",
        "data": {
            "key": {
                "remoteJid": "5511988888888@s.whatsapp.net",
                "fromMe": False,
                "id": "MSG12345"
            },
            "message": {
                "conversation": "Olá"
            },
            "messageType": "conversation",
            "pushName": "Felpopo"
        }
    }

    # Post webhook using the helper (the response should be immediate, but helper waits for bg tasks)
    response = await post_webhook(client, payload)
    assert response.status_code == 200
    assert response.json() == {"status": "processing"}

@pytest.mark.asyncio
async def test_complete_store_flow_success(client, admin_session, db_session):
    tenant, product = await setup_store_tenant(admin_session)
    phone_number = "5511988888888"
    jid = f"{phone_number}@s.whatsapp.net"

    def make_payload(text_content):
        return {
            "event": "messages.upsert",
            "instance": f"saas_tenant_{tenant.id}",
            "data": {
                "key": {
                    "remoteJid": jid,
                    "fromMe": False,
                    "id": str(uuid.uuid4())
                },
                "message": {
                    "conversation": text_content
                },
                "messageType": "conversation",
                "pushName": "Paciente Teste"
            }
        }

    # Step 1: Send "Olá" -> Expect Welcome Menu listing the Caneca
    res1 = await post_webhook(client, make_payload("Olá"))
    assert res1.status_code == 200
    assert len(SENT_MESSAGES) == 1
    assert "Caneca Personalizada" in SENT_MESSAGES[0]["mensagem"]
    
    # Step 2: Choose Product 1 -> Expect ask quantity
    res2 = await post_webhook(client, make_payload("1"))
    assert res2.status_code == 200
    assert len(SENT_MESSAGES) == 2
    assert "Caneca Personalizada" in SENT_MESSAGES[1]["mensagem"]
    assert any(w in SENT_MESSAGES[1]["mensagem"].lower() for w in ["quantidade", "quantas", "unidade", "unidades"])

    # Step 3: Enter quantity "3" (within regular limit) -> Expect ask personalization
    res3 = await post_webhook(client, make_payload("3"))
    assert res3.status_code == 200
    assert len(SENT_MESSAGES) == 3
    assert any(w in SENT_MESSAGES[2]["mensagem"].lower() for w in ["personalizar", "personalização", "personalizacao", "arte", "detalhes"])

    # Step 4: Enter personalization -> Expect review summary with tier price calculation
    # Since quantity = 3, p1 applies: R$ 20.00 * 3 = R$ 60.00
    res4 = await post_webhook(client, make_payload("Tema Naruto com nome Felpopo"))
    assert res4.status_code == 200
    assert len(SENT_MESSAGES) == 4
    assert "Naruto" in SENT_MESSAGES[3]["mensagem"]
    assert "60.00" in SENT_MESSAGES[3]["mensagem"] # 3 * 20.00

    # Step 5: Confirm order "1" -> Expect success message and DB records
    res5 = await post_webhook(client, make_payload("1"))
    assert res5.status_code == 200
    assert len(SENT_MESSAGES) == 5
    assert any(word in SENT_MESSAGES[4]["mensagem"].lower() for word in ["sucesso", "registrado", "sistema", "cadastrado", "preferência", "preferencia"])

    # Verify Database records under correct RLS context
    await db_session.execute(text("SELECT set_tenant_id(:tenant_id)"), {"tenant_id": tenant.id})
    
    # Check ClientPaciente was created
    client_res = await db_session.execute(select(ClientePaciente).where(ClientePaciente.whatsapp == phone_number))
    db_client = client_res.scalar_one_or_none()
    assert db_client is not None
    assert db_client.nome == "Paciente Teste"

    # Check AtendimentoPedido was created
    order_res = await db_session.execute(select(AtendimentoPedido).where(AtendimentoPedido.cliente_id == db_client.id))
    order = order_res.scalar_one_or_none()
    assert order is not None
    assert float(order.total) == 60.00
    assert order.lojista_aprovado is True
    assert order.status == "em_producao"

    # Check ItemAtendimento details
    item_res = await db_session.execute(select(ItemAtendimento).where(ItemAtendimento.atendimento_id == order.id))
    item = item_res.scalar_one_or_none()
    assert item is not None
    assert item.quantidade == 3
    assert float(item.preco_unitario) == 20.00
    assert item.personalizacao == "Tema Naruto com nome Felpopo"

@pytest.mark.asyncio
async def test_large_order_requires_approval(client, admin_session, db_session):
    tenant, product = await setup_store_tenant(admin_session)
    phone_number = "5511977777777"
    jid = f"{phone_number}@s.whatsapp.net"

    def make_payload(text_content):
        return {
            "event": "messages.upsert",
            "instance": f"saas_tenant_{tenant.id}",
            "data": {
                "key": {
                    "remoteJid": jid,
                    "fromMe": False,
                    "id": str(uuid.uuid4())
                },
                "message": {
                    "conversation": text_content
                },
                "messageType": "conversation",
                "pushName": "Atacado"
            }
        }

    # Run flow
    await post_webhook(client, make_payload("Olá"))
    await post_webhook(client, make_payload("1"))
    # Quantity "12" is larger than limite_pedido_grande=10, p2 price applies (15.00 each -> Total = R$ 180.00)
    await post_webhook(client, make_payload("12"))
    await post_webhook(client, make_payload("Brinde de Empresa"))
    
    # Confirm
    await post_webhook(client, make_payload("1"))

    # Verify RLS isolation
    await db_session.execute(text("SELECT set_tenant_id(:tenant_id)"), {"tenant_id": tenant.id})
    client_res = await db_session.execute(select(ClientePaciente).where(ClientePaciente.whatsapp == phone_number))
    db_client = client_res.scalar_one()

    # Query the order
    order_res = await db_session.execute(select(AtendimentoPedido).where(AtendimentoPedido.cliente_id == db_client.id))
    order = order_res.scalar_one()

    # Assert it requires lojista approval
    assert order.lojista_aprovado is False
    assert order.status == "aguardando"
    assert float(order.total) == 180.00  # 12 * 15.00

    # Assert holds template notification was sent
    assert any(word in SENT_MESSAGES[-1]["mensagem"].lower() for word in ["gerente", "gerência", "gerencia", "aprovação", "aprovacao", "grande porte", "volume grande"])

@pytest.mark.asyncio
async def test_kill_switch_triggers_service_unavailable(client, admin_session):
    tenant, product = await setup_store_tenant(admin_session)

    # Trigger Kill Switch: disable system
    async with SuperuserSession() as session:
        await session.execute(
            text("UPDATE tenants SET sistema_ativo = False WHERE id = :id"),
            {"id": tenant.id}
        )
        await session.commit()

    payload = {
        "event": "messages.upsert",
        "instance": f"saas_tenant_{tenant.id}",
        "data": {
            "key": {
                "remoteJid": "5511988888888@s.whatsapp.net",
                "fromMe": False,
                "id": "MSG_KILL"
            },
            "message": {
                "conversation": "Oi"
            },
            "messageType": "conversation",
            "pushName": "Teste"
        }
    }

    # Run webhook
    await post_webhook(client, payload)
    
    # Expect service unavailable reply
    assert len(SENT_MESSAGES) == 1
    assert "indisponível" in SENT_MESSAGES[0]["mensagem"].lower()

@pytest.mark.asyncio
async def test_out_of_hours_trigger(client, admin_session):
    tenant, product = await setup_store_tenant(admin_session)

    # Force out of hours settings
    async with SuperuserSession() as session:
        await session.execute(
            text("UPDATE tenants SET horario_abertura = '23:58', horario_fechamento = '23:59' WHERE id = :id"),
            {"id": tenant.id}
        )
        await session.commit()

    payload = {
        "event": "messages.upsert",
        "instance": f"saas_tenant_{tenant.id}",
        "data": {
            "key": {
                "remoteJid": "5511988888888@s.whatsapp.net",
                "fromMe": False,
                "id": "MSG_HOURS"
            },
            "message": {
                "conversation": "Quero comprar"
            },
            "messageType": "conversation",
            "pushName": "Comprador Noturno"
        }
    }

    # Run webhook
    await post_webhook(client, payload)

    # Expect out of hours reply
    assert len(SENT_MESSAGES) == 1
    msg_lower = SENT_MESSAGES[0]["mensagem"].lower()
    assert any(word in msg_lower for word in ["fechados", "funcionamos", "funcionamento", "expediente"])
