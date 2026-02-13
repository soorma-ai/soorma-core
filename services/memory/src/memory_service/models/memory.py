"""Database models for memory service."""

import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, JSON, CheckConstraint, UniqueConstraint, Boolean
from sqlalchemy.dialects.postgresql import UUID
from pgvector.sqlalchemy import Vector

from memory_service.core.database import Base


def utc_now():
    """Return timezone-naive UTC datetime for PostgreSQL TIMESTAMP WITHOUT TIME ZONE."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Tenant(Base):
    """Tenant model (replica from Identity Service)."""

    __tablename__ = "tenants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)


class User(Base):
    """User model (replica from Identity Service)."""

    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    username = Column(Text, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)


class SemanticMemory(Base):
    """Semantic memory - factual knowledge (private by default, optional public).
    
    RF-ARCH-012: Upsert support via external_id and content_hash
    RF-ARCH-014: Privacy support via user_id and is_public
    """

    __tablename__ = "semantic_memory"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    # RF-ARCH-014: User ownership (private by default)
    user_id = Column(String(255), nullable=False)
    
    # Core content
    content = Column(Text, nullable=False)
    embedding = Column(Vector(1536))
    memory_metadata = Column(JSON, default={}, nullable=False)
    
    # RF-ARCH-012: Upsert support
    external_id = Column(String(255), nullable=True)  # User-provided ID for versioning
    content_hash = Column(String(64), nullable=False)  # SHA-256 for deduplication
    
    # RF-ARCH-014: Privacy control
    is_public = Column(Boolean, nullable=False, default=False)  # Default private
    
    # Timestamps
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)


class EpisodicMemory(Base):
    """Episodic memory - interaction history specific to User + Agent."""

    __tablename__ = "episodic_memory"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    agent_id = Column(Text, nullable=False)
    role = Column(Text, nullable=False)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(1536))
    memory_metadata = Column(JSON, default={}, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    __table_args__ = (
        CheckConstraint("role IN ('user', 'assistant', 'system', 'tool')", name="role_check"),
    )


class ProceduralMemory(Base):
    """Procedural memory - skills, prompts, and rules."""

    __tablename__ = "procedural_memory"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    agent_id = Column(Text, nullable=False)
    trigger_condition = Column(Text)
    embedding = Column(Vector(1536))
    procedure_type = Column(Text, nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "procedure_type IN ('system_prompt', 'few_shot_example')",
            name="procedure_type_check",
        ),
    )


class WorkingMemory(Base):
    """Working memory - plan-scoped shared state."""

    __tablename__ = "working_memory"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    plan_id = Column(UUID(as_uuid=True), nullable=False)
    key = Column(Text, nullable=False)
    value = Column(JSON, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    __table_args__ = (UniqueConstraint("plan_id", "key", name="plan_key_unique"),)


class TaskContext(Base):
    """Task context for async Worker completion."""

    __tablename__ = "task_context"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    task_id = Column(String(100), nullable=False)
    plan_id = Column(String(100), nullable=True)
    event_type = Column(String(255), nullable=False)
    response_event = Column(String(255), nullable=True)
    response_topic = Column(String(100), default='action-results', nullable=False)
    data = Column(JSON, default={}, nullable=False)
    sub_tasks = Column(JSON, default=[], nullable=False)
    state = Column(JSON, default={}, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    __table_args__ = (UniqueConstraint("tenant_id", "task_id", name="task_context_unique"),)


class PlanContext(Base):
    """Plan context for Planner state machine."""

    __tablename__ = "plan_context"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    plan_id = Column(
        UUID(as_uuid=True),
        ForeignKey("plans.id", ondelete="CASCADE"),
        nullable=False,
    )
    session_id = Column(String(100), nullable=True)
    goal_event = Column(String(255), nullable=False)
    goal_data = Column(JSON, default={}, nullable=False)
    response_event = Column(String(255), nullable=True)
    state = Column(JSON, default={}, nullable=False)
    current_state = Column(String(100), nullable=True)
    correlation_ids = Column(JSON, default=[], nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    __table_args__ = (UniqueConstraint("plan_id", name="plan_context_unique"),)


class Plan(Base):
    """Plan summary for queries."""

    __tablename__ = "plans"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    plan_id = Column(String(100), nullable=False)
    session_id = Column(String(100), nullable=True)
    goal_event = Column(String(255), nullable=False)
    goal_data = Column(JSON, default={}, nullable=False)
    status = Column(String(50), default='running', nullable=False)
    parent_plan_id = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    __table_args__ = (
        UniqueConstraint("tenant_id", "plan_id", name="plan_unique"),
        CheckConstraint(
            "status IN ('running', 'completed', 'failed', 'paused')",
            name="plan_status_check",
        ),
    )


class Session(Base):
    """Session for grouping related plans."""

    __tablename__ = "sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    session_id = Column(String(100), nullable=False)
    name = Column(String(255), nullable=True)
    session_metadata = Column(JSON, default={}, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    last_interaction = Column(DateTime, default=utc_now, nullable=False)

    __table_args__ = (UniqueConstraint("tenant_id", "session_id", name="session_unique"),)

