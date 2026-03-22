# Test Specifications — Narrative
## Unit: soorma-service-common
## Initiative: Multi-Tenancy Model Implementation
## Scope: happy-path-negative
**Unit abbreviation**: SSC = soorma-service-common

---

### TC-SSC-001 — TenancyMiddleware extracts all three identity headers to request.state

**Context**: The core behaviour of `TenancyMiddleware` — it must reliably extract all three tenancy headers from every inbound HTTP request and store them on `request.state`. This is the contract that all downstream FastAPI dependencies depend on. Covers FR-3a.2.

**Scenario description**: An HTTP request carrying all three tenancy headers is processed by a FastAPI app with `TenancyMiddleware` registered. The handler reads the identity values from `request.state`.

**Steps**:
1. Create a minimal FastAPI app with `TenancyMiddleware` registered
2. Send a test request with headers: `X-Tenant-ID: spt_abc`, `X-Service-Tenant-ID: tenant_xyz`, `X-User-ID: user_123`
3. In the route handler, read `request.state.platform_tenant_id`, `request.state.service_tenant_id`, `request.state.service_user_id`

**Expected outcome**: `platform_tenant_id = "spt_abc"`, `service_tenant_id = "tenant_xyz"`, `service_user_id = "user_123"`.

**Scope tag**: happy-path
**Priority**: High
**Source**: soorma-service-common / FR-3a.2
**Construction artifacts**: aidlc-docs/platform/multi-tenancy/construction/soorma-service-common/

---

### TC-SSC-002 — Missing X-Tenant-ID defaults to DEFAULT_PLATFORM_TENANT_ID

**Context**: When a request does not include `X-Tenant-ID`, the middleware must fall back to the default constant from `soorma_common` rather than setting `None`. This prevents downstream queries from running without a platform tenant. Covers FR-3a.2.

**Scenario description**: An HTTP request without `X-Tenant-ID` header is processed; the route handler reads `request.state.platform_tenant_id`.

**Steps**:
1. Create a minimal FastAPI app with `TenancyMiddleware` registered
2. Send a request without the `X-Tenant-ID` header (but with `X-Service-Tenant-ID` and `X-User-ID` present)
3. Read `request.state.platform_tenant_id` in the handler

**Expected outcome**: `platform_tenant_id` equals `DEFAULT_PLATFORM_TENANT_ID` (`"spt_00000000-0000-0000-0000-000000000000"`), not `None`.

**Scope tag**: happy-path
**Priority**: High
**Source**: soorma-service-common / FR-3a.2
**Construction artifacts**: aidlc-docs/platform/multi-tenancy/construction/soorma-service-common/

---

### TC-SSC-003 — get_tenanted_db calls set_config for all three session variables

**Context**: The RLS activation mechanism — `get_tenanted_db` must call `set_config` for all three PostgreSQL session variables within the same database transaction before yielding the session. Without this, RLS policies silently pass (as they did before this initiative). Covers FR-3a.3.

**Scenario description**: A route handler that uses `Depends(get_tenanted_db)` triggers the `set_config` calls when a database session is obtained.

**Steps**:
1. Create a route handler using `Depends(get_tenanted_db)` in a FastAPI app with `TenancyMiddleware` registered
2. Send a request with known tenant headers
3. Inspect (via mock or real DB introspection) that `set_config('app.platform_tenant_id', ...)`, `set_config('app.service_tenant_id', ...)`, and `set_config('app.service_user_id', ...)` were called with the correct values

**Expected outcome**: All three `set_config` calls are made with `transaction=True` (transaction-scoped) and the values match the headers extracted by `TenancyMiddleware`.

**Scope tag**: happy-path
**Priority**: High
**Source**: soorma-service-common / FR-3a.3
**Construction artifacts**: aidlc-docs/platform/multi-tenancy/construction/soorma-service-common/

---

### TC-SSC-004 — get_tenant_context bundles all three identity dims plus tenanted DB session

**Context**: The `TenantContext` convenience bundle is the primary integration point for route handlers. A single `Depends(get_tenant_context)` should provide all three identity dimensions and a tenanted DB session. Covers FR-3a.4 / TenantContext design.

**Scenario description**: A route handler accepts a `TenantContext` via `Depends(get_tenant_context)`. It reads identity dims and uses the DB session.

**Steps**:
1. Register `TenancyMiddleware` in a FastAPI test app
2. Define a route handler with `ctx: TenantContext = Depends(get_tenant_context)`
3. Send a request with all three tenant headers
4. In the handler, inspect `ctx.platform_tenant_id`, `ctx.service_tenant_id`, `ctx.service_user_id`, and `ctx.db`

**Expected outcome**: All three identity dims are populated from the headers; `ctx.db` is a live (tenanted) database session that has had `set_config` called.

**Scope tag**: happy-path
**Priority**: High
**Source**: soorma-service-common / FR-3a.4
**Construction artifacts**: aidlc-docs/platform/multi-tenancy/construction/soorma-service-common/

---

### TC-SSC-005 — PlatformTenantDataDeletion defines the three required abstract methods

