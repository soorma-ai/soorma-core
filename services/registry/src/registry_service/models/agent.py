"""
SQLAlchemy models for agent registry.
"""
from datetime import datetime
from typing import List
from uuid import UUID
from sqlalchemy import Integer, String, DateTime, Text, ForeignKey, JSON, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from .base import Base


class AgentTable(Base):
    """Agent definition storage."""
    __tablename__ = "agents"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        onupdate=func.now()
    )
    last_heartbeat: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
        comment="Last time agent refreshed its registration"
    )
    
    # Agent identification
    agent_id: Mapped[str] = mapped_column(
        String(255), 
        nullable=False,
        index=True,
        comment="Agent ID (unique per tenant)"
    )
    name: Mapped[str] = mapped_column(
        String(255), 
        nullable=False,
        index=True
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Event associations stored as JSON for SQLite compatibility
    # Will use ARRAY for PostgreSQL when available
    consumed_events: Mapped[List[str]] = mapped_column(
        JSON,
        nullable=False
    )
    produced_events: Mapped[List[str]] = mapped_column(
        JSON,
        nullable=False
    )
    
    # Developer tenancy column (added in migration 003)
    # Registry is scoped to the developer's own tenant — not end-user sessions.
    # See ARCHITECTURE_PATTERNS.md Section 1 for the developer-tenant vs user-tenant distinction.
    tenant_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True, native_uuid=True),  # native_uuid=True: PostgreSQL native UUID; SQLite CHAR(32) TEXT affinity (avoids numeric coercion bug)
        nullable=False,
        index=True,
        comment="Developer tenant identifier — registry is developer-scoped, not user-session-scoped"
    )
    version: Mapped[str] = mapped_column(
        String(50),
        nullable=True,
        server_default="1.0.0",
        comment="Agent version for compatibility tracking"
    )
    
    # Relationship to capabilities
    capabilities: Mapped[List["AgentCapabilityTable"]] = relationship(
        "AgentCapabilityTable",
        back_populates="agent",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<AgentTable(id={self.id}, agent_id={self.agent_id}, name={self.name})>"


class AgentCapabilityTable(Base):
    """Agent capability storage."""
    __tablename__ = "agent_capabilities"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    agent_table_id: Mapped[int] = mapped_column(
        Integer, 
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    task_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Event contract for this capability
    consumed_event: Mapped[str] = mapped_column(
        String(255), 
        nullable=False,
        index=True,
        comment="Event that triggers this capability"
    )
    produced_events: Mapped[List[str]] = mapped_column(
        JSON,
        nullable=False,
        comment="Events this capability can produce"
    )
    
    # Relationship back to agent
    agent: Mapped["AgentTable"] = relationship(
        "AgentTable",
        back_populates="capabilities"
    )
    
    def __repr__(self) -> str:
        return f"<AgentCapabilityTable(id={self.id}, task_name={self.task_name}, consumed_event={self.consumed_event})>"
