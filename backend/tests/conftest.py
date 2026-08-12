from typing import AsyncGenerator
import os
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import text, NullPool
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.config import settings
from sqlalchemy.engine import make_url

# Superuser engine (bypasses RLS, used for database seeding and cleanup)
superuser_url = os.getenv("TEST_SUPERUSER_DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/projeto_saas_test")
for candidate_url in (superuser_url, settings.DATABASE_URL):
    database_name = make_url(candidate_url).database or ""
    if not database_name.endswith("_test") and os.getenv("ALLOW_UNSAFE_TEST_DATABASE") != "1":
        raise RuntimeError(
            f"Testes destrutivos recusados no banco '{database_name}'. Use um banco cujo nome termine em _test."
        )
superuser_engine = create_async_engine(superuser_url, poolclass=NullPool)

# Application/Test engine (connects as non-superuser, RLS is active)
app_engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)

# Session makers
SuperuserSession = async_sessionmaker(bind=superuser_engine, class_=AsyncSession, expire_on_commit=False)
AppSession = async_sessionmaker(bind=app_engine, class_=AsyncSession, expire_on_commit=False)

# Monkeypatch AsyncSessionLocal globally to prevent event loop mismatch in async tests
import app.database
app.database.AsyncSessionLocal = AppSession

from app.database import Base, get_db
from app.main import app

@pytest.fixture
async def admin_session() -> AsyncGenerator[AsyncSession, None]:
    """Provides a superuser session to seed data and runs cleanup afterwards."""
    async with SuperuserSession() as session:
        try:
            # Debug: check if database contains any emails
            res = await session.execute(text("SELECT email FROM usuarios;"))
            emails = res.scalars().all()
            print("\nDEBUG - Emails in DB before test:", emails)
            yield session
        finally:
            await session.rollback()
            # Cleanup all tables after the test runs
            try:
                # Use DELETE statements instead of TRUNCATE to avoid requiring exclusive table locks
                await session.execute(text("DELETE FROM aprovacoes;"))
                await session.execute(text("DELETE FROM estados_conversa;"))
                await session.execute(text("DELETE FROM token_blacklist;"))
                await session.execute(text("DELETE FROM webhook_events;"))
                await session.execute(text("DELETE FROM master_audit_logs;"))
                await session.execute(text("DELETE FROM master_leads;"))
                await session.execute(text("DELETE FROM master_admins;"))
                await session.execute(text("DELETE FROM configuracoes;"))
                await session.execute(text("DELETE FROM logs_mensagens;"))
                await session.execute(text("DELETE FROM lista_espera;"))
                await session.execute(text("DELETE FROM itens_atendimento;"))
                await session.execute(text("DELETE FROM atendimentos_pedidos;"))
                await session.execute(text("DELETE FROM precos;"))
                await session.execute(text("DELETE FROM servicos_produtos;"))
                await session.execute(text("DELETE FROM clientes_pacientes;"))
                await session.execute(text("DELETE FROM usuarios;"))
                await session.execute(text("DELETE FROM tenants;"))
                await session.commit()
            except Exception:
                await session.rollback()

@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provides a non-superuser session representing the app's database connection (subject to RLS)."""
    async with AppSession() as session:
        yield session

@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Provides an AsyncClient for FastAPI request simulation, overriding get_db dependency."""
    from fastapi import Request
    
    async def _get_test_db(request: Request = None):
        if request is not None and hasattr(request.state, "db"):
            yield request.state.db
        else:
            yield db_session

    app.dependency_overrides[get_db] = _get_test_db
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as async_client:
        yield async_client
        
    app.dependency_overrides.clear()
