import asyncio
import os
import uuid

from sqlalchemy import select, text

from app.database import AsyncSessionLocal
from app.models.models import MasterAdmin
from app.utils.security import get_password_hash, validate_password_strength


async def seed_master():
    email = os.getenv("MASTER_ADMIN_EMAIL", "").strip().lower()
    password = os.getenv("MASTER_ADMIN_PASSWORD", "")
    if not email or not password:
        raise RuntimeError("Defina MASTER_ADMIN_EMAIL e MASTER_ADMIN_PASSWORD antes de executar.")
    validate_password_strength(password)

    async with AsyncSessionLocal() as db:
        await db.execute(text("SET LOCAL app.bypass_rls = 'true'"))
        admin = (await db.execute(
            select(MasterAdmin).where(MasterAdmin.email == email)
        )).scalar_one_or_none()

        if not admin:
            admin = MasterAdmin(
                id=uuid.uuid4(),
                nome="Master Admin",
                email=email,
                senha_hash=get_password_hash(password),
                ativo=True,
            )
            db.add(admin)
        else:
            admin.nome = "Master Admin"
            admin.senha_hash = get_password_hash(password)
            admin.ativo = True

        await db.commit()

    print("Master admin pronto.")
    print(f"Email: {email}")
    print("Senha definida pela variavel MASTER_ADMIN_PASSWORD (nao exibida).")


if __name__ == "__main__":
    asyncio.run(seed_master())
