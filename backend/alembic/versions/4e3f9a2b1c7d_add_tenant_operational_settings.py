"""add tenant operational settings

Revision ID: 4e3f9a2b1c7d
Revises: f604faf735db
Create Date: 2026-07-12 19:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "4e3f9a2b1c7d"
down_revision: Union[str, Sequence[str], None] = "f604faf735db"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("tenants", sa.Column("owner_whatsapp", sa.String(length=50), nullable=True))
    op.add_column("tenants", sa.Column("evolution_instance_name", sa.String(length=120), nullable=True))
    op.create_unique_constraint(
        "uq_tenants_evolution_instance_name",
        "tenants",
        ["evolution_instance_name"],
    )

    op.execute("UPDATE tenants SET owner_whatsapp = whatsapp_numero WHERE owner_whatsapp IS NULL")
    op.execute("""
        UPDATE tenants
        SET evolution_instance_name = 'saas_tenant_' || id::text
        WHERE evolution_instance_name IS NULL
    """)


def downgrade() -> None:
    op.drop_constraint("uq_tenants_evolution_instance_name", "tenants", type_="unique")
    op.drop_column("tenants", "evolution_instance_name")
    op.drop_column("tenants", "owner_whatsapp")
