"""Tenant admin credential rotation API tests."""

import pytest
from httpx import ASGITransport, AsyncClient

from identity_service.core.dependencies import TenantContext, get_tenant_context
from identity_service.main import app
from identity_service.services.admin_api_keys import tenant_admin_api_key_service
from identity_service.services.onboarding_service import onboarding_service
from soorma_common.models import OnboardingRequest


@pytest.mark.asyncio
async def test_rotate_tenant_admin_credential_revokes_old_key_and_returns_new_key(db_session):
    """Rotation should revoke the current key and immediately activate a new one."""
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
            rotate_response = await async_client.post(
                "/v1/identity/tenant-admin-credentials/rotate",
                headers={
                    "X-Identity-Admin-Key": onboarding.tenant_admin_api_key,
                    "X-Tenant-ID": onboarding.platform_tenant_id,
                },
            )

            assert rotate_response.status_code == 200
            rotate_payload = rotate_response.json()
            assert rotate_payload["status"] == "rotated"
            assert rotate_payload["tenantAdminApiKey"] != onboarding.tenant_admin_api_key
            assert rotate_payload["tenantAdminApiKey"].startswith("idadm.")

            old_key_reuse_response = await async_client.post(
                "/v1/identity/tenant-admin-credentials/rotate",
                headers={
                    "X-Identity-Admin-Key": onboarding.tenant_admin_api_key,
                    "X-Tenant-ID": onboarding.platform_tenant_id,
                },
            )
            assert old_key_reuse_response.status_code == 403

            new_key_rotate_response = await async_client.post(
                "/v1/identity/tenant-admin-credentials/rotate",
                headers={
                    "X-Identity-Admin-Key": rotate_payload["tenantAdminApiKey"],
                    "X-Tenant-ID": onboarding.platform_tenant_id,
                },
            )
            assert new_key_rotate_response.status_code == 200
    finally:
        app.dependency_overrides.pop(get_tenant_context, None)


@pytest.mark.asyncio
async def test_rotate_tenant_admin_credential_requires_explicit_tenant_header(db_session):
    """Rotation should fail when tenant header is missing."""
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
            response = await async_client.post(
                "/v1/identity/tenant-admin-credentials/rotate",
                headers={"X-Identity-Admin-Key": onboarding.tenant_admin_api_key},
            )

        assert response.status_code == 400
        assert response.json()["detail"] == "X-Tenant-ID header is required for tenant admin authorization."
    finally:
        app.dependency_overrides.pop(get_tenant_context, None)
