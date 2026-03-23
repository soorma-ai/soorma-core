"""
RED Phase tests for schema registry endpoints.

These tests assert REAL expected behavior and currently FAIL because
SchemaRegistryService methods raise NotImplementedError (STUB phase).

Expected failures: 500 Internal Server Error (server-side NotImplementedError)
NOT ImportError or AttributeError — those would mean stubs were not created.
"""
import pytest

# Re-use conftest.py fixtures: client (TEST_TENANT_ID) and setup_test_db
TEST_TENANT_ID = "spt_00000000-0000-0000-0000-000000000000"
TENANT_A = "spt_11111111-1111-1111-1111-111111111111"
TENANT_B = "spt_22222222-2222-2222-2222-222222222222"

# ─── Helpers ──────────────────────────────────────────────────────────────────

def _schema_payload(
    schema_name: str = "research_request_v1",
    version: str = "1.0.0",
    json_schema: dict | None = None,
    description: str = "Test schema",
    owner_agent_id: str | None = None,
) -> dict:
    """Build a valid POST /v1/schemas request body."""
    payload: dict = {
        "schema": {
            "schemaName": schema_name,
            "version": version,
            "jsonSchema": json_schema or {"type": "object", "properties": {"query": {"type": "string"}}},
            "description": description,
        }
    }
    if owner_agent_id is not None:
        payload["schema"]["ownerAgentId"] = owner_agent_id
    return payload


# ─── POST /v1/schemas ─────────────────────────────────────────────────────────

class TestRegisterSchema:
    """Tests for POST /v1/schemas."""

    def test_register_schema_success(self, client):
        """Registering a new schema returns 200 with success=True."""
        response = client.post("/v1/schemas", json=_schema_payload())
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["schemaName"] == "research_request_v1"
        assert data["version"] == "1.0.0"

    def test_register_schema_returns_message(self, client):
        """Response includes a message string."""
        response = client.post("/v1/schemas", json=_schema_payload())
        assert response.status_code == 200
        assert "message" in response.json()
        assert isinstance(response.json()["message"], str)

    def test_register_schema_duplicate_409(self, client):
        """Registering the same (schema_name, version) twice returns 409 Conflict."""
        payload = _schema_payload(schema_name="dup_schema_v1", version="1.0.0")
        r1 = client.post("/v1/schemas", json=payload)
        assert r1.status_code == 200  # first registration succeeds
        r2 = client.post("/v1/schemas", json=payload)  # duplicate
        assert r2.status_code == 409

    def test_register_schema_different_versions_ok(self, client):
        """Same name but different version is allowed (new registration)."""
        client.post("/v1/schemas", json=_schema_payload(schema_name="versioned_v1", version="1.0.0"))
        response = client.post("/v1/schemas", json=_schema_payload(schema_name="versioned_v1", version="2.0.0"))
        assert response.status_code == 200

    def test_register_schema_requires_tenant_header(self):
        """POST /v1/schemas without X-Tenant-ID defaults to DEFAULT_PLATFORM_TENANT_ID (200)."""
        from fastapi.testclient import TestClient
        from registry_service.main import app
        no_auth_client = TestClient(app)
        response = no_auth_client.post("/v1/schemas", json=_schema_payload())
        assert response.status_code == 200

    def test_register_schema_with_owner_agent_id(self, client):
        """Schema can be registered with an owner_agent_id."""
        payload = _schema_payload(schema_name="owned_schema_v1", owner_agent_id="research-worker-001")
        response = client.post("/v1/schemas", json=payload)
        assert response.status_code == 200

    def test_register_multiple_schemas(self, client):
        """Multiple distinct schemas can be registered successfully."""
        schemas = [
            _schema_payload(schema_name="schema_a_v1"),
            _schema_payload(schema_name="schema_b_v1"),
            _schema_payload(schema_name="schema_c_v1"),
        ]
        for payload in schemas:
            r = client.post("/v1/schemas", json=payload)
            assert r.status_code == 200


# ─── GET /v1/schemas/{schema_name} ────────────────────────────────────────────

class TestGetSchema:
    """Tests for GET /v1/schemas/{schema_name} (latest version)."""

    def test_get_schema_by_name_success(self, client):
        """Registered schema is retrievable by name."""
        client.post("/v1/schemas", json=_schema_payload(schema_name="retrievable_v1"))
        response = client.get("/v1/schemas/retrievable_v1")
        assert response.status_code == 200
        data = response.json()
        assert data["schemaName"] == "retrievable_v1"
        assert data["version"] == "1.0.0"
        assert "jsonSchema" in data

    def test_get_schema_not_found_404(self, client):
        """GET /v1/schemas/nonexistent returns 404."""
        response = client.get("/v1/schemas/nonexistent_schema_xyz")
        assert response.status_code == 404

    def test_get_schema_returns_latest_version(self, client):
        """Multiple versions: GET without version returns the latest one."""
        client.post("/v1/schemas", json=_schema_payload(schema_name="multi_v1", version="1.0.0"))
        client.post("/v1/schemas", json=_schema_payload(schema_name="multi_v1", version="2.0.0"))
        response = client.get("/v1/schemas/multi_v1")
        assert response.status_code == 200
        # Latest should be returned (2.0.0 was registered last)
        assert response.json()["version"] == "2.0.0"

    def test_get_schema_requires_tenant_header(self):
        """GET /v1/schemas/{name} without X-Tenant-ID defaults to DEFAULT_PLATFORM_TENANT_ID.
        Schema not registered under that tenant, so returns 404."""
        from fastapi.testclient import TestClient
        from registry_service.main import app
        no_auth_client = TestClient(app)
        response = no_auth_client.get("/v1/schemas/any_schema")
        assert response.status_code == 404


