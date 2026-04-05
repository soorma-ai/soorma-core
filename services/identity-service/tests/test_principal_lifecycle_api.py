"""Principal lifecycle service behavior tests."""

import pytest
from soorma_common.models import PrincipalRequest
from soorma_common.models import OnboardingRequest

from identity_service.services.onboarding_service import onboarding_service
from identity_service.services.principal_service import principal_service


@pytest.mark.asyncio
async def test_create_principal_returns_active_lifecycle(db_session):
    """Principal creation should return the principal in active state."""
    await onboarding_service.onboard_tenant(
        db_session,
        OnboardingRequest(
            tenant_domain_id="td-acme",
            platform_tenant_id="pt-acme",
            bootstrap_admin_principal_id="principal-admin",
            created_by="system",
        ),
    )

    request = PrincipalRequest(
        principal_id="principal-1",
        tenant_domain_id="td-acme",
        principal_type="developer",
        lifecycle_state="active",
    )

    response = await principal_service.create_principal(db_session, request)

    assert response.principal_id == "principal-1"
    assert response.tenant_domain_id == "td-acme"
    assert response.lifecycle_state == "active"

    revoked = await principal_service.revoke_principal(db_session, "principal-1")
    assert revoked.lifecycle_state == "revoked"
