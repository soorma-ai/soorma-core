"""Identity Service client (Layer 1)."""

from datetime import datetime, timedelta, timezone
import os
from typing import Optional, TypeVar

import httpx
import jwt

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
from soorma_common.tenancy import DEFAULT_PLATFORM_TENANT_ID


ResponseT = TypeVar("ResponseT", bound=BaseDTO)

_CALLER_JWT_ENV = "SOORMA_IDENTITY_CALLER_JWT"
_JWT_SECRET_ENV = "SOORMA_AUTH_JWT_SECRET"
_JWT_ISSUER_ENV = "SOORMA_AUTH_JWT_ISSUER"
_JWT_AUDIENCE_ENV = "SOORMA_AUTH_JWT_AUDIENCE"
_INCLUDE_LEGACY_ALIAS_ENV = "SOORMA_IDENTITY_INCLUDE_LEGACY_ALIAS"


def _is_truthy(value: Optional[str]) -> bool:
    """Return True when env-style flag values are enabled."""
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


class IdentityServiceClient:
    """Low-level HTTP client for identity service."""

    def __init__(
        self,
        base_url: str = "http://localhost:8085",
        timeout: float = 30.0,
        platform_tenant_id: Optional[str] = None,
        admin_api_key: Optional[str] = None,
        caller_jwt: Optional[str] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.platform_tenant_id = platform_tenant_id or DEFAULT_PLATFORM_TENANT_ID
        self.admin_api_key = admin_api_key or os.getenv("IDENTITY_ADMIN_API_KEY", "dev-identity-admin")
        self.caller_jwt = caller_jwt or os.getenv(_CALLER_JWT_ENV)
        self._client = httpx.AsyncClient(timeout=timeout)

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
    ) -> dict[str, str]:
        """Build required identity headers for identity-service calls."""
        if not service_tenant_id or not service_user_id:
            raise ValueError("service_tenant_id and service_user_id are required")

        headers = {
            "X-Tenant-ID": self.platform_tenant_id,
            "X-Identity-Admin-Key": self.admin_api_key,
        }

        caller_jwt = self._resolve_caller_jwt(service_tenant_id, service_user_id)
        if caller_jwt:
            headers["Authorization"] = f"Bearer {caller_jwt}"
            if _is_truthy(os.getenv(_INCLUDE_LEGACY_ALIAS_ENV)):
                headers["X-Service-Tenant-ID"] = service_tenant_id
                headers["X-User-ID"] = service_user_id
            return headers

        headers["X-Service-Tenant-ID"] = service_tenant_id
        headers["X-User-ID"] = service_user_id
        return headers

    def _resolve_caller_jwt(self, service_tenant_id: str, service_user_id: str) -> Optional[str]:
        """Resolve outbound caller JWT from explicit token or local signing config."""
        explicit_token = str(self.caller_jwt or "").strip()
        if explicit_token:
            return explicit_token

        jwt_secret = os.getenv(_JWT_SECRET_ENV)
        if not jwt_secret:
            return None

        issued_at = datetime.now(timezone.utc)
        claims: dict[str, object] = {
            "platform_tenant_id": self.platform_tenant_id,
            "service_tenant_id": service_tenant_id,
            "service_user_id": service_user_id,
            "principal_id": service_user_id,
            "principal_type": "service",
            "roles": ["service"],
            "iat": int(issued_at.timestamp()),
            "exp": int((issued_at + timedelta(minutes=5)).timestamp()),
        }

        jwt_issuer = str(os.getenv(_JWT_ISSUER_ENV) or "").strip()
        jwt_audience = str(os.getenv(_JWT_AUDIENCE_ENV) or "").strip()
        if jwt_issuer:
            claims["iss"] = jwt_issuer
        if jwt_audience:
            claims["aud"] = jwt_audience

        return str(jwt.encode(claims, jwt_secret, algorithm="HS256"))

    async def _post(
        self,
        path: str,
        payload: BaseDTO,
        response_model: type[ResponseT],
        service_tenant_id: str,
        service_user_id: str,
    ) -> ResponseT:
        """Execute POST request against identity-service endpoint."""
        response = await self._client.post(
            f"{self.base_url}{path}",
            headers=self._build_identity_headers(service_tenant_id, service_user_id),
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
    ) -> ResponseT:
        """Execute PUT request against identity-service endpoint."""
        response = await self._client.put(
            f"{self.base_url}{path}",
            headers=self._build_identity_headers(service_tenant_id, service_user_id),
            json=payload.model_dump(by_alias=True),
        )
        response.raise_for_status()
        return response_model.model_validate(response.json())

    async def onboard_tenant(
        self,
        payload: OnboardingRequest,
        service_tenant_id: str,
        service_user_id: str,
    ) -> OnboardingResponse:
        """Create tenant identity domain and bootstrap admin principal."""
        return await self._post(
            "/v1/identity/onboarding",
            payload,
            OnboardingResponse,
            service_tenant_id,
            service_user_id,
        )

    async def create_principal(
        self,
        payload: PrincipalRequest,
        service_tenant_id: str,
        service_user_id: str,
    ) -> PrincipalResponse:
        """Create principal."""
        return await self._post(
            "/v1/identity/principals",
            payload,
            PrincipalResponse,
            service_tenant_id,
            service_user_id,
        )

    async def update_principal(
        self,
        principal_id: str,
        payload: PrincipalRequest,
        service_tenant_id: str,
        service_user_id: str,
    ) -> PrincipalResponse:
        """Update principal."""
        return await self._put(
            f"/v1/identity/principals/{principal_id}",
            payload,
            PrincipalResponse,
            service_tenant_id,
            service_user_id,
        )

    async def revoke_principal(
        self,
        principal_id: str,
        service_tenant_id: str,
        service_user_id: str,
    ) -> PrincipalResponse:
        """Revoke principal."""
        response = await self._client.post(
            f"{self.base_url}/v1/identity/principals/{principal_id}/revoke",
            headers=self._build_identity_headers(service_tenant_id, service_user_id),
            json={},
        )
        response.raise_for_status()
        return PrincipalResponse.model_validate(response.json())

    async def issue_token(
        self,
        payload: TokenIssueRequest,
        service_tenant_id: str,
        service_user_id: str,
    ) -> TokenIssueResponse:
        """Issue platform/delegated token based on issuance policy."""
        return await self._post(
            "/v1/identity/tokens/issue",
            payload,
            TokenIssueResponse,
            service_tenant_id=service_tenant_id,
            service_user_id=service_user_id,
        )

    async def register_delegated_issuer(
        self,
        payload: DelegatedIssuerRequest,
        service_tenant_id: str,
        service_user_id: str,
    ) -> DelegatedIssuerResponse:
        """Register delegated issuer trust metadata."""
        return await self._post(
            "/v1/identity/delegated-issuers",
            payload,
            DelegatedIssuerResponse,
            service_tenant_id,
            service_user_id,
        )

    async def update_delegated_issuer(
        self,
        delegated_issuer_id: str,
        payload: DelegatedIssuerRequest,
        service_tenant_id: str,
        service_user_id: str,
    ) -> DelegatedIssuerResponse:
        """Update delegated issuer trust metadata."""
        return await self._put(
            f"/v1/identity/delegated-issuers/{delegated_issuer_id}",
            payload,
            DelegatedIssuerResponse,
            service_tenant_id,
            service_user_id,
        )

    async def evaluate_mapping(
        self,
        payload: MappingEvaluationRequest,
        service_tenant_id: str,
        service_user_id: str,
    ) -> MappingEvaluationResponse:
        """Evaluate identity mapping collision policy."""
        return await self._post(
            "/v1/identity/mappings/evaluate",
            payload,
            MappingEvaluationResponse,
            service_tenant_id,
            service_user_id,
        )
