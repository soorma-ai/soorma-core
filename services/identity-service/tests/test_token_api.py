"""Token service behavior tests."""

import jwt
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from soorma_common.models import (
    DelegatedIssuerRequest,
    OnboardingRequest,
    TokenIssueRequest,
)

from identity_service.core.dependencies import TenantContext, require_user_tenant_context
from identity_service.main import app
from identity_service.models.domain import IdentityAuditEvent, TokenIssuanceRecord
from identity_service.services.delegated_trust_service import delegated_trust_service
from identity_service.services.errors import IdentityServiceError
from identity_service.services.onboarding_service import onboarding_service
from identity_service.services.token_service import token_service


@pytest.mark.asyncio
async def test_platform_token_issuance_returns_bearer_token(db_session):
    """Platform issuance should return a bearer token payload."""
    await onboarding_service.onboard_tenant(
        db_session,
        OnboardingRequest(
            tenant_domain_id="td-acme",
            platform_tenant_id="pt-acme",
            bootstrap_admin_principal_id="principal-1",
            created_by="system",
        ),
    )

    request = TokenIssueRequest(
        tenant_domain_id="td-acme",
        principal_id="principal-1",
        issuance_type="platform",
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
    assert claims["sub"] == "principal-1"
    assert claims["aud"] == "soorma-services"
    assert claims["platform_tenant_id"] == "pt-acme"
    assert claims["principal_id"] == "principal-1"
    assert claims["principal_type"] == "admin"
    assert claims["roles"] == ["admin"]
    assert claims["jti"]
    assert claims["iat"]
    assert claims["exp"]


@pytest.mark.asyncio
async def test_delegated_issuance_denied_when_issuer_not_trusted(db_session):
    """Delegated issuance should fail closed without trusted issuer context."""
    await onboarding_service.onboard_tenant(
        db_session,
        OnboardingRequest(
            tenant_domain_id="td-acme",
            platform_tenant_id="pt-acme",
            bootstrap_admin_principal_id="principal-1",
            created_by="system",
        ),
    )

    request = TokenIssueRequest(
        tenant_domain_id="td-acme",
        principal_id="principal-1",
        issuance_type="delegated",
        delegated_issuer_id="issuer-unknown",
    )

    with pytest.raises(IdentityServiceError) as err:
        await token_service.issue_token(db_session, request)

    assert err.value.code == "delegated_issuer_untrusted"
    assert err.value.status_code == 403

    denied_record = (
        await db_session.execute(
            select(TokenIssuanceRecord).where(
                TokenIssuanceRecord.principal_id == "principal-1",
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
    await onboarding_service.onboard_tenant(
        db_session,
        OnboardingRequest(
            tenant_domain_id="td-acme",
            platform_tenant_id="pt-acme",
            bootstrap_admin_principal_id="principal-1",
            created_by="system",
        ),
    )
    await delegated_trust_service.register_issuer(
        db_session,
        DelegatedIssuerRequest(
            delegated_issuer_id="issuer-1",
            tenant_domain_id="td-acme",
            issuer_id="soorma-identity-service",
            jwk_set_ref_or_material="https://issuer.example/jwks.json",
            audience_policy_ref="aud-default",
            claim_mapping_policy_ref="claim-default",
            created_by="admin-1",
        ),
    )

    response = await token_service.issue_token(
        db_session,
        TokenIssueRequest(
            tenant_domain_id="td-acme",
            principal_id="principal-1",
            issuance_type="delegated",
            delegated_issuer_id="issuer-1",
        ),
    )
    assert response.token_type == "Bearer"
    assert response.token


@pytest.mark.asyncio
async def test_delegated_issuer_denial_returns_typed_safe_error_envelope(db_session):
    """Denied delegated issuance should return stable typed error payload from API."""
    await onboarding_service.onboard_tenant(
        db_session,
        OnboardingRequest(
            tenant_domain_id="td-http",
            platform_tenant_id="pt-http",
            bootstrap_admin_principal_id="principal-http",
            created_by="system",
        ),
    )

    async def _override_user_context() -> TenantContext:
        return TenantContext(
            platform_tenant_id="pt-http",
            service_tenant_id="svc-http",
            service_user_id="user-http",
            db=db_session,
            correlation_id="corr-http-1",
        )

    app.dependency_overrides[require_user_tenant_context] = _override_user_context
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as async_client:
            response = await async_client.post(
                "/v1/identity/tokens/issue",
                json={
                    "tenant_domain_id": "td-http",
                    "principal_id": "principal-http",
                    "issuance_type": "delegated",
                    "delegated_issuer_id": "issuer-missing",
                },
            )

        assert response.status_code == 403
        payload = response.json()
        assert payload["detail"]["code"] == "delegated_issuer_untrusted"
        assert payload["detail"]["message"] == "Delegated issuer is not trusted."
        assert payload["detail"]["correlation_id"] == "corr-http-1"
    finally:
        app.dependency_overrides.pop(require_user_tenant_context, None)
