# Unit of Work

## Decomposition Decision
- **Approach**: Hybrid capability-first with explicit layer subphases.
- **Unit Count**: 4 units (balanced PR cadence).
- **Critical Path Principle**: Each unit is mergeable to main with predecessors completed and without requiring full-project completion.

## Unit 1 - Shared Auth Context Foundation
- **Unit Name**: uow-shared-auth-foundation
- **Purpose**: Establish JWT-capable shared dependency layer while preserving existing DI/router call sites.
- **Scope**:
  - Evolve shared auth context/dependency abstractions in common library.
  - Implement compatibility adapter behavior for coexistence.
  - Provide policy hooks for mandatory/optional claim validation.
- **Primary Artifacts/Targets**:
  - Shared dependency/middleware contracts.
  - Auth context normalization interfaces.
- **Why first**: Enables non-breaking downstream service and SDK updates.
- **Mergeability**: Can be merged independently with coexistence mode and tests.

## Unit 2 - Identity Service Core Domain
- **Unit Name**: uow-identity-core-domain
- **Purpose**: Implement core identity domain capabilities for tenant onboarding, principal lifecycle, token issuance, and delegated trust registration.
- **Scope**:
  - Tenant onboarding and principal lifecycle APIs.
  - Token issuance with mandatory claims.
  - Delegated issuer static-key trust model (v1) with extension points.
  - Claim context policy and mapping-rule support.
- **Primary Artifacts/Targets**:
  - Identity service components and methods.
  - Policy and trust components.
- **Dependencies**: Requires Unit 1 shared context foundation.
- **Mergeability**: Mergeable after Unit 1 with feature-complete core APIs and tests.

## Unit 3 - SDK and Wrapper JWT Integration
- **Unit Name**: uow-sdk-jwt-integration
- **Purpose**: Upgrade SDK wrappers/clients to use JWT-authenticated flows without changing handler call signatures, and begin 1:1 tenant-id convergence.
- **Scope**:
  - Wrapper/client JWT request support.
  - Preserve two-layer SDK contracts and handler ergonomics.
  - Validate wrapper compatibility with identity core APIs.
  - Introduce canonical `tenant_id` semantics while retaining temporary backward-compatible aliases needed before Unit 4 cutover.
  - Add `soorma dev` tenant bootstrap CLI capability so local developers can initialize tenant onboarding without manual curl/Swagger flows.
- **Primary Artifacts/Targets**:
  - SDK wrapper/client integration updates.
  - Integration tests across SDK and service boundaries.
- **Dependencies**: Requires Unit 1 and Unit 2.
- **Mergeability**: Mergeable independently once integration tests pass.

### Unit 3 Migration Checklist (1:1 Tenant Model - Compatibility Phase)
- [ ] Define canonical tenant source as JWT `tenant_id` claim for SDK->service calls.
- [ ] Ensure SDK clients/wrappers stop introducing new `platform_tenant_id` payload semantics and rely on JWT-derived tenant context.
- [ ] Keep temporary compatibility aliases only where required for incremental merge safety.
- [ ] Define and approve caller authentication mechanism for token-issuance requests (separate from issued-subject JWT).
- [ ] Define token-issuance authorization policy model: self-issue baseline and explicit admin override conditions.
- [ ] Define asymmetric signing model for platform-issued JWTs (no shared symmetric signing secret across services).
- [ ] Define key-management model for local and non-local environments (private key ownership, public key distribution, rotation semantics).
- [ ] Define JWT algorithm and metadata requirements for issued tokens (`alg`, `kid`, issuer/audience constraints).
- [ ] Define verifier model for consuming services using public keys (JWKS consumption and cache/refresh behavior).
- [ ] Implement transitional caller-auth compatibility strategy for token issuance (bootstrap admin key path may remain only as bounded temporary behavior).
- [ ] Update identity token issuance/validation contract docs to mark `tenant_id` as canonical and legacy tenant fields as transitional.
- [ ] Add compatibility assertions: when legacy tenant header/field is present, it must match JWT `tenant_id`; mismatch fails closed.
- [ ] Add integration tests for coexistence mode: JWT-only success, JWT+legacy matching success, JWT+legacy mismatch denial.
- [ ] Add token-issuance authorization tests: caller-self success, caller-target mismatch denial, and scoped admin override success.
- [ ] Add signing/verification compatibility tests for asymmetric path (issue with private key, validate with public key/JWKS).
- [ ] Add `soorma dev` tenant bootstrap command for local onboarding automation (no manual curl/Swagger required).
- [ ] Add CLI tests for bootstrap command success and fail-closed behavior (auth/context/config errors).
- [ ] Add CLI docs for bootstrap usage, required env/config, and output contract.

