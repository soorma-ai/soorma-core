"""Identity Service client (Layer 1)."""

import os
from typing import Optional, TypeVar

import httpx

from soorma_common.models import (
    BaseDTO,
    DelegatedIssuerRequest,
    DelegatedIssuerResponse,
    MappingEvaluationRequest,
    MappingEvaluationResponse,
    OnboardingRequest,
    OnboardingResponse,
    PrincipalRequest,
    PrincipalResponse,
    TenantAdminCredentialRotateResponse,
    TokenIssueRequest,
    TokenIssueResponse,
)


ResponseT = TypeVar("ResponseT", bound=BaseDTO)


class IdentityServiceClient:
    """Low-level HTTP client for identity service."""

    def __init__(
        self,
        base_url: str = "http://localhost:8085",
        timeout: float = 30.0,
        superuser_api_key: Optional[str] = None,
        tenant_admin_api_key: Optional[str] = None,
        platform_tenant_id: Optional[str] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.platform_tenant_id: Optional[str] = str(
            platform_tenant_id or os.getenv("SOORMA_PLATFORM_TENANT_ID", "")
        ).strip() or None
        self.superuser_api_key = superuser_api_key or os.getenv(
            "IDENTITY_SUPERUSER_API_KEY",
            os.getenv("IDENTITY_ADMIN_API_KEY", "dev-identity-admin"),
        )
        self.tenant_admin_api_key = tenant_admin_api_key or os.getenv(
            "IDENTITY_TENANT_ADMIN_API_KEY",
            "",
        )
        self._client = httpx.AsyncClient(timeout=timeout)

    def set_platform_tenant_id(self, platform_tenant_id: Optional[str]) -> None:
        """Bind the platform tenant ID once onboarding or discovery has provided it."""
        value = str(platform_tenant_id or "").strip()
        self.platform_tenant_id = value or None

    def set_tenant_admin_api_key(self, tenant_admin_api_key: Optional[str]) -> None:
        """Bind the tenant admin API key once onboarding has provided it."""
        value = str(tenant_admin_api_key or "").strip()
        self.tenant_admin_api_key = value or None

    async def close(self) -> None:
        """Close underlying HTTP client."""
        await self._client.aclose()

    async def __aenter__(self) -> "IdentityServiceClient":
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()

    def _build_superuser_headers(
        self,
        superuser_api_key: Optional[str] = None,
    ) -> dict[str, str]:
        """Build headers for superuser-scoped identity operations."""
        resolved_superuser_api_key = str(
            superuser_api_key or self.superuser_api_key or ""
        ).strip()
        if not resolved_superuser_api_key:
            raise ValueError("superuser_api_key is required for onboarding")
        return {"X-Identity-Admin-Key": resolved_superuser_api_key}

    def _resolve_tenant_admin_context(
        self,
        platform_tenant_id: Optional[str] = None,
        tenant_admin_api_key: Optional[str] = None,
    ) -> tuple[str, str]:
        """Resolve platform tenant scope and tenant admin key for tenant admin operations."""
        resolved_platform_tenant_id = str(
            platform_tenant_id or self.platform_tenant_id or ""
        ).strip() or None
        resolved_tenant_admin_api_key = str(
            tenant_admin_api_key or self.tenant_admin_api_key or ""
        ).strip() or None
        if resolved_platform_tenant_id is None:
            raise ValueError("platform_tenant_id is required for tenant admin operations")
        if resolved_tenant_admin_api_key is None:
            raise ValueError("tenant_admin_api_key is required for tenant admin operations")
        return resolved_platform_tenant_id, resolved_tenant_admin_api_key

    def _build_tenant_admin_headers(
        self,
        platform_tenant_id: Optional[str] = None,
        tenant_admin_api_key: Optional[str] = None,
    ) -> dict[str, str]:
        """Build headers for tenant admin scoped identity-service calls."""
        resolved_platform_tenant_id, resolved_tenant_admin_api_key = self._resolve_tenant_admin_context(
            platform_tenant_id=platform_tenant_id,
            tenant_admin_api_key=tenant_admin_api_key,
        )
        return {
            "X-Identity-Admin-Key": resolved_tenant_admin_api_key,
            "X-Tenant-ID": resolved_platform_tenant_id,
        }

    async def _post(
        self,
        path: str,
        payload: BaseDTO,
        response_model: type[ResponseT],
        platform_tenant_id: Optional[str] = None,
        tenant_admin_api_key: Optional[str] = None,
    ) -> ResponseT:
        """Execute POST request against identity-service endpoint."""
        response = await self._client.post(
            f"{self.base_url}{path}",
            headers=self._build_tenant_admin_headers(
                platform_tenant_id=platform_tenant_id,
                tenant_admin_api_key=tenant_admin_api_key,
            ),
            json=payload.model_dump(by_alias=True),
        )
        response.raise_for_status()
        return response_model.model_validate(response.json())

    async def _put(
        self,
        path: str,
        payload: BaseDTO,
        response_model: type[ResponseT],
        platform_tenant_id: Optional[str] = None,
        tenant_admin_api_key: Optional[str] = None,
    ) -> ResponseT:
        """Execute PUT request against identity-service endpoint."""
        response = await self._client.put(
            f"{self.base_url}{path}",
            headers=self._build_tenant_admin_headers(
                platform_tenant_id=platform_tenant_id,
                tenant_admin_api_key=tenant_admin_api_key,
            ),
            json=payload.model_dump(by_alias=True),
        )
        response.raise_for_status()
        return response_model.model_validate(response.json())

    async def onboard_tenant(
        self,
        payload: OnboardingRequest,
        superuser_api_key: Optional[str] = None,
    ) -> OnboardingResponse:
        """Create tenant identity domain and bootstrap admin principal."""
        response = await self._client.post(
            f"{self.base_url}/v1/identity/onboarding",
            headers=self._build_superuser_headers(superuser_api_key=superuser_api_key),
            json=payload.model_dump(by_alias=True),
        )
        response.raise_for_status()
        result = OnboardingResponse.model_validate(response.json())
        self.set_platform_tenant_id(result.platform_tenant_id)
        self.set_tenant_admin_api_key(result.tenant_admin_api_key)
        return result

    async def create_principal(
        self,
        payload: PrincipalRequest,
        platform_tenant_id: Optional[str] = None,
        tenant_admin_api_key: Optional[str] = None,
    ) -> PrincipalResponse:
        """Create principal."""
        return await self._post(
            "/v1/identity/principals",
            payload,
            PrincipalResponse,
            platform_tenant_id=platform_tenant_id,
            tenant_admin_api_key=tenant_admin_api_key,
        )

    async def update_principal(
        self,
        principal_id: str,
        payload: PrincipalRequest,
        platform_tenant_id: Optional[str] = None,
        tenant_admin_api_key: Optional[str] = None,
    ) -> PrincipalResponse:
        """Update principal."""
        return await self._put(
            f"/v1/identity/principals/{principal_id}",
            payload,
            PrincipalResponse,
            platform_tenant_id=platform_tenant_id,
            tenant_admin_api_key=tenant_admin_api_key,
        )

    async def revoke_principal(
        self,
        principal_id: str,
        platform_tenant_id: Optional[str] = None,
        tenant_admin_api_key: Optional[str] = None,
    ) -> PrincipalResponse:
        """Revoke principal."""
        response = await self._client.post(
            f"{self.base_url}/v1/identity/principals/{principal_id}/revoke",
            headers=self._build_tenant_admin_headers(
                platform_tenant_id=platform_tenant_id,
                tenant_admin_api_key=tenant_admin_api_key,
            ),
            json={},
        )
        response.raise_for_status()
        return PrincipalResponse.model_validate(response.json())

    async def issue_token(
        self,
        payload: TokenIssueRequest,
        platform_tenant_id: Optional[str] = None,
        tenant_admin_api_key: Optional[str] = None,
    ) -> TokenIssueResponse:
        """Issue platform/delegated token based on issuance policy."""
        return await self._post(
            "/v1/identity/tokens/issue",
            payload,
            TokenIssueResponse,
            platform_tenant_id=platform_tenant_id,
            tenant_admin_api_key=tenant_admin_api_key,
        )

    async def rotate_tenant_admin_key(
        self,
        platform_tenant_id: Optional[str] = None,
        tenant_admin_api_key: Optional[str] = None,
    ) -> TenantAdminCredentialRotateResponse:
        """Rotate tenant admin API key and bind the new credential for subsequent requests."""
        response = await self._client.post(
            f"{self.base_url}/v1/identity/tenant-admin-credentials/rotate",
            headers=self._build_tenant_admin_headers(
                platform_tenant_id=platform_tenant_id,
                tenant_admin_api_key=tenant_admin_api_key,
            ),
            json={},
        )
        response.raise_for_status()
        result = TenantAdminCredentialRotateResponse.model_validate(response.json())
        self.set_tenant_admin_api_key(result.tenant_admin_api_key)
        return result

    async def register_delegated_issuer(
        self,
        payload: DelegatedIssuerRequest,
        platform_tenant_id: Optional[str] = None,
        tenant_admin_api_key: Optional[str] = None,
    ) -> DelegatedIssuerResponse:
        """Register delegated issuer trust metadata."""
        return await self._post(
            "/v1/identity/delegated-issuers",
            payload,
            DelegatedIssuerResponse,
            platform_tenant_id=platform_tenant_id,
            tenant_admin_api_key=tenant_admin_api_key,
        )

    async def update_delegated_issuer(
        self,
        delegated_issuer_id: str,
        payload: DelegatedIssuerRequest,
        platform_tenant_id: Optional[str] = None,
        tenant_admin_api_key: Optional[str] = None,
    ) -> DelegatedIssuerResponse:
        """Update delegated issuer trust metadata."""
        return await self._put(
            f"/v1/identity/delegated-issuers/{delegated_issuer_id}",
            payload,
            DelegatedIssuerResponse,
            platform_tenant_id=platform_tenant_id,
            tenant_admin_api_key=tenant_admin_api_key,
        )

    async def evaluate_mapping(
        self,
        payload: MappingEvaluationRequest,
        platform_tenant_id: Optional[str] = None,
        tenant_admin_api_key: Optional[str] = None,
    ) -> MappingEvaluationResponse:
        """Evaluate identity mapping collision policy."""
        return await self._post(
            "/v1/identity/mappings/evaluate",
            payload,
            MappingEvaluationResponse,
            platform_tenant_id=platform_tenant_id,
            tenant_admin_api_key=tenant_admin_api_key,
        )
