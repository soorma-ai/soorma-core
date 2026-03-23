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
down_revision = "007_user_plan_fkeys"
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

# Tables where user_id was a UUID FK to users.id (6 tables — NOT semantic_memory, NOT plan_context)
_UUID_USER_FK_TABLES = [
    "episodic_memory",
    "procedural_memory",
    "working_memory",
    "task_context",
    "plans",
    "sessions",
]

# Tables that had tenant_id FK but NO user_id column
_TENANT_ONLY_FK_TABLES = [
    "plan_context",
]


def upgrade() -> None:
    conn = op.get_bind()

    # ─────────────────────────────────────────────────────────────────────────
    # Step 1: Drop all existing RLS policies on all 8 tables
    # (Old policies use ::UUID cast which is invalid after migration)
    # Policy names are the actual names created by prior migrations.
    # ─────────────────────────────────────────────────────────────────────────
    _existing_policies = {
        # policy name → table name
        "semantic_memory_read_policy":       "semantic_memory",
        "semantic_memory_write_policy":      "semantic_memory",
        "semantic_memory_update_policy":     "semantic_memory",
        "user_agent_isolation":              "episodic_memory",
        "procedural_isolation":              "procedural_memory",
        "working_memory_user_isolation":     "working_memory",
        "task_context_isolation":            "task_context",
        "plan_context_isolation":            "plan_context",
        "sessions_isolation":                "sessions",
        "plans_isolation":                   "plans",
    }
    for policy, table in _existing_policies.items():
        conn.execute(sa.text(f"DROP POLICY IF EXISTS {policy} ON {table}"))

    # Belt-and-suspenders: also drop any generic-named policies that may exist
    for table in _ALL_8_TABLES:
        conn.execute(sa.text(f"DROP POLICY IF EXISTS {table}_tenant_isolation ON {table}"))
        conn.execute(sa.text(f"DROP POLICY IF EXISTS {table}_rls_policy ON {table}"))
        conn.execute(sa.text(f"DROP POLICY IF EXISTS {table}_platform_rls ON {table}"))

    # Disable RLS before schema changes
    for table in _ALL_8_TABLES:
        conn.execute(sa.text(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY"))

    # ─────────────────────────────────────────────────────────────────────────
    # Step 2: Drop FK constraints referencing tenants.id and users.id
    # ─────────────────────────────────────────────────────────────────────────
    for table in _ALL_8_TABLES:
        conn.execute(sa.text(f"ALTER TABLE {table} DROP CONSTRAINT IF EXISTS {table}_tenant_id_fkey"))
    for table in _UUID_USER_FK_TABLES:
        conn.execute(sa.text(f"ALTER TABLE {table} DROP CONSTRAINT IF EXISTS {table}_user_id_fkey"))
    # plan_context has no user_id FK — only the tenant_id FK was dropped above

    # Drop plan_context.plan_id FK to plans.id (Step 9 prerequisite)
    # Constraint was named 'fk_plan_context_plan_id' by migration 007.
    conn.execute(sa.text("ALTER TABLE plan_context DROP CONSTRAINT IF EXISTS fk_plan_context_plan_id"))
    conn.execute(sa.text("ALTER TABLE plan_context DROP CONSTRAINT IF EXISTS plan_context_plan_id_fkey"))  # belt-and-suspenders

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
    # Step 6: Migrate existing UUID FK data
    # 6a. Tables with both tenant_id + user_id FK columns (6 tables)
    # ─────────────────────────────────────────────────────────────────────────
    for table in _UUID_USER_FK_TABLES:
        conn.execute(sa.text(
            f"UPDATE {table} SET "
            f"service_tenant_id = tenant_id::text, "
            f"service_user_id = user_id::text"
        ))

    # 6b. Tables with only tenant_id FK (plan_context — no user_id column)
    for table in _TENANT_ONLY_FK_TABLES:
        conn.execute(sa.text(
            f"UPDATE {table} SET service_tenant_id = tenant_id::text"
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
    # CASCADE handles any remaining dependent objects (e.g. stale policies)
    # ─────────────────────────────────────────────────────────────────────────
    for table in _ALL_8_TABLES:
        conn.execute(sa.text(f"ALTER TABLE {table} DROP COLUMN IF EXISTS tenant_id CASCADE"))
        conn.execute(sa.text(f"ALTER TABLE {table} DROP COLUMN IF EXISTS user_id CASCADE"))

    # ─────────────────────────────────────────────────────────────────────────
    # Step 9: Convert plan_context.plan_id from UUID to String(100)
    # (FK already dropped in Step 2)
    # ─────────────────────────────────────────────────────────────────────────
    conn.execute(sa.text(
        "ALTER TABLE plan_context ALTER COLUMN plan_id TYPE VARCHAR(100) USING plan_id::text"
    ))

    # ─────────────────────────────────────────────────────────────────────────
    # Step 9b: Convert working_memory.plan_id from UUID to String(100)
    # The plan_key_unique constraint on (plan_id, key) must be dropped first.
    # ─────────────────────────────────────────────────────────────────────────
    conn.execute(sa.text("ALTER TABLE working_memory DROP CONSTRAINT IF EXISTS plan_key_unique"))
    conn.execute(sa.text(
        "ALTER TABLE working_memory ALTER COLUMN plan_id TYPE VARCHAR(100) USING plan_id::text"
    ))
    conn.execute(sa.text(
        "ALTER TABLE working_memory ADD CONSTRAINT plan_key_unique UNIQUE (plan_id, key)"
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

    # Recreate semantic_memory upsert indexes using three-column identity names
    # These indexes back ON CONFLICT targets in semantic CRUD operations.
    conn.execute(sa.text("DROP INDEX IF EXISTS semantic_memory_user_external_id_private_idx"))
    conn.execute(sa.text("DROP INDEX IF EXISTS semantic_memory_tenant_external_id_public_idx"))
    conn.execute(sa.text("DROP INDEX IF EXISTS semantic_memory_user_content_hash_private_idx"))
    conn.execute(sa.text("DROP INDEX IF EXISTS semantic_memory_tenant_content_hash_public_idx"))

    conn.execute(sa.text(
        "CREATE UNIQUE INDEX semantic_memory_user_external_id_private_idx "
        "ON semantic_memory (platform_tenant_id, service_user_id, external_id) "
        "WHERE external_id IS NOT NULL AND is_public = FALSE"
    ))
    conn.execute(sa.text(
        "CREATE UNIQUE INDEX semantic_memory_tenant_external_id_public_idx "
        "ON semantic_memory (platform_tenant_id, external_id) "
        "WHERE external_id IS NOT NULL AND is_public = TRUE"
    ))
    conn.execute(sa.text(
        "CREATE UNIQUE INDEX semantic_memory_user_content_hash_private_idx "
        "ON semantic_memory (platform_tenant_id, service_user_id, content_hash) "
        "WHERE is_public = FALSE"
    ))
    conn.execute(sa.text(
        "CREATE UNIQUE INDEX semantic_memory_tenant_content_hash_public_idx "
        "ON semantic_memory (platform_tenant_id, content_hash) "
        "WHERE is_public = TRUE"
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
