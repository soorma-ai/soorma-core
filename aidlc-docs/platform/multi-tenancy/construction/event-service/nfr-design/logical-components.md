# Logical Components — U7: services/event-service
## Initiative: Multi-Tenancy Model Implementation
**Date**: 2026-03-25

---

## Overview

U7 introduces no new infrastructure resources. Its logical components are runtime code-path elements inside Event Service that together enforce the approved NFR set before an event reaches the message bus.

---

## Component Map

```text
services/event-service/
├── main.py
│   Registers shared tenancy/auth middleware boundary
│
├── API Route Layer
│   src/api/routes/events.py
│   - publish_event route
│   - FastAPI dependency injection for platform identity
│   - validation rejection boundary
│
├── Identity Resolution Layer
│   soorma_service_common.get_platform_tenant_id
│   - returns authoritative platform identity from authenticated context
│   - hides auth transport specifics from route logic
│
├── Metadata Sanitization Layer
│   publish-path helper logic in route/service
│   - trim tenant_id/user_id
│   - empty-to-None normalization
│   - required-field enforcement for tenant_id/user_id
│   - len<=64 validation
│
├── Anti-Spoofing Enforcement Layer
│   publish-path overwrite of event.platform_tenant_id
│   - discards producer-supplied platform tenant identity
│
├── Event Serialization Layer
│   EventEnvelope.model_dump(...)
│   - serializes sanitized envelope for transport
│
└── Publish Adapter Layer
    event_manager.publish(topic, message)
    - sends validated envelope to configured adapter (NATS/memory)
```

---

## Dependency Flow

```text
HTTP Request
    → Tenancy/Auth Middleware
        populates authenticated request context
    → FastAPI route resolution
        publish_event(request, platform_tenant_id=Depends(...))
    → Metadata Sanitization Layer
        normalize tenant_id/user_id
        enforce required tenant_id/user_id
        validate len<=64
    → Anti-Spoofing Layer
        overwrite event.platform_tenant_id
    → Serialization Layer
        model_dump sanitized envelope
    → event_manager.publish(...)
    → PublishResponse
```

---

## Logical Responsibility Split

| Component | Responsibility | NFR Coverage |
|---|---|---|
| Tenancy/Auth Middleware + DI | Produce authoritative platform identity | NFR-ES-01, NFR-ES-03 |
| Route-level sanitization logic | Normalize and validate service metadata | NFR-ES-02, NFR-ES-05 |
| Overwrite logic | Prevent spoofing of platform identity | NFR-ES-01 |
| Logging logic | Structured rejection/diagnostic output | NFR-ES-06 |
| Event manager | Existing transport abstraction; unchanged | NFR-ES-07 |

---

## No New Infrastructure Required

U7 NFR design adds no:
- database
- cache
- queue
- external auth service call in publish path
- persistent identity store

This keeps the unit within the current operational baseline while strengthening validation and trust-boundary behavior.

---

## Test-Relevant Components

The following logical components must be exercised in code generation/tests:
- DI-based platform identity resolution
- fallback branch to `DEFAULT_PLATFORM_TENANT_ID`
- required `tenant_id` and `user_id` enforcement
- anti-spoofing overwrite of `platform_tenant_id`
- no-publish path on validation failure
- structured rejection logging hooks
