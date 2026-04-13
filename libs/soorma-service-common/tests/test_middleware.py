"""
Tests for TenancyMiddleware.

RED phase: all tests assert real expected behavior.
They MUST fail with NotImplementedError until middleware.dispatch is implemented.
"""
import pytest
from fastapi.testclient import TestClient

from soorma_service_common.middleware import (
    TenancyMiddleware,
    configure_platform_tenant_openapi,
)


class TestTenancyMiddlewareHeaderExtraction:
    """TenancyMiddleware extracts identity headers into request.state."""

    def test_x_tenant_id_populates_platform_tenant_id(self, make_test_app):
        """X-Tenant-ID header → request.state.platform_tenant_id."""
        client = TestClient(make_test_app(), raise_server_exceptions=False)
        response = client.get("/test", headers={"X-Tenant-ID": "spt_acme"})
        assert response.status_code == 200
        assert response.json()["platform_tenant_id"] == "spt_acme"

    def test_missing_x_tenant_id_uses_default(self, make_test_app):
        """Absent X-Tenant-ID → request.state.platform_tenant_id = DEFAULT_PLATFORM_TENANT_ID."""
        from soorma_common.tenancy import DEFAULT_PLATFORM_TENANT_ID

        client = TestClient(make_test_app(), raise_server_exceptions=False)
        response = client.get("/test")
        assert response.status_code == 200
        assert response.json()["platform_tenant_id"] == DEFAULT_PLATFORM_TENANT_ID

    def test_x_service_tenant_id_populates_service_tenant_id(self, make_test_app):
        """X-Service-Tenant-ID header → request.state.service_tenant_id."""
        client = TestClient(make_test_app(), raise_server_exceptions=False)
        response = client.get(
            "/test",
            headers={"X-Tenant-ID": "spt_acme", "X-Service-Tenant-ID": "tenant-org-1"},
        )
        assert response.status_code == 200
        assert response.json()["service_tenant_id"] == "tenant-org-1"

    def test_missing_x_service_tenant_id_is_none(self, make_test_app):
        """Absent X-Service-Tenant-ID → request.state.service_tenant_id is None."""
        client = TestClient(make_test_app(), raise_server_exceptions=False)
        response = client.get("/test", headers={"X-Tenant-ID": "spt_acme"})
        assert response.status_code == 200
        assert response.json()["service_tenant_id"] is None

    def test_x_user_id_populates_service_user_id(self, make_test_app):
        """X-User-ID header → request.state.service_user_id."""
        client = TestClient(make_test_app(), raise_server_exceptions=False)
        response = client.get(
            "/test",
            headers={"X-Tenant-ID": "spt_acme", "X-User-ID": "user-42"},
        )
        assert response.status_code == 200
        assert response.json()["service_user_id"] == "user-42"

    def test_missing_x_user_id_is_none(self, make_test_app):
        """Absent X-User-ID → request.state.service_user_id is None."""
        client = TestClient(make_test_app(), raise_server_exceptions=False)
        response = client.get("/test", headers={"X-Tenant-ID": "spt_acme"})
        assert response.status_code == 200
        assert response.json()["service_user_id"] is None


class TestTenancyMiddlewareBypassPaths:
    """TenancyMiddleware bypasses identity extraction for health/docs paths."""

    @pytest.mark.parametrize(
        "path",
        ["/health", "/docs", "/openapi.json", "/redoc"],
    )
    def test_bypass_paths_do_not_require_headers(self, path, make_test_app):
        """Health and docs paths pass through without populating request.state."""
        client = TestClient(make_test_app(), raise_server_exceptions=False)
        # No identity headers — if middleware tried to set them, this would show DEFAULT value
        # On bypass paths, the endpoint itself doesn't use request.state so we get a 200 (or 404/422 for missing routes)
        # The key assertion: the server does NOT crash attempting to process state
        # /health is the only bypass we have an endpoint for in test app
        if path == "/health":
            response = client.get(path)
            assert response.status_code == 200
        else:
            # Docs/openapi paths are served by FastAPI itself; just verify no 500
            response = client.get(path, follow_redirects=True)
            assert response.status_code != 500


