# Unit of Work Dependency

## Dependency Matrix

| Unit | Depends On | Dependency Type | Rationale |
|---|---|---|---|
| uow-shared-auth-foundation | None | Root | Establishes reusable auth context/compatibility base |
| uow-identity-core-domain | uow-shared-auth-foundation | Hard | Core identity APIs depend on stable shared auth dependencies |
| uow-sdk-jwt-integration | uow-shared-auth-foundation, uow-identity-core-domain | Hard | SDK JWT behavior requires shared context and identity API contracts; begins canonical single tenant id propagation |
| uow-cutover-hardening | uow-shared-auth-foundation, uow-identity-core-domain, uow-sdk-jwt-integration | Hard | Safe removal of legacy path and dual tenant-id redundancy requires all prior units complete |

## Critical Path
uow-shared-auth-foundation -> uow-identity-core-domain -> uow-sdk-jwt-integration -> uow-cutover-hardening

## Parallelization Notes
- No full parallel execution on critical path due auth-contract dependencies.
- Subtasks within each unit may run in parallel (tests/docs/adapters), but merge gates follow dependency order.

## Mergeability Strategy
- Every unit must be independently mergeable to main after predecessor completion.
- Unit completion criteria include:
  - Tests green for unit scope.
  - No required downstream unit changes to keep current behavior functional.
  - Compatibility behavior preserved until final cutover unit.

## Risk Controls by Dependency Stage
- Stage 1 risk: contract regression in shared dependencies -> mitigate with compatibility tests.
- Stage 2 risk: identity core policy mismatch -> mitigate with claim/policy integration tests.
- Stage 3 risk: SDK contract drift during canonical tenant-id convergence -> mitigate with wrapper compatibility tests and JWT/legacy mismatch fail-closed checks.
- Stage 4 risk: cutover outage and data-contract breakage during redundancy removal -> mitigate with fail-closed verification, schema migration checklist, and rollback checklist.

## Single Tenant ID Convergence Controls
- Unit 3 (compatibility phase): adopt JWT `tenant_id` as canonical tenant source while permitting bounded transitional aliases.
- Unit 4 (final cutover): remove legacy tenant-header dependency and dual naming (`platform_tenant_id` and `tenant_domain_id`) from active contracts in favor of one canonical tenant id.

## Signing and Verification Controls
- Unit 3 (compatibility phase): introduce asymmetric signing path for platform-issued JWTs and consumer verification via public key/JWKS compatibility flow.
- Unit 4 (final cutover): remove shared-secret production dependency and enforce asymmetric signing with finalized JWKS/public-key distribution and rotation behavior.

## Construction Tracking Artifacts
- Unit 3 checklist: aidlc-docs/platform/identity-service/construction/plans/uow-sdk-jwt-integration-migration-checklist.md
- Unit 4 checklist: aidlc-docs/platform/identity-service/construction/plans/uow-cutover-hardening-migration-checklist.md