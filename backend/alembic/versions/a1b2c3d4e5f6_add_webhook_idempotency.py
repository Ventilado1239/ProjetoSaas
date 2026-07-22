"""add webhook idempotency

Revision ID: a1b2c3d4e5f6
Revises: f0a1b2c3d4e5
"""
import os
import re
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "f0a1b2c3d4e5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "webhook_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(length=30), nullable=False),
        sa.Column("event_id", sa.String(length=255), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=True),
        sa.Column("recebido_em", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "event_id", name="uq_webhook_provider_event"),
    )
    op.execute("REVOKE ALL ON webhook_events FROM PUBLIC;")
    app_role = os.getenv("DATABASE_APP_ROLE", "saas_app_user")
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", app_role):
        raise ValueError("DATABASE_APP_ROLE invalido")
    op.execute(f"""
        DO $$ BEGIN
          IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{app_role}') THEN
            EXECUTE 'GRANT SELECT, INSERT, DELETE ON webhook_events TO {app_role}';
          END IF;
        END $$;
    """)


def downgrade() -> None:
    op.drop_table("webhook_events")
