import asyncio
import uuid
from datetime import datetime, date, timedelta, timezone
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

# Import models
from app.models.models import (
    Tenant, Usuario, ClientePaciente, ServicoProduto, Preco,
    AtendimentoPedido, ItemAtendimento, ListaEspera, LogMensagem,
    Aprovacao, LogAuditoria
)

async def seed():
    superuser_url = "postgresql+asyncpg://postgres:postgres@localhost:5432/projeto_saas"
    engine = create_async_engine(superuser_url)
    Session = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    tenant_id = uuid.UUID("d290f1ee-6c54-4b01-90e6-d701748f0851")

    async with Session() as session:
        try:
            # 1. Clean up existing test data (except the tenant and user we already created)
            print("Cleaning up old demo data...")
            await session.execute(text("DELETE FROM aprovacoes;"))
            await session.execute(text("DELETE FROM estados_conversa;"))
            await session.execute(text("DELETE FROM token_blacklist;"))
            await session.execute(text("DELETE FROM logs_mensagens;"))
            await session.execute(text("DELETE FROM lista_espera;"))
            await session.execute(text("DELETE FROM itens_atendimento;"))
            await session.execute(text("DELETE FROM atendimentos_pedidos;"))
            await session.execute(text("DELETE FROM precos;"))
            await session.execute(text("DELETE FROM servicos_produtos;"))
            await session.execute(text("DELETE FROM clientes_pacientes;"))
            await session.commit()

            print("Seeding new demo data...")

            # Ensure default Tenant exists
            from sqlalchemy import select
            res_tenant = await session.execute(select(Tenant).where(Tenant.id == tenant_id))
            tenant = res_tenant.scalar_one_or_none()
            if not tenant:
                print("Creating default tenant...")
                tenant = Tenant(
                    id=tenant_id,
                    nome="Clínica Demo",
                    tipo="clinica",
                    whatsapp_numero="5511990000000",
                    plano="starter",
                    sistema_ativo=True,
                    horario_abertura="08:00",
                    horario_fechamento="18:00",
                    limite_pedido_grande=10,
                    cor_primaria="#2563eb"
                )
                session.add(tenant)
                await session.flush()

            # Ensure default User exists
            from app.utils.security import get_password_hash
            res_user = await session.execute(select(Usuario).where(Usuario.email == "admin@demo.com"))
            user = res_user.scalar_one_or_none()
            if not user:
                print("Creating default user...")
                user = Usuario(
                    id=uuid.uuid4(),
                    tenant_id=tenant_id,
                    nome="Administrador",
                    email="admin@demo.com",
                    senha_hash=get_password_hash("admin123"),
                    perfil="dono"
                )
                session.add(user)
                await session.flush()

            # 2. Add services
            s1 = ServicoProduto(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                nome="Consulta Odontológica",
                categoria="Odontologia",
                duracao_minutos=60,
                ativo=True
            )
            s2 = ServicoProduto(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                nome="Limpeza Profilaxia",
                categoria="Odontologia",
                duracao_minutos=30,
                ativo=True
            )
            s3 = ServicoProduto(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                nome="Clareamento Dental",
                categoria="Estética",
                duracao_minutos=45,
                ativo=True
            )
            session.add_all([s1, s2, s3])
            await session.flush()

            # 3. Add prices
            p1 = Preco(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                servico_id=s1.id,
                qtd_min=1,
                qtd_max=1,
                preco_particular=250.00,
                preco_convenio=150.00,
                convenio="Amil"
            )
            p2 = Preco(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                servico_id=s2.id,
                qtd_min=1,
                qtd_max=1,
                preco_particular=150.00,
                preco_convenio=100.00,
                convenio="Unimed"
            )
            p3 = Preco(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                servico_id=s3.id,
                qtd_min=1,
                qtd_max=1,
                preco_particular=600.00,
                preco_convenio=450.00,
                convenio="Bradesco"
            )
            session.add_all([p1, p2, p3])
            await session.flush()

            # 4. Add clients
            c1 = ClientePaciente(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                nome="Alice Silva",
                whatsapp="5511990000001",
                data_nascimento=date(1990, 5, 12),
                convenio="Amil",
                total_atendimentos=3,
                ticket_medio=150.00,
                status_reativacao="ativo"
            )
            c2 = ClientePaciente(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                nome="Bruno Costa",
                whatsapp="5511990000002",
                data_nascimento=date(1985, 10, 22),
                convenio="Unimed",
                total_atendimentos=1,
                ticket_medio=100.00,
                status_reativacao="inativo_3m"
            )
            c3 = ClientePaciente(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                nome="Carla Souza",
                whatsapp="5511990000003",
                data_nascimento=date(1993, 2, 8),
                convenio="Bradesco",
                total_atendimentos=5,
                ticket_medio=450.00,
                status_reativacao="inativo_6m"
            )
            c4 = ClientePaciente(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                nome="Daniel Oliveira",
                whatsapp="5511990000004",
                data_nascimento=date(1978, 7, 15),
                convenio=None,
                total_atendimentos=0,
                ticket_medio=0.00,
                status_reativacao="inativo_12m"
            )
            c5 = ClientePaciente(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                nome="Eliane Santos",
                whatsapp="5511990000005",
                data_nascimento=date(2001, 12, 30),
                convenio="SulAmerica",
                total_atendimentos=2,
                ticket_medio=200.00,
                status_reativacao="reativado"
            )
            session.add_all([c1, c2, c3, c4, c5])
            await session.flush()

            # 5. Add appointments (AtendimentoPedido)
            now = datetime.now(timezone.utc)
            
            # Appt 1: Alice (Today)
            ap1 = AtendimentoPedido(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                cliente_id=c1.id,
                data_agendamento=now.replace(hour=9, minute=0, second=0),
                status="confirmado",
                confirmado=True,
                total=150.00,
                pago=False,
                origem="whatsapp"
            )
            
            # Appt 2: Bruno (Today)
            ap2 = AtendimentoPedido(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                cliente_id=c2.id,
                data_agendamento=now.replace(hour=10, minute=30, second=0),
                status="aguardando",
                confirmado=False,
                total=100.00,
                pago=False,
                origem="whatsapp"
            )

            # Appt 3: Carla (Yesterday, completed)
            ap3 = AtendimentoPedido(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                cliente_id=c3.id,
                data_agendamento=now - timedelta(days=1),
                data_atendimento=now - timedelta(days=1),
                status="realizado",
                confirmado=True,
                compareceu=True,
                total=450.00,
                pago=True,
                origem="dashboard"
            )

            # Appt 4: Daniel (Yesterday, missed)
            ap4 = AtendimentoPedido(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                cliente_id=c4.id,
                data_agendamento=now - timedelta(days=1),
                status="falta",
                confirmado=True,
                compareceu=False,
                total=250.00,
                pago=False,
                origem="whatsapp"
            )

            # Appt 5: Eliane (Tomorrow)
            ap5 = AtendimentoPedido(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                cliente_id=c5.id,
                data_agendamento=now + timedelta(days=1),
                status="aguardando",
                confirmado=False,
                total=150.00,
                pago=False,
                origem="whatsapp"
            )
            
            session.add_all([ap1, ap2, ap3, ap4, ap5])
            await session.flush()

            # 6. Add items (ItemAtendimento)
            item1 = ItemAtendimento(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                atendimento_id=ap1.id,
                servico_id=s1.id,
                quantidade=1,
                preco_unitario=150.00
            )
            item2 = ItemAtendimento(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                atendimento_id=ap2.id,
                servico_id=s2.id,
                quantidade=1,
                preco_unitario=100.00
            )
            item3 = ItemAtendimento(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                atendimento_id=ap3.id,
                servico_id=s3.id,
                quantidade=1,
                preco_unitario=450.00
            )
            item4 = ItemAtendimento(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                atendimento_id=ap4.id,
                servico_id=s1.id,
                quantidade=1,
                preco_unitario=250.00
            )
            item5 = ItemAtendimento(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                atendimento_id=ap5.id,
                servico_id=s1.id,
                quantidade=1,
                preco_unitario=150.00
            )
            session.add_all([item1, item2, item3, item4, item5])

            # 7. Add waitlist (ListaEspera)
            w1 = ListaEspera(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                cliente_id=c2.id,
                servico_id=s3.id,
                data_preferida=now + timedelta(days=2),
                status="aguardando"
            )
            w2 = ListaEspera(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                cliente_id=c4.id,
                servico_id=s2.id,
                data_preferida=now + timedelta(days=3),
                status="aguardando"
            )
            session.add_all([w1, w2])

            # 8. Add approvals (Aprovacoes)
            al1 = Aprovacao(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                tipo="pedido_grande",
                atendimento_id=ap2.id,
                cliente_id=c2.id,
                detalhes="Quantidade de agendamentos acima do limite padrão do consultório (5 consultas ativas).",
                status="pendente"
            )
            al2 = Aprovacao(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                tipo="cliente_sumiu",
                atendimento_id=ap5.id,
                cliente_id=c5.id,
                detalhes="Cliente não respondeu à tentativa de confirmação nas últimas 1h30.",
                status="pendente"
            )
            session.add_all([al1, al2])

            # 9. Add message logs (LogMensagem)
            msg1 = LogMensagem(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                cliente_whatsapp=c1.whatsapp,
                direcao="entrada",
                mensagem="Olá, quero marcar uma consulta para hoje por favor",
                tipo="texto"
            )
            msg2 = LogMensagem(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                cliente_whatsapp=c1.whatsapp,
                direcao="saida",
                mensagem="Olá Alice! Temos vaga hoje às 09:00 com o Dr. Admin. Deseja confirmar?",
                tipo="texto"
            )
            msg3 = LogMensagem(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                cliente_whatsapp=c1.whatsapp,
                direcao="entrada",
                mensagem="Sim, por favor! Pode marcar.",
                tipo="texto"
            )
            session.add_all([msg1, msg2, msg3])

            await session.commit()
            print("Demo data seeded successfully!")

        except Exception as e:
            await session.rollback()
            print("Error during seeding:", e)

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(seed())
