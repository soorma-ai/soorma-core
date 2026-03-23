# Business Logic Model — U4: services/memory
## Initiative: Multi-Tenancy Model Implementation
**Date**: 2026-03-23

---

## 1. Alembic Migration Logic

### Migration: `008_multi_tenancy_three_column_identity.py`

**Purpose**: Transform Memory Service database from two-column UUID FK identity to three-column opaque-string identity, rebuilding RLS policies for string comparison.

**Execution order within migration** (order matters — FKs must be dropped before tables):

```
Step 1: Drop all existing RLS policies on all 8 tables
        (policies reference ::UUID cast — invalid after migration)

Step 2: Drop FK constraints on all 8 tables referencing tenants.id and users.id

Step 3: Add platform_tenant_id VARCHAR(64) NOT NULL to all 8 tables
        DEFAULT 'spt_00000000-0000-0000-0000-000000000000' for existing rows

Step 4: Add service_tenant_id VARCHAR(64) NULL to all 8 tables

Step 5: Add service_user_id VARCHAR(64) NULL to all 8 tables

Step 6: Migrate existing tenant_id data → service_tenant_id (tenant_id::text)
        Migrate existing user_id data → service_user_id (user_id::text)
        where user_id is a UUID FK (episodic_memory, procedural_memory,
        working_memory, task_context, plan_context, plans, sessions)

Step 7: For semantic_memory: rename user_id String(255) → service_user_id String(64)
        (was not a UUID FK — already a plain string; cast/truncate to VARCHAR(64))

Step 8: Drop old tenant_id and user_id columns from all 8 tables

Step 9: Drop FKs on plan_context.plan_id → plans.id; convert to plain String(100)

Step 10: Drop tenants table
Step 11: Drop users table

Step 12: Update unique constraints:
         - task_context: rename to (platform_tenant_id, task_id)
         - plan_context: (plan_id) — unchanged, just column type changed
         - plans: rename unique to (platform_tenant_id, plan_id)
         - sessions: rename unique to (platform_tenant_id, session_id)
         - working_memory: (plan_id, key) — unchanged

Step 13: Rebuild RLS policies using string comparison (see Section 3)

Step 14: Enable RLS on all 8 tables (ALTER TABLE ... ENABLE ROW LEVEL SECURITY)
         FORCE ROW LEVEL SECURITY for superuser bypass protection
```

**Downgrade** (`downgrade()` function):
- Adds back `tenants` and `users` tables with minimal schema
- Adds back `tenant_id UUID` and `user_id UUID` columns (NULL — cannot recover data)
- Drops three-column identity columns
- Marks as **data-destructive**: document clearly in migration docstring

---

## 2. ORM Model Update Logic

### `memory_service/models/memory.py`

- Remove `Tenant` and `User` model classes entirely
- For each of the 8 table classes:
  - Replace `tenant_id = Column(UUID(as_uuid=True), ForeignKey(...))` → `platform_tenant_id = Column(String(64), nullable=False)`
  - Replace `user_id = Column(UUID(as_uuid=True), ForeignKey(...))` → `service_user_id = Column(String(64), nullable=True)`
  - Add `service_tenant_id = Column(String(64), nullable=True)`
  - Remove all `ForeignKey` imports references
  - Update `__table_args__` UniqueConstraints to use new column names

### `memory_service/core/database.py`

- Remove `ensure_tenant_exists()` function (no longer needed — no tenants table)
- Remove `set_session_context()` function (replaced by `get_tenanted_db` from soorma-service-common)
- Keep `get_db()` generator (used by `create_get_tenanted_db` factory)

---

## 3. RLS Policy Rebuild Logic

### Policy Pattern (per table)

Each table gets ONE policy (SELECT + INSERT + UPDATE + DELETE via `FOR ALL`) using string comparison:

```sql
CREATE POLICY {table_name}_platform_tenant_isolation
  ON {table_name}
  USING (
    platform_tenant_id = current_setting('app.platform_tenant_id', true)
  );
```

**Why single column**: The RLS policy enforces `platform_tenant_id` only. Application code enforces the full composite key `(platform_tenant_id, service_tenant_id, service_user_id)` via WHERE clauses. RLS is defence-in-depth for the highest-risk dimension (platform tenant isolation).

**String comparison rationale**: `current_setting('app.platform_tenant_id', true)` returns a string. `platform_tenant_id` is `VARCHAR(64)`. No `::uuid` cast needed — avoids the cast failure that the old policies would encounter with `spt_`-prefixed IDs.

