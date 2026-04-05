"""Mapping service behavior tests."""

import pytest
from soorma_common.models import MappingEvaluationRequest, OnboardingRequest, PrincipalRequest

from identity_service.services.onboarding_service import onboarding_service
from identity_service.services.principal_service import principal_service
from identity_service.services.mapping_service import mapping_service


@pytest.mark.asyncio
async def test_mapping_collision_without_override_is_denied(db_session):
    """Collision should be denied when override is not requested."""
    await onboarding_service.onboard_tenant(
        db_session,
        OnboardingRequest(
            tenant_domain_id="td-acme",
            platform_tenant_id="pt-acme",
            bootstrap_admin_principal_id="principal-admin",
            created_by="system",
        ),
    )
    await principal_service.create_principal(
        db_session,
        PrincipalRequest(
            principal_id="principal-2",
            tenant_domain_id="td-acme",
            principal_type="developer",
            lifecycle_state="active",
        ),
    )

    initial_request = MappingEvaluationRequest(
        tenant_domain_id="td-acme",
        source_issuer_id="issuer-1",
        external_identity_key="ext-123",
        canonical_identity_key="canonical-456",
        principal_id="principal-admin",
        override_requested=False,
    )
    initial_response = await mapping_service.evaluate_mapping(db_session, initial_request)
    assert initial_response.decision == "allow"

    request = MappingEvaluationRequest(
        tenant_domain_id="td-acme",
        source_issuer_id="issuer-1",
        external_identity_key="ext-123",
        canonical_identity_key="canonical-456",
        principal_id="principal-2",
        override_requested=False,
    )

    response = await mapping_service.evaluate_mapping(db_session, request)

    assert response.decision == "deny"
    assert response.reason_code == "collision_no_override"

    override = MappingEvaluationRequest(
        tenant_domain_id="td-acme",
        source_issuer_id="issuer-1",
        external_identity_key="ext-123",
        canonical_identity_key="canonical-789",
        principal_id="principal-2",
        override_requested=True,
    )
    override_response = await mapping_service.evaluate_mapping(db_session, override)
    assert override_response.decision == "deny"
    assert override_response.reason_code == "override_admin_required"

    admin_override = MappingEvaluationRequest(
        tenant_domain_id="td-acme",
        source_issuer_id="issuer-1",
        external_identity_key="ext-123",
        canonical_identity_key="canonical-789",
        principal_id="principal-admin",
        override_requested=True,
    )
    admin_override_response = await mapping_service.evaluate_mapping(db_session, admin_override)
    assert admin_override_response.decision == "allow"
    assert admin_override_response.reason_code == "override_accepted"
