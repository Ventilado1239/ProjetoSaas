import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

async def wipe():
    superuser_url = "postgresql+asyncpg://postgres:postgres@localhost:5432/projeto_saas"
    engine = create_async_engine(superuser_url)

    async with engine.begin() as conn:
        try:
            print("Wiping all mock data (keeping Tenant and Admin user)...")
            await conn.execute(text("DELETE FROM aprovacoes;"))
            await conn.execute(text("DELETE FROM estados_conversa;"))
            await conn.execute(text("DELETE FROM token_blacklist;"))
            await conn.execute(text("DELETE FROM configuracoes;"))
            await conn.execute(text("DELETE FROM logs_mensagens;"))
            await conn.execute(text("DELETE FROM lista_espera;"))
            await conn.execute(text("DELETE FROM itens_atendimento;"))
            await conn.execute(text("DELETE FROM atendimentos_pedidos;"))
            await conn.execute(text("DELETE FROM precos;"))
            await conn.execute(text("DELETE FROM servicos_produtos;"))
            await conn.execute(text("DELETE FROM clientes_pacientes;"))
            print("Database wiped successfully. Tenant & Admin user preserved.")
        except Exception as e:
            print("Error wiping database:", e)
            
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(wipe())
