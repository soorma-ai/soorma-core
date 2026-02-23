"""Add composite unique constraint for event_name and topic

Revision ID: 002_composite_key
Revises: 001_initial
Create Date: 2026-02-22

This migration enables the same event name to exist on different topics
(e.g., 'data.fetch.requested' on both 'action-requests' and 'action-results').

Changes:
- Drop unique index on event_name alone
- Add composite unique constraint on (event_name, topic)
- Add non-unique index on event_name for queries
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '002_composite_key'
down_revision: Union[str, Sequence[str], None] = '001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Change event_name from unique to composite unique with topic."""
    
    # Drop the old unique index on event_name
    op.drop_index('ix_events_event_name', table_name='events')
    
    # Create non-unique index on event_name (for query performance)
    op.create_index(op.f('ix_events_event_name'), 'events', ['event_name'], unique=False)
    
    # Add composite unique constraint on (event_name, topic)
    op.create_unique_constraint('uix_event_name_topic', 'events', ['event_name', 'topic'])


def downgrade() -> None:
    """Revert to unique event_name only."""
    
    # Drop composite unique constraint
    op.drop_constraint('uix_event_name_topic', 'events', type_='unique')
    
    # Drop non-unique index
    op.drop_index(op.f('ix_events_event_name'), table_name='events')
    
    # Recreate unique index on event_name
    op.create_index(op.f('ix_events_event_name'), 'events', ['event_name'], unique=True)
