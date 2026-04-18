"""Tenancy middleware for bearer-authenticated request identity.

Resolution order:
1. If bearer JWT exists, validate it and project claims into request state.
2. If a trusted identity admin header exists, allow the documented admin bypass.
3. Otherwise fail closed with missing-bearer-token authentication errors.

Middleware never calls set_config; DB session/RLS activation remains in
dependency utilities.
"""
import json
import os
import time
from typing import Any, Callable
import urllib.request

import jwt
from jwt.algorithms import RSAAlgorithm
from fastapi import FastAPI
from fastapi import HTTPException
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from starlette.responses import Response

from soorma_common.tenancy import DEFAULT_PLATFORM_TENANT_ID

_BYPASS_PATHS = frozenset([
    "/health",
    "/docs",
    "/openapi.json",
    "/redoc",
    "/v1/identity/.well-known/openid-configuration",
    "/v1/identity/.well-known/jwks.json",
])
_AUTHORIZATION_HEADER = "authorization"
_BEARER_PREFIX = "bearer "
_IDENTITY_ADMIN_HEADER = "x-identity-admin-key"
_JWT_SECRET_ENV = "SOORMA_AUTH_JWT_SECRET"
_JWT_ISSUER_ENV = "SOORMA_AUTH_JWT_ISSUER"
_JWT_AUDIENCE_ENV = "SOORMA_AUTH_JWT_AUDIENCE"
_JWT_PUBLIC_KEYS_ENV = "SOORMA_AUTH_JWT_PUBLIC_KEYS_JSON"
_JWT_PUBLIC_KEY_PEM_ENV = "SOORMA_AUTH_JWT_PUBLIC_KEY_PEM"
_JWT_PUBLIC_KEY_ID_ENV = "SOORMA_AUTH_JWT_PUBLIC_KEY_ID"
_JWKS_URL_ENV = "SOORMA_AUTH_JWKS_URL"
_JWKS_JSON_ENV = "SOORMA_AUTH_JWKS_JSON"
_JWKS_CACHE_TTL_ENV = "SOORMA_AUTH_JWKS_CACHE_TTL_SECONDS"
_OPENID_CONFIGURATION_URL_ENV = "SOORMA_AUTH_OPENID_CONFIGURATION_URL"
_OPENID_CONFIGURATION_JSON_ENV = "SOORMA_AUTH_OPENID_CONFIGURATION_JSON"
_ALLOWED_PRINCIPAL_TYPES = frozenset(
    {"admin", "service", "agent", "user", "developer", "planner", "worker", "tool"}
)
_JWKS_CACHE_TIMEOUT_SECONDS = 2.0
_DEFAULT_JWKS_CACHE_TTL_SECONDS = 300

_JWKS_CACHE: dict[str, Any] = {
    "url": None,
    "expires_at": 0.0,
    "keys": {},
}

_OPENID_CONFIGURATION_CACHE: dict[str, Any] = {
    "url": None,
    "expires_at": 0.0,
    "payload": None,
}


def configure_platform_tenant_openapi(
    app: FastAPI,
    *,
    scheme_name: str = "PlatformTenantHeader",
    header_name: str = "X-Tenant-ID",
    include_paths: set[str] | None = None,
    add_global_security: bool = True,
) -> None:
    """Expose platform tenant header in Swagger/OpenAPI for compatibility flows.

    This helper documents ``X-Tenant-ID`` for trusted-admin or compatibility
    scenarios. Normal secured service traffic authenticates with bearer tokens.
    """

    original_openapi = app.openapi

    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema

        schema = original_openapi()
        components = schema.setdefault("components", {})
        security_schemes = components.setdefault("securitySchemes", {})
        security_schemes[scheme_name] = {
            "type": "apiKey",
            "in": "header",
            "name": header_name,
            "description": "Required Soorma platform tenant context header.",
        }

        if add_global_security:
            security = schema.setdefault("security", [])
            tenant_security = {scheme_name: []}
            if tenant_security not in security:
                security.append(tenant_security)

        # Also expose X-Tenant-ID as an operation header parameter so it appears
        # directly in Swagger "Try it out" forms.
        paths = schema.get("paths", {})
        for path, methods in paths.items():
            if path == "/health":
                continue
            if include_paths is not None and path not in include_paths:
                continue
            if not isinstance(methods, dict):
                continue

            for method_name, operation in methods.items():
                if method_name.lower() not in {
                    "get",
                    "post",
                    "put",
                    "patch",
                    "delete",
                    "options",
                    "head",
                    "trace",
                }:
                    continue
                if not isinstance(operation, dict):
                    continue

                parameters = operation.setdefault("parameters", [])
                already_present = any(
                    isinstance(param, dict)
                    and param.get("in") == "header"
                    and str(param.get("name", "")).lower() == header_name.lower()
                    for param in parameters
                )
                if already_present:
                    continue

                parameters.append(
                    {
                        "name": header_name,
                        "in": "header",
                        "required": False,
                        "schema": {"type": "string"},
                        "description": (
                            "Soorma platform tenant context header. "
                            "Use this for tenant-scoped API calls."
                        ),
                    }
                )

        app.openapi_schema = schema
        return app.openapi_schema

    app.openapi = custom_openapi


