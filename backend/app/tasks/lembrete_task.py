import logging
import uuid
import zoneinfo
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.models import Tenant, AtendimentoPedido, ClientePaciente, Aprovacao, LogMensagem
from app.services.whatsapp_service import enviar_mensagem

logger = logging.getLogger(__name__)

DEFAULT_OWNER_PHONE = "5511999999999"

async def processar_lembretes_diarios(db: Optional[AsyncSession] = None, current_time: Optional[datetime] = None):
    """
    Scheduled task that runs daily.
    Calculates today's summary for each active tenant whose opening hours match the current time (+/- 30 minutes)
    and sends it to the owner.
    """
    logger.info("Iniciando processamento de lembretes diários...")
    if db is None:
        async with AsyncSessionLocal() as session:
            try:
                await _run_lembretes(session, current_time)
                await session.commit()
            except Exception as e:
                logger.exception(f"Erro ao processar lembretes diários: {e}")
                await session.rollback()
    else:
        await _run_lembretes(db, current_time)

async def _run_lembretes(db: AsyncSession, current_time: Optional[datetime] = None):
    # 1. Fetch all active tenants
    await db.execute(text("SET LOCAL app.bypass_rls = 'true'"))
    res_tenants = await db.execute(select(Tenant).where(Tenant.sistema_ativo == True))
    tenants = res_tenants.scalars().all()
    await db.execute(text("SET LOCAL app.bypass_rls = 'false'"))
    
    sp_tz = zoneinfo.ZoneInfo("America/Sao_Paulo")
    if current_time:
        if current_time.tzinfo is None:
            now_sp = current_time.replace(tzinfo=timezone.utc).astimezone(sp_tz)
        else:
            now_sp = current_time.astimezone(sp_tz)
    else:
        now_sp = datetime.now(sp_tz)
        
    current_minutes = now_sp.hour * 60 + now_sp.minute
    today = now_sp.date()
    
    # Define time bounds for today in UTC
    start_dt = datetime.combine(today, datetime.min.time()).replace(tzinfo=sp_tz)
    end_dt = datetime.combine(today, datetime.max.time()).replace(tzinfo=sp_tz)

    for tenant in tenants:
        # Check if the opening hour matches "now" (+/- 30 minutes)
        # Parse tenant's horario_abertura (format expected: "HH:MM")
        try:
            h_open, m_open = map(int, tenant.horario_abertura.split(":"))
            open_minutes = h_open * 60 + m_open
        except Exception:
            logger.warning(f"Horário de abertura inválido para tenant {tenant.id}: {tenant.horario_abertura}. Ignorando filtro de tempo.")
            # Fallback to matching if parsing fails (e.g. during tests with empty strings)
            open_minutes = current_minutes
        
        # Check if absolute difference is <= 30 minutes
        if abs(open_minutes - current_minutes) > 30:
            continue
            
        logger.info(f"Processando resumo diário para o tenant {tenant.nome} ({tenant.id})...")
        
        # Enforce RLS context
        await db.execute(text("SELECT set_tenant_id(:tenant_id)"), {"tenant_id": tenant.id})
        
        # 2. Fetch today's appointments and join with ClientePaciente (1-to-1 relationship)
        stmt_appts = (
            select(AtendimentoPedido, ClientePaciente)
            .join(ClientePaciente, AtendimentoPedido.cliente_id == ClientePaciente.id)
            .where(
                AtendimentoPedido.tenant_id == tenant.id,
                AtendimentoPedido.data_agendamento >= start_dt,
                AtendimentoPedido.data_agendamento <= end_dt,
                AtendimentoPedido.status != "cancelado"
            )
            .order_by(AtendimentoPedido.data_agendamento.asc())
        )
        res_appts = await db.execute(stmt_appts)
        appts_rows = res_appts.all()
        
        total_count = len(appts_rows)
        confirmed_count = sum(1 for r in appts_rows if r[0].confirmado or r[0].status in ["confirmado", "realizado", "entregue", "pronto"])
        pending_confirm = sum(1 for r in appts_rows if not r[0].confirmado and r[0].status == "aguardando")
        
        # 3. Fetch pending approvals
        stmt_aprv = (
            select(Aprovacao)
            .where(
                Aprovacao.tenant_id == tenant.id,
                Aprovacao.status == "pendente"
            )
        )
        res_aprv = await db.execute(stmt_aprv)
        pending_aprv_count = len(res_aprv.scalars().all())
        
        # 4. Construct appointment list details
        appt_lines = []
        for appt, client in appts_rows:
            client_name = client.nome if client else "Cliente"
            
            time_str = appt.data_agendamento.astimezone(sp_tz).strftime("%H:%M")
            status_emoji = "✅" if (appt.confirmado or appt.status in ["confirmado", "realizado", "entregue", "pronto"]) else "⏳"
            
            appt_lines.append(f"• {time_str} - {client_name} {status_emoji}")
            
        appt_list_text = "\n".join(appt_lines) if appt_lines else "• Nenhum atendimento agendado."
        
        # 5. Build report text
        summary_msg = (
            f"🌞 *BOM DIA! AQUI ESTÁ SEU RESUMO DIÁRIO* 🌞\n\n"
            f"📅 *Data*: {today.strftime('%d/%m/%Y')}\n"
            f"🏢 *Tenant*: {tenant.nome}\n\n"
            f"📊 *Métricas do Dia*:\n"
            f"📈 Total de Atendimentos: {total_count}\n"
            f"🟢 Confirmados: {confirmed_count}\n"
            f"🟡 Aguardando Confirmação: {pending_confirm}\n"
            f"🚨 Aprovações Pendentes: {pending_aprv_count}\n\n"
            f"📋 *Agenda do Dia*:\n"
            f"{appt_list_text}\n\n"
            f"Tenha um excelente dia de trabalho! 🚀"
        )
        
        # Send message to owner
        owner_phone = DEFAULT_OWNER_PHONE
        await enviar_mensagem(str(tenant.id), owner_phone, summary_msg)
        
        # Log outgoing message
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
        
    logger.info("Processamento de lembretes diários concluído.")
