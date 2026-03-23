# Domain Entities — U4: services/memory
## Initiative: Multi-Tenancy Model Implementation
**Date**: 2026-03-23

---

## Overview

This document defines the ORM model changes required for U4. Eight tables transition from a two-column identity (UUID FK `tenant_id` + UUID FK `user_id`) to a three-column opaque-string identity (`platform_tenant_id`, `service_tenant_id`, `service_user_id`) with no FK constraints. Two reference tables (`tenants`, `users`) are dropped entirely.

---

## Dropped Entities

### `Tenant` (dropped)
- **Table**: `tenants`
- **Dropped because**: Soorma does not own service-tenant identity. Platform tenants are governed by the soorma-core Identity Service (future). Service tenants are managed by the platform tenant's own systems.
- **Impact**: All FK constraints referencing `tenants.id` on all 8 tables are dropped in migration.

### `User` (dropped)
- **Table**: `users`
- **Dropped because**: Same rationale — soorma-core does not own service-user identity.
- **Impact**: All FK constraints referencing `users.id` on all 8 tables are dropped in migration.

---

## Identity Columns — New Pattern (all 8 tables)

Every table that previously had `tenant_id UUID FK` and/or `user_id UUID FK` receives the following three columns instead:

| Column | Type | Nullable | Default | Purpose |
|--------|------|----------|---------|---------|
| `platform_tenant_id` | `VARCHAR(64)` | NOT NULL | — | Tier-1 scope: the platform customer |
| `service_tenant_id` | `VARCHAR(64)` | NULL | — | Tier-2 scope: the platform tenant's customer |
| `service_user_id` | `VARCHAR(64)` | NULL | — | Tier-2 scope: the individual user |

**Note**: `service_tenant_id` and `service_user_id` are nullable — they are optional identity dimensions. Only `platform_tenant_id` is mandatory for RLS enforcement.

---

## Updated Entities

### `SemanticMemory`
**Table**: `semantic_memory`

**Before**:
```python
tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
user_id = Column(String(255), nullable=False)  # was already string, not FK
```

**After**:
```python
platform_tenant_id = Column(String(64), nullable=False)
service_tenant_id = Column(String(64), nullable=True)
service_user_id = Column(String(64), nullable=True)
```

**Notes**:
- `user_id` was already `String(255)` (not a FK to `users`) — now renamed `service_user_id` and shortened to `String(64)`
- `is_public`, `content`, `embedding`, `external_id`, `content_hash` fields: unchanged
- `content_hash` constraint: `external_id`-based upsert now scoped on `(platform_tenant_id, service_tenant_id, external_id)` rather than `(tenant_id, user_id, external_id)`

---

### `EpisodicMemory`
**Table**: `episodic_memory`

**Before**:
```python
tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
```

**After**:
```python
platform_tenant_id = Column(String(64), nullable=False)
service_tenant_id = Column(String(64), nullable=True)
service_user_id = Column(String(64), nullable=True)
```

**Notes**: `agent_id`, `role`, `content`, `embedding`, `memory_metadata`, `created_at` unchanged.

---

### `ProceduralMemory`
**Table**: `procedural_memory`

**Before**:
```python
tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
```

**After**:
```python
platform_tenant_id = Column(String(64), nullable=False)
service_tenant_id = Column(String(64), nullable=True)
service_user_id = Column(String(64), nullable=True)
```

**Notes**: `agent_id`, `trigger_condition`, `embedding`, `procedure_type`, `content`, `created_at` unchanged.

---

### `WorkingMemory`
**Table**: `working_memory`

**Before**:
```python
tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
```

**After**:
```python
platform_tenant_id = Column(String(64), nullable=False)
service_tenant_id = Column(String(64), nullable=True)
service_user_id = Column(String(64), nullable=True)
```

**Notes**: `plan_id`, `key`, `value`, `updated_at` unchanged. The `plan_key_unique` constraint changes: unique on `(plan_id, key)` only (plan_id is already scoped by tenant via RLS; no need to add tenant columns to the constraint).

---

### `TaskContext`
**Table**: `task_context`

**Before**:
```python
tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
```

**After**:
```python
platform_tenant_id = Column(String(64), nullable=False)
service_tenant_id = Column(String(64), nullable=True)
service_user_id = Column(String(64), nullable=True)
```

