"""Add unique constraint on action_progress (tenant_id, action_id)

Required for ON CONFLICT DO UPDATE idempotency in event handlers.

Revision ID: abc123def456
Revises: 3f5269c8780b
Create Date: 2026-02-23 00:01:00.000000+00:00

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = 'abc123def456'
down_revision = '3f5269c8780b'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_unique_constraint(
        'uq_action_tenant_action',
        'action_progress',
        ['tenant_id', 'action_id'],
    )


def downgrade() -> None:
    op.drop_constraint(
        'uq_action_tenant_action',
        'action_progress',
        type_='unique',
    )
