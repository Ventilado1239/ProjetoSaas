"""security and audit

Revision ID: f604faf735db
Revises: 6a1d267ec1fc
Create Date: 2026-06-03 10:48:14.485858

"""
from typing import Sequence, Union
import os

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f604faf735db'
down_revision: Union[str, Sequence[str], None] = '6a1d267ec1fc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Redefine set_tenant_id to be session-persistent (is_local=false) instead of transaction-local (is_local=true)
    # This prevents the context from being wiped on commit, which breaks subsequent refreshes/selects in RLS.
    op.execute("""
    CREATE OR REPLACE FUNCTION set_tenant_id(tenant_id_val uuid)
    RETURNS void AS $$
    BEGIN
      PERFORM set_config('app.tenant_id', COALESCE(tenant_id_val::text, ''), false);
    END;
    $$ LANGUAGE plpgsql SECURITY DEFINER;
    """)

    # 1. Enable pgcrypto extension (requires superuser privileges during execution, which pytest does)
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")

    # 2. Create logs_auditoria table
    op.create_table(
        'logs_auditoria',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('tenant_id', sa.Uuid(), nullable=False),
        sa.Column('usuario_id', sa.Uuid(), nullable=True),
        sa.Column('usuario_email', sa.String(length=255), nullable=True),
        sa.Column('acao', sa.String(length=50), nullable=False),
        sa.Column('tabela', sa.String(length=50), nullable=False),
        sa.Column('registro_id', sa.Uuid(), nullable=False),
        sa.Column('valores_antigos', sa.String(length=4000), nullable=True),
        sa.Column('valores_novos', sa.String(length=4000), nullable=True),
        sa.Column('criado_em', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )

    # 3. Enable RLS on logs_auditoria
    op.execute("ALTER TABLE logs_auditoria ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE logs_auditoria FORCE ROW LEVEL SECURITY;")
    op.execute("""
    CREATE POLICY tenant_isolation_policy ON logs_auditoria
      USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
    """)

    # 4. Convert fields to bytea using pgp_sym_encrypt
    key = os.getenv("JWT_SECRET", "8e6b12a7eb8c9d0d3f23a9d18e47bf923a1a1f0a1c6a2e4b8a2e1d7a9c8f6e2b")
    
    # Cast/encrypt nome
    op.execute(f"ALTER TABLE clientes_pacientes ALTER COLUMN nome TYPE bytea USING pgp_sym_encrypt(nome, '{key}');")
    
    # Cast/encrypt convenio (only if not null)
    op.execute(f"ALTER TABLE clientes_pacientes ALTER COLUMN convenio TYPE bytea USING CASE WHEN convenio IS NOT NULL THEN pgp_sym_encrypt(convenio, '{key}') ELSE NULL END;")


def downgrade() -> None:
    """Downgrade schema."""
    key = os.getenv("JWT_SECRET", "8e6b12a7eb8c9d0d3f23a9d18e47bf923a1a1f0a1c6a2e4b8a2e1d7a9c8f6e2b")
    
    # 1. Cast/decrypt convenio back to varchar(100)
    op.execute(f"ALTER TABLE clientes_pacientes ALTER COLUMN convenio TYPE varchar(100) USING CASE WHEN convenio IS NOT NULL THEN pgp_sym_decrypt(convenio, '{key}') ELSE NULL END;")
    
    # 2. Cast/decrypt nome back to varchar(255)
    op.execute(f"ALTER TABLE clientes_pacientes ALTER COLUMN nome TYPE varchar(255) USING pgp_sym_decrypt(nome, '{key}');")

    # 3. Drop RLS policy and table
    op.execute("DROP POLICY IF EXISTS tenant_isolation_policy ON logs_auditoria;")
    op.execute("ALTER TABLE logs_auditoria NO FORCE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE logs_auditoria DISABLE ROW LEVEL SECURITY;")
    op.drop_table('logs_auditoria')

    # Revert set_tenant_id to transaction-local (is_local=true)
    op.execute("""
    CREATE OR REPLACE FUNCTION set_tenant_id(tenant_id_val uuid)
    RETURNS void AS $$
    BEGIN
      PERFORM set_config('app.tenant_id', tenant_id_val::text, true);
    END;
    $$ LANGUAGE plpgsql SECURITY DEFINER;
    """)