class TestTenancyMiddlewareNoDbCall:
    """TenancyMiddleware must NOT call set_config (DB not available in middleware scope)."""

    def test_middleware_does_not_call_database(self, make_test_app):
        """Middleware only sets request.state — DB set_config is handled by get_tenanted_db."""
        # This is verified structurally: TenancyMiddleware.__init__ takes no db argument
        # and dispatch receives only request + call_next (standard BaseHTTPMiddleware signature)
        middleware = TenancyMiddleware.__new__(TenancyMiddleware)
        import inspect
        sig = inspect.signature(TenancyMiddleware.dispatch)
        param_names = list(sig.parameters.keys())
        # dispatch(self, request, call_next) — no db parameter
        assert "db" not in param_names
        assert "session" not in param_names


class TestTenancyMiddlewareJwtCoexistence:
    """JWT precedence and coexistence behavior for middleware identity extraction."""

    def test_jwt_present_uses_jwt_identity_over_headers(self, make_test_app, monkeypatch):
        """When JWT is present and valid, JWT claims override conflicting headers."""
        import jwt

        monkeypatch.setenv("SOORMA_AUTH_JWT_SECRET", "test-secret")
        monkeypatch.setenv("SOORMA_AUTH_JWT_ISSUER", "soorma-identity")
        monkeypatch.setenv("SOORMA_AUTH_JWT_AUDIENCE", "soorma-services")

        token = jwt.encode(
            {
                "platform_tenant_id": "spt_jwt",
                "service_tenant_id": "tenant_jwt",
                "service_user_id": "user_jwt",
                "exp": 4102444800,
                "aud": "soorma-services",
                "iss": "soorma-identity",
            },
            "test-secret",
            algorithm="HS256",
        )
        client = TestClient(make_test_app(), raise_server_exceptions=False)
        response = client.get(
            "/test",
            headers={
                "Authorization": f"Bearer {token}",
                "X-Tenant-ID": "spt_header",
                "X-Service-Tenant-ID": "tenant_header",
                "X-User-ID": "user_header",
            },
        )
        assert response.status_code == 200
        assert response.json()["platform_tenant_id"] == "spt_jwt"
        assert response.json()["service_tenant_id"] == "tenant_jwt"
        assert response.json()["service_user_id"] == "user_jwt"

    def test_invalid_jwt_fails_no_header_fallback(self, make_test_app, monkeypatch):
        """Invalid JWT must fail closed and never fall back to headers."""
        monkeypatch.setenv("SOORMA_AUTH_JWT_SECRET", "test-secret")
        monkeypatch.setenv("SOORMA_AUTH_JWT_ISSUER", "soorma-identity")
        monkeypatch.setenv("SOORMA_AUTH_JWT_AUDIENCE", "soorma-services")

        client = TestClient(make_test_app(), raise_server_exceptions=False)
        response = client.get(
            "/test",
            headers={
                "Authorization": "Bearer not-a-valid-token",
                "X-Tenant-ID": "spt_header",
                "X-Service-Tenant-ID": "tenant_header",
                "X-User-ID": "user_header",
            },
        )
        assert response.status_code == 401

    def test_no_jwt_uses_legacy_headers(self, make_test_app):
        """If JWT is absent, middleware must continue legacy header path."""
        client = TestClient(make_test_app(), raise_server_exceptions=False)
        response = client.get(
            "/test",
            headers={
                "X-Tenant-ID": "spt_header",
                "X-Service-Tenant-ID": "tenant_header",
                "X-User-ID": "user_header",
            },
        )
        assert response.status_code == 200
        assert response.json()["platform_tenant_id"] == "spt_header"
        assert response.json()["service_tenant_id"] == "tenant_header"
        assert response.json()["service_user_id"] == "user_header"

    def test_jwt_invalid_principal_type_fails_closed(self, make_test_app, monkeypatch):
        """JWT with unsupported principal_type must fail closed (401)."""
        import jwt

        monkeypatch.setenv("SOORMA_AUTH_JWT_SECRET", "test-secret")
        monkeypatch.setenv("SOORMA_AUTH_JWT_ISSUER", "soorma-identity")
        monkeypatch.setenv("SOORMA_AUTH_JWT_AUDIENCE", "soorma-services")

        token = jwt.encode(
            {
                "platform_tenant_id": "spt_jwt",
                "service_tenant_id": "tenant_jwt",
                "service_user_id": "user_jwt",
                "principal_type": "robot",
                "roles": ["admin"],
                "exp": 4102444800,
                "aud": "soorma-services",
                "iss": "soorma-identity",
            },
            "test-secret",
            algorithm="HS256",
        )

        client = TestClient(make_test_app(), raise_server_exceptions=False)
        response = client.get(
            "/test",
            headers={
                "Authorization": f"Bearer {token}",
                "X-Tenant-ID": "spt_header",
            },
        )
        assert response.status_code == 401

    def test_jwt_roles_must_be_list_fails_closed(self, make_test_app, monkeypatch):
        """JWT with malformed roles claim must fail closed (401)."""
        import jwt

        monkeypatch.setenv("SOORMA_AUTH_JWT_SECRET", "test-secret")
        monkeypatch.setenv("SOORMA_AUTH_JWT_ISSUER", "soorma-identity")
        monkeypatch.setenv("SOORMA_AUTH_JWT_AUDIENCE", "soorma-services")

        token = jwt.encode(
            {
                "platform_tenant_id": "spt_jwt",
                "service_tenant_id": "tenant_jwt",
                "service_user_id": "user_jwt",
                "roles": "admin",
                "exp": 4102444800,
                "aud": "soorma-services",
                "iss": "soorma-identity",
            },
            "test-secret",
            algorithm="HS256",
        )

        client = TestClient(make_test_app(), raise_server_exceptions=False)
        response = client.get(
            "/test",
            headers={
                "Authorization": f"Bearer {token}",
                "X-Tenant-ID": "spt_header",
            },
        )
        assert response.status_code == 401


