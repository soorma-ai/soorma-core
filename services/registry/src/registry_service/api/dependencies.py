"""
API dependencies for authentication and request context.

Registry Service Authentication Model:
  The Registry Service is scoped to the **developer's own tenant**.
  It does NOT accept or use end-user tenant/session identity.

  Conceptual model (see ARCHITECTURE_PATTERNS.md Section 1):
    - Developer Tenant: who built the agents (this service's scope)
    - User Tenant:      the developer's end-client's tenant   }--> used by Memory, Tracker, Bus
    - User ID:          identity within a user tenant         }

  v0.7.x pattern: custom X-Tenant-ID header (developer tenant)
  v0.8.0+: will be replaced with API Key / machine token validation
"""
from uuid import UUID
from fastapi import Header, HTTPException, status


async def get_developer_tenant_id(
    x_tenant_id: str = Header(..., description="Developer Tenant ID (X-Tenant-ID header)")
) -> UUID:
    """
    Extract the developer's tenant_id from the X-Tenant-ID request header.

    The Registry Service is scoped to the developer's own tenant — agents and
    events registered here belong to the developer, not to any end-user session.

    This is the v0.7.x development authentication pattern. In v0.8.0+ this will
    be replaced with API Key / machine token validation.

    Args:
        x_tenant_id: Developer tenant UUID from X-Tenant-ID header

    Returns:
        developer_tenant_id as UUID

    Raises:
        HTTPException: 400 if header is missing or not a valid UUID
        HTTPException: 401 if authentication fails (future API Key validation)
    """
    try:
        return UUID(x_tenant_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid UUID format in X-Tenant-ID header: {str(e)}"
        )
