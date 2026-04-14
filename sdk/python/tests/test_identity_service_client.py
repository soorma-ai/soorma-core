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
    async def test_issue_token_uses_jwt_authorization_when_configured(
        self,
        identity_client: IdentityServiceClient,
        monkeypatch: pytest.MonkeyPatch,
    ):
        """Client should send canonical outbound JWT auth when JWT config is present."""
        monkeypatch.setenv("SOORMA_AUTH_JWT_SECRET", "test-secret")
        monkeypatch.setenv("SOORMA_AUTH_JWT_ISSUER", "soorma-identity-service")
        monkeypatch.setenv("SOORMA_AUTH_JWT_AUDIENCE", "soorma-services")
        monkeypatch.delenv("SOORMA_IDENTITY_INCLUDE_LEGACY_ALIAS", raising=False)

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
        assert headers["X-Tenant-ID"] == identity_client.platform_tenant_id
        assert headers["X-Identity-Admin-Key"] == identity_client.admin_api_key
        assert headers["Authorization"].startswith("Bearer ")
        assert "X-Service-Tenant-ID" not in headers
        assert "X-User-ID" not in headers

    @pytest.mark.asyncio
    async def test_issue_token_uses_legacy_alias_when_jwt_not_configured(
        self,
        identity_client: IdentityServiceClient,
        monkeypatch: pytest.MonkeyPatch,
    ):
        """Client should retain legacy headers when outbound JWT cannot be built."""
        monkeypatch.delenv("SOORMA_AUTH_JWT_SECRET", raising=False)
        monkeypatch.delenv("SOORMA_IDENTITY_CALLER_JWT", raising=False)

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
        assert headers["X-Service-Tenant-ID"] == "svc-tenant"
        assert headers["X-User-ID"] == "svc-user"
        assert "Authorization" not in headers

    @pytest.mark.asyncio
    async def test_issue_token_supports_matching_alias_compatibility_mode(
        self,
        identity_client: IdentityServiceClient,
        monkeypatch: pytest.MonkeyPatch,
    ):
        """Compatibility mode should include alias headers alongside JWT auth."""
        monkeypatch.setenv("SOORMA_AUTH_JWT_SECRET", "test-secret")
        monkeypatch.setenv("SOORMA_IDENTITY_INCLUDE_LEGACY_ALIAS", "true")

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
        assert headers["Authorization"].startswith("Bearer ")
        assert headers["X-Service-Tenant-ID"] == "svc-tenant"
        assert headers["X-User-ID"] == "svc-user"
