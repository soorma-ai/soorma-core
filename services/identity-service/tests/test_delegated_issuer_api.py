"""Delegated issuer service behavior tests."""

import pytest
from soorma_common.models import DelegatedIssuerRequest, OnboardingRequest

from identity_service.services.onboarding_service import onboarding_service
from identity_service.services.delegated_trust_service import delegated_trust_service


@pytest.mark.asyncio
async def test_register_delegated_issuer_returns_active_status(db_session):
    """Registering delegated issuer should return active status."""
    await onboarding_service.onboard_tenant(
        db_session,
        OnboardingRequest(
            tenant_domain_id="td-acme",
            platform_tenant_id="pt-acme",
            bootstrap_admin_principal_id="principal-admin",
            created_by="system",
        ),
    )

    request = DelegatedIssuerRequest(
        delegated_issuer_id="issuer-1",
        tenant_domain_id="td-acme",
        issuer_id="https://issuer.acme",
        jwk_set_ref_or_material="https://issuer.acme/.well-known/jwks.json",
        audience_policy_ref="aud-default",
        claim_mapping_policy_ref="cmp-default",
        created_by="admin-1",
    )

    response = await delegated_trust_service.register_issuer(db_session, request)

    assert response.delegated_issuer_id == "issuer-1"
    assert response.issuer_id == "https://issuer.acme"
    assert response.status == "active"

    assert await delegated_trust_service.is_trusted(db_session, "issuer-1")
