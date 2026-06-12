import logging
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.models import Tenant
from app.services.horario_service import is_within_opening_window, retomar_conversas_abertura

logger = logging.getLogger(__name__)

SP_TZ = ZoneInfo("America/Sao_Paulo")


async def processar_retomadas(db: Optional[AsyncSession] = None):
    """
    Scheduled task that runs every 5 minutes.
    Detects tenants that just opened and resumes overnight conversations.
    """
    logger.info("Verificando tenants que acabaram de abrir para retomada de conversas...")
    if db is None:
        async with AsyncSessionLocal() as session:
            try:
                await _run_retomadas(session)
                await session.commit()
            except Exception as e:
                logger.exception(f"Erro ao processar retomadas: {e}")
                await session.rollback()
    else:
        await _run_retomadas(db)


async def _run_retomadas(db: AsyncSession):
    now_sp = datetime.now(SP_TZ)

    # Fetch all active tenants (bypass RLS)
    await db.execute(text("SET LOCAL app.bypass_rls = 'true'"))
    res_tenants = await db.execute(select(Tenant).where(Tenant.sistema_ativo == True))
    tenants = res_tenants.scalars().all()
    await db.execute(text("SET LOCAL app.bypass_rls = 'false'"))

    for tenant in tenants:
        # Check if this tenant just opened (within 5 minutes of opening time)
        if not is_within_opening_window(tenant, now_sp, window_minutes=5):
            continue

        logger.info(f"Tenant {tenant.nome} acabou de abrir. Iniciando retomada de conversas...")

        # Set RLS context
        await db.execute(text("SELECT set_tenant_id(:tenant_id)"), {"tenant_id": tenant.id})

        await retomar_conversas_abertura(db, tenant)

    logger.info("Processamento de retomadas concluído.")
