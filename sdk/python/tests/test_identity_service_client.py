"""Tests for IdentityServiceClient behavior contracts."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from soorma_common.models import OnboardingRequest, TokenIssueRequest, TokenIssuanceType

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
            "platform_tenant_id": "platform-tenant-1",
            "bootstrap_admin_principal_id": "principal-1",
            "status": "created",
        }
        mock_response.raise_for_status = MagicMock()

        identity_client._client = AsyncMock()
        identity_client._client.post = AsyncMock(return_value=mock_response)

        result = await identity_client.onboard_tenant(
            payload=OnboardingRequest(),
            service_tenant_id="svc-tenant",
            service_user_id="svc-user",
        )

        assert result.tenant_domain_id == "tenant-domain-1"
        assert result.status == "created"
        identity_client._client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_issue_token_uses_admin_headers_when_platform_tenant_is_bound(
        self,
        identity_client: IdentityServiceClient,
    ):
        """Client should send bound platform tenant plus admin key when available."""

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "token": "signed.jwt.value",
            "token_type": "Bearer",
        }
        mock_response.raise_for_status = MagicMock()

        identity_client._client = AsyncMock()
        identity_client._client.post = AsyncMock(return_value=mock_response)
        identity_client.set_platform_tenant_id("platform-tenant-1")

        await identity_client.issue_token(
            payload=TokenIssueRequest(
                principal_id="principal-1",
                issuance_type=TokenIssuanceType.PLATFORM,
            ),
            service_tenant_id="svc-tenant",
            service_user_id="svc-user",
        )

        headers = identity_client._client.post.call_args.kwargs["headers"]
        assert headers["X-Tenant-ID"] == identity_client.platform_tenant_id
        assert headers["X-Identity-Admin-Key"] == identity_client.admin_api_key
        assert "Authorization" not in headers
        assert "X-Service-Tenant-ID" not in headers
        assert "X-User-ID" not in headers

    @pytest.mark.asyncio
    async def test_issue_token_uses_admin_key_only_before_platform_tenant_is_bound(
        self,
        identity_client: IdentityServiceClient,
    ):
        """Client should use only the admin key before onboarding returns platform tenant."""

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "token": "signed.jwt.value",
            "token_type": "Bearer",
        }
        mock_response.raise_for_status = MagicMock()

        identity_client._client = AsyncMock()
        identity_client._client.post = AsyncMock(return_value=mock_response)

        await identity_client.issue_token(
            payload=TokenIssueRequest(
                principal_id="principal-1",
                issuance_type=TokenIssuanceType.PLATFORM,
            ),
            service_tenant_id="svc-tenant",
            service_user_id="svc-user",
        )

        headers = identity_client._client.post.call_args.kwargs["headers"]
        assert headers["X-Identity-Admin-Key"] == identity_client.admin_api_key
        assert "X-Tenant-ID" not in headers
        assert "Authorization" not in headers
        assert "X-Service-Tenant-ID" not in headers
        assert "X-User-ID" not in headers

    @pytest.mark.asyncio
    async def test_onboard_tenant_does_not_require_bound_platform_tenant(
        self,
        identity_client: IdentityServiceClient,
    ):
        """Onboarding should work before any platform tenant ID has been bound."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "tenant_domain_id": "tenant-domain-1",
            "platform_tenant_id": "platform-tenant-1",
            "bootstrap_admin_principal_id": "principal-1",
            "status": "created",
        }
        mock_response.raise_for_status = MagicMock()

        identity_client._client = AsyncMock()
        identity_client._client.post = AsyncMock(return_value=mock_response)

        await identity_client.onboard_tenant(
            payload=OnboardingRequest(),
            service_tenant_id="svc-tenant",
            service_user_id="svc-user",
        )

        headers = identity_client._client.post.call_args.kwargs["headers"]
        assert headers["X-Identity-Admin-Key"] == identity_client.admin_api_key
        assert "X-Tenant-ID" not in headers
        assert "X-Service-Tenant-ID" not in headers
        assert "X-User-ID" not in headers
