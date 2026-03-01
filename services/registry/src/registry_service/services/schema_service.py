"""
Service layer for schema registry operations.

STUB: All method signatures defined with NotImplementedError.
GREEN: Real implementation in Task 3.2.
"""
from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from soorma_common import PayloadSchema, PayloadSchemaResponse
from ..crud import schema_crud


class SchemaRegistryService:
    """Business logic for payload schema registration and retrieval."""

    @staticmethod
    async def register_schema(
        db: AsyncSession,
        schema: PayloadSchema,
        tenant_id: UUID,
    ) -> PayloadSchemaResponse:
        """
        Register a new payload schema.

        Returns 409-triggering duplicate error if (schema_name, version, tenant_id)
        already exists (Decision D1: schemas are immutable once registered).

        Args:
            db: Database session
            schema: Schema definition to register
            tenant_id: Developer tenant UUID

        Returns:
            PayloadSchemaResponse with success=True or raises ValueError on duplicate
        """
        raise NotImplementedError("SchemaRegistryService.register_schema not yet implemented")

    @staticmethod
    async def get_schema_by_name(
        db: AsyncSession,
        schema_name: str,
        tenant_id: UUID,
    ) -> Optional[PayloadSchema]:
        """
        Retrieve the latest version of a schema by name.

        Args:
            db: Database session
            schema_name: Schema name to look up
            tenant_id: Developer tenant UUID

        Returns:
            PayloadSchema DTO if found, None otherwise
        """
        raise NotImplementedError("SchemaRegistryService.get_schema_by_name not yet implemented")

    @staticmethod
    async def get_schema_by_name_version(
        db: AsyncSession,
        schema_name: str,
        version: str,
        tenant_id: UUID,
    ) -> Optional[PayloadSchema]:
        """
        Retrieve a specific (name, version) schema.

        Args:
            db: Database session
            schema_name: Schema name
            version: Semantic version string
            tenant_id: Developer tenant UUID

        Returns:
            PayloadSchema DTO if found, None otherwise
        """
        raise NotImplementedError("SchemaRegistryService.get_schema_by_name_version not yet implemented")

    @staticmethod
    async def list_schemas(
        db: AsyncSession,
        tenant_id: UUID,
        owner_agent_id: Optional[str] = None,
    ) -> List[PayloadSchema]:
        """
        List schemas for a tenant, optionally filtered by owner agent.

        Args:
            db: Database session
            tenant_id: Developer tenant UUID
            owner_agent_id: Optional agent ID filter

        Returns:
            List of PayloadSchema DTOs
        """
        raise NotImplementedError("SchemaRegistryService.list_schemas not yet implemented")