**Context**: Services implementing the GDPR deletion interface must implement `delete_by_platform_tenant`, `delete_by_service_tenant`, and `delete_by_service_user`. The abstract base class must enforce this contract correctly. Covers FR-4.1 / FR-3a (ABC).

**Scenario description**: A developer attempts to subclass `PlatformTenantDataDeletion` without implementing all abstract methods. Python raises a `TypeError`.

**Steps**:
1. Import `PlatformTenantDataDeletion` from `soorma_service_common`
2. Define an incomplete subclass that does not implement all three abstract methods
3. Attempt to instantiate the incomplete subclass

**Expected outcome**: `TypeError: Can't instantiate abstract class ... with abstract methods ...` listing the unimplemented methods.

**Scope tag**: happy-path
**Priority**: Medium
**Source**: soorma-service-common / FR-3a (ABC)
**Construction artifacts**: aidlc-docs/platform/multi-tenancy/construction/soorma-service-common/

---

### TC-SSC-006 — set_config_for_session activates RLS variables for NATS-path DB sessions

**Context**: The NATS event handler path has no HTTP request object, so it cannot use `get_tenanted_db`. The `set_config_for_session` helper must activate all three session variables when called with explicit tenant identity values. Covers FR-3a.3 (NATS path).

**Scenario description**: A NATS event handler obtains a DB session directly and calls `set_config_for_session` with explicit identity values before querying.

**Steps**:
1. Obtain a raw database session (simulating the NATS path)
2. Call `set_config_for_session(db, platform_tenant_id="spt_abc", service_tenant_id="t1", service_user_id="u1")`
3. Verify via mock or DB introspection that all three `set_config` calls were made with the correct values

**Expected outcome**: `set_config('app.platform_tenant_id', 'spt_abc', True)`, `set_config('app.service_tenant_id', 't1', True)`, and `set_config('app.service_user_id', 'u1', True)` were all called.

**Scope tag**: happy-path
**Priority**: High
**Source**: soorma-service-common / FR-3a.3
**Construction artifacts**: aidlc-docs/platform/multi-tenancy/construction/soorma-service-common/

---

### TC-SSC-007 — Missing optional service tenant headers result in None in request.state

**Context**: Negative case: `X-Service-Tenant-ID` and `X-User-ID` are optional. When absent, `request.state` should carry `None` for those fields — not raise an error or set empty strings. Covers FR-3a.2.

**Scenario description**: A request carrying only `X-Tenant-ID` (no service tenant or user header) is processed by `TenancyMiddleware`.

**Steps**:
1. Create a FastAPI app with `TenancyMiddleware` registered
2. Send a request with only `X-Tenant-ID: spt_abc` — no `X-Service-Tenant-ID` or `X-User-ID`
3. In the handler, read `request.state.service_tenant_id` and `request.state.service_user_id`

**Expected outcome**: `service_tenant_id` is `None`; `service_user_id` is `None`; no error is raised; the request is processed normally.

**Scope tag**: happy-path-negative
**Priority**: High
**Source**: soorma-service-common / FR-3a.2
**Construction artifacts**: aidlc-docs/platform/multi-tenancy/construction/soorma-service-common/

---

### TC-SSC-008 — get_tenanted_db does not yield session if set_config raises

**Context**: Negative case: if `set_config` fails (e.g., DB connection error), the session must not be yielded to the handler — otherwise the handler might execute queries without RLS activation. Covers FR-3a.3 (error path).

**Scenario description**: `set_config` raises a database error during `get_tenanted_db` execution. The dependency propagates the error rather than silently yielding an insecure session.

**Steps**:
1. Patch the DB session so that `execute(set_config(...))` raises an `SQLAlchemyError`
2. Make a request to a route using `Depends(get_tenanted_db)`
3. Observe the response

**Expected outcome**: An HTTP 500 (or equivalent unhandled server error) is returned. The route handler is NOT called. The session is not yielded.

**Scope tag**: happy-path-negative
**Priority**: High
**Source**: soorma-service-common / FR-3a.3
**Construction artifacts**: aidlc-docs/platform/multi-tenancy/construction/soorma-service-common/

---

### TC-SSC-009 — soorma-service-common does not import FastAPI or Starlette in SDK path

**Context**: Negative/constraint case: the library MUST NOT pull FastAPI/Starlette into the SDK dependency graph. This validates FR-3a.1 — the library is for backend services only, and its existence must not force SDK users to install web framework dependencies.

**Scenario description**: The library's top-level imports are checked to be compatible with use in environments that do not include FastAPI. The SDK's `pyproject.toml` does not list `soorma-service-common` as a dependency.

**Steps**:
1. Inspect `sdk/python/pyproject.toml` — confirm `soorma-service-common` is NOT listed as a dependency
2. Inspect `libs/soorma-service-common/pyproject.toml` — confirm FastAPI/Starlette are listed as dependencies there and only there

**Expected outcome**: `soorma-service-common` does not appear in the SDK's dependency tree. FastAPI/Starlette dependencies are isolated to `soorma-service-common` and the backend services.

**Scope tag**: happy-path-negative
**Priority**: High
**Source**: soorma-service-common / FR-3a.1
**Construction artifacts**: aidlc-docs/platform/multi-tenancy/construction/soorma-service-common/
