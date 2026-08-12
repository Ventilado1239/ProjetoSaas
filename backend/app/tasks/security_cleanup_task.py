import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, text

from app.database import AsyncSessionLocal
from app.models.models import TokenBlacklist, WebhookEvent

logger = logging.getLogger(__name__)


async def cleanup_security_records() -> None:
    """Remove expired revocations and old webhook deduplication identifiers."""
    async with AsyncSessionLocal() as db:
        try:
            await db.execute(text("SET LOCAL app.bypass_rls = 'true'"))
            now = datetime.now(timezone.utc)
            await db.execute(delete(TokenBlacklist).where(TokenBlacklist.expira_em < now))
            await db.execute(delete(WebhookEvent).where(WebhookEvent.recebido_em < now - timedelta(days=90)))
            await db.commit()
        except Exception:
            await db.rollback()
            logger.exception("Falha ao limpar registros de seguranca expirados")
