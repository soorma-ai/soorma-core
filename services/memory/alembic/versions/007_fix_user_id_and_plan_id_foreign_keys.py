"""Fix user_id and plan_id foreign keys

Revision ID: 007_user_plan_fkeys
Revises: 006_add_user_id_to_task_context
Create Date: 2026-02-13

Changes:
- Add FK constraint to working_memory.user_id
- Convert plan_context.plan_id from String to UUID FK referencing plans.id
- Update plan_context unique constraint from (tenant_id, plan_id) to (plan_id)

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '007_user_plan_fkeys'
down_revision = '006_add_user_id_to_task_context'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add foreign key constraints."""
    from sqlalchemy.dialects import postgresql
    
    # 1. Add FK constraint to working_memory.user_id
    op.create_foreign_key(
        'fk_working_memory_user_id',
        'working_memory',
        'users',
        ['user_id'],
        ['id'],
        ondelete='CASCADE'
    )
    
    # Create index for user_id lookups
    op.create_index(
        'ix_working_memory_user_id',
        'working_memory',
        ['user_id']
    )
    
    # 2. Convert plan_context.plan_id from String to UUID FK
    # Drop old unique constraint
    op.drop_constraint('plan_context_unique', 'plan_context', type_='unique')
    
    # Add temporary column for new UUID plan_id
    op.add_column(
        'plan_context',
        sa.Column('plan_id_new', postgresql.UUID(as_uuid=True), nullable=True)
    )
    
    # Migrate data: map string plan_id to UUID from plans table
    op.execute("""
        UPDATE plan_context pc
        SET plan_id_new = p.id
        FROM plans p
        WHERE pc.tenant_id = p.tenant_id 
        AND pc.plan_id = p.plan_id
    """)
    
    # Drop old plan_id column
    op.drop_column('plan_context', 'plan_id')
    
    # Rename new column to plan_id
    op.alter_column('plan_context', 'plan_id_new', new_column_name='plan_id')
    
    # Make plan_id not nullable
    op.alter_column('plan_context', 'plan_id', nullable=False)
    
    # Add FK constraint to plans.id
    op.create_foreign_key(
        'fk_plan_context_plan_id',
        'plan_context',
        'plans',
        ['plan_id'],
        ['id'],
        ondelete='CASCADE'
    )
    
    # Create new unique constraint on just plan_id
    op.create_unique_constraint('plan_context_unique', 'plan_context', ['plan_id'])
    
    # Create index for plan_id lookups
    op.create_index(
        'ix_plan_context_plan_id',
        'plan_context',
        ['plan_id']
    )


def downgrade() -> None:
    """Remove foreign key constraints and revert plan_id to String."""
    from sqlalchemy.dialects import postgresql
    
    # Drop working_memory FK
    op.drop_index('ix_working_memory_user_id', 'working_memory')
    op.drop_constraint('fk_working_memory_user_id', 'working_memory', type_='foreignkey')
    
    # Revert plan_context changes
    op.drop_index('ix_plan_context_plan_id', 'plan_context')
    op.drop_constraint('plan_context_unique', 'plan_context', type_='unique')
    op.drop_constraint('fk_plan_context_plan_id', 'plan_context', type_='foreignkey')
    
    # Add temporary string column
    op.add_column(
        'plan_context',
        sa.Column('plan_id_old', sa.String(100), nullable=True)
    )
    
    # Migrate data back: map UUID plan_id to string from plans table
    op.execute("""
        UPDATE plan_context pc
        SET plan_id_old = p.plan_id
        FROM plans p
        WHERE pc.plan_id = p.id
    """)
    
    # Drop UUID column
    op.drop_column('plan_context', 'plan_id')
    
    # Rename old column back
    op.alter_column('plan_context', 'plan_id_old', new_column_name='plan_id')
    
    # Make not nullable
    op.alter_column('plan_context', 'plan_id', nullable=False)
    
    # Recreate original unique constraint
    op.create_unique_constraint('plan_context_unique', 'plan_context', ['tenant_id', 'plan_id'])
