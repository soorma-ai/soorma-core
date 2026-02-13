"""Add user_id to task_context table

Revision ID: 006_add_user_id_to_task_context
Revises: 005_task_and_plan_context
Create Date: 2026-02-13

Changes:
- Add user_id column to task_context for user tracking

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '006_add_user_id_to_task_context'
down_revision = '005_task_and_plan_context'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add user_id column to task_context."""
    from sqlalchemy.dialects import postgresql
    
    # Add user_id column as UUID with FK to users table
    op.add_column(
        'task_context',
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False)
    )
    
    # Add foreign key constraint
    op.create_foreign_key(
        'fk_task_context_user_id',
        'task_context',
        'users',
        ['user_id'],
        ['id'],
        ondelete='CASCADE'
    )
    
    # Create index for user_id lookups
    op.create_index(
        'ix_task_context_user_id',
        'task_context',
        ['user_id']
    )


def downgrade() -> None:
    """Remove user_id column from task_context."""
    op.drop_index('ix_task_context_user_id', 'task_context')
    op.drop_constraint('fk_task_context_user_id', 'task_context', type_='foreignkey')
    op.drop_column('task_context', 'user_id')
