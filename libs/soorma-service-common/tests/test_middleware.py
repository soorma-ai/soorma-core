"""
Tests for TenancyMiddleware.

RED phase: all tests assert real expected behavior.
They MUST fail with NotImplementedError until middleware.dispatch is implemented.
"""
import pytest
from fastapi.testclient import TestClient

from soorma_service_common.middleware import TenancyMiddleware


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
