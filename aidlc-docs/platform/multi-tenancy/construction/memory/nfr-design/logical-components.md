# Logical Components — U4: services/memory
## Initiative: Multi-Tenancy Model Implementation
**Date**: 2026-03-23

---

## Component Map

```
services/memory/
├── Alembic Migration 008
│     Drops: tenants table, users table, all UUID FK constraints, old RLS policies
│     Adds: platform_tenant_id, service_tenant_id, service_user_id on 8 tables
│     Rebuilds: RLS policies (string comparison)
│
├── ORM Layer (models/memory.py)
│     Removes: Tenant class, User class
│     Updates: 8 table classes — replace UUID FK columns with String(64) columns
│
├── Middleware / Dependencies Layer
│     Replaces: local TenancyMiddleware → soorma_service_common.TenancyMiddleware
│     Replaces: local TenantContext/get_tenant_context → re-exports from soorma-service-common
│     Removes:  memory_service/core/middleware.py (entire file)
│     Updates:  memory_service/core/dependencies.py (thin re-export wrapper)
│     Updates:  memory_service/core/database.py (remove ensure_tenant_exists, set_session_context)
│
├── CRUD Layer (crud/*.py — 8 files)
│     Updates: All function signatures: (tenant_id: UUID, user_id: UUID)
│              → (platform_tenant_id: str, service_tenant_id: str, service_user_id: str)
│     Updates: All WHERE clauses to use new column names
│
├── Service Layer (services/*.py — 8 files)
│     Updates: All service method signatures (same as CRUD pattern)
│     Updates: CRUD call sites with new parameter names
│
├── API Layer (api/v1/*.py — 8 route files)
│     Updates: All TenantContext usages → .platform_tenant_id, .service_tenant_id, .service_user_id
│     Adds:    api/v1/admin.py (deletion endpoints)
│
├── Data Deletion (services/data_deletion.py — new)
│     Implements: MemoryDataDeletion(PlatformTenantDataDeletion)
│     Covers: 6 tables
│
├── Config (core/config.py)
│     Removes: is_local_testing, default_tenant_name, default_user_id, default_username
│     Updates: default_tenant_id default value → "spt_00000000-0000-0000-0000-000000000000"
│
└── Tests (tests/*.py)
      Updates: All test fixtures and assertions to use new identity model
```

---

## Dependency Flow

```
HTTP Request
    → TenancyMiddleware (soorma_service_common) — header extraction
    → get_tenant_context (soorma_service_common) — bundles TenantContext
        ↳ get_tenanted_db (soorma_service_common) — set_config x3
            ↳ get_db (memory_service.core.database) — AsyncSession
    → Route Handler (api/v1/*.py)
    → Service (services/*.py)
    → CRUD (crud/*.py)
    → ORM (models/memory.py)
    → PostgreSQL (RLS active via set_config)
```

---

## Affected File Count

| Layer | Files | Action |
|-------|-------|--------|
| Alembic | 1 new migration | Create |
| ORM models | 1 file | Modify |
| databases | 1 file | Modify (remove 2 functions) |
| middleware | 1 file | Delete |
| dependencies | 1 file | Replace with re-exports |
| config | 1 file | Modify |
| main | 1 file | Modify (import TenancyMiddleware) |
| CRUD | 8 files | Modify (signature + WHERE changes) |
| Services | 8 files | Modify (signature + call sites) |
| API routes | 8 + 1 new | Modify (context fields) + Create admin.py |
| Data deletion | 1 new | Create |
| Tests | ~15 files | Modify |
| **Total** | **~47 files** | — |
