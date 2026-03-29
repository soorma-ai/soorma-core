# Requirements: Memory Service Identity-Scope Consistency Fix

## Intent Analysis

- **User Request**: Fix identity-scope inconsistencies across Memory Service — ingress validation, CRUD predicate alignment, working memory unique constraint, and shared user-identity enforcement utility.
- **Request Type**: Bug Fix / Security Enhancement
- **Scope**: `libs/soorma-service-common` (new shared dependency) + `services/memory` (validation, CRUD, migration, tests)
- **Complexity**: Moderate-Complex — spans DB schema migration, shared library change, API validation layer, and CRUD predicate alignment across 7 resource types.

---

## Scope Decision (Authoritative)

**Chosen Model**: **Option A — Full User-Scoped**, applied uniformly to ALL memory resource types including `task_context` and `plan_context`.

**Rationale**: The Soorma two-tier tenancy model guarantees that every interaction carries a concrete `service_user_id` — including automation, triggers, and machine-initiated tasks (which use machine user identities, e.g., `agent-scheduler`). This architectural guarantee eliminates the Worker-to-Worker handoff risk that would make Option B necessary. A uniform user-scope model provides: no exceptions table to maintain, stronger audit attribution, and fail-fast detection of identity propagation bugs.

---

## Functional Requirements

### FR-1: Authoritative Identity Scope Matrix

**Requirement**: Define and document a canonical "user required vs optional" matrix for all Memory Service endpoints/operations.

| Resource | Operations | `service_user_id` Required |
|---|---|---|
| Semantic memory | upsert, query, search | Yes |
| Episodic memory | create, get, list, delete | Yes |
| Procedural memory | create, get, list, delete | Yes |
| Working memory | set, get, delete-key, delete-plan | Yes |
| Plans | create, get, list, update, delete | Yes |
| Sessions | create, get, list, update, delete | Yes |
| Task context | upsert, get, update, delete | Yes |
| Plan context | upsert, get, update, delete | Yes |
| Admin | (system management) | No — explicitly tenant-scoped only |

---

### FR-2: Shared `require_user_context` FastAPI Dependency

**Requirement**: Add a new FastAPI dependency to `libs/soorma-service-common` that validates both `service_tenant_id` AND `service_user_id` are present on the request context.

**Rationale**: `service_user_id` alone is not globally unique — it is only unique within a `service_tenant_id`. Both dimensions must be present together for any user-scoped operation to be unambiguous.

**Behaviour**:
- Returns `HTTP 400 Bad Request` if `context.service_tenant_id` is `None` or empty string
- Returns `HTTP 400 Bad Request` if `context.service_user_id` is `None` or empty string
- Both checks are applied; either missing is a `400`
- Error response body MUST use a **generic message** that does not expose internal implementation details (e.g., no mention of `X-User-ID` / `X-Service-Tenant-ID` headers, as the authentication mechanism may change in v0.8.0+)
  - Example acceptable body: `{"detail": "Missing required user identity context"}`
- Does NOT raise when both `service_tenant_id` and `service_user_id` are present
- Pattern: new `Depends()`-compatible function or dependency class

**Design Constraints**:
- Must be a standalone, reusable dependency — other services (tracker, registry, etc.) can import and apply it without modification
- Signature must be designed with extensibility in mind (e.g., future `require_role` or similar enrichment should be addable without breaking callers)
- Applied via `Depends()` in route handlers or router-level dependencies — not embedded in middleware or service layer

---

### FR-3: Apply `require_user_context` to All User-Scoped Memory Endpoints

**Requirement**: All Memory Service endpoints in the FR-1 matrix marked "Yes" must use the new `require_user_context` dependency, enforcing that both `service_tenant_id` and `service_user_id` are present.

**Affected routers**: semantic, episodic, procedural, working, plans, sessions, task_context, plan_context.

**Not affected**: admin router — it is explicitly tenant-scoped.

---

### FR-4: Plans CRUD Predicate Alignment

**Requirement**: All plan CRUD operations — `list_plans`, `get_plan`, `update_plan`, and `delete_plan` in `crud/plans.py` — must filter on the full three-column identity. Currently `list_plans` filters on `platform_tenant_id + service_user_id` only (missing `service_tenant_id`), and `get_plan`/`update_plan`/`delete_plan` filter on `platform_tenant_id + plan_id` only (missing both `service_tenant_id` and `service_user_id`).

