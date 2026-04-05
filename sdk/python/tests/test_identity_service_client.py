"""Tests for IdentityServiceClient behavior contracts."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from soorma_common.models import OnboardingRequest

from soorma.identity.client import IdentityServiceClient


@pytest.fixture
def identity_client() -> IdentityServiceClient:
    """Create low-level identity service client."""
    return IdentityServiceClient(base_url="http://localhost:8085")


class TestIdentityServiceClientContracts:
    """Verify low-level client behavior contracts."""

    @pytest.mark.asyncio
    async def test_onboard_tenant_returns_domain_payload(self, identity_client: IdentityServiceClient):
        """onboard_tenant should return normalized onboarding response payload."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "tenant_domain_id": "tenant-domain-1",
            "bootstrap_admin_principal_id": "principal-1",
            "status": "created",
        }
        mock_response.raise_for_status = MagicMock()

        identity_client._client = AsyncMock()
        identity_client._client.post = AsyncMock(return_value=mock_response)

        result = await identity_client.onboard_tenant(
            payload=OnboardingRequest(
                tenant_domain_id="tenant-domain-1",
                platform_tenant_id="platform-tenant-1",
                bootstrap_admin_principal_id="principal-1",
                created_by="system",
            ),
            service_tenant_id="svc-tenant",
            service_user_id="svc-user",
        )

        assert result.tenant_domain_id == "tenant-domain-1"
        assert result.status == "created"
        identity_client._client.post.assert_called_once()
