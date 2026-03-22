# Business Rules — soorma-service-common (U2)
## Initiative: Multi-Tenancy Model Implementation
**Date**: 2026-03-22

---

## BR-U2-01: Middleware MUST NOT access the database

**Component**: `TenancyMiddleware`
**Rule**: `TenancyMiddleware.dispatch()` MUST perform header extraction only. It MUST NOT open, acquire, or interact with a database session in any way.
**Rationale**: Starlette async middleware cannot safely integrate with FastAPI's dependency-managed DB session lifecycle. Opening DB connections in middleware would bypass commit/rollback/close guarantees and risk connection pool leakage. (Q1 design decision)
**Violation consequence**: RLS set_config would fire in the wrong lifecycle scope, potentially leaving session variables active across unrelated requests.

---

## BR-U2-02: DEFAULT_PLATFORM_TENANT_ID fallback for absent X-Tenant-ID

**Component**: `TenancyMiddleware`
**Rule**: When the `X-Tenant-ID` header is absent or empty, `request.state.platform_tenant_id` MUST be set to `DEFAULT_PLATFORM_TENANT_ID` imported from `soorma_common.tenancy`. It MUST NOT be set to `None`, empty string, or any locally-defined constant.
**Rationale**: The constant's value and its env-var override mechanism are defined once in `soorma-common` (C1). Duplicating or overriding it in `soorma-service-common` would create two sources of truth.
**Enforcement**: Import `DEFAULT_PLATFORM_TENANT_ID` from `soorma_common.tenancy` — do not redefine it.

---

## BR-U2-03: set_config MUST fire before any RLS-protected query

**Component**: `get_tenanted_db`, `set_config_for_session`
**Rule**: The three `set_config` calls MUST execute within the same database transaction as, and BEFORE, any query on an RLS-protected table. There MUST be no DB read or write on an RLS-protected table before `set_config` has been called on that session in the current transaction.
**Rationale**: PostgreSQL evaluates RLS policies at query execution time using `current_setting()`. If `set_config` has not been called before the first query, RLS policies will see empty/stale session variables and either reject the query or return wrong data.
**Enforcement**: `get_tenanted_db` calls `set_config` immediately after the session is yielded by `get_db`, before yielding to the caller. `set_config_for_session` is called by NATS handlers before their first DB query.

---

## BR-U2-04: set_config must use transaction-scoped lifetime (third arg = true)

**Component**: `get_tenanted_db`, `set_config_for_session`
**Rule**: ALL `set_config` calls MUST use `true` as the third argument (transaction-scoped). Using `false` (session-scoped) is prohibited.
**Rationale**: Connection pools reuse connections across requests. Session-scoped `set_config` values persist on the connection after transaction commit, which would leak one request's identity into the next request that reuses that connection — a critical cross-tenant data exposure vulnerability.
**Enforcement**: Code review; automated test verifying `set_config` is called with third arg `true`.

---

## BR-U2-05: None sentinel values must be converted to empty string for set_config

**Component**: `get_tenanted_db`, `set_config_for_session`
**Rule**: When `service_tenant_id` or `service_user_id` is `None`, it MUST be passed to `set_config` as `''` (empty string). `NULL` cannot be passed to `set_config`; it would raise a PostgreSQL error.
**Rationale**: PostgreSQL `set_config` expects a string value. RLS policies handle empty string as "no filter" for optional dimensions (e.g., Registry has no service_tenant_id concept).

---

## BR-U2-06: No FastAPI/Starlette imports in soorma-common (C1) — library boundary

**Component**: All `soorma-service-common` modules
**Rule**: `soorma-service-common` MAY import FastAPI, Starlette, and SQLAlchemy. `soorma-common` (C1) MUST NOT. Any code that requires FastAPI/Starlette must live in `soorma-service-common`, not `soorma-common`.
**Rationale**: `soorma-common` is used by the SDK (`sdk/python`). Adding FastAPI to `soorma-common` would force the SDK to install a FastAPI dependency, which is inappropriate for agent-side code.
**Enforcement**: `soorma-common/pyproject.toml` must never include FastAPI or Starlette in its `dependencies` list.

---

## BR-U2-07: PlatformTenantDataDeletion — composite key rule (partial-key deletion prohibited)

**Component**: `PlatformTenantDataDeletion` (and all concrete implementations)
**Rule**: Deletion operations MUST always include `platform_tenant_id` as the outer scope. Any deletion method that accepts `service_tenant_id` or `service_user_id` MUST also require `platform_tenant_id`. Deleting by `service_tenant_id` alone (without `platform_tenant_id`) is prohibited.
**Rationale**: Without `platform_tenant_id` as the outer scope, a `service_tenant_id` collision across platform tenants could delete data belonging to a different platform tenant — a catastrophic cross-tenant data loss vulnerability.
**Enforcement**: All three abstract methods include `platform_tenant_id` as a mandatory parameter. Concrete implementations must include it in all WHERE clauses.

---

## BR-U2-08: PlatformTenantDataDeletion — all covered tables must be included

**Component**: `PlatformTenantDataDeletion` concrete implementations
**Rule**: Each `delete_by_*` method MUST delete from ALL tables covered by that service. Partial coverage (deleting from some tables but not others for the same service) is prohibited.
**Rationale**: GDPR erasure must be complete. Leaving data in even one table constitutes a GDPR compliance failure.
**Enforcement**: Each concrete implementation must enumerate its covered tables in a docstring; tests must verify deletion from each table.

---

## BR-U2-09: TenantContext.db must be an RLS-activated session

**Component**: `get_tenant_context`, `TenantContext`
**Rule**: The `db` field in `TenantContext` MUST always be a session obtained from `get_tenanted_db` (not from bare `get_db`). `get_tenant_context` MUST depend on `get_tenanted_db`, never `get_db` directly.
**Rationale**: Route handlers that depend on `get_tenant_context` assume RLS is active on the session. If `get_tenant_context` were wired to bare `get_db`, callers would use a non-RLS session while believing RLS is active.

---

## BR-U2-10: soorma-service-common MUST NOT import SDK packages or service-specific code

**Component**: All `soorma-service-common` modules
**Rule**: `soorma-service-common` MUST NOT import from `soorma_nats`, `sdk/python`, `memory_service`, `tracker_service`, `registry_service`, or any other service-specific module.
**Rationale**: `soorma-service-common` is a shared library. Circular or service-specific imports would couple it to its consumers, making it impossible to use without installing all services.
**Enforcement**: `pyproject.toml` dependencies must not reference service packages. Code review rejects any cross-service import.

---

## BR-U2-11: Health/docs endpoints are excluded from TenancyMiddleware processing

**Component**: `TenancyMiddleware`
**Rule**: Requests to the following paths MUST bypass identity extraction and proceed directly to `call_next`: `/health`, `/docs`, `/openapi.json`, `/redoc`.
**Rationale**: Health checks and API documentation endpoints do not process business data. Requiring tenancy headers on these endpoints would break monitoring systems and developer tooling.
**Implementation**: Path check at the start of `dispatch()`; if path matches, call `call_next(request)` immediately without setting `request.state` identity values.
