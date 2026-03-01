"""
Service layer for schema registry operations.
"""
from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from soorma_common import PayloadSchema, PayloadSchemaResponse
from ..crud import schema_crud
from ..models import PayloadSchemaTable


def _table_to_dto(row: PayloadSchemaTable) -> PayloadSchema:
    """Map a PayloadSchemaTable ORM row to a PayloadSchema DTO.

    Args:
        row: ORM row from the payload_schemas table

    Returns:
        PayloadSchema Pydantic DTO
    """
    return PayloadSchema(
        schema_name=row.schema_name,
        version=row.version,
        json_schema=row.json_schema,
        description=row.description,
        owner_agent_id=row.owner_agent_id,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


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
        # Decision D1: schemas are immutable once registered — duplicate = 409 Conflict
        existing = await schema_crud.get_schema_by_name_version(
            db, schema.schema_name, schema.version, tenant_id
        )
        if existing is not None:
            raise ValueError(
                f"Schema '{schema.schema_name}@{schema.version}' already exists for this tenant"
            )

        await schema_crud.create_schema(db, schema, tenant_id)
        await db.commit()
        return PayloadSchemaResponse(
            schema_name=schema.schema_name,
            version=schema.version,
            success=True,
            message=f"Schema '{schema.schema_name}@{schema.version}' registered successfully.",
        )

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
        row = await schema_crud.get_latest_schema_by_name(db, schema_name, tenant_id)
        return _table_to_dto(row) if row is not None else None

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
        row = await schema_crud.get_schema_by_name_version(db, schema_name, version, tenant_id)
        return _table_to_dto(row) if row is not None else None

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
        if owner_agent_id is not None:
            rows = await schema_crud.list_schemas_by_owner(db, owner_agent_id, tenant_id)
        else:
            rows = await schema_crud.list_all_schemas(db, tenant_id)
        return [_table_to_dto(row) for row in rows]
