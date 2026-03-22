# Business Logic Model — soorma-common (U1)
## Initiative: Multi-Tenancy Model Implementation
**Date**: 2026-03-22

---

## Overview

U1 introduces two business logic concerns to `libs/soorma-common`:

1. **Platform Tenant Constant Resolution** — a runtime-configurable default platform tenant ID used throughout the system as a fallback during development and testing. It resolves via a simple environment variable lookup pattern.

2. **Platform Tenant Identity on Event Envelopes** — `EventEnvelope` gains a `platform_tenant_id` field that carries the injected platform tenant context through the event bus. The authoritative source of this value is the Event Service (injected from the `X-Tenant-ID` auth header). The field is opaque on the envelope; SDK agents must not populate it.

---

## Module: `soorma_common/tenancy.py`

### Business Logic: Constant Resolution

**Flow**:
```
At module import time:
  1. Check environment variable SOORMA_PLATFORM_TENANT_ID
  2. If set and non-empty → use that value
  3. If not set or empty → use literal fallback "spt_00000000-0000-0000-0000-000000000000"
  4. Assign result to module-level constant DEFAULT_PLATFORM_TENANT_ID
```

**Key decisions** (from inception / requirements analysis):
- Resolution happens **at module import time** (not lazily per access) — this is a module-level constant assignment
- The constant is a `str`, never validated as UUID format (NFR-3.2)
- The env var name `SOORMA_PLATFORM_TENANT_ID` is the canonical override mechanism (FR-1.2, Q6=B)
- Value `"spt_00000000-0000-0000-0000-000000000000"` is the fixed fallback for dev/test environments only (FR-1.1)

**Trust model**:
- In production: replaced by values from the future Identity Service
- In development/test: the constant enables local single-tenant testing without a live Identity Service
- The value itself is opaque — no semantic meaning is attached to the `spt_` prefix by this library

---

## DTO: `EventEnvelope.platform_tenant_id`

### Business Logic: Tenant Injection Model

**Flow** (from inception design, FR-6):
```
SDK Agent → POST /events to Event Service
  [platform_tenant_id may be None or absent on the outbound envelope]

Event Service (server-side, authenticated request):
  1. Read X-Tenant-ID header → request.state.platform_tenant_id (set by TenancyMiddleware)
  2. Overwrite/inject event.platform_tenant_id = request.state.platform_tenant_id
  3. Publish enriched envelope to NATS with authoritative platform_tenant_id set

NATS Subscribers (e.g., Tracker):
  1. Read event.platform_tenant_id as the authoritative platform tenant (trusted)
  2. Use for DB scoping (set_config) + RLS enforcement
```

**Field semantics on the envelope** (from FR-6, Application Design):
- `platform_tenant_id`: Injected by Event Service at publish time from authenticated `X-Tenant-ID` header. `Optional[str]`, defaults to `None`. Set to `None` on outbound SDK envelopes — Event Service overwrites it regardless.
- `tenant_id`: **Service tenant ID** — supplied by SDK agent. Identifies which tenant's workspace the agent is operating within. Unchanged through the event bus.
- `user_id`: **Service user ID** — supplied by SDK agent. Identifies the user within the service tenant context. Unchanged through the event bus.

**Identity dimension summary**:

| Field | Dimension | Set by | Trusted by |
|-------|-----------|--------|-----------|
| `platform_tenant_id` | Platform tenant | Event Service (auth header injection) | NATS subscribers |
| `tenant_id` | Service tenant | SDK agent (per-request) | Memory/Tracker service layer |
| `user_id` | Service user | SDK agent (per-request) | Memory/Tracker service layer |

---

## Non-Functional Constraints

- `tenancy.py` MUST NOT import FastAPI, Starlette, SQLAlchemy, or any HTTP framework (SDK compatibility, C1 Boundary constraint)
- `tenancy.py` MUST NOT import from service-specific packages
- No business validation logic on tenant/user ID values — pure opaque strings (NFR-3.2)