**Notes**: `task_id`, `plan_id`, `event_type`, `response_event`, `response_topic`, `data`, `sub_tasks`, `state`, `created_at`, `updated_at` unchanged. The `task_context_unique` constraint changes from `(tenant_id, task_id)` to `(platform_tenant_id, task_id)`.

---

### `PlanContext`
**Table**: `plan_context`

**Before**:
```python
tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
plan_id = Column(UUID(as_uuid=True), ForeignKey("plans.id", ondelete="CASCADE"), nullable=False)
```

**After**:
```python
platform_tenant_id = Column(String(64), nullable=False)
plan_id = Column(String(100), nullable=False)  # plain column, no FK
service_tenant_id = Column(String(64), nullable=True)
service_user_id = Column(String(64), nullable=True)
```

**Notes**: `session_id`, `goal_event`, `goal_data`, `response_event`, `state`, `current_state`, `correlation_ids`, `created_at`, `updated_at` unchanged. The `plan_context_unique` constraint remains `(plan_id)` — but `plan_id` is now `String(100)` not UUID FK.

---

### `Plan`
**Table**: `plans`

**Before**:
```python
tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
plan_id = Column(String(100), nullable=False)
```

**After**:
```python
platform_tenant_id = Column(String(64), nullable=False)
service_tenant_id = Column(String(64), nullable=True)
service_user_id = Column(String(64), nullable=True)
plan_id = Column(String(100), nullable=False)  # unchanged
```

**Notes**: `session_id`, `goal_event`, `goal_data`, `status`, `parent_plan_id`, `created_at`, `updated_at` unchanged. The `plan_unique` constraint changes from `(tenant_id, plan_id)` to `(platform_tenant_id, plan_id)`.

---

### `Session`
**Table**: `sessions`

**Before**:
```python
tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
session_id = Column(String(100), nullable=False)
```

**After**:
```python
platform_tenant_id = Column(String(64), nullable=False)
service_tenant_id = Column(String(64), nullable=True)
service_user_id = Column(String(64), nullable=True)
session_id = Column(String(100), nullable=False)  # unchanged
```

**Notes**: `name`, `session_metadata`, `created_at`, `last_interaction` unchanged. The `session_unique` constraint changes from `(tenant_id, session_id)` to `(platform_tenant_id, session_id)`.

---

## New Entity: `MemoryDataDeletion`

**Module**: `memory_service/services/data_deletion.py`

```python
class MemoryDataDeletion(PlatformTenantDataDeletion):
    """
    GDPR erasure for Memory Service.
    Covered tables (6): semantic_memory, episodic_memory, procedural_memory,
                        working_memory, task_context, plan_context.
    Note: plans and sessions are NOT in scope for MemoryDataDeletion.
    They are lifecycle management tables, deleted via separate plan/session
    management workflows. Included in deletion API endpoint but as a
    separate consideration (see business-rules.md BR-U4-08).
    """
```

**Methods** (all return `int` = total rows deleted):
- `delete_by_platform_tenant(db, platform_tenant_id)` — deletes from all 6 tables
- `delete_by_service_tenant(db, platform_tenant_id, service_tenant_id)` — scoped to service tenant within platform tenant
- `delete_by_service_user(db, platform_tenant_id, service_tenant_id, service_user_id)` — scoped to specific user

---

## Identity Summary Table

| Table | Covered by MemoryDataDeletion | pk type | New unique constraint |
|-------|------|-----|-----|
| `semantic_memory` | Yes | `UUID` (unchanged) | — (no unique on tenant cols) |
| `episodic_memory` | Yes | `UUID` (unchanged) | — |
| `procedural_memory` | Yes | `UUID` (unchanged) | — |
| `working_memory` | Yes | `UUID` (unchanged) | `(plan_id, key)` |
| `task_context` | Yes | `UUID` (unchanged) | `(platform_tenant_id, task_id)` |
| `plan_context` | Yes | `UUID` (unchanged) | `(plan_id)` |
| `plans` | No (lifecycle) | `UUID` (unchanged) | `(platform_tenant_id, plan_id)` |
| `sessions` | No (lifecycle) | `UUID` (unchanged) | `(platform_tenant_id, session_id)` |