**`true` as second arg**: The `missing_ok` parameter — if the setting is unset (e.g., connection not going through `get_tenanted_db`), returns empty string `''` rather than raising an error. The comparison `platform_tenant_id = ''` will never match any real row, so queries return 0 rows (TC-M-009 behaviour).

---

## 4. Middleware and Dependency Replacement Logic

### `memory_service/main.py`

```python
# Remove:
from memory_service.core.middleware import TenancyMiddleware
# Replace with:
from soorma_service_common import TenancyMiddleware
```

Remove `lifespan` log line: `"Local testing mode: {settings.is_local_testing}"` (setting removed).

### `memory_service/core/dependencies.py`

Replace entire file content with re-exports:
```python
"""
Re-export TenantContext and dependency functions from soorma-service-common.
Keeps existing import paths inside Memory Service working unchanged.
"""
from soorma_service_common import (
    TenantContext,
    create_get_tenant_context,
    create_get_tenanted_db,
)
from memory_service.core.database import get_db

get_tenanted_db = create_get_tenanted_db(get_db)
get_tenant_context = create_get_tenant_context(get_tenanted_db)

__all__ = ["TenantContext", "get_tenanted_db", "get_tenant_context"]
```

### `memory_service/core/middleware.py`

Delete entire file (replaced by `soorma_service_common.TenancyMiddleware`).

---

## 5. Service Layer Signature Update Logic

All service layer methods that previously accepted `(tenant_id: UUID, user_id: UUID)` change to `(platform_tenant_id: str, service_tenant_id: str, service_user_id: str)`.

### Pattern applied to all 8 service files:

```python
# Before:
async def store_knowledge(
    self,
    db: AsyncSession,
    tenant_id: UUID,
    user_id: str,
    data: SemanticMemoryCreate,
) -> SemanticMemoryResponse:

# After:
async def store_knowledge(
    self,
    db: AsyncSession,
    platform_tenant_id: str,
    service_tenant_id: str,
    service_user_id: str,
    data: SemanticMemoryCreate,
) -> SemanticMemoryResponse:
```

### API endpoint call sites (8 route files)

Route handlers currently use:
```python
context: TenantContext = Depends(get_tenant_context)
# ...
await service.method(context.db, context.tenant_id, str(context.user_id), data)
```

After update:
```python
context: TenantContext = Depends(get_tenant_context)
# ...
await service.method(
    context.db,
    context.platform_tenant_id,
    context.service_tenant_id or "",
    context.service_user_id or "",
    data,
)
```

---

## 6. CRUD Layer Signature Update Logic

All CRUD functions follow the same pattern as service layer:

```python
# Before:
async def upsert_semantic_memory(
    db: AsyncSession,
    tenant_id: UUID,
    user_id: str,
    ...
) -> SemanticMemory:
    stmt = insert(SemanticMemory).values(tenant_id=tenant_id, user_id=user_id, ...)

# After:
async def upsert_semantic_memory(
    db: AsyncSession,
    platform_tenant_id: str,
    service_tenant_id: str,
    service_user_id: str,
    ...
) -> SemanticMemory:
    stmt = insert(SemanticMemory).values(
        platform_tenant_id=platform_tenant_id,
        service_tenant_id=service_tenant_id,
        service_user_id=service_user_id,
        ...
    )
```

All WHERE clause filters change from `Model.tenant_id == tenant_id` to `Model.platform_tenant_id == platform_tenant_id` (primary filter). Service-tenant and user filters applied where needed.

---

## 7. MemoryDataDeletion Logic

### `memory_service/services/data_deletion.py` (new)

