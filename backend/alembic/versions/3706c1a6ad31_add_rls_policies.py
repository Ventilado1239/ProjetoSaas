"""add_rls_policies

Revision ID: 3706c1a6ad31
Revises: 8263b8fa988a
Create Date: 2026-06-02 23:39:44.141565

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3706c1a6ad31'
down_revision: Union[str, Sequence[str], None] = '8263b8fa988a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create set_tenant_id function
    op.execute("""
    CREATE OR REPLACE FUNCTION set_tenant_id(tenant_id_val uuid)
    RETURNS void AS $$
    BEGIN
      PERFORM set_config('app.tenant_id', tenant_id_val::text, true);
    END;
    $$ LANGUAGE plpgsql SECURITY DEFINER;
    """)

    # List of tables to enable standard RLS on
    tables_with_tenant_id = [
        "clientes_pacientes",
        "servicos_produtos",
        "precos",
        "atendimentos_pedidos",
        "itens_atendimento",
        "lista_espera",
        "logs_mensagens",
        "configuracoes"
    ]

    # Enable RLS on tenants (uses 'id' column, supports bypass_rls for auth/webhook lookups)
    op.execute("ALTER TABLE tenants ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE tenants FORCE ROW LEVEL SECURITY;")
    op.execute("""
    CREATE POLICY tenant_isolation_policy ON tenants
      USING (id = NULLIF(current_setting('app.tenant_id', true), '')::uuid OR current_setting('app.bypass_rls', true) = 'true');
    """)

    # Enable RLS on usuarios (uses 'tenant_id' column, supports bypass_rls for login lookup)
    op.execute("ALTER TABLE usuarios ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE usuarios FORCE ROW LEVEL SECURITY;")
    op.execute("""
    CREATE POLICY tenant_isolation_policy ON usuarios
      USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid OR current_setting('app.bypass_rls', true) = 'true');
    """)

    # Enable RLS on other tables (uses 'tenant_id' column)
    for table in tables_with_tenant_id:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY;")
        op.execute(f"""
        CREATE POLICY tenant_isolation_policy ON {table}
          USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
        """)


def downgrade() -> None:
    tables_with_tenant_id = [
        "usuarios",
        "clientes_pacientes",
        "servicos_produtos",
        "precos",
        "atendimentos_pedidos",
        "itens_atendimento",
        "lista_espera",
        "logs_mensagens",
        "configuracoes"
    ]

    for table in tables_with_tenant_id:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation_policy ON {table};")
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY;")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;")

    op.execute("DROP POLICY IF EXISTS tenant_isolation_policy ON tenants;")
    op.execute("ALTER TABLE tenants NO FORCE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE tenants DISABLE ROW LEVEL SECURITY;")

    op.execute("DROP FUNCTION IF EXISTS set_tenant_id(uuid);")

