"""
Tests for Phase 4 — Support Automations
Tests: lembrete_task, pos_atendimento, horario_service/retomada_task,
       pdf_service, abandono_task, backup_service
"""
import pytest
import uuid
import json
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, text

from app.models.models import (
    Tenant, ClientePaciente, ServicoProduto, Preco,
    AtendimentoPedido, ItemAtendimento, EstadoConversa, LogMensagem
)
from app.services.whatsapp_service import SENT_MESSAGES, clear_sent_messages
from app.tasks.lembrete_task import processar_lembretes_diarios
from app.services.pos_atendimento_service import enviar_agradecimento_pos_atendimento
from app.services.horario_service import registrar_mensagem_noturna, retomar_conversas_abertura
from app.tasks.retomada_task import processar_retomadas
from app.tasks.abandono_task import processar_abandonos
from app.services.pdf_service import gerar_pdf_fechamento_diario, gerar_pdf_roi_mensal
from app.services.backup_service import gerar_backup_csv
from tests.conftest import SuperuserSession
import app.services.whatsapp_service as ws

ws.SIMULATE_DELAY = False


async def setup_support_tenant(admin_session):
    """Creates a complete tenant with client, service, and pricing for testing."""
    tenant = Tenant(
        id=uuid.uuid4(),
        nome="Clínica Teste Suporte",
        tipo="clinica",
        whatsapp_numero="5511888888888",
        plano="pro",
        sistema_ativo=True,
        horario_abertura="08:00",
        horario_fechamento="18:00",
        limite_pedido_grande=5,
        cor_primaria="#2563eb"
    )
    admin_session.add(tenant)
    await admin_session.flush()

    service = ServicoProduto(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        nome="Consulta Geral",
        categoria="Clínico",
        duracao_minutos=30,
        ativo=True
    )
    admin_session.add(service)
    await admin_session.flush()

    price = Preco(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        servico_id=service.id,
        qtd_min=1,
        qtd_max=1,
        preco_particular=200.00
    )
    admin_session.add(price)
    await admin_session.flush()

    client = ClientePaciente(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        nome="Paciente Teste",
        whatsapp="5511990000001",
        status_reativacao="ativo"
    )
    admin_session.add(client)
    await admin_session.flush()
    await admin_session.commit()

    return tenant, service, price, client


@pytest.fixture(autouse=True)
def clean_whatsapp_queue():
    clear_sent_messages()


# ═══════════════════════════════════════════════
# TASK-021: Lembrete Diário
# ═══════════════════════════════════════════════

@pytest.mark.asyncio
async def test_lembrete_diario_sends_summary(client, admin_session, db_session):
    """Verifies the daily summary task sends a message with appointment count."""
    tenant, service, price, patient = await setup_support_tenant(admin_session)
    tenant_id = tenant.id
    patient_id = patient.id

    # Create an appointment for today
    now = datetime.now(timezone.utc)
    appt = AtendimentoPedido(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        cliente_id=patient_id,
        data_agendamento=now,
        status="aguardando",
        total=200.00,
        pago=False,
        origem="whatsapp"
    )
    admin_session.add(appt)
    await admin_session.commit()

    await db_session.execute(text("SELECT set_tenant_id(:tid)"), {"tid": tenant_id})
    clear_sent_messages()
    from zoneinfo import ZoneInfo
    sp_tz = ZoneInfo("America/Sao_Paulo")
    test_time = datetime.now(sp_tz).replace(hour=8, minute=0, second=0, microsecond=0)
    await processar_lembretes_diarios(db_session, current_time=test_time)

    # Should have sent at least one message
    assert len(SENT_MESSAGES) >= 1
    # Message should contain summary keywords
    any_summary = any("atendimento" in m["mensagem"].lower() or "agenda" in m["mensagem"].lower() for m in SENT_MESSAGES)
    assert any_summary, f"Expected summary message, got: {[m['mensagem'][:80] for m in SENT_MESSAGES]}"
    await db_session.commit()


# ═══════════════════════════════════════════════
# TASK-022: Pós-Atendimento
# ═══════════════════════════════════════════════

@pytest.mark.asyncio
async def test_pos_atendimento_sends_followup(client, admin_session, db_session):
    """Verifies follow-up message is sent for completed appointments."""
    tenant, service, price, patient = await setup_support_tenant(admin_session)
    tenant_id = tenant.id
    patient_id = patient.id

    appt = AtendimentoPedido(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        cliente_id=patient_id,
        data_agendamento=datetime.now(timezone.utc) - timedelta(hours=1),
        status="realizado",
        total=200.00,
        pago=True,
        origem="whatsapp"
    )
    admin_session.add(appt)
    await admin_session.commit()

    appt_id = appt.id
    clear_sent_messages()

    # Call the follow-up directly
    await enviar_agradecimento_pos_atendimento(tenant_id, appt_id, db=db_session)

    assert len(SENT_MESSAGES) >= 1
    msg = SENT_MESSAGES[0]["mensagem"]
    assert "Paciente Teste" in msg or "agradec" in msg.lower() or "visita" in msg.lower()
    await db_session.commit()