```python
class MemoryDataDeletion(PlatformTenantDataDeletion):
    """6 tables: semantic_memory, episodic_memory, procedural_memory,
       working_memory, task_context, plan_context."""

    _TABLES_6 = [
        SemanticMemory, EpisodicMemory, ProceduralMemory,
        WorkingMemory, TaskContext, PlanContext,
    ]

    async def delete_by_platform_tenant(self, db, platform_tenant_id) -> int:
        total = 0
        for Model in self._TABLES_6:
            result = await db.execute(
                delete(Model).where(Model.platform_tenant_id == platform_tenant_id)
            )
            total += result.rowcount
        return total

    async def delete_by_service_tenant(self, db, platform_tenant_id, service_tenant_id) -> int:
        total = 0
        for Model in self._TABLES_6:
            result = await db.execute(
                delete(Model).where(
                    Model.platform_tenant_id == platform_tenant_id,
                    Model.service_tenant_id == service_tenant_id,
                )
            )
            total += result.rowcount
        return total

    async def delete_by_service_user(self, db, platform_tenant_id, service_tenant_id, service_user_id) -> int:
        total = 0
        for Model in self._TABLES_6:
            result = await db.execute(
                delete(Model).where(
                    Model.platform_tenant_id == platform_tenant_id,
                    Model.service_tenant_id == service_tenant_id,
                    Model.service_user_id == service_user_id,
                )
            )
            total += result.rowcount
        return total
```

**Transaction management**: Each deletion method operates within the caller's transaction. The API endpoint owns `db.commit()`.

---

## 8. Deletion API Endpoint Logic

### Route: `DELETE /v1/memory/admin/data`

New router file: `memory_service/api/v1/admin.py`

```python
@router.delete("/admin/data/platform-tenant/{platform_tenant_id}", status_code=200)
async def delete_platform_tenant_data(platform_tenant_id: str, db=Depends(get_db)):
    """GDPR: Delete all data for a platform tenant. Admin-only."""
    deleter = MemoryDataDeletion()
    count = await deleter.delete_by_platform_tenant(db, platform_tenant_id)
    await db.commit()
    return {"deleted_rows": count, "platform_tenant_id": platform_tenant_id}

@router.delete("/admin/data/service-tenant", status_code=200)
async def delete_service_tenant_data(
    platform_tenant_id: str, service_tenant_id: str, db=Depends(get_db)
):
    """GDPR: Delete all data for a service tenant within a platform tenant."""
    deleter = MemoryDataDeletion()
    count = await deleter.delete_by_service_tenant(db, platform_tenant_id, service_tenant_id)
    await db.commit()
    return {"deleted_rows": count}

@router.delete("/admin/data/service-user", status_code=200)
async def delete_service_user_data(
    platform_tenant_id: str, service_tenant_id: str, service_user_id: str,
    db=Depends(get_db)
):
    """GDPR: Delete all data for a specific service user."""
    deleter = MemoryDataDeletion()
    count = await deleter.delete_by_service_user(db, platform_tenant_id, service_tenant_id, service_user_id)
    await db.commit()
    return {"deleted_rows": count}
```

**Note**: Admin endpoints use bare `get_db` (no RLS needed for deletions that bypass RLS by design — admin-level deletion). Deletion routes are called by an admin process, not a regular user request.

---

## 9. Config Update Logic

### `memory_service/core/config.py`

```python
# Remove:
is_local_testing: bool = ...
default_tenant_name: str = ...
default_user_id: str = ...
default_username: str = ...

# Update:
default_tenant_id: str = os.environ.get(
    "DEFAULT_TENANT_ID", "spt_00000000-0000-0000-0000-000000000000"
)
```

The `is_local_testing` flag is no longer needed (no SQLite path in memory service to begin with — memory service was already PostgreSQL-only).

---

## 10. DTO / Response Model Update Logic

### `soorma_common/models.py`

The DTOs (`SemanticMemoryResponse`, `WorkingMemoryResponse`, etc.) in `soorma-common` need updating to reflect the new field names. The U4 spec handles this at the **service layer and API layer** (response construction). The soorma-common DTO update is part of this unit's scope.

Key changes to DTOs:
- Replace `tenant_id: str` with `platform_tenant_id: str` 
- Add `service_tenant_id: Optional[str]`
- Add `service_user_id: Optional[str]`
- Remove legacy `tenant_id` field from response models

**Note**: soorma-common is a separate library — ensure backward compatibility is handled carefully. The DTO update is scoped to the response model field structure. The `SemanticMemoryCreate`, `WorkingMemorySet`, etc. request models do not carry tenant fields (they come from headers, not request body).

---

## 11. settings.default_tenant_id Update

```python
# Before:
default_tenant_id: str = os.environ.get("DEFAULT_TENANT_ID", "00000000-0000-0000-0000-000000000000")

# After:
default_tenant_id: str = os.environ.get("DEFAULT_TENANT_ID", "spt_00000000-0000-0000-0000-000000000000")
```

This setting maps to `X-Tenant-ID` header default in tests and `.env.example`.
