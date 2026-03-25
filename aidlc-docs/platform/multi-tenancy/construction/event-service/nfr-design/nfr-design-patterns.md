# NFR Design Patterns — U7: services/event-service
## Initiative: Multi-Tenancy Model Implementation
**Date**: 2026-03-25

---

## Pattern 1: Dependency-Injected Identity Resolution Boundary

### Problem
Event Service must obtain authoritative platform identity from authenticated context without coupling route logic to a specific transport such as `X-Tenant-ID` headers.

### Design Decision
Use FastAPI dependency injection as the route-facing identity abstraction:
- route depends on `get_platform_tenant_id`
- middleware/auth implementation owns how identity is extracted
- route business logic remains unchanged when auth source later shifts to API key or JWT

### Implementation Model
```python
@router.post("/publish", response_model=PublishResponse)
async def publish_event(
    request: PublishRequest,
    platform_tenant_id: str = Depends(get_platform_tenant_id),
) -> PublishResponse:
    ...
```

### Why this satisfies NFRs
- NFR-ES-01: trusted platform identity source
- NFR-ES-03: maintainable auth evolution boundary
- SECURITY-08: endpoint does not trust caller-supplied platform identity

---

## Pattern 2: Trust-Boundary Metadata Sanitization Pipeline

### Problem
The incoming event envelope contains partially trusted metadata (`tenant_id`, `user_id`) and an untrusted `platform_tenant_id`. Event Service must produce a bus-safe envelope with normalized, required, bounded identity fields.

### Design Decision
Apply a deterministic normalization-and-validation pipeline before publish:
1. trim `tenant_id` and `user_id`
2. convert empty string to `None`
3. require non-empty `tenant_id`
4. require non-empty `user_id`
5. enforce max length 64 for all identity dimensions
6. overwrite `platform_tenant_id` from authenticated context

### Failure Model
Any pipeline failure aborts publish and returns a client error.

### Why this satisfies NFRs
- NFR-ES-02: centralized sanitization
- NFR-ES-05: fail-closed semantics
- SECURITY-05 / SECURITY-15: validated inputs and safe defaults

---

## Pattern 3: Unconditional Platform Identity Overwrite (Anti-Spoofing)

### Problem
Clients may send `event.platform_tenant_id`, intentionally or accidentally. Trusting it would allow cross-tenant spoofing on the event bus.

### Design Decision
Always overwrite:
```python
event.platform_tenant_id = resolved_platform_tenant_id
```
No compare-and-merge behavior. No acceptance of payload platform identity.

### Why this satisfies NFRs
- NFR-ES-01 directly
- BR-U7-01 / BR-U7-08
- TC-ES-003 verification target

---

## Pattern 4: Transitional Default Fallback Isolation

### Problem
Current pre-identity-service mode still needs compatibility when authenticated platform identity is absent. This fallback must not be spread throughout the codebase.

### Design Decision
Isolate fallback to one publish-path resolution branch only:
```python
resolved_platform_tenant_id = platform_tenant_id or DEFAULT_PLATFORM_TENANT_ID
```
No downstream component should implement its own defaulting behavior for publish requests.

### Why this satisfies NFRs
- NFR-ES-04: explicit transitional compatibility
- contains technical debt to one removable location when identity service hardening arrives

---

## Pattern 5: In-Memory Validation Before Publish Call

### Problem
U7 adds no database layer, so all NFR enforcement must happen before calling `event_manager.publish`.

### Design Decision
Keep validation, normalization, overwrite, and rejection entirely in-process and synchronous-with-request.

### Consequences
- negligible latency overhead
- no new infrastructure dependency
- failure is observable before message emission

### Why this satisfies NFRs
- NFR-ES-05: no publish on invalid input
- NFR-ES-07: throughput/availability baseline remains unchanged

---

## Pattern 6: Structured Rejection Logging

### Problem
Validation failures must be diagnosable without leaking full payload contents or spoofed metadata values into logs.

### Design Decision
Emit structured warning/error logs containing:
- event id when parseable
- event type when parseable
- correlation id / trace id when present
- rejected field names / failure reason

Do not log full raw payload bodies as the standard rejection path.

### Why this satisfies NFRs
- NFR-ES-06
- SECURITY-03 / SECURITY-14 logging hygiene expectations

---

## Pattern 7: Machine-Actor Identity Requirement

### Problem
System or automation events still require complete traceability.

### Design Decision
Treat machine/service principals as first-class actors:
- `tenant_id` identifies scoped subject tenancy
- `user_id` identifies the actor, human or machine
- Event Service enforces both as required after sanitization

### Why this satisfies NFRs
- complete subject scoping and actor traceability
- no split model between human and automation events
- aligns with updated Q5 decision and fail-closed validation model
