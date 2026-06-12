import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import select, delete, text
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.models import ClientePaciente, AtendimentoPedido, LogAuditoria, LogMensagem, Tenant, Usuario
from app.middleware.security import SecurityAndRateLimitMiddleware
from app.main import app

def reset_rate_limiter():
    """Helper to locate SecurityAndRateLimitMiddleware and clear its rate limit memory."""
    current_app = getattr(app, "middleware_stack", None)
    while current_app:
        if isinstance(current_app, SecurityAndRateLimitMiddleware):
            current_app.ip_limits.clear()
            current_app.tenant_limits.clear()
            return
        current_app = getattr(current_app, "app", None)

@pytest.mark.anyio
async def test_security_headers(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    
    # Assert headers are present and correct
    headers = response.headers
    assert headers.get("strict-transport-security") == "max-age=63072000; includeSubDomains; preload"
    assert headers.get("x-content-type-options") == "nosniff"
    assert headers.get("x-frame-options") == "DENY"
    assert headers.get("content-security-policy") == "default-src 'self'; frame-ancestors 'none';"

@pytest.mark.anyio
async def test_rate_limiting_ip(client: AsyncClient):
    reset_rate_limiter()
    
    # Send 100 requests (which is the limit for IP)
    for _ in range(100):
        response = await client.get("/health")
        assert response.status_code == 200
        
    # The 101st request should trigger 429 Too Many Requests
    response = await client.get("/health")
    assert response.status_code == 429
    assert "Rate limit exceeded" in response.json()["detail"]
    
    # Cleanup rate limit dict
    reset_rate_limiter()

@pytest.mark.anyio
async def test_no_clinical_data_in_database():
    """Verify that no database table has fields related to clinical data/diagnostics."""
    from sqlalchemy.inspection import inspect
    
    tables_to_check = [ClientePaciente, AtendimentoPedido, LogMensagem]
    forbidden_keywords = {"prontuario", "diagnostico", "clinico", "doenca", "medicamento", "sintoma", "tratamento"}
    
    for table in tables_to_check:
        mapper = inspect(table)
        for column in mapper.attrs:
            col_name = column.key.lower()
            for kw in forbidden_keywords:
                assert kw not in col_name, f"Forbidden clinical keyword '{kw}' found in table '{table.__tablename__}' column '{col_name}'"

@pytest.mark.anyio
async def test_audit_logging_and_lgpd_erasure(client: AsyncClient, admin_session: AsyncSession):
    # 1. Seed a Tenant and User
    tenant_id = uuid.uuid4()
    tenant = Tenant(
        id=tenant_id,
        nome="Clinica Teste LGPD",
        tipo="clinica",
        whatsapp_numero="5511999999999",
        plano="pro",
        sistema_ativo=True
    )
    
    user_id = uuid.uuid4()
    user = Usuario(
        id=user_id,
        tenant_id=tenant_id,
        nome="Dr. Teste LGPD",
        email="medico_lgpd@teste.com",
        senha_hash="dummy_hash",
        perfil="dono"
    )
    admin_session.add(tenant)
    admin_session.add(user)
    await admin_session.commit()
    
    # Generate Bearer Token for this user
    from app.utils.security import create_access_token
    token = create_access_token({"sub": str(user_id), "tenant_id": str(tenant_id)})
    headers = {"Authorization": f"Bearer {token}"}
    
    # 2. CREATE CLIENT (INSERT AUDIT)
    client_data = {
        "nome": "Paciente Seguro",
        "whatsapp": "5511988888888",
        "data_nascimento": "1990-01-01",
        "convenio": "Amil"
    }
    
    response = await client.post("/clientes", json=client_data, headers=headers)
    assert response.status_code == 201
    created_client = response.json()
    client_uuid = uuid.UUID(created_client["id"])
    
    # Verify client is encrypted in the DB by checking via admin_session (bypasses pgpTypeDecorator compiling decrypt)
    res = await admin_session.execute(text("SELECT nome, convenio FROM clientes_pacientes WHERE id = :id"), {"id": client_uuid})
    raw_row = res.first()
    assert raw_row is not None
    # Raw values in DB should be bytes (encrypted binary payload) since column type is BYTEA
    assert isinstance(raw_row[0], bytes)
    assert isinstance(raw_row[1], bytes)
    
    # Verify INSERT Audit log exists
    res = await admin_session.execute(
        select(LogAuditoria).where(LogAuditoria.tenant_id == tenant_id, LogAuditoria.acao == "INSERT")
    )
    insert_log = res.scalar_one_or_none()
    assert insert_log is not None
    assert insert_log.tabela == "clientes_pacientes"
    assert insert_log.usuario_email == "medico_lgpd@teste.com"
    
    # 3. UPDATE CLIENT (UPDATE AUDIT)
    update_data = {
        "nome": "Paciente Seguro Editado",
        "whatsapp": "5511988888888",
        "data_nascimento": "1990-01-01",
        "convenio": "Unimed"
    }
    response = await client.put(f"/clientes/{client_uuid}", json=update_data, headers=headers)
    assert response.status_code == 200
    
    # Verify UPDATE Audit log exists and registers changes
    res = await admin_session.execute(
        select(LogAuditoria).where(LogAuditoria.tenant_id == tenant_id, LogAuditoria.acao == "UPDATE")
    )
    update_log = res.scalar_one_or_none()
    assert update_log is not None
    assert "Unimed" in update_log.valores_novos
    assert "Amil" in update_log.valores_antigos
    
    # Add dummy message logs for this patient's whatsapp
    msg_log = LogMensagem(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        cliente_whatsapp="5511988888888",
        direcao="entrada",
        mensagem="Minha consulta de amanhã",
        tipo="texto"
    )
    admin_session.add(msg_log)
    await admin_session.commit()
    
    # 4. DELETE LGPD (LGPD_DELETE AUDIT WITH ANONYMIZATION)
    response = await client.delete(f"/clientes/{client_uuid}/lgpd", headers=headers)
    assert response.status_code == 204
    
    # Verify client is deleted from DB
    res = await admin_session.execute(text("SELECT id FROM clientes_pacientes WHERE id = :id"), {"id": client_uuid})
    assert res.first() is None
    
    # Verify message logs are cleared
    res = await admin_session.execute(
        select(LogMensagem).where(LogMensagem.cliente_whatsapp == "5511988888888")
    )
    assert res.scalars().all() == []
    
    # Verify LGPD_DELETE audit exists and is anonymized (no PII in valores_antigos)
    res = await admin_session.execute(
        select(LogAuditoria).where(LogAuditoria.tenant_id == tenant_id, LogAuditoria.acao == "LGPD_DELETE")
    )
    delete_log = res.scalar_one_or_none()
    assert delete_log is not None
    assert "Paciente Seguro" not in delete_log.valores_antigos
    assert "Direito ao esquecimento" in delete_log.valores_antigos or "direito ao esquecimento" in delete_log.valores_antigos

@pytest.mark.anyio
async def test_audit_logs_tenant_isolation(client: AsyncClient, admin_session: AsyncSession, db_session: AsyncSession):
    # Seed Tenant A and User A
    tenant_a_id = uuid.uuid4()
    tenant_a = Tenant(id=tenant_a_id, nome="Tenant A", tipo="clinica", whatsapp_numero="5511900000000", plano="starter")
    user_a_id = uuid.uuid4()
    user_a = Usuario(id=user_a_id, tenant_id=tenant_a_id, nome="User A", email="usera@tenant.com", senha_hash="pw", perfil="dono")
    
    # Seed Tenant B and User B
    tenant_b_id = uuid.uuid4()
    tenant_b = Tenant(id=tenant_b_id, nome="Tenant B", tipo="clinica", whatsapp_numero="5511911111111", plano="starter")
    user_b_id = uuid.uuid4()
    user_b = Usuario(id=user_b_id, tenant_id=tenant_b_id, nome="User B", email="userb@tenant.com", senha_hash="pw", perfil="dono")
    
    # Seed an Audit Log for Tenant B
    audit_b = LogAuditoria(
        id=uuid.uuid4(),
        tenant_id=tenant_b_id,
        usuario_id=user_b_id,
        usuario_email="userb@tenant.com",
        acao="UPDATE",
        tabela="atendimentos_pedidos",
        registro_id=uuid.uuid4(),
        valores_antigos='{"status": "aguardando"}',
        valores_novos='{"status": "confirmado"}'
    )
    
    admin_session.add(tenant_a)
    admin_session.add(user_a)
    admin_session.add(tenant_b)
    admin_session.add(user_b)
    await admin_session.flush()
    
    admin_session.add(audit_b)
    await admin_session.commit()
    
    # Log in as Tenant A
    from app.utils.security import create_access_token
    token_a = create_access_token({"sub": str(user_a_id), "tenant_id": str(tenant_a_id)})
    headers_a = {"Authorization": f"Bearer {token_a}"}
    
    # Access the DB as Tenant A using a query that would yield all audit logs if RLS was disabled
    # Set tenant A context
    await db_session.execute(text("SELECT set_tenant_id(:tenant_id)"), {"tenant_id": tenant_a_id})
    
    # Select all audit logs
    result = await db_session.execute(select(LogAuditoria))
    logs = result.scalars().all()
    
    # Verify that Tenant A cannot see the audit logs of Tenant B
    for log in logs:
        assert log.tenant_id == tenant_a_id
        assert log.tenant_id != tenant_b_id
