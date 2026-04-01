# Unit of Work Dependency

## Dependency Matrix

| Unit | Depends On | Dependency Type | Rationale |
|---|---|---|---|
| uow-shared-auth-foundation | None | Root | Establishes reusable auth context/compatibility base |
| uow-identity-core-domain | uow-shared-auth-foundation | Hard | Core identity APIs depend on stable shared auth dependencies |
| uow-sdk-jwt-integration | uow-shared-auth-foundation, uow-identity-core-domain | Hard | SDK JWT behavior requires shared context and identity API contracts |
| uow-cutover-hardening | uow-shared-auth-foundation, uow-identity-core-domain, uow-sdk-jwt-integration | Hard | Safe removal of legacy path requires all prior units complete |

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
- Stage 3 risk: SDK contract drift -> mitigate with wrapper compatibility tests.
- Stage 4 risk: cutover outage -> mitigate with fail-closed verification and rollback checklist.