# ─── GET /v1/schemas/{schema_name}/versions/{version} ─────────────────────────

class TestGetSchemaByVersion:
    """Tests for GET /v1/schemas/{schema_name}/versions/{version}."""

    def test_get_specific_version_success(self, client):
        """Specific version can be retrieved."""
        client.post("/v1/schemas", json=_schema_payload(schema_name="ver_test_v1", version="1.0.0"))
        client.post("/v1/schemas", json=_schema_payload(schema_name="ver_test_v1", version="2.0.0"))
        response = client.get("/v1/schemas/ver_test_v1/versions/1.0.0")
        assert response.status_code == 200
        assert response.json()["version"] == "1.0.0"

    def test_get_specific_version_not_found_404(self, client):
        """Request for nonexistent version returns 404."""
        client.post("/v1/schemas", json=_schema_payload(schema_name="ver_test2_v1", version="1.0.0"))
        response = client.get("/v1/schemas/ver_test2_v1/versions/99.0.0")
        assert response.status_code == 404


# ─── GET /v1/schemas?owner_agent_id={id} ──────────────────────────────────────

class TestListSchemas:
    """Tests for GET /v1/schemas (list endpoint)."""

    def test_list_schemas_by_owner(self, client):
        """Schemas owned by a specific agent are filterable."""
        client.post("/v1/schemas", json=_schema_payload(schema_name="owned_a_v1", owner_agent_id="worker-101"))
        client.post("/v1/schemas", json=_schema_payload(schema_name="owned_b_v1", owner_agent_id="worker-101"))
        client.post("/v1/schemas", json=_schema_payload(schema_name="unowned_v1", owner_agent_id=None))

        response = client.get("/v1/schemas?owner_agent_id=worker-101")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 2
        names = {s["schemaName"] for s in data["schemas"]}
        assert "owned_a_v1" in names
        assert "owned_b_v1" in names
        assert "unowned_v1" not in names

    def test_list_schemas_all_for_tenant(self, client):
        """List without filter returns all schemas for the tenant."""
        client.post("/v1/schemas", json=_schema_payload(schema_name="all_a_v1"))
        client.post("/v1/schemas", json=_schema_payload(schema_name="all_b_v1"))
        response = client.get("/v1/schemas")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] >= 2
        names = {s["schemaName"] for s in data["schemas"]}
        assert "all_a_v1" in names
        assert "all_b_v1" in names

    def test_list_schemas_empty_without_owner_filter(self, client):
        """Empty list when no schemas registered."""
        response = client.get("/v1/schemas?owner_agent_id=no-such-agent")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 0
        assert data["schemas"] == []

    def test_list_schemas_requires_tenant_header(self):
        """GET /v1/schemas without X-Tenant-ID defaults to DEFAULT_PLATFORM_TENANT_ID (200)."""
        from fastapi.testclient import TestClient
        from registry_service.main import app
        no_auth_client = TestClient(app)
        response = no_auth_client.get("/v1/schemas")
        assert response.status_code == 200


# ─── Cross-tenant isolation ────────────────────────────────────────────────────

class TestSchemaCrossTenantIsolation:
    """Tests for multi-tenancy isolation of schema CRUD."""

    def test_schema_cross_tenant_isolation(self):
        """Tenant A schemas are NOT visible to Tenant B."""
        from fastapi.testclient import TestClient
        from registry_service.main import app

        client_a = TestClient(app, headers={"X-Tenant-ID": TENANT_A})
        client_b = TestClient(app, headers={"X-Tenant-ID": TENANT_B})

        # Register schema as Tenant A
        r = client_a.post("/v1/schemas", json=_schema_payload(schema_name="secret_v1"))
        assert r.status_code == 200

        # Tenant B should NOT see it
        response = client_b.get("/v1/schemas/secret_v1")
        assert response.status_code == 404

    def test_same_schema_name_different_tenants(self):
        """Both tenants can register schemas with the same name independently."""
        from fastapi.testclient import TestClient
        from registry_service.main import app

        client_a = TestClient(app, headers={"X-Tenant-ID": TENANT_A})
        client_b = TestClient(app, headers={"X-Tenant-ID": TENANT_B})

        r_a = client_a.post("/v1/schemas", json=_schema_payload(schema_name="common_name_v1"))
        r_b = client_b.post("/v1/schemas", json=_schema_payload(schema_name="common_name_v1"))
        assert r_a.status_code == 200
        assert r_b.status_code == 200  # not 409 — different tenants

    def test_list_schemas_tenant_scoped(self):
        """List only returns schemas for the requesting tenant."""
        from fastapi.testclient import TestClient
        from registry_service.main import app

        client_a = TestClient(app, headers={"X-Tenant-ID": TENANT_A})
        client_b = TestClient(app, headers={"X-Tenant-ID": TENANT_B})

        client_a.post("/v1/schemas", json=_schema_payload(schema_name="tenant_a_exclusive_v1"))
        response = client_b.get("/v1/schemas")
        assert response.status_code == 200
        names = {s["schemaName"] for s in response.json()["schemas"]}
        assert "tenant_a_exclusive_v1" not in names