**After (all operations)**: `WHERE platform_tenant_id = ? AND service_tenant_id = ? AND service_user_id = ? AND plan_id = ?` (or omit `plan_id` for `list_plans`)

All four operation signatures must accept `service_tenant_id` as a required parameter.

---

### FR-5: Sessions CRUD Predicate Alignment

**Requirement**: All session CRUD operations — `list_sessions`, `get_session`, `update_session_interaction`, and `delete_session` in `crud/sessions.py` — must filter on the full three-column identity. Currently `list_sessions` filters on `platform_tenant_id + service_user_id` only (missing `service_tenant_id`), and `get_session`/`update_session_interaction`/`delete_session` filter on `platform_tenant_id + session_id` only (missing both `service_tenant_id` and `service_user_id`).

**After (all operations)**: `WHERE platform_tenant_id = ? AND service_tenant_id = ? AND service_user_id = ? AND session_id = ?` (or omit `session_id` for `list_sessions`)

All four operation signatures must accept `service_tenant_id` as a required parameter.

---

### FR-6: Task Context CRUD Predicate Alignment

**Requirement**: `get_task_context`, `update_task_context`, and `delete_task_context` in `crud/task_context.py` currently filter on `platform_tenant_id + task_id` only. Add `service_tenant_id` and `service_user_id` as filter predicates.

The existing upsert already stores `service_user_id` (and `service_tenant_id`). Update the upsert conflict target from `(platform_tenant_id, task_id)` to `(platform_tenant_id, service_tenant_id, service_user_id, task_id)`.

**Before**: `WHERE platform_tenant_id = ? AND task_id = ?`  
**After**: `WHERE platform_tenant_id = ? AND service_tenant_id = ? AND service_user_id = ? AND task_id = ?`

**All operation signatures** must be updated to accept both `service_tenant_id` and `service_user_id` as required parameters (not optional).

---

### FR-7: Plan Context CRUD Predicate Alignment

**Requirement**: `get_plan_context`, `update_plan_context`, `delete_plan_context`, and `upsert_plan_context` in `crud/plan_context.py` currently have no `service_user_id` parameter and no `service_tenant_id` filter. Add both `service_tenant_id` and `service_user_id` as required parameters and include them in all filter predicates and the upsert values.

**Before**: `WHERE platform_tenant_id = ? AND plan_id = ?`  
**After**: `WHERE platform_tenant_id = ? AND service_tenant_id = ? AND service_user_id = ? AND plan_id = ?`

Update the upsert conflict target from `['plan_id']` to `['platform_tenant_id', 'service_tenant_id', 'service_user_id', 'plan_id']`.

---

### FR-8: Working Memory Unique Constraint Migration

**Requirement**: The `working_memory` table unique constraint currently covers `(plan_id, key)` only, which allows cross-user overwrite when two users share the same `plan_id` and `key`. Replace this constraint with a user-scoped constraint.

**New constraint**: `UNIQUE (platform_tenant_id, service_tenant_id, service_user_id, plan_id, key)`

**Migration strategy** (write-only, no backfill):
- Drop the existing `plan_key_unique` constraint
- Create the new `(platform_tenant_id, service_tenant_id, service_user_id, plan_id, key)` unique constraint
- Existing records are NOT backfilled — this is development data with no production user data at risk
- The `ON CONFLICT` target in `crud/working.py` `set_working_memory` must be updated to reference the new constraint

---

### FR-9: Semantic Memory Partial Index Verification

**Requirement**: Verify that all `ON CONFLICT` targets in `crud/semantic.py` `upsert_semantic_memory` correspond to actual partial unique indexes on the `semantic_memory` table. Under the three-column identity model, the private-scoped indexes must include `service_tenant_id` alongside `service_user_id` to ensure uniqueness is scoped correctly. Confirm all four indexes exist as specified:

| Scenario | Index columns | Partial WHERE clause |
|---|---|---|
| Private + external_id | `(platform_tenant_id, service_tenant_id, service_user_id, external_id)` | `external_id IS NOT NULL AND is_public = FALSE` |
| Public + external_id | `(platform_tenant_id, external_id)` | `external_id IS NOT NULL AND is_public = TRUE` |
| Private + content_hash | `(platform_tenant_id, service_tenant_id, service_user_id, content_hash)` | `is_public = FALSE` |
| Public + content_hash | `(platform_tenant_id, content_hash)` | `is_public = TRUE` |

