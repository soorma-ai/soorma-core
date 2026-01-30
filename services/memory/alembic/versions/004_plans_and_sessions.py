"""Add plans and sessions tables

Revision ID: 004_plans_and_sessions
Revises: 003_working_memory_user_scope
Create Date: 2026-01-30

Changes:
- Add sessions table for grouping related plans
- Add plans table for workflow execution tracking
- Add RLS policies for multi-tenant isolation

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '004_plans_and_sessions'
down_revision = '003_working_memory_user_scope'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add plans and sessions tables with RLS policies."""
    
    # Create sessions table
    op.create_table(
        'sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('session_id', sa.String(100), nullable=False),
        sa.Column('name', sa.String(255), nullable=True),
        sa.Column('session_metadata', postgresql.JSONB, nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('(NOW() AT TIME ZONE \'UTC\')')),
        sa.Column('last_interaction', sa.DateTime, nullable=False, server_default=sa.text('(NOW() AT TIME ZONE \'UTC\')')),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('tenant_id', 'session_id', name='session_unique'),
    )
    
    # Create index on sessions for lookup performance
    op.create_index('ix_sessions_tenant_user', 'sessions', ['tenant_id', 'user_id'])
    op.create_index('ix_sessions_last_interaction', 'sessions', ['last_interaction'])
    
    # Enable RLS on sessions
    op.execute('ALTER TABLE sessions ENABLE ROW LEVEL SECURITY')
    op.execute("""
        CREATE POLICY sessions_isolation ON sessions
        USING (
            tenant_id = current_setting('app.current_tenant')::UUID
            AND user_id = current_setting('app.current_user')::UUID
        )
    """)
    
    # Create plans table
    op.create_table(
        'plans',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('plan_id', sa.String(100), nullable=False),
        sa.Column('session_id', sa.String(100), nullable=True),
        sa.Column('goal_event', sa.String(255), nullable=False),
        sa.Column('goal_data', postgresql.JSONB, nullable=False, server_default='{}'),
        sa.Column('status', sa.String(50), nullable=False, server_default='running'),
        sa.Column('parent_plan_id', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('(NOW() AT TIME ZONE \'UTC\')')),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.text('(NOW() AT TIME ZONE \'UTC\')')),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('tenant_id', 'plan_id', name='plan_unique'),
        sa.CheckConstraint(
            "status IN ('running', 'completed', 'failed', 'paused')",
            name='plan_status_check'
        ),
    )
    
    # Create indexes on plans for lookup performance
    op.create_index('ix_plans_tenant_user', 'plans', ['tenant_id', 'user_id'])
    op.create_index('ix_plans_session_id', 'plans', ['session_id'])
    op.create_index('ix_plans_status', 'plans', ['status'])
    op.create_index('ix_plans_updated_at', 'plans', ['updated_at'])
    
    # Enable RLS on plans
    op.execute('ALTER TABLE plans ENABLE ROW LEVEL SECURITY')
    op.execute("""
        CREATE POLICY plans_isolation ON plans
        USING (
            tenant_id = current_setting('app.current_tenant')::UUID
            AND user_id = current_setting('app.current_user')::UUID
        )
    """)


def downgrade() -> None:
    """Drop plans and sessions tables."""
    # Drop RLS policies
    op.execute('DROP POLICY IF EXISTS plans_isolation ON plans')
    op.execute('DROP POLICY IF EXISTS sessions_isolation ON sessions')
    
    # Drop tables (cascades to foreign keys)
    op.drop_table('plans')
    op.drop_table('sessions')
