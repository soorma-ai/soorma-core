"""
TenancyMiddleware — per-request identity extraction from HTTP headers.

Starlette BaseHTTPMiddleware that reads all three identity dimensions from
incoming request headers and stores them on request.state for downstream
FastAPI dependency functions.

Does NOT call set_config — DB connection management belongs in get_tenanted_db
(Q1 design decision: split responsibility between middleware and dependency).
"""
from typing import Callable

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from soorma_common.tenancy import DEFAULT_PLATFORM_TENANT_ID

_BYPASS_PATHS = frozenset(["/health", "/docs", "/openapi.json", "/redoc"])


class TenancyMiddleware(BaseHTTPMiddleware):
    """
    Middleware that extracts platform_tenant_id, service_tenant_id, and
    service_user_id from HTTP headers and stores them on request.state.

    Register in each consuming service's main.py:
        app.add_middleware(TenancyMiddleware)

    Does NOT open or interact with a database connection (BR-U2-01).
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Extract identity headers and store on request.state, then call call_next.

        Header mapping:
            X-Tenant-ID          → request.state.platform_tenant_id  (default: DEFAULT_PLATFORM_TENANT_ID)
            X-Service-Tenant-ID  → request.state.service_tenant_id   (default: None)
            X-User-ID            → request.state.service_user_id     (default: None)

        Health/docs paths (/health, /docs, /openapi.json, /redoc) bypass extraction.
        """
        if request.url.path in _BYPASS_PATHS:
            return await call_next(request)

        request.state.platform_tenant_id = (
            request.headers.get("x-tenant-id") or DEFAULT_PLATFORM_TENANT_ID
        )
        request.state.service_tenant_id = request.headers.get("x-service-tenant-id") or None
        request.state.service_user_id = request.headers.get("x-user-id") or None

        return await call_next(request)
