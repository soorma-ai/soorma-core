# NFR Requirements — U4: services/memory
## Initiative: Multi-Tenancy Model Implementation
**Date**: 2026-03-23

---

## Overview

The dominant NFR for the Memory Service multi-tenancy migration is **Security** — specifically, the enforcement of Row-Level Security (RLS) policies that were previously absent or unenforced. The service transitions from a single-tenant model (no RLS, UUID-based) to a multi-tenant model with policy-enforced platform tenant isolation.

---

## NFR-M-01: Row-Level Security (RLS) — BLOCKING Security Requirement

**Type**: Security  
**Priority**: Critical (blocking — must be implemented)  
**Source**: FR-3b.2, FR-3b.4 (requirements.md); security-baseline SECURITY-03

**Requirement**:  
All 8 Memory Service tables MUST have PostgreSQL Row-Level Security enabled and enforced. Every connection that reads or writes to these tables MUST have `app.platform_tenant_id` set via `set_config` before executing any query.

**Acceptance Criteria**:
- `ENABLE ROW LEVEL SECURITY` + `FORCE ROW LEVEL SECURITY` on all 8 tables
- RLS policy per table: `platform_tenant_id = current_setting('app.platform_tenant_id', true)`
- All route handlers use `get_tenanted_db` (via `get_tenant_context`) — never bare `get_db` except admin endpoints
- TC-M-003: Cross-tenant isolation test passes (query with wrong platform_tenant_id → 0 rows)
- TC-M-008: RLS policies use string comparison (no `::uuid` cast)
- TC-M-009: Query without set_config → 0 rows

---

## NFR-M-02: GDPR Erasure Completeness

**Type**: Compliance (Data Protection)  
**Priority**: High  
**Source**: FR-4.1, FR-4.2 (requirements.md)

**Requirement**:  
The `MemoryDataDeletion` implementation MUST delete from ALL 6 covered tables in a single operation. Partial deletion (some tables but not all) MUST be treated as a failure.

**Acceptance Criteria**:
- TC-M-005: `delete_by_platform_tenant()` removes all rows across all 6 tables
- TC-M-006: `delete_by_service_tenant()` scoped within platform tenant — sibling platform tenants unaffected
- TC-M-011: `delete_by_service_user()` removes only the specific user's rows

---

## NFR-M-03: Transaction Scoping for set_config

**Type**: Security (Data Integrity)  
**Priority**: Critical  
**Source**: BR-U2-04 (from soorma-service-common); architectural decisions Q1

**Requirement**:  
`set_config` MUST use transaction-scoped lifetime (`true` third arg). Session-scoped `set_config` is prohibited due to connection pool reuse risks.

**Acceptance Criteria**:
- Code review: all `set_config` calls use `true` as third argument
- `get_tenanted_db` is used for all route-handler DB sessions (except admin endpoints)
- Integration test: `get_tenanted_db` makes exactly 3 `set_config` calls per request

---

## NFR-M-04: No Cross-Tenant Data Leakage via Composite Key Enforcement

**Type**: Security  
**Priority**: Critical  
**Source**: Application Design "Critical Security Constraint"

**Requirement**:  
Every query on a memory table MUST include `platform_tenant_id` as a WHERE clause condition. Queries using only `service_tenant_id` or `service_user_id` without `platform_tenant_id` are prohibited.

**Acceptance Criteria**:
- Code review: CRUD layer includes `Model.platform_tenant_id == platform_tenant_id` in all SELECT/UPDATE/DELETE queries
- No CRUD function accepts a `service_tenant_id` or `service_user_id` parameter without also requiring `platform_tenant_id`

---

## NFR-M-05: Memory Service Remains PostgreSQL-Only

**Type**: Operational / Maintainability  
**Priority**: Medium  
**Source**: BR-U4-10; aligned with U3 (Registry) PostgreSQL-only direction

**Requirement**:  
Remove all `is_local_testing` flags and SQLite references. Memory Service uses only PostgreSQL (with `asyncpg` driver) for both development and production.

**Acceptance Criteria**:
- `is_local_testing` removed from `Settings`
- No SQLite conditional paths in database.py or config.py
- Tests use `pytest-asyncio` with PostgreSQL test DB (or async mock via `AsyncMock`)

---

## NFR-M-06: Structured Logging (Security Baseline SECURITY-03)

**Type**: Security / Observability  
**Priority**: Medium  
**Source**: SECURITY-03 (logging extension)

**Requirement**:  
Memory Service retains existing structured logging. Sensitive data (tenant IDs, user IDs) MUST NOT appear in unstructured log output. The service uses `print()` currently — upgrading to structured logging is out of scope for this unit (pre-production). Verify that `platform_tenant_id` in log lines is acceptable (it's an opaque string, not PII).

**Acceptance Criteria**:
- No passwords or API keys in logs
- Tenant ID logging is acceptable (opaque string, not PII in this context)
- Out-of-scope upgrade: logging framework migration is a separate initiative
