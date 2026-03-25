# Domain Entities — U7: services/event-service
## Initiative: Multi-Tenancy Model Implementation
**Date**: 2026-03-25

---

## Overview

This unit does not introduce persistent database entities. It defines and sanitizes event metadata at the Event Service trust boundary before publish.

Primary focus:
- normalize and validate event envelope identity metadata
- enforce authoritative `platform_tenant_id` injection
- preserve service-level semantics for `tenant_id` and `user_id`

---

## Updated Domain Entity: EventEnvelope (Transport Entity)

**Source type**: `soorma_common.events.EventEnvelope`

### Identity fields in scope

```python
tenant_id: Optional[str]            # service tenant dimension; must be present after sanitization
user_id: Optional[str]              # service user dimension; must be present after sanitization
platform_tenant_id: Optional[str]   # authoritative platform tenant dimension
```

### Ownership and trust model

- `platform_tenant_id`: Owned by Event Service; always injected/overwritten from authenticated context.
- `tenant_id`: SDK/client-provided service tenant metadata; sanitized by Event Service and required for all events.
- `user_id`: SDK/client-provided service user metadata; sanitized by Event Service and required for all events, including machine/service actors.

### Constraints

- Max length for all identity dimensions: `<= 64` when present.
- IDs are opaque strings; no UUID/prefix/regex enforcement.
- Empty string values are normalized to `None` before required-field checks.

---

## Updated Route Contract Entity: PublishRequest

**Endpoint**: `POST /v1/events/publish`

**Functional-design decision (Q3):** use dependency injection for platform identity resolution.

Target route shape:

```python
async def publish_event(
    request: PublishRequest,
    platform_tenant_id: str = Depends(get_platform_tenant_id),
) -> PublishResponse:
    ...
```

Rationale:
- keeps endpoint decoupled from specific authentication transport details
- supports future migration from `X-Tenant-ID` to API key/JWT without route signature churn

---

## New Logical Entity: SanitizedEventMetadata

A logical projection (not a persisted DTO) applied in publish flow before bus publish.

Fields:
- `platform_tenant_id: str` (authoritative, injected)
- `tenant_id: str` (trimmed + empty-to-None + length-checked; required after sanitization)
- `user_id: str` (trimmed + empty-to-None + length-checked; required after sanitization)

Normalization behavior:
- strip leading/trailing whitespace for all three fields
- convert `""` to `None` before required-field checks
- reject values exceeding 64 characters

---

## Identity Behavior Matrix

| Field | Input Source | Event Service Action | Final Bus Value |
|---|---|---|---|
| `platform_tenant_id` | Authenticated context via DI | Always overwrite | Authenticated value, or `DEFAULT_PLATFORM_TENANT_ID` fallback per Q1 |
| `tenant_id` | Request payload envelope | Sanitize, require non-empty scoped tenant identity, len<=64 | Sanitized value |
| `user_id` | Request payload envelope | Sanitize, require non-empty actor identity, len<=64 | Sanitized value |

---

## Error Entity (Behavioral)

Event Service returns validation failures without publishing when:
- injected `platform_tenant_id` exceeds 64
- payload `tenant_id` is missing/empty after sanitization
- payload `tenant_id` exceeds 64
- payload `user_id` is missing/empty after sanitization
- payload `user_id` exceeds 64
- request schema is malformed

This preserves fail-closed semantics for metadata sanitization and anti-spoofing.

---

## Traceability

- FR-6.3: `platform_tenant_id` is Event-Service-injected; SDK cannot author it
- FR-6.5: Tenancy middleware/dependency used for platform identity extraction
- FR-6.6: publish path injects/overwrites platform tenant before publish
- NFR-1.1: platform tenant originates from authenticated channel only
- TC-ES-002/003/004/005/007/008: covered by route + metadata behavior above
