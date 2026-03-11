"""Tests for RegistryClient.discover() and discover_agents() (Task 3A, Phase 3).

RED phase: all tests call stub methods that raise NotImplementedError.
Tests assert REAL expected behaviour (not stub behaviour).

Run:
    pytest sdk/python/tests/test_registry_discover.py -v
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
import httpx

from soorma.registry.client import RegistryClient
from soorma_common import (
    AgentDefinition,
    AgentCapability,
    EventDefinition,
    DiscoveredAgent,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_registry_client() -> RegistryClient:
    """Return a RegistryClient with a mocked HTTP client."""
    client = RegistryClient(base_url="http://test-registry")
    client._client = AsyncMock()
    return client


def _make_agent_mock_response(agents_json: list) -> MagicMock:
    """Build a mock HTTP response returning an AgentQueryResponse-shaped dict."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"agents": agents_json, "count": len(agents_json)}
    mock_response.raise_for_status = MagicMock()  # no-op (success)
    return mock_response


def _sample_agent_dict(name: str = "SearchWorker:1.0.0") -> dict:
    """Return a minimal camelCase agent dict matching AgentQueryResponse shape."""
    return {
        "agentId": "search-worker-001",
        "name": name,
        "description": "Performs web search",
        "capabilities": [
            {
                "taskName": "web_search",
                "description": "Search the web",
                "consumedEvent": {
                    "eventName": "search.requested",
                    "topic": "action-requests",
                    "description": "Trigger a web search",
                    "payloadSchemaName": "search_request_v1",
                },
                "producedEvents": [
                    {
                        "eventName": "search.completed",
                        "topic": "action-results",
                        "description": "Search result",
                    }
                ],
            }
        ],
    }


# ---------------------------------------------------------------------------
# discover() tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_discover_returns_discovered_agent_list():
    """discover() returns a list of DiscoveredAgent (not AgentDefinition)."""
    client = _make_registry_client()
    client._client.get.return_value = _make_agent_mock_response(
        [_sample_agent_dict()]
    )

    result = await client.discover(requirements=["web_search"])

    assert isinstance(result, list)
    assert len(result) == 1
    assert isinstance(result[0], DiscoveredAgent)


@pytest.mark.asyncio
async def test_discover_calls_discover_endpoint_without_filter_params():
    """discover() calls /v1/agents/discover with no query params and filters client-side.

    The service endpoint only supports consumed_event filtering (by event name),
    not task_name filtering.  discover() fetches all agents and applies the
    requirements filter in Python, so no query params should be sent.
    """
    client = _make_registry_client()
    client._client.get.return_value = _make_agent_mock_response([])

    await client.discover(requirements=["web_search", "translation"])

    client._client.get.assert_called_once()
    call_kwargs = client._client.get.call_args
    url = call_kwargs[0][0]
    # No requirements/include_schemas params sent to the service
    params = call_kwargs[1].get("params", {})
    assert "/v1/agents/discover" in url
    assert "requirements" not in params
    assert "include_schemas" not in params


@pytest.mark.asyncio
async def test_discover_filters_by_task_name_client_side():
    """discover(requirements=[...]) returns only agents whose capability task_name matches."""
    client = _make_registry_client()
    matching = _sample_agent_dict("SearchWorker:1.0.0")   # task_name=web_search
    non_matching = dict(_sample_agent_dict("OtherWorker:1.0.0"))  # will be patched
    non_matching["agentId"] = "other-001"
    non_matching["capabilities"] = [
        {
            "taskName": "billing",
            "description": "Handle billing",
            "consumedEvent": {"eventName": "billing.requested", "topic": "action-requests", "description": ""},
            "producedEvents": [],
        }
    ]
    client._client.get.return_value = _make_agent_mock_response([matching, non_matching])

    result = await client.discover(requirements=["web_search"])

    # Only the agent with task_name containing "web_search" should be returned
    assert len(result) == 1
    assert result[0].agent_id == "search-worker-001"


@pytest.mark.asyncio
async def test_discover_empty_result():
    """discover() handles empty list response gracefully."""
    client = _make_registry_client()
    client._client.get.return_value = _make_agent_mock_response([])

    result = await client.discover(requirements=["unknown_capability"])

    assert result == []


@pytest.mark.asyncio
async def test_discover_maps_agent_definition_to_discovered_agent():
    """discover() maps AgentDefinition fields into DiscoveredAgent correctly."""
    client = _make_registry_client()
    client._client.get.return_value = _make_agent_mock_response(
        [_sample_agent_dict("SearchWorker:2.1.0")]
    )

    result = await client.discover(requirements=["web_search"])

    assert len(result) == 1
    agent = result[0]
    assert agent.agent_id == "search-worker-001"
    assert agent.description == "Performs web search"
    assert len(agent.capabilities) == 1
    assert agent.capabilities[0].task_name == "web_search"


@pytest.mark.asyncio
async def test_discover_parses_version_from_name():
    """discover() extracts version from 'Name:version' convention."""
    client = _make_registry_client()
    client._client.get.return_value = _make_agent_mock_response(
        [_sample_agent_dict("SearchWorker:1.0.0")]
    )

    result = await client.discover(requirements=["web_search"])

    agent = result[0]
    assert agent.name == "SearchWorker"
    assert agent.version == "1.0.0"


@pytest.mark.asyncio
async def test_discover_defaults_version_when_no_suffix():
    """discover() defaults version to '1.0.0' when name has no ':version' suffix."""
    client = _make_registry_client()
    client._client.get.return_value = _make_agent_mock_response(
        [_sample_agent_dict("SearchWorker")]  # no version suffix
    )

    result = await client.discover(requirements=["web_search"])

    agent = result[0]
    assert agent.name == "SearchWorker"
    assert agent.version == "1.0.0"


# ---------------------------------------------------------------------------
# discover_agents() tests (backward compat)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_discover_agents_returns_discovered_agent_list():
    """discover_agents() returns List[DiscoveredAgent], not List[AgentDefinition]."""
    client = _make_registry_client()
    client._client.get.return_value = _make_agent_mock_response(
        [_sample_agent_dict()]
    )

    result = await client.discover_agents()

    assert isinstance(result, list)
    assert len(result) == 1
    assert isinstance(result[0], DiscoveredAgent)
