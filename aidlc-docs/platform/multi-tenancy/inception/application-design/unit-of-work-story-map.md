# Unit of Work — Requirement Traceability
## Initiative: Multi-Tenancy Model Implementation
**Date**: 2026-03-22

> User Stories stage was skipped (no user-facing features). Traceability maps directly from Functional Requirements (FR) and Non-Functional Requirements (NFR) to units.

---

## Requirement → Unit Assignment

| Requirement | Description (summary) | Unit(s) |
|---|---|---|
| FR-1.1 | `DEFAULT_PLATFORM_TENANT_ID` constant | U1 |
| FR-1.2 | `SOORMA_PLATFORM_TENANT_ID` env var override | U1 |
| FR-1.3 | Deprecation warning on constant | U1 |
| FR-1.4 | No format validation on tenant/user ID strings | U1 |
| FR-2.1 | Registry `tenant_id` UUID → VARCHAR(64) migration | U3 |
| FR-2.2 | Alembic migration using `::text` cast | U3 |
| FR-2.3 | `AgentTable.tenant_id` → `String(64)` ORM | U3 |
| FR-2.4 | `EventTable.tenant_id` → `String(64)` ORM | U3 |
| FR-2.5 | `SchemaTable.tenant_id` → `String(64)` ORM | U3 |
| FR-2.6 | Remove `get_developer_tenant_id()`; adopt `TenancyMiddleware` + `get_platform_tenant_id` from soorma-service-common | U3 |
| FR-2.7 | All Registry CRUD/service layer: `UUID` → `str` | U3 |
| FR-2.8 | Registry tests use new platform tenant ID format | U3 |
| FR-2.9 | Remove `IS_LOCAL_TESTING` / SQLite path from Registry | U3 |
| FR-3a.1 | Create `libs/soorma-service-common` new library | U2 |
| FR-3a.2 | Implement `TenancyMiddleware` | U2 |
| FR-3a.3 | `set_config` activation in `get_tenanted_db` dependency | U2 |
| FR-3a.4 | `get_platform_tenant_id`, `get_service_tenant_id`, `get_service_user_id` dependency functions | U2 |
| FR-3a.5 | All services use shared `TenancyMiddleware` (no per-service re-impl) | U2 (library); U3, U4, U5, U7 (adoption) |
| FR-3b.1 | Drop existing RLS policies on memory tables | U4 |
| FR-3b.2 | Recreate RLS policies with string comparison + new session vars | U4 |
| FR-3b.3 | All 8 memory tables have updated policies | U4 |
| FR-3b.4 | `set_config` (middleware) + RLS policies are a matched pair | U2 (set_config); U4 (RLS policies) |
| FR-3.1 | Drop `tenants` + `users` reference tables | U4 |
| FR-3.2 | Remove all FK constraints from memory tables | U4 |
| FR-3.3 | Add `platform_tenant_id`, rename `service_tenant_id`/`service_user_id` on all memory tables | U4 |
| FR-3.4 | Update ORM models for all memory tables | U4 |
| FR-3.5 | Breaking Alembic migration (no data migration) | U4 |
| FR-3.6 | Replace local memory `TenancyMiddleware` with shared one | U4 |
| FR-3.7 | Update `settings.default_tenant_id` default value | U4 |
| FR-3.8 | Update Memory Service service layer: new three-dim params | U4 |
| FR-3.9 | Update Memory Service API DTOs and request/response models | U4 |
| FR-3.10 | Memory SDK client headers update | U6 |
| FR-4.1 | `MemoryDataDeletion` service with three deletion scopes | U4 |
| FR-4.2 | Deletion covers all 6 memory tables | U4 |
| FR-4.3 | Internal deletion API endpoint | U4 |
| FR-5.1 | Tracker `tenant_id → service_tenant_id` migration | U5 |
| FR-5.2 | Tracker `user_id → service_user_id` migration | U5 |
| FR-5.3 | Add `platform_tenant_id VARCHAR(64) NOT NULL` to Tracker tables | U5 |
| FR-5.4 | Update Tracker ORM models | U5 |
| FR-5.5 | Tracker Alembic migration | U5 |
| FR-5.6 | Register shared `TenancyMiddleware` in Tracker; update event subscribers | U5 |
| FR-5.7 | Tracker API query endpoints filter by composite key | U5 |
| FR-5.8 | `TrackerDataDeletion` covering `plan_progress` + `action_progress` | U5 |
| FR-6.1 | `EventEnvelope.tenant_id` field retained (now = service tenant) | U1 |
| FR-6.2 | `EventEnvelope.user_id` field retained (now = service user) | U1 |
| FR-6.3 | Add `EventEnvelope.platform_tenant_id` field; Event Service injects, SDK must not set | U1 (field); U7 (injection) |
| FR-6.4 | Update `EventEnvelope` field docstrings | U1 |
| FR-6.5 | Event Service registers `TenancyMiddleware` | U7 |
| FR-6.6 | Event Service `publish_event` injects `platform_tenant_id` from `request.state` | U7 |
| FR-6.7 | Tracker NATS handlers extract `platform_tenant_id` from `event.platform_tenant_id` | U5 |
| FR-7.1 | SDK clients: `platform_tenant_id` at init time (not per-call) | U6 |
| FR-7.2 | SDK Memory client per-call params: `service_tenant_id` / `service_user_id` | U6 |
| FR-7.3 | SDK Tracker client: same init + per-call pattern | U6 |
| FR-7.4 | PlatformContext wrappers: `service_tenant_id` / `service_user_id`; `platform_tenant_id` hidden | U6 |
| FR-7.5 | `cli/commands/init.py` use new constant | U6 |
| FR-7.6 | Update all SDK tests | U6 |
| FR-8.1 | `ARCHITECTURE_PATTERNS.md` Section 1: two-tier tenancy | U6 |
| FR-8.2 | Header table update | U6 |
| FR-8.3 | Document `platform_tenant_id` injection model | U6 |
| NFR-1.1 | `platform_tenant_id` from authenticated channel only | U2 (middleware); U7 (injection) |
| NFR-1.2 | No cross-tenant leakage — composite key mandatory | U2 (set_config + RLS); U4, U5 (composite key in all queries) |
| NFR-1.3 | Partial keys (service_tenant_id alone) prohibited | U4, U5 (CRUD enforcement) |
| NFR-2.1–2.3 | Breaking change; no data migration; update all tests | All units |
| NFR-3.1 | `VARCHAR(64)` max length on all tenant/user columns | U3, U4, U5 |
| NFR-3.2 | No UUID format validation | U1, U3 |
| NFR-3.3 | Default constant carries deprecation warning | U1 |

---

## Coverage Summary

| Unit | FR count | NFR count | All requirements covered? |
|---|---|---|---|
| U1 | FR-1.1–1.4, FR-6.1–6.4 (partial) | NFR-3.2, NFR-3.3 | ✓ |
| U2 | FR-3a.1–3a.5, FR-3b.4 (partial) | NFR-1.1, NFR-1.2 (set_config) | ✓ |
| U3 | FR-2.1–2.9 | NFR-3.1 | ✓ |
| U4 | FR-3b.1–3b.3, FR-3.1–3.9, FR-4.1–4.3 | NFR-1.2, NFR-1.3, NFR-3.1 | ✓ |
| U5 | FR-5.1–5.8, FR-6.7 | NFR-1.3, NFR-3.1 | ✓ |
| U6 | FR-3.10, FR-7.1–7.6, FR-8.1–8.3 | NFR-2.3 | ✓ |
| U7 | FR-6.3 (injection), FR-6.5, FR-6.6 | NFR-1.1 | ✓ |

All 47 functional requirement sub-items and all NFRs are assigned to at least one unit. No gaps.
