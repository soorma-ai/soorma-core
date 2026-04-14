# Functional Design Plan - uow-cutover-hardening

## Unit Context
- Unit: uow-cutover-hardening
- Purpose: Complete FR-11 phase 3 cutover, remove tenant-id redundancy, and finalize security/operational hardening baseline.
- Dependencies: uow-shared-auth-foundation, uow-identity-core-domain, uow-sdk-jwt-integration.
- Story coverage:
  - US-4.3 Header Auth Removal Cutover
  - FR-11 Incremental JWT Rollout (phase 3 cutover)
  - FR-13 Auditability
  - NFR-1 Security baseline enforcement
  - NFR-2 fail-closed authorization
  - NFR-4 observability

## Architecture Pattern Alignment
- Section 1 (Authentication model): enforce JWT-only ingress for secured routes and preserve explicit trust boundaries for identity issuance paths.
- Section 2 (Two-layer SDK): preserve wrapper-first access patterns while finalizing cutover behavior in shared dependencies and service boundaries.
- Section 3 (Event choreography): preserve explicit response and correlation semantics while hardening auth-related event decisions.
- Section 4 (Multi-tenancy and RLS): converge active contracts to canonical tenant_id and ensure tenant-bound authorization checks fail closed.
- Section 6 (Error handling): deny safely for missing/invalid auth context without leaking internals.
- Section 7 (Testing): require deterministic unit/integration coverage and explicit negative security checks for cutover.

## Extension and Security Alignment
- Security Baseline (enabled): functional design must address SECURITY-03, SECURITY-08, SECURITY-10, SECURITY-11, SECURITY-14, and SECURITY-15.
- QA Test Cases (enabled, happy-path-negative): design decisions must preserve traceability to TC-UCH-001, TC-UCH-002, and TC-UCH-003.
- PR Checkpoint (enabled): functional design outputs will be reviewed at the construction design checkpoint before code generation.

## Source Artifacts Loaded
- aidlc-docs/platform/identity-service/inception/application-design/unit-of-work.md
- aidlc-docs/platform/identity-service/inception/application-design/unit-of-work-story-map.md
- aidlc-docs/platform/identity-service/inception/requirements/requirements.md
- aidlc-docs/platform/identity-service/inception/user-stories/stories.md
- aidlc-docs/platform/identity-service/construction/plans/uow-cutover-hardening-migration-checklist.md
- aidlc-docs/platform/identity-service/inception/test-cases/uow-cutover-hardening/test-specs-narrative.md

## Execution Checklist
- [x] Step 1 - Analyze unit scope, dependencies, requirements traceability, and migration checklist.
- [x] Step 2 - Create functional design planning checklist for this unit.
- [x] Step 3 - Generate clarifying questions for cutover-hardening business logic and policy behavior.
- [x] Step 4 - Store planning artifact.
- [x] Step 5 - Collect and analyze answers.
- [x] Step 6 - Generate functional design artifacts.
- [x] Step 7 - Present functional design completion review gate.

## Functional Design Clarifying Questions
Please answer each question by filling in the [Answer]: line.

## Question 1
How should cutover activation be modeled for production behavior?

A) Single one-time cutover enforced by released JWT-only code path (no runtime feature flag)

B) Single cutover with a temporary runtime JWT-only flag for operational rollback

C) Endpoint-by-endpoint rollout switches with partial cutover support

D) Environment-based implicit behavior without explicit cutover controls

X) Other (please describe after [Answer]: tag below)

[Answer]: A)

Rationale:
- No long-lived cutover flag should remain in production code.
- Cutover is treated as a one-time release boundary, not a runtime toggle.
- Rollback is handled through deployment rollback procedure, not flag reversal.

## Question 2
Which secured endpoints, if any, should remain exempt from JWT requirement after cutover?

A) No secured endpoint exemptions; only unauthenticated health/discovery endpoints remain public (token issuance would also require caller JWT)

B) Identity token-issuance endpoint only may use trusted caller credentials; all other secured endpoints require JWT

C) Allow temporary endpoint exemption list configurable by environment

X) Other (please describe after [Answer]: tag below)

[Answer]: B)

Rationale:
- This avoids bootstrap recursion for first-token acquisition.
- It aligns with the target model: token issuance is the controlled trusted-caller entry point, while all other secured endpoints remain JWT-only.
- Health/discovery endpoints remain unauthenticated and outside secured endpoint policy.

## Question 3
What is the final functional policy for token issuance authorization after cutover?

A) Self-issue only for authenticated caller principal

B) Self-issue default plus explicit admin-override path with required reason and scope audit (admin override authorizes issue-for-other and is separate from trusted-caller authentication)

C) Any authenticated principal in the same tenant may issue for others

X) Other (please describe after [Answer]: tag below)

[Answer]: B)

Rationale:
- Self-issue remains the default policy baseline.
- Issue-for-other requires explicit admin override authorization derived from caller auth context.
- Override authority is not self-asserted in request payload; it is validated from caller scope/role claims or server-side credential policy binding.
- Override requests must include explicit reason/scope and produce structured audit telemetry.
- Tenant-boundary checks and fail-closed behavior are mandatory for all override decisions.

