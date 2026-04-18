"""Token service behavior tests."""

import jwt
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from soorma_common.models import (
    DelegatedIssuerRequest,
    OnboardingRequest,
    TokenIssueRequest,
    TokenIssuanceType,
)

from identity_service.core.dependencies import TenantContext, get_tenant_context
from identity_service.main import app
from identity_service.models.domain import IdentityAuditEvent, TokenIssuanceRecord
from identity_service.services.delegated_trust_service import delegated_trust_service
from identity_service.services.errors import IdentityServiceError
from identity_service.services.onboarding_service import onboarding_service
from identity_service.services.token_service import token_service


@pytest.mark.asyncio
async def test_platform_token_issuance_returns_bearer_token(db_session):
    """Platform issuance should return a bearer token payload."""
    onboarding = await onboarding_service.onboard_tenant(
        db_session,
        OnboardingRequest(),
        actor_id="system",
    )

    request = TokenIssueRequest(
        principal_id=onboarding.bootstrap_admin_principal_id,
        issuance_type=TokenIssuanceType.PLATFORM,
    )

    response = await token_service.issue_token(db_session, request)

    assert isinstance(response.token, str)
    assert response.token
    assert response.token_type == "Bearer"

    claims = jwt.decode(
        response.token,
        "dev-identity-signing-key",
        algorithms=["HS256"],
        options={"verify_aud": False},
    )
    assert claims["iss"] == "soorma-identity-service"
    assert claims["sub"] == onboarding.bootstrap_admin_principal_id
    assert claims["aud"] == "soorma-services"
    assert claims["tenant_id"] == onboarding.platform_tenant_id
    assert claims["platform_tenant_id"] == onboarding.platform_tenant_id
    assert claims["principal_id"] == onboarding.bootstrap_admin_principal_id
    assert claims["principal_type"] == "admin"
    assert claims["roles"] == ["admin"]
    assert claims["jti"]
    assert claims["iat"]
    assert claims["exp"]


@pytest.mark.asyncio
async def test_delegated_issuance_denied_when_issuer_not_trusted(db_session):
    """Delegated issuance should fail closed without trusted issuer context."""
    onboarding = await onboarding_service.onboard_tenant(
        db_session,
        OnboardingRequest(),
        actor_id="system",
    )

    request = TokenIssueRequest(
        principal_id=onboarding.bootstrap_admin_principal_id,
        issuance_type=TokenIssuanceType.DELEGATED,
        delegated_issuer_id="issuer-unknown",
    )

    with pytest.raises(IdentityServiceError) as err:
        await token_service.issue_token(db_session, request)

    assert err.value.code == "delegated_issuer_untrusted"
    assert err.value.status_code == 403

    denied_record = (
        await db_session.execute(
            select(TokenIssuanceRecord).where(
                TokenIssuanceRecord.principal_id == onboarding.bootstrap_admin_principal_id,
                TokenIssuanceRecord.decision == "denied",
            )
        )
    ).scalars().first()
    assert denied_record is not None
    assert denied_record.decision_reason_code == "delegated_issuer_untrusted"

    denied_audit = (
        await db_session.execute(
            select(IdentityAuditEvent).where(
                IdentityAuditEvent.event_type == "identity.token.denied"
            )
        )
    ).scalars().first()
    assert denied_audit is not None


@pytest.mark.asyncio
async def test_delegated_issuance_allowed_when_issuer_trusted(db_session):
    """Delegated issuance should return token when issuer trust exists."""
    onboarding = await onboarding_service.onboard_tenant(
        db_session,
        OnboardingRequest(),
        actor_id="system",
    )
    delegated = await delegated_trust_service.register_issuer(
        db_session,
        DelegatedIssuerRequest(
            tenant_domain_id=onboarding.tenant_domain_id,
            issuer_id="soorma-identity-service",
            jwk_set_ref_or_material="https://issuer.example/jwks.json",
            audience_policy_ref="aud-default",
            claim_mapping_policy_ref="claim-default",
        ),
        actor_id="admin-1",
    )

    response = await token_service.issue_token(
        db_session,
        TokenIssueRequest(
            principal_id=onboarding.bootstrap_admin_principal_id,
            issuance_type=TokenIssuanceType.DELEGATED,
            delegated_issuer_id=delegated.delegated_issuer_id,
        ),
    )
    assert response.token_type == "Bearer"
    assert response.token


