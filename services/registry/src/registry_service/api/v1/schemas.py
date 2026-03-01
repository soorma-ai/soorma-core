"""
API endpoints for payload schema registry.
"""
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Query, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from soorma_common import (
    PayloadSchema,
    PayloadSchemaRegistrationRequest,
    PayloadSchemaResponse,
    PayloadSchemaListResponse,
)
from ...services import SchemaRegistryService
from ...core.database import get_db
from ..dependencies import get_developer_tenant_id

router = APIRouter(prefix="/schemas", tags=["schemas"])


@router.post("", response_model=PayloadSchemaResponse)
async def register_schema(
    request: PayloadSchemaRegistrationRequest,
    db: AsyncSession = Depends(get_db),
    developer_tenant_id: UUID = Depends(get_developer_tenant_id),
) -> PayloadSchemaResponse:
    """
    Register a new payload schema.

    Returns 409 Conflict if the same (schema_name, version) already exists for this tenant.
    Schemas are immutable once registered — new version = new registration (Decision D1).

    Args:
        request: Wrapped PayloadSchema definition
        db: Database session (injected)
        developer_tenant_id: Developer tenant UUID from X-Tenant-ID header

    Returns:
        PayloadSchemaResponse with success flag
    """
    try:
        return await SchemaRegistryService.register_schema(
            db, request.schema, developer_tenant_id
        )
    except ValueError as exc:
        # Duplicate (name, version, tenant) → 409 Conflict
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )


@router.get("/{schema_name}/versions/{version}", response_model=PayloadSchema)
async def get_schema_by_version(
    schema_name: str,
    version: str,
    db: AsyncSession = Depends(get_db),
    developer_tenant_id: UUID = Depends(get_developer_tenant_id),
) -> PayloadSchema:
    """
    Retrieve a specific (schema_name, version) payload schema.

    Args:
        schema_name: Schema name
        version: Semantic version string (e.g. '1.0.0')
        db: Database session (injected)
        developer_tenant_id: Developer tenant UUID from X-Tenant-ID header

    Returns:
        PayloadSchema DTO

    Raises:
        HTTPException 404 if not found
    """
    schema = await SchemaRegistryService.get_schema_by_name_version(
        db, schema_name, version, developer_tenant_id
    )
    if schema is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schema '{schema_name}@{version}' not found",
        )
    return schema


@router.get("/{schema_name}", response_model=PayloadSchema)
async def get_latest_schema(
    schema_name: str,
    db: AsyncSession = Depends(get_db),
    developer_tenant_id: UUID = Depends(get_developer_tenant_id),
) -> PayloadSchema:
    """
    Retrieve the latest version of a schema by name.

    Args:
        schema_name: Schema name
        db: Database session (injected)
        developer_tenant_id: Developer tenant UUID from X-Tenant-ID header

    Returns:
        PayloadSchema DTO (latest version by created_at)

    Raises:
        HTTPException 404 if not found
    """
    schema = await SchemaRegistryService.get_schema_by_name(
        db, schema_name, developer_tenant_id
    )
    if schema is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schema '{schema_name}' not found",
        )
    return schema


@router.get("", response_model=PayloadSchemaListResponse)
async def list_schemas(
    owner_agent_id: Optional[str] = Query(None, description="Filter by owner agent ID"),
    db: AsyncSession = Depends(get_db),
    developer_tenant_id: UUID = Depends(get_developer_tenant_id),
) -> PayloadSchemaListResponse:
    """
    List payload schemas for the tenant, optionally filtered by owner agent.

    Args:
        owner_agent_id: Optional agent ID filter
        db: Database session (injected)
        developer_tenant_id: Developer tenant UUID from X-Tenant-ID header

    Returns:
        PayloadSchemaListResponse with schemas and count
    """
    schemas = await SchemaRegistryService.list_schemas(
        db, developer_tenant_id, owner_agent_id
    )
    return PayloadSchemaListResponse(schemas=schemas, count=len(schemas))
