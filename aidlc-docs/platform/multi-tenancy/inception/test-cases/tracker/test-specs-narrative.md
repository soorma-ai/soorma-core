# Test Specifications — Narrative
## Unit: tracker
## Initiative: Multi-Tenancy Model Implementation
## Scope: happy-path-negative
**Unit abbreviation**: T = tracker

---

### TC-T-001 — Alembic migration renames tenant_id/user_id and adds platform_tenant_id

**Context**: The Tracker Service column rename migration must be lossless — existing data (if any) is preserved, and the new column names align with the two-tier model. Covers FR-5.1, FR-5.2, FR-5.3, FR-5.5.

**Scenario description**: The Alembic migration is applied to a Tracker test database. The resulting schema is inspected.

**Steps**:
1. Apply the Tracker Alembic migration to a test database
2. Inspect `plan_progress` table columns
3. Inspect `action_progress` table columns

**Expected outcome**: Both tables have `service_tenant_id VARCHAR(64) NOT NULL`, `service_user_id VARCHAR(64) NOT NULL`, and `platform_tenant_id VARCHAR(64) NOT NULL`. The old `tenant_id` and `user_id` columns are gone.

**Scope tag**: happy-path
**Priority**: High
**Source**: tracker / FR-5.1, FR-5.2, FR-5.3, FR-5.5
**Construction artifacts**: aidlc-docs/platform/multi-tenancy/construction/tracker/

---

### TC-T-002 — TenantContext replaces per-route header parsing in Tracker API handlers

**Context**: The Tracker Service previously parsed `x_tenant_id: str = Header(...)` in each route directly. This must be replaced by a single `Depends(get_tenant_context)` from `soorma-service-common`. Covers FR-5.6.

**Scenario description**: The Tracker route handler source is inspected for direct `Header(...)` usage and for adoption of `get_tenant_context`.

**Steps**:
1. Inspect all Tracker API route handler signatures
2. Check for direct `Header(...)` parameters named `x_tenant_id`, `x_service_tenant_id`, or similar
3. Check for `Depends(get_tenant_context)` or `Depends(get_platform_tenant_id)` from `soorma_service_common`

**Expected outcome**: No direct `Header(...)` tenant-credential extraction in route signatures. All identity extraction uses `get_tenant_context` or the individual `get_*` dependency functions from `soorma_service_common`.

**Scope tag**: happy-path
**Priority**: High
**Source**: tracker / FR-5.6
**Construction artifacts**: aidlc-docs/platform/multi-tenancy/construction/tracker/

---

### TC-T-003 — Tracker API queries filter by all three identity dimensions

**Context**: Query endpoints must filter by `(platform_tenant_id, service_tenant_id, service_user_id)` — not just by `service_tenant_id`. This is the composite key enforcement. Covers FR-5.7.

**Scenario description**: Two plan progress records exist under different `platform_tenant_id` values but the same `service_tenant_id`. Querying with the first platform tenant's context returns only its records.

**Steps**:
1. Insert plan_progress row: `(platform_tenant_id=spt_1, service_tenant_id=st1, service_user_id=user1)`
2. Insert plan_progress row: `(platform_tenant_id=spt_2, service_tenant_id=st1, service_user_id=user1)`
3. Query via API with `X-Tenant-ID: spt_1`, `X-Service-Tenant-ID: st1`, `X-User-ID: user1`

**Expected outcome**: Only the record for `spt_1` is returned. The record for `spt_2` is not visible.

**Scope tag**: happy-path
**Priority**: High
**Source**: tracker / FR-5.7, NFR-1.3
**Construction artifacts**: aidlc-docs/platform/multi-tenancy/construction/tracker/

---

### TC-T-004 — NATS event handler extracts platform_tenant_id from event.platform_tenant_id

**Context**: The Tracker's NATS-path must trust `event.platform_tenant_id` (set by the Event Service) rather than reading it from headers (no HTTP context in NATS path). Covers FR-6.7, FR-5.6.

**Scenario description**: A NATS event arrives with `platform_tenant_id="spt_from_event_service"` in the `EventEnvelope`. The Tracker handler stores the plan progress row using this value for `platform_tenant_id`.

