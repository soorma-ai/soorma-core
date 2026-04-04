"""Tenancy middleware with JWT-first coexistence behavior.

Resolution order:
1. If bearer JWT exists, validate and use JWT claims for request identity.
2. If JWT is absent, fall back to legacy tenancy headers.

Middleware never calls set_config; DB session/RLS activation remains in
dependency utilities.
"""
import os
from typing import Callable

import jwt
from fastapi import HTTPException
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from starlette.responses import Response

from soorma_common.tenancy import DEFAULT_PLATFORM_TENANT_ID

_BYPASS_PATHS = frozenset(["/health", "/docs", "/openapi.json", "/redoc"])
_AUTHORIZATION_HEADER = "authorization"
_BEARER_PREFIX = "bearer "
_JWT_SECRET_ENV = "SOORMA_AUTH_JWT_SECRET"
_JWT_ISSUER_ENV = "SOORMA_AUTH_JWT_ISSUER"
_JWT_AUDIENCE_ENV = "SOORMA_AUTH_JWT_AUDIENCE"


class TenancyMiddleware(BaseHTTPMiddleware):
    """
    Middleware that extracts platform_tenant_id, service_tenant_id, and
    service_user_id from HTTP headers and stores them on request.state.

    Register in each consuming service's main.py:
        app.add_middleware(TenancyMiddleware)

    Does NOT open or interact with a database connection (BR-U2-01).
    """

    def _extract_bearer_token(self, request: Request) -> str | None:
        """Extract bearer token from Authorization header when present."""
        auth_value = request.headers.get(_AUTHORIZATION_HEADER)
        if not auth_value:
            return None
        lowered = auth_value.lower()
        if not lowered.startswith(_BEARER_PREFIX):
            return None
        return auth_value[len(_BEARER_PREFIX):].strip() or None

    def _resolve_identity_from_jwt(self, token: str) -> tuple[str, str | None, str | None]:
        """Resolve platform/service identity tuple from JWT claims.

        JWT is authoritative when present; callers must never fall back to headers
        after JWT parse/validation failure.
        """
        secret = os.environ.get(_JWT_SECRET_ENV)
        if not secret:
            raise HTTPException(
                status_code=401,
                detail="JWT validation not configured",
            )

        issuer = os.environ.get(_JWT_ISSUER_ENV)
        audience = os.environ.get(_JWT_AUDIENCE_ENV)

        decode_kwargs: dict[str, object] = {
            "key": secret,
            "algorithms": ["HS256"],
            "options": {
                "require": ["exp", "platform_tenant_id"],
                "verify_aud": bool(audience),
                "verify_iss": bool(issuer),
            },
        }
        if audience:
            decode_kwargs["audience"] = audience
        if issuer:
            decode_kwargs["issuer"] = issuer

        try:
            claims = jwt.decode(token, **decode_kwargs)
        except jwt.PyJWTError as exc:
            raise HTTPException(status_code=401, detail="Invalid JWT") from exc

        platform_tenant_id = str(claims.get("platform_tenant_id") or "").strip()
        if not platform_tenant_id:
            raise HTTPException(status_code=401, detail="Invalid JWT")

        service_tenant = claims.get("service_tenant_id")
        service_user = claims.get("service_user_id")
        service_tenant_id = str(service_tenant).strip() if service_tenant is not None else None
        service_user_id = str(service_user).strip() if service_user is not None else None

        return platform_tenant_id, service_tenant_id or None, service_user_id or None

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

        bearer_token = self._extract_bearer_token(request)
        if bearer_token is not None:
            try:
                (
                    request.state.platform_tenant_id,
                    request.state.service_tenant_id,
                    request.state.service_user_id,
                ) = self._resolve_identity_from_jwt(bearer_token)
            except HTTPException as exc:
                return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
        else:
            request.state.platform_tenant_id = (
                request.headers.get("x-tenant-id") or DEFAULT_PLATFORM_TENANT_ID
            )
            request.state.service_tenant_id = request.headers.get("x-service-tenant-id") or None
            request.state.service_user_id = request.headers.get("x-user-id") or None

        return await call_next(request)
