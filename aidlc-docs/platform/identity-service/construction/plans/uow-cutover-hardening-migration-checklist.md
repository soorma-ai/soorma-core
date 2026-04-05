# Unit 4 Migration Checklist - uow-cutover-hardening

## Purpose
Track final cutover execution for single tenant-id convergence and removal of legacy tenant propagation behavior.

## Scope
- Remove X-Tenant-ID runtime dependency for tenant propagation.
- Enforce JWT-only tenant derivation.
- Eliminate active dual naming and storage redundancy for tenant identifiers.
- Finalize token-issuance caller-auth hardening and strict subject-bound authorization.
- Finalize asymmetric signing and public-key JWT verification in production path.

## Execution Checklist
- [ ] Confirm Unit 3 migration checklist exit criteria are complete.
- [ ] Remove legacy tenant-header dependency from runtime request flows.
- [ ] Enforce JWT-only tenant derivation at ingress and internal service boundaries.
- [ ] Converge active contracts to one canonical tenant id.
- [ ] Remove broad static admin-key path for normal token issuance operations.
- [ ] Implement final caller-auth mechanism for token issuance as approved in Unit 3.
- [ ] Enforce strict issuance authorization policy:
  - [ ] self-issue only by default
  - [ ] explicit admin-override path with auditable reason and scope
  - [ ] caller tenant must match target principal tenant unless override policy explicitly allows
- [ ] Remove shared-secret HS256 as default production signing/verification path for platform-issued tokens.
- [ ] Enforce asymmetric signing with identity-service private key custody.
- [ ] Enforce verifier public-key resolution from JWKS/public-key distribution path.
- [ ] Finalize key rotation behavior and `kid` rollover handling.
- [ ] Finalize delegated-issuer OIDC/JWKS validation support per approved scope.
- [ ] Remove or deprecate dual naming in active interfaces:
  - [ ] platform_tenant_id
  - [ ] tenant_domain_id
- [ ] Execute persistence migration to remove redundant tenant-id storage or finalize canonical-column rename policy.
- [ ] Remove production-path dependence on development fallback tenant constants.
- [ ] Update docs and examples to single tenant-id terminology only.
- [ ] Run full regression coverage for:
  - [ ] Authn/authz fail-closed behavior.
  - [ ] Token issuance and claim validation.
  - [ ] Event and service tenant propagation.
  - [ ] SDK and wrapper compatibility.
  - [ ] cross-principal issuance denial.
  - [ ] cross-tenant issuance denial.
  - [ ] unauthenticated and invalid-caller-credential denial.
  - [ ] invalid signature denial.
  - [ ] unknown `kid` denial.
  - [ ] rotated key acceptance and old-key rejection window behavior.
- [ ] Produce construction code summary artifact for Unit 4.

## Exit Criteria
- [ ] No production path relies on legacy tenant-header propagation.
- [ ] One canonical tenant id is used consistently in JWT, SDK, service boundaries, and identity contracts.
- [ ] Redundant tenant-id fields are removed or explicitly deprecated with a bounded removal window.
- [ ] Rollback and cutover verification evidence is captured in build-and-test outputs.
- [ ] Token issuance caller-auth and subject-authorization controls are enforced with deterministic fail-closed behavior.
- [ ] Platform-issued JWT trust no longer depends on a shared symmetric secret between signer and verifiers.

## Rollout Verification
- [ ] Canary or staged validation plan executed.
- [ ] Observability checks confirm no tenant-context mismatch errors post cutover.
- [ ] Security validation confirms mismatch paths fail closed.
