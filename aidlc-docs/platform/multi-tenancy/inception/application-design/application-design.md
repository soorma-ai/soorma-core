# Application Design — Consolidated
## Initiative: Multi-Tenancy Model Implementation
**Date**: 2026-03-22

---

## Overview

This document consolidates all application design artifacts for the multi-tenancy model initiative. The initiative replaces soorma-core's single-tier UUID tenancy with a two-tier model (platform tenant + service tenant + service user) across 8 components in 5 packages.

**Detailed artifacts**: See sibling files in `inception/application-design/`:
- [components.md](components.md) — Component definitions and responsibilities
- [component-methods.md](component-methods.md) — Method signatures and interfaces
- [services.md](services.md) — Service definitions and orchestration patterns
- [component-dependency.md](component-dependency.md) — Dependency matrix, data flow, communication patterns

---

## Design Decisions (from application-design-plan.md)

| Q | Decision | Rationale |
|---|---|---|
| Q1 — `set_config` execution | Split responsibility: `TenancyMiddleware` = headers only; `get_tenanted_db` dependency = `set_config` + DB session | Middleware cannot open DB connections cleanly in async FastAPI; dependency pattern is idiomatic and transaction-safe |
| Q2 — Registry middleware | Option A — Registry adopts `TenancyMiddleware` + `get_platform_tenant_id` from `soorma-service-common` | Consistency across all services; SQLite concern was an existing wrong inconsistency (Registry migrated to PostgreSQL); Registry unit (U3) also drops `IS_LOCAL_TESTING` SQLite path |
| Q3 — `PlatformTenantDataDeletion` | Option A — abstract base class in `soorma-service-common`; concrete impls per service | Enables future GDPR coordinator to call a single interface across services; no added complexity today |
| FR-6 — EventEnvelope + NATS tenancy | Option B — add `platform_tenant_id` to `EventEnvelope`; Event Service injects/overwrites it from `X-Tenant-ID` header at publish time | NATS bus is NOT single-platform-tenant; SDK portability to future event buses that may not support headers; Event Service is the trust boundary |

---

## Component Summary

| ID | Component | Type | Key Change |
|---|---|---|---|
| C1 | `libs/soorma-common` | Modified | Add `DEFAULT_PLATFORM_TENANT_ID` constant + env override; add `platform_tenant_id` field to `EventEnvelope`; update docstrings |
| C2 | `libs/soorma-service-common` | **NEW** | `TenancyMiddleware`, `get_tenanted_db`, `TenantContext`/`get_tenant_context` bundle, dependency functions, `PlatformTenantDataDeletion` ABC |
| C3 | `services/registry` | Modified | UUID→VARCHAR; adopt `soorma-service-common`; drop SQLite path |
| C4 | `services/memory` | Modified | Drop tenants/users tables; three-column identity; rebuild RLS; `MemoryDataDeletion` |
| C5 | `services/tracker` | Modified | Column renames + `platform_tenant_id`; adopt middleware; `TrackerDataDeletion`; NATS path trusts `event.platform_tenant_id` |
| C6 | `sdk/python` service clients | Modified | `platform_tenant_id` at init; per-call `service_tenant_id`/`service_user_id` |
| C7 | `sdk/python` PlatformContext | Modified | Wrappers pass `service_tenant_id`/`service_user_id` from event envelope; no platform leakage |
| C8 | `services/event-service` | Modified | Register `TenancyMiddleware`; inject `event.platform_tenant_id` from `X-Tenant-ID` header at publish |

---

## Identity Model

```
HTTP Request
┌─────────────────────────────────────────────────────────┐
│  X-Tenant-ID          → platform_tenant_id  (Tier 1)   │
│  X-Service-Tenant-ID  → service_tenant_id   (Tier 2)   │
│  X-User-ID            → service_user_id     (Tier 2)   │
└─────────────────────────────────────────────────────────┘
         ↓  TenancyMiddleware
    request.state
         ↓  get_tenanted_db
    set_config x3 (transaction-scoped)
         ↓
    PostgreSQL RLS active
         ↓
    All queries: WHERE (platform_tenant_id, service_tenant_id, service_user_id)
```

---

## New Library: `libs/soorma-service-common`

The most significant structural change in this initiative is the creation of a new shared library that provides:

1. **`TenancyMiddleware`** — Uniform header extraction registered in all services
2. **`get_tenanted_db`** — FastAPI dependency that activates RLS via `set_config` before every DB operation
3. **`PlatformTenantDataDeletion`** — Shared abstract interface for GDPR deletion (concrete impls: `MemoryDataDeletion`, `TrackerDataDeletion`)

**Why a separate library?** `soorma-common` is used by both the SDK and services. Adding FastAPI/Starlette to it would contaminate the SDK's dependency graph. `soorma-service-common` is services-only.

---

## Critical Security Constraint

**Composite key enforcement**: Every database query on service-scoped tables MUST include `platform_tenant_id` as a WHERE condition. Using `service_tenant_id` alone — without `platform_tenant_id` — is a cross-tenant data leakage vulnerability.

RLS policies are a defence-in-depth enforcement of this rule at the database level. The application code must also enforce it explicitly (RLS policies apply to non-owner connections; defence must not rely solely on DB).

---

## Update Sequence

```
U1 soorma-common  ──────────────────────────────────────────────────► unlock everything
                   ↓                              ↓
U2 soorma-service-common             U3 services/registry (parallel)
   (TenancyMiddleware, get_tenanted_db,   (UUID→VARCHAR, adopt middleware,
    PlatformTenantDataDeletion ABC)        drop SQLite, PostgreSQL-only)
         ↓                  ↓
U4 services/memory    U5 services/tracker  (parallel after U1+U2)
   (schema + RLS)        (column renames)
              ↓
         U6 sdk/python  (after U4+U5 API surfaces stable)
```