@pytest.mark.asyncio
async def test_pos_atendimento_skips_non_realizado(client, admin_session, db_session):
    """Verifies follow-up is NOT sent if appointment status changed from 'realizado'."""
    tenant, service, price, patient = await setup_support_tenant(admin_session)
    tenant_id = tenant.id
    patient_id = patient.id

    appt = AtendimentoPedido(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        cliente_id=patient_id,
        data_agendamento=datetime.now(timezone.utc) - timedelta(hours=1),
        status="cancelado",  # Changed status
        total=200.00,
        pago=False,
        origem="whatsapp"
    )
    admin_session.add(appt)
    await admin_session.commit()

    appt_id = appt.id
    clear_sent_messages()

    await enviar_agradecimento_pos_atendimento(tenant_id, appt_id, db=db_session)

    # Should NOT have sent any message
    assert len(SENT_MESSAGES) == 0
    await db_session.commit()


# ═══════════════════════════════════════════════
# TASK-023: Horário / Retomada
# ═══════════════════════════════════════════════

@pytest.mark.asyncio
async def test_registrar_mensagem_noturna(client, admin_session, db_session):
    """Verifies overnight messages are stored with 'aguardando_abertura' state."""
    tenant, service, price, patient = await setup_support_tenant(admin_session)
    tenant_id = tenant.id

    await db_session.execute(text("SELECT set_tenant_id(:tid)"), {"tid": tenant_id})

    await registrar_mensagem_noturna(
        db_session, tenant, patient.whatsapp, "Oi, quero agendar!", patient.nome
    )
    await db_session.flush()

    # Check state was created
    stmt = select(EstadoConversa).where(
        EstadoConversa.tenant_id == tenant_id,
        EstadoConversa.etapa_atual == "aguardando_abertura"
    )
    res = await db_session.execute(stmt)
    state = res.scalar_one_or_none()
    assert state is not None
    dados = json.loads(state.dados_acumulados)
    assert dados["mensagem_noturna"] == "Oi, quero agendar!"
    await db_session.commit()


@pytest.mark.asyncio
async def test_retomar_conversas_sends_morning_messages(admin_session, db_session):
    """Verifies morning resumption sends messages to overnight contacts."""
    tenant, service, price, patient = await setup_support_tenant(admin_session)
    tenant_id = tenant.id
    patient_id = patient.id

    # Create an 'aguardando_abertura' state manually
    state = EstadoConversa(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        cliente_id=patient_id,
        etapa_atual="aguardando_abertura",
        dados_acumulados=json.dumps({
            "mensagem_noturna": "Quero marcar consulta",
            "etapa_antes_noturna": None
        })
    )
    admin_session.add(state)
    await admin_session.commit()

    await db_session.execute(text("SELECT set_tenant_id(:tid)"), {"tid": tenant_id})
    clear_sent_messages()

    await retomar_conversas_abertura(db_session, tenant)
    await db_session.commit()

    # Should have sent messages (both to owner and client)
    assert len(SENT_MESSAGES) >= 1
    client_msgs = [m for m in SENT_MESSAGES if m["numero"] == patient.whatsapp]
    assert len(client_msgs) >= 1
    assert "bom dia" in client_msgs[0]["mensagem"].lower() or "abr" in client_msgs[0]["mensagem"].lower()


# ═══════════════════════════════════════════════
# TASK-024: PDF Service
# ═══════════════════════════════════════════════

@pytest.mark.asyncio
async def test_pdf_fechamento_generates_valid_pdf():
    """Verifies the daily closing PDF is generated and has valid PDF header."""
    from datetime import date
    dados = {
        "total_atendimentos": 10,
        "realizados": 7,
        "faltas": 2,
        "cancelados": 1,
        "em_producao": 0,
        "receita_total": 1500.00,
        "receita_recebida": 1200.00,
        "receita_pendente": 300.00,
        "mensagens_noturnas": 3,
        "atendimentos": [
            {"horario": "09:00", "cliente": "João", "servico": "Consulta", "status": "realizado"},
            {"horario": "10:00", "cliente": "Maria", "servico": "Retorno", "status": "falta"},
        ]
    }
    pdf_bytes = gerar_pdf_fechamento_diario(
        tenant_nome="Clínica Exemplo",
        cor_primaria="#2563eb",
        data_relatorio=date.today(),
        dados=dados
    )

    assert len(pdf_bytes) > 100
    assert pdf_bytes[:5] == b"%PDF-"


