"""grant application role access on fresh installations

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
"""
import os
import re
from typing import Sequence, Union

from alembic import op


revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, Sequence[str], None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


APPLICATION_TABLES = (
    "tenants",
    "usuarios",
    "clientes_pacientes",
    "servicos_produtos",
    "precos",
    "atendimentos_pedidos",
    "itens_atendimento",
    "lista_espera",
    "logs_mensagens",
    "configuracoes",
    "token_blacklist",
    "webhook_events",
    "estados_conversa",
    "aprovacoes",
    "logs_auditoria",
    "master_admins",
    "master_leads",
    "master_audit_logs",
)


def _application_role() -> str:
    role = os.getenv("DATABASE_APP_ROLE", "saas_app_user")
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", role):
        raise ValueError("DATABASE_APP_ROLE invalido")
    return role


def upgrade() -> None:
    role = _application_role()
    table_list = ", ".join(APPLICATION_TABLES)
    op.execute(f"REVOKE ALL ON {table_list} FROM PUBLIC")
    op.execute(f"GRANT USAGE ON SCHEMA public TO {role}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON {table_list} TO {role}")
    op.execute(f"GRANT EXECUTE ON FUNCTION set_tenant_id(uuid) TO {role}")


def downgrade() -> None:
    role = _application_role()
    table_list = ", ".join(APPLICATION_TABLES)
    op.execute(f"REVOKE SELECT, INSERT, UPDATE, DELETE ON {table_list} FROM {role}")
    op.execute(f"REVOKE EXECUTE ON FUNCTION set_tenant_id(uuid) FROM {role}")
