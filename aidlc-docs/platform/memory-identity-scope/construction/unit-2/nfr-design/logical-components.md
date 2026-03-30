# Unit-2 Logical Components

## Overview
Unit-2 NFR design uses a small set of logical components to implement fail-closed runtime enforcement, admin authorization consistency, and predicate reliability.

## Component LC-2-1: User Route Identity Guard
### Responsibility
- Enforce user-context identity requirements at user-scoped route boundary.
- Reject invalid requests early with deterministic HTTP 400 behavior.

### Inputs
- Request-scoped context resolved by existing tenant-context dependency.

### Outputs
- Success: route continues.
- Failure: fail-closed validation response.

## Component LC-2-2: Service Boundary Identity Backstop
### Responsibility
- Re-validate mandatory identity tuple before CRUD calls.
- Prevent bypass when service methods are invoked outside route path.

### Inputs
- Service method identity arguments.

### Outputs
- Success: CRUD execution proceeds.
- Failure: explicit validation exception; no data access.

## Component LC-2-3: Admin Authorization Guard
### Responsibility
- Provide shared authorization logic for privileged admin endpoints.
- Ensure endpoint-level explicit application of admin authorization checks.

### Inputs
- Request auth context and admin policy rules.

### Outputs
- Authorized: admin handler proceeds.
- Unauthorized: deny request.

## Component LC-2-4: Identity Predicate Helper
### Responsibility
- Build canonical full-identity predicates for CRUD queries.
- Provide optional resource-key predicate composition helper.

### Inputs
- `platform_tenant_id`
- `service_tenant_id`
- `service_user_id`
- optional resource key/value pair

### Outputs
- Reusable predicate fragments for query composition.

### Design boundary
- Includes identity-scoping helpers only.
- Excludes business-specific filtering logic.

## Component LC-2-5: Validation Logging Adapter
### Responsibility
- Emit structured warning events for validation failures.
- Enforce allowed/forbidden field policy.

### Allowed data
- event name
- severity
- platform tenant id
- failure reason
- correlation id/request id

### Disallowed data
- service tenant id
- service user id
- secrets/tokens/PII

## Interaction Flow
1. User-scoped request hits LC-2-1 route guard.
2. Route handler calls service methods.
3. LC-2-2 validates identity tuple as mandatory backstop.
4. CRUD path composes predicates using LC-2-4 helper.
5. If validation fails at any guard, LC-2-5 emits structured warning and execution stops.
6. Admin request path uses LC-2-3 guard and follows admin operational flow.

## Boundary Rationale
- LC-2-1 and LC-2-2 implement layered fail-closed defense.
- LC-2-3 isolates privileged authorization from user ownership semantics.
- LC-2-4 controls predicate consistency and reduces drift.
- LC-2-5 centralizes observability and privacy policy for validation events.
