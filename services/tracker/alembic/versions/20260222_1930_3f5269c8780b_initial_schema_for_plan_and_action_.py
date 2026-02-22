"""Alembic migration script template."""

"""Initial schema for plan and action progress tracking

Revision ID: 3f5269c8780b
Revises: 
Create Date: 2026-02-22 19:30:31.996281+00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '3f5269c8780b'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create ENUM types
    plan_status_enum = postgresql.ENUM(
        'pending', 'in_progress', 'completed', 'failed', 'cancelled',
        name='plan_status_enum',
        create_type=False
    )
    plan_status_enum.create(op.get_bind(), checkfirst=True)
    
    action_status_enum = postgresql.ENUM(
        'pending', 'running', 'completed', 'failed', 'skipped',
        name='action_status_enum',
        create_type=False
    )
    action_status_enum.create(op.get_bind(), checkfirst=True)
    
    # Create plan_progress table
    op.create_table(
        'plan_progress',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('plan_id', sa.String(length=255), nullable=False),
        sa.Column('tenant_id', sa.String(length=255), nullable=False),
        sa.Column('user_id', sa.String(length=255), nullable=False),
        sa.Column('plan_name', sa.String(length=500), nullable=True),
        sa.Column('plan_description', sa.Text(), nullable=True),
        sa.Column('status', plan_status_enum, nullable=False, server_default='pending'),
        sa.Column('total_actions', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('completed_actions', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('failed_actions', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('plan_id', name='uq_plan_id'),
    )
    
    # Create indexes for plan_progress
    op.create_index('idx_plan_tenant_plan', 'plan_progress', ['tenant_id', 'plan_id'])
    op.create_index('idx_plan_status', 'plan_progress', ['status'])
    op.create_index('idx_plan_created', 'plan_progress', ['created_at'])
    op.create_index(op.f('ix_plan_progress_plan_id'), 'plan_progress', ['plan_id'])
    op.create_index(op.f('ix_plan_progress_tenant_id'), 'plan_progress', ['tenant_id'])
    
    # Create action_progress table
    op.create_table(
        'action_progress',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('plan_id', sa.String(length=255), nullable=False),
        sa.Column('action_id', sa.String(length=255), nullable=False),
        sa.Column('tenant_id', sa.String(length=255), nullable=False),
        sa.Column('user_id', sa.String(length=255), nullable=False),
        sa.Column('action_name', sa.String(length=500), nullable=False),
        sa.Column('action_description', sa.Text(), nullable=True),
        sa.Column('action_type', sa.String(length=100), nullable=True),
        sa.Column('status', action_status_enum, nullable=False, server_default='pending'),
        sa.Column('assigned_to', sa.String(length=255), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('result', sa.Text(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['plan_id'], ['plan_progress.plan_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    
    # Create indexes for action_progress
    op.create_index('idx_action_tenant_action', 'action_progress', ['tenant_id', 'action_id'])
    op.create_index('idx_action_plan', 'action_progress', ['plan_id'])
    op.create_index('idx_action_status', 'action_progress', ['status'])
    op.create_index('idx_action_created', 'action_progress', ['created_at'])
    op.create_index(op.f('ix_action_progress_action_id'), 'action_progress', ['action_id'])
    op.create_index(op.f('ix_action_progress_tenant_id'), 'action_progress', ['tenant_id'])


def downgrade() -> None:
    # Drop indexes for action_progress
    op.drop_index(op.f('ix_action_progress_tenant_id'), table_name='action_progress')
    op.drop_index(op.f('ix_action_progress_action_id'), table_name='action_progress')
    op.drop_index('idx_action_created', table_name='action_progress')
    op.drop_index('idx_action_status', table_name='action_progress')
    op.drop_index('idx_action_plan', table_name='action_progress')
    op.drop_index('idx_action_tenant_action', table_name='action_progress')
    
    # Drop action_progress table
    op.drop_table('action_progress')
    
    # Drop indexes for plan_progress
    op.drop_index(op.f('ix_plan_progress_tenant_id'), table_name='plan_progress')
    op.drop_index(op.f('ix_plan_progress_plan_id'), table_name='plan_progress')
    op.drop_index('idx_plan_created', table_name='plan_progress')
    op.drop_index('idx_plan_status', table_name='plan_progress')
    op.drop_index('idx_plan_tenant_plan', table_name='plan_progress')
    
    # Drop plan_progress table
    op.drop_table('plan_progress')
    
    # Drop ENUM types
    action_status_enum = postgresql.ENUM(name='action_status_enum')
    action_status_enum.drop(op.get_bind(), checkfirst=True)
    
    plan_status_enum = postgresql.ENUM(name='plan_status_enum')
    plan_status_enum.drop(op.get_bind(), checkfirst=True)