@pytest.mark.asyncio
async def test_delegated_issuer_denial_returns_typed_safe_error_envelope(db_session):
    """Denied delegated issuance should return stable typed error payload from API."""
    onboarding = await onboarding_service.onboard_tenant(
        db_session,
        OnboardingRequest(),
        actor_id="system",
    )

    async def _override_user_context() -> TenantContext:
        return TenantContext(
            platform_tenant_id=onboarding.platform_tenant_id,
            service_tenant_id="svc-http",
            service_user_id="user-http",
            db=db_session,
            correlation_id="corr-http-1",
        )

    app.dependency_overrides[get_tenant_context] = _override_user_context
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as async_client:
            response = await async_client.post(
                "/v1/identity/tokens/issue",
                json={
                    "principal_id": onboarding.bootstrap_admin_principal_id,
                    "issuance_type": "delegated",
                    "delegated_issuer_id": "issuer-missing",
                },
                headers={
                    "X-Identity-Admin-Key": onboarding.tenant_admin_api_key,
                    "X-Tenant-ID": onboarding.platform_tenant_id,
                },
            )

        assert response.status_code == 403
        payload = response.json()
        assert payload["detail"]["code"] == "delegated_issuer_untrusted"
        assert payload["detail"]["message"] == "Delegated issuer is not trusted."
        assert payload["detail"]["correlation_id"] == "corr-http-1"
    finally:
        app.dependency_overrides.pop(get_tenant_context, None)


@pytest.mark.asyncio
async def test_platform_token_issue_allows_admin_without_service_user_context(db_session):
    """Admin token issuance endpoint should not require service tenant/user headers."""
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
                "/v1/identity/tokens/issue",
                json={
                    "principal_id": onboarding.bootstrap_admin_principal_id,
                    "issuance_type": "platform",
                },
                headers={
                    "X-Identity-Admin-Key": onboarding.tenant_admin_api_key,
                    "X-Tenant-ID": onboarding.platform_tenant_id,
                },
            )

        assert response.status_code == 200
        payload = response.json()
        assert payload["tokenType"] == "Bearer"
        assert isinstance(payload["token"], str)
        assert payload["token"]
    finally:
        app.dependency_overrides.pop(get_tenant_context, None)


@pytest.mark.asyncio
async def test_platform_token_issue_rejects_platform_tenant_mismatch(db_session):
    """Admin token issuance should fail when principal belongs to another platform tenant."""
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
            response = await async_client.post(
                "/v1/identity/tokens/issue",
                json={
                    "principal_id": tenant_b.bootstrap_admin_principal_id,
                    "issuance_type": "platform",
                },
                headers={
                    "X-Identity-Admin-Key": tenant_a.tenant_admin_api_key,
                    "X-Tenant-ID": tenant_a.platform_tenant_id,
                },
            )

        assert response.status_code == 403
        payload = response.json()
        assert payload["detail"]["code"] == "principal_platform_tenant_mismatch"
        assert payload["detail"]["message"] == "Principal does not belong to current platform tenant context."
    finally:
        app.dependency_overrides.pop(get_tenant_context, None)


@pytest.mark.asyncio
async def test_platform_tenant_mismatch_returns_typed_safe_error_envelope(db_session):
    """Platform mismatch denial should return stable typed error payload from API."""
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

    async def _override_tenant_context() -> TenantContext:
        return TenantContext(
            platform_tenant_id=tenant_a.platform_tenant_id,
            service_tenant_id="svc-http",
            service_user_id="user-http",
            db=db_session,
            correlation_id="corr-platform-mismatch",
        )

    app.dependency_overrides[get_tenant_context] = _override_tenant_context
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as async_client:
            response = await async_client.post(
                "/v1/identity/tokens/issue",
                json={
                    "principal_id": tenant_b.bootstrap_admin_principal_id,
                    "issuance_type": "platform",
                },
                headers={
                    "X-Identity-Admin-Key": tenant_a.tenant_admin_api_key,
                    "X-Tenant-ID": tenant_a.platform_tenant_id,
                },
            )

        assert response.status_code == 403
        payload = response.json()
        assert payload["detail"]["code"] == "principal_platform_tenant_mismatch"
        assert payload["detail"]["message"] == "Principal does not belong to current platform tenant context."
        assert payload["detail"]["correlation_id"] == "corr-platform-mismatch"
    finally:
        app.dependency_overrides.pop(get_tenant_context, None)


@pytest.mark.asyncio
async def test_platform_token_issue_requires_tenant_header_for_tenant_admin_key(db_session):
    """Tenant admin token issuance must require an explicit X-Tenant-ID header."""
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
                "/v1/identity/tokens/issue",
                json={
                    "principal_id": onboarding.bootstrap_admin_principal_id,
                    "issuance_type": "platform",
                },
                headers={"X-Identity-Admin-Key": onboarding.tenant_admin_api_key},
            )

        assert response.status_code == 400
        assert response.json()["detail"] == "X-Tenant-ID header is required for tenant admin authorization."
    finally:
        app.dependency_overrides.pop(get_tenant_context, None)
