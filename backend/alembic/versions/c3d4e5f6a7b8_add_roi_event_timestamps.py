"""add ROI event timestamps

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, Sequence[str], None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("clientes_pacientes", sa.Column("reativado_em", sa.DateTime(timezone=True), nullable=True))
    op.add_column("lista_espera", sa.Column("agendado_em", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_clientes_reativado_em", "clientes_pacientes", ["tenant_id", "reativado_em"])
    op.create_index("ix_lista_espera_agendado_em", "lista_espera", ["tenant_id", "agendado_em"])


def downgrade() -> None:
    op.drop_index("ix_lista_espera_agendado_em", table_name="lista_espera")
    op.drop_index("ix_clientes_reativado_em", table_name="clientes_pacientes")
    op.drop_column("lista_espera", "agendado_em")
    op.drop_column("clientes_pacientes", "reativado_em")
