# Domain Entities — soorma-common (U1)
## Initiative: Multi-Tenancy Model Implementation
**Date**: 2026-03-22

---

## Overview

U1 introduces one new module and modifies one existing DTO in `libs/soorma-common`. There are no new domain entities in the traditional persistence sense — this unit deals with shared constants and event envelope metadata.

---

## New Module: `soorma_common/tenancy.py`

### Entity: `DEFAULT_PLATFORM_TENANT_ID` (module-level constant)

| Attribute | Value |
|-----------|-------|
| **Type** | `str` |
| **Value** | `"spt_00000000-0000-0000-0000-000000000000"` (literal fallback) |
| **Override** | `os.environ.get("SOORMA_PLATFORM_TENANT_ID")` — takes precedence if set |
| **Resolution** | At module import time |
| **Scope** | Global constant — same value for entire process lifetime |
| **Validation** | None — opaque string |
| **Re-exported** | Yes — via `soorma_common/__init__.py` |

**Python representation**:
```python
import os

_DEFAULT = "spt_00000000-0000-0000-0000-000000000000"
# WARNING: Development/testing only. MUST NOT be used in production
# once the Identity Service is implemented. See NFR-3.3.
DEFAULT_PLATFORM_TENANT_ID: str = os.environ.get("SOORMA_PLATFORM_TENANT_ID") or _DEFAULT
```

---

## Modified DTO: `EventEnvelope` (`soorma_common/events.py`)

### New field: `platform_tenant_id`

| Attribute | Value |
|-----------|-------|
| **Type** | `Optional[str]` |
| **Default** | `None` |
| **Validation** | None — opaque string |
| **Set by** | Event Service only (server-side, from `X-Tenant-ID` header) |
| **SDK behavior** | MUST NOT be set; Event Service overwrites it regardless |
| **Field position** | Adjacent to `tenant_id` and `user_id` |

### Updated field: `tenant_id`

| Attribute | Change |
|-----------|--------|
| **Type** | `Optional[str]` — unchanged |
| **Default** | `None` — unchanged |
| **Docstring** | Updated to: "Service tenant ID — SDK-supplied. Identifies the tenant within the service layer. Distinct from `platform_tenant_id`. Passed through the event bus unchanged." |

### Updated field: `user_id`

| Attribute | Change |
|-----------|--------|
| **Type** | `Optional[str]` — unchanged |
| **Default** | `None` — unchanged |
| **Docstring** | Updated to: "Service user ID — SDK-supplied. Identifies the user within the service tenant context. Passed through the event bus unchanged." |

---

## Module Dependency Map

```
soorma_common/tenancy.py
  imports: os (stdlib only)
  exports: DEFAULT_PLATFORM_TENANT_ID
  re-exported by: soorma_common/__init__.py

soorma_common/events.py
  modified: EventEnvelope (add platform_tenant_id, update docstrings)
  no new imports required
```

---

## Files Changed in U1

| File | Change Type | Description |
|------|-------------|-------------|
| `libs/soorma-common/src/soorma_common/tenancy.py` | **NEW** | Platform tenant constant + env var resolution |
| `libs/soorma-common/src/soorma_common/events.py` | **MODIFIED** | Add `platform_tenant_id` field to `EventEnvelope`; update `tenant_id` and `user_id` docstrings |
| `libs/soorma-common/src/soorma_common/__init__.py` | **MODIFIED** | Add `DEFAULT_PLATFORM_TENANT_ID` to exports (import from `.tenancy`) |
| `libs/soorma-common/tests/test_tenancy.py` | **NEW** | Tests for constant resolution + env var override |
| `libs/soorma-common/tests/test_events.py` | **MODIFIED** | Add tests for `platform_tenant_id` field on `EventEnvelope` |

---

## Integration Boundaries

U1 is a **dependency-free** unit — it has no upstream dependencies in this initiative. All other units (U2–U7) depend on U1 completing first.

Downstream consumers of U1 artifacts:
- **U2** (`soorma-service-common`): `TenancyMiddleware` defaults to `DEFAULT_PLATFORM_TENANT_ID` when `X-Tenant-ID` header is absent
- **U3** (`services/registry`): uses `DEFAULT_PLATFORM_TENANT_ID` constant in tests
- **U4** (`services/memory`): same as U3
- **U5** (`services/tracker`): reads `event.platform_tenant_id` from enriched `EventEnvelope`
- **U6** (`sdk/python`): SDK service clients default init-time `platform_tenant_id` from `DEFAULT_PLATFORM_TENANT_ID`
- **U7** (`services/event-service`): injects `platform_tenant_id` field into `EventEnvelope` at publish time (using the field defined in U1)
