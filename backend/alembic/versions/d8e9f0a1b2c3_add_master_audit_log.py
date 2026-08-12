"""add master audit log

Revision ID: d8e9f0a1b2c3
Revises: c7d8e9f0a1b2
"""
import os
import re
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "d8e9f0a1b2c3"
down_revision: Union[str, Sequence[str], None] = "c7d8e9f0a1b2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("master_admins", sa.Column("ultimo_login_em", sa.DateTime(timezone=True), nullable=True))
    op.create_table(
        "master_audit_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("admin_id", sa.Uuid(), nullable=True),
        sa.Column("acao", sa.String(length=80), nullable=False),
        sa.Column("entidade", sa.String(length=80), nullable=False),
        sa.Column("entidade_id", sa.Uuid(), nullable=True),
        sa.Column("detalhes", sa.String(length=2048), nullable=True),
        sa.Column("ip_origem", sa.String(length=64), nullable=True),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["admin_id"], ["master_admins.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.execute("REVOKE ALL ON master_audit_logs FROM PUBLIC;")
    app_role = os.getenv("DATABASE_APP_ROLE", "saas_app_user")
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", app_role):
        raise ValueError("DATABASE_APP_ROLE invalido")
    op.execute(f"""
        DO $$ BEGIN
          IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{app_role}') THEN
            EXECUTE 'GRANT SELECT, INSERT ON master_audit_logs TO {app_role}';
          END IF;
        END $$;
    """)


def downgrade() -> None:
    op.drop_table("master_audit_logs")
    op.drop_column("master_admins", "ultimo_login_em")
