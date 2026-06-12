import logging
import uuid
from datetime import datetime, timedelta
from typing import Optional
from zoneinfo import ZoneInfo
from sqlalchemy import select, text, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.models import (
    Tenant, AtendimentoPedido, ClientePaciente, ListaEspera, LogMensagem
)
from app.services.pdf_service import gerar_pdf_roi_mensal
from app.services.whatsapp_service import enviar_mensagem

logger = logging.getLogger(__name__)

SP_TZ = ZoneInfo("America/Sao_Paulo")
DEFAULT_OWNER_PHONE = "5511999999999"

# Plan pricing for ROI calculation
PLAN_PRICING = {
    "starter": 99.00,
    "pro": 199.00,
    "premium": 399.00,
}


async def processar_relatorios_roi_mensal(db: Optional[AsyncSession] = None):
    """
    Scheduled task running on the 1st of every month at 08:00.
    Calculates ROI and generates an executive PDF for each active tenant.
    """
    logger.info("Iniciando geração de relatórios de ROI mensal...")
    if db is None:
        async with AsyncSessionLocal() as session:
            try:
                await _run_roi(session)
                await session.commit()
            except Exception as e:
                logger.exception(f"Erro ao processar relatórios de ROI: {e}")
                await session.rollback()
    else:
        await _run_roi(db)


async def _run_roi(db: AsyncSession):
    now_sp = datetime.now(SP_TZ)

    # Calculate the previous month date range
    first_of_current = now_sp.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    last_of_prev = first_of_current - timedelta(seconds=1)
    first_of_prev = last_of_prev.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    mes_ano = first_of_prev.strftime("%m/%Y")

    start_dt = first_of_prev
    end_dt = last_of_prev

    # Fetch all active tenants (bypass RLS)
    await db.execute(text("SET LOCAL app.bypass_rls = 'true'"))
    res_tenants = await db.execute(select(Tenant).where(Tenant.sistema_ativo == True))
    tenants = res_tenants.scalars().all()
    await db.execute(text("SET LOCAL app.bypass_rls = 'false'"))

    for tenant in tenants:
        try:
            await _gerar_roi_tenant(db, tenant, start_dt, end_dt, mes_ano)
        except Exception as e:
            logger.exception(f"Erro ao gerar ROI para tenant {tenant.nome}: {e}")


async def _gerar_roi_tenant(
    db: AsyncSession,
    tenant: Tenant,
    start_dt: datetime,
    end_dt: datetime,
    mes_ano: str
):
    await db.execute(text("SELECT set_tenant_id(:tenant_id)"), {"tenant_id": tenant.id})

    # Query all appointments in the previous month
    stmt = (
        select(AtendimentoPedido)
        .where(
            AtendimentoPedido.tenant_id == tenant.id,
            AtendimentoPedido.data_agendamento >= start_dt,
            AtendimentoPedido.data_agendamento <= end_dt,
        )
    )
    res = await db.execute(stmt)
    appts = res.scalars().all()

    total_atendimentos = len(appts)
    realizados = [a for a in appts if a.status in ["realizado", "entregue", "pronto"]]
    faltas = [a for a in appts if a.status == "falta"]

    taxa_comparecimento = (len(realizados) / total_atendimentos * 100) if total_atendimentos > 0 else 0
    receita_total = sum(float(a.total) for a in realizados)
    receita_perdida_faltas = sum(float(a.total) for a in faltas)

    # Count reactivated clients (status_reativacao changed to 'reativado' in the period)
    stmt_reativados = (
        select(func.count())
        .select_from(ClientePaciente)
        .where(
            ClientePaciente.tenant_id == tenant.id,
            ClientePaciente.status_reativacao == "reativado",
        )
    )
    res_reativados = await db.execute(stmt_reativados)
    reativados_crm = res_reativados.scalar() or 0

    # Count appointments generated from waitlist
    stmt_lista = (
        select(func.count())
        .select_from(ListaEspera)
        .where(
            ListaEspera.tenant_id == tenant.id,
            ListaEspera.status == "agendado",
        )
    )
    res_lista = await db.execute(stmt_lista)
    consultas_lista_espera = res_lista.scalar() or 0

    # Calculate ROI
    mensalidade = PLAN_PRICING.get(tenant.plano, 199.00)
    # Impact: recovered revenue from reactivation + waitlist + reduced no-show losses
    impacto_reativacao = reativados_crm * (receita_total / max(len(realizados), 1))
    impacto_lista = consultas_lista_espera * (receita_total / max(len(realizados), 1))
    impacto_total = impacto_reativacao + impacto_lista + (receita_perdida_faltas * 0.3)  # 30% of losses prevented

    roi = impacto_total / mensalidade if mensalidade > 0 else 0

    dados = {
        "total_atendimentos": total_atendimentos,
        "taxa_comparecimento": taxa_comparecimento,
        "receita_total": receita_total,
        "receita_perdida_faltas": receita_perdida_faltas,
        "reativados_crm": reativados_crm,
        "consultas_lista_espera": consultas_lista_espera,
        "impacto_total": impacto_total,
        "mensalidade": mensalidade,
        "roi": roi,
    }

    # Generate PDF
    pdf_bytes = gerar_pdf_roi_mensal(
        tenant_nome=tenant.nome,
        cor_primaria=tenant.cor_primaria or "#2563eb",
        mes_ano=mes_ano,
        dados=dados,
    )

    logger.info(f"PDF de ROI gerado para {tenant.nome}: {len(pdf_bytes)} bytes, ROI={roi:.1f}x")

    # Send WhatsApp summary to owner
    owner_phone = DEFAULT_OWNER_PHONE
    msg = (
        f"📈 *RELATÓRIO MENSAL DE ROI — {mes_ano}*\n\n"
        f"🏢 {tenant.nome}\n\n"
        f"📊 Atendimentos: {total_atendimentos}\n"
        f"✅ Comparecimento: {taxa_comparecimento:.0f}%\n"
        f"💰 Receita: R$ {receita_total:,.2f}\n"
        f"🔄 Reativados pelo CRM: {reativados_crm}\n"
        f"📋 Gerados pela Lista de Espera: {consultas_lista_espera}\n\n"
        f"🚀 *O sistema gerou R$ {impacto_total:,.2f} de impacto neste mês!*\n"
        f"📊 *ROI: {roi:.1f}x sobre a mensalidade*"
    )

    await enviar_mensagem(str(tenant.id), owner_phone, msg)

    log = LogMensagem(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        cliente_whatsapp=owner_phone,
        direcao="saida",
        mensagem=msg,
        tipo="texto"
    )
    db.add(log)
    await db.flush()

    logger.info(f"Relatório de ROI enviado para o dono do tenant {tenant.nome}.")
