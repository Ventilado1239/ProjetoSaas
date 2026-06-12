import pytest
from app.utils.security import get_password_hash
from app.models.models import Tenant, Usuario
import uuid

async def create_test_user(admin_session, email, password, perfil="dono", tenant_name="Tenant Test"):
    tenant = Tenant(
        id=uuid.uuid4(),
        nome=tenant_name,
        tipo="loja",
        whatsapp_numero="5511999999999",
        plano="starter",
        sistema_ativo=True,
        horario_abertura="08:00",
        horario_fechamento="18:00",
        limite_pedido_grande=10,
        cor_primaria="#2563eb"
    )
    admin_session.add(tenant)
    await admin_session.flush() # Populate tenant.id
    
    user = Usuario(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        nome="Admin User",
        email=email,
        senha_hash=get_password_hash(password),
        perfil=perfil
    )
    admin_session.add(user)
    await admin_session.commit()
    return tenant, user

@pytest.mark.asyncio
async def test_login_success(client, admin_session):
    # Setup test user
    email = "test@example.com"
    password = "secretpassword"
    tenant, user = await create_test_user(admin_session, email, password)

    # Perform login request
    response = await client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    
    data = response.json()
    assert "user" in data
    assert data["user"]["email"] == email
    assert data["user"]["perfil"] == "dono"
    
    # Assert cookies are set
    cookies = client.cookies
    assert "access_token" in cookies
    assert "refresh_token" in cookies

@pytest.mark.asyncio
async def test_login_invalid_password(client, admin_session):
    email = "test@example.com"
    password = "secretpassword"
    await create_test_user(admin_session, email, password)

    # Try invalid password
    response = await client.post("/auth/login", json={"email": email, "password": "wrongpassword"})
    assert response.status_code == 401
    assert "access_token" not in client.cookies

@pytest.mark.asyncio
async def test_refresh_token_rotation(client, admin_session):
    email = "test@example.com"
    password = "secretpassword"
    await create_test_user(admin_session, email, password)

    # Login to get cookies
    login_response = await client.post("/auth/login", json={"email": email, "password": password})
    assert login_response.status_code == 200
    
    first_refresh_token = client.cookies.get("refresh_token")
    assert first_refresh_token is not None

    # Perform refresh
    refresh_response = await client.post("/auth/refresh")
    assert refresh_response.status_code == 200
    
    second_refresh_token = client.cookies.get("refresh_token")
    assert second_refresh_token != first_refresh_token  # Assert rotation

    # Re-use first refresh token (should fail)
    # We manually clear cookies and set the old one back
    client.cookies.clear()
    client.cookies.set("refresh_token", first_refresh_token)
    
    fail_response = await client.post("/auth/refresh")
    assert fail_response.status_code == 401

@pytest.mark.asyncio
async def test_logout(client, admin_session):
    email = "test@example.com"
    password = "secretpassword"
    await create_test_user(admin_session, email, password)

    # Login
    await client.post("/auth/login", json={"email": email, "password": password})
    assert "refresh_token" in client.cookies

    # Logout
    logout_response = await client.post("/auth/logout")
    assert logout_response.status_code == 200
    
    assert "access_token" not in client.cookies
    assert "refresh_token" not in client.cookies
