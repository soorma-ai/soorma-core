# Requirements-to-Unit Mapping

## Mapping Summary
This initiative skipped user stories (internal technical/security fix). This map links approved requirements (FR/NFR) to execution units.

## Functional Requirements Mapping

| Requirement | Unit | Notes |
|---|---|---|
| FR-1 Identity scope matrix | U2 | Implemented through runtime predicate and route dependency coverage |
| FR-2 Shared require_user_context dependency | U1 | Core shared dependency implementation |
| FR-3 Apply dependency to user-scoped memory endpoints | U2 | Router-level dependency application |
| FR-4 Plans CRUD predicate alignment | U2 | Full identity tuple propagation |
| FR-5 Sessions CRUD predicate alignment | U2 | Full identity tuple propagation |
| FR-6 Task context predicate + conflict alignment | U2 + U3 | Runtime predicates in U2; unique constraint alignment in U3 |
| FR-7 Plan context predicate + conflict alignment | U2 + U3 | Runtime predicates in U2; unique constraint alignment in U3 |
| FR-8 Working memory unique constraint migration | U3 | Alembic + model alignment |
| FR-9 Semantic unique index verification/alignment | U2 + U3 | Conflict-target updates in U2; index alignment migration in U3 |
| FR-10 Signature propagation across layers | U2 | API/service/CRUD contract propagation |
| FR-11 SQLAlchemy unique constraint alignment | U3 | Model and migration-level alignment |

## Non-Functional Requirements Mapping

| Requirement | Unit | Notes |
|---|---|---|
| NFR-1 Generic validation errors | U1 + U2 | Dependency message behavior + route enforcement |
| NFR-2 Admin endpoint backward compatibility | U2 | Explicit exemption from require_user_context |
| NFR-3 Migration safety | U3 | Upgrade/downgrade validation |
| NFR-4 No regression in existing tests | U2 + U3 | Additive tests with existing suite preservation |
| NFR-5 Extensible shared dependency design | U1 | Dependency interface design |
| NFR-6 RLS remains platform-only | U2 + U3 | Runtime/app-level enforcement without RLS policy scope changes |

## Acceptance Criteria Coverage by Unit

| Acceptance Criterion | Unit Ownership |
|---|---|
| Missing identity returns 400 | U1 + U2 |
| CRUD scope consistency | U2 |
| Working memory write/read scope consistency | U2 + U3 |
| Semantic upsert conflict/index parity | U2 + U3 |
| Shared dependency reusable by services | U1 |
| Migration reversible | U3 |
| Isolation/collision tests | U3 (primary), U2 (support) |
| Admin endpoints unaffected | U2 |

## Verification Focus by Unit

- **U1 verification**: dependency behavior and API contract
- **U2 verification**: runtime behavior and scope propagation
- **U3 verification**: schema/index correctness and high-value isolation tests
