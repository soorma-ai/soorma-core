"""Authentication and tenancy middleware."""

import jwt
from typing import Optional
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware

from memory_service.core.config import settings


class TenancyMiddleware(BaseHTTPMiddleware):
    """Middleware to extract tenant and user context from JWT tokens."""

    async def dispatch(self, request: Request, call_next):
        """Process request and extract tenant/user context."""
        # Skip middleware for health checks and docs
        if request.url.path in ["/health", "/docs", "/openapi.json", "/redoc"]:
            return await call_next(request)

        # Extract tenant_id and user_id
        tenant_id = None
        user_id = None

        if settings.is_local_testing:
            # Local development mode - use default tenant
            tenant_id = settings.default_tenant_id
            user_id = settings.default_user_id
        else:
            # Production mode - extract from JWT
            auth_header = request.headers.get("Authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Missing or invalid authorization header",
                )

            token = auth_header.split(" ")[1]
            try:
                payload = jwt.decode(
                    token,
                    settings.jwt_secret or "",
                    algorithms=[settings.jwt_algorithm],
                )
                tenant_id = payload.get("tenant_id")
                user_id = payload.get("user_id") or payload.get("sub")

                if not tenant_id or not user_id:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Token missing tenant_id or user_id",
                    )
            except jwt.InvalidTokenError as e:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"Invalid token: {str(e)}",
                )

        # Store in request state
        request.state.tenant_id = tenant_id
        request.state.user_id = user_id

        return await call_next(request)


def get_tenant_id(request: Request) -> str:
    """Get tenant ID from request state."""
    return getattr(request.state, "tenant_id", settings.default_tenant_id)


def get_user_id(request: Request) -> str:
    """Get user ID from request state."""
    return getattr(request.state, "user_id", settings.default_user_id)
