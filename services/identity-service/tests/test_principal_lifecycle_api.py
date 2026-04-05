"""Principal lifecycle service behavior tests."""

import pytest
from soorma_common.models import PrincipalRequest
from soorma_common.models import OnboardingRequest

from identity_service.services.onboarding_service import onboarding_service
from identity_service.services.principal_service import principal_service


@pytest.mark.asyncio
async def test_create_principal_returns_active_lifecycle(db_session):
    """Principal creation should return the principal in active state."""
    onboarding = await onboarding_service.onboard_tenant(
        db_session,
        OnboardingRequest(),
        actor_id="system",
    )

    request = PrincipalRequest(
        tenant_domain_id=onboarding.tenant_domain_id,
        principal_type="developer",
        lifecycle_state="active",
        external_ref="dev-1@example.com",
    )

    response = await principal_service.create_principal(db_session, request)

    assert response.principal_id.startswith("pr_")
    assert response.tenant_domain_id == onboarding.tenant_domain_id
    assert response.lifecycle_state == "active"

    revoked = await principal_service.revoke_principal(db_session, response.principal_id)
    assert revoked.lifecycle_state == "revoked"
