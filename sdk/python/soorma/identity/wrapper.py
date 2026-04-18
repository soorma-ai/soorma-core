"""Identity client wrapper (Layer 2)."""

from dataclasses import dataclass, field
import contextvars
import os
from typing import Any, Optional, TypedDict

from soorma_common.models import (
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

from .client import IdentityServiceClient


class IdentityContextMetadata(TypedDict):
    """Identity metadata bound from an event envelope."""

    platform_tenant_id: str


@dataclass
class IdentityClient:
    """Agent-friendly wrapper for identity-service APIs."""

    base_url: str = field(default_factory=lambda: os.getenv("SOORMA_IDENTITY_URL", "http://localhost:8085"))
    _client: Optional[IdentityServiceClient] = field(default=None, repr=False, init=False)
    _bound_event_identity: contextvars.ContextVar[Optional[IdentityContextMetadata]] = field(
        default_factory=lambda: contextvars.ContextVar(
            "soorma_identity_bound_event_identity",
            default=None,
        ),
        init=False,
        repr=False,
    )

    async def _ensure_client(self) -> IdentityServiceClient:
        """Lazy initialize low-level identity client."""
        if self._client is None:
            self._client = IdentityServiceClient(base_url=self.base_url)
        return self._client

    def bind_event_metadata(self, event: Any) -> contextvars.Token:
        """Bind event platform identity for optional wrapper defaults."""
        return self._bound_event_identity.set(
            {
                "platform_tenant_id": str(getattr(event, "platform_tenant_id", "") or "").strip(),
            }
        )

    def reset_event_metadata(self, token: contextvars.Token) -> None:
        """Reset previously bound identity metadata."""
        self._bound_event_identity.reset(token)

    def _resolve_platform_tenant_id(
        self,
        platform_tenant_id: Optional[str],
    ) -> Optional[str]:
        """Resolve platform tenant scope from explicit args or bound event metadata."""
        metadata = self._bound_event_identity.get()
        raw_platform_tenant_id = (
            platform_tenant_id
            if platform_tenant_id is not None
            else (metadata or {}).get("platform_tenant_id")
        )
        resolved_platform_tenant_id = (
            str(raw_platform_tenant_id).strip()
            if raw_platform_tenant_id is not None
            else None
        )
        return resolved_platform_tenant_id or None

    def _require_platform_tenant_id(self, platform_tenant_id: Optional[str]) -> str:
        """Require a non-blank platform tenant scope for tenant admin operations."""
        resolved_platform_tenant_id = self._resolve_platform_tenant_id(platform_tenant_id)
        if not resolved_platform_tenant_id:
            raise ValueError("platform_tenant_id is required for tenant admin operations")
        return resolved_platform_tenant_id

    async def onboard_tenant(
        self,
        payload: OnboardingRequest,
        superuser_api_key: Optional[str] = None,
    ) -> OnboardingResponse:
        """Onboard tenant identity domain."""
        client = await self._ensure_client()
        return await client.onboard_tenant(payload, superuser_api_key=superuser_api_key)

    async def issue_token(
        self,
        payload: TokenIssueRequest,
        platform_tenant_id: Optional[str] = None,
        tenant_admin_api_key: Optional[str] = None,
    ) -> TokenIssueResponse:
        """Issue token under platform/delegated policy."""
        client = await self._ensure_client()
        resolved_platform_tenant_id = self._require_platform_tenant_id(platform_tenant_id)
        return await client.issue_token(
            payload,
            platform_tenant_id=resolved_platform_tenant_id,
            tenant_admin_api_key=tenant_admin_api_key,
        )

    async def create_principal(
        self,
        payload: PrincipalRequest,
        platform_tenant_id: Optional[str] = None,
        tenant_admin_api_key: Optional[str] = None,
    ) -> PrincipalResponse:
        """Create principal via identity-service."""
        client = await self._ensure_client()
        resolved_platform_tenant_id = self._require_platform_tenant_id(platform_tenant_id)
        return await client.create_principal(
            payload,
            platform_tenant_id=resolved_platform_tenant_id,
            tenant_admin_api_key=tenant_admin_api_key,
        )

    async def update_principal(
        self,
        principal_id: str,
        payload: PrincipalRequest,
        platform_tenant_id: Optional[str] = None,
        tenant_admin_api_key: Optional[str] = None,
    ) -> PrincipalResponse:
        """Update principal via identity-service."""
        client = await self._ensure_client()
        resolved_platform_tenant_id = self._require_platform_tenant_id(platform_tenant_id)
        return await client.update_principal(
            principal_id,
            payload,
            platform_tenant_id=resolved_platform_tenant_id,
            tenant_admin_api_key=tenant_admin_api_key,
        )

    async def revoke_principal(
        self,
        principal_id: str,
        platform_tenant_id: Optional[str] = None,
        tenant_admin_api_key: Optional[str] = None,
    ) -> PrincipalResponse:
        """Revoke principal via identity-service."""
        client = await self._ensure_client()
        resolved_platform_tenant_id = self._require_platform_tenant_id(platform_tenant_id)
        return await client.revoke_principal(
            principal_id,
            platform_tenant_id=resolved_platform_tenant_id,
            tenant_admin_api_key=tenant_admin_api_key,
        )

    async def register_delegated_issuer(
        self,
        payload: DelegatedIssuerRequest,
        platform_tenant_id: Optional[str] = None,
        tenant_admin_api_key: Optional[str] = None,
    ) -> DelegatedIssuerResponse:
        """Register delegated issuer trust metadata."""
        client = await self._ensure_client()
        resolved_platform_tenant_id = self._require_platform_tenant_id(platform_tenant_id)
        return await client.register_delegated_issuer(
            payload,
            platform_tenant_id=resolved_platform_tenant_id,
            tenant_admin_api_key=tenant_admin_api_key,
        )

    async def update_delegated_issuer(
        self,
        delegated_issuer_id: str,
        payload: DelegatedIssuerRequest,
        platform_tenant_id: Optional[str] = None,
        tenant_admin_api_key: Optional[str] = None,
    ) -> DelegatedIssuerResponse:
        """Update delegated issuer via identity-service."""
        client = await self._ensure_client()
        resolved_platform_tenant_id = self._require_platform_tenant_id(platform_tenant_id)
        return await client.update_delegated_issuer(
            delegated_issuer_id,
            payload,
            platform_tenant_id=resolved_platform_tenant_id,
            tenant_admin_api_key=tenant_admin_api_key,
        )

    async def evaluate_mapping(
        self,
        payload: MappingEvaluationRequest,
        platform_tenant_id: Optional[str] = None,
        tenant_admin_api_key: Optional[str] = None,
    ) -> MappingEvaluationResponse:
        """Evaluate identity mapping and collision policy."""
        client = await self._ensure_client()
        resolved_platform_tenant_id = self._require_platform_tenant_id(platform_tenant_id)
        return await client.evaluate_mapping(
            payload,
            platform_tenant_id=resolved_platform_tenant_id,
            tenant_admin_api_key=tenant_admin_api_key,
        )

    async def close(self) -> None:
        """Close low-level client if initialized."""
        if self._client:
            await self._client.close()
            self._client = None
