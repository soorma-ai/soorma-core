"""
Tests for TenancyMiddleware.

RED phase: all tests assert real expected behavior.
They MUST fail with NotImplementedError until middleware.dispatch is implemented.
"""
import json
import pytest
from fastapi.testclient import TestClient
from jwt.algorithms import RSAAlgorithm

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import load_pem_public_key

from soorma_service_common.middleware import (
    TenancyMiddleware,
    configure_platform_tenant_openapi,
)


def _generate_rsa_keypair() -> tuple[str, str]:
    """Generate PEM keypair for RS256 middleware tests."""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")
    return private_pem, public_pem


def _build_jwks_json(kid: str, public_pem: str) -> str:
    """Build JWKS JSON containing a single RSA key."""
    public_key_obj = load_pem_public_key(public_pem.encode("utf-8"))
    jwk_payload = json.loads(RSAAlgorithm.to_jwk(public_key_obj))
    jwk_payload.update({"kid": kid, "use": "sig", "alg": "RS256"})
    return json.dumps({"keys": [jwk_payload]})


class TestTenancyMiddlewareHeaderExtraction:
    """TenancyMiddleware extracts identity headers for trusted admin-key requests."""

    @staticmethod
    def _admin_headers(**extra_headers: str) -> dict[str, str]:
        headers = {"X-Identity-Admin-Key": "dev-identity-admin"}
        headers.update(extra_headers)
        return headers

    def test_x_tenant_id_populates_platform_tenant_id(self, make_test_app):
        """Trusted admin request projects X-Tenant-ID into request.state.platform_tenant_id."""
        client = TestClient(make_test_app(), raise_server_exceptions=False)
        response = client.get("/test", headers=self._admin_headers(**{"X-Tenant-ID": "spt_acme"}))
        assert response.status_code == 200
        assert response.json()["platform_tenant_id"] == "spt_acme"

    def test_missing_x_tenant_id_uses_default(self, make_test_app):
        """Trusted admin request without X-Tenant-ID uses DEFAULT_PLATFORM_TENANT_ID."""
        from soorma_common.tenancy import DEFAULT_PLATFORM_TENANT_ID

        client = TestClient(make_test_app(), raise_server_exceptions=False)
        response = client.get("/test", headers=self._admin_headers())
        assert response.status_code == 200
        assert response.json()["platform_tenant_id"] == DEFAULT_PLATFORM_TENANT_ID

    def test_x_service_tenant_id_populates_service_tenant_id(self, make_test_app):
        """Trusted admin request projects X-Service-Tenant-ID into request.state.service_tenant_id."""
        client = TestClient(make_test_app(), raise_server_exceptions=False)
        response = client.get(
            "/test",
            headers=self._admin_headers(**{"X-Tenant-ID": "spt_acme", "X-Service-Tenant-ID": "tenant-org-1"}),
        )
        assert response.status_code == 200
        assert response.json()["service_tenant_id"] == "tenant-org-1"

    def test_missing_x_service_tenant_id_is_none(self, make_test_app):
        """Trusted admin request without X-Service-Tenant-ID leaves request.state.service_tenant_id as None."""
        client = TestClient(make_test_app(), raise_server_exceptions=False)
        response = client.get("/test", headers=self._admin_headers(**{"X-Tenant-ID": "spt_acme"}))
        assert response.status_code == 200
        assert response.json()["service_tenant_id"] is None

    def test_x_user_id_populates_service_user_id(self, make_test_app):
        """Trusted admin request projects X-User-ID into request.state.service_user_id."""
        client = TestClient(make_test_app(), raise_server_exceptions=False)
        response = client.get(
            "/test",
            headers=self._admin_headers(**{"X-Tenant-ID": "spt_acme", "X-User-ID": "user-42"}),
        )
        assert response.status_code == 200
        assert response.json()["service_user_id"] == "user-42"

    def test_missing_x_user_id_is_none(self, make_test_app):
        """Trusted admin request without X-User-ID leaves request.state.service_user_id as None."""
        client = TestClient(make_test_app(), raise_server_exceptions=False)
        response = client.get("/test", headers=self._admin_headers(**{"X-Tenant-ID": "spt_acme"}))
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

    def test_jwt_present_with_matching_alias_headers_succeeds(self, make_test_app, monkeypatch):
        """When JWT and alias headers match, request succeeds on JWT canonical path."""
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
                "X-Service-Tenant-ID": "tenant_jwt",
                "X-User-ID": "user_jwt",
            },
        )
        assert response.status_code == 200
        assert response.json()["platform_tenant_id"] == "spt_jwt"
        assert response.json()["service_tenant_id"] == "tenant_jwt"
        assert response.json()["service_user_id"] == "user_jwt"

    def test_jwt_with_mismatching_alias_headers_fails_closed(self, make_test_app, monkeypatch):
        """When JWT and alias headers disagree, middleware denies fail-closed."""
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
                "X-Service-Tenant-ID": "tenant_header",
                "X-User-ID": "user_jwt",
            },
        )

        assert response.status_code == 401

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

    def test_no_jwt_without_admin_bypass_is_denied(self, make_test_app):
        """If JWT is absent and no trusted admin bypass exists, middleware denies access."""
        client = TestClient(make_test_app(), raise_server_exceptions=False)
        response = client.get(
            "/test",
            headers={
                "X-Tenant-ID": "spt_header",
                "X-Service-Tenant-ID": "tenant_header",
                "X-User-ID": "user_header",
            },
        )
        assert response.status_code == 401

    def test_admin_header_bypass_allows_identity_control_plane_request(self, make_test_app):
        """Trusted admin-key requests may bypass JWT enforcement for identity control-plane routes."""
        client = TestClient(make_test_app(), raise_server_exceptions=False)
        response = client.get(
            "/test",
            headers={
                "X-Tenant-ID": "spt_header",
                "X-Service-Tenant-ID": "tenant_header",
                "X-User-ID": "user_header",
                "X-Identity-Admin-Key": "dev-identity-admin",
            },
        )
        assert response.status_code == 200
        assert response.json()["platform_tenant_id"] == "spt_header"
        assert response.json()["service_tenant_id"] == "tenant_header"
        assert response.json()["service_user_id"] == "user_header"

    def test_jwt_uses_canonical_tenant_id_claim_when_present(self, make_test_app, monkeypatch):
        """Middleware should prefer canonical tenant_id claim over legacy platform_tenant_id claim."""
        import jwt

        monkeypatch.setenv("SOORMA_AUTH_JWT_SECRET", "test-secret")
        monkeypatch.setenv("SOORMA_AUTH_JWT_ISSUER", "soorma-identity")
        monkeypatch.setenv("SOORMA_AUTH_JWT_AUDIENCE", "soorma-services")

        token = jwt.encode(
            {
                "tenant_id": "tenant-canonical",
                "platform_tenant_id": "tenant-legacy",
                "service_tenant_id": "svc-tenant",
                "service_user_id": "svc-user",
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
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        assert response.json()["platform_tenant_id"] == "tenant-canonical"

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

    def test_rs256_jwt_uses_jwks_primary_success(self, make_test_app, monkeypatch):
        """RS256 JWT should validate with JWKS primary verifier material."""
        import jwt

        private_pem, public_pem = _generate_rsa_keypair()
        monkeypatch.setenv("SOORMA_AUTH_JWKS_JSON", _build_jwks_json("kid-main", public_pem))
        monkeypatch.setenv("SOORMA_AUTH_JWT_ISSUER", "soorma-identity")
        monkeypatch.setenv("SOORMA_AUTH_JWT_AUDIENCE", "soorma-services")

        token = jwt.encode(
            {
                "platform_tenant_id": "spt_rs",
                "service_tenant_id": "tenant_rs",
                "service_user_id": "user_rs",
                "exp": 4102444800,
                "aud": "soorma-services",
                "iss": "soorma-identity",
            },
            private_pem,
            algorithm="RS256",
            headers={"kid": "kid-main", "alg": "RS256"},
        )

        client = TestClient(make_test_app(), raise_server_exceptions=False)
        response = client.get(
            "/test",
            headers={
                "Authorization": f"Bearer {token}",
                "X-Service-Tenant-ID": "tenant_rs",
                "X-User-ID": "user_rs",
            },
        )
        assert response.status_code == 200
        assert response.json()["platform_tenant_id"] == "spt_rs"

    def test_rs256_jwt_unknown_kid_denied(self, make_test_app, monkeypatch):
        """RS256 JWT with unknown kid should fail closed."""
        import jwt

        private_pem, public_pem = _generate_rsa_keypair()
        monkeypatch.setenv("SOORMA_AUTH_JWKS_JSON", _build_jwks_json("kid-main", public_pem))
        monkeypatch.setenv("SOORMA_AUTH_JWT_ISSUER", "soorma-identity")
        monkeypatch.setenv("SOORMA_AUTH_JWT_AUDIENCE", "soorma-services")

        token = jwt.encode(
            {
                "platform_tenant_id": "spt_rs",
                "service_tenant_id": "tenant_rs",
                "service_user_id": "user_rs",
                "exp": 4102444800,
                "aud": "soorma-services",
                "iss": "soorma-identity",
            },
            private_pem,
            algorithm="RS256",
            headers={"kid": "kid-unknown", "alg": "RS256"},
        )

        client = TestClient(make_test_app(), raise_server_exceptions=False)
        response = client.get("/test", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 401

    def test_rs256_jwt_jwks_primary_failure_does_not_use_fallback(self, make_test_app, monkeypatch):
        """When JWKS has kid but signature fails, middleware must fail closed."""
        import jwt

        valid_private_pem, valid_public_pem = _generate_rsa_keypair()
        stale_private_pem, stale_public_pem = _generate_rsa_keypair()

        monkeypatch.setenv("SOORMA_AUTH_JWKS_JSON", _build_jwks_json("kid-main", stale_public_pem))
        monkeypatch.setenv("SOORMA_AUTH_JWT_PUBLIC_KEYS_JSON", json.dumps({"kid-main": valid_public_pem}))
        monkeypatch.setenv("SOORMA_AUTH_JWT_ISSUER", "soorma-identity")
        monkeypatch.setenv("SOORMA_AUTH_JWT_AUDIENCE", "soorma-services")

        token = jwt.encode(
            {
                "platform_tenant_id": "spt_rs",
                "service_tenant_id": "tenant_rs",
                "service_user_id": "user_rs",
                "exp": 4102444800,
                "aud": "soorma-services",
                "iss": "soorma-identity",
            },
            valid_private_pem,
            algorithm="RS256",
            headers={"kid": "kid-main", "alg": "RS256"},
        )

        client = TestClient(make_test_app(), raise_server_exceptions=False)
        response = client.get("/test", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 401

    def test_rs256_jwt_static_fallback_when_jwks_unavailable(self, make_test_app, monkeypatch):
        """Static RS256 fallback should be used when JWKS primary source is unavailable."""
        import jwt

        private_pem, public_pem = _generate_rsa_keypair()

        monkeypatch.setenv("SOORMA_AUTH_JWKS_JSON", "{invalid-json")
        monkeypatch.setenv("SOORMA_AUTH_JWT_PUBLIC_KEYS_JSON", json.dumps({"kid-main": public_pem}))
        monkeypatch.setenv("SOORMA_AUTH_JWT_ISSUER", "soorma-identity")
        monkeypatch.setenv("SOORMA_AUTH_JWT_AUDIENCE", "soorma-services")

        token = jwt.encode(
            {
                "platform_tenant_id": "spt_rs",
                "service_tenant_id": "tenant_rs",
                "service_user_id": "user_rs",
                "exp": 4102444800,
                "aud": "soorma-services",
                "iss": "soorma-identity",
            },
            private_pem,
            algorithm="RS256",
            headers={"kid": "kid-main", "alg": "RS256"},
        )

        client = TestClient(make_test_app(), raise_server_exceptions=False)
        response = client.get("/test", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200

    def test_rs256_jwt_uses_jwks_url_discovery(self, make_test_app, monkeypatch):
        """Middleware should fetch JWKS via discovery URL when configured."""
        import jwt

        private_pem, public_pem = _generate_rsa_keypair()
        jwks_json = _build_jwks_json("kid-main", public_pem)

        class _FakeResponse:
            def __init__(self, payload: str):
                self._payload = payload

            def read(self) -> bytes:
                return self._payload.encode("utf-8")

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

        def _fake_urlopen(url: str, timeout: float):
            assert url == "http://identity.local/v1/identity/.well-known/jwks.json"
            assert timeout > 0
            return _FakeResponse(jwks_json)

        monkeypatch.setenv("SOORMA_AUTH_JWKS_URL", "http://identity.local/v1/identity/.well-known/jwks.json")
        monkeypatch.setenv("SOORMA_AUTH_JWKS_CACHE_TTL_SECONDS", "60")
        monkeypatch.setenv("SOORMA_AUTH_JWT_ISSUER", "soorma-identity")
        monkeypatch.setenv("SOORMA_AUTH_JWT_AUDIENCE", "soorma-services")
        monkeypatch.delenv("SOORMA_AUTH_JWKS_JSON", raising=False)
        monkeypatch.setattr("soorma_service_common.middleware.urllib.request.urlopen", _fake_urlopen)

        token = jwt.encode(
            {
                "platform_tenant_id": "spt_rs",
                "service_tenant_id": "tenant_rs",
                "service_user_id": "user_rs",
                "exp": 4102444800,
                "aud": "soorma-services",
                "iss": "soorma-identity",
            },
            private_pem,
            algorithm="RS256",
            headers={"kid": "kid-main", "alg": "RS256"},
        )

        client = TestClient(make_test_app(), raise_server_exceptions=False)
        response = client.get("/test", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200

    def test_rs256_jwt_uses_discovery_issuer_when_explicit_issuer_unset(self, make_test_app, monkeypatch):
        """Issuer trust should be derived from OpenID config when explicit issuer is unset."""
        import jwt

        private_pem, public_pem = _generate_rsa_keypair()
        monkeypatch.setenv("SOORMA_AUTH_JWKS_JSON", _build_jwks_json("kid-main", public_pem))
        monkeypatch.setenv(
            "SOORMA_AUTH_OPENID_CONFIGURATION_JSON",
            json.dumps({"issuer": "soorma-identity"}),
        )
        monkeypatch.delenv("SOORMA_AUTH_JWT_ISSUER", raising=False)
        monkeypatch.setenv("SOORMA_AUTH_JWT_AUDIENCE", "soorma-services")

        token = jwt.encode(
            {
                "platform_tenant_id": "spt_rs",
                "service_tenant_id": "tenant_rs",
                "service_user_id": "user_rs",
                "exp": 4102444800,
                "aud": "soorma-services",
                "iss": "soorma-identity",
            },
            private_pem,
            algorithm="RS256",
            headers={"kid": "kid-main", "alg": "RS256"},
        )

        client = TestClient(make_test_app(), raise_server_exceptions=False)
        response = client.get("/test", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200

    def test_rs256_jwt_discovery_issuer_mismatch_denied(self, make_test_app, monkeypatch):
        """Token should be denied when OpenID-discovered issuer does not match claim issuer."""
        import jwt

        private_pem, public_pem = _generate_rsa_keypair()
        monkeypatch.setenv("SOORMA_AUTH_JWKS_JSON", _build_jwks_json("kid-main", public_pem))
        monkeypatch.setenv(
            "SOORMA_AUTH_OPENID_CONFIGURATION_JSON",
            json.dumps({"issuer": "trusted-issuer"}),
        )
        monkeypatch.delenv("SOORMA_AUTH_JWT_ISSUER", raising=False)
        monkeypatch.setenv("SOORMA_AUTH_JWT_AUDIENCE", "soorma-services")

        token = jwt.encode(
            {
                "platform_tenant_id": "spt_rs",
                "service_tenant_id": "tenant_rs",
                "service_user_id": "user_rs",
                "exp": 4102444800,
                "aud": "soorma-services",
                "iss": "soorma-identity",
            },
            private_pem,
            algorithm="RS256",
            headers={"kid": "kid-main", "alg": "RS256"},
        )

        client = TestClient(make_test_app(), raise_server_exceptions=False)
        response = client.get("/test", headers={"Authorization": f"Bearer {token}"})
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
