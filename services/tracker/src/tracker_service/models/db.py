"""SQLAlchemy database models for Tracker Service (STUB)."""

from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import (
    String,
    Integer,
    DateTime,
    Text,
    Index,
    ForeignKey,
    Enum as SQLEnum,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
import enum


def utcnow():
    """Return current UTC time with timezone awareness."""
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


class PlanStatus(str, enum.Enum):
    """Plan execution status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ActionStatus(str, enum.Enum):
    """Action execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class PlanProgress(Base):
    """Track plan execution progress (STUB).
    
    Multi-tenant table with RLS enforced at database level.
    Each plan tracks overall execution state and timing.
    """
    __tablename__ = "plan_progress"
    
    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Business identifiers
    plan_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    tenant_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Plan metadata
    plan_name: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    plan_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Execution state
    status: Mapped[PlanStatus] = mapped_column(
        SQLEnum(PlanStatus, name="plan_status_enum"),
        nullable=False,
        default=PlanStatus.PENDING,
    )
    
    # Progress metrics
    total_actions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completed_actions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_actions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        nullable=False,
        default=utcnow,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), 
        nullable=True,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), 
        nullable=True,
    )
    
    # Error tracking
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Relationships
    actions: Mapped[list["ActionProgress"]] = relationship(
        "ActionProgress",
        back_populates="plan",
        cascade="all, delete-orphan",
    )
    
    # Indexes for multi-tenant queries
    __table_args__ = (
        Index("idx_plan_tenant_plan", "tenant_id", "plan_id"),
        Index("idx_plan_status", "status"),
        Index("idx_plan_created", "created_at"),
    )


class ActionProgress(Base):
    """Track individual action execution progress (STUB).
    
    Multi-tenant table with RLS enforced at database level.
    Each action belongs to a plan and tracks detailed execution state.
    """
    __tablename__ = "action_progress"
    
    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Foreign key to plan
    plan_id: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("plan_progress.plan_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Business identifiers
    action_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    tenant_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Action metadata
    action_name: Mapped[str] = mapped_column(String(500), nullable=False)
    action_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    action_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Execution state
    status: Mapped[ActionStatus] = mapped_column(
        SQLEnum(ActionStatus, name="action_status_enum"),
        nullable=False,
        default=ActionStatus.PENDING,
    )
    
    # Execution details
    assigned_to: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # Worker/Tool ID
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    # Results and error tracking
    result: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Relationships
    plan: Mapped["PlanProgress"] = relationship("PlanProgress", back_populates="actions")
    
    # Indexes for multi-tenant queries
    __table_args__ = (
        Index("idx_action_tenant_action", "tenant_id", "action_id"),
        Index("idx_action_plan", "plan_id"),
        Index("idx_action_status", "status"),
        Index("idx_action_created", "created_at"),
    )
