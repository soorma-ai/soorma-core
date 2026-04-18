"""Helpers for scoped identity-service admin API keys."""

from __future__ import annotations

import base64
import hashlib
import hmac
import os


class TenantAdminApiKeyService:
    """Issue and validate tenant-bound identity admin API keys."""

    def __init__(self, secret: str, *, prefix: str = "idadm"):
        self._secret = secret.encode("utf-8")
        self._prefix = prefix

    def issue_api_key(self, platform_tenant_id: str) -> str:
        """Generate a deterministic tenant-bound admin API key."""
        normalized_platform_tenant_id = str(platform_tenant_id or "").strip()
        if not normalized_platform_tenant_id:
            raise ValueError("platform_tenant_id is required")

        digest = hmac.new(
            self._secret,
            normalized_platform_tenant_id.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        signature = base64.urlsafe_b64encode(digest).decode("utf-8").rstrip("=")
        return f"{self._prefix}_{normalized_platform_tenant_id}_{signature}"

    def validate_api_key(self, platform_tenant_id: str, provided_api_key: str | None) -> bool:
        """Return whether the supplied admin API key matches the tenant binding."""
        normalized_provided_api_key = str(provided_api_key or "").strip()
        if not normalized_provided_api_key:
            return False
        expected_api_key = self.issue_api_key(platform_tenant_id)
        return hmac.compare_digest(normalized_provided_api_key, expected_api_key)


tenant_admin_api_key_service = TenantAdminApiKeyService(
    os.environ.get(
        "IDENTITY_TENANT_ADMIN_API_KEY_SECRET",
        os.environ.get(
            "IDENTITY_SUPERUSER_API_KEY",
            os.environ.get("IDENTITY_ADMIN_API_KEY", "dev-identity-admin"),
        ),
    )
)
