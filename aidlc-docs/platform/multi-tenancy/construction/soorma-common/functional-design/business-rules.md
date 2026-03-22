# Business Rules — soorma-common (U1)
## Initiative: Multi-Tenancy Model Implementation
**Date**: 2026-03-22

---

## Module: `soorma_common/tenancy.py`

### BR-U1-01: Env Var Takes Precedence Over Literal Default
- **Rule**: `DEFAULT_PLATFORM_TENANT_ID` MUST be set from `os.environ.get("SOORMA_PLATFORM_TENANT_ID")` at module import time. If the env var is set and non-empty, its value is used. Otherwise, the literal fallback `"spt_00000000-0000-0000-0000-000000000000"` is used.
- **Source**: FR-1.1, FR-1.2, Q6=B (env-var overridable, constant in soorma_common)
- **Rationale**: Enables deployment-time reconfiguration without code changes.

### BR-U1-02: Code Comment Warning Against Production Use
- **Rule**: The constant definition in `tenancy.py` MUST include a plain code comment (not a Python `warnings.warn()` call) that explicitly states: the constant is for development/testing only and MUST NOT be used in production after the Identity Service is implemented.
- **Source**: FR-1.3, NFR-3.3
- **Rationale**: Prevents accidental use in production without adding runtime overhead or disrupting test execution with `DeprecationWarning` noise.

### BR-U1-03: No Format Validation
- **Rule**: Neither `tenancy.py` nor any other U1 change may perform format validation (UUID regex, prefix check, etc.) on tenant or user ID strings. All values are opaque strings.
- **Source**: FR-1.4, NFR-3.2
- **Rationale**: Enables non-UUID platform tenant identifiers (e.g., `spt_...` format) and future extensibility.

### BR-U1-04: Module Dependency Constraint
- **Rule**: `soorma_common/tenancy.py` MUST only import from Python's standard library (`os`). It MUST NOT import FastAPI, Starlette, SQLAlchemy, httpx, or any third-party package other than those already in `pyproject.toml` dependencies.
- **Source**: C1 Boundary (components.md) — SDK compatibility constraint
- **Rationale**: `soorma-common` is used by the SDK (pure Python) — no server-framework dependencies allowed.

### BR-U1-05: Export from Package `__init__.py`
- **Rule**: `DEFAULT_PLATFORM_TENANT_ID` MUST be re-exported from `soorma_common/__init__.py` so consumers can use `from soorma_common import DEFAULT_PLATFORM_TENANT_ID` consistently with the existing import pattern.
- **Source**: Consistency with C1 usage pattern (components.md: "Used by: SDK clients, all backend services, event handlers")
- **Rationale**: All SDK and service code uses `from soorma_common import ...` for shared types; the constant should follow the same pattern.

---

## DTO: `EventEnvelope` in `soorma_common/events.py`

### BR-U1-06: Add `platform_tenant_id` Field as Optional
- **Rule**: `EventEnvelope` MUST include `platform_tenant_id: Optional[str]` with `default=None`. The field is optional because the SDK publishes events before the Event Service injects the value.
- **Source**: FR-6.3, Application Design C1 + C8

### BR-U1-07: `platform_tenant_id` is Server-Side Only — Documented Constraint
- **Rule**: The `platform_tenant_id` field docstring MUST clearly state it is injected by the Event Service from the authenticated `X-Tenant-ID` header, and that SDK agents MUST NOT set this field. Any value set by the SDK will be overwritten by the Event Service.
- **Source**: FR-6.3, FR-6.6, design decision (Application Design round 2)
- **Rationale**: Creates a clear trust boundary — `platform_tenant_id` is authoritative only when set by Event Service.

### BR-U1-08: Update `tenant_id` Docstring to Reflect Service Tenant Semantics
- **Rule**: `EventEnvelope.tenant_id` docstring MUST be updated to: "Service tenant ID — SDK-supplied. Identifies the tenant within the service layer (e.g., memory, tracker). Distinct from `platform_tenant_id`. Passed through the event bus unchanged."
- **Source**: FR-6.1, FR-6.4

### BR-U1-09: Update `user_id` Docstring to Reflect Service User Semantics
- **Rule**: `EventEnvelope.user_id` docstring MUST be updated to: "Service user ID — SDK-supplied. Identifies the user within the service tenant context. Passed through the event bus unchanged."
- **Source**: FR-6.2, FR-6.4

### BR-U1-10: No Validation on `platform_tenant_id` Field
- **Rule**: `EventEnvelope.platform_tenant_id` MUST NOT include any Pydantic `@field_validator` or pattern constraint. It is an opaque string.
- **Source**: NFR-3.2

### BR-U1-11: `platform_tenant_id` Position in Field Ordering
- **Rule**: The `platform_tenant_id` field MUST be placed adjacent to `tenant_id` and `user_id` in the `EventEnvelope` model definition to group related identity fields together.
- **Source**: Code readability standard

---

## Test Coverage Rules

### BR-U1-T01: Test `DEFAULT_PLATFORM_TENANT_ID` resolution
- Verify default value is `"spt_00000000-0000-0000-0000-000000000000"` when env var is absent
- Verify env var override sets the constant value correctly

### BR-U1-T02: Test `EventEnvelope.platform_tenant_id` field
- Verify field defaults to `None` when not provided
- Verify field accepts a valid opaque string
- Verify existing envelope construction (without `platform_tenant_id`) is backward compatible
