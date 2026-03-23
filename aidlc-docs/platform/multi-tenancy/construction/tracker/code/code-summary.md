# Code Summary — U5: services/tracker
## Initiative: Multi-Tenancy Model Implementation
**Completed**: 2026-03-23T15:06:09Z
**Unit**: U5 — `services/tracker` (Wave 3)
**Tests**: 21/21 pass

---

## Overview

Tracker Service upgraded from legacy two-column identity (`tenant_id`, `user_id`) to three-dimensional tenancy model (`platform_tenant_id`, `service_tenant_id`, `service_user_id`) — consistent with soorma-service-common patterns established in U2.

---

## Files Changed

### Modified
| File | Change Summary |
|------|---------------|
| `services/tracker/src/tracker_service/models/db.py` | Replaced `tenant_id`/`user_id` with three-dim identity columns; scoped uniqueness + composite FK via `__table_args__` |
| `services/tracker/src/tracker_service/main.py` | Registered `TenancyMiddleware`; switched to consolidated `v1_router` |
| `services/tracker/src/tracker_service/core/config.py` | Replaced `default_tenant_id`/`default_user_id` with `default_platform_tenant_id`, `default_service_tenant_id`, `default_service_user_id` |
| `services/tracker/src/tracker_service/api/v1/__init__.py` | Created `v1_router` aggregating query + admin routers under `/v1` prefix |
| `services/tracker/src/tracker_service/api/v1/query.py` | `TenantContext = Depends(get_tenant_context)` replaces raw header parsing; three-dim WHERE filters; `_validate_identity_dimensions()` enforces presence + ≤64 chars |
| `services/tracker/src/tracker_service/subscribers/event_handlers.py` | `_extract_identity_dimensions()` replaces `_extract_tenant_user()`; fail-closed on missing `platform_tenant_id`; `set_config_for_session()` added before DB ops; scoped upsert conflict targets |
| `services/tracker/pyproject.toml` | Added `soorma-service-common` dependency |
| `services/tracker/tests/conftest.py` | Overrides both `get_db` and `get_tenant_context`; header-based fixture bypasses PostgreSQL `set_config` for SQLite tests |
| `services/tracker/tests/test_query_api.py` | Fixtures use three-dim identity; `X-Service-Tenant-ID` header added to all calls |
| `services/tracker/tests/test_subscribers.py` | Fully rewritten: `_base_event()` helper with `platform_tenant_id`; fail-closed test; `_extract_identity_dimensions` tests |
| `services/tracker/tests/test_main.py` | Version assertion + settings field names updated |

### Created
| File | Purpose |
|------|---------|
| `services/tracker/src/tracker_service/core/dependencies.py` | Tracker-local `get_tenanted_db` and `get_tenant_context` bindings (mirrors memory service pattern) |
| `services/tracker/src/tracker_service/api/v1/admin.py` | Internal GDPR deletion endpoints: `/admin/platform/{ptid}`, `/admin/tenant/{ptid}/{stid}`, `/admin/user/{ptid}/{stid}/{suid}` |
| `services/tracker/src/tracker_service/services/__init__.py` | Services package marker |
| `services/tracker/src/tracker_service/services/data_deletion.py` | `TrackerDataDeletion(PlatformTenantDataDeletion)` covering `ActionProgress` + `PlanProgress` |
| `services/tracker/alembic/versions/20260323_0712_f7a1c2b9d1e0_tracker_three_dimensional_tenancy.py` | Alembic migration: rename identity columns, add `platform_tenant_id`, update constraints/indexes/FK |

---

## Key Design Decisions

### Three-Dimensional Identity
- `platform_tenant_id` VARCHAR(64) NOT NULL — authoritative platform dimension from `event.platform_tenant_id`
- `service_tenant_id` VARCHAR(64) NOT NULL — maps from `event.tenant_id`
- `service_user_id` VARCHAR(64) NOT NULL — maps from `event.user_id`

### Scoped Uniqueness
- `plan_progress`: `(platform_tenant_id, service_tenant_id, plan_id)`
- `action_progress`: `(platform_tenant_id, service_tenant_id, action_id)`

### Fail-Closed (BR-U5-08)
`_extract_identity_dimensions(event)` raises `ValueError("event.platform_tenant_id is required")` if `event.platform_tenant_id` is falsy — no silent data corruption.

### Guard-Before-Extract Ordering
In `handle_action_request`, the `if not plan_id: return` guard fires **before** `_extract_identity_dimensions()` and `set_config_for_session()` — no DB calls for unplanned events.

### Admin Deletion Endpoints
Internal GDPR endpoints use bare `get_db` (no tenant context) — isolation is enforced by the deletion service itself using explicit tenant filters.

---

## Business Rules Implemented
- BR-U5-01 — Three-column identity in both tables
- BR-U5-02 — Scoped uniqueness on plan/action within platform+service tenant
- BR-U5-03 — `platform_tenant_id` from `event.platform_tenant_id`
- BR-U5-04 — `service_tenant_id` from `event.tenant_id`
- BR-U5-05 — `service_user_id` from `event.user_id`
- BR-U5-06 — All three columns required, no nullable
- BR-U5-07 — Max length 64 for all identity columns
- BR-U5-08 — Fail closed on missing `platform_tenant_id`
- BR-U5-09 — Composite FK `action_progress → plan_progress`
- BR-U5-10 — Internal admin deletion endpoints

## Test Coverage
- TC-T-001: Schema/constraints validated via ORM + migration
- TC-T-002: Query API tenant-context dependency
- TC-T-003: Composite filtering in queries
- TC-T-004: Event subscriber identity extraction
- TC-T-005: `set_config_for_session` ordering (guard-before-extract)
- TC-T-006: Admin deletion endpoints exist and route correctly
- TC-T-007: Max-length validation in API layer
- TC-T-008: Fail-closed on missing `platform_tenant_id`
