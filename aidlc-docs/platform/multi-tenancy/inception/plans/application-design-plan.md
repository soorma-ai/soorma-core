# Application Design Plan
## Initiative: Multi-Tenancy Model Implementation
**INITIATIVE_ROOT**: `aidlc-docs/platform/multi-tenancy/`
**Stage**: Application Design
**Date**: 2026-03-22

---

## Step 1: Context Analysis

The requirements are detailed and approved. The following components require Application Design:

### New Components (require full design)
- `libs/soorma-service-common` — new shared FastAPI library: `TenancyMiddleware`, FastAPI dependency functions, and `PlatformTenantDataDeletion`

### Modified Components (require interface update design)
- `libs/soorma-common` — add `DEFAULT_PLATFORM_TENANT_ID` constant
- `services/registry` — drop UUID validation, update ORM + API deps
- `services/memory` — schema restructure, RLS rebuild, adopt shared middleware, GDPR deletion
- `services/tracker` — schema restructure, adopt shared middleware, GDPR deletion
- `sdk/python` — update Memory/Tracker clients + PlatformContext wrappers

---

## Step 2: Design Plan

- [x] Analyze requirements and identify component boundaries
- [x] Ask clarifying questions (3 design decisions below — need answers before artifact generation)
- [x] Generate `components.md`
- [x] Generate `component-methods.md`
- [x] Generate `services.md`
- [x] Generate `component-dependency.md`
- [x] Generate `application-design.md` (consolidated)
- [x] Validate design completeness

---

## Step 3: Clarifying Questions

Three design decisions are genuinely ambiguous from the requirements. Please fill in the `[Answer]:` tags.

---

### Q1 — `set_config` execution model in async SQLAlchemy

FR-3a.3 requires `set_config` to be called within the same DB transaction as the subsequent query. In an async FastAPI + asyncpg stack, the `TenancyMiddleware` processes the request before a DB session exists — it cannot call `set_config` directly.

Two viable options:

**Option A — Split responsibility**: `TenancyMiddleware` sets `request.state` only (pure header extraction, no DB ops). A separate FastAPI dependency `get_tenanted_db(request, db)` wraps the standard `get_db` and calls `await db.execute("SELECT set_config(...)")` before yielding. Services import `get_tenanted_db` as their DB session dependency.

**Option B — Middleware with DB injection**: `TenancyMiddleware` is extended to call `set_config` directly by accepting a SQLAlchemy async session factory as a constructor argument and opening a connection per-request.

*Split responsibility (A) is the recommended pattern for async FastAPI. Middleware that opens DB connections can cause connection-per-middleware issues under load.*

[Answer]: A

---

### Q2 — Registry Service and `soorma-service-common`

FR-3a.5 states: "Memory Service, Tracker Service (and any future services) MUST use the shared TenancyMiddleware." Registry is **not listed**. Registry is developer-facing (platform tenant only; no service tenant/user).

**Additional context (user feedback)**: Registry's `IS_LOCAL_TESTING` SQLite path is an existing inconsistency — all services use PostgreSQL exclusively (including dev). Unit tests do not use a real DB. Registry will drop SQLite and align to PostgreSQL-only as part of the Registry unit (U3). This eliminates the `set_config` compatibility concern.

**Option A — Registry uses `soorma-service-common` (consistent pattern)**: Import `TenancyMiddleware` and `get_platform_tenant_id()` from `soorma-service-common`. No `set_config` in Registry because Registry has no RLS-protected tables — middleware handles header extraction only. All services follow the same pattern.

**Option B — Registry updates its own dependency function independently**: Keep Registry's `get_developer_tenant_id()` in `registry_service/api/dependencies.py`, just remove UUID validation and change return type to `str`. No dependency on `soorma-service-common`.

*User preference: consistency across all services. SQLite concern is moot — Registry will migrate to PostgreSQL-only.*

**Scope note**: Registry unit (U3) must also include: remove `IS_LOCAL_TESTING` SQLite path from `database.py` and `config.py`; standardize to PostgreSQL-only (matching Memory + Tracker pattern).

[Answer]: A

---

### Q3 — `PlatformTenantDataDeletion` placement

FR-4 says implement in Memory Service. FR-5.8 says extend the concept to Tracker Service. The question is whether to define a shared abstract interface.

**Option A — Shared abstract interface in `soorma-service-common`** + concrete implementations per service:

```python
# soorma-service-common
class PlatformTenantDataDeletion(ABC):
    async def delete_by_platform_tenant(self, platform_tenant_id: str) -> int: ...
    async def delete_by_service_tenant(self, platform_tenant_id: str, service_tenant_id: str) -> int: ...
    async def delete_by_service_user(self, platform_tenant_id: str, service_tenant_id: str, service_user_id: str) -> int: ...
```

**Option B — Per-service concrete classes only** (no shared interface): `MemoryDataDeletion` in memory service, `TrackerDataDeletion` in tracker service. Same method signatures by convention but no shared base class.

*Option A makes a future GDPR service coordinator easier. Option B is simpler — two services, no shared base needed yet.*

[Answer]: A

---

## Step 4: After Answers Collected

Once questions above are answered, generate application design artifacts:
- `inception/application-design/components.md`
- `inception/application-design/component-methods.md`
- `inception/application-design/services.md`
- `inception/application-design/component-dependency.md`
- `inception/application-design/application-design.md`
