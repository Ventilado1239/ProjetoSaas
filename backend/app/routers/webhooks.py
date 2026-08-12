import logging
import uuid
import hmac
import json
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Request, Depends, status
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.database import get_db
from app.models.models import Tenant, LogMensagem, WebhookEvent
from app.config import settings
from app.services.tenant_settings import get_evolution_instance_name, get_owner_whatsapp
from app.services.whatsapp_service import enviar_mensagem

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhooks", tags=["webhooks"])
MAX_WEBHOOK_BYTES = 1_000_000
ASAAS_EVENT_ALIASES = {
    # Legacy names are accepted during migration, but all internal handling uses
    # the current Asaas event names.
    "payment.overdue": "PAYMENT_OVERDUE",
    "payment.received": "PAYMENT_RECEIVED",
}
SUPPORTED_ASAAS_EVENTS = {"PAYMENT_OVERDUE", "PAYMENT_RECEIVED"}

@router.post("/asaas")
async def receive_asaas_webhook(
    request: Request,
    asaas_access_token: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Receives billing events from Asaas.
    Verifies the auth token and processes current Asaas payment events.
    """
    # 1. Verify token
    webhook_token = settings.ASAAS_WEBHOOK_TOKEN or settings.ASAAS_WEBHOOK_SECRET
    if not webhook_token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Webhook de cobranca nao configurado"
        )
    if not asaas_access_token or not hmac.compare_digest(asaas_access_token, webhook_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de acesso do Asaas inválido"
        )
        
    try:
        raw_body = await request.body()
        if len(raw_body) > MAX_WEBHOOK_BYTES:
            raise HTTPException(status_code=413, detail="Payload muito grande")
        payload = json.loads(raw_body)
    except HTTPException:
        raise
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise HTTPException(status_code=400, detail="Payload JSON inválido")
        
    raw_event = payload.get("event")
    event = ASAAS_EVENT_ALIASES.get(raw_event, raw_event)
    payment = payload.get("payment", {})
    tenant_id_str = payment.get("externalReference")
    
    if not event or not tenant_id_str:
        return {"status": "ignored", "reason": "missing_event_or_external_reference"}
    if event not in SUPPORTED_ASAAS_EVENTS:
        return {"status": "ignored", "reason": "unhandled_event"}
        
    try:
        tenant_id = uuid.UUID(tenant_id_str)
    except ValueError:
        return {"status": "ignored", "reason": "invalid_tenant_uuid"}
        
    # Enforce database session RLS context bypass / admin access
    await db.execute(text("SET LOCAL app.bypass_rls = 'true'"))
    
    # Fetch tenant
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        return {"status": "error", "message": "Tenant não encontrado"}

    event_id = str(payload.get("id") or f"{event}:{payment.get('id', '')}")[:255]
    if not payment.get("id") and not payload.get("id"):
        raise HTTPException(status_code=400, detail="Evento sem identificador")
    inserted_event_id = await db.scalar(
        pg_insert(WebhookEvent)
        .values(id=uuid.uuid4(), provider="asaas", event_id=event_id, tenant_id=tenant.id)
        .on_conflict_do_nothing(constraint="uq_webhook_provider_event")
        .returning(WebhookEvent.id)
    )
    if not inserted_event_id:
        return {"status": "duplicate", "event_id": event_id}

    owner_phone = get_owner_whatsapp(tenant)
    instance_name = get_evolution_instance_name(tenant.id, tenant)
        
    # Re-enable RLS context for safety during operations
    await db.execute(text("SELECT set_tenant_id(:tenant_id)"), {"tenant_id": tenant.id})
    
    if event == "PAYMENT_OVERDUE":
        due_date_str = payment.get("dueDate")
        days_overdue = 0
        if due_date_str:
            try:
                due_date = datetime.strptime(due_date_str, "%Y-%m-%d").date()
                today = datetime.now(timezone.utc).date()
                days_overdue = (today - due_date).days
            except Exception as e:
                logger.error(f"Erro ao parsear due date '{due_date_str}': {e}")
                
        # Block only after 5 days of delinquency
        if days_overdue >= 5:
            tenant.sistema_ativo = False
            tenant.pagamento_status = "inadimplente"
            await db.flush()
            
            # Send block notification to owner
            payment_link = payment.get("invoiceUrl") or "https://asaas.com/pay"
            reply = (
                f"❌ *SISTEMA BLOQUEADO por Inadimplência* ❌\n\n"
                f"Olá! Identificamos que a mensalidade do seu SaaS está atrasada há {days_overdue} dias.\n"
                f"Os fluxos automatizados do WhatsApp foram suspensos.\n\n"
                f"Efetue o pagamento para reativar o sistema imediatamente:\n"
                f"🔗 Link de pagamento: {payment_link}\n\n"
                f"Dúvidas? Entre em contato com nosso suporte."
            )
            await enviar_mensagem(str(tenant.id), owner_phone, reply, instance_name=instance_name)
            
            # Log message
            log = LogMensagem(
                id=uuid.uuid4(),
                tenant_id=tenant.id,
                cliente_whatsapp=owner_phone,
                direcao="saida",
                mensagem=reply,
                tipo="texto"
            )
            db.add(log)
            await db.commit()
            return {"status": "blocked", "days_overdue": days_overdue}
        else:
            tenant.pagamento_status = "atrasado"
            # Send friendly warning reminder
            payment_link = payment.get("invoiceUrl") or "https://asaas.com/pay"
            reply = (
                f"⚠️ *AVISO de Mensalidade Atrasada* ⚠️\n\n"
                f"Olá! Notamos que sua mensalidade está vencida. Evite o bloqueio dos serviços do WhatsApp (que ocorrerá após 5 dias de atraso).\n\n"
                f"Efetue o pagamento:\n"
                f"🔗 Link de pagamento: {payment_link}"
            )
            await enviar_mensagem(str(tenant.id), owner_phone, reply, instance_name=instance_name)
            await db.commit()
            return {"status": "warning_sent", "days_overdue": days_overdue}
            
    elif event == "PAYMENT_RECEIVED":
        # Reactivate system
        tenant.sistema_ativo = True
        tenant.pagamento_status = "em_dia"
        await db.flush()
        
        # Send confirmation to owner
        reply = (
            f"✅ *SISTEMA REATIVADO* ✅\n\n"
            f"Obrigado! Identificamos o pagamento da sua mensalidade.\n"
            f"O sistema de automação e o dashboard foram reativados com sucesso. Ótimos negócios! 🚀"
        )
        await enviar_mensagem(str(tenant.id), owner_phone, reply, instance_name=instance_name)
        
        log = LogMensagem(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            cliente_whatsapp=owner_phone,
            direcao="saida",
            mensagem=reply,
            tipo="texto"
        )
        db.add(log)
        await db.commit()
        return {"status": "reactivated"}
        
    await db.commit()
    return {"status": "ignored", "reason": "unhandled_event"}
