# NFR Requirements — soorma-service-common (U2)
## Initiative: Multi-Tenancy Model Implementation
**Date**: 2026-03-22

---

## NFR-U2-SEC-01: RLS Activation Completeness (SECURITY — BLOCKING)

**Category**: Security
**Priority**: Critical

**Requirement**: PostgreSQL Row-Level Security MUST be activated on the correct connection and within the correct transaction scope for every database request handled by a service that enforces multi-tenancy.

**Specifics**:
- `set_config` MUST be called for ALL three session variables: `app.platform_tenant_id`, `app.service_tenant_id`, `app.service_user_id`
- `set_config` MUST use transaction-scoped lifetime (third argument = `true`)
- `set_config` MUST be called BEFORE the first SELECT/INSERT/UPDATE/DELETE on any RLS-protected table within the same transaction
- None sentinel values MUST be converted to `''` (empty string) before passing to `set_config` — PostgreSQL `set_config` does not accept NULL

**Non-compliance consequence**: RLS policies fail silently or reject valid requests; cross-tenant data access becomes possible.

**Verification**:
- Unit tests verify that `set_config` is called exactly 3 times per DB request with correct values
- Unit tests verify `true` as the third argument (transaction-scoped)
- Unit tests verify `None` → `''` conversion
- Tests verify `set_config` is called before any DB query (mock call order inspection)

---

## NFR-U2-SEC-02: No Platform Tenant ID Leakage (SECURITY — BLOCKING)

**Category**: Security
**Priority**: Critical

**Requirement**: `platform_tenant_id` MUST NEVER be accepted as a per-call parameter from SDK agent code or API consumers. It MUST only flow through the authenticated HTTP header path (`X-Tenant-ID → middleware → request.state`) or the Event Service injection path (event.platform_tenant_id).

**Specifics**:
- `TenancyMiddleware` is the single source of truth for `platform_tenant_id` on the HTTP path
- `get_platform_tenant_id()` dependency reads from `request.state` only (no query params, no body)
- Service clients in the SDK set `platform_tenant_id` at init time from `DEFAULT_PLATFORM_TENANT_ID`/env var — not per-call
- NATS handlers read `event.platform_tenant_id` which was injected by the authenticated Event Service

**Verification**:
- No route handler accepts `platform_tenant_id` as a query parameter or request body field
- `get_platform_tenant_id` dependency reads from `request.state` only
- `TenantContext`'s `platform_tenant_id` is never accepted as a constructor argument from route handler code

---

## NFR-U2-SEC-03: Cross-Tenant Isolation Invariant (SECURITY — BLOCKING)

**Category**: Security
**Priority**: Critical

**Requirement**: The composite key `(platform_tenant_id, service_tenant_id, service_user_id)` MUST be the complete identity scope for all RLS-protected operations. No partial-key operations are permitted.

**Specifics**:
- `PlatformTenantDataDeletion` methods MUST always include `platform_tenant_id` as the outermost scope
- Any operation that uses `service_tenant_id` MUST also use `platform_tenant_id`
- `get_tenanted_db` always sets all three variables — no "partial activation" variant

**Verification**:
- All abstract method signatures in `PlatformTenantDataDeletion` require `platform_tenant_id`
- Integration tests verify RLS prevents access when `platform_tenant_id` mismatches

---

## NFR-U2-PERF-01: Middleware Overhead (PERFORMANCE — NON-BLOCKING)

**Category**: Performance
**Priority**: Medium

**Requirement**: `TenancyMiddleware.dispatch()` MUST add no more than 1ms of processing overhead per request (p99) exclusive of `call_next()` time.

**Specifics**:
- Header extraction is synchronous string reads — O(1) per request
- No DB access in middleware (guaranteed by BR-U2-01)
- No external calls in middleware

**Acceptance**: This is automatically satisfied by the design (header reads are microsecond operations). No special implementation required; document as verified by design.

---

## NFR-U2-PERF-02: set_config Round-Trips (PERFORMANCE — NON-BLOCKING)

**Category**: Performance
**Priority**: Medium

**Requirement**: The three `set_config` calls MUST execute within the same database connection as the subsequent ORM queries. No additional connection acquisition per request.

**Specifics**:
- `get_tenanted_db` wraps `get_db` — the SAME `AsyncSession` used by `set_config` is yielded for use by ORM queries
- `set_config` calls are async SQL executes within the open transaction — approximately 0.1–0.5ms per call on localhost-equivalent connections
- Three calls × 0.5ms = maximum 1.5ms additional overhead per RLS-protected DB request

**Acceptance**: Acceptable overhead given the security benefit. Verified by design — no special implementation required.

---

## NFR-U2-MAINT-01: Library Isolation (MAINTAINABILITY — NON-BLOCKING)

**Category**: Maintainability
**Priority**: High

**Requirement**: `soorma-service-common` MUST remain a single-purpose shared-infrastructure library with zero coupling to any specific service's business logic.

**Specifics**:
- No imports from `memory_service`, `tracker_service`, `registry_service`, or `sdk`
- No service-specific configuration (no hardcoded URLs, credentials, or service names)
- `get_db` is not imported or defined in `soorma-service-common` — it is provided by each consuming service via FastAPI's `Depends` mechanism

**Verification**:
- `pyproject.toml` has no service-package dependencies
- Code review rejects any cross-service import

---

## NFR-U2-MAINT-02: SDK Dependency Boundary (MAINTAINABILITY — BLOCKING for soorma-common; NON-BLOCKING for soorma-service-common)

**Category**: Maintainability
**Priority**: High

**Requirement**: `soorma-common` (`libs/soorma-common`) MUST NOT acquire FastAPI, Starlette, or SQLAlchemy dependencies. `soorma-service-common` may freely use them.

**Rationale**: `soorma-common` is on the SDK's dependency graph (`sdk/python` imports it). Adding web framework dependencies to `soorma-common` would force them into every SDK user's install.

**Verification**: `soorma-common/pyproject.toml` has no web framework dependencies (checked as part of U1 completion; must not regress).

---

## NFR Summary Table

| ID | Category | Priority | Blocking | Description |
|----|----------|----------|----------|-------------|
| NFR-U2-SEC-01 | Security | Critical | YES | RLS activation completeness |
| NFR-U2-SEC-02 | Security | Critical | YES | No platform_tenant_id leakage |
| NFR-U2-SEC-03 | Security | Critical | YES | Cross-tenant isolation invariant |
| NFR-U2-PERF-01 | Performance | Medium | No | Middleware overhead < 1ms |
| NFR-U2-PERF-02 | Performance | Medium | No | set_config shares connection |
| NFR-U2-MAINT-01 | Maintainability | High | No | Library isolation |
| NFR-U2-MAINT-02 | Maintainability | High | Blocking (soorma-common) | SDK dependency boundary |
