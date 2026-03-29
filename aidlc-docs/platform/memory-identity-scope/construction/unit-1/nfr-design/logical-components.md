# Unit-1 Logical Components

## Overview
Unit-1 NFR design uses two explicit logical components to implement quality, security, and maintainability requirements without unnecessary layering.

## Component LC-1: Identity Validation Dependency
### Responsibility
- Validate required user-scope identity dimensions from request context.
- Aggregate validation failures and return one deterministic HTTP 400 response.
- Use centralized default error messages.

### Inputs
- Resolved tenant context object
- Optional request metadata (correlation ID if available)

### Outputs
- Success: pass-through context object
- Failure: HTTP 400 with stable generic error output

### Quality constraints
- No network/database I/O
- Constant-time field checks
- Fail-closed behavior only

## Component LC-2: Logging Adapter Interface Seam
### Responsibility
- Emit structured warning event on validation failure.
- Enforce safe-field whitelist for logs.

### Allowed data
- event_name
- severity
- platform_tenant_id
- failure_reason
- correlation/request identifier

### Disallowed data
- service_tenant_id
- service_user_id
- credentials, raw payloads, PII

### Integration model
- Called by LC-1 only on validation failure path.
- Adapter abstraction allows future routing changes without touching core validation logic.

## Interaction Flow
1. Request context enters LC-1.
2. LC-1 evaluates required identity dimensions.
3. On failure, LC-1 sends structured failure event to LC-2.
4. LC-1 returns aggregated HTTP 400 response.
5. On success, LC-1 returns original context object to route handler.

## Boundary Rationale
- LC-1 keeps core security/business validation deterministic.
- LC-2 isolates observability concerns and field-governance policy.
- Two-component model balances clarity and minimal complexity for Unit-1 scope.
