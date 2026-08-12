import logging
from typing import Any, Optional

import httpx

from app.config import settings


logger = logging.getLogger(__name__)
http_client = httpx.AsyncClient()


class AsaasAPIError(RuntimeError):
    pass


def ensure_billing_enabled() -> None:
    if not settings.ASAAS_BILLING_ENABLED or not settings.ASAAS_API_KEY:
        raise AsaasAPIError("Cobranca automatica do Asaas nao configurada.")


async def close_http_client() -> None:
    await http_client.aclose()


async def _request(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    ensure_billing_enabled()
    url = f"{settings.ASAAS_API_URL.rstrip('/')}/{path.lstrip('/')}"
    headers = {
        "access_token": settings.ASAAS_API_KEY,
        "Content-Type": "application/json",
        "User-Agent": "ProjetoSaaS/1.0",
    }
    try:
        response = await http_client.post(url, headers=headers, json=payload, timeout=15.0)
        response.raise_for_status()
        data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.exception("Falha segura na comunicacao com o Asaas", extra={"path": path})
        raise AsaasAPIError("O Asaas recusou ou nao respondeu a operacao.") from exc
    if not isinstance(data, dict) or not data.get("id"):
        raise AsaasAPIError("Resposta inesperada do Asaas.")
    return data


async def create_customer(
    *,
    tenant_id: str,
    name: str,
    cpf_cnpj: str,
    email: Optional[str],
    mobile_phone: str,
) -> dict[str, Any]:
    payload = {
        "name": name,
        "cpfCnpj": "".join(ch for ch in cpf_cnpj if ch.isdigit()),
        "email": email,
        "mobilePhone": "".join(ch for ch in mobile_phone if ch.isdigit()),
        "externalReference": tenant_id,
        "notificationDisabled": False,
    }
    return await _request("customers", {key: value for key, value in payload.items() if value})


async def create_subscription(
    *,
    tenant_id: str,
    customer_id: str,
    value: float,
    next_due_date: str,
    billing_type: str,
    cycle: str,
    description: str,
) -> dict[str, Any]:
    return await _request("subscriptions", {
        "customer": customer_id,
        "billingType": billing_type,
        "value": value,
        "nextDueDate": next_due_date,
        "cycle": cycle,
        "description": description,
        "externalReference": tenant_id,
    })
