# Business Logic Model — U7: services/event-service
## Initiative: Multi-Tenancy Model Implementation
**Date**: 2026-03-25

---

## 1. Publish Flow (Authoritative Metadata Injection)

### Goal

Ensure every published envelope carries trusted platform identity while preserving complete service-level subject scoping and ensuring every event has an attributable actor identity.

### Route shape (Q3)

```python
async def publish_event(
    request: PublishRequest,
    platform_tenant_id: str = Depends(get_platform_tenant_id),
) -> PublishResponse:
```

`platform_tenant_id` is resolved via dependency injection to future-proof auth transport changes.

---

## 2. Metadata Sanitization Pipeline (Q5)

For incoming `request.event`:

1. Normalize `tenant_id` and `user_id`:
   - trim whitespace
   - convert empty string to `None`
2. Validate required/optional identity presence:
   - `tenant_id` must be non-null after sanitization
   - `user_id` must be non-null after sanitization
3. Validate identity lengths (`<= 64`) when present:
   - `platform_tenant_id`
   - `tenant_id`
   - `user_id`
4. Enforce anti-spoofing overwrite:
   - `event.platform_tenant_id = resolved_platform_tenant_id`
5. Preserve semantic passthrough:
   - `tenant_id` and `user_id` values remain semantically unchanged after sanitization

Automation case:
- machine/service-originated events must supply both a provisioned service tenant identity and a machine actor identity
- missing `tenant_id` or `user_id` is invalid and must block publish

---

## 3. Platform Tenant Resolution and Fallback (Q1)

Decision:
- Use authenticated context when present
- If absent, fallback to `DEFAULT_PLATFORM_TENANT_ID` for now
- Revisit to stricter behavior when Identity Service and service-to-service auth are available

Resolution order:

```text
resolved_platform_tenant_id = get_platform_tenant_id(...)
if not resolved_platform_tenant_id:
    resolved_platform_tenant_id = DEFAULT_PLATFORM_TENANT_ID
```

Then apply length validation and overwrite into envelope.

---

## 4. Anti-Spoofing Rule (Q2)

Always overwrite unconditionally:

```python
event.platform_tenant_id = resolved_platform_tenant_id
```

No conditional merge behavior. Payload-supplied `event.platform_tenant_id` is never trusted.

---

## 5. Publish Execution Steps

```text
Step 1: Validate request schema (FastAPI/Pydantic)
Step 2: Resolve platform_tenant_id via dependency injection
Step 3: Apply fallback to DEFAULT_PLATFORM_TENANT_ID if required (Q1)
Step 4: Sanitize tenant_id/user_id (trim + empty->None)
Step 5: Validate required scoped identities (`tenant_id` and `user_id` must be present)
Step 6: Validate all present identity dimensions length <= 64
Step 7: Overwrite event.platform_tenant_id with authoritative value
Step 8: Serialize envelope and publish via event_manager
Step 9: Return success response with published event id
```

Failure path:
- any validation failure => reject request and do not publish

---

## 6. Security and Trust Boundary Model

Event Service is the trust boundary for bus metadata integrity:
- trusted identity source: auth dependency output
- untrusted identity source: payload `event.platform_tenant_id`
- partially trusted payload metadata: `tenant_id`/`user_id` (must be sanitized, with both required for full subject scoping and actor identity)

This model supports both current header-based auth and future API-key/JWT extraction behind the dependency layer.

---

## 7. Test Mapping

- TC-ES-001: middleware/dependency populates platform identity context
- TC-ES-002: injected platform id appears on published envelope
- TC-ES-003: spoofed payload platform id is overwritten
- TC-ES-004: fallback path to default platform tenant (current decision)
- TC-ES-005: tenant_id/user_id preserved semantically after sanitization, with subject scope and actor identity retained
- TC-ES-007: malformed request rejected prior to publish
- TC-ES-008: oversized or missing required scoped identity rejected (fail closed)
