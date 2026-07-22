import logging
import uuid
import hmac
import json
from typing import Optional
from zoneinfo import ZoneInfo
from datetime import datetime

from fastapi import APIRouter, Depends, BackgroundTasks, Header, HTTPException, Request, status
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.database import get_db, AsyncSessionLocal
from app.config import settings
from app.models.models import Tenant, LogMensagem, WebhookEvent
from app.services import fluxo_service
from app.services.tenant_settings import get_evolution_instance_name
from app.services.whatsapp_service import enviar_mensagem
from app.utils.mensagens import get_message

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])
MAX_WEBHOOK_BYTES = 1_000_000

def is_outside_working_hours(tenant: Tenant) -> bool:
    """Checks if the current Brasilia time is outside the tenant's configured working hours."""
    try:
        tz = ZoneInfo("America/Sao_Paulo")
        now = datetime.now(tz)
        current_time_str = now.strftime("%H:%M")
        
        # Simple string comparison works for "HH:MM" format
        return current_time_str < tenant.horario_abertura or current_time_str > tenant.horario_fechamento
    except Exception as e:
        logger.error(f"Erro ao verificar horário de funcionamento: {e}")
        # Default to False to allow message processing if timezone logic fails
        return False

async def processar_webhook_async(
    tenant_id: uuid.UUID,
    client_phone: str,
    message_text: str,
    message_type: str,
    push_name: str
):
    """Asynchronously processes the message in a background task under the correct RLS context."""
    async with AsyncSessionLocal() as db:
        try:
            # 1. Enforce tenant context in the connection session
            await db.execute(
                text("SELECT set_tenant_id(:tenant_id)"),
                {"tenant_id": tenant_id}
            )

            # 2. Fetch the tenant configuration
            tenant = await db.get(Tenant, tenant_id)
            if not tenant:
                logger.error(f"Tenant {tenant_id} não encontrado no banco de dados.")
                return

            # 3. Check system status (Kill Switch)
            if not tenant.sistema_ativo:
                logger.warning(f"Tenant {tenant.nome} inativo. Enviando mensagem de indisponibilidade.")
                reply = "Serviço temporariamente indisponível."
                await enviar_mensagem(
                    str(tenant.id),
                    client_phone,
                    reply,
                    instance_name=get_evolution_instance_name(tenant.id, tenant),
                )
                return

            # 4. Check working hours (Fluxo 7)
            if is_outside_working_hours(tenant):
                # Log incoming message first
                log_in = LogMensagem(
                    id=uuid.uuid4(),
                    tenant_id=tenant.id,
                    cliente_whatsapp=client_phone,
                    direcao="entrada",
                    mensagem=message_text or f"[{message_type.upper()}]",
                    tipo=message_type
                )
                db.add(log_in)
                await db.flush()

                # Send out of office notification
                reply = get_message(
                    "out_of_hours",
                    horario_abertura=tenant.horario_abertura,
                    horario_fechamento=tenant.horario_fechamento
                )
                
                await enviar_mensagem(
                    str(tenant.id),
                    client_phone,
                    reply,
                    instance_name=get_evolution_instance_name(tenant.id, tenant),
                )
                
                # Log outgoing message
                log_out = LogMensagem(
                    id=uuid.uuid4(),
                    tenant_id=tenant.id,
                    cliente_whatsapp=client_phone,
                    direcao="saida",
                    mensagem=reply,
                    tipo="texto"
                )
                db.add(log_out)
                await db.commit()
                return

            # 5. Log incoming message
            log_in = LogMensagem(
                id=uuid.uuid4(),
                tenant_id=tenant.id,
                cliente_whatsapp=client_phone,
                direcao="entrada",
                mensagem=message_text or f"[{message_type.upper()}]",
                tipo=message_type
            )
            db.add(log_in)
            await db.flush()

            # 6. Execute conversation flow
            await fluxo_service.processar_mensagem(
                db=db,
                tenant=tenant,
                client_phone=client_phone,
                message_text=message_text,
                message_type=message_type,
                push_name=push_name
            )
            
            await db.commit()
            
        except Exception as e:
            logger.exception(f"Erro ao processar mensagem do WhatsApp em background: {e}")
            await db.rollback()

