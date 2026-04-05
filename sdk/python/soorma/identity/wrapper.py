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

    tenant_id: str
    user_id: str


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
        """Bind event identity for implicit wrapper defaults."""
        return self._bound_event_identity.set(
            {
                "tenant_id": event.tenant_id,
                "user_id": event.user_id,
            }
        )

    def reset_event_metadata(self, token: contextvars.Token) -> None:
        """Reset previously bound identity metadata."""
        self._bound_event_identity.reset(token)

    def _resolve_identity(
        self,
        tenant_id: Optional[str],
        user_id: Optional[str],
    ) -> tuple[str, str]:
        """Resolve identity from explicit args or bound event metadata."""
        metadata = self._bound_event_identity.get()
        resolved_tenant_id = tenant_id if tenant_id is not None else (metadata or {}).get("tenant_id")
        resolved_user_id = user_id if user_id is not None else (metadata or {}).get("user_id")
        if not resolved_tenant_id or not resolved_user_id:
            raise ValueError("tenant_id and user_id are required (get from event context)")
        return resolved_tenant_id, resolved_user_id

    async def onboard_tenant(
        self,
        payload: OnboardingRequest,
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> OnboardingResponse:
        """Onboard tenant identity domain."""
        client = await self._ensure_client()
        resolved_tenant_id, resolved_user_id = self._resolve_identity(tenant_id, user_id)
        return await client.onboard_tenant(
            payload,
            service_tenant_id=resolved_tenant_id,
            service_user_id=resolved_user_id,
        )

    async def issue_token(
        self,
        payload: TokenIssueRequest,
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> TokenIssueResponse:
        """Issue token under platform/delegated policy."""
        client = await self._ensure_client()
        resolved_tenant_id, resolved_user_id = self._resolve_identity(tenant_id, user_id)
        return await client.issue_token(
            payload,
            service_tenant_id=resolved_tenant_id,
            service_user_id=resolved_user_id,
        )

    async def create_principal(
        self,
        payload: PrincipalRequest,
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> PrincipalResponse:
        """Create principal via identity-service."""
        client = await self._ensure_client()
        resolved_tenant_id, resolved_user_id = self._resolve_identity(tenant_id, user_id)
        return await client.create_principal(
            payload,
            service_tenant_id=resolved_tenant_id,
            service_user_id=resolved_user_id,
        )

    async def update_principal(
        self,
        principal_id: str,
        payload: PrincipalRequest,
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> PrincipalResponse:
        """Update principal via identity-service."""
        client = await self._ensure_client()
        resolved_tenant_id, resolved_user_id = self._resolve_identity(tenant_id, user_id)
        return await client.update_principal(
            principal_id,
            payload,
            service_tenant_id=resolved_tenant_id,
            service_user_id=resolved_user_id,
        )

    async def revoke_principal(
        self,
        principal_id: str,
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> PrincipalResponse:
        """Revoke principal via identity-service."""
        client = await self._ensure_client()
        resolved_tenant_id, resolved_user_id = self._resolve_identity(tenant_id, user_id)
        return await client.revoke_principal(
            principal_id,
            service_tenant_id=resolved_tenant_id,
            service_user_id=resolved_user_id,
        )

    async def register_delegated_issuer(
        self,
        payload: DelegatedIssuerRequest,
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> DelegatedIssuerResponse:
        """Register delegated issuer trust metadata."""
        client = await self._ensure_client()
        resolved_tenant_id, resolved_user_id = self._resolve_identity(tenant_id, user_id)
        return await client.register_delegated_issuer(
            payload,
            service_tenant_id=resolved_tenant_id,
            service_user_id=resolved_user_id,
        )

    async def update_delegated_issuer(
        self,
        delegated_issuer_id: str,
        payload: DelegatedIssuerRequest,
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> DelegatedIssuerResponse:
        """Update delegated issuer via identity-service."""
        client = await self._ensure_client()
        resolved_tenant_id, resolved_user_id = self._resolve_identity(tenant_id, user_id)
        return await client.update_delegated_issuer(
            delegated_issuer_id,
            payload,
            service_tenant_id=resolved_tenant_id,
            service_user_id=resolved_user_id,
        )

    async def evaluate_mapping(
        self,
        payload: MappingEvaluationRequest,
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> MappingEvaluationResponse:
        """Evaluate identity mapping and collision policy."""
        client = await self._ensure_client()
        resolved_tenant_id, resolved_user_id = self._resolve_identity(tenant_id, user_id)
        return await client.evaluate_mapping(
            payload,
            service_tenant_id=resolved_tenant_id,
            service_user_id=resolved_user_id,
        )

    async def close(self) -> None:
        """Close low-level client if initialized."""
        if self._client:
            await self._client.close()
            self._client = None
