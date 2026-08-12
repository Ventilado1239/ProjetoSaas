import uuid
from typing import Optional

from app.models.models import Tenant


def get_owner_whatsapp(tenant: Tenant) -> str:
    """Return the operational owner WhatsApp for alerts and admin notifications."""
    owner_whatsapp = getattr(tenant, "owner_whatsapp", None)
    return owner_whatsapp or tenant.whatsapp_numero


def get_evolution_instance_name(tenant_id: uuid.UUID | str, tenant: Optional[Tenant] = None) -> str:
    """Return the Evolution API instance name associated with a tenant."""
    instance_name = getattr(tenant, "evolution_instance_name", None) if tenant else None
    return instance_name or f"saas_tenant_{tenant_id}"
