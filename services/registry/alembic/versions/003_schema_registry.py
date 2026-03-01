"""Add schema registry and multi-tenancy support

Revision ID: 003_schema_registry
Revises: 002_composite_key
Create Date: 2026-02-28

This migration implements Phase 1 of the Discovery & Schema Registry system:
- Creates payload_schemas table for schema versioning
- Adds multi-tenancy columns (tenant_id, user_id, version) to agents table
- Adds multi-tenancy and schema reference columns to events table
- Implements PostgreSQL Row-Level Security (RLS) policies
- Changes uniqueness constraints to tenant-scoped
- Adds composite indexes optimized for RLS query patterns

BREAKING CHANGES (v0.8.1):
- agents.agent_id now unique per tenant (not globally unique)
- events.event_name now unique per tenant (not globally unique)
- All tables require tenant_id/user_id (from authentication headers)

Migration Strategy:
- Uses default UUIDs during migration (safe rollback)
- After migration, default values are removed
- Existing data gets '00000000-0000-0000-0000-000000000000' tenant/user
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '003_schema_registry'
down_revision: Union[str, Sequence[str], None] = '002_composite_key'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Implement schema registry and multi-tenancy support.
    
    Steps:
    1. Create payload_schemas table
    2. Add multi-tenancy columns to agents table
    3. Add multi-tenancy and schema columns to events table
    4. Update uniqueness constraints to tenant-scoped
    5. Create composite indexes for RLS query patterns
    6. Enable RLS and create policies
    7. Remove default values from tenant_id/user_id columns
    """
    
    # Step 1: Create payload_schemas table
    op.create_table(
        'payload_schemas',
        sa.Column('id', postgresql.UUID(), server_default=sa.text('gen_random_uuid()'),  nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('schema_name', sa.String(255), nullable=False, comment='Unique schema name (e.g., research_request_v1)'),
        sa.Column('version', sa.String(50), nullable=False, comment='Semantic version (e.g., 1.0.0)'),
        sa.Column('json_schema', sa.JSON(), nullable=False, comment='JSON Schema definition'),
        sa.Column('description', sa.Text(), nullable=True, comment='Human-readable description'),
        sa.Column('owner_agent_id', sa.String(255), nullable=True, comment='Agent ID that owns this schema'),
        sa.Column('tenant_id', postgresql.UUID(), nullable=False, 
                  comment='Tenant identifier from validated JWT/API Key (no FK - Identity service owns tenant entity)'),
        sa.Column('user_id', postgresql.UUID(), nullable=False,
                  comment='User identifier from validated JWT/API Key (no FK - Identity service owns user entity)'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('schema_name', 'version', 'tenant_id', name='uq_schema_name_version_tenant')
    )
    
    # Create composite indexes for RLS query patterns
    op.create_index('idx_payload_schemas_tenant_schema', 'payload_schemas', ['tenant_id', 'schema_name'])
    op.create_index('idx_payload_schemas_owner_agent_id', 'payload_schemas', ['owner_agent_id'])
    
    # Step 2: Add multi-tenancy columns to agents table (with defaults for existing rows)
    op.add_column('agents', sa.Column('tenant_id', postgresql.UUID(), nullable=False,
                                       server_default="'00000000-0000-0000-0000-000000000000'::uuid",
                                       comment='Tenant identifier from validated JWT/API Key (no FK - Identity service owns tenant entity)'))
    op.add_column('agents', sa.Column('user_id', postgresql.UUID(), nullable=False,
                                       server_default="'00000000-0000-0000-0000-000000000000'::uuid",
                                       comment='User identifier from validated JWT/API Key (no FK - Identity service owns user entity)'))
    op.add_column('agents', sa.Column('version', sa.String(50), server_default='1.0.0'))
    
    # Create composite indexes for agents (RLS query patterns)
    op.create_index('idx_agents_tenant_agent', 'agents', ['tenant_id', 'agent_id'])
    op.create_index('idx_agents_tenant_name', 'agents', ['tenant_id', 'name'])
    op.create_index('idx_agents_version', 'agents', ['version'])
    
    # BREAKING CHANGE: Remove global unique constraint on agent_id
    op.drop_index('ix_agents_agent_id', table_name='agents')
    
    # Add tenant-scoped unique constraint
    op.create_index('uq_agents_agent_tenant', 'agents', ['agent_id', 'tenant_id'], unique=True)
    
    # Remove defaults after migration (force explicit tenant/user context)
    op.alter_column('agents', 'tenant_id', server_default=None)
    op.alter_column('agents', 'user_id', server_default=None)
    
    # Step 3: Add multi-tenancy and schema columns to events table
    op.add_column('events', sa.Column('owner_agent_id', sa.String(255), nullable=True))
    op.add_column('events', sa.Column('tenant_id', postgresql.UUID(), nullable=False,
                                       server_default="'00000000-0000-0000-0000-000000000000'::uuid",
                                       comment='Tenant identifier from validated JWT/API Key (no FK - Identity service owns tenant entity)'))
    op.add_column('events', sa.Column('user_id', postgresql.UUID(), nullable=False,
                                       server_default="'00000000-0000-0000-0000-000000000000'::uuid",
                                       comment='User identifier from validated JWT/API Key (no FK - Identity service owns user entity)'))
    op.add_column('events', sa.Column('payload_schema_name', sa.String(255), nullable=True))
    op.add_column('events', sa.Column('response_schema_name', sa.String(255), nullable=True))
    
    # Create composite indexes for events (RLS query patterns)
    op.create_index('idx_events_tenant_event', 'events', ['tenant_id', 'event_name'])
    op.create_index('idx_events_tenant_topic', 'events', ['tenant_id', 'topic'])
    op.create_index('idx_events_owner_agent_id', 'events', ['owner_agent_id'])
    op.create_index('idx_events_payload_schema_name', 'events', ['payload_schema_name'])
    
    # BREAKING CHANGE: Remove global unique constraint on (event_name, topic)
    op.drop_constraint('uix_event_name_topic', 'events', type_='unique')
    
    # Add tenant-scoped unique constraint
    op.create_index('uq_events_event_tenant', 'events', ['event_name', 'tenant_id'], unique=True)
    
    # Remove defaults
    op.alter_column('events', 'tenant_id', server_default=None)
    op.alter_column('events', 'user_id', server_default=None)
    
    # Step 4: Enable RLS and create policies
    
    # Enable RLS on payload_schemas
    op.execute("ALTER TABLE payload_schemas ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY payload_schemas_tenant_isolation ON payload_schemas
            USING (tenant_id = current_setting('app.tenant_id', true)::UUID)
    """)
    op.execute("""
        CREATE POLICY payload_schemas_user_write ON payload_schemas
            FOR INSERT
            WITH CHECK (
                tenant_id = current_setting('app.tenant_id', true)::UUID 
                AND user_id = current_setting('app.user_id', true)::UUID
            )
    """)
    
    # Enable RLS on agents
    op.execute("ALTER TABLE agents ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY agents_tenant_isolation ON agents
            USING (tenant_id = current_setting('app.tenant_id', true)::UUID)
    """)
    op.execute("""
        CREATE POLICY agents_user_write ON agents
            FOR INSERT
            WITH CHECK (
                tenant_id = current_setting('app.tenant_id', true)::UUID 
                AND user_id = current_setting('app.tenant_id', true)::UUID
            )
    """)
    
    # Enable RLS on events
    op.execute("ALTER TABLE events ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY events_tenant_isolation ON events
            USING (tenant_id = current_setting('app.tenant_id', true)::UUID)
    """)
    op.execute("""
        CREATE POLICY events_user_write ON events
            FOR INSERT
            WITH CHECK (
                tenant_id = current_setting('app.tenant_id', true)::UUID 
                AND user_id = current_setting('app.user_id', true)::UUID
            )
    """)


def downgrade() -> None:
    """
    Rollback schema registry and multi-tenancy changes.
    
    Steps (reverse order):
    1. Drop RLS policies
    2. Disable RLS
    3. Drop composite indexes
    4. Restore global uniqueness constraints
    5. Drop columns from events table
    6. Drop columns from agents table
    7. Drop payload_schemas table
    """
    
    # Step 1: Drop RLS policies (events)
    op.execute("DROP POLICY IF EXISTS events_user_write ON events")
    op.execute("DROP POLICY IF EXISTS events_tenant_isolation ON events")
    op.execute("ALTER TABLE events DISABLE ROW LEVEL SECURITY")
    
    # Drop RLS policies (agents)
    op.execute("DROP POLICY IF EXISTS agents_user_write ON agents")
    op.execute("DROP POLICY IF EXISTS agents_tenant_isolation ON agents")
    op.execute("ALTER TABLE agents DISABLE ROW LEVEL SECURITY")
    
    # Drop RLS policies (payload_schemas)
    op.execute("DROP POLICY IF EXISTS payload_schemas_user_write ON payload_schemas")
    op.execute("DROP POLICY IF EXISTS payload_schemas_tenant_isolation ON payload_schemas")
    op.execute("ALTER TABLE payload_schemas DISABLE ROW LEVEL SECURITY")
    
    # Step 2: Restore global uniqueness for events
    op.drop_index('uq_events_event_tenant', table_name='events')
    op.create_unique_constraint('uix_event_name_topic', 'events', ['event_name', 'topic'])
    
    # Step 3: Drop indexes and columns from events table
    op.drop_index('idx_events_payload_schema_name', table_name='events')
    op.drop_index('idx_events_owner_agent_id', table_name='events')
    op.drop_index('idx_events_tenant_topic', table_name='events')
    op.drop_index('idx_events_tenant_event', table_name='events')
    
    op.drop_column('events', 'response_schema_name')
    op.drop_column('events', 'payload_schema_name')
    op.drop_column('events', 'user_id')
    op.drop_column('events', 'tenant_id')
    op.drop_column('events', 'owner_agent_id')
    
    # Step 4: Restore global uniqueness for agents
    op.drop_index('uq_agents_agent_tenant', table_name='agents')
    op.create_index('ix_agents_agent_id', 'agents', ['agent_id'], unique=True)
    
    # Step 5: Drop indexes and columns from agents table
    op.drop_index('idx_agents_version', table_name='agents')
    op.drop_index('idx_agents_tenant_name', table_name='agents')
    op.drop_index('idx_agents_tenant_agent', table_name='agents')
    
    op.drop_column('agents', 'version')
    op.drop_column('agents', 'user_id')
    op.drop_column('agents', 'tenant_id')
    
    # Step 6: Drop payload_schemas table (with indexes)
    op.drop_index('idx_payload_schemas_owner_agent_id', table_name='payload_schemas')
    op.drop_index('idx_payload_schemas_tenant_schema', table_name='payload_schemas')
    op.drop_table('payload_schemas')
