"""Tests for IdentityClient wrapper (Layer 2)."""

from unittest.mock import AsyncMock

import pytest
from soorma_common.models import (
    OnboardingRequest,
    OnboardingResponse,
    TokenIssueRequest,
    TokenIssueResponse,
)

from soorma.identity.client import IdentityServiceClient
from soorma.identity.wrapper import IdentityClient


@pytest.fixture
def identity_wrapper() -> IdentityClient:
    """Create wrapper instance for tests."""
    return IdentityClient(base_url="http://localhost:8085")


@pytest.fixture
def mock_service_client() -> AsyncMock:
    """Create mocked identity service client."""
    return AsyncMock(spec=IdentityServiceClient)


class TestIdentityWrapper:
    """Identity wrapper delegation tests."""

    @pytest.mark.asyncio
    async def test_onboard_tenant_delegates(self, identity_wrapper: IdentityClient, mock_service_client: AsyncMock):
        """Wrapper should forward onboarding calls to low-level service client."""
        payload = OnboardingRequest(
            tenant_domain_id="tenant-domain-1",
            platform_tenant_id="platform-tenant-1",
            bootstrap_admin_principal_id="principal-1",
            created_by="system",
        )
        mock_service_client.onboard_tenant = AsyncMock(
            return_value=OnboardingResponse(
                tenant_domain_id="tenant-domain-1",
                bootstrap_admin_principal_id="principal-1",
                status="created",
            )
        )
        identity_wrapper._client = mock_service_client

        result = await identity_wrapper.onboard_tenant(
            payload,
            tenant_id="svc-tenant",
            user_id="svc-user",
        )

        assert result.tenant_domain_id == "tenant-domain-1"
        mock_service_client.onboard_tenant.assert_called_once_with(
            payload,
            service_tenant_id="svc-tenant",
            service_user_id="svc-user",
        )

    @pytest.mark.asyncio
    async def test_requires_identity_context(self, identity_wrapper: IdentityClient):
        """Wrapper should fail closed when tenant/user identity is missing."""
        with pytest.raises(ValueError, match="tenant_id and user_id are required"):
            await identity_wrapper.issue_token(
                payload=TokenIssueRequest(
                    tenant_domain_id="tenant-domain-1",
                    principal_id="principal-1",
                    issuance_type="platform",
                )
            )

    @pytest.mark.asyncio
    async def test_issue_token_contract_returns_bearer_payload(self, identity_wrapper: IdentityClient):
        """Wrapper issue_token contract should return token payload."""
        mock_service_client = AsyncMock(spec=IdentityServiceClient)
        mock_service_client.issue_token = AsyncMock(
            return_value=TokenIssueResponse(token_type="Bearer", token="stub-token")
        )
        identity_wrapper._client = mock_service_client

        result = await identity_wrapper.issue_token(
            payload=TokenIssueRequest(
                tenant_domain_id="tenant-domain-1",
                principal_id="principal-1",
                issuance_type="platform",
            ),
            tenant_id="svc-tenant",
            user_id="svc-user",
        )

        assert result.token_type == "Bearer"
        assert isinstance(result.token, str)
        assert result.token
        mock_service_client.issue_token.assert_called_once_with(
            TokenIssueRequest(
                tenant_domain_id="tenant-domain-1",
                principal_id="principal-1",
                issuance_type="platform",
            ),
            service_tenant_id="svc-tenant",
            service_user_id="svc-user",
        )
