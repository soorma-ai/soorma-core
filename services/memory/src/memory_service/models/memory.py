"""Database models for memory service."""

import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, JSON, CheckConstraint, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from pgvector.sqlalchemy import Vector

from memory_service.core.database import Base


class Tenant(Base):
    """Tenant model (replica from Identity Service)."""

    __tablename__ = "tenants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


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
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class SemanticMemory(Base):
    """Semantic memory - factual knowledge shared across tenant."""

    __tablename__ = "semantic_memory"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    content = Column(Text, nullable=False)
    embedding = Column(Vector(1536))
    memory_metadata = Column(JSON, default={}, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


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
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

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
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

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
    plan_id = Column(UUID(as_uuid=True), nullable=False)
    key = Column(Text, nullable=False)
    value = Column(JSON, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

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
    task_id = Column(String(100), nullable=False)
    plan_id = Column(String(100), nullable=True)
    event_type = Column(String(255), nullable=False)
    response_event = Column(String(255), nullable=True)
    response_topic = Column(String(100), default='action-results', nullable=False)
    data = Column(JSON, default={}, nullable=False)
    sub_tasks = Column(JSON, default=[], nullable=False)
    state = Column(JSON, default={}, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

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
    plan_id = Column(String(100), nullable=False)
    session_id = Column(String(100), nullable=True)
    goal_event = Column(String(255), nullable=False)
    goal_data = Column(JSON, default={}, nullable=False)
    response_event = Column(String(255), nullable=True)
    state = Column(JSON, default={}, nullable=False)
    current_state = Column(String(100), nullable=True)
    correlation_ids = Column(JSON, default=[], nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (UniqueConstraint("tenant_id", "plan_id", name="plan_context_unique"),)


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
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

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
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_interaction = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (UniqueConstraint("tenant_id", "session_id", name="session_unique"),)