Clarification note:
- Trusted caller request authenticates who is calling the token-issuance endpoint.
- Admin override controls whether that authenticated caller may request a token for a different target principal.
- Override authority source is caller auth context, not request body assertion:
  - If caller auth uses JWT, override permission is conveyed by caller JWT role/scope claims (for example `identity:token:issue:any-principal`).
  - If caller auth uses API key/admin key, override permission is resolved by server-side policy bound to that credential.
- The issuance request may carry `target_principal_id` and `override_reason`, but those fields never grant authority by themselves.
- Server must enforce: caller authenticated, override permission present for issue-for-other, tenant boundary checks pass, and override action is fully audited.

## Question 4
How should canonical tenant identifier convergence be handled in active interfaces?

A) Immediate hard rename to tenant_id with no compatibility aliases

B) Canonical tenant_id active path with bounded compatibility aliases that must match and are scheduled for removal

C) Keep dual naming indefinitely for backward compatibility

X) Other (please describe after [Answer]: tag below)

[Answer]: A)

Rationale:
- Converge immediately to canonical tenant_id as part of this release.
- No backward-compatibility aliases or grace period are required.
- This mirrors Q1 hard cutover posture (release-boundary fix, not staged runtime compatibility).
- Any incompatible callers are addressed via coordinated release rollout, not dual-contract support.

## Question 5
Which signing and verification posture should be enforced in normal production path?

A) RS256 signing with identity-service private key custody and JWKS/public-key verification in consumers

B) HS256 shared-secret signing/verification remains allowed as production fallback

C) Support both equally in production indefinitely

X) Other (please describe after [Answer]: tag below)

[Answer]: A)

Rationale:
- Hard cutover posture favors a single production signing and verification contract.
- RS256 plus JWKS/public-key verification enforces private-key custody separation and removes shared-secret coupling.
- HS256 production fallback (option B) only has transitional value for staged migration; it conflicts with the release-boundary hard-fix strategy.
- Fail-closed behavior is stronger when verifiers do not silently downgrade to symmetric fallback in production.
- Local developer ergonomics are handled by asymmetric bootstrap automation in soorma dev CLI (generate or seed RS256 keypair/JWKS and wire env), not by HS256 production fallback.
- If HS256 exists anywhere, it must be explicit non-production test mode and disabled in normal soorma dev default path.

## Question 6
How should unknown kid and rotated key behavior be functionally defined?

A) Unknown kid denied fail-closed; rotated keys accepted only within explicit overlap window; expired overlap denies old keys

B) Unknown kid triggers permissive fallback to any available key

C) Unknown kid accepted in non-production environments only

X) Other (please describe after [Answer]: tag below)

[Answer]: A)

## Question 7
What minimum audit telemetry is required for denied legacy/header-only requests post-cutover?

A) Event type, timestamp, correlation/request id, tenant context, decision outcome, and denial reason code (no token/header secrets)

B) Error message only

C) Full request dump including headers for debugging

X) Other (please describe after [Answer]: tag below)

[Answer]: A)

## Question 8
How should rollback readiness be represented in functional behavior?

A) Documented reversible configuration/operational procedure with deterministic verification checks

B) Code revert only; no explicit runtime rollback controls

C) Best effort guidance without deterministic criteria

X) Other (please describe after [Answer]: tag below)

[Answer]: A)

Rationale:
- Hard cutover does not remove rollback responsibility; it changes rollback mechanism.
- Rollback is release/deployment based with deterministic entry/exit verification, not runtime feature-flag reversal.
- This preserves fail-closed security posture while maintaining operational safety during incident recovery.

Clarification note:
- Yes, rollback readiness is still required under hard cutover posture.
- Rollback in this context means release/deployment rollback with deterministic verification checks, not runtime feature-flag rollback.
- The rollback plan should specify entry criteria, execution steps, and post-rollback validation signals.

## Question 9
How should delegated issuer validation scope be finalized for this unit?

A) Complete approved OIDC/JWKS delegated validation behavior now as part of cutover-hardening

B) Keep delegated validation at current static-key behavior only and defer OIDC/JWKS finalization to future work

C) Make delegated validation mode runtime-selectable without policy constraints

X) Other (please describe after [Answer]: tag below)

[Answer]: A)

Rationale:
- Option A is within approved Unit 4 scope and aligns with hard cutover posture.
- Completing delegated issuer OIDC/JWKS finalization now prevents a split trust model after release.
- Scope is bounded to approved behaviors only: issuer trust validation, JWKS retrieval/cache/rotation handling, and policy-gated delegated claim acceptance.
- No new product surface is introduced beyond approved unit boundaries.

Clarification note:
- Option A is within approved unit scope, because Unit 4 checklist already includes delegated-issuer OIDC/JWKS validation finalization per approved scope.
- It is not scope creep if implementation is bounded to approved behaviors only (issuer trust validation, JWKS retrieval/cache/rotation handling, and policy-gated claim acceptance).
- It becomes scope creep only if expanded into new product surface beyond approved scope.
- Choosing option B is a valid deferral, but it is a scope change that should be explicitly re-baselined against Unit 4 exit criteria.

## Approval
After completing all answers, reply in chat with:
"functional design plan answers provided"