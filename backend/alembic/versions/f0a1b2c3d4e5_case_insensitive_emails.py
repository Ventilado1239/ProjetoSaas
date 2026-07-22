"""case insensitive email uniqueness

Revision ID: f0a1b2c3d4e5
Revises: e9f0a1b2c3d4
"""
from typing import Sequence, Union

from alembic import op

revision: str = "f0a1b2c3d4e5"
down_revision: Union[str, Sequence[str], None] = "e9f0a1b2c3d4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("UPDATE usuarios SET email = lower(trim(email));")
    op.execute("UPDATE master_admins SET email = lower(trim(email));")
    op.execute("CREATE UNIQUE INDEX uq_usuarios_email_lower ON usuarios (lower(email));")
    op.execute("CREATE UNIQUE INDEX uq_master_admins_email_lower ON master_admins (lower(email));")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_master_admins_email_lower;")
    op.execute("DROP INDEX IF EXISTS uq_usuarios_email_lower;")
