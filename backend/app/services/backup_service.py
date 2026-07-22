import io
import csv
import logging
import uuid
import base64
import hashlib
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from cryptography.fernet import Fernet

from app.models.models import (
    Tenant, ClientePaciente, AtendimentoPedido,
    ServicoProduto, LogMensagem
)

logger = logging.getLogger(__name__)

SP_TZ = ZoneInfo("America/Sao_Paulo")


def encrypt_backup_content(content: bytes, encryption_key: str) -> bytes:
    """Encrypt backup bytes with an authenticated key derived from configuration."""
    key = base64.urlsafe_b64encode(hashlib.sha256(encryption_key.encode("utf-8")).digest())
    return Fernet(key).encrypt(content)


def decrypt_backup_content(content: bytes, encryption_key: str) -> bytes:
    """Decrypt and authenticate backup bytes for controlled restore workflows."""
    key = base64.urlsafe_b64encode(hashlib.sha256(encryption_key.encode("utf-8")).digest())
    return Fernet(key).decrypt(content)


async def gerar_backup_csv(db: AsyncSession, tenant: Tenant) -> dict:
    """
    Generates CSV exports for the tenant's key data tables.
    Returns a dict mapping filename to CSV bytes.
    """
    await db.execute(text("SELECT set_tenant_id(:tenant_id)"), {"tenant_id": tenant.id})

    backups = {}

    # 1. Clients
    res = await db.execute(
        select(ClientePaciente).where(ClientePaciente.tenant_id == tenant.id)
    )
    clients = res.scalars().all()
    buf_clients = io.StringIO()
    writer = csv.writer(buf_clients)
    writer.writerow(["id", "nome", "whatsapp", "status_reativacao", "ultima_consulta"])
    for c in clients:
        writer.writerow([
            str(c.id), c.nome, c.whatsapp,
            c.status_reativacao,
            c.ultima_consulta.isoformat() if c.ultima_consulta else ""
        ])
    backups["clientes.csv"] = buf_clients.getvalue().encode("utf-8")

    # 2. Appointments / Orders
    res = await db.execute(
        select(AtendimentoPedido).where(AtendimentoPedido.tenant_id == tenant.id)
    )
    appts = res.scalars().all()
    buf_appts = io.StringIO()
    writer = csv.writer(buf_appts)
    writer.writerow(["id", "cliente_id", "data_agendamento", "status", "total", "pago"])
    for a in appts:
        writer.writerow([
            str(a.id), str(a.cliente_id),
            a.data_agendamento.isoformat() if a.data_agendamento else "",
            a.status, str(a.total), str(a.pago)
        ])
    backups["atendimentos.csv"] = buf_appts.getvalue().encode("utf-8")

    # 3. Services / Products
    res = await db.execute(
        select(ServicoProduto).where(ServicoProduto.tenant_id == tenant.id)
    )
    services = res.scalars().all()
    buf_svcs = io.StringIO()
    writer = csv.writer(buf_svcs)
    writer.writerow(["id", "nome", "categoria", "ativo"])
    for s in services:
        writer.writerow([str(s.id), s.nome, s.categoria or "", str(s.ativo)])
    backups["servicos_produtos.csv"] = buf_svcs.getvalue().encode("utf-8")

    # 4. Message log (last 30 days only)
    cutoff = datetime.now(SP_TZ) - timedelta(days=30)
    res = await db.execute(
        select(LogMensagem)
        .where(
            LogMensagem.tenant_id == tenant.id,
            LogMensagem.criado_em >= cutoff,
        )
        .order_by(LogMensagem.criado_em.desc())
    )
    logs = res.scalars().all()
    buf_logs = io.StringIO()
    writer = csv.writer(buf_logs)
    writer.writerow(["id", "cliente_whatsapp", "direcao", "tipo", "mensagem", "criado_em"])
    for l in logs:
        writer.writerow([
            str(l.id), l.cliente_whatsapp, l.direcao, l.tipo,
            l.mensagem[:200] if l.mensagem else "",
            l.criado_em.isoformat() if l.criado_em else ""
        ])
    backups["log_mensagens_30d.csv"] = buf_logs.getvalue().encode("utf-8")

    total_bytes = sum(len(v) for v in backups.values())
    logger.info(f"Backup CSV gerado para {tenant.nome}: {len(backups)} arquivos, {total_bytes} bytes.")

    return backups
