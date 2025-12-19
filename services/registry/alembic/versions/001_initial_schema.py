"""Initial schema for Registry Service

Revision ID: 001_initial
Revises: 
Create Date: 2025-12-18

This consolidates the complete schema for the Registry Service including:
- Events table: Event definitions with JSON schemas
- Agents table: Agent registrations with TTL/heartbeat support
- Agent Capabilities table: Per-capability event contracts
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create all tables for the Registry Service."""
    
    # Events table - stores event definitions
    op.create_table('events',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('event_name', sa.String(length=255), nullable=False),
        sa.Column('topic', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('payload_schema', sa.JSON(), nullable=False),
        sa.Column('response_schema', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_events_event_name'), 'events', ['event_name'], unique=True)
    op.create_index(op.f('ix_events_topic'), 'events', ['topic'], unique=False)
    
    # Agents table - stores agent registrations with heartbeat for TTL
    op.create_table('agents',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('agent_id', sa.String(length=255), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('consumed_events', sa.JSON(), nullable=False),
        sa.Column('produced_events', sa.JSON(), nullable=False),
        sa.Column('last_heartbeat', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False, comment='Last time agent refreshed its registration'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_agents_agent_id'), 'agents', ['agent_id'], unique=True)
    op.create_index(op.f('ix_agents_name'), 'agents', ['name'], unique=False)
    op.create_index(op.f('ix_agents_last_heartbeat'), 'agents', ['last_heartbeat'], unique=False)
    
    # Agent Capabilities table - stores per-capability event contracts
    op.create_table('agent_capabilities',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('agent_table_id', sa.Integer(), nullable=False),
        sa.Column('task_name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('consumed_event', sa.String(length=255), nullable=False, comment='Event that triggers this capability'),
        sa.Column('produced_events', sa.JSON(), nullable=False, comment='Events this capability can produce'),
        sa.ForeignKeyConstraint(['agent_table_id'], ['agents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_agent_capabilities_agent_table_id'), 'agent_capabilities', ['agent_table_id'], unique=False)
    op.create_index(op.f('ix_agent_capabilities_consumed_event'), 'agent_capabilities', ['consumed_event'], unique=False)


def downgrade() -> None:
    """Drop all tables."""
    op.drop_index(op.f('ix_agent_capabilities_consumed_event'), table_name='agent_capabilities')
    op.drop_index(op.f('ix_agent_capabilities_agent_table_id'), table_name='agent_capabilities')
    op.drop_table('agent_capabilities')
    
    op.drop_index(op.f('ix_agents_last_heartbeat'), table_name='agents')
    op.drop_index(op.f('ix_agents_name'), table_name='agents')
    op.drop_index(op.f('ix_agents_agent_id'), table_name='agents')
    op.drop_table('agents')
    
    op.drop_index(op.f('ix_events_topic'), table_name='events')
    op.drop_index(op.f('ix_events_event_name'), table_name='events')
    op.drop_table('events')
