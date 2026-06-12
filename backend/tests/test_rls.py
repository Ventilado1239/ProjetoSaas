import pytest
from sqlalchemy import select, text
from app.utils.security import get_password_hash
from app.models.models import Tenant, Usuario, ClientePaciente
import uuid

async def setup_tenants_and_clients(admin_session):
    # 1. Create Tenant A
    tenant_a = Tenant(
        id=uuid.uuid4(),
        nome="Clinica A",
        tipo="clinica",
        whatsapp_numero="5511911111111",
        plano="pro",
        sistema_ativo=True
    )
    admin_session.add(tenant_a)
    
    # 2. Create Tenant B
    tenant_b = Tenant(
        id=uuid.uuid4(),
        nome="Loja B",
        tipo="loja",
        whatsapp_numero="5511922222222",
        plano="starter",
        sistema_ativo=True
    )
    admin_session.add(tenant_b)
    await admin_session.flush()

    # 3. Create User for Tenant A
    user_a = Usuario(
        id=uuid.uuid4(),
        tenant_id=tenant_a.id,
        nome="User A",
        email="user_a@test.com",
        senha_hash=get_password_hash("password123"),
        perfil="dono"
    )
    admin_session.add(user_a)

    # 4. Create User for Tenant B
    user_b = Usuario(
        id=uuid.uuid4(),
        tenant_id=tenant_b.id,
        nome="User B",
        email="user_b@test.com",
        senha_hash=get_password_hash("password123"),
        perfil="dono"
    )
    admin_session.add(user_b)

    # 5. Create Client for Tenant A
    client_a = ClientePaciente(
        id=uuid.uuid4(),
        tenant_id=tenant_a.id,
        nome="Paciente de A",
        whatsapp="5511988888888",
        status_reativacao="ativo"
    )
    admin_session.add(client_a)

    # 6. Create Client for Tenant B
    client_b = ClientePaciente(
        id=uuid.uuid4(),
        tenant_id=tenant_b.id,
        nome="Cliente de B",
        whatsapp="5511977777777",
        status_reativacao="ativo"
    )
    admin_session.add(client_b)
    
    await admin_session.commit()
    return tenant_a, tenant_b, user_a, user_b, client_a, client_b

@pytest.mark.asyncio
async def test_database_level_rls_isolation(admin_session, db_session):
    tenant_a, tenant_b, user_a, user_b, client_a, client_b = await setup_tenants_and_clients(admin_session)
    
    # 1. Enable isolation by setting tenant context to Tenant A on the app session (db_session)
    await db_session.execute(text("SELECT set_tenant_id(:tenant_id)"), {"tenant_id": tenant_a.id})
    
    # Query clients using app session (which connects as non-superuser saas_app_user)
    result = await db_session.execute(select(ClientePaciente))
    clients = result.scalars().all()
    
    # We should only see Client A
    assert len(clients) == 1
    assert clients[0].id == client_a.id
    assert clients[0].tenant_id == tenant_a.id
    
    # 2. Enable isolation by setting tenant context to Tenant B
    await db_session.execute(text("SELECT set_tenant_id(:tenant_id)"), {"tenant_id": tenant_b.id})
    
    result = await db_session.execute(select(ClientePaciente))
    clients = result.scalars().all()
    
    # We should only see Client B
    assert len(clients) == 1
    assert clients[0].id == client_b.id
    assert clients[0].tenant_id == tenant_b.id

@pytest.mark.asyncio
async def test_database_level_rls_null_context(admin_session, db_session):
    tenant_a, tenant_b, user_a, user_b, client_a, client_b = await setup_tenants_and_clients(admin_session)
    
    # Set context to NULL (unauthenticated state)
    await db_session.execute(text("SELECT set_tenant_id(NULL)"))
    
    # Query clients using app session
    result = await db_session.execute(select(ClientePaciente))
    clients = result.scalars().all()
    
    # RLS should block all rows, returning zero rows
    assert len(clients) == 0

@pytest.mark.asyncio
async def test_api_middleware_rls_isolation(client, admin_session):
    tenant_a, tenant_b, user_a, user_b, client_a, client_b = await setup_tenants_and_clients(admin_session)
    
    # To test API endpoints, we need a route that accesses the database.
    # We register a temporary test route on the FastAPI app context for RLS verification.
    from app.main import app
    from app.dependencies import get_current_user
    from fastapi import Depends
    from sqlalchemy.ext.asyncio import AsyncSession
    from app.database import get_db

    # Use a flag to avoid registering the route twice if tests are re-run
    if not hasattr(app, "_test_route_registered"):
        @app.get("/test/clients")
        async def get_test_clients(current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(ClientePaciente))
            return result.scalars().all()
        app._test_route_registered = True

    # 1. Login as User A
    login_response = await client.post("/auth/login", json={"email": "user_a@test.com", "password": "password123"})
    assert login_response.status_code == 200
    
    # Request clients
    response = await client.get("/test/clients")
    assert response.status_code == 200
    clients_data = response.json()
    
    # Assert only Client A is returned
    assert len(clients_data) == 1
    assert clients_data[0]["nome"] == "Paciente de A"
    
    # 2. Login as User B
    client.cookies.clear()
    login_response = await client.post("/auth/login", json={"email": "user_b@test.com", "password": "password123"})
    assert login_response.status_code == 200
    
    # Request clients
    response = await client.get("/test/clients")
    assert response.status_code == 200
    clients_data = response.json()
    
    # Assert only Client B is returned
    assert len(clients_data) == 1
    assert clients_data[0]["nome"] == "Cliente de B"
