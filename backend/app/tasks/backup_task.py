import logging
import os
import uuid
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.models import Tenant, LogMensagem
from app.services.backup_service import gerar_backup_csv
from app.services.whatsapp_service import enviar_mensagem

logger = logging.getLogger(__name__)

SP_TZ = ZoneInfo("America/Sao_Paulo")
DEFAULT_OWNER_PHONE = "5511999999999"
BACKUP_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "backups")


async def processar_backups(db: Optional[AsyncSession] = None):
    """
    Scheduled task that runs daily at 23:00.
    Generates CSV backups for each active tenant and stores them locally.
    """
    logger.info("Iniciando backup diário...")
    if db is None:
        async with AsyncSessionLocal() as session:
            try:
                await _run_backups(session)
                await session.commit()
            except Exception as e:
                logger.exception(f"Erro ao processar backups: {e}")
                await session.rollback()
    else:
        await _run_backups(db)


async def _run_backups(db: AsyncSession):
    now_sp = datetime.now(SP_TZ)
    date_str = now_sp.strftime("%Y-%m-%d")

    # Fetch all active tenants (bypass RLS)
    await db.execute(text("SET LOCAL app.bypass_rls = 'true'"))
    res_tenants = await db.execute(select(Tenant).where(Tenant.sistema_ativo == True))
    tenants = res_tenants.scalars().all()
    await db.execute(text("SET LOCAL app.bypass_rls = 'false'"))

    total_success = 0
    total_fail = 0

    for tenant in tenants:
        try:
            await db.execute(
                text("SELECT set_tenant_id(:tenant_id)"),
                {"tenant_id": tenant.id}
            )

            backups = await gerar_backup_csv(db, tenant)

            # Create backup directory structure
            tenant_dir = os.path.join(BACKUP_DIR, str(tenant.id), date_str)
            os.makedirs(tenant_dir, exist_ok=True)

            for filename, content in backups.items():
                filepath = os.path.join(tenant_dir, filename)
                with open(filepath, "wb") as f:
                    f.write(content)

            total_bytes = sum(len(v) for v in backups.values())
            total_files = len(backups)

            # Notify owner
            msg = (
                f"✅ *BACKUP DIÁRIO — {date_str}*\n\n"
                f"📦 {total_files} arquivos gerados\n"
                f"📊 {total_bytes:,} bytes totais\n"
                f"🔒 Armazenamento local seguro"
            )
            await enviar_mensagem(str(tenant.id), DEFAULT_OWNER_PHONE, msg)

            log = LogMensagem(
                id=uuid.uuid4(),
                tenant_id=tenant.id,
                cliente_whatsapp=DEFAULT_OWNER_PHONE,
                direcao="saida",
                mensagem=msg,
                tipo="texto"
            )
            db.add(log)
            await db.flush()

            total_success += 1
            logger.info(f"Backup concluído para {tenant.nome}: {total_files} arquivos.")

        except Exception as e:
            logger.exception(f"Erro ao gerar backup para tenant {tenant.nome}: {e}")
            total_fail += 1

    logger.info(f"Backup diário concluído: {total_success} sucesso(s), {total_fail} falha(s).")
