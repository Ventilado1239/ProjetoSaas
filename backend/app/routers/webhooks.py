import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Request, Depends, status
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.models import Tenant, LogMensagem
from app.config import settings
from app.services.whatsapp_service import enviar_mensagem

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhooks", tags=["webhooks"])

# Owner phone fallback (normally configured in tenant settings, but default to this for testing/demo)
DEFAULT_OWNER_PHONE = "5511999999999"

@router.post("/asaas")
async def receive_asaas_webhook(
    request: Request,
    asaas_access_token: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Receives billing events from Asaas.
    Verifies token, processes payment.overdue (blocks after 5 days) and payment.received.
    """
    # 1. Verify token
    if settings.ASAAS_WEBHOOK_TOKEN and asaas_access_token != settings.ASAAS_WEBHOOK_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de acesso do Asaas inválido"
        )
        
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Payload JSON inválido")
        
    event = payload.get("event")
    payment = payload.get("payment", {})
    tenant_id_str = payment.get("externalReference")
    
    if not event or not tenant_id_str:
        return {"status": "ignored", "reason": "missing_event_or_external_reference"}
        
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
        
    # Re-enable RLS context for safety during operations
    await db.execute(text("SELECT set_tenant_id(:tenant_id)"), {"tenant_id": tenant.id})
    
    if event == "payment.overdue":
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
            await enviar_mensagem(str(tenant.id), DEFAULT_OWNER_PHONE, reply)
            
            # Log message
            log = LogMensagem(
                id=uuid.uuid4(),
                tenant_id=tenant.id,
                cliente_whatsapp=DEFAULT_OWNER_PHONE,
                direcao="saida",
                mensagem=reply,
                tipo="texto"
            )
            db.add(log)
            await db.commit()
            return {"status": "blocked", "days_overdue": days_overdue}
        else:
            # Send friendly warning reminder
            payment_link = payment.get("invoiceUrl") or "https://asaas.com/pay"
            reply = (
                f"⚠️ *AVISO de Mensalidade Atrasada* ⚠️\n\n"
                f"Olá! Notamos que sua mensalidade está vencida. Evite o bloqueio dos serviços do WhatsApp (que ocorrerá após 5 dias de atraso).\n\n"
                f"Efetue o pagamento:\n"
                f"🔗 Link de pagamento: {payment_link}"
            )
            await enviar_mensagem(str(tenant.id), DEFAULT_OWNER_PHONE, reply)
            await db.commit()
            return {"status": "warning_sent", "days_overdue": days_overdue}
            
    elif event == "payment.received":
        # Reactivate system
        tenant.sistema_ativo = True
        await db.flush()
        
        # Send confirmation to owner
        reply = (
            f"✅ *SISTEMA REATIVADO* ✅\n\n"
            f"Obrigado! Identificamos o pagamento da sua mensalidade.\n"
            f"O sistema de automação e o dashboard foram reativados com sucesso. Ótimos negócios! 🚀"
        )
        await enviar_mensagem(str(tenant.id), DEFAULT_OWNER_PHONE, reply)
        
        log = LogMensagem(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            cliente_whatsapp=DEFAULT_OWNER_PHONE,
            direcao="saida",
            mensagem=reply,
            tipo="texto"
        )
        db.add(log)
        await db.commit()
        return {"status": "reactivated"}
        
    await db.commit()
    return {"status": "ignored", "reason": "unhandled_event"}
