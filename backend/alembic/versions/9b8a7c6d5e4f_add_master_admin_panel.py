"""add master admin panel

Revision ID: 9b8a7c6d5e4f
Revises: 4e3f9a2b1c7d
Create Date: 2026-07-12 20:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "9b8a7c6d5e4f"
down_revision: Union[str, Sequence[str], None] = "4e3f9a2b1c7d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("tenants", sa.Column("responsavel_nome", sa.String(length=255), nullable=True))
    op.add_column("tenants", sa.Column("responsavel_email", sa.String(length=255), nullable=True))
    op.add_column("tenants", sa.Column("mensalidade", sa.Numeric(10, 2), nullable=True))
    op.add_column("tenants", sa.Column("pagamento_status", sa.String(length=50), nullable=False, server_default="em_dia"))
    op.add_column("tenants", sa.Column("crm_stage", sa.String(length=50), nullable=False, server_default="ativo"))
    op.add_column("tenants", sa.Column("proximo_vencimento", sa.Date(), nullable=True))
    op.add_column("tenants", sa.Column("observacoes", sa.String(length=2048), nullable=True))

    op.create_table(
        "master_admins",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("nome", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("senha_hash", sa.String(length=255), nullable=False),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )

    op.create_table(
        "master_leads",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("nome_clinica", sa.String(length=255), nullable=False),
        sa.Column("responsavel_nome", sa.String(length=255), nullable=True),
        sa.Column("responsavel_email", sa.String(length=255), nullable=True),
        sa.Column("whatsapp", sa.String(length=50), nullable=True),
        sa.Column("etapa", sa.String(length=50), nullable=False, server_default="lead"),
        sa.Column("valor_potencial", sa.Numeric(10, 2), nullable=True),
        sa.Column("proxima_acao", sa.String(length=255), nullable=True),
        sa.Column("observacoes", sa.String(length=2048), nullable=True),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("master_leads")
    op.drop_table("master_admins")
    op.drop_column("tenants", "observacoes")
    op.drop_column("tenants", "proximo_vencimento")
    op.drop_column("tenants", "crm_stage")
    op.drop_column("tenants", "pagamento_status")
    op.drop_column("tenants", "mensalidade")
    op.drop_column("tenants", "responsavel_email")
    op.drop_column("tenants", "responsavel_nome")
