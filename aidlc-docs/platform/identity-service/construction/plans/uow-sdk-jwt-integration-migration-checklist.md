# Unit 3 Migration Checklist - uow-sdk-jwt-integration

## Purpose
Track construction execution for Unit 3 single tenant-id convergence while preserving incremental merge safety.

## Scope
- JWT-first SDK and wrapper integration.
- Canonical tenant propagation using JWT tenant_id.
- Transitional compatibility controls required before Unit 4 cutover.
- Explicit caller-auth mechanism and authorization-policy design for token issuance.
- Asymmetric signing and public-key verification design/prototyping for platform-issued JWTs.
- Local developer onboarding automation via `soorma dev` tenant bootstrap command (to replace manual curl/Swagger bootstrap flow).

## Execution Checklist
- [ ] Confirm Unit 1 and Unit 2 outputs are merged and available in branch baseline.
- [ ] Define canonical tenant source as JWT tenant_id for SDK to service flows.
- [ ] Decide and document caller authentication mechanism for token issuance requests (for example: client credentials, signed client assertion, mTLS, or temporary bootstrap key path).
- [ ] Define subject-authorization policy for token issuance:
  - [ ] self-issue allowed (caller principal_id == requested principal_id)
  - [ ] admin-override conditions explicitly scoped and auditable
  - [ ] tenant-boundary enforcement rules defined
- [ ] Define asymmetric signing design:
  - [ ] selected algorithm for platform-issued tokens (RS256 or ES256)
  - [ ] private key ownership boundary (identity service signer only)
  - [ ] public key distribution strategy for consumers (JWKS/public key)
  - [ ] token header requirements (`alg`, `kid`)
- [ ] Implement compatibility-phase asymmetric issuance path and verifier path in local/dev test flow.
- [ ] Update SDK clients and wrappers to avoid introducing new platform_tenant_id payload semantics.
- [ ] Keep only bounded transitional aliases required by still-open Unit 4 dependencies.
- [ ] Implement `soorma dev` tenant bootstrap command that invokes identity onboarding using configured admin credentials and tenant context.
- [ ] Define command UX and output contract (human-readable summary and machine-readable/json mode).
- [ ] Ensure idempotent/repeat-run behavior is explicit and documented (for example: reuse/error mode).
- [ ] Add fail-closed validation for JWT and legacy tenant mismatch paths.
- [ ] Ensure two-layer architecture remains intact (agent handlers use wrappers only).
- [ ] Update request/response and event propagation contracts to document canonical tenant semantics.
- [ ] Implement compatibility-phase token issuance route behavior to enforce selected caller-auth and subject-authorization policy.
- [ ] Add integration tests for:
  - [ ] JWT-only success path.
  - [ ] JWT plus matching legacy tenant success path.
  - [ ] JWT plus mismatching legacy tenant denial path.
  - [ ] caller self-issue success path.
  - [ ] caller-to-other-principal denial path.
  - [ ] admin-override success path (scoped).
  - [ ] asymmetric signature validation success path.
  - [ ] invalid signature and unknown `kid` denial path.
  - [ ] CLI bootstrap happy-path onboarding from local `soorma dev` flow.
  - [ ] CLI bootstrap negative paths (missing admin key, invalid tenant context, identity service unavailable).
- [ ] Run impacted suites:
  - [ ] SDK wrapper and identity client tests.
  - [ ] Identity service auth and issuance tests.
  - [ ] Shared dependency validation tests.
- [ ] Produce construction code summary artifact for Unit 3.

## Exit Criteria
- [ ] JWT path is primary and validated.
- [ ] Canonical tenant value is propagated end to end from JWT tenant_id.
- [ ] Transitional compatibility paths are explicitly bounded and documented for Unit 4 removal.
- [ ] No new code introduces dual tenant-id semantics.
- [ ] Caller-auth mechanism and token-issuance authorization policy are explicitly implemented and tested.
- [ ] Asymmetric issuance and public-key verification path are implemented and tested in compatibility phase.

## Rollback Readiness
- [ ] Compatibility feature flags or toggles are documented.
- [ ] Regression rollback instructions are included in build-and-test outputs.
