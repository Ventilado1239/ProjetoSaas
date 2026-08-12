"""harden master table grants

Revision ID: c7d8e9f0a1b2
Revises: b1c2d3e4f5a6
"""
import os
import re
from typing import Sequence, Union

from alembic import op

revision: str = "c7d8e9f0a1b2"
down_revision: Union[str, Sequence[str], None] = "b1c2d3e4f5a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("REVOKE ALL ON master_admins FROM PUBLIC;")
    op.execute("REVOKE ALL ON master_leads FROM PUBLIC;")
    app_role = os.getenv("DATABASE_APP_ROLE", "saas_app_user")
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", app_role):
        raise ValueError("DATABASE_APP_ROLE invalido")
    op.execute(f"""
        DO $$ BEGIN
          IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{app_role}') THEN
            EXECUTE 'GRANT SELECT, INSERT, UPDATE, DELETE ON master_admins, master_leads TO {app_role}';
          END IF;
        END $$;
    """)


def downgrade() -> None:
    # Security hardening is intentionally not reversed to PUBLIC access.
    pass
