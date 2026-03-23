# Business Rules — U5: services/tracker
## Initiative: Multi-Tenancy Model Implementation
**Date**: 2026-03-23

---

## BR-U5-01: Composite tenant key is mandatory for all tracker reads/writes

**Rule**: Tracker operations MUST scope by `platform_tenant_id` + `service_tenant_id`, with `service_user_id` included for user-scoped queries.

**Rationale**: Service tenant/user IDs are not globally unique. Partial-key filtering can cause cross-namespace leakage.

**Enforcement**: Query and update statements include scoped identity predicates; no lookups by `plan_id` or `action_id` alone.

---

## BR-U5-02: `service_user_id` nullability remains unchanged from current model intent

**Rule**: Keep `service_user_id` required (`NOT NULL`) for both tracker tables in this migration.

**Rationale**: Existing model already treats user identity as required for progress tracking. Changing nullability now adds semantic drift and testing risk.

**Enforcement**: Schema NOT NULL + API/event path validation on write.

---

## BR-U5-03: Scoped uniqueness replaces legacy global uniqueness assumptions

**Rule**:
- `plan_progress` uniqueness: `(platform_tenant_id, service_tenant_id, plan_id)`
- `action_progress` uniqueness: `(platform_tenant_id, service_tenant_id, action_id)`

`service_user_id` is indexed for filtering but not required in uniqueness constraints by default.

**Rationale**: Preserves domain business keys (`plan_id`, `action_id`) while ensuring tenant-namespace isolation and avoiding unnecessary write contention.

---

## BR-U5-04: Event path fails closed when `platform_tenant_id` is missing

**Rule**: NATS handlers MUST reject persistence if `event.platform_tenant_id` is absent.

**Rationale**: Tracker trusts Event Service to inject authoritative platform tenant context. Missing context is a security and correctness failure.

**Enforcement**: Do not insert/update rows; emit structured warning log with correlation metadata.

---

## BR-U5-05: Event path must activate tenancy session variables before DB queries

**Rule**: NATS handlers call `set_config_for_session` prior to any DB query/update in handler scope.

**Rationale**: Keeps tenancy context explicit and consistent across API and event paths.

**Enforcement**: First DB-adjacent operation in handler is tenancy activation.

---

## BR-U5-06: API validation is minimal and opaque-ID friendly

**Rule**: For this unit, enforce only:
- required/non-empty IDs where required
- max length 64 for `platform_tenant_id`, `service_tenant_id`, `service_user_id`

No regex/prefix/UUID validation.

**Rationale**: Best devex tradeoff: clear failures with low friction, while respecting opaque identifier design.

**Note**: shared-helper standardization is deferred to a dedicated follow-up refactor.

---

## BR-U5-07: Internal deletion endpoint is allowed; public deletion endpoint is out of scope

**Rule**: Implement `TrackerDataDeletion` and internal admin route(s) only.

**Rationale**: Keeps parity with Memory service operational pattern and avoids exposing destructive APIs publicly in this unit.

**Enforcement**: Internal route namespace + service layer transactional deletes.

---

## BR-U5-08: Direct header parsing in tracker query routes is replaced by shared context dependency

**Rule**: Tracker API routes should use `TenantContext`/`get_tenant_context` from shared service-common wiring rather than repeated `Header(...)` identity extraction.

**Rationale**: Centralizes tenancy behavior and avoids drift between services.

**Enforcement**: Route signatures consume context dependency; identities flow from middleware-populated request state.

---

## BR-U5-09: Logging must support troubleshooting without leaking sensitive payloads

**Rule**: Log identity-validation and missing-context failures with metadata only; avoid raw payload dumping.

**Rationale**: Security baseline and operability: enough context for debugging without exposing sensitive content.

**Enforcement**: Structured warning/error logs with event id/type, correlation id, and missing fields.

---

## BR-U5-10: Backward compatibility posture is breaking-but-controlled

**Rule**: Migration may invalidate existing pre-production tracker data assumptions. This is acceptable for this initiative.

**Rationale**: Requirements explicitly mark this as a breaking pre-production change; correctness of new tenancy model is prioritized.

**Enforcement**: Tests updated to new identity fields and constraints; old field names removed from active code paths.
