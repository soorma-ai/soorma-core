"""Helpers for scoped identity-service admin API keys."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from identity_service.core.config import settings
from identity_service.crud.admin_credentials import tenant_admin_credential_repository
from soorma_common.models import TenantAdminCredentialRotateResponse


class TenantAdminApiKeyService:
    """Issue, validate, and rotate persisted tenant-bound admin API keys."""

    def __init__(self, secret: str, *, prefix: str = "idadm"):
        self._secret = secret.encode("utf-8")
        self._prefix = prefix

    def _new_credential_id(self) -> str:
        """Create a new opaque credential identifier."""
        return f"tak_{uuid4().hex}"

    def _new_secret(self) -> str:
        """Create a new high-entropy tenant admin secret."""
        return secrets.token_urlsafe(32)

    def _hash_secret_value(self, secret_value: str) -> str:
        """Hash a secret value using a server-side pepper for at-rest protection."""
        normalized_secret_value = str(secret_value or "").strip()
        if not normalized_secret_value:
            raise ValueError("secret_value is required")
        return hmac.new(
            self._secret,
            normalized_secret_value.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    def _build_api_key(self, credential_id: str, secret_value: str) -> str:
        """Construct the opaque credential presented to clients."""
        return f"{self._prefix}.{credential_id}.{secret_value}"

    def _parse_api_key(self, provided_api_key: str | None) -> tuple[str, str] | None:
        """Extract credential id and secret from a presented API key."""
        normalized_provided_api_key = str(provided_api_key or "").strip()
        if not normalized_provided_api_key:
            return None
        prefix, separator, remainder = normalized_provided_api_key.partition(".")
        if separator == "" or prefix != self._prefix:
            return None
        credential_id, separator, secret_value = remainder.partition(".")
        if separator == "" or not credential_id or not secret_value:
            return None
        return credential_id, secret_value

    async def issue_api_key(
        self,
        db: AsyncSession,
        platform_tenant_id: str,
        *,
        actor_id: str,
        revoke_existing: bool = False,
        commit: bool = True,
    ) -> TenantAdminCredentialRotateResponse:
        """Persist and return a newly minted tenant admin API credential."""
        normalized_platform_tenant_id = str(platform_tenant_id or "").strip()
        if not normalized_platform_tenant_id:
            raise ValueError("platform_tenant_id is required")

        if revoke_existing:
            await tenant_admin_credential_repository.revoke_active_credentials(
                db,
                normalized_platform_tenant_id,
                commit=False,
            )

        credential_id = self._new_credential_id()
        secret_value = self._new_secret()
        await tenant_admin_credential_repository.create_credential(
            db,
            {
                "credential_id": credential_id,
                "platform_tenant_id": normalized_platform_tenant_id,
                "secret_hash": self._hash_secret_value(secret_value),
                "status": "active",
                "created_by": actor_id,
            },
            commit=commit,
        )
        return TenantAdminCredentialRotateResponse(
            credential_id=credential_id,
            tenant_admin_api_key=self._build_api_key(credential_id, secret_value),
            status="rotated" if revoke_existing else "active",
        )

    async def validate_api_key(
        self,
        db: AsyncSession,
        platform_tenant_id: str,
        provided_api_key: str | None,
    ) -> bool:
        """Return whether the supplied admin API key matches an active stored credential."""
        normalized_platform_tenant_id = str(platform_tenant_id or "").strip()
        if not normalized_platform_tenant_id:
            return False

        parsed_api_key = self._parse_api_key(provided_api_key)
        if parsed_api_key is None:
            return False
        credential_id, secret_value = parsed_api_key

        credential = await tenant_admin_credential_repository.get_active_credential(
            db,
            credential_id,
            normalized_platform_tenant_id,
        )
        if credential is None:
            return False

        expected_secret_hash = str(credential["secret_hash"])
        provided_secret_hash = self._hash_secret_value(secret_value)
        return hmac.compare_digest(provided_secret_hash, expected_secret_hash)

    async def rotate_api_key(
        self,
        db: AsyncSession,
        platform_tenant_id: str,
        *,
        actor_id: str,
    ) -> TenantAdminCredentialRotateResponse:
        """Rotate the tenant admin API key, revoking existing active credentials."""
        return await self.issue_api_key(
            db,
            platform_tenant_id,
            actor_id=actor_id,
            revoke_existing=True,
        )


tenant_admin_api_key_service = TenantAdminApiKeyService(
    settings.identity_tenant_admin_api_key_secret,
)