@router.post("/webhook")
async def receive_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    webhook_secret: Optional[str] = None,
    x_webhook_secret: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Webhook endpoint to receive incoming WhatsApp messages from Evolution API.
    Guarantees fast response (< 500ms) by processing business logic in a background task.
    """
    expected_secret = settings.EVOLUTION_WEBHOOK_SECRET
    if expected_secret:
        supplied_secret = x_webhook_secret or webhook_secret
        if not supplied_secret or not hmac.compare_digest(supplied_secret, expected_secret):
            raise HTTPException(status_code=401, detail="Webhook nao autorizado")

    try:
        raw_body = await request.body()
        if len(raw_body) > MAX_WEBHOOK_BYTES:
            raise HTTPException(status_code=413, detail="Payload muito grande")
        payload = json.loads(raw_body)
    except HTTPException:
        raise
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise HTTPException(status_code=400, detail="Payload JSON invalido")

    data = payload.get("data", {})
    key = data.get("key", {})
    from_me = key.get("fromMe", False)

    # 1. Ignore outbound messages sent by the bot to prevent loops
    if from_me:
        return {"status": "ignored", "reason": "sent_by_me"}

    # 2. Extract message type and sender info
    remote_jid = key.get("remoteJid", "")
    if not remote_jid or "@g.us" in remote_jid:
        # Ignore group messages and empty JIDs
        return {"status": "ignored", "reason": "group_or_empty_jid"}

    client_phone = "".join(char for char in remote_jid.split("@")[0] if char.isdigit())[:15]
    if not 10 <= len(client_phone) <= 15:
        return {"status": "ignored", "reason": "invalid_sender"}
    push_name = str(data.get("pushName") or "Cliente")[:255]

    # Extract message content
    message_obj = data.get("message", {})
    if not message_obj:
        return {"status": "ignored", "reason": "empty_message_object"}

    message_text = ""
    message_type = "texto"

    if "conversation" in message_obj:
        message_text = message_obj["conversation"]
    elif "extendedTextMessage" in message_obj:
        message_text = message_obj["extendedTextMessage"].get("text", "")
    elif "audioMessage" in message_obj:
        message_type = "audio"
    elif "imageMessage" in message_obj:
        message_type = "imagem"
    elif "documentMessage" in message_obj:
        message_type = "documento"
    else:
        # Fallback to general messageType
        msg_type_str = data.get("messageType", "")
        if msg_type_str in ["audioMessage", "audio"]:
            message_type = "audio"
        elif msg_type_str in ["imageMessage", "image"]:
            message_type = "imagem"
        elif msg_type_str in ["documentMessage", "document"]:
            message_type = "documento"
        else:
            message_type = "media"

    message_text = str(message_text)[:4000]

    # 3. Resolve tenant strictly from the authenticated Evolution instance.
    tenant_id = None
    instance_name = str(payload.get("instance", ""))[:120]
    if instance_name.startswith("saas_tenant_"):
        try:
            tenant_id = uuid.UUID(instance_name.removeprefix("saas_tenant_"))
        except ValueError:
            pass

    if not tenant_id and instance_name:
        await db.execute(text("SET LOCAL app.bypass_rls = 'true'"))
        tenant = (await db.execute(
            select(Tenant).where(Tenant.evolution_instance_name == instance_name)
        )).scalar_one_or_none()
        await db.execute(text("SET LOCAL app.bypass_rls = 'false'"))
        if tenant:
            tenant_id = tenant.id

    if not tenant_id:
        logger.warning("Mensagem ignorada: Não foi possível determinar o tenant_id.")
        return {"status": "ignored", "reason": "tenant_not_resolved"}

    raw_message_id = str(key.get("id", ""))
    if not raw_message_id:
        return {"status": "ignored", "reason": "missing_message_id"}
    message_id = f"{instance_name}:{raw_message_id}"[:255]
    inserted_event_id = await db.scalar(
        pg_insert(WebhookEvent)
        .values(id=uuid.uuid4(), provider="evolution", event_id=message_id, tenant_id=tenant_id)
        .on_conflict_do_nothing(constraint="uq_webhook_provider_event")
        .returning(WebhookEvent.id)
    )
    if not inserted_event_id:
        return {"status": "duplicate", "event_id": message_id}
    await db.commit()

    # 4. Dispatch async processing
    background_tasks.add_task(
        processar_webhook_async,
        tenant_id=tenant_id,
        client_phone=client_phone,
        message_text=message_text,
        message_type=message_type,
        push_name=push_name
    )

    # Immediately respond to webhook under 500ms
    return {"status": "processing"}
