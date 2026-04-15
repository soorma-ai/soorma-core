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
        admin_api_key: Optional[str] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.platform_tenant_id: Optional[str] = None
        self.admin_api_key = admin_api_key or os.getenv("IDENTITY_ADMIN_API_KEY", "dev-identity-admin")
        self._client = httpx.AsyncClient(timeout=timeout)

    def set_platform_tenant_id(self, platform_tenant_id: Optional[str]) -> None:
        """Bind the platform tenant ID once onboarding or discovery has provided it."""
        value = str(platform_tenant_id or "").strip()
        self.platform_tenant_id = value or None

    async def close(self) -> None:
        """Close underlying HTTP client."""
        await self._client.aclose()

    async def __aenter__(self) -> "IdentityServiceClient":
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()

    def _build_identity_headers(
        self,
        service_tenant_id: str,
        service_user_id: str,
        platform_tenant_id: Optional[str] = None,
    ) -> dict[str, str]:
        """Build required identity headers for identity-service calls."""
        resolved_platform_tenant_id = str(
            platform_tenant_id or self.platform_tenant_id or ""
        ).strip() or None
        headers = {"X-Identity-Admin-Key": self.admin_api_key}
        if resolved_platform_tenant_id is not None:
            headers["X-Tenant-ID"] = resolved_platform_tenant_id
        return headers

    async def _post(
        self,
        path: str,
        payload: BaseDTO,
        response_model: type[ResponseT],
        service_tenant_id: str,
        service_user_id: str,
        platform_tenant_id: Optional[str] = None,
    ) -> ResponseT:
        """Execute POST request against identity-service endpoint."""
        response = await self._client.post(
            f"{self.base_url}{path}",
            headers=self._build_identity_headers(
                service_tenant_id,
                service_user_id,
                platform_tenant_id=platform_tenant_id,
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
        service_tenant_id: str,
        service_user_id: str,
        platform_tenant_id: Optional[str] = None,
    ) -> ResponseT:
        """Execute PUT request against identity-service endpoint."""
        response = await self._client.put(
            f"{self.base_url}{path}",
            headers=self._build_identity_headers(
                service_tenant_id,
                service_user_id,
                platform_tenant_id=platform_tenant_id,
            ),
            json=payload.model_dump(by_alias=True),
        )
        response.raise_for_status()
        return response_model.model_validate(response.json())

    async def onboard_tenant(
        self,
        payload: OnboardingRequest,
        service_tenant_id: str,
        service_user_id: str,
        platform_tenant_id: Optional[str] = None,
    ) -> OnboardingResponse:
        """Create tenant identity domain and bootstrap admin principal."""
        return await self._post(
            "/v1/identity/onboarding",
            payload,
            OnboardingResponse,
            service_tenant_id,
            service_user_id,
            platform_tenant_id=platform_tenant_id,
        )

    async def create_principal(
        self,
        payload: PrincipalRequest,
        service_tenant_id: str,
        service_user_id: str,
        platform_tenant_id: Optional[str] = None,
    ) -> PrincipalResponse:
        """Create principal."""
        return await self._post(
            "/v1/identity/principals",
            payload,
            PrincipalResponse,
            service_tenant_id,
            service_user_id,
            platform_tenant_id=platform_tenant_id,
        )

    async def update_principal(
        self,
        principal_id: str,
        payload: PrincipalRequest,
        service_tenant_id: str,
        service_user_id: str,
        platform_tenant_id: Optional[str] = None,
    ) -> PrincipalResponse:
        """Update principal."""
        return await self._put(
            f"/v1/identity/principals/{principal_id}",
            payload,
            PrincipalResponse,
            service_tenant_id,
            service_user_id,
            platform_tenant_id=platform_tenant_id,
        )

    async def revoke_principal(
        self,
        principal_id: str,
        service_tenant_id: str,
        service_user_id: str,
        platform_tenant_id: Optional[str] = None,
    ) -> PrincipalResponse:
        """Revoke principal."""
        response = await self._client.post(
            f"{self.base_url}/v1/identity/principals/{principal_id}/revoke",
            headers=self._build_identity_headers(
                service_tenant_id,
                service_user_id,
                platform_tenant_id=platform_tenant_id,
            ),
            json={},
        )
        response.raise_for_status()
        return PrincipalResponse.model_validate(response.json())

    async def issue_token(
        self,
        payload: TokenIssueRequest,
        service_tenant_id: str,
        service_user_id: str,
        platform_tenant_id: Optional[str] = None,
    ) -> TokenIssueResponse:
        """Issue platform/delegated token based on issuance policy."""
        return await self._post(
            "/v1/identity/tokens/issue",
            payload,
            TokenIssueResponse,
            service_tenant_id=service_tenant_id,
            service_user_id=service_user_id,
            platform_tenant_id=platform_tenant_id,
        )

    async def register_delegated_issuer(
        self,
        payload: DelegatedIssuerRequest,
        service_tenant_id: str,
        service_user_id: str,
        platform_tenant_id: Optional[str] = None,
    ) -> DelegatedIssuerResponse:
        """Register delegated issuer trust metadata."""
        return await self._post(
            "/v1/identity/delegated-issuers",
            payload,
            DelegatedIssuerResponse,
            service_tenant_id,
            service_user_id,
            platform_tenant_id=platform_tenant_id,
        )

    async def update_delegated_issuer(
        self,
        delegated_issuer_id: str,
        payload: DelegatedIssuerRequest,
        service_tenant_id: str,
        service_user_id: str,
        platform_tenant_id: Optional[str] = None,
    ) -> DelegatedIssuerResponse:
        """Update delegated issuer trust metadata."""
        return await self._put(
            f"/v1/identity/delegated-issuers/{delegated_issuer_id}",
            payload,
            DelegatedIssuerResponse,
            service_tenant_id,
            service_user_id,
            platform_tenant_id=platform_tenant_id,
        )

    async def evaluate_mapping(
        self,
        payload: MappingEvaluationRequest,
        service_tenant_id: str,
        service_user_id: str,
        platform_tenant_id: Optional[str] = None,
    ) -> MappingEvaluationResponse:
        """Evaluate identity mapping collision policy."""
        return await self._post(
            "/v1/identity/mappings/evaluate",
            payload,
            MappingEvaluationResponse,
            service_tenant_id,
            service_user_id,
            platform_tenant_id=platform_tenant_id,
        )
