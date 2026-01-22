"""Tenancy middleware for single-tenant mode."""

from typing import Optional
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from memory_service.core.config import settings


class TenancyMiddleware(BaseHTTPMiddleware):
    """
    Middleware for single-tenant mode.
    
    Currently Memory Service operates in single-tenant mode with no authentication.
    - tenant_id: Always uses default tenant (single-tenant mode)
    - user_id: Extracted from query parameters (no auth required)
    - agent_id: Extracted from query parameters
    
    Future: Multi-tenant authentication will be handled by Identity Service.
    """

    async def dispatch(self, request: Request, call_next):
        """Process request in single-tenant mode."""
        # Skip middleware for health checks and docs
        if request.url.path in ["/health", "/docs", "/openapi.json", "/redoc"]:
            return await call_next(request)

        # Single-tenant mode - always use default tenant
        tenant_id = settings.default_tenant_id
        
        # Extract user_id from query params (backward compatibility) or headers
        user_id = request.query_params.get("user_id") or request.headers.get("X-User-ID")
        
        # Store in request state
        request.state.tenant_id = tenant_id
        request.state.user_id = user_id

        return await call_next(request)


def get_tenant_id(request: Request) -> str:
    """Get tenant ID from request state (always default in single-tenant mode)."""
    return getattr(request.state, "tenant_id", settings.default_tenant_id)


def get_user_id(request: Request) -> Optional[str]:
    """
    Get user ID from request state.
    
    Note: In v0.5.0, user_id comes from query parameters, not from middleware.
    This function exists for backward compatibility but returns None.
    Endpoints should get user_id from query parameters directly.
    """
    return getattr(request.state, "user_id", None)
