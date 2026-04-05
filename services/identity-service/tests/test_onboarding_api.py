"""Onboarding service behavior tests."""

import pytest
from sqlalchemy import select
from soorma_common.models import OnboardingRequest

from identity_service.models.domain import PlatformTenantIdentityDomain, Principal
from identity_service.services.onboarding_service import onboarding_service


@pytest.mark.asyncio
async def test_onboarding_creates_tenant_domain_and_bootstrap_principal(db_session):
    """Onboarding should return created domain and bootstrap principal IDs."""
    request = OnboardingRequest(
        tenant_domain_id="td-acme",
        platform_tenant_id="pt-acme",
        bootstrap_admin_principal_id="principal-admin",
        created_by="system",
    )

    response = await onboarding_service.onboard_tenant(db_session, request)

    assert response.tenant_domain_id == "td-acme"
    assert response.bootstrap_admin_principal_id == "principal-admin"
    assert response.status == "created"

    domain = (await db_session.execute(
        select(PlatformTenantIdentityDomain).where(
            PlatformTenantIdentityDomain.tenant_domain_id == "td-acme"
        )
    )).scalars().first()
    assert domain is not None

    principal = (await db_session.execute(
        select(Principal).where(Principal.principal_id == "principal-admin")
    )).scalars().first()
    assert principal is not None
    assert principal.lifecycle_state == "active"
