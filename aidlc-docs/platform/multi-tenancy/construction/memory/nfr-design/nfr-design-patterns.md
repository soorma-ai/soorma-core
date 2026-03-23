# NFR Design Patterns — U4: services/memory
## Initiative: Multi-Tenancy Model Implementation
**Date**: 2026-03-23

---

## Pattern 1: RLS Policy Expression (String Comparison)

### Rationale
Old RLS policies used `::UUID` cast: `tenant_id = current_setting('app.tenant_id', true)::UUID`. After the migration, `platform_tenant_id` is `VARCHAR(64)` and carries `spt_`-prefixed values — the `::UUID` cast would fail. New policies use direct string equality.

### Implementation

```sql
-- Applied to EACH of the 8 tables
ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY;
ALTER TABLE {table_name} FORCE ROW LEVEL SECURITY;

CREATE POLICY {table_name}_platform_rls
  ON {table_name}
  USING (
    platform_tenant_id = current_setting('app.platform_tenant_id', true)
  );
```

**`FORCE ROW LEVEL SECURITY`**: Required to prevent table OWNER (superuser-equivalent) from bypassing RLS. In test environments where the DB owner creates test data, FORCE ensures policies are always evaluated.

**`current_setting('app.platform_tenant_id', true)`**: The `true` (`missing_ok`) argument prevents a PostgreSQL error if the session variable is not set. Returns `''` (empty string). Since no `platform_tenant_id` value equals `''`, the policy returns 0 rows — which is the desired behaviour (TC-M-009).

---

## Pattern 2: set_config Activation Lifecycle

### Request Path (HTTP)

```
HTTP Request 
    ↓
TenancyMiddleware.dispatch()
    Reads X-Tenant-ID header → request.state.platform_tenant_id
    Reads X-Service-Tenant-ID → request.state.service_tenant_id
    Reads X-User-ID           → request.state.service_user_id
    ↓
Route Handler: Depends(get_tenant_context)
    ↓
get_tenant_context → get_tenanted_db → get_db
    Calls set_config('app.platform_tenant_id', ..., true)  ← transaction-scoped
    Calls set_config('app.service_tenant_id',  ..., true)  ← transaction-scoped  
    Calls set_config('app.service_user_id',    ..., true)  ← transaction-scoped
    Yields AsyncSession with RLS active
    ↓
CRUD/Service Layer: All PostgreSQL queries execute with RLS session variables set
    ↓
Transaction commits; session variables expire with the transaction
```

### NATS Path (future — not implemented in this unit)

```
NATS event received
    ↓
Event handler: extracts platform_tenant_id from event.platform_tenant_id
    event.tenant_id → service_tenant_id
    event.user_id   → service_user_id
    ↓
Call set_config_for_session(db, ...) before first DB query
    ↓
Execute queries with RLS active
```

---

## Pattern 3: Composite Key Enforcement (Defence-in-Depth)

### Two-Layer Enforcement

| Layer | Mechanism | Enforces |
|-------|-----------|---------|
| Application (CRUD) | WHERE clause | `platform_tenant_id`, `service_tenant_id`, `service_user_id` |
| Database (RLS) | Row policy | `platform_tenant_id` only |

### Why Both Are Required

RLS enforces the outer scope only (platform tenant). Application WHERE clauses enforce the inner scopes (service tenant, user). Neither alone is sufficient:
- RLS alone: service tenant 1 could see service tenant 2's rows (both share the same platform tenant)
- App WHERE alone: RLS off means a compromised connection could bypass app enforcement

### Composite Key Pattern in CRUD

```python
# SELECT pattern (minimum required filter)
stmt = select(Model).where(
    Model.platform_tenant_id == platform_tenant_id,  # REQUIRED always
    Model.service_tenant_id == service_tenant_id,    # When service scope needed
    Model.service_user_id == service_user_id,        # When user scope needed
)

# DELETE pattern (composite key — no partial deletes)
stmt = delete(Model).where(
    Model.platform_tenant_id == platform_tenant_id,  # REQUIRED outer scope
    Model.service_tenant_id == service_tenant_id,    # scope
    # service_user_id optional — depends on operation scope
)
```

---

## Pattern 4: Admin Deletion RLS Bypass

### Rationale

GDPR deletion endpoints must delete data belonging to a given platform tenant across all tables. This operation cannot run under the tenant's own RLS session (the policies would restrict visibility to only that tenant's rows — which would work, but requires activating RLS first). Instead, admin endpoints use a **database owner connection** that bypasses RLS, or they connect as a role that is excluded from RLS policies.

### Implementation Choice

For this unit, admin endpoints use `Depends(get_db)` which connects as the application database user. In PostgreSQL, if `FORCE ROW LEVEL SECURITY` is set, the app user is also subject to RLS unless the role has `BYPASSRLS`.

**Design decision**: Admin endpoints set `set_config` to the target platform_tenant_id before executing deletes. This means RLS allows the deletes through with the correct tenant scope. This is simpler than managing a separate admin DB role.

```python
# Admin endpoint deletion pattern
platform_tenant_id = path_param
await set_config_for_session(db, platform_tenant_id, "", "")
result = await deleter.delete_by_platform_tenant(db, platform_tenant_id)
await db.commit()
```

**Note**: `set_config_for_session` is imported from `soorma_service_common`. Admin endpoints import this directly to activate the correct RLS scope.
