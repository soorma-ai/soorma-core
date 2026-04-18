"""Mapping API tenant-admin authorization tests."""

import pytest
from httpx import ASGITransport, AsyncClient

from identity_service.core.dependencies import TenantContext, get_tenant_context
from identity_service.main import app
from identity_service.services.mapping_service import mapping_service
from identity_service.services.onboarding_service import onboarding_service
from soorma_common.models import MappingEvaluationResponse, OnboardingRequest


@pytest.mark.asyncio
async def test_mapping_evaluate_accepts_tenant_admin_auth(db_session, monkeypatch):
    """Mapping evaluation should use tenant-admin auth instead of user-context JWTs."""
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

    async def _evaluate_mapping(*args, **kwargs):
        return MappingEvaluationResponse(decision="allow", reason_code="ok")

    monkeypatch.setattr(mapping_service, "evaluate_mapping", _evaluate_mapping)
    app.dependency_overrides[get_tenant_context] = _override_tenant_context
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as async_client:
            response = await async_client.post(
                "/v1/identity/mappings/evaluate",
                json={
                    "tenant_domain_id": onboarding.tenant_domain_id,
                    "source_issuer_id": "issuer-a",
                    "external_identity_key": "ext-user-1",
                    "canonical_identity_key": "canon-user-1",
                    "principal_id": onboarding.bootstrap_admin_principal_id,
                    "override_requested": False,
                },
                headers={
                    "X-Identity-Admin-Key": onboarding.tenant_admin_api_key,
                    "X-Tenant-ID": onboarding.platform_tenant_id,
                },
            )

        assert response.status_code == 200
        assert response.json() == {"decision": "allow", "reasonCode": "ok"}
    finally:
        app.dependency_overrides.pop(get_tenant_context, None)
