"""Onboarding service behavior tests."""

import importlib

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, text
from soorma_common.models import OnboardingRequest

from identity_service.core.dependencies import TenantContext, get_tenant_context
from identity_service.main import app
from identity_service.models.domain import PlatformTenantIdentityDomain, Principal, TenantAdminCredential
from identity_service.services.admin_api_keys import tenant_admin_api_key_service
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
    parsed_key = tenant_admin_api_key_service._parse_api_key(response.tenant_admin_api_key)
    assert parsed_key is not None
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

    credential = (
        await db_session.execute(
            select(TenantAdminCredential).where(
                TenantAdminCredential.platform_tenant_id == response.platform_tenant_id,
                TenantAdminCredential.status == "active",
            )
        )
    ).scalars().first()
    assert credential is not None
    assert credential.credential_id == parsed_key[0]


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


@pytest.mark.asyncio
async def test_onboarding_succeeds_with_preexisting_session_transaction(db_session):
    """Onboarding should succeed when dependency setup already started a DB transaction."""
    await db_session.execute(text("SELECT 1"))
    assert db_session.in_transaction()

    response = await onboarding_service.onboard_tenant(
        db_session,
        OnboardingRequest(bootstrap_admin_external_ref="txn-test-admin"),
        actor_id="system",
    )

    assert response.status == "created"
    assert response.tenant_domain_id.startswith("td_")
    assert response.bootstrap_admin_principal_id.startswith("pr_")


@pytest.mark.asyncio
async def test_onboarding_api_allows_admin_bootstrap_without_service_user_context(db_session):
    """Admin bootstrap onboarding should not require service tenant/user headers."""

    async def _override_tenant_context() -> TenantContext:
        return TenantContext(
            platform_tenant_id="spt_test-platform",
            service_tenant_id=None,
            service_user_id=None,
            db=db_session,
        )

    app.dependency_overrides[get_tenant_context] = _override_tenant_context
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as async_client:
            response = await async_client.post(
                "/v1/identity/onboarding",
                json={"bootstrapAdminExternalRef": "test_tenant_01"},
                headers={"X-Identity-Admin-Key": "dev-identity-admin"},
            )

        assert response.status_code == 200
        payload = response.json()
        assert payload["tenantDomainId"].startswith("td_")
        assert payload["platformTenantId"].startswith("pt_")
        assert payload["bootstrapAdminPrincipalId"].startswith("pr_")
        assert payload["tenantAdminApiKey"].startswith("idadm.")
    finally:
        app.dependency_overrides.pop(get_tenant_context, None)
