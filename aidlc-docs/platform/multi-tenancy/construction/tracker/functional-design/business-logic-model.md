# Business Logic Model — U5: services/tracker
## Initiative: Multi-Tenancy Model Implementation
**Date**: 2026-03-23

---

## 1. Migration Logic

### Migration: tracker two-tier identity update

**Purpose**: Move tracker persistence from legacy tenant/user naming to three-dimensional identity with scoped uniqueness.

Execution order:

```text
Step 1: Rename columns
  - plan_progress.tenant_id -> service_tenant_id
  - plan_progress.user_id -> service_user_id
  - action_progress.tenant_id -> service_tenant_id
  - action_progress.user_id -> service_user_id

Step 2: Add platform_tenant_id VARCHAR(64) NOT NULL to both tables
  - initialize existing rows using DEFAULT_PLATFORM_TENANT_ID

Step 3: Enforce VARCHAR(64) for all identity columns
  - platform_tenant_id, service_tenant_id, service_user_id

Step 4: Drop legacy uniqueness/indexes
  - uq_plan_id
  - uq_action_tenant_action
  - idx_plan_tenant_plan
  - idx_action_tenant_action

Step 5: Recreate scoped uniqueness/indexes
  - uq_plan_scope_plan: (platform_tenant_id, service_tenant_id, plan_id)
  - uq_action_scope_action: (platform_tenant_id, service_tenant_id, action_id)
  - idx_plan_scope_plan
  - idx_action_scope_action

Step 6: Keep operational indexes
  - plan/action status and created timestamps
```

---

## 2. API Path Logic

### Input Extraction

Tracker query endpoints transition from direct header wiring to shared tenant context:
- use `TenantContext = Depends(get_tenant_context)`
- read:
  - `context.platform_tenant_id`
  - `context.service_tenant_id`
  - `context.service_user_id`

### Query Filtering Rule

All tracker reads use composite filtering:

```python
.where(Model.platform_tenant_id == context.platform_tenant_id)
.where(Model.service_tenant_id == context.service_tenant_id)
.where(Model.service_user_id == context.service_user_id)
```

This satisfies NFR composite-namespace isolation and blocks partial-key reads.

---

## 3. NATS/Event Path Logic

### Trust Boundary

- `platform_tenant_id` comes from `event.platform_tenant_id` injected by Event Service.
- `service_tenant_id` and `service_user_id` come from envelope tenant/user dimensions.

### Missing `platform_tenant_id` Behavior (Q1)

Decision: **fail closed**.

If `event.platform_tenant_id` is absent:
- reject event for persistence path
- emit structured warning log
- do not write tracker rows

No fallback to default tenant in NATS path.

### Session Activation

Before DB reads/writes in NATS handlers, call:
- `set_config_for_session(db, platform_tenant_id, service_tenant_id, service_user_id)`

This keeps parity with the tenancy session model and avoids bypassing tenant context assumptions.

---

## 4. Upsert/Update Logic

### Plan Upsert

When plan-state events arrive:
- upsert `plan_progress` by scoped key `(platform_tenant_id, service_tenant_id, plan_id)`
- initialize counters and timestamps when inserted
- update state/timestamps when existing

### Action Upsert

When action-requested events arrive:
- upsert `action_progress` by scoped key `(platform_tenant_id, service_tenant_id, action_id)`
- associate with `plan_id` when present
- update action status transitions on result events

### Counter Updates

`plan_progress` counters (`total_actions`, `completed_actions`, `failed_actions`) update only within the same scoped tenant key and `plan_id`.

---

## 5. Validation Logic (Q5)

Decision: Option A for this unit.

Enforcement model for current implementation:
- API layer validates required identity values are present where required.
- API layer validates string length <= 64 for the three identity dimensions.
- DB schema (`VARCHAR(64)`, NOT NULL where required) is final guardrail.
- IDs remain opaque: no UUID, prefix, or regex format validation.

Shared helper standardization is deferred to a follow-up refactor initiative.

---

## 6. GDPR Deletion Logic (Q4)

Decision: internal endpoint + service class.

`TrackerDataDeletion` executes in one transaction and supports:
- by platform tenant
- by service tenant within platform tenant
- by service user within platform + service tenant

Internal admin route exposes these operations for controlled operational use.

---

## 7. Error Handling Logic

### Fail-Closed Rules

- Missing `platform_tenant_id` in event path: reject persistence, log warning.
- Missing scoped IDs in API path: return validation error; do not query.
- Constraint violations (length/uniqueness): bubble as controlled API errors.

### Logging Requirements

Structured logs for rejected events include:
- event id
- event type
- missing identity dimension(s)
- correlation id / trace id when available

No sensitive payload dumping in logs.

---

## 8. Test Mapping

This business logic model maps directly to tracker inception test cases:
- TC-T-001: migration and schema constraints
- TC-T-002: TenantContext adoption
- TC-T-003: composite-key filtering
- TC-T-004: platform tenant extraction from event
- TC-T-005: `set_config_for_session` call ordering
- TC-T-006: deletion by platform tenant
- TC-T-007: max-length validation
- TC-T-008: null platform tenant fail-closed behavior
