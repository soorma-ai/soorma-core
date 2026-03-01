"""
CRUD operations for payload schema registry.
"""
from typing import List, Optional
from uuid import UUID, uuid4
from datetime import datetime, timezone
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from soorma_common import PayloadSchema
from ..models import PayloadSchemaTable


class SchemaCRUD:
    """CRUD operations for the payload_schemas table."""

    async def create_schema(
        self,
        db: AsyncSession,
        schema: PayloadSchema,
        tenant_id: UUID,
    ) -> PayloadSchemaTable:
        """
        Insert a new payload schema row.

        Args:
            db: Database session
            schema: PayloadSchema DTO to persist
            tenant_id: Developer tenant UUID

        Returns:
            Newly created PayloadSchemaTable instance
        """
        row = PayloadSchemaTable(
            id=uuid4(),
            # Use Python-side datetime for microsecond precision — SQLite's func.now()
            # only has second precision, making get_latest_schema ordering unreliable
            # when multiple schemas are inserted in the same second.
            created_at=datetime.now(timezone.utc),
            schema_name=schema.schema_name,
            version=schema.version,
            json_schema=schema.json_schema,
            description=schema.description,
            owner_agent_id=schema.owner_agent_id,
            tenant_id=tenant_id,
        )
        db.add(row)
        await db.flush()
        return row

    async def get_schema_by_name_version(
        self,
        db: AsyncSession,
        schema_name: str,
        version: str,
        tenant_id: UUID,
    ) -> Optional[PayloadSchemaTable]:
        """
        Look up a schema by (schema_name, version, tenant_id).

        Args:
            db: Database session
            schema_name: Schema name
            version: Semantic version string
            tenant_id: Developer tenant UUID

        Returns:
            PayloadSchemaTable if found, None otherwise
        """
        result = await db.execute(
            select(PayloadSchemaTable).where(
                PayloadSchemaTable.schema_name == schema_name,
                PayloadSchemaTable.version == version,
                PayloadSchemaTable.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_latest_schema_by_name(
        self,
        db: AsyncSession,
        schema_name: str,
        tenant_id: UUID,
    ) -> Optional[PayloadSchemaTable]:
        """
        Look up the most recently created schema with the given name.

        Args:
            db: Database session
            schema_name: Schema name
            tenant_id: Developer tenant UUID

        Returns:
            PayloadSchemaTable if found, None otherwise
        """
        result = await db.execute(
            select(PayloadSchemaTable)
            .where(
                PayloadSchemaTable.schema_name == schema_name,
                PayloadSchemaTable.tenant_id == tenant_id,
            )
            .order_by(desc(PayloadSchemaTable.created_at))
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def list_schemas_by_owner(
        self,
        db: AsyncSession,
        owner_agent_id: str,
        tenant_id: UUID,
    ) -> List[PayloadSchemaTable]:
        """
        Return all schemas belonging to a specific agent.

        Args:
            db: Database session
            owner_agent_id: Agent ID that owns the schemas
            tenant_id: Developer tenant UUID

        Returns:
            List of PayloadSchemaTable rows
        """
        result = await db.execute(
            select(PayloadSchemaTable).where(
                PayloadSchemaTable.owner_agent_id == owner_agent_id,
                PayloadSchemaTable.tenant_id == tenant_id,
            ).order_by(PayloadSchemaTable.schema_name)
        )
        return list(result.scalars().all())

    async def list_all_schemas(
        self,
        db: AsyncSession,
        tenant_id: UUID,
    ) -> List[PayloadSchemaTable]:
        """
        Return all schemas for a tenant.

        Args:
            db: Database session
            tenant_id: Developer tenant UUID

        Returns:
            List of all PayloadSchemaTable rows for the tenant
        """
        result = await db.execute(
            select(PayloadSchemaTable)
            .where(PayloadSchemaTable.tenant_id == tenant_id)
            .order_by(PayloadSchemaTable.schema_name)
        )
        return list(result.scalars().all())


# Module-level singleton (matches pattern of agent_crud, event_crud)
schema_crud = SchemaCRUD()
