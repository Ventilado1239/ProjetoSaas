import logging
from zoneinfo import ZoneInfo
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)

# Initialize the scheduler with the Brasilia timezone
scheduler = AsyncIOScheduler(timezone=ZoneInfo("America/Sao_Paulo"))

def start_scheduler():
    """Starts the background task scheduler."""
    import sys
    if "pytest" in sys.modules:
        logger.info("Ambiente de testes detectado. Ignorando inicialização do APScheduler.")
        return
    if not scheduler.running:
        logger.info("Inicializando o APScheduler com timezone America/Sao_Paulo...")
        
        # 1. Register 48h confirmation task: 2x daily (08:00 and 14:00)
        from app.tasks.confirmacao_task import processar_confirmacoes
        scheduler.add_job(
            processar_confirmacoes,
            CronTrigger(hour="8,14", minute="0"),
            id="confirmacoes_48h",
            name="Confirmação de agendamentos 48h antes",
            replace_existing=True
        )

        # 2. Register CRM reactivation task: Weekly (Mondays at 09:00)
        from app.tasks.reativacao_task import processar_reativacoes
        scheduler.add_job(
            processar_reativacoes,
            CronTrigger(day_of_week="mon", hour="9", minute="0"),
            id="reativacao_inativos",
            name="CRM de reativação de clientes inativos",
            replace_existing=True
        )

        # 3. Register CRM daily opening hour resumption/out-of-office catchup
        # (This runs every 5 minutes to check which tenants just opened and need messages sent)
        from app.tasks.retomada_task import processar_retomadas
        scheduler.add_job(
            processar_retomadas,
            CronTrigger(minute="*/5"),
            id="retomada_mensagens",
            name="Retomada de conversas na abertura do expediente",
            replace_existing=True
        )

        # 4. Register daily closing PDF report: Daily at 18:00
        from app.tasks.pdf_task import processar_relatorios_fechamento
        scheduler.add_job(
            processar_relatorios_fechamento,
            CronTrigger(hour="18", minute="0"),
            id="fechamento_diario_pdf",
            name="Geração e envio de PDF de fechamento diário",
            replace_existing=True
        )

        # 5. Register monthly ROI report: Day 1 of every month at 08:00
        from app.tasks.roi_task import processar_relatorios_roi_mensal
        scheduler.add_job(
            processar_relatorios_roi_mensal,
            CronTrigger(day="1", hour="8", minute="0"),
            id="roi_mensal_pdf",
            name="Geração e envio de PDF de ROI mensal",
            replace_existing=True
        )

        # 6. Register Daily Backup: Daily at 23:00
        from app.tasks.backup_task import processar_backups
        scheduler.add_job(
            processar_backups,
            CronTrigger(hour="23", minute="0"),
            id="backup_diario",
            name="Backup diário de dados para o Google Drive",
            replace_existing=True
        )

        # 7. Register Owner Daily Summary: Daily at 07:00
        from app.tasks.lembrete_task import processar_lembretes_diarios
        scheduler.add_job(
            processar_lembretes_diarios,
            CronTrigger(hour="7", minute="0"),
            id="lembretes_diarios",
            name="Resumo diário de atendimentos para os donos",
            replace_existing=True
        )

        # 8. Register Client Abandonment Detection: Every 15 minutes
        from app.tasks.abandono_task import processar_abandonos
        scheduler.add_job(
            processar_abandonos,
            CronTrigger(minute="*/15"),
            id="abandono_conversas",
            name="Detecção de conversas abandonadas",
            replace_existing=True
        )

        scheduler.start()
        logger.info("APScheduler iniciado com sucesso.")

def shutdown_scheduler():
    """Stops the background task scheduler."""
    if scheduler.running:
        logger.info("Encerrando o APScheduler...")
        scheduler.shutdown()
        logger.info("APScheduler encerrado.")