class TestOpenApiPlatformTenantHeader:
    """OpenAPI helper exposes X-Tenant-ID in Swagger docs for Try it out."""

    def test_openapi_includes_platform_tenant_security_scheme(self, make_test_app):
        """Configured app schema should include a global API key header scheme."""
        app = make_test_app()
        configure_platform_tenant_openapi(app)

        schema = app.openapi()
        scheme = schema["components"]["securitySchemes"]["PlatformTenantHeader"]

        assert scheme["type"] == "apiKey"
        assert scheme["in"] == "header"
        assert scheme["name"] == "X-Tenant-ID"
        assert {"PlatformTenantHeader": []} in schema["security"]

    def test_openapi_includes_platform_tenant_operation_header(self, make_test_app):
        """Configured schema should expose X-Tenant-ID directly on operations."""
        app = make_test_app()
        configure_platform_tenant_openapi(app)

        schema = app.openapi()
        parameters = schema["paths"]["/test"]["get"].get("parameters", [])
        header_params = [
            p
            for p in parameters
            if p.get("in") == "header" and p.get("name") == "X-Tenant-ID"
        ]

        assert len(header_params) == 1
        assert header_params[0]["required"] is False

    def test_configure_platform_tenant_openapi_is_idempotent(self, make_test_app):
        """Repeated helper calls should not duplicate global security entries."""
        app = make_test_app()
        configure_platform_tenant_openapi(app)
        configure_platform_tenant_openapi(app)

        schema = app.openapi()
        security_entries = schema.get("security", [])
        parameters = schema["paths"]["/test"]["get"].get("parameters", [])
        header_params = [
            p
            for p in parameters
            if p.get("in") == "header" and p.get("name") == "X-Tenant-ID"
        ]

        assert security_entries.count({"PlatformTenantHeader": []}) == 1
        assert len(header_params) == 1
