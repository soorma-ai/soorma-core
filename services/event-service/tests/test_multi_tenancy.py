"""Multi-tenancy trust-boundary tests for Event Service publish endpoint."""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from soorma_common.tenancy import DEFAULT_PLATFORM_TENANT_ID
from src.main import app


@pytest.fixture
async def async_client():
    """Create async test client for API endpoint tests."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


def _base_event_payload() -> dict:
    """Return a valid base publish payload used by trust-boundary tests."""
    return {
        "event": {
            "source": "test-agent",
            "type": "test.event",
            "topic": "action-requests",
            "data": {"key": "value"},
            "tenant_id": "service_tenant_1",
            "user_id": "service_user_1",
        }
    }


@pytest.mark.asyncio
async def test_publish_overwrites_payload_platform_tenant_id(async_client):
    """Event Service must overwrite any payload-supplied platform_tenant_id."""
    payload = _base_event_payload()
    payload["event"]["platform_tenant_id"] = "spt_spoofed"

    with patch("src.api.routes.events.event_manager.publish", new=AsyncMock()) as mock_publish:
        response = await async_client.post(
            "/v1/events/publish",
            json=payload,
            headers={"X-Tenant-ID": "spt_real"},
        )

    assert response.status_code == 200
    publish_message = mock_publish.await_args.args[1]
    assert publish_message["platform_tenant_id"] == "spt_real"


@pytest.mark.asyncio
async def test_publish_fallback_to_default_platform_tenant(async_client):
    """Missing X-Tenant-ID should use DEFAULT_PLATFORM_TENANT_ID fallback."""
    payload = _base_event_payload()

    with patch("src.api.routes.events.event_manager.publish", new=AsyncMock()) as mock_publish:
        response = await async_client.post("/v1/events/publish", json=payload)

    assert response.status_code == 200
    publish_message = mock_publish.await_args.args[1]
    assert publish_message["platform_tenant_id"] == DEFAULT_PLATFORM_TENANT_ID


@pytest.mark.asyncio
async def test_publish_rejects_missing_tenant_id_after_sanitization(async_client, tenancy_headers):
    """tenant_id is required after sanitization."""
    payload = _base_event_payload()
    payload["event"]["tenant_id"] = "   "

    with patch("src.api.routes.events.event_manager.publish", new=AsyncMock()) as mock_publish:
        response = await async_client.post(
            "/v1/events/publish",
            json=payload,
            headers=tenancy_headers,
        )

    assert response.status_code == 422
    assert response.json()["detail"] == "tenant_id is required"
    mock_publish.assert_not_called()


@pytest.mark.asyncio
async def test_publish_rejects_missing_user_id_after_sanitization(async_client, tenancy_headers):
    """user_id is required after sanitization."""
    payload = _base_event_payload()
    payload["event"]["user_id"] = "   "

    with patch("src.api.routes.events.event_manager.publish", new=AsyncMock()) as mock_publish:
        response = await async_client.post(
            "/v1/events/publish",
            json=payload,
            headers=tenancy_headers,
        )

    assert response.status_code == 422
    assert response.json()["detail"] == "user_id is required"
    mock_publish.assert_not_called()


@pytest.mark.asyncio
async def test_publish_rejects_oversized_platform_tenant_id(async_client):
    """Oversized platform_tenant_id values must fail closed."""
    payload = _base_event_payload()

    oversized_header = {"X-Tenant-ID": "a" * 65}
    with patch("src.api.routes.events.event_manager.publish", new=AsyncMock()) as mock_publish:
        response = await async_client.post(
            "/v1/events/publish",
            json=payload,
            headers=oversized_header,
        )

    assert response.status_code == 422
    assert "platform_tenant_id" in response.json()["detail"]
    mock_publish.assert_not_called()


@pytest.mark.asyncio
async def test_publish_trims_tenant_and_user_id(async_client, tenancy_headers):
    """tenant_id and user_id should be trimmed before publish."""
    payload = _base_event_payload()
    payload["event"]["tenant_id"] = "  svc_tenant  "
    payload["event"]["user_id"] = "  svc_user  "

    with patch("src.api.routes.events.event_manager.publish", new=AsyncMock()) as mock_publish:
        response = await async_client.post(
            "/v1/events/publish",
            json=payload,
            headers=tenancy_headers,
        )

    assert response.status_code == 200
    publish_message = mock_publish.await_args.args[1]
    assert publish_message["tenant_id"] == "svc_tenant"
    assert publish_message["user_id"] == "svc_user"
