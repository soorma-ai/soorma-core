"""Multi-tenancy three-column identity migration for Memory Service.

Transforms all 8 memory tables from two-column UUID FK identity
(tenant_id UUID FK → tenants, user_id UUID FK → users) to three-column
opaque-string identity (platform_tenant_id, service_tenant_id, service_user_id
as VARCHAR(64) plain columns, no FK constraints).

Reference tables tenants and users are dropped.
RLS policies are rebuilt using string comparison (no ::UUID cast).

WARNING: downgrade() is DATA-DESTRUCTIVE — original UUID values cannot be
recovered from VARCHAR string representations after the upgrade.
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None

DEFAULT_PLATFORM_TENANT_ID = "spt_00000000-0000-0000-0000-000000000000"

# All 8 tables that get the three-column identity migration
_ALL_8_TABLES = [
    "semantic_memory",
    "episodic_memory",
    "procedural_memory",
    "working_memory",
    "task_context",
    "plan_context",
    "plans",
    "sessions",
]

# Tables where user_id was a UUID FK to users.id (7 tables — NOT semantic_memory)
_UUID_USER_FK_TABLES = [
    "episodic_memory",
    "procedural_memory",
    "working_memory",
    "task_context",
    "plan_context",
    "plans",
    "sessions",
]


def upgrade() -> None:
    conn = op.get_bind()

    # ─────────────────────────────────────────────────────────────────────────
    # Step 1: Drop all existing RLS policies on all 8 tables
    # (Old policies use ::UUID cast which is invalid after migration)
    # ─────────────────────────────────────────────────────────────────────────
    for table in _ALL_8_TABLES:
        conn.execute(sa.text(f"DROP POLICY IF EXISTS {table}_tenant_isolation ON {table}"))
        conn.execute(sa.text(f"DROP POLICY IF EXISTS {table}_rls_policy ON {table}"))
        conn.execute(sa.text(f"DROP POLICY IF EXISTS {table}_platform_rls ON {table}"))
        # Disable RLS before schema changes
        conn.execute(sa.text(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY"))

    # ─────────────────────────────────────────────────────────────────────────
    # Step 2: Drop FK constraints referencing tenants.id and users.id
    # ─────────────────────────────────────────────────────────────────────────
    for table in _ALL_8_TABLES:
        conn.execute(sa.text(f"ALTER TABLE {table} DROP CONSTRAINT IF EXISTS {table}_tenant_id_fkey"))
    for table in _UUID_USER_FK_TABLES:
        conn.execute(sa.text(f"ALTER TABLE {table} DROP CONSTRAINT IF EXISTS {table}_user_id_fkey"))

    # Drop plan_context.plan_id FK to plans.id (Step 9 prerequisite)
    conn.execute(sa.text("ALTER TABLE plan_context DROP CONSTRAINT IF EXISTS plan_context_plan_id_fkey"))

    # ─────────────────────────────────────────────────────────────────────────
    # Step 3: Add platform_tenant_id VARCHAR(64) NOT NULL with default
    # ─────────────────────────────────────────────────────────────────────────
    for table in _ALL_8_TABLES:
        conn.execute(sa.text(
            f"ALTER TABLE {table} ADD COLUMN platform_tenant_id VARCHAR(64) "
            f"NOT NULL DEFAULT '{DEFAULT_PLATFORM_TENANT_ID}'"
        ))

    # ─────────────────────────────────────────────────────────────────────────
    # Step 4: Add service_tenant_id VARCHAR(64) NULL
    # ─────────────────────────────────────────────────────────────────────────
    for table in _ALL_8_TABLES:
        conn.execute(sa.text(
            f"ALTER TABLE {table} ADD COLUMN service_tenant_id VARCHAR(64) NULL"
        ))

    # ─────────────────────────────────────────────────────────────────────────
    # Step 5: Add service_user_id VARCHAR(64) NULL
    # ─────────────────────────────────────────────────────────────────────────
    for table in _ALL_8_TABLES:
        conn.execute(sa.text(
            f"ALTER TABLE {table} ADD COLUMN service_user_id VARCHAR(64) NULL"
        ))

    # ─────────────────────────────────────────────────────────────────────────
    # Step 6: Migrate existing UUID FK data — 7 tables (UUID cast to text)
    # tenant_id::text → service_tenant_id
    # user_id::text   → service_user_id
    # ─────────────────────────────────────────────────────────────────────────
    for table in _UUID_USER_FK_TABLES:
        conn.execute(sa.text(
            f"UPDATE {table} SET "
            f"service_tenant_id = tenant_id::text, "
            f"service_user_id = user_id::text"
        ))

    # ─────────────────────────────────────────────────────────────────────────
    # Step 7: semantic_memory — user_id was String(255), not a UUID FK
    # Rename/migrate: truncate to 64 chars to fit VARCHAR(64)
    # Add new service_user_id from user_id (cast text, truncate)
    # Also migrate tenant_id FK to service_tenant_id
    # ─────────────────────────────────────────────────────────────────────────
    conn.execute(sa.text(
        "UPDATE semantic_memory SET "
        "service_tenant_id = tenant_id::text, "
        "service_user_id = LEFT(user_id, 64)"
    ))

    # ─────────────────────────────────────────────────────────────────────────
    # Step 8: Drop old tenant_id and user_id columns from all 8 tables
    # ─────────────────────────────────────────────────────────────────────────
    for table in _ALL_8_TABLES:
        conn.execute(sa.text(f"ALTER TABLE {table} DROP COLUMN IF EXISTS tenant_id"))
        conn.execute(sa.text(f"ALTER TABLE {table} DROP COLUMN IF EXISTS user_id"))

    # ─────────────────────────────────────────────────────────────────────────
    # Step 9: Convert plan_context.plan_id from UUID to String(100)
    # (FK already dropped in Step 2)
    # ─────────────────────────────────────────────────────────────────────────
    conn.execute(sa.text(
        "ALTER TABLE plan_context ALTER COLUMN plan_id TYPE VARCHAR(100) USING plan_id::text"
    ))

    # ─────────────────────────────────────────────────────────────────────────
    # Step 10: Drop tenants table
    # ─────────────────────────────────────────────────────────────────────────
    conn.execute(sa.text("DROP TABLE IF EXISTS tenants CASCADE"))

    # ─────────────────────────────────────────────────────────────────────────
    # Step 11: Drop users table
    # ─────────────────────────────────────────────────────────────────────────
    conn.execute(sa.text("DROP TABLE IF EXISTS users CASCADE"))

    # ─────────────────────────────────────────────────────────────────────────
    # Step 12: Update unique constraints
    # ─────────────────────────────────────────────────────────────────────────

    # task_context: (tenant_id, task_id) → (platform_tenant_id, task_id)
    conn.execute(sa.text("ALTER TABLE task_context DROP CONSTRAINT IF EXISTS task_context_unique"))
    conn.execute(sa.text(
        "ALTER TABLE task_context ADD CONSTRAINT task_context_unique "
        "UNIQUE (platform_tenant_id, task_id)"
    ))

    # plans: (tenant_id, plan_id) → (platform_tenant_id, plan_id)
    conn.execute(sa.text("ALTER TABLE plans DROP CONSTRAINT IF EXISTS plan_unique"))
    conn.execute(sa.text(
        "ALTER TABLE plans ADD CONSTRAINT plan_unique "
        "UNIQUE (platform_tenant_id, plan_id)"
    ))

    # sessions: need unique on (platform_tenant_id, session_id)
    conn.execute(sa.text("ALTER TABLE sessions DROP CONSTRAINT IF EXISTS sessions_session_id_key"))
    conn.execute(sa.text("ALTER TABLE sessions DROP CONSTRAINT IF EXISTS sessions_unique"))
    conn.execute(sa.text(
        "ALTER TABLE sessions ADD CONSTRAINT sessions_unique "
        "UNIQUE (platform_tenant_id, session_id)"
    ))

    # Remove default on platform_tenant_id now that data migration is complete
    # (DEFAULT was only needed to handle pre-existing rows)
    for table in _ALL_8_TABLES:
        conn.execute(sa.text(
            f"ALTER TABLE {table} ALTER COLUMN platform_tenant_id DROP DEFAULT"
        ))

    # ─────────────────────────────────────────────────────────────────────────
    # Step 13: Rebuild RLS policies using string comparison (no ::UUID cast)
    # ─────────────────────────────────────────────────────────────────────────
    for table in _ALL_8_TABLES:
        conn.execute(sa.text(f"""
            CREATE POLICY {table}_platform_rls
              ON {table}
              USING (
                platform_tenant_id = current_setting('app.platform_tenant_id', true)
              )
        """))

    # ─────────────────────────────────────────────────────────────────────────
    # Step 14: Enable RLS + FORCE ROW LEVEL SECURITY on all 8 tables
    # FORCE ensures table OWNER (superuser) also goes through policy evaluation
    # ─────────────────────────────────────────────────────────────────────────
    for table in _ALL_8_TABLES:
        conn.execute(sa.text(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY"))
        conn.execute(sa.text(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY"))


def downgrade() -> None:
    """Reverse the three-column identity migration.

    WARNING: DATA-DESTRUCTIVE. The original UUID values for tenant_id and
    user_id cannot be recovered from the VARCHAR string representations.
    Downgraded tenant_id and user_id columns will be NULL for all rows.
    This downgrade is provided for schema compatibility only.
    """
    conn = op.get_bind()

    # Disable and drop new RLS policies
    for table in _ALL_8_TABLES:
        conn.execute(sa.text(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY"))
        conn.execute(sa.text(f"DROP POLICY IF EXISTS {table}_platform_rls ON {table}"))

    # Recreate tenants and users tables (minimal schema — no data)
    conn.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS tenants (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name TEXT NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT NOW()
        )
    """))
    conn.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS users (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            username TEXT NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT NOW()
        )
    """))

    # Drop new unique constraints
    conn.execute(sa.text("ALTER TABLE task_context DROP CONSTRAINT IF EXISTS task_context_unique"))
    conn.execute(sa.text("ALTER TABLE plans DROP CONSTRAINT IF EXISTS plan_unique"))
    conn.execute(sa.text("ALTER TABLE sessions DROP CONSTRAINT IF EXISTS sessions_unique"))

    # Revert plan_context.plan_id back to UUID (NULL — data cannot be recovered)
    conn.execute(sa.text(
        "ALTER TABLE plan_context ALTER COLUMN plan_id TYPE UUID USING NULL"
    ))

    # Drop new columns and add back old UUID FK columns (NULL)
    for table in _ALL_8_TABLES:
        conn.execute(sa.text(f"ALTER TABLE {table} DROP COLUMN IF EXISTS platform_tenant_id"))
        conn.execute(sa.text(f"ALTER TABLE {table} DROP COLUMN IF EXISTS service_tenant_id"))
        conn.execute(sa.text(f"ALTER TABLE {table} DROP COLUMN IF EXISTS service_user_id"))
        conn.execute(sa.text(
            f"ALTER TABLE {table} ADD COLUMN tenant_id UUID "
            f"REFERENCES tenants(id) ON DELETE CASCADE"
        ))
    for table in _UUID_USER_FK_TABLES:
        conn.execute(sa.text(
            f"ALTER TABLE {table} ADD COLUMN user_id UUID "
            f"REFERENCES users(id) ON DELETE CASCADE"
        ))

    # semantic_memory: add back user_id as String(255)
    conn.execute(sa.text("ALTER TABLE semantic_memory ADD COLUMN user_id VARCHAR(255)"))
