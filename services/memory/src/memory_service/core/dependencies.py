"""FastAPI dependencies for common request handling."""

from uuid import UUID
from fastapi import Request, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from memory_service.core.database import get_db, set_session_context
from memory_service.core.middleware import get_tenant_id, get_user_id


class TenantContext:
    """Encapsulates tenant/user context with database session."""
    
    def __init__(self, tenant_id: UUID, user_id: UUID, db: AsyncSession):
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.db = db


async def get_tenant_context(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> TenantContext:
    """
    Dependency that extracts tenant/user IDs and sets session context.
    
    This eliminates boilerplate in every endpoint:
    - Parses tenant_id and user_id from request
    - Calls set_session_context for PostgreSQL RLS
    - Returns a clean context object
    
    Usage:
        @router.post("/endpoint")
        async def my_endpoint(
            data: MyRequest,
            context: TenantContext = Depends(get_tenant_context),
        ):
            result = await service.do_something(context.db, context.tenant_id, data)
            return result
    """
    from fastapi import HTTPException, status
    
    tenant_id = UUID(get_tenant_id(request))
    
    # Get user_id from middleware state (extracted from query params or headers)
    user_id_str = get_user_id(request)
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="user_id is required (provide as query parameter or X-User-ID header)"
        )
    
    try:
        user_id = UUID(user_id_str)
    except (ValueError, AttributeError) as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Invalid user_id format: {user_id_str}"
        )
    
    await set_session_context(db, str(tenant_id), str(user_id))
    
    return TenantContext(tenant_id, user_id, db)
