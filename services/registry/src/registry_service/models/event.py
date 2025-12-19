"""
SQLAlchemy model for event registry.
"""
from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy import Integer, String, DateTime, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from .base import Base


class EventTable(Base):
    """Event definition storage."""
    __tablename__ = "events"
    
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
        unique=True, 
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
    
    def __repr__(self) -> str:
        return f"<EventTable(id={self.id}, event_name={self.event_name}, topic={self.topic})>"
