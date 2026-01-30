"""Add user ownership to working_memory

Revision ID: 003_working_memory_user_scope
Revises: 002_upsert_privacy
Create Date: 2026-01-29

Changes:
- Add user_id column to working_memory for ownership enforcement
- Update RLS policy to require tenant_id AND user_id match

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '003_working_memory_user_scope'
down_revision = '002_upsert_privacy'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add user ownership to working_memory and update RLS policy."""
    # Add user_id column (initially nullable for backfill)
    op.add_column('working_memory', sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True))

    # Backfill user_id for existing records (development default)
    # In production, consider data migration or database reset for pre-release
    op.execute("""
        UPDATE working_memory
        SET user_id = '00000000-0000-0000-0000-000000000000'::UUID
        WHERE user_id IS NULL
    """)

    # Make user_id NOT NULL
    op.alter_column('working_memory', 'user_id', nullable=False)

    # Replace RLS policy to enforce user ownership
    op.execute('DROP POLICY IF EXISTS plan_isolation ON working_memory')
    op.execute("""
        CREATE POLICY working_memory_user_isolation ON working_memory
        USING (
            tenant_id = current_setting('app.current_tenant')::UUID
            AND user_id = current_setting('app.current_user')::UUID
        )
    """)


def downgrade() -> None:
    """Revert user ownership changes for working_memory."""
    # Restore previous tenant-only policy
    op.execute('DROP POLICY IF EXISTS working_memory_user_isolation ON working_memory')
    op.execute("""
        CREATE POLICY plan_isolation ON working_memory
        USING (tenant_id = current_setting('app.current_tenant')::UUID)
    """)

    # Drop user_id column
    op.drop_column('working_memory', 'user_id')
