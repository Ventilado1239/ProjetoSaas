from typing import Optional
from fastapi import Request
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.config import settings

class Base(DeclarativeBase):
    pass

# Configure connection args, enforcing SSL for non-local database connections
connect_args = {}
if "localhost" not in settings.DATABASE_URL and "127.0.0.1" not in settings.DATABASE_URL:
    # Require SSL for production (e.g. Supabase connection)
    connect_args["ssl"] = "require"

# Create async engine with a connection pool
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
    connect_args=connect_args
)

# Async session maker
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# FastAPI dependency to obtain a db session
async def get_db(request: Request = None):
    # If session is initialized and bound to request state by TenantMiddleware, reuse it
    if request is not None and hasattr(request.state, "db"):
        yield request.state.db
    else:
        # Fallback for standalone scripts, tasks, and tests where middleware is bypassed
        async with AsyncSessionLocal() as session:
            try:
                yield session
            finally:
                await session.close()