@pytest.mark.asyncio
async def test_pdf_roi_generates_valid_pdf():
    """Verifies the monthly ROI PDF is generated and has valid PDF header."""
    dados = {
        "total_atendimentos": 200,
        "taxa_comparecimento": 85.5,
        "receita_total": 30000.00,
        "receita_perdida_faltas": 4500.00,
        "reativados_crm": 15,
        "consultas_lista_espera": 8,
        "impacto_total": 6500.00,
        "mensalidade": 199.00,
        "roi": 32.7,
    }
    pdf_bytes = gerar_pdf_roi_mensal(
        tenant_nome="Clínica Exemplo",
        cor_primaria="#10b981",
        mes_ano="05/2026",
        dados=dados
    )

    assert len(pdf_bytes) > 100
    assert pdf_bytes[:5] == b"%PDF-"


# ═══════════════════════════════════════════════
# TASK-026: Abandono de Conversa
# ═══════════════════════════════════════════════

@pytest.mark.asyncio
async def test_abandono_detects_stale_conversations(client, admin_session, db_session):
    """Verifies that stale mid-flow conversations are detected and nudged."""
    tenant, service, price, patient = await setup_support_tenant(admin_session)
    tenant_id = tenant.id
    patient_id = patient.id

    # Create a stale conversation state (updated > 30 min ago)
    stale_time = datetime.now(timezone.utc) - timedelta(minutes=35)
    state = EstadoConversa(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        cliente_id=patient_id,
        etapa_atual="aguardando_quantidade",
        dados_acumulados="{}",
    )
    admin_session.add(state)
    await admin_session.flush()

    # Manually set the updated timestamp to be stale
    await admin_session.execute(
        text(
            "UPDATE estados_conversa SET atualizado_em = :ts WHERE id = :sid"
        ),
        {"ts": stale_time, "sid": state.id}
    )
    await admin_session.commit()

    clear_sent_messages()
    await processar_abandonos(db_session)
    await db_session.commit()

    # Should have sent a nudge message
    assert len(SENT_MESSAGES) >= 1
    nudge_msgs = [m for m in SENT_MESSAGES if m["numero"] == patient.whatsapp]
    assert len(nudge_msgs) >= 1
    assert "conversa" in nudge_msgs[0]["mensagem"].lower() or "parada" in nudge_msgs[0]["mensagem"].lower()


@pytest.mark.asyncio
async def test_abandono_ignores_recent_conversations(client, admin_session, db_session):
    """Verifies that recent mid-flow conversations are NOT flagged as abandoned."""
    tenant, service, price, patient = await setup_support_tenant(admin_session)
    tenant_id = tenant.id
    patient_id = patient.id

    # Create a recent conversation state
    state = EstadoConversa(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        cliente_id=patient_id,
        etapa_atual="aguardando_quantidade",
        dados_acumulados="{}",
    )
    admin_session.add(state)
    await admin_session.commit()

    clear_sent_messages()
    await processar_abandonos(db_session)
    await db_session.commit()

    # Should NOT have sent any nudge
    assert len(SENT_MESSAGES) == 0


# ═══════════════════════════════════════════════
# TASK-027: Backup Service
# ═══════════════════════════════════════════════

@pytest.mark.asyncio
async def test_backup_generates_csv_files(client, admin_session, db_session):
    """Verifies CSV backup generates files for each data table."""
    tenant, service, price, patient = await setup_support_tenant(admin_session)
    tenant_id = tenant.id
    patient_id = patient.id

    # Add an appointment
    appt = AtendimentoPedido(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        cliente_id=patient_id,
        data_agendamento=datetime.now(timezone.utc),
        status="realizado",
        total=200.00,
        pago=True,
        origem="whatsapp"
    )
    admin_session.add(appt)

    # Add a message log
    log = LogMensagem(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        cliente_whatsapp=patient.whatsapp,
        direcao="entrada",
        mensagem="Oi, quero agendar",
        tipo="texto"
    )
    admin_session.add(log)
    await admin_session.commit()

    await db_session.execute(text("SELECT set_tenant_id(:tid)"), {"tid": tenant_id})

    backups = await gerar_backup_csv(db_session, tenant)

    assert "clientes.csv" in backups
    assert "atendimentos.csv" in backups
    assert "servicos_produtos.csv" in backups
    assert "log_mensagens_30d.csv" in backups

    # Validate client CSV contains patient
    client_csv = backups["clientes.csv"].decode("utf-8")
    assert "Paciente Teste" in client_csv

    # Validate appointments CSV has data
    appt_csv = backups["atendimentos.csv"].decode("utf-8")
    assert "realizado" in appt_csv
    await db_session.rollback()
