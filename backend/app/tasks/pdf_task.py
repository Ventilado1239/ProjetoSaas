import logging
import uuid
from datetime import datetime, timedelta
from typing import Optional
from zoneinfo import ZoneInfo
from sqlalchemy import select, text, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.models import (
    Tenant, AtendimentoPedido, ClientePaciente,
    ItemAtendimento, ServicoProduto, LogMensagem, EstadoConversa
)
from app.services.pdf_service import gerar_pdf_fechamento_diario
from app.services.tenant_settings import get_evolution_instance_name, get_owner_whatsapp
from app.services.whatsapp_service import enviar_mensagem

logger = logging.getLogger(__name__)

SP_TZ = ZoneInfo("America/Sao_Paulo")
MAX_RETRIES = 3
RETRY_INTERVAL_MINUTES = 10


async def processar_relatorios_fechamento(db: Optional[AsyncSession] = None):
    """
    Scheduled task that runs daily at 18:00.
    Generates a closing PDF report for each active tenant and sends it via WhatsApp.
    """
    logger.info("Iniciando geração de relatórios de fechamento diário...")
    if db is None:
        async with AsyncSessionLocal() as session:
            try:
                await _run_fechamento(session)
                await session.commit()
            except Exception as e:
                logger.exception(f"Erro ao processar relatórios de fechamento: {e}")
                await session.rollback()
    else:
        await _run_fechamento(db)


async def _run_fechamento(db: AsyncSession):
    now_sp = datetime.now(SP_TZ)
    today = now_sp.date()

    # Time bounds for today in SP timezone
    start_dt = datetime.combine(today, datetime.min.time()).replace(tzinfo=SP_TZ)
    end_dt = datetime.combine(today, datetime.max.time()).replace(tzinfo=SP_TZ)

    # Fetch all active tenants (bypass RLS)
    await db.execute(text("SET LOCAL app.bypass_rls = 'true'"))
    res_tenants = await db.execute(select(Tenant).where(Tenant.sistema_ativo == True))
    tenants = res_tenants.scalars().all()
    await db.execute(text("SET LOCAL app.bypass_rls = 'false'"))

    for tenant in tenants:
        try:
            await _gerar_e_enviar_pdf(db, tenant, start_dt, end_dt, today)
        except Exception as e:
            logger.exception(f"Erro ao gerar PDF para tenant {tenant.nome}: {e}")
            # Schedule retry
            _agendar_retry(tenant.id, attempt=1)


