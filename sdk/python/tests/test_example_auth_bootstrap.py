"""Tests for shared example JWT bootstrap persistence helpers."""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from soorma_common.models import OnboardingResponse, TokenIssueResponse


EXAMPLE_NAME = "01-hello-world"
SHARED_AUTH_PATH = Path(__file__).resolve().parents[3] / "examples" / "shared" / "auth.py"


@pytest.fixture
def shared_auth_module():
    """Load the shared example auth helper as a module for direct testing."""
    import importlib.util

    spec = importlib.util.spec_from_file_location("example_shared_auth", SHARED_AUTH_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.mark.asyncio
async def test_ensure_example_auth_token_bootstraps_once_and_persists(shared_auth_module, tmp_path, monkeypatch):
    """Helper should persist onboarding metadata and reuse a cached provider token."""
    repo_root = tmp_path / "repo"
    examples_dir = repo_root / "examples" / "01-hello-world"
    sdk_dir = repo_root / "sdk"
    examples_dir.mkdir(parents=True)
    sdk_dir.mkdir(parents=True)
    script_path = examples_dir / "worker.py"
    script_path.write_text("# placeholder\n")

    mock_identity_client = AsyncMock()
    mock_identity_client.onboard_tenant = AsyncMock(
        return_value=OnboardingResponse(
            tenant_domain_id="td-1",
            platform_tenant_id="pt-1",
            bootstrap_admin_principal_id="pr-1",
            status="created",
        )
    )
    mock_identity_client.issue_token = AsyncMock(
        return_value=TokenIssueResponse(token="jwt-token", token_type="Bearer")
    )
    mock_identity_client.set_platform_tenant_id = MagicMock()
    mock_identity_client.__aenter__.return_value = mock_identity_client
    mock_identity_client.__aexit__.return_value = None

    with patch.object(shared_auth_module, "IdentityServiceClient", return_value=mock_identity_client), patch.object(
        shared_auth_module.jwt,
        "decode",
        return_value={"exp": 4102444800},
    ):
        token = await shared_auth_module.ensure_example_auth_token(EXAMPLE_NAME, script_path)
        second_token = await shared_auth_module.ensure_example_auth_token(EXAMPLE_NAME, script_path)

    assert token == "jwt-token"
    assert second_token == "jwt-token"
    assert mock_identity_client.onboard_tenant.await_count == 1
    assert mock_identity_client.issue_token.await_count == 2
    mock_identity_client.set_platform_tenant_id.assert_called_with("pt-1")

    bootstrap_file = repo_root / ".soorma" / shared_auth_module.bootstrap_filename(EXAMPLE_NAME)
    payload = json.loads(bootstrap_file.read_text())
    assert payload["platform_tenant_id"] == "pt-1"
    assert payload["bootstrap_admin_principal_id"] == "pr-1"
    assert shared_auth_module.os.environ["SOORMA_AUTH_TOKEN"] == "jwt-token"
    assert shared_auth_module.os.environ["SOORMA_PLATFORM_TENANT_ID"] == "pt-1"


@pytest.mark.asyncio
async def test_build_example_token_provider_refreshes_when_cached_token_is_expired(
    shared_auth_module, tmp_path
):
    """Provider should refresh cached JWTs once they are past the refresh window."""
    repo_root = tmp_path / "repo"
    examples_dir = repo_root / "examples" / "01-hello-world"
    sdk_dir = repo_root / "sdk"
    examples_dir.mkdir(parents=True)
    sdk_dir.mkdir(parents=True)
    script_path = examples_dir / "worker.py"
    script_path.write_text("# placeholder\n")

    mock_identity_client = AsyncMock()
    mock_identity_client.onboard_tenant = AsyncMock(
        return_value=OnboardingResponse(
            tenant_domain_id="td-1",
            platform_tenant_id="pt-1",
            bootstrap_admin_principal_id="pr-1",
            status="created",
        )
    )
    mock_identity_client.issue_token = AsyncMock(
        side_effect=[
            TokenIssueResponse(token="fresh-token-1", token_type="Bearer"),
            TokenIssueResponse(token="fresh-token", token_type="Bearer"),
        ]
    )
    mock_identity_client.set_platform_tenant_id = MagicMock()
    mock_identity_client.__aenter__.return_value = mock_identity_client
    mock_identity_client.__aexit__.return_value = None

    provider = shared_auth_module.build_example_token_provider(EXAMPLE_NAME, script_path)
    provider._cached_token = "expired-token"

    with patch.object(shared_auth_module, "IdentityServiceClient", return_value=mock_identity_client), patch.object(
        shared_auth_module.jwt,
        "decode",
        side_effect=[{"exp": 1}, {"exp": 4102444800}],
    ):
        token = await provider.get_token()
        refreshed_token = await provider.get_token(force_refresh=True)

    assert token == "fresh-token-1"
    assert refreshed_token == "fresh-token"
    assert mock_identity_client.onboard_tenant.await_count == 1
    assert mock_identity_client.issue_token.await_count == 2
    mock_identity_client.set_platform_tenant_id.assert_called_with("pt-1")


@pytest.mark.asyncio
async def test_build_example_token_provider_exposes_bootstrapped_ids(shared_auth_module, tmp_path):
    """Provider should expose bootstrapped tenant and principal identifiers."""
    repo_root = tmp_path / "repo"
    examples_dir = repo_root / "examples" / "01-hello-world"
    sdk_dir = repo_root / "sdk"
    examples_dir.mkdir(parents=True)
    sdk_dir.mkdir(parents=True)
    script_path = examples_dir / "worker.py"
    script_path.write_text("# placeholder\n")

    provider = shared_auth_module.build_example_token_provider(EXAMPLE_NAME, script_path)
    shared_auth_module.persist_bootstrap_payload(
        EXAMPLE_NAME,
        script_path,
        {
            "tenant_domain_id": "td-1",
            "platform_tenant_id": "pt-1",
            "bootstrap_admin_principal_id": "pr-1",
        },
    )

    assert await provider.get_platform_tenant_id() == "pt-1"
    assert await provider.get_bootstrap_admin_principal_id() == "pr-1"


def test_load_bootstrap_payload_returns_none_for_invalid_json(shared_auth_module, tmp_path):
    """Invalid persisted bootstrap payload should be ignored and regenerated."""
    repo_root = tmp_path / "repo"
    examples_dir = repo_root / "examples" / "01-hello-world"
    sdk_dir = repo_root / "sdk"
    examples_dir.mkdir(parents=True)
    sdk_dir.mkdir(parents=True)
    script_path = examples_dir / "worker.py"
    script_path.write_text("# placeholder\n")
    bootstrap_file = repo_root / ".soorma" / shared_auth_module.bootstrap_filename(EXAMPLE_NAME)
    bootstrap_file.parent.mkdir(parents=True)
    bootstrap_file.write_text("{invalid-json")

    assert shared_auth_module.load_bootstrap_payload(EXAMPLE_NAME, script_path) is None