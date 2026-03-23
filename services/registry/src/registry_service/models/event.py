"""
SQLAlchemy model for event registry.
"""
from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy import Integer, String, DateTime, Text, JSON, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from .base import Base


class EventTable(Base):
    """Event definition storage."""
    __tablename__ = "events"
    
    # Note: Unique constraint (event_name, tenant_id) created by migration 003
    # SQLAlchemy will use the constraint from the database
    __table_args__ = ()
    
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
    
    # Event identification
    event_name: Mapped[str] = mapped_column(
        String(255), 
        nullable=False, 
        index=True
    )
    topic: Mapped[str] = mapped_column(
        String(100), 
        nullable=False, 
        index=True
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    
    # JSON schemas stored as JSON columns
    payload_schema: Mapped[Dict[str, Any]] = mapped_column(
        JSON, 
        nullable=False
    )
    response_schema: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON, 
        nullable=True
    )
    
    # Developer tenancy and schema registry columns (added in migration 003, renamed in migration 004)
    # Registry is scoped to the developer's own tenant — not end-user sessions.
    owner_agent_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        comment="Agent ID that owns/registered this event"
    )
    platform_tenant_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
        comment="Platform tenant identifier — registry is developer-scoped, not user-session-scoped"
    )
    payload_schema_name: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        comment="Reference to payload_schemas.schema_name"
    )
    response_schema_name: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Reference to payload_schemas.schema_name for response"
    )
    
    def __repr__(self) -> str:
        return f"<EventTable(id={self.id}, event_name={self.event_name}, topic={self.topic})>"
