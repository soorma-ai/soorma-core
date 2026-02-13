"""Add task_context and plan_context tables

Revision ID: 005_task_and_plan_context
Revises: 004_plans_and_sessions
Create Date: 2026-02-12

Changes:
- Add task_context table for async Worker completion tracking (RF-SDK-004)
- Add plan_context table for Planner state machine
- Add RLS policies for multi-tenant isolation

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '005_task_and_plan_context'
down_revision = '004_plans_and_sessions'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add task_context and plan_context tables with RLS policies."""
    
    # Create task_context table for async Worker completion
    op.create_table(
        'task_context',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('task_id', sa.String(100), nullable=False),
        sa.Column('plan_id', sa.String(100), nullable=True),
        sa.Column('event_type', sa.String(255), nullable=False),
        sa.Column('response_event', sa.String(255), nullable=True),
        sa.Column('response_topic', sa.String(100), nullable=False, server_default='action-results'),
        sa.Column('data', postgresql.JSONB, nullable=False, server_default='{}'),
        sa.Column('sub_tasks', postgresql.JSONB, nullable=False, server_default='[]'),
        sa.Column('state', postgresql.JSONB, nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('(NOW() AT TIME ZONE \'UTC\')')),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.text('(NOW() AT TIME ZONE \'UTC\')')),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('tenant_id', 'task_id', name='task_context_unique'),
    )
    
    # Create indexes on task_context for lookup performance
    op.create_index('ix_task_context_tenant_task', 'task_context', ['tenant_id', 'task_id'])
    op.create_index('ix_task_context_plan_id', 'task_context', ['plan_id'])
    op.create_index('ix_task_context_updated_at', 'task_context', ['updated_at'])
    
    # Enable RLS on task_context
    op.execute('ALTER TABLE task_context ENABLE ROW LEVEL SECURITY')
    op.execute("""
        CREATE POLICY task_context_isolation ON task_context
        USING (tenant_id = current_setting('app.current_tenant')::UUID)
    """)
    
    # Create plan_context table for Planner state machine
    op.create_table(
        'plan_context',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('plan_id', sa.String(100), nullable=False),
        sa.Column('session_id', sa.String(100), nullable=True),
        sa.Column('goal_event', sa.String(255), nullable=False),
        sa.Column('goal_data', postgresql.JSONB, nullable=False, server_default='{}'),
        sa.Column('response_event', sa.String(255), nullable=True),
        sa.Column('state', postgresql.JSONB, nullable=False, server_default='{}'),
        sa.Column('current_state', sa.String(100), nullable=True),
        sa.Column('correlation_ids', postgresql.JSONB, nullable=False, server_default='[]'),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('(NOW() AT TIME ZONE \'UTC\')')),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.text('(NOW() AT TIME ZONE \'UTC\')')),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('tenant_id', 'plan_id', name='plan_context_unique'),
    )
    
    # Create indexes on plan_context for lookup performance
    op.create_index('ix_plan_context_tenant_plan', 'plan_context', ['tenant_id', 'plan_id'])
    op.create_index('ix_plan_context_session_id', 'plan_context', ['session_id'])
    op.create_index('ix_plan_context_current_state', 'plan_context', ['current_state'])
    op.create_index('ix_plan_context_updated_at', 'plan_context', ['updated_at'])
    
    # Enable RLS on plan_context
    op.execute('ALTER TABLE plan_context ENABLE ROW LEVEL SECURITY')
    op.execute("""
        CREATE POLICY plan_context_isolation ON plan_context
        USING (tenant_id = current_setting('app.current_tenant')::UUID)
    """)


def downgrade() -> None:
    """Drop task_context and plan_context tables."""
    # Drop RLS policies
    op.execute('DROP POLICY IF EXISTS plan_context_isolation ON plan_context')
    op.execute('DROP POLICY IF EXISTS task_context_isolation ON task_context')
    
    # Drop tables (cascades to foreign keys)
    op.drop_table('plan_context')
    op.drop_table('task_context')