### Unit 3 Done Criteria
- JWT path is primary and validated across SDK wrappers/clients.
- Canonical tenant value is propagated end-to-end from JWT claim.
- Backward compatibility remains available only as controlled temporary behavior.
- Caller-auth mechanism for token issuance is explicitly specified and implemented for compatibility phase.
- Asymmetric signing path and JWKS-based verification path are explicitly specified and implemented for compatibility phase.

## Unit 4 - Cutover, Hardening, and Legacy Header Removal
- **Unit Name**: uow-cutover-hardening
- **Purpose**: Complete FR-11 phase 3 cutover, remove tenant-id redundancy, and finalize operational hardening baseline.
- **Scope**:
  - Remove header-only auth path.
  - Enforce JWT-only ingress behavior.
  - Finalize security controls, telemetry completeness, and rollout verification.
  - Remove dual tenant identifier semantics and standardize on a single tenant id.
- **Primary Artifacts/Targets**:
  - Cutover configuration and validation paths.
  - Build/test coverage for rollback and fail-closed behavior.
- **Dependencies**: Requires Unit 1, Unit 2, Unit 3.
- **Mergeability**: Final merge after full validation; still structured as one bounded unit.

### Unit 4 Migration Checklist (1:1 Tenant Model - Final Cutover)
- [ ] Remove `X-Tenant-ID` runtime dependency for tenant propagation in service-to-service and SDK requests.
- [ ] Enforce JWT-only tenant derivation at ingress and internal context boundaries.
- [ ] Replace remaining dual naming (`platform_tenant_id` and `tenant_domain_id`) with a single canonical `tenant_id` in active contracts.
- [ ] Remove broad static admin-key token-issuance path from normal operations; keep only explicitly defined break-glass path if approved.
- [ ] Enforce token-issuance subject binding: authenticated caller principal may issue only for self unless explicit admin override policy is satisfied.
- [ ] Enforce tenant-boundary checks for token issuance (caller tenant must match target principal tenant unless explicitly permitted).
- [ ] Remove HS256/shared-secret issuance and verification from normal production path.
- [ ] Enforce asymmetric signing for platform-issued tokens (for example RS256 or ES256) with private key restricted to identity-service signer.
- [ ] Enforce public-key verification in consuming services via JWKS/public-key distribution path.
- [ ] Finalize OIDC/JWKS support for delegated issuer validation according to approved trust model scope.
- [ ] Execute persistence/schema migration to eliminate redundant tenant-id storage (or keep one canonical column with explicit rename policy).
- [ ] Remove development fallback usage based on default platform tenant constants from production code paths.
- [ ] Update API/SDK docs and examples to single-tenant-id terminology only.
- [ ] Run regression suites for auth, token issuance, event propagation, and fail-closed security behavior.
- [ ] Run explicit negative security tests for token issuance: cross-principal denial, cross-tenant denial, unauthenticated denial, invalid-credential denial.
- [ ] Run explicit cryptographic validation tests: invalid signature denial, unknown `kid` denial, rotated-key acceptance window behavior.

### Unit 4 Done Criteria
- No production path relies on legacy tenant header propagation.
- One canonical tenant id is used consistently in JWT claims, event context, SDK requests, and identity APIs.
- Redundant tenant-id fields are removed or formally deprecated with a bounded removal window.
- Token issuance is protected by explicit caller authentication design and deterministic subject/tenant authorization enforcement.
- Shared symmetric signing secret is no longer required for platform-issued JWT validation in normal operations.

## Unit Quality Rules
- Each unit includes embedded compatibility acceptance checks (FR-11).
- Each unit includes security and QA checks (per enabled extensions).
- Each unit produces reviewable PR-scope outputs with clear done criteria.
- No unit depends on unplanned hidden work outside predecessor chain.