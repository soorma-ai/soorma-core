"""
SQLAlchemy model for payload schema registry.
"""
from datetime import datetime
from typing import Dict, Any, Optional
from uuid import UUID, uuid4
from sqlalchemy import String, DateTime, Text, JSON, Uuid
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from .base import Base


class PayloadSchemaTable(Base):
    """
    Payload schema storage with versioning and multi-tenancy support.

    Multi-tenancy: tenant_id uses Uuid(as_uuid=True) — same pattern as AgentTable.
    Primary key: uses Python-side uuid4() for SQLite compatibility (Decision D4 in action plan).
    """
    __tablename__ = "payload_schemas"

    # Primary key: Python-side uuid4() so PostgreSQL and SQLite both work correctly.
    # gen_random_uuid() is PostgreSQL-only and breaks SQLite test runs.
    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True, native_uuid=True),
        primary_key=True,
        default=uuid4,
        comment="Primary key (UUID)"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        comment="Creation timestamp"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        comment="Last update timestamp"
    )
    
    # Schema identification (unique constraint: schema_name, version, tenant_id)
    schema_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Unique schema name (e.g., 'research_request_v1')"
    )
    version: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Semantic version (e.g., '1.0.0')"
    )
    
    # Schema content (JSON validation handled in service layer)
    json_schema: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        comment="JSON Schema definition"
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Human-readable description"
    )
    
    # Ownership (no FK constraint — microservices independence; see action plan decision D7)
    owner_agent_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Agent ID that owns this schema (no FK to agents table)"
    )
    
    # Developer tenancy (registry is scoped to the developer, not end-user sessions)
    platform_tenant_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
        comment="Platform tenant identifier — registry is developer-scoped, not user-session-scoped"
    )

    def __repr__(self) -> str:
        """String representation."""
        return f"<PayloadSchemaTable(id={self.id}, schema_name={self.schema_name}, version={self.version}, platform_tenant_id={self.platform_tenant_id})>"
