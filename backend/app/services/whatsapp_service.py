import asyncio
import random
import logging
from typing import List, Dict, Any, Optional
import httpx
from app.config import settings

logger = logging.getLogger(__name__)

# In-memory database to store sent messages for testing purposes
SENT_MESSAGES: List[Dict[str, Any]] = []

# Global flag to enable/disable typing delay (disabled during automated tests)
SIMULATE_DELAY = True

# Global shared client to reuse connections and prevent socket exhaustion
http_client = httpx.AsyncClient()

def clear_sent_messages():
    """Clears the history of sent messages (used for unit testing)."""
    global SENT_MESSAGES
    SENT_MESSAGES.clear()

async def enviar_mensagem(tenant_id: str, numero: str, mensagem: str) -> bool:
    """
    Sends a message to a WhatsApp number with human behavior simulation:
    - Triggers composing/typing presence.
    - Waits random delay of 3 to 8 seconds.
    - Posts the text payload to Evolution API or mocks if not configured.
    """
    # Sanitize number to remove non-numeric chars (expecting format like 5511999999999)
    number_clean = "".join(filter(str.isdigit, numero))
    if not number_clean:
        logger.error(f"Número inválido para envio: {numero}")
        return False

    instance_name = f"saas_tenant_{tenant_id}"
    
    # 1. Comportamento Humano: Typing delay
    delay = random.randint(3, 8) if SIMULATE_DELAY else 0
    logger.info(f"Simulando digitação para {number_clean} (delay de {delay}s)...")

    # Record message locally for testing inspection
    SENT_MESSAGES.append({
        "tenant_id": tenant_id,
        "numero": number_clean,
        "mensagem": mensagem,
        "delay": delay
    })

    # If API is not configured, run in mock mode
    if not settings.EVOLUTION_API_URL or not settings.EVOLUTION_API_KEY:
        logger.info(f"[MOCK WHATSAPP] Enviado para {number_clean} no tenant {tenant_id}: {mensagem}")
        if delay > 0:
            await asyncio.sleep(delay)
        return True

    # 2. Trigger typing presence on Evolution API (graceful fallback if it fails)
    if delay > 0:
        try:
            presence_url = f"{settings.EVOLUTION_API_URL.rstrip('/')}/chat/sendPresence/{instance_name}"
            headers = {
                "apikey": settings.EVOLUTION_API_KEY,
                "Content-Type": "application/json"
            }
            presence_data = {
                "number": number_clean,
                "presence": "composing",
                "delay": delay * 1000
            }
            
            await http_client.post(presence_url, headers=headers, json=presence_data, timeout=5.0)
        except Exception as e:
            logger.warning(f"Erro ao disparar presença no WhatsApp: {e}")

        # Wait out the typing delay
        await asyncio.sleep(delay)

    # 3. Send text message
    try:
        send_url = f"{settings.EVOLUTION_API_URL.rstrip('/')}/message/sendText/{instance_name}"
        headers = {
            "apikey": settings.EVOLUTION_API_KEY,
            "Content-Type": "application/json"
        }
        send_data = {
            "number": number_clean,
            "text": mensagem,
            "delay": 1200,
            "linkPreview": True
        }
        
        await http_client.post(send_url, headers=headers, json=send_data, timeout=10.0)
            
        logger.info(f"Mensagem enviada com sucesso para {number_clean} no tenant {tenant_id}")
        return True
    except Exception as e:
        logger.error(f"Erro ao enviar mensagem via Evolution API: {e}")
        return False

async def enviar_fila(lista_numeros: List[str], mensagem: str, tenant_id: str) -> List[bool]:
    """
    Sends a message to multiple numbers sequentially.
    Ensures safe interval of randint(30, 60) seconds between dispatches to mitigate spam detection.
    """
    results = []
    for idx, numero in enumerate(lista_numeros):
        if idx > 0:
            interval = random.randint(30, 60)
            logger.info(f"Aguardando {interval}s antes de enviar para o próximo número da fila...")
            await asyncio.sleep(interval)
        
        res = await enviar_mensagem(tenant_id, numero, mensagem)
        results.append(res)
        
    return results
