"""add user token version

Revision ID: e9f0a1b2c3d4
Revises: d8e9f0a1b2c3
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "e9f0a1b2c3d4"
down_revision: Union[str, Sequence[str], None] = "d8e9f0a1b2c3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("usuarios", sa.Column("token_version", sa.Integer(), nullable=False, server_default="0"))


def downgrade() -> None:
    op.drop_column("usuarios", "token_version")
