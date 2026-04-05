"""Provider facade token tests."""

import pytest

from identity_service.services.provider_facade import provider_facade


@pytest.mark.asyncio
async def test_issue_signed_token_and_validate_roundtrip():
    """Provider facade should issue and validate a token for the same issuer."""
    token = await provider_facade.issue_signed_token(
        {
            "tenant_domain_id": "td-acme",
            "principal_id": "principal-1",
            "iss": "issuer-a",
        }
    )
    assert token

    assert await provider_facade.validate_delegated_assertion("issuer-a", token)
    assert not await provider_facade.validate_delegated_assertion("issuer-b", token)


@pytest.mark.asyncio
async def test_validate_delegated_assertion_rejects_bad_token():
    """Facade should reject malformed delegated assertions."""
    assert not await provider_facade.validate_delegated_assertion("issuer-a", "bad.token.value")
