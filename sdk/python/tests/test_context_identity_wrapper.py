"""Tests for IdentityClient wrapper (Layer 2)."""

from unittest.mock import AsyncMock

import pytest
from soorma_common.models import (
    OnboardingRequest,
    OnboardingResponse,
    TenantAdminCredentialRotateResponse,
    TokenIssueRequest,
    TokenIssueResponse,
    TokenIssuanceType,
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
            bootstrap_admin_external_ref="admin@example.com",
        )
        mock_service_client.onboard_tenant = AsyncMock(
            return_value=OnboardingResponse(
                tenant_domain_id="tenant-domain-1",
                platform_tenant_id="platform-tenant-1",
                bootstrap_admin_principal_id="principal-1",
                tenant_admin_api_key="idadm.tak_123.secret-value",
                status="created",
            )
        )
        identity_wrapper._client = mock_service_client

        result = await identity_wrapper.onboard_tenant(payload)

        assert result.tenant_domain_id == "tenant-domain-1"
        mock_service_client.onboard_tenant.assert_called_once_with(payload, superuser_api_key=None)

    @pytest.mark.asyncio
    async def test_requires_platform_tenant_for_tenant_admin_operations(self, identity_wrapper: IdentityClient):
        """Wrapper should fail closed when tenant admin scope is missing."""
        with pytest.raises(ValueError, match="platform_tenant_id is required"):
            await identity_wrapper.issue_token(
                payload=TokenIssueRequest(
                    principal_id="principal-1",
                    issuance_type=TokenIssuanceType.PLATFORM,
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
                principal_id="principal-1",
                issuance_type=TokenIssuanceType.PLATFORM,
            ),
            platform_tenant_id="platform-tenant-1",
            tenant_admin_api_key="tenant-admin-key",
        )

        assert result.token_type == "Bearer"
        assert isinstance(result.token, str)
        assert result.token
        mock_service_client.issue_token.assert_called_once_with(
            TokenIssueRequest(
                principal_id="principal-1",
                issuance_type=TokenIssuanceType.PLATFORM,
            ),
            platform_tenant_id="platform-tenant-1",
            tenant_admin_api_key="tenant-admin-key",
        )

    @pytest.mark.asyncio
    async def test_blank_platform_tenant_values_fail_closed(self, identity_wrapper: IdentityClient):
        """Wrapper must reject blank tenant scope instead of delegating."""
        mock_service_client = AsyncMock(spec=IdentityServiceClient)
        mock_service_client.issue_token = AsyncMock(
            return_value=TokenIssueResponse(token_type="Bearer", token="stub-token")
        )
        identity_wrapper._client = mock_service_client

        with pytest.raises(ValueError, match="platform_tenant_id is required"):
            await identity_wrapper.issue_token(
                payload=TokenIssueRequest(
                    principal_id="principal-1",
                    issuance_type=TokenIssuanceType.PLATFORM,
                ),
                platform_tenant_id="   ",
                tenant_admin_api_key="tenant-admin-key",
            )

    @pytest.mark.asyncio
    async def test_rotate_tenant_admin_key_delegates(self, identity_wrapper: IdentityClient):
        """Wrapper should forward tenant admin key rotation to the low-level client."""
        mock_service_client = AsyncMock(spec=IdentityServiceClient)
        mock_service_client.rotate_tenant_admin_key = AsyncMock(
            return_value=TenantAdminCredentialRotateResponse(
                credential_id="tak_rotated",
                tenant_admin_api_key="idadm.tak_rotated.rotated-secret",
                status="rotated",
            )
        )
        identity_wrapper._client = mock_service_client

        result = await identity_wrapper.rotate_tenant_admin_key(
            platform_tenant_id="platform-tenant-1",
            tenant_admin_api_key="idadm.tak_old.old-secret",
        )

        assert result.status == "rotated"
        mock_service_client.rotate_tenant_admin_key.assert_called_once_with(
            platform_tenant_id="platform-tenant-1",
            tenant_admin_api_key="idadm.tak_old.old-secret",
        )
