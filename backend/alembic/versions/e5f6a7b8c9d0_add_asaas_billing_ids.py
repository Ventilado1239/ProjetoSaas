"""add Asaas billing identifiers

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, Sequence[str], None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("tenants", sa.Column("asaas_customer_id", sa.String(length=64), nullable=True))
    op.add_column("tenants", sa.Column("asaas_subscription_id", sa.String(length=64), nullable=True))
    op.create_unique_constraint("uq_tenants_asaas_customer_id", "tenants", ["asaas_customer_id"])
    op.create_unique_constraint("uq_tenants_asaas_subscription_id", "tenants", ["asaas_subscription_id"])


def downgrade() -> None:
    op.drop_constraint("uq_tenants_asaas_subscription_id", "tenants", type_="unique")
    op.drop_constraint("uq_tenants_asaas_customer_id", "tenants", type_="unique")
    op.drop_column("tenants", "asaas_subscription_id")
    op.drop_column("tenants", "asaas_customer_id")
