"""
CRUD operations for payload schema registry.

STUB: All method signatures defined with NotImplementedError.
GREEN: Real implementation in Task 3.1.
"""
from typing import List, Optional
from uuid import UUID
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
        raise NotImplementedError("SchemaCRUD.create_schema not yet implemented")

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
        raise NotImplementedError("SchemaCRUD.get_schema_by_name_version not yet implemented")

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
        raise NotImplementedError("SchemaCRUD.get_latest_schema_by_name not yet implemented")

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
        raise NotImplementedError("SchemaCRUD.list_schemas_by_owner not yet implemented")

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
        raise NotImplementedError("SchemaCRUD.list_all_schemas not yet implemented")


# Module-level singleton (matches pattern of agent_crud, event_crud)
schema_crud = SchemaCRUD()
