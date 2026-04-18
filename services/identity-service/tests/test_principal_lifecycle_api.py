"""Principal lifecycle service behavior tests."""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from soorma_common.models import PrincipalRequest
from soorma_common.models import OnboardingRequest

from identity_service.core.dependencies import TenantContext, get_tenant_context
from identity_service.main import app
from identity_service.models.domain import Principal
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


@pytest.mark.asyncio
async def test_principal_admin_routes_allow_missing_service_user_context(db_session):
    """Admin principal routes should not require service tenant/user headers."""
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
            create_response = await async_client.post(
                "/v1/identity/principals",
                json={
                    "tenantDomainId": onboarding.tenant_domain_id,
                    "principalType": "developer",
                    "lifecycleState": "active",
                    "externalRef": "admin-route-create@example.com",
                },
                headers={
                    "X-Identity-Admin-Key": onboarding.tenant_admin_api_key,
                    "X-Tenant-ID": onboarding.platform_tenant_id,
                },
            )
            assert create_response.status_code == 200
            created_payload = create_response.json()

            update_response = await async_client.put(
                f"/v1/identity/principals/{created_payload['principalId']}",
                json={
                    "tenantDomainId": onboarding.tenant_domain_id,
                    "principalType": "developer",
                    "lifecycleState": "active",
                    "externalRef": "admin-route-update@example.com",
                },
                headers={
                    "X-Identity-Admin-Key": onboarding.tenant_admin_api_key,
                    "X-Tenant-ID": onboarding.platform_tenant_id,
                },
            )
            assert update_response.status_code == 200

            revoke_response = await async_client.post(
                f"/v1/identity/principals/{created_payload['principalId']}/revoke",
                headers={
                    "X-Identity-Admin-Key": onboarding.tenant_admin_api_key,
                    "X-Tenant-ID": onboarding.platform_tenant_id,
                },
            )
            assert revoke_response.status_code == 200
            revoked_payload = revoke_response.json()

        assert created_payload["principalId"].startswith("pr_")
        assert revoked_payload["lifecycleState"] == "revoked"
    finally:
        app.dependency_overrides.pop(get_tenant_context, None)


@pytest.mark.asyncio
async def test_principal_update_succeeds_and_updates_external_ref(db_session):
    """Admin update should succeed for same tenant context and persist external_ref changes."""
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
            create_response = await async_client.post(
                "/v1/identity/principals",
                json={
                    "tenantDomainId": onboarding.tenant_domain_id,
                    "principalType": "developer",
                    "lifecycleState": "active",
                    "externalRef": "principal-before-update@example.com",
                },
                headers={
                    "X-Identity-Admin-Key": onboarding.tenant_admin_api_key,
                    "X-Tenant-ID": onboarding.platform_tenant_id,
                },
            )
            assert create_response.status_code == 200
            created_payload = create_response.json()

            update_response = await async_client.put(
                f"/v1/identity/principals/{created_payload['principalId']}",
                json={
                    "tenantDomainId": onboarding.tenant_domain_id,
                    "principalType": "developer",
                    "lifecycleState": "active",
                    "externalRef": "principal-after-update@example.com",
                },
                headers={
                    "X-Identity-Admin-Key": onboarding.tenant_admin_api_key,
                    "X-Tenant-ID": onboarding.platform_tenant_id,
                },
            )

        assert update_response.status_code == 200

        principal_row = (
            await db_session.execute(
                select(Principal).where(Principal.principal_id == created_payload["principalId"])
            )
        ).scalars().first()

        assert principal_row is not None
        assert principal_row.external_ref == "principal-after-update@example.com"
    finally:
        app.dependency_overrides.pop(get_tenant_context, None)


@pytest.mark.asyncio
async def test_principal_update_rejects_platform_tenant_mismatch(db_session):
    """Admin update should fail when principal belongs to a different platform tenant."""
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

    principal_b = await principal_service.create_principal(
        db_session,
        PrincipalRequest(
            tenant_domain_id=tenant_b.tenant_domain_id,
            principal_type="developer",
            lifecycle_state="active",
            external_ref="cross-tenant-principal@example.com",
        ),
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
                f"/v1/identity/principals/{principal_b.principal_id}",
                json={
                    "tenantDomainId": tenant_b.tenant_domain_id,
                    "principalType": "developer",
                    "lifecycleState": "active",
                    "externalRef": "cross-tenant-principal-updated@example.com",
                },
                headers={
                    "X-Identity-Admin-Key": tenant_a.tenant_admin_api_key,
                    "X-Tenant-ID": tenant_a.platform_tenant_id,
                },
            )

        assert response.status_code == 403
        assert response.json()["detail"] == "Tenant domain does not belong to current platform tenant context."
    finally:
        app.dependency_overrides.pop(get_tenant_context, None)


@pytest.mark.asyncio
async def test_principal_update_rejects_payload_tenant_domain_mismatch(db_session):
    """Admin update should fail when payload tenant domain does not match persisted principal tenant domain."""
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

    principal_a = await principal_service.create_principal(
        db_session,
        PrincipalRequest(
            tenant_domain_id=tenant_a.tenant_domain_id,
            principal_type="developer",
            lifecycle_state="active",
            external_ref="payload-mismatch@example.com",
        ),
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
                f"/v1/identity/principals/{principal_a.principal_id}",
                json={
                    "tenantDomainId": tenant_b.tenant_domain_id,
                    "principalType": "developer",
                    "lifecycleState": "active",
                    "externalRef": "payload-mismatch-updated@example.com",
                },
                headers={
                    "X-Identity-Admin-Key": tenant_a.tenant_admin_api_key,
                    "X-Tenant-ID": tenant_a.platform_tenant_id,
                },
            )

        assert response.status_code == 400
        assert response.json()["detail"] == (
            "Principal tenant domain in payload does not match persisted principal tenant domain."
        )
    finally:
        app.dependency_overrides.pop(get_tenant_context, None)
