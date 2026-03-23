"""Rename tenant_id to platform_tenant_id (UUID -> VARCHAR(64))

Revision ID: 004_platform_tenant_id
Revises: 003_schema_registry
Create Date: 2026-03-24

This migration updates the multi-tenancy column across all registry tables:
- Renames tenant_id → platform_tenant_id on agents, events, payload_schemas
- Changes column type from UUID to VARCHAR(64) to support string-prefixed tenant IDs
  (e.g. "spt_00000000-0000-0000-0000-000000000000")
- Updates composite indexes and unique constraints to reference platform_tenant_id
- Drops old RLS policies (which used app.tenant_id with ::UUID cast)
- Creates new RLS policies using app.platform_tenant_id (plain string comparison)
- Adds FORCE ROW LEVEL SECURITY to all tenant-isolated tables

BREAKING CHANGES:
- agents.tenant_id column renamed to platform_tenant_id, type changed to VARCHAR(64)
- events.tenant_id column renamed to platform_tenant_id, type changed to VARCHAR(64)
- payload_schemas.tenant_id column renamed to platform_tenant_id, type changed to VARCHAR(64)
- Existing UUID values are preserved as their text representation during migration
  (e.g. "00000000-0000-0000-0000-000000000000") — backfill to spt_ prefix is separate

NOTE: downgrade() is intentionally a no-op. Reverting UUID <-> VARCHAR(64) would
corrupt data and is not supported in this migration sequence.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '004_platform_tenant_id'
down_revision: Union[str, Sequence[str], None] = '003_schema_registry'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Rename tenant_id → platform_tenant_id and update RLS policies on all tables.

    Processing order: agents → events → payload_schemas
    For each table:
    1. Drop unique index and composite indexes referencing tenant_id
    2. Drop old RLS policies (app.tenant_id with ::UUID cast)
    3. Rename column and change type UUID → VARCHAR(64)
    4. Recreate composite indexes with platform_tenant_id
    5. Recreate unique constraint with platform_tenant_id
    6. FORCE ROW LEVEL SECURITY
    7. Create new RLS policies (app.platform_tenant_id, plain string comparison)
    """

    # ── agents table ──────────────────────────────────────────────────────────

    # Drop unique index and composite indexes created in migration 003
    op.drop_index('uq_agents_agent_tenant', table_name='agents')
    op.drop_index('idx_agents_tenant_agent', table_name='agents')
    op.drop_index('idx_agents_tenant_name', table_name='agents')

    # Drop old RLS policies that reference app.tenant_id with ::UUID cast
    op.execute("DROP POLICY IF EXISTS agents_tenant_isolation ON agents")
    op.execute("DROP POLICY IF EXISTS agents_developer_write ON agents")

    # Rename column and change type UUID → VARCHAR(64)
    op.execute("ALTER TABLE agents RENAME COLUMN tenant_id TO platform_tenant_id")
    op.execute(
        "ALTER TABLE agents ALTER COLUMN platform_tenant_id "
        "TYPE VARCHAR(64) USING platform_tenant_id::text"
    )

    # Recreate composite indexes with platform_tenant_id
    op.create_index('idx_agents_tenant_agent', 'agents', ['platform_tenant_id', 'agent_id'])
    op.create_index('idx_agents_tenant_name', 'agents', ['platform_tenant_id', 'name'])

    # Recreate unique constraint with platform_tenant_id
    op.create_index('uq_agents_agent_tenant', 'agents', ['agent_id', 'platform_tenant_id'], unique=True)

    # Force RLS (prevents table owners from bypassing policies)
    op.execute("ALTER TABLE agents FORCE ROW LEVEL SECURITY")

    # New RLS policies using app.platform_tenant_id (plain string, no UUID cast)
    op.execute("""
        CREATE POLICY agents_tenant_isolation ON agents
            USING (platform_tenant_id = current_setting('app.platform_tenant_id', true))
    """)
    op.execute("""
        CREATE POLICY agents_developer_write ON agents
            FOR INSERT
            WITH CHECK (
                platform_tenant_id = current_setting('app.platform_tenant_id', true)
            )
    """)

    # ── events table ──────────────────────────────────────────────────────────

    # Drop unique index and composite indexes created in migration 003
    op.drop_index('uq_events_event_tenant', table_name='events')
    op.drop_index('idx_events_tenant_event', table_name='events')
    op.drop_index('idx_events_tenant_topic', table_name='events')

    # Drop old RLS policies that reference app.tenant_id with ::UUID cast
    op.execute("DROP POLICY IF EXISTS events_tenant_isolation ON events")
    op.execute("DROP POLICY IF EXISTS events_developer_write ON events")

    # Rename column and change type UUID → VARCHAR(64)
    op.execute("ALTER TABLE events RENAME COLUMN tenant_id TO platform_tenant_id")
    op.execute(
        "ALTER TABLE events ALTER COLUMN platform_tenant_id "
        "TYPE VARCHAR(64) USING platform_tenant_id::text"
    )

    # Recreate composite indexes with platform_tenant_id
    op.create_index('idx_events_tenant_event', 'events', ['platform_tenant_id', 'event_name'])
    op.create_index('idx_events_tenant_topic', 'events', ['platform_tenant_id', 'topic'])

    # Recreate unique constraint with platform_tenant_id
    op.create_index('uq_events_event_tenant', 'events', ['event_name', 'platform_tenant_id'], unique=True)

    # Force RLS (prevents table owners from bypassing policies)
    op.execute("ALTER TABLE events FORCE ROW LEVEL SECURITY")

    # New RLS policies using app.platform_tenant_id (plain string, no UUID cast)
    op.execute("""
        CREATE POLICY events_tenant_isolation ON events
            USING (platform_tenant_id = current_setting('app.platform_tenant_id', true))
    """)
    op.execute("""
        CREATE POLICY events_developer_write ON events
            FOR INSERT
            WITH CHECK (
                platform_tenant_id = current_setting('app.platform_tenant_id', true)
            )
    """)

    # ── payload_schemas table ─────────────────────────────────────────────────

    # Drop unique constraint (named constraint, not just index) created in migration 003
    op.drop_constraint('uq_schema_name_version_tenant', 'payload_schemas', type_='unique')
    op.drop_index('idx_payload_schemas_tenant_schema', table_name='payload_schemas')

    # Drop old RLS policies that reference app.tenant_id with ::UUID cast
    op.execute("DROP POLICY IF EXISTS payload_schemas_tenant_isolation ON payload_schemas")
    op.execute("DROP POLICY IF EXISTS payload_schemas_developer_write ON payload_schemas")

    # Rename column and change type UUID → VARCHAR(64)
    op.execute("ALTER TABLE payload_schemas RENAME COLUMN tenant_id TO platform_tenant_id")
    op.execute(
        "ALTER TABLE payload_schemas ALTER COLUMN platform_tenant_id "
        "TYPE VARCHAR(64) USING platform_tenant_id::text"
    )

    # Recreate composite index with platform_tenant_id
    op.create_index('idx_payload_schemas_tenant_schema', 'payload_schemas', ['platform_tenant_id', 'schema_name'])

    # Recreate unique constraint with platform_tenant_id
    op.create_unique_constraint(
        'uq_schema_name_version_tenant',
        'payload_schemas',
        ['schema_name', 'version', 'platform_tenant_id']
    )

    # Force RLS (prevents table owners from bypassing policies)
    op.execute("ALTER TABLE payload_schemas FORCE ROW LEVEL SECURITY")

    # New RLS policies using app.platform_tenant_id (plain string, no UUID cast)
    op.execute("""
        CREATE POLICY payload_schemas_tenant_isolation ON payload_schemas
            USING (platform_tenant_id = current_setting('app.platform_tenant_id', true))
    """)
    op.execute("""
        CREATE POLICY payload_schemas_developer_write ON payload_schemas
            FOR INSERT
            WITH CHECK (
                platform_tenant_id = current_setting('app.platform_tenant_id', true)
            )
    """)


def downgrade() -> None:
    # Intentional no-op: reverting VARCHAR(64) → UUID would corrupt data.
    # To roll back, restore from a pre-migration database snapshot.
    pass
