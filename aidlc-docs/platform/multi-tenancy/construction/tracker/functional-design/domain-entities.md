# Domain Entities — U5: services/tracker
## Initiative: Multi-Tenancy Model Implementation
**Date**: 2026-03-23

---

## Overview

This document defines the Tracker Service entity changes for two-tier multi-tenancy. Both tracker tables move from legacy two-column identity (`tenant_id`, `user_id`) to three-column identity (`platform_tenant_id`, `service_tenant_id`, `service_user_id`) with string IDs capped at 64 characters.

Primary entity business keys remain:
- `plan_progress`: `plan_id`
- `action_progress`: `action_id`

---

## Updated Entity: `PlanProgress`

**Table**: `plan_progress`

### Identity Columns

**Before**:
```python
tenant_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
user_id: Mapped[str] = mapped_column(String(255), nullable=False)
```

**After**:
```python
platform_tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
service_tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
service_user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
```

### Business Identifier
- `plan_id` remains a string identifier (`String(255)`) and is tenant-scoped under the new composite namespace.

### Constraint/Index Strategy
- Replace global uniqueness on `plan_id` with composite uniqueness:
  - `UniqueConstraint("platform_tenant_id", "service_tenant_id", "plan_id", name="uq_plan_scope_plan")`
- Add lookup index for API and event-path reads:
  - `Index("idx_plan_scope_plan", "platform_tenant_id", "service_tenant_id", "plan_id")`
- Keep status/time indexes for reporting:
  - `idx_plan_status`, `idx_plan_created`

---

## Updated Entity: `ActionProgress`

**Table**: `action_progress`

### Identity Columns

**Before**:
```python
tenant_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
user_id: Mapped[str] = mapped_column(String(255), nullable=False)
```

**After**:
```python
platform_tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
service_tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
service_user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
```

### Business Identifier
- `action_id` remains a string identifier (`String(255)`) and is tenant-scoped under the new composite namespace.

### Constraint/Index Strategy
- Replace legacy uniqueness on `(tenant_id, action_id)` with:
  - `UniqueConstraint("platform_tenant_id", "service_tenant_id", "action_id", name="uq_action_scope_action")`
- Add lookup index for status updates and reads:
  - `Index("idx_action_scope_action", "platform_tenant_id", "service_tenant_id", "action_id")`
- Keep plan/status/time indexes:
  - `idx_action_plan`, `idx_action_status`, `idx_action_created`

### Note on `service_user_id`
- `service_user_id` is indexed for filtering and reporting.
- It is not part of default uniqueness to avoid over-constraining writes unless product behavior later requires per-user duplicate `action_id` support.

---

## Relationship Model

- `ActionProgress.plan_id` remains FK-like linkage to `PlanProgress.plan_id` with cascade behavior.
- Logical ownership is now scoped by composite tenant dimensions:
  - `(platform_tenant_id, service_tenant_id)` on both entities must align for related rows.

---

## New Service Entity: `TrackerDataDeletion`

**Module**: `tracker_service/services/data_deletion.py`

Concrete implementation of `PlatformTenantDataDeletion` for Tracker tables:

- `delete_by_platform_tenant(db, platform_tenant_id)`
- `delete_by_service_tenant(db, platform_tenant_id, service_tenant_id)`
- `delete_by_service_user(db, platform_tenant_id, service_tenant_id, service_user_id)`

Coverage:
- `plan_progress`
- `action_progress`

API exposure decision for this unit:
- Internal admin endpoint is included (same pattern as Memory U4), not public-facing.

---

## Identity Summary

| Table | platform_tenant_id | service_tenant_id | service_user_id | Unique Business Key |
|---|---|---|---|---|
| `plan_progress` | `VARCHAR(64) NOT NULL` | `VARCHAR(64) NOT NULL` | `VARCHAR(64) NOT NULL` | `(platform_tenant_id, service_tenant_id, plan_id)` |
| `action_progress` | `VARCHAR(64) NOT NULL` | `VARCHAR(64) NOT NULL` | `VARCHAR(64) NOT NULL` | `(platform_tenant_id, service_tenant_id, action_id)` |