**Steps**:
1. Simulate a NATS event delivery to the Tracker handler with `EventEnvelope.platform_tenant_id="spt_from_event_service"`, `tenant_id="st1"`, `user_id="user1"`
2. Observe the plan_progress row created

**Expected outcome**: `plan_progress.platform_tenant_id = "spt_from_event_service"`, `service_tenant_id = "st1"`, `service_user_id = "user1"`.

**Scope tag**: happy-path
**Priority**: High
**Source**: tracker / FR-6.7, FR-5.6
**Construction artifacts**: aidlc-docs/platform/multi-tenancy/construction/tracker/

---

### TC-T-005 — set_config_for_session called before DB query in NATS event handler

**Context**: The NATS path has no HTTP request, so it must call `set_config_for_session` manually before any DB interaction to ensure correct session state. Covers FR-3a.3 (NATS path for Tracker).

**Scenario description**: A NATS event handler is triggered. The test instrument confirms `set_config_for_session` is called with the identity from the event envelope before any DB write.

**Steps**:
1. Mock/spy on `set_config_for_session` from `soorma_service_common`
2. Trigger the Tracker NATS event handler with a test event
3. Check that `set_config_for_session` was called with the event's identity values

**Expected outcome**: `set_config_for_session(db, platform_tenant_id=..., service_tenant_id=..., service_user_id=...)` was called before the database INSERT for plan progress.

**Scope tag**: happy-path
**Priority**: High
**Source**: tracker / FR-5.6, FR-3a.3
**Construction artifacts**: aidlc-docs/platform/multi-tenancy/construction/tracker/

---

### TC-T-006 — TrackerDataDeletion.delete_by_platform_tenant removes all rows from both tables

**Context**: The GDPR deletion interface must cover both `plan_progress` and `action_progress`. Covers FR-5.8.

**Scenario description**: Rows are inserted into both tables under a specific `platform_tenant_id`. The deletion method is called and all rows for that tenant are removed.

**Steps**:
1. Insert rows into `plan_progress` and `action_progress` with `platform_tenant_id="spt_delete_tracker"`
2. Call `TrackerDataDeletion.delete_by_platform_tenant(platform_tenant_id="spt_delete_tracker")`
3. Query both tables for rows with that `platform_tenant_id`

**Expected outcome**: Both tables return zero rows for `spt_delete_tracker`. Other tenants' rows unaffected.

**Scope tag**: happy-path
**Priority**: High
**Source**: tracker / FR-5.8
**Construction artifacts**: aidlc-docs/platform/multi-tenancy/construction/tracker/

---

### TC-T-007 — Tracker API rejects request with service_tenant_id exceeding 64 chars

**Context**: Negative case: the 64-character length constraint (NFR-3.1) must be enforced for tracker columns too.

**Scenario description**: A Tracker API request is sent with `X-Service-Tenant-ID` containing 65 characters.

**Steps**:
1. Send a GET plan progress request with `X-Service-Tenant-ID: {"a" * 65}` to the Tracker API

**Expected outcome**: HTTP 422 or a database constraint violation. No data is stored or queried with the oversized value.

**Scope tag**: happy-path-negative
**Priority**: High
**Source**: tracker / NFR-3.1
**Construction artifacts**: aidlc-docs/platform/multi-tenancy/construction/tracker/

---

### TC-T-008 — NATS event without platform_tenant_id does not create a row with empty/null identity

**Context**: Negative case: if a NATS event arrives with `platform_tenant_id=None` (e.g., published by old SDK before Event Service injection is deployed), the Tracker must not create a tracker row with an invalid/empty platform tenant ID. Covers FR-6.7 (trust model).

**Scenario description**: A NATS event arrives with `EventEnvelope.platform_tenant_id=None`. The Tracker handler must either use the default or reject the event — it must not write `None` to the database.

**Steps**:
1. Construct event with `platform_tenant_id=None`
2. Trigger the Tracker NATS handler with this event

**Expected outcome**: Either `DEFAULT_PLATFORM_TENANT_ID` is used (fallback) or the event is rejected with a logged warning. No DB row with `platform_tenant_id=NULL` is created.

**Scope tag**: happy-path-negative
**Priority**: High
**Source**: tracker / FR-6.7
**Construction artifacts**: aidlc-docs/platform/multi-tenancy/construction/tracker/
