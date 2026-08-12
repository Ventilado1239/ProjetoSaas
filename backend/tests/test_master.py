import uuid

import pytest
from sqlalchemy import select, text

from app.models.models import MasterAdmin, MasterAuditLog, Tenant, Usuario
from app.utils.security import get_password_hash


@pytest.mark.asyncio
async def test_master_provisioning_and_password_reset_are_audited(client, admin_session):
    admin = MasterAdmin(
        id=uuid.uuid4(),
        nome="Master Seguro",
        email="master@example.com",
        senha_hash=get_password_hash("MasterSeguro2026"),
        ativo=True,
    )
    admin_session.add(admin)
    await admin_session.commit()

    login = await client.post(
        "/master/auth/login",
        json={"email": "MASTER@example.com", "password": "MasterSeguro2026"},
    )
    assert login.status_code == 200
    assert "master_access_token" in client.cookies

    create = await client.post(
        "/master/tenants",
        json={
            "nome": "Clinica Nova",
            "tipo": "clinica",
            "whatsapp_numero": "5511999999999",
            "admin_nome": "Dono da Clinica",
            "admin_email": "DONO@EXAMPLE.COM",
            "admin_password": "SenhaInicial2026",
            "plano": "pro",
            "mensalidade": 497,
        },
    )
    assert create.status_code == 201
    body = create.json()
    assert "admin_password" not in body
    tenant_id = body["id"]

    reset = await client.post(
        f"/master/tenants/{tenant_id}/reset-password",
        json={"new_password": "SenhaRenovada2026"},
    )
    assert reset.status_code == 200
    assert "new_password" not in reset.json()

    await admin_session.execute(text("SET LOCAL app.bypass_rls = 'true'"))
    user = (await admin_session.execute(
        select(Usuario).where(Usuario.email == "dono@example.com")
    )).scalar_one()
    assert user.token_version == 1

    audit_actions = (await admin_session.execute(
        select(MasterAuditLog.acao).order_by(MasterAuditLog.criado_em)
    )).scalars().all()
    assert "LOGIN" in audit_actions
    assert "CREATE" in audit_actions
    assert "RESET_PASSWORD" in audit_actions


@pytest.mark.asyncio
async def test_master_rejects_weak_initial_password(client, admin_session):
    admin = MasterAdmin(
        id=uuid.uuid4(),
        nome="Master Seguro",
        email="master2@example.com",
        senha_hash=get_password_hash("MasterSeguro2026"),
        ativo=True,
    )
    admin_session.add(admin)
    await admin_session.commit()
    await client.post("/master/auth/login", json={"email": admin.email, "password": "MasterSeguro2026"})

    response = await client.post(
        "/master/tenants",
        json={
            "nome": "Clinica Insegura",
            "whatsapp_numero": "5511999999999",
            "admin_email": "owner-weak@example.com",
            "admin_password": "master123",
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_master_creates_asaas_subscription_without_storing_tax_id(client, admin_session, monkeypatch):
    admin = MasterAdmin(
        id=uuid.uuid4(), nome="Master Billing", email="billing@example.com",
        senha_hash=get_password_hash("MasterSeguro2026"), ativo=True,
    )
    admin_session.add(admin)
    await admin_session.commit()
    await client.post("/master/auth/login", json={"email": admin.email, "password": "MasterSeguro2026"})
    created = await client.post("/master/tenants", json={
        "nome": "Clinica Billing",
        "whatsapp_numero": "5511999999999",
        "admin_email": "dono-billing@example.com",
        "admin_password": "SenhaInicial2026",
        "mensalidade": 497,
    })
    tenant_id = created.json()["id"]
    captured = {}

    async def fake_customer(**kwargs):
        captured["customer"] = kwargs
        return {"id": "cus_test_secure"}

    async def fake_subscription(**kwargs):
        captured["subscription"] = kwargs
        return {"id": "sub_test_secure"}

    monkeypatch.setattr("app.services.asaas_service.create_customer", fake_customer)
    monkeypatch.setattr("app.services.asaas_service.create_subscription", fake_subscription)
    response = await client.post(f"/master/tenants/{tenant_id}/billing/subscription", json={
        "cpf_cnpj": "123.456.789-01",
        "next_due_date": "2026-08-10",
        "billing_type": "PIX",
        "cycle": "MONTHLY",
    })
    assert response.status_code == 201
    assert response.json()["subscription_id"] == "sub_test_secure"
    assert captured["customer"]["cpf_cnpj"] == "12345678901"
    assert captured["subscription"]["tenant_id"] == tenant_id

    await admin_session.execute(text("SET LOCAL app.bypass_rls = 'true'"))
    tenant = await admin_session.get(Tenant, uuid.UUID(tenant_id))
    assert tenant.asaas_customer_id == "cus_test_secure"
    assert tenant.asaas_subscription_id == "sub_test_secure"
    audit_details = (await admin_session.execute(select(MasterAuditLog.detalhes))).scalars().all()
    assert all("12345678901" not in (details or "") for details in audit_details)

    duplicate = await client.post(f"/master/tenants/{tenant_id}/billing/subscription", json={
        "cpf_cnpj": "12345678901", "next_due_date": "2026-08-10"
    })
    assert duplicate.status_code == 409
