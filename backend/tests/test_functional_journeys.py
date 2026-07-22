import uuid
from datetime import datetime, timezone

import pytest

from sqlalchemy import select

from app.models.models import LogAuditoria, Tenant, Usuario
from app.utils.security import get_password_hash


async def create_owner(admin_session):
    tenant = Tenant(
        id=uuid.uuid4(),
        nome="Operacao Funcional",
        tipo="loja",
        whatsapp_numero="5511999999999",
        owner_whatsapp="5511988888888",
        evolution_instance_name="functional-instance",
        plano="pro",
        sistema_ativo=True,
        horario_abertura="08:00",
        horario_fechamento="18:00",
        limite_pedido_grande=10,
        cor_primaria="#2563eb",
    )
    owner = Usuario(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        nome="Dono Funcional",
        email="funcional@example.com",
        senha_hash=get_password_hash("SenhaFuncional2026"),
        perfil="dono",
    )
    admin_session.add_all([tenant, owner])
    await admin_session.commit()
    return tenant, owner


@pytest.mark.asyncio
async def test_complete_dashboard_crud_and_reporting_journey(client, admin_session, monkeypatch):
    await create_owner(admin_session)
    login = await client.post(
        "/auth/login",
        json={"email": "funcional@example.com", "password": "SenhaFuncional2026"},
    )
    assert login.status_code == 200
    assert (await client.get("/auth/me")).status_code == 200

    config = await client.get("/configuracoes")
    assert config.status_code == 200
    config_update = await client.put(
        "/configuracoes",
        json={
            "limite_pedido_grande": 25,
            "mensagem_boas_vindas": "Bem-vindo ao atendimento",
            "owner_whatsapp": "+55 (11) 98888-8888",
            "evolution_instance_name": "functional-instance",
        },
    )
    assert config_update.status_code == 200
    assert config_update.json()["owner_whatsapp"] == "5511988888888"
    cleared_integration = await client.put(
        "/configuracoes",
        json={"owner_whatsapp": None, "evolution_instance_name": None},
    )
    assert cleared_integration.status_code == 200
    assert cleared_integration.json()["owner_whatsapp"] is None
    assert cleared_integration.json()["evolution_instance_name"] is None

    service = await client.post(
        "/servicos",
        json={
            "nome": "Caneca personalizada",
            "categoria": "Presentes",
            "duracao_minutos": 30,
            "precos": [
                {"qtd_min": 1, "qtd_max": 9, "preco_particular": 50.0},
                {"qtd_min": 10, "qtd_max": 100, "preco_particular": 42.5},
            ],
        },
    )
    assert service.status_code == 201
    service_id = service.json()["id"]
    assert len(service.json()["precos"]) == 2

    service_update = await client.put(
        f"/servicos/{service_id}",
        json={
            "nome": "Caneca premium",
            "categoria": "Presentes",
            "duracao_minutos": 45,
            "ativo": True,
            "precos": [{"qtd_min": 1, "qtd_max": 100, "preco_particular": 55.0}],
        },
    )
    assert service_update.status_code == 200
    assert service_update.json()["nome"] == "Caneca premium"

    first_client = await client.post(
        "/clientes",
        json={"nome": "Cliente Um", "whatsapp": "+55 (11) 97777-1111"},
    )
    second_client = await client.post(
        "/clientes",
        json={"nome": "Cliente Dois", "whatsapp": "5511977772222"},
    )
    assert first_client.status_code == second_client.status_code == 201
    first_client_id = first_client.json()["id"]
    second_client_id = second_client.json()["id"]
    duplicate_update = await client.put(
        f"/clientes/{second_client_id}",
        json={"nome": "Cliente Dois", "whatsapp": "5511977771111"},
    )
    assert duplicate_update.status_code == 400
    assert (await client.get("/clientes?search=Cliente&limit=1&offset=0")).status_code == 200
    assert (await client.get("/clientes?limit=1000")).status_code == 422

    invalid_appointment = await client.post(
        "/atendimentos",
        json={
            "cliente_id": first_client_id,
            "data_agendamento": "2026-02-10T10:00:00-03:00",
            "itens": [{"servico_id": str(uuid.uuid4()), "quantidade": 2, "preco_unitario": 50}],
        },
    )
    assert invalid_appointment.status_code == 404

    appointment = await client.post(
        "/atendimentos",
        json={
            "cliente_id": first_client_id,
            "data_agendamento": "2026-02-10T10:00:00-03:00",
            "itens": [{"servico_id": service_id, "quantidade": 2, "preco_unitario": 50}],
        },
    )
    assert appointment.status_code == 201
    assert appointment.json()["total"] == 100.0
    appointment_id = appointment.json()["id"]
    ready = await client.patch(f"/atendimentos/{appointment_id}/status", json={"status": "pronto"})
    assert ready.status_code == 200
    assert ready.json()["status"] == "pronto"
    completed = await client.patch(
        f"/atendimentos/{appointment_id}/status",
        json={"status": "entregue", "pago": True},
    )
    assert completed.status_code == 200
    assert completed.json()["pago"] is True
    assert completed.json()["data_entrega"] is not None

    outside_month = await client.post(
        "/atendimentos",
        json={
            "cliente_id": second_client_id,
            "data_agendamento": "2026-03-10T10:00:00-03:00",
            "status": "entregue",
            "total": 999.0,
            "pago": True,
        },
    )
    assert outside_month.status_code == 201

    invalid_waitlist = await client.post(
        "/lista-espera",
        json={
            "cliente_id": first_client_id,
            "servico_id": str(uuid.uuid4()),
            "data_preferida": "2026-04-01T09:00:00-03:00",
        },
    )
    assert invalid_waitlist.status_code == 404
    waitlist = await client.post(
        "/lista-espera",
        json={
            "cliente_id": first_client_id,
            "servico_id": service_id,
            "data_preferida": "2026-04-01T09:00:00-03:00",
        },
    )
    assert waitlist.status_code == 201
    waitlist_id = waitlist.json()["id"]
    assert len((await client.get("/lista-espera")).json()) == 1
    assert (await client.delete(f"/lista-espera/{waitlist_id}")).status_code == 204

    appointments = await client.get("/atendimentos?status=entregue")
    assert appointments.status_code == 200
    assert len(appointments.json()) == 2
    assert (await client.get("/atendimentos?status=inventado")).status_code == 422
    assert (await client.get("/dashboard/roi")).status_code == 200

    captured = {}

    def fake_monthly_pdf(**kwargs):
        captured.update(kwargs["dados"])
        return b"%PDF-functional"

    monkeypatch.setattr("app.routers.dashboard.gerar_pdf_roi_mensal", fake_monthly_pdf)
    monthly = await client.get("/relatorios/pdf/mensal?mes_ano=02/2026")
    assert monthly.status_code == 200
    assert monthly.content.startswith(b"%PDF")
    assert captured["total_atendimentos"] == 1
    assert captured["receita_total"] == 100.0
    assert (await client.get("/relatorios/pdf/mensal?mes_ano=13/2026")).status_code == 422

    daily = await client.get("/relatorios/pdf/dia?data=2026-02-10")
    assert daily.status_code == 200
    assert daily.content.startswith(b"%PDF")

    erased = await client.delete(f"/clientes/{first_client_id}/lgpd")
    assert erased.status_code == 204
    assert (await client.get(f"/clientes/{first_client_id}")).status_code == 404


