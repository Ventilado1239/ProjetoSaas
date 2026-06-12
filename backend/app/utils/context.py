import contextvars
from typing import Optional
import uuid
from app.models.models import Usuario

current_user_var: contextvars.ContextVar[Optional[Usuario]] = contextvars.ContextVar("current_user", default=None)
tenant_id_var: contextvars.ContextVar[Optional[uuid.UUID]] = contextvars.ContextVar("tenant_id", default=None)