class TenancyMiddleware(BaseHTTPMiddleware):
    """
    Middleware that extracts platform_tenant_id, service_tenant_id, and
    service_user_id from HTTP headers and stores them on request.state.

    Register in each consuming service's main.py:
        app.add_middleware(TenancyMiddleware)

    Does NOT open or interact with a database connection (BR-U2-01).
    """

    def _is_identity_admin_request(self, request: Request) -> bool:
        """Return True for trusted admin-key identity-service control-plane requests."""
        return bool(str(request.headers.get(_IDENTITY_ADMIN_HEADER) or "").strip())

    def _extract_bearer_token(self, request: Request) -> str | None:
        """Extract bearer token from Authorization header when present."""
        auth_value = request.headers.get(_AUTHORIZATION_HEADER)
        if not auth_value:
            return None
        lowered = auth_value.lower()
        if not lowered.startswith(_BEARER_PREFIX):
            return None
        return auth_value[len(_BEARER_PREFIX):].strip() or None

    def _decode_claims(
        self,
        token: str,
        key: Any,
        algorithm: str,
        issuer: str | None,
        audience: str | None,
    ) -> dict[str, Any] | None:
        """Decode JWT claims with standard auth constraints."""
        decode_kwargs: dict[str, object] = {
            "key": key,
            "algorithms": [algorithm],
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
            return jwt.decode(token, **decode_kwargs)
        except jwt.PyJWTError:
            return None

    def _load_static_rs256_fallback_keys(self) -> dict[str, str]:
        """Load static RS256 verifier keys as bounded fallback."""
        keyring_raw = str(os.environ.get(_JWT_PUBLIC_KEYS_ENV) or "").strip()
        if keyring_raw:
            try:
                parsed = json.loads(keyring_raw)
                if isinstance(parsed, dict):
                    normalized = {
                        str(kid).strip(): str(key).strip()
                        for kid, key in parsed.items()
                        if str(kid).strip() and str(key).strip()
                    }
                    if normalized:
                        return normalized
            except json.JSONDecodeError:
                pass

        pem_key = str(os.environ.get(_JWT_PUBLIC_KEY_PEM_ENV) or "").strip()
        if pem_key:
            kid = str(os.environ.get(_JWT_PUBLIC_KEY_ID_ENV) or "default-rs256").strip() or "default-rs256"
            return {kid: pem_key}

        return {}

    def _jwks_keys_from_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Convert JWKS payload to verifier map keyed by kid."""
        jwk_entries = payload.get("keys") if isinstance(payload, dict) else None
        if not isinstance(jwk_entries, list):
            return {}

        verifier_keys: dict[str, Any] = {}
        for entry in jwk_entries:
            if not isinstance(entry, dict):
                continue
            kid = str(entry.get("kid") or "").strip()
            if not kid:
                continue
            try:
                verifier_keys[kid] = RSAAlgorithm.from_jwk(json.dumps(entry))
            except Exception:
                continue
        return verifier_keys

    def _load_jwks_primary_keys(self) -> dict[str, Any]:
        """Load JWKS verifier keys from inline JSON or discovery endpoint cache."""
        inline_jwks_raw = str(os.environ.get(_JWKS_JSON_ENV) or "").strip()
        if inline_jwks_raw:
            try:
                inline_payload = json.loads(inline_jwks_raw)
                return self._jwks_keys_from_payload(inline_payload)
            except json.JSONDecodeError:
                return {}

        jwks_url = str(os.environ.get(_JWKS_URL_ENV) or "").strip()
        if not jwks_url:
            return {}

        now = time.time()
        cached_url = _JWKS_CACHE.get("url")
        cached_expiry = float(_JWKS_CACHE.get("expires_at") or 0.0)
        if cached_url == jwks_url and now < cached_expiry:
            return dict(_JWKS_CACHE.get("keys") or {})

        try:
            with urllib.request.urlopen(jwks_url, timeout=_JWKS_CACHE_TIMEOUT_SECONDS) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except Exception:
            return {}

        keys = self._jwks_keys_from_payload(payload)
        try:
            ttl = int(str(os.environ.get(_JWKS_CACHE_TTL_ENV) or _DEFAULT_JWKS_CACHE_TTL_SECONDS))
        except ValueError:
            ttl = _DEFAULT_JWKS_CACHE_TTL_SECONDS

        _JWKS_CACHE["url"] = jwks_url
        _JWKS_CACHE["keys"] = keys
        _JWKS_CACHE["expires_at"] = now + max(1, ttl)
        return keys

    def _resolve_openid_configuration_url(self) -> str | None:
        """Resolve OpenID configuration URL from explicit env or JWKS URL convention."""
        explicit_openid_url = str(os.environ.get(_OPENID_CONFIGURATION_URL_ENV) or "").strip()
        if explicit_openid_url:
            return explicit_openid_url

        jwks_url = str(os.environ.get(_JWKS_URL_ENV) or "").strip()
        if jwks_url.endswith("/jwks.json"):
            return f"{jwks_url.rsplit('/', 1)[0]}/openid-configuration"
        return None

    def _load_openid_configuration(self) -> dict[str, Any]:
        """Load OpenID configuration metadata from inline JSON or discovery endpoint."""
        inline_config_raw = str(os.environ.get(_OPENID_CONFIGURATION_JSON_ENV) or "").strip()
        if inline_config_raw:
            try:
                parsed = json.loads(inline_config_raw)
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                return {}

        openid_url = self._resolve_openid_configuration_url()
        if not openid_url:
            return {}

        now = time.time()
        cached_url = _OPENID_CONFIGURATION_CACHE.get("url")
        cached_expiry = float(_OPENID_CONFIGURATION_CACHE.get("expires_at") or 0.0)
        if cached_url == openid_url and now < cached_expiry:
            return dict(_OPENID_CONFIGURATION_CACHE.get("payload") or {})

        try:
            with urllib.request.urlopen(openid_url, timeout=_JWKS_CACHE_TIMEOUT_SECONDS) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except Exception:
            return {}
        if not isinstance(payload, dict):
            return {}

        try:
            ttl = int(str(os.environ.get(_JWKS_CACHE_TTL_ENV) or _DEFAULT_JWKS_CACHE_TTL_SECONDS))
        except ValueError:
            ttl = _DEFAULT_JWKS_CACHE_TTL_SECONDS

        _OPENID_CONFIGURATION_CACHE["url"] = openid_url
        _OPENID_CONFIGURATION_CACHE["payload"] = payload
        _OPENID_CONFIGURATION_CACHE["expires_at"] = now + max(1, ttl)
        return payload

    def _resolve_expected_issuer(self) -> str | None:
        """Resolve trusted issuer from explicit config or OpenID discovery metadata."""
        explicit_issuer = str(os.environ.get(_JWT_ISSUER_ENV) or "").strip()
        if explicit_issuer:
            return explicit_issuer

        discovery_metadata = self._load_openid_configuration()
        discovered_issuer = str(discovery_metadata.get("issuer") or "").strip()
        return discovered_issuer or None

    def _resolve_identity_from_jwt(self, token: str) -> tuple[str, str | None, str | None, str | None, str | None, list[str], str | None, str | None]:
        """Resolve platform/service identity tuple from JWT claims.

        JWT is authoritative when present; callers must never fall back to headers
        after JWT parse/validation failure.
        """
        issuer = self._resolve_expected_issuer()
        audience = os.environ.get(_JWT_AUDIENCE_ENV)

        try:
            unverified_header = jwt.get_unverified_header(token)
        except jwt.PyJWTError as exc:
            raise HTTPException(status_code=401, detail="Invalid JWT") from exc

        algorithm = str(unverified_header.get("alg") or "").strip().upper()
        kid = str(unverified_header.get("kid") or "").strip()

        claims: dict[str, Any] | None = None
        if algorithm == "RS256":
            primary_jwks_keys = self._load_jwks_primary_keys()
            if primary_jwks_keys:
                primary_key = primary_jwks_keys.get(kid)
                if primary_key is None:
                    raise HTTPException(status_code=401, detail="Invalid JWT")
                claims = self._decode_claims(token, primary_key, "RS256", issuer, audience)
                if claims is None:
                    # Fail closed when JWKS primary key is available but verification fails.
                    raise HTTPException(status_code=401, detail="Invalid JWT")
            else:
                fallback_keys = self._load_static_rs256_fallback_keys()
                fallback_key = fallback_keys.get(kid)
                if fallback_key is None:
                    raise HTTPException(status_code=401, detail="JWT validation not configured")
                claims = self._decode_claims(token, fallback_key, "RS256", issuer, audience)
                if claims is None:
                    raise HTTPException(status_code=401, detail="Invalid JWT")
        elif algorithm == "HS256":
            secret = os.environ.get(_JWT_SECRET_ENV)
            if not secret:
                raise HTTPException(
                    status_code=401,
                    detail="JWT validation not configured",
                )
            claims = self._decode_claims(token, secret, "HS256", issuer, audience)
            if claims is None:
                raise HTTPException(status_code=401, detail="Invalid JWT")
        else:
            raise HTTPException(status_code=401, detail="Invalid JWT")

        platform_tenant_id = str(
            claims.get("tenant_id") or claims.get("platform_tenant_id") or ""
        ).strip()
        if not platform_tenant_id:
            raise HTTPException(status_code=401, detail="Invalid JWT")

        service_tenant = (
            claims.get("service_tenant_id")
            or claims.get("tenant_id")
            or claims.get("platform_tenant_id")
        )
        service_user = (
            claims.get("service_user_id")
            or claims.get("user_id")
            or claims.get("principal_id")
            or claims.get("sub")
        )
        service_tenant_id = str(service_tenant).strip() if service_tenant is not None else None
        service_user_id = str(service_user).strip() if service_user is not None else None

        principal_id = str(claims.get("principal_id") or "").strip() or None
        principal_type = str(claims.get("principal_type") or "").strip() or None
        if principal_type is not None and principal_type not in _ALLOWED_PRINCIPAL_TYPES:
            raise HTTPException(status_code=401, detail="Invalid JWT")

        raw_roles = claims.get("roles") or []
        if not isinstance(raw_roles, (list, tuple, set)):
            raise HTTPException(status_code=401, detail="Invalid JWT")
        roles = [str(role).strip() for role in raw_roles if str(role).strip()]
        claim_issuer = str(claims.get("iss") or "").strip() or issuer
        claim_audience = str(claims.get("aud") or "").strip() or audience

        return (
            platform_tenant_id,
            service_tenant_id or None,
            service_user_id or None,
            principal_id,
            principal_type,
            roles,
            claim_issuer,
            claim_audience,
        )

    def _validate_legacy_alias_match(
        self,
        request: Request,
        service_tenant_id: str | None,
        service_user_id: str | None,
    ) -> None:
        """Fail closed when compatibility alias headers conflict with JWT claims."""
        legacy_service_tenant_id = str(request.headers.get("x-service-tenant-id") or "").strip() or None
        legacy_service_user_id = str(request.headers.get("x-user-id") or "").strip() or None

        if legacy_service_tenant_id is not None and legacy_service_tenant_id != (service_tenant_id or None):
            raise HTTPException(status_code=401, detail="Invalid JWT")
        if legacy_service_user_id is not None and legacy_service_user_id != (service_user_id or None):
            raise HTTPException(status_code=401, detail="Invalid JWT")

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
                    request.state.principal_id,
                    request.state.principal_type,
                    request.state.roles,
                    request.state.auth_issuer,
                    request.state.auth_audience,
                ) = self._resolve_identity_from_jwt(bearer_token)
                self._validate_legacy_alias_match(
                    request,
                    request.state.service_tenant_id,
                    request.state.service_user_id,
                )
                request.state.auth_source = "jwt"
            except HTTPException as exc:
                return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
        elif self._is_identity_admin_request(request):
            request.state.platform_tenant_id = (
                request.headers.get("x-tenant-id") or DEFAULT_PLATFORM_TENANT_ID
            )
            request.state.service_tenant_id = request.headers.get("x-service-tenant-id") or None
            request.state.service_user_id = request.headers.get("x-user-id") or None
            request.state.principal_id = None
            request.state.principal_type = None
            request.state.roles = []
            request.state.auth_issuer = None
            request.state.auth_audience = None
            request.state.auth_source = "trusted-admin-header"
        else:
            return JSONResponse(status_code=401, content={"detail": "Missing bearer token"})

        return await call_next(request)
