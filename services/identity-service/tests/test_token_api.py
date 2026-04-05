"""Token service behavior tests."""

import pytest
from soorma_common.models import (
    DelegatedIssuerRequest,
    OnboardingRequest,
    TokenIssueRequest,
)

from identity_service.services.delegated_trust_service import delegated_trust_service
from identity_service.services.onboarding_service import onboarding_service
from identity_service.services.token_service import token_service


@pytest.mark.asyncio
async def test_platform_token_issuance_returns_bearer_token(db_session):
    """Platform issuance should return a bearer token payload."""
    await onboarding_service.onboard_tenant(
        db_session,
        OnboardingRequest(
            tenant_domain_id="td-acme",
            platform_tenant_id="pt-acme",
            bootstrap_admin_principal_id="principal-1",
            created_by="system",
        ),
    )

    request = TokenIssueRequest(
        tenant_domain_id="td-acme",
        principal_id="principal-1",
        issuance_type="platform",
    )

    response = await token_service.issue_token(db_session, request)

    assert isinstance(response.token, str)
    assert response.token
    assert response.token_type == "Bearer"


@pytest.mark.asyncio
async def test_delegated_issuance_denied_when_issuer_not_trusted(db_session):
    """Delegated issuance should fail closed without trusted issuer context."""
    await onboarding_service.onboard_tenant(
        db_session,
        OnboardingRequest(
            tenant_domain_id="td-acme",
            platform_tenant_id="pt-acme",
            bootstrap_admin_principal_id="principal-1",
            created_by="system",
        ),
    )

    request = TokenIssueRequest(
        tenant_domain_id="td-acme",
        principal_id="principal-1",
        issuance_type="delegated",
        delegated_issuer_id="issuer-unknown",
    )

    with pytest.raises(PermissionError, match="delegated issuer is not trusted"):
        await token_service.issue_token(db_session, request)


@pytest.mark.asyncio
async def test_delegated_issuance_allowed_when_issuer_trusted(db_session):
    """Delegated issuance should return token when issuer trust exists."""
    await onboarding_service.onboard_tenant(
        db_session,
        OnboardingRequest(
            tenant_domain_id="td-acme",
            platform_tenant_id="pt-acme",
            bootstrap_admin_principal_id="principal-1",
            created_by="system",
        ),
    )
    await delegated_trust_service.register_issuer(
        db_session,
        DelegatedIssuerRequest(
            delegated_issuer_id="issuer-1",
            tenant_domain_id="td-acme",
            issuer_id="soorma-identity-service",
            jwk_set_ref_or_material="https://issuer.example/jwks.json",
            audience_policy_ref="aud-default",
            claim_mapping_policy_ref="claim-default",
            created_by="admin-1",
        ),
    )

    response = await token_service.issue_token(
        db_session,
        TokenIssueRequest(
            tenant_domain_id="td-acme",
            principal_id="principal-1",
            issuance_type="delegated",
            delegated_issuer_id="issuer-1",
        ),
    )
    assert response.token_type == "Bearer"
    assert response.token
