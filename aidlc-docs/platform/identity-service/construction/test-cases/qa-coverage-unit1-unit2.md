# QA Test Case Coverage - Unit-1 and Unit-2

## Scope
This document records test coverage status for the following QA suites:
- Unit-1: `uow-shared-auth-foundation` (USAF)
- Unit-2: `uow-identity-core-domain` (UICD)

Source artifacts:
- `aidlc-docs/platform/identity-service/inception/test-cases/uow-shared-auth-foundation/test-case-index.md`
- `aidlc-docs/platform/identity-service/inception/test-cases/uow-shared-auth-foundation/test-specs-tabular.md`
- `aidlc-docs/platform/identity-service/inception/test-cases/uow-identity-core-domain/test-case-index.md`
- `aidlc-docs/platform/identity-service/inception/test-cases/uow-identity-core-domain/test-specs-tabular.md`
- `aidlc-docs/platform/identity-service/inception/test-cases/uow-identity-core-domain/enrichment-delta.md`

Validation timestamp: 2026-04-04 (UTC)

## Execution Evidence
Recent validation runs:
- `python -m pytest services/identity-service/tests/test_onboarding_api.py services/identity-service/tests/test_token_api.py services/identity-service/tests/test_mapping_policy_api.py`
  - Result: 7 passed
- `python -m pytest services/identity-service/tests --cov=services/identity-service/src/identity_service --cov-report=term`
  - Result: 14 passed, identity-service total line coverage 83%
- `python -m pytest libs/soorma-service-common/tests/test_dependencies.py`
  - Result: 28 passed

## Coverage Matrix

| Test Case ID | FR / BR Mapping | Coverage Status | Automated Evidence | Notes |
|---|---|---|---|---|
| TC-USAF-001 | FR-11 (JWT authoritative when present) | Covered | `libs/soorma-service-common/tests/test_middleware.py` (`test_jwt_present_uses_jwt_identity_over_headers`) | Verifies JWT context precedence over conflicting legacy headers. |
| TC-USAF-002 | FR-11 compatibility constraint (coexistence: legacy headers accepted when JWT absent) | Covered | `libs/soorma-service-common/tests/test_middleware.py` (`test_no_jwt_uses_legacy_headers`) | Aligned with corrected QA expectation for phase-1/phase-2 coexistence. |
| TC-USAF-003 | NFR-2 fail-closed auth behavior | Covered | `libs/soorma-service-common/tests/test_dependencies.py` (`test_raises_401_when_service_tenant_missing`, `test_raises_401_when_service_user_missing`, whitespace variants) | Missing user-context now fails closed with 401 and safe message. |
| TC-UICD-001 | FR-1, BR-02 (onboarding atomicity) | Covered | `services/identity-service/tests/test_onboarding_api.py` (`test_onboarding_creates_tenant_domain_and_bootstrap_principal`, `test_onboarding_rolls_back_domain_when_principal_creation_fails`) | Positive and rollback paths verified; transaction atomicity enforced. |
| TC-UICD-002 | FR-6, BR-11 (mandatory claim contract) | Covered | `services/identity-service/tests/test_token_api.py` (`test_platform_token_issuance_returns_bearer_token`) | Asserts mandatory claims: `iss`, `sub`, `aud`, `exp`, `iat`, `jti`, `platform_tenant_id`, `principal_id`, `principal_type`, `roles`. |
| TC-UICD-003 | FR-5, BR-17, BR-18 (typed deny + safe envelope + audit) | Covered | `services/identity-service/tests/test_token_api.py` (`test_delegated_issuance_denied_when_issuer_not_trusted`, `test_delegated_issuer_denial_returns_typed_safe_error_envelope`) | Verifies typed deny code, HTTP-safe payload, correlation ID propagation, and deny audit/issuance record persistence. |
| TC-UICD-004 | FR-9, BR-13, BR-16 (collision default deny + explicit/admin override) | Covered | `services/identity-service/tests/test_mapping_policy_api.py` (`test_mapping_collision_without_override_is_denied`) | Verifies default deny on collision, deny when non-admin requests override, allow only with explicit admin override. |

## Summary
- Total QA cases assessed: 7
- Covered: 7
- Partial: 0
- Missing: 0

## Residual Risks
- USAF cases are validated at shared dependency/middleware layer. Add service-route integration checks if route-level acceptance evidence is required by release gate policy.
