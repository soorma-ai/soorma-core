# Unit of Work Dependency Matrix

## Dependency Graph

```text
U1 (shared dependency)
  -> U2 (memory runtime alignment)
      -> U3 (schema/index/migration/tests)
```

## Matrix

| Unit | Depends On | Why Dependency Exists | Can Start Before Dependency Complete? |
|---|---|---|---|
| U1 | None | Foundation unit | Yes |
| U2 | U1 | Requires `require_user_context` implementation and public export | No |
| U3 | U2 | Constraint/index definitions must align to finalized runtime predicates/conflict targets | Draft-only yes, merge-ready no |

## Interface Contracts Between Units

### U1 -> U2 Contract
- `require_user_context` exists and is importable from shared package
- Validation behavior is stable: 400 on missing service_tenant_id/service_user_id
- Error message semantics are generic and future-proof

### U2 -> U3 Contract
- Runtime identity tuple is standardized at API/service/CRUD boundaries
- Conflict target semantics finalized for working/task/plan/semantic paths
- Admin/user-scoped route boundaries finalized

## Risk and Mitigation by Dependency

### Risk: U2 starts before U1 contract stabilizes
- **Impact**: churn in route dependency wiring and tests
- **Mitigation**: strict sequencing policy (Q2=A)

### Risk: U3 migration/index implementation diverges from U2 runtime semantics
- **Impact**: upsert conflicts, nondeterministic behavior, test failures
- **Mitigation**: finalize U2 first; use alignment checklist for U3

### Risk: test duplication across units
- **Impact**: maintenance overhead
- **Mitigation**: Q3=A ownership split (shared-lib tests for dependency contract; memory tests for behavioral isolation)

## Integration Checkpoints

1. **Checkpoint A (after U1)**
- Shared dependency tests pass
- Memory service can import dependency

2. **Checkpoint B (after U2)**
- API and CRUD behavior aligns to full identity tuple
- User-scoped/admin route boundaries verified

3. **Checkpoint C (after U3)**
- Migration upgrade/downgrade checks pass
- Isolation and collision-prevention tests pass
