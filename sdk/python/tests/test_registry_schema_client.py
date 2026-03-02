"""Gap-fill tests for RegistryClient schema methods (Task 3E, Phase 3).

Covers register_schema(), get_schema(), and list_schemas() which were
implemented before Phase 3 but lacked unit tests.

Per plan note: these are gap-fill coverage tests — no forced TDD cycle.
Tests are written directly against the expected real behaviour.

Run:
    pytest sdk/python/tests/test_registry_schema_client.py -v
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from soorma.registry.client import RegistryClient
from soorma_common import PayloadSchema


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

def _make_registry_client() -> RegistryClient:
    """Return a RegistryClient with a mocked async HTTP client."""
    client = RegistryClient(base_url="http://test-registry")
    client._client = AsyncMock()
    return client


def _sample_schema_dict(
    name: str = "research_request_v1",
    version: str = "1.0.0",
) -> dict:
    """Return a minimal camelCase PayloadSchema dict matching the API shape."""
    return {
        "schemaName": name,
        "version": version,
        "jsonSchema": {"type": "object", "properties": {"query": {"type": "string"}}},
        "description": "Schema for research requests",
        "ownerAgentId": "search-worker-001",
        "createdAt": None,
        "updatedAt": None,
    }


def _make_schema_response(schema_dict: dict) -> MagicMock:
    """Build a 200 HTTP mock response containing a single PayloadSchema dict."""
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = schema_dict
    resp.raise_for_status = MagicMock()
    return resp


def _make_schema_register_response(
    name: str = "research_request_v1",
    version: str = "1.0.0",
) -> MagicMock:
    """Build a 201 HTTP mock for schema registration (PayloadSchemaResponse shape)."""
    resp = MagicMock()
    resp.status_code = 201
    resp.json.return_value = {
        "schemaName": name,
        "version": version,
        "success": True,
        "message": "Schema registered successfully",
    }
    resp.raise_for_status = MagicMock()
    return resp


def _make_schema_list_response(schemas: list) -> MagicMock:
    """Build a 200 HTTP mock returning a PayloadSchemaListResponse-shaped dict."""
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"schemas": schemas, "count": len(schemas)}
    resp.raise_for_status = MagicMock()
    return resp


def _make_404_response() -> MagicMock:
    """Build a 404 HTTP mock response."""
    resp = MagicMock()
    resp.status_code = 404
    resp.raise_for_status = MagicMock()
    return resp


def _sample_payload_schema(
    name: str = "research_request_v1",
    version: str = "1.0.0",
) -> PayloadSchema:
    """Build a PayloadSchema DTO for use in register_schema() calls."""
    return PayloadSchema(
        schema_name=name,
        version=version,
        json_schema={"type": "object", "properties": {"query": {"type": "string"}}},
        description="Schema for research requests",
        owner_agent_id="search-worker-001",
    )


# ---------------------------------------------------------------------------
# register_schema() tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_register_schema_posts_to_correct_url() -> None:
    """register_schema() should POST to /v1/schemas."""
    registry = _make_registry_client()
    registry._client.post = AsyncMock(
        return_value=_make_schema_register_response()
    )

    schema = _sample_payload_schema()
    await registry.register_schema(schema)

    call_kwargs = registry._client.post.call_args
    assert "/v1/schemas" in call_kwargs.args[0]


@pytest.mark.asyncio
async def test_register_schema_sends_schema_in_envelope() -> None:
    """register_schema() should wrap schema under 'schema' key (camelCase alias)."""
    registry = _make_registry_client()
    registry._client.post = AsyncMock(
        return_value=_make_schema_register_response()
    )

    schema = _sample_payload_schema()
    await registry.register_schema(schema)

    call_kwargs = registry._client.post.call_args
    body: dict = call_kwargs.kwargs["json"]
    # Payload should be wrapped in 'schema' envelope key
    assert "schema" in body
    inner: dict = body["schema"]
    # Fields should come through camelCase (by_alias=True)
    assert inner["schemaName"] == "research_request_v1"
    assert inner["version"] == "1.0.0"


@pytest.mark.asyncio
async def test_register_schema_returns_payload_schema_response() -> None:
    """register_schema() should return a PayloadSchemaResponse with success=True."""
    from soorma_common import PayloadSchemaResponse  # type: ignore[attr-defined]

    registry = _make_registry_client()
    registry._client.post = AsyncMock(
        return_value=_make_schema_register_response()
    )

    result = await registry.register_schema(_sample_payload_schema())

    assert isinstance(result, PayloadSchemaResponse)
    assert result.success is True
    assert result.schema_name == "research_request_v1"


# ---------------------------------------------------------------------------
# get_schema() tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_schema_latest_version_calls_name_url() -> None:
    """get_schema(name) without version should call GET /v1/schemas/{name}."""
    registry = _make_registry_client()
    registry._client.get = AsyncMock(
        return_value=_make_schema_response(_sample_schema_dict())
    )

    await registry.get_schema("research_request_v1")

    call_url = registry._client.get.call_args.args[0]
    assert call_url.endswith("/v1/schemas/research_request_v1")
    # Must NOT contain 'versions' segment
    assert "versions" not in call_url


@pytest.mark.asyncio
async def test_get_schema_specific_version_calls_versioned_url() -> None:
    """get_schema(name, version) should call GET /v1/schemas/{name}/versions/{ver}."""
    registry = _make_registry_client()
    registry._client.get = AsyncMock(
        return_value=_make_schema_response(_sample_schema_dict(version="2.0.0"))
    )

    await registry.get_schema("research_request_v1", version="2.0.0")

    call_url = registry._client.get.call_args.args[0]
    assert "research_request_v1/versions/2.0.0" in call_url


@pytest.mark.asyncio
async def test_get_schema_returns_payload_schema_dto() -> None:
    """get_schema() should return a PayloadSchema DTO on success."""
    registry = _make_registry_client()
    registry._client.get = AsyncMock(
        return_value=_make_schema_response(_sample_schema_dict())
    )

    result = await registry.get_schema("research_request_v1")

    assert isinstance(result, PayloadSchema)
    assert result.schema_name == "research_request_v1"
    assert result.version == "1.0.0"


@pytest.mark.asyncio
async def test_get_schema_returns_none_on_404() -> None:
    """get_schema() should return None (not raise) when the service returns 404."""
    registry = _make_registry_client()
    registry._client.get = AsyncMock(return_value=_make_404_response())

    result = await registry.get_schema("nonexistent_schema")

    assert result is None


# ---------------------------------------------------------------------------
# list_schemas() tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_schemas_calls_schemas_endpoint() -> None:
    """list_schemas() should call GET /v1/schemas."""
    registry = _make_registry_client()
    registry._client.get = AsyncMock(
        return_value=_make_schema_list_response([_sample_schema_dict()])
    )

    await registry.list_schemas()

    call_url = registry._client.get.call_args.args[0]
    assert call_url.endswith("/v1/schemas")


@pytest.mark.asyncio
async def test_list_schemas_with_owner_filter_passes_param() -> None:
    """list_schemas(owner_agent_id) should include owner_agent_id as a query param."""
    registry = _make_registry_client()
    registry._client.get = AsyncMock(
        return_value=_make_schema_list_response([])
    )

    await registry.list_schemas(owner_agent_id="search-worker-001")

    call_kwargs = registry._client.get.call_args.kwargs
    assert call_kwargs.get("params", {}).get("owner_agent_id") == "search-worker-001"


@pytest.mark.asyncio
async def test_list_schemas_no_filter_sends_empty_params() -> None:
    """list_schemas() without filter should NOT pass owner_agent_id as query param."""
    registry = _make_registry_client()
    registry._client.get = AsyncMock(
        return_value=_make_schema_list_response([])
    )

    await registry.list_schemas()

    call_kwargs = registry._client.get.call_args.kwargs
    params = call_kwargs.get("params", {})
    assert "owner_agent_id" not in params


@pytest.mark.asyncio
async def test_list_schemas_returns_list_of_payload_schemas() -> None:
    """list_schemas() should return a list of PayloadSchema DTOs."""
    registry = _make_registry_client()
    schema_dicts = [
        _sample_schema_dict(name="schema_a_v1", version="1.0.0"),
        _sample_schema_dict(name="schema_b_v2", version="2.0.0"),
    ]
    registry._client.get = AsyncMock(
        return_value=_make_schema_list_response(schema_dicts)
    )

    results = await registry.list_schemas()

    assert isinstance(results, list)
    assert len(results) == 2
    assert all(isinstance(s, PayloadSchema) for s in results)
    names = {s.schema_name for s in results}
    assert names == {"schema_a_v1", "schema_b_v2"}
