"""Onboarding service behavior tests."""

import importlib

import pytest
from sqlalchemy import select
from soorma_common.models import OnboardingRequest

from identity_service.models.domain import PlatformTenantIdentityDomain, Principal
from identity_service.services.onboarding_service import onboarding_service

onboarding_service_module = importlib.import_module("identity_service.services.onboarding_service")


@pytest.mark.asyncio
async def test_onboarding_creates_tenant_domain_and_bootstrap_principal(db_session):
    """Onboarding should return created domain and bootstrap principal IDs."""
    request = OnboardingRequest(bootstrap_admin_external_ref="admin@example.com")

    response = await onboarding_service.onboard_tenant(db_session, request, actor_id="system")

    assert response.tenant_domain_id.startswith("td_")
    assert response.platform_tenant_id.startswith("pt_")
    assert response.bootstrap_admin_principal_id.startswith("pr_")
    assert response.status == "created"

    domain = (await db_session.execute(
        select(PlatformTenantIdentityDomain).where(
            PlatformTenantIdentityDomain.tenant_domain_id == response.tenant_domain_id
        )
    )).scalars().first()
    assert domain is not None
    assert domain.platform_tenant_id == response.platform_tenant_id

    principal = (await db_session.execute(
        select(Principal).where(Principal.principal_id == response.bootstrap_admin_principal_id)
    )).scalars().first()
    assert principal is not None
    assert principal.lifecycle_state == "active"
    assert principal.external_ref == "admin@example.com"


@pytest.mark.asyncio
async def test_onboarding_rolls_back_domain_when_principal_creation_fails(db_session, monkeypatch):
    """Onboarding must be atomic: a principal failure must roll back tenant-domain insert."""

    async def _raise_on_create(*args, **kwargs):
        raise RuntimeError("simulated principal write failure")

    monkeypatch.setattr(
        onboarding_service_module.principal_repository,
        "create_principal",
        _raise_on_create,
    )

    with pytest.raises(RuntimeError, match="simulated principal write failure"):
        await onboarding_service.onboard_tenant(
            db_session,
            OnboardingRequest(),
            actor_id="system",
        )

    all_domains = (await db_session.execute(select(PlatformTenantIdentityDomain))).scalars().all()
    assert len(all_domains) == 0
