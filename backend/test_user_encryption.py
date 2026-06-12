import asyncio
from sqlalchemy import text
from app.database import engine

async def check():
    async with engine.begin() as conn:
        try:
            result = await conn.execute(text("SELECT pgp_sym_encrypt('hello_world', 'secret_key');"))
            val = result.scalar()
            print("saas_app_user can encrypt! Value:", val)
            
            result_dec = await conn.execute(text("SELECT pgp_sym_decrypt(:val, 'secret_key');"), {"val": val})
            val_dec = result_dec.scalar()
            print("saas_app_user can decrypt! Value:", val_dec)
        except Exception as e:
            print("saas_app_user encryption error:", e)

if __name__ == "__main__":
    asyncio.run(check())
