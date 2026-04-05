"""Delegated issuer service behavior tests."""

import pytest
from httpx import ASGITransport, AsyncClient
from soorma_common.models import DelegatedIssuerRequest, OnboardingRequest

from identity_service.core.dependencies import TenantContext, get_tenant_context
from identity_service.main import app
from identity_service.services.onboarding_service import onboarding_service
from identity_service.services.delegated_trust_service import delegated_trust_service


@pytest.mark.asyncio
async def test_register_delegated_issuer_returns_active_status(db_session):
    """Registering delegated issuer should return active status."""
    onboarding = await onboarding_service.onboard_tenant(
        db_session,
        OnboardingRequest(),
        actor_id="system",
    )

    request = DelegatedIssuerRequest(
        tenant_domain_id=onboarding.tenant_domain_id,
        issuer_id="https://issuer.acme",
        jwk_set_ref_or_material="https://issuer.acme/.well-known/jwks.json",
        audience_policy_ref="aud-default",
        claim_mapping_policy_ref="cmp-default",
    )

    response = await delegated_trust_service.register_issuer(db_session, request, actor_id="admin-1")

    assert response.delegated_issuer_id.startswith("di_")
    assert response.issuer_id == "https://issuer.acme"
    assert response.status == "active"

    assert await delegated_trust_service.is_trusted(db_session, response.delegated_issuer_id)


@pytest.mark.asyncio
async def test_delegated_issuer_admin_routes_allow_missing_service_user_context(db_session):
    """Admin delegated issuer routes should not require service tenant/user headers."""
    onboarding = await onboarding_service.onboard_tenant(
        db_session,
        OnboardingRequest(),
        actor_id="system",
    )

    async def _override_tenant_context() -> TenantContext:
        return TenantContext(
            platform_tenant_id=onboarding.platform_tenant_id,
            service_tenant_id=None,
            service_user_id=None,
            db=db_session,
        )

    app.dependency_overrides[get_tenant_context] = _override_tenant_context
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as async_client:
            register_response = await async_client.post(
                "/v1/identity/delegated-issuers",
                json={
                    "tenantDomainId": onboarding.tenant_domain_id,
                    "issuerId": "https://issuer.admin-route",
                    "jwkSetRefOrMaterial": "https://issuer.admin-route/.well-known/jwks.json",
                    "audiencePolicyRef": "aud-admin-route",
                    "claimMappingPolicyRef": "cmp-admin-route",
                },
                headers={"X-Identity-Admin-Key": "dev-identity-admin"},
            )
            assert register_response.status_code == 200
            register_payload = register_response.json()

            update_response = await async_client.put(
                f"/v1/identity/delegated-issuers/{register_payload['delegatedIssuerId']}",
                json={
                    "tenantDomainId": onboarding.tenant_domain_id,
                    "issuerId": "https://issuer.admin-route",
                    "jwkSetRefOrMaterial": "https://issuer.admin-route/.well-known/jwks.v2.json",
                    "audiencePolicyRef": "aud-admin-route-v2",
                    "claimMappingPolicyRef": "cmp-admin-route-v2",
                },
                headers={"X-Identity-Admin-Key": "dev-identity-admin"},
            )

        assert update_response.status_code == 200
        updated_payload = update_response.json()
        assert register_payload["delegatedIssuerId"].startswith("di_")
        assert updated_payload["issuerId"] == "https://issuer.admin-route"
    finally:
        app.dependency_overrides.pop(get_tenant_context, None)


@pytest.mark.asyncio
async def test_delegated_issuer_update_rejects_platform_tenant_mismatch(db_session):
    """Admin delegated issuer update should fail for cross-platform-tenant resource access."""
    tenant_a = await onboarding_service.onboard_tenant(
        db_session,
        OnboardingRequest(),
        actor_id="system",
    )
    tenant_b = await onboarding_service.onboard_tenant(
        db_session,
        OnboardingRequest(),
        actor_id="system",
    )

    issuer_b = await delegated_trust_service.register_issuer(
        db_session,
        DelegatedIssuerRequest(
            tenant_domain_id=tenant_b.tenant_domain_id,
            issuer_id="https://issuer.cross-tenant",
            jwk_set_ref_or_material="https://issuer.cross-tenant/.well-known/jwks.json",
            audience_policy_ref="aud-cross-tenant",
            claim_mapping_policy_ref="cmp-cross-tenant",
        ),
        actor_id="system",
    )

    async def _override_tenant_context() -> TenantContext:
        return TenantContext(
            platform_tenant_id=tenant_a.platform_tenant_id,
            service_tenant_id=None,
            service_user_id=None,
            db=db_session,
        )

    app.dependency_overrides[get_tenant_context] = _override_tenant_context
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as async_client:
            response = await async_client.put(
                f"/v1/identity/delegated-issuers/{issuer_b.delegated_issuer_id}",
                json={
                    "tenantDomainId": tenant_b.tenant_domain_id,
                    "issuerId": "https://issuer.cross-tenant",
                    "jwkSetRefOrMaterial": "https://issuer.cross-tenant/.well-known/jwks.v2.json",
                    "audiencePolicyRef": "aud-cross-tenant-v2",
                    "claimMappingPolicyRef": "cmp-cross-tenant-v2",
                },
                headers={"X-Identity-Admin-Key": "dev-identity-admin"},
            )

        assert response.status_code == 403
        assert response.json()["detail"] == "Tenant domain does not belong to current platform tenant context."
    finally:
        app.dependency_overrides.pop(get_tenant_context, None)
