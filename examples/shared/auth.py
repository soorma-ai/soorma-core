"""Reusable identity bootstrap and JWT provider helpers for examples."""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Optional

import jwt

from soorma.identity.client import IdentityServiceClient
from soorma_common.models import OnboardingRequest, TokenIssueRequest, TokenIssuanceType


DEFAULT_PLATFORM_TENANT_ID = "00000000-0000-0000-0000-000000000000"
DEFAULT_SERVICE_USER_ID = "00000000-0000-0000-0000-000000000001"
TOKEN_REFRESH_WINDOW_SECONDS = 30


def bootstrap_filename(example_name: str) -> str:
    """Return the persisted bootstrap filename for an example."""
    return f"{example_name}-identity.json"


def _find_repo_root(start_path: Path) -> Path:
    """Find repository root by walking parents until examples/ and sdk/ are present."""
    resolved_path = start_path.resolve()
    search_roots = [resolved_path, *resolved_path.parents]
    for candidate in search_roots:
        if (candidate / "examples").exists() and (candidate / "sdk").exists():
            return candidate
    raise RuntimeError("Unable to locate soorma-core repository root from example path")


def _get_soorma_dir(start_path: Path) -> Path:
    """Return the shared .soorma directory used by example helpers."""
    repo_root = _find_repo_root(start_path)
    soorma_dir = repo_root / ".soorma"
    soorma_dir.mkdir(exist_ok=True)
    return soorma_dir


def bootstrap_file_path(example_name: str, start_path: Path) -> Path:
    """Return persisted bootstrap metadata path for an example."""
    return _get_soorma_dir(start_path) / bootstrap_filename(example_name)


def load_bootstrap_payload(example_name: str, start_path: Path) -> dict[str, Any] | None:
    """Load persisted bootstrap payload when available and structurally valid."""
    bootstrap_file = bootstrap_file_path(example_name, start_path)
    if not bootstrap_file.exists():
        return None
    try:
        payload = json.loads(bootstrap_file.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    required_keys = {"platform_tenant_id", "bootstrap_admin_principal_id", "tenant_domain_id"}
    if not required_keys.issubset(payload):
        return None
    return payload


def persist_bootstrap_payload(example_name: str, start_path: Path, payload: dict[str, Any]) -> None:
    """Persist example bootstrap payload for reuse across runs."""
    bootstrap_file = bootstrap_file_path(example_name, start_path)
    bootstrap_file.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")


def _is_token_fresh(token: str) -> bool:
    """Return whether the cached JWT remains valid beyond the refresh window."""
    try:
        payload = jwt.decode(token, options={"verify_signature": False, "verify_exp": False})
    except jwt.PyJWTError:
        return False

    exp = payload.get("exp")
    if exp is None:
        return True

    try:
        expires_at = int(exp)
    except (TypeError, ValueError):
        return False

    return expires_at - TOKEN_REFRESH_WINDOW_SECONDS > int(time.time())


class ExampleTokenProvider:
    """Trusted-proxy style token provider for local examples."""

    def __init__(self, example_name: str, start_path: Path | str):
        self.example_name = example_name
        self.start_path = Path(start_path).resolve()
        self._cached_token: Optional[str] = None
        self._bootstrap_payload: Optional[dict[str, Any]] = None

    async def __call__(self) -> str:
        """Return a cached JWT or request a new one when needed."""
        return await self.get_token()

    async def get_token(self, force_refresh: bool = False) -> str:
        """Return a valid JWT, bootstrapping and refreshing as needed."""
        if not force_refresh and self._cached_token and _is_token_fresh(self._cached_token):
            self._export_environment(self._cached_token)
            return self._cached_token

        bootstrap_payload = await self._ensure_bootstrap_payload()
        async with IdentityServiceClient() as identity_client:
            token_response = await identity_client.issue_token(
                TokenIssueRequest(
                    principal_id=str(bootstrap_payload["bootstrap_admin_principal_id"]),
                    issuance_type=TokenIssuanceType.PLATFORM,
                ),
                service_tenant_id=DEFAULT_PLATFORM_TENANT_ID,
                service_user_id=DEFAULT_SERVICE_USER_ID,
            )

        self._cached_token = token_response.token
        self._export_environment(token_response.token)
        return token_response.token

    async def _ensure_bootstrap_payload(self) -> dict[str, Any]:
        """Load or create the persisted example principal bootstrap payload."""
        if self._bootstrap_payload is not None:
            return self._bootstrap_payload

        persisted_payload = load_bootstrap_payload(self.example_name, self.start_path)
        if persisted_payload is None:
            async with IdentityServiceClient() as identity_client:
                onboarding_response = await identity_client.onboard_tenant(
                    OnboardingRequest(
                        bootstrap_admin_external_ref=f"{self.example_name}-bootstrap-admin"
                    ),
                    service_tenant_id=DEFAULT_PLATFORM_TENANT_ID,
                    service_user_id=DEFAULT_SERVICE_USER_ID,
                )
            persisted_payload = onboarding_response.model_dump()
            persist_bootstrap_payload(self.example_name, self.start_path, persisted_payload)

        self._bootstrap_payload = persisted_payload
        return persisted_payload

    def _export_environment(self, token: str) -> None:
        """Export current example auth context for subprocess compatibility."""
        if self._bootstrap_payload is None:
            return
        os.environ["SOORMA_AUTH_TOKEN"] = token
        os.environ["SOORMA_PLATFORM_TENANT_ID"] = str(self._bootstrap_payload["platform_tenant_id"])
        os.environ["SOORMA_DEVELOPER_TENANT_ID"] = str(self._bootstrap_payload["platform_tenant_id"])


def build_example_token_provider(example_name: str, start_path: Path | str) -> ExampleTokenProvider:
    """Create a reusable token provider for an example."""
    return ExampleTokenProvider(example_name=example_name, start_path=start_path)


async def ensure_example_auth_token(example_name: str, start_path: Path | str) -> str:
    """Convenience helper for eagerly provisioning a valid example JWT."""
    provider = build_example_token_provider(example_name=example_name, start_path=start_path)
    return await provider.get_token()


async def _main(argv: list[str]) -> int:
    """CLI entry point for priming example bootstrap and token state."""
    if len(argv) != 3:
        print("Usage: python -m examples.shared.auth <example-name> <example-path>", file=sys.stderr)
        return 2

    await ensure_example_auth_token(example_name=argv[1], start_path=argv[2])
    return 0


if __name__ == "__main__":
    import asyncio

    raise SystemExit(asyncio.run(_main(sys.argv)))