async def _gerar_e_enviar_pdf(
    db: AsyncSession,
    tenant: Tenant,
    start_dt: datetime,
    end_dt: datetime,
    today
):
    await db.execute(text("SELECT set_tenant_id(:tenant_id)"), {"tenant_id": tenant.id})

    # Query today's appointments and join with ClientePaciente (1-to-1 relationship)
    stmt = (
        select(AtendimentoPedido, ClientePaciente)
        .join(ClientePaciente, AtendimentoPedido.cliente_id == ClientePaciente.id)
        .where(
            AtendimentoPedido.tenant_id == tenant.id,
            AtendimentoPedido.data_agendamento >= start_dt,
            AtendimentoPedido.data_agendamento <= end_dt,
        )
        .order_by(AtendimentoPedido.data_agendamento.asc())
    )
    res = await db.execute(stmt)
    appts_rows = res.all()

    # Batch query all items for these appointments to find associated service names
    appt_ids = [row[0].id for row in appts_rows]
    items_by_appt = {}
    if appt_ids:
        items_query = (
            select(ItemAtendimento.atendimento_id, ServicoProduto.nome)
            .join(ServicoProduto, ItemAtendimento.servico_id == ServicoProduto.id)
            .where(ItemAtendimento.atendimento_id.in_(appt_ids))
        )
        items_rows = (await db.execute(items_query)).all()
        for appt_id, service_name in items_rows:
            if appt_id not in items_by_appt:
                items_by_appt[appt_id] = []
            items_by_appt[appt_id].append(service_name)

    total = len(appts_rows)
    realizados = sum(1 for r in appts_rows if r[0].status in ["realizado", "entregue", "pronto"])
    faltas = sum(1 for r in appts_rows if r[0].status == "falta")
    cancelados = sum(1 for r in appts_rows if r[0].status == "cancelado")
    em_producao = sum(1 for r in appts_rows if r[0].status == "em_producao")

    receita_total = sum(float(r[0].total) for r in appts_rows if r[0].status not in ["cancelado", "falta"])
    receita_recebida = sum(float(r[0].total) for r in appts_rows if r[0].pago)
    receita_pendente = receita_total - receita_recebida

    # Count nocturnal messages
    stmt_noturnas = (
        select(func.count())
        .select_from(EstadoConversa)
        .where(
            EstadoConversa.tenant_id == tenant.id,
            EstadoConversa.etapa_atual == "aguardando_abertura"
        )
    )
    res_noturnas = await db.execute(stmt_noturnas)
    mensagens_noturnas = res_noturnas.scalar() or 0

    # Build appointment details list
    atendimentos_list = []
    for appt, client in appts_rows:
        client_name = client.nome if client else "N/A"
        services_list = items_by_appt.get(appt.id, [])
        service_name = ", ".join(services_list) if services_list else "N/A"
        horario = appt.data_agendamento.astimezone(SP_TZ).strftime("%H:%M")

        atendimentos_list.append({
            "horario": horario,
            "cliente": client_name,
            "servico": service_name,
            "status": appt.status,
        })

    dados = {
        "total_atendimentos": total,
        "realizados": realizados,
        "faltas": faltas,
        "cancelados": cancelados,
        "em_producao": em_producao,
        "receita_total": receita_total,
        "receita_recebida": receita_recebida,
        "receita_pendente": receita_pendente,
        "mensagens_noturnas": mensagens_noturnas,
        "atendimentos": atendimentos_list,
    }

    # Generate PDF
    pdf_bytes = gerar_pdf_fechamento_diario(
        tenant_nome=tenant.nome,
        cor_primaria=tenant.cor_primaria or "#2563eb",
        data_relatorio=today,
        dados=dados,
    )

    logger.info(f"PDF de fechamento gerado para {tenant.nome}: {len(pdf_bytes)} bytes")

    # Send notification to owner via WhatsApp
    owner_phone = get_owner_whatsapp(tenant)
    summary_msg = (
        f"📊 *RELATÓRIO DE FECHAMENTO — {today.strftime('%d/%m/%Y')}*\n\n"
        f"📈 Atendimentos: {total}\n"
        f"✅ Realizados: {realizados}\n"
        f"❌ Faltas: {faltas}\n"
        f"💰 Receita: R$ {receita_total:,.2f}\n"
        f"💵 Recebida: R$ {receita_recebida:,.2f}\n"
        f"⏳ Pendente: R$ {receita_pendente:,.2f}\n\n"
        f"O PDF completo foi gerado e salvo com sucesso."
    )

    await enviar_mensagem(
        str(tenant.id),
        owner_phone,
        summary_msg,
        instance_name=get_evolution_instance_name(tenant.id, tenant),
    )

    log = LogMensagem(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        cliente_whatsapp=owner_phone,
        direcao="saida",
        mensagem=summary_msg,
        tipo="texto"
    )
    db.add(log)
    await db.flush()


def _agendar_retry(tenant_id: uuid.UUID, attempt: int):
    """Schedules a retry for PDF generation up to MAX_RETRIES times."""
    if attempt > MAX_RETRIES:
        logger.error(f"Falha definitiva: PDF para tenant {tenant_id} falhou após {MAX_RETRIES} tentativas.")
        return

    try:
        from app.tasks.scheduler import scheduler
        run_time = datetime.now(SP_TZ) + timedelta(minutes=RETRY_INTERVAL_MINUTES * attempt)
        scheduler.add_job(
            _retry_pdf_generation,
            trigger="date",
            run_date=run_time,
            args=[tenant_id, attempt],
            id=f"retry_pdf_{tenant_id}_{attempt}",
            replace_existing=True,
        )
        logger.info(f"Agendada tentativa {attempt}/{MAX_RETRIES} de PDF para tenant {tenant_id} às {run_time}.")
    except Exception as e:
        logger.error(f"Erro ao agendar retry de PDF: {e}")


async def _retry_pdf_generation(tenant_id: uuid.UUID, attempt: int):
    """Retry job for PDF generation."""
    logger.info(f"Tentativa {attempt}/{MAX_RETRIES} de gerar PDF para tenant {tenant_id}...")
    async with AsyncSessionLocal() as db:
        try:
            await db.execute(text("SELECT set_tenant_id(:tenant_id)"), {"tenant_id": tenant_id})
            tenant = await db.get(Tenant, tenant_id)
            if not tenant:
                return

            now_sp = datetime.now(SP_TZ)
            today = now_sp.date()
            start_dt = datetime.combine(today, datetime.min.time()).replace(tzinfo=SP_TZ)
            end_dt = datetime.combine(today, datetime.max.time()).replace(tzinfo=SP_TZ)

            await _gerar_e_enviar_pdf(db, tenant, start_dt, end_dt, today)
            await db.commit()
            logger.info(f"PDF gerado com sucesso na tentativa {attempt} para tenant {tenant.nome}.")
        except Exception as e:
            logger.exception(f"Tentativa {attempt} falhou para tenant {tenant_id}: {e}")
            await db.rollback()
            _agendar_retry(tenant_id, attempt + 1)
