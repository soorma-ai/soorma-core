# Code Generation Plan — U5: services/tracker
## Initiative: Multi-Tenancy Model Implementation
**Date**: 2026-03-23
**Unit**: U5 — `services/tracker` (Wave 3)
**Depends On**: U1 (`libs/soorma-common` ✅), U2 (`libs/soorma-service-common` ✅)
**Change Type**: Moderate

---

## Unit Context

Tracker transitions from legacy identity fields (`tenant_id`, `user_id`) to the three-column model:
- `platform_tenant_id`
- `service_tenant_id`
- `service_user_id`

Functional Design rules in force: BR-U5-01 through BR-U5-10.

Key U5 decisions to implement:
- Fail closed in NATS path if `event.platform_tenant_id` missing
- Keep `service_user_id` required
- Scoped uniqueness:
  - `plan_progress`: `(platform_tenant_id, service_tenant_id, plan_id)`
  - `action_progress`: `(platform_tenant_id, service_tenant_id, action_id)`
- Internal admin deletion endpoint included
- Validation model: minimal local enforcement in tracker (presence + max length 64 + DB constraints)

---

## Part 1 — Planning Status

- [x] Step 1 — Analyze unit design artifacts and tracker test mappings
- [x] Step 2 — Identify exact code locations to modify/create
- [x] Step 3 — Define executable step sequence with story/test traceability
- [x] Step 4 — Create this code-generation plan document
- [x] Step 5 — Summarize plan for user review
- [x] Step 6 — Log approval prompt in audit.md
- [ ] Step 7 — Wait for explicit user approval to execute code generation
- [ ] Step 8 — Record user approval in audit.md
- [ ] Step 9 — Update aidlc-state.md for generation execution start

---

## Planned Execution Steps (Part 2 — after approval)

### Group 1: Migrations and Models

- [ ] Step 10 — Create new Alembic migration in `services/tracker/alembic/versions/` for:
  - `tenant_id -> service_tenant_id`
  - `user_id -> service_user_id`
  - add `platform_tenant_id VARCHAR(64) NOT NULL`
  - enforce `VARCHAR(64)` length on all three identity columns
- [ ] Step 11 — Update uniqueness/indexes in migration:
  - drop `uq_plan_id`, create scoped plan uniqueness
  - drop `uq_action_tenant_action`, create scoped action uniqueness
  - replace tenant-scoped indexes with scope-aware indexes
- [ ] Step 12 — Update ORM in `services/tracker/src/tracker_service/models/db.py`:
  - renamed fields
  - new platform tenant field
  - updated constraints/indexes
  - keep `service_user_id` required

### Group 2: App Wiring and Dependencies

- [ ] Step 13 — Update `services/tracker/src/tracker_service/main.py`:
  - register `TenancyMiddleware` from `soorma_service_common`
- [ ] Step 14 — Update `services/tracker/src/tracker_service/core/config.py` defaults:
  - default platform tenant constant alignment
  - remove stale legacy defaults if no longer used

### Group 3: API Query Layer

- [ ] Step 15 — Refactor `services/tracker/src/tracker_service/api/v1/query.py`:
  - replace direct header parsing with shared tenant context dependency
  - enforce max length 64 validation on identity dims at API layer
  - apply composite filtering in all selects

### Group 4: Event Subscriber Path

- [ ] Step 16 — Refactor `services/tracker/src/tracker_service/subscribers/event_handlers.py`:
  - use `event.platform_tenant_id` as authoritative platform dimension
  - fail closed if missing platform tenant
  - map envelope tenant/user to service tenant/user fields
- [ ] Step 17 — Ensure NATS DB path calls `set_config_for_session` before queries/updates
- [ ] Step 18 — Update upsert conflict targets to new scoped uniqueness keys

### Group 5: GDPR Deletion

- [ ] Step 19 — Create `services/tracker/src/tracker_service/services/data_deletion.py`:
  - implement `TrackerDataDeletion(PlatformTenantDataDeletion)`
  - support delete by platform tenant/service tenant/service user
- [ ] Step 20 — Create internal admin route `services/tracker/src/tracker_service/api/v1/admin.py`:
  - internal delete endpoints mirroring memory service operational pattern
- [ ] Step 21 — Register admin routes in `services/tracker/src/tracker_service/api/v1/__init__.py`

### Group 6: Tests

- [ ] Step 22 — Update `services/tracker/tests/conftest.py` fixtures for new identity fields
- [ ] Step 23 — Update `services/tracker/tests/test_query_api.py` for tenant-context dependency and composite filters
- [ ] Step 24 — Update `services/tracker/tests/test_subscribers.py` for fail-closed missing `platform_tenant_id`
- [ ] Step 25 — Update `services/tracker/tests/test_nats_subscribers.py` for `set_config_for_session` ordering and scoped upserts
- [ ] Step 26 — Add/extend tests for migration constraints and max-length validation (TC-T-001, TC-T-007)
- [ ] Step 27 — Add/extend tests for deletion behavior (TC-T-006)

### Group 7: Documentation and Changelog

- [ ] Step 28 — Update tracker unit code summary at `aidlc-docs/platform/multi-tenancy/construction/tracker/code/code-summary.md`
- [ ] Step 29 — Update tracker changelog entry in `services/tracker/CHANGELOG.md`

### Group 8: Progress and Quality Gates

- [ ] Step 30 — Mark completed plan checkboxes during execution (in this file)
- [ ] Step 31 — Update `aidlc-state.md` for U5 Code Generation progress
- [ ] Step 32 — Ensure artifacts are ready for QA enrichment and design PR checkpoint sequencing

---

## Stories / Test Traceability

- FR-5.1..5.8 and FR-6.7 map to Steps 10-21
- NFR-1.3 and NFR-3.1 map to Steps 12, 15, 16, 22-27
- Tracker test cases covered:
  - TC-T-001: Steps 10-12, 26
  - TC-T-002: Step 15
  - TC-T-003: Steps 12, 15
  - TC-T-004: Step 16
  - TC-T-005: Step 17
  - TC-T-006: Steps 19-21, 27
  - TC-T-007: Steps 15, 26
  - TC-T-008: Step 16, 24