@pytest.mark.asyncio
async def test_frontend_supported_terminal_statuses_are_accepted(client, admin_session):
    await create_owner(admin_session)
    await client.post(
        "/auth/login",
        json={"email": "funcional@example.com", "password": "SenhaFuncional2026"},
    )
    customer = await client.post(
        "/clientes",
        json={"nome": "Cliente Status", "whatsapp": "5511966666666"},
    )
    appointment = await client.post(
        "/atendimentos",
        json={
            "cliente_id": customer.json()["id"],
            "data_agendamento": datetime.now(timezone.utc).isoformat(),
        },
    )
    appointment_id = appointment.json()["id"]
    for status_name in ("pronto", "abandonado"):
        response = await client.patch(
            f"/atendimentos/{appointment_id}/status",
            json={"status": status_name},
        )
        assert response.status_code == 200
        assert response.json()["status"] == status_name


@pytest.mark.asyncio
async def test_owner_manages_real_operators_and_deactivation_revokes_sessions(client, admin_session):
    _, owner = await create_owner(admin_session)
    await client.post(
        "/auth/login",
        json={"email": "funcional@example.com", "password": "SenhaFuncional2026"},
    )

    initial = await client.get("/usuarios")
    assert initial.status_code == 200
    assert [item["email"] for item in initial.json()] == [owner.email]

    weak = await client.post(
        "/usuarios",
        json={
            "nome": "Operador Fraco",
            "email": "fraco@example.com",
            "password": "password1234",
            "perfil": "recepcionista",
        },
    )
    assert weak.status_code == 400

    created = await client.post(
        "/usuarios",
        json={
            "nome": "Operador Real",
            "email": "OPERADOR@example.com",
            "password": "OperadorSeguro2026",
            "perfil": "recepcionista",
        },
    )
    assert created.status_code == 201
    operator_id = created.json()["id"]
    assert created.json()["email"] == "operador@example.com"

    operator_login = await client.post(
        "/auth/login",
        json={"email": "operador@example.com", "password": "OperadorSeguro2026"},
    )
    assert operator_login.status_code == 200
    operator_token = client.cookies.get("access_token")
    assert (await client.get("/usuarios")).status_code == 403

    await client.post(
        "/auth/login",
        json={"email": "funcional@example.com", "password": "SenhaFuncional2026"},
    )
    deactivated = await client.delete(f"/usuarios/{operator_id}")
    assert deactivated.status_code == 204

    rejected = await client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {operator_token}"},
    )
    assert rejected.status_code == 401
    assert (await client.post(
        "/auth/login",
        json={"email": "operador@example.com", "password": "OperadorSeguro2026"},
    )).status_code == 401

    logs = (await admin_session.execute(
        select(LogAuditoria).where(LogAuditoria.registro_id == uuid.UUID(operator_id))
    )).scalars().all()
    assert {log.acao for log in logs} == {"USER_CREATE", "USER_DEACTIVATE"}
    assert all("password" not in (log.valores_novos or "") for log in logs)