If any index is missing or mismatched, add a corrective migration. Update `conflict_target` lists in `upsert_semantic_memory` to match.

---

### FR-10: CRUD Signature Propagation Through Service and API Layers

**Requirement**: All service layer functions (`services/working_memory_service.py`, etc.) and API route handlers that call updated CRUD functions must propagate `service_tenant_id` and `service_user_id` through their call chains. No call site should silently drop either parameter.

---

### FR-11: SQLAlchemy Model Unique Constraint Alignment

**Requirement**: Several model `__table_args__` unique constraints are stale relative to the three-column identity model. Update them to match the new predicate and conflict-target definitions:

| Table | Current constraint | Updated constraint |
|---|---|---|
| `working_memory` | `UNIQUE(plan_id, key)` | `UNIQUE(platform_tenant_id, service_tenant_id, service_user_id, plan_id, key)` |
| `task_context` | `UNIQUE(platform_tenant_id, task_id)` | `UNIQUE(platform_tenant_id, service_tenant_id, service_user_id, task_id)` |
| `plan_context` | `UNIQUE(plan_id)` | `UNIQUE(platform_tenant_id, service_tenant_id, service_user_id, plan_id)` |
| `plans` | `UNIQUE(platform_tenant_id, plan_id)` | No change — `plan_id` is a UUID; collision across users is impossible |
| `sessions` | `UNIQUE(platform_tenant_id, session_id)` | No change — `session_id` is a UUID; collision across users is impossible |

Model changes must be accompanied by corresponding Alembic migrations where not already covered by FR-6, FR-7, and FR-8.

---

## Non-Functional Requirements

### NFR-1: Generic Error Messages for Identity Validation

The `require_user_context` dependency MUST return error messages that do not expose internal transport mechanism details. Error bodies must not reference `X-User-ID`, `X-Service-Tenant-ID`, or any header/session/auth-layer internals. This requirement exists to future-proof the error surface for the v0.8.0+ API Key / JWT transition.

### NFR-2: Backwards Compatibility for Admin Endpoints

Admin endpoints (`api/v1/admin.py`) must NOT be affected by the `require_user_id` dependency. They are explicitly system-scoped and must continue to function without a `service_user_id`.

### NFR-3: Migration Safety

The working memory constraint migration must be written as a standard Alembic revision with proper `upgrade()` and `downgrade()` functions. Downgrade must restore the original `plan_key_unique` constraint to allow safe rollback.

### NFR-4: No Regression in Existing Tests

All existing tests that currently pass must continue to pass. New tests are additive — they do not replace existing coverage.

### NFR-5: Extensible Shared Dependency Design

The `require_user_id` dependency in `soorma-service-common` must be designed so that future enhancements (e.g., `require_role`, `require_service_tenant`) can be added without breaking existing callers.
### NFR-6: RLS Scope Is Platform Tenant Only — By Design

Row Level Security policies on all 8 memory tables enforce `platform_tenant_id` isolation only. Service tenant and user isolation are application-layer concerns (CRUD predicates). This boundary is intentional:
- RLS cannot express the "user required vs optional" distinction per endpoint that the application needs
- Adding `service_tenant_id`/`service_user_id` to RLS policies would block legitimate system-level (admin) access with no override path
- This fix does **not** change RLS policies — it strengthens the application layer above RLS
---

## Out of Scope

- JWT / API Key authentication rollout (tracked separately as v0.8.0+)
- Non-memory services (changes to soorma-service-common only — no changes to registry, tracker, event-service routes)
- Large schema redesign beyond scope-alignment and the working memory constraint fix
- Semantic memory embedding model versioning or caching optimisation

---

## Acceptance Criteria

1. No private write path succeeds without both `service_tenant_id` and `service_user_id` — all user-scoped endpoints return `400` when either is absent.
2. CRUD scope is consistent per resource: create / get / list / update / delete all filter on the same identity dimensions.
3. Working memory write and read/delete scope match — cross-user overwrite is impossible at the database constraint level.
4. Semantic upsert `ON CONFLICT` targets match existing partial unique indexes.
5. The new `require_user_context` dependency is in `soorma-service-common`, validates both `service_tenant_id` and `service_user_id`, and is usable by any service.
6. Alembic migration for working memory constraint is reversible (upgrade + downgrade).
7. Tests cover: missing user `400` response, missing service tenant `400` response, cross-user read isolation, cross-user write collision prevention, deterministic upsert under 3-column identity.
8. Admin endpoints are unaffected.
