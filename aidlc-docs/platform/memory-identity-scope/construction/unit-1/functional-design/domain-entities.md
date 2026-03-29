# Unit-1 Domain Entities

## Overview
Unit-1 introduces no new persistence entities. It defines validation behavior around existing request identity context.

## Entity: TenantContext (Existing)
Represents request identity context resolved before route handler logic.

### Relevant Fields
- `platform_tenant_id`: platform tenant identity (already required by broader tenancy model)
- `service_tenant_id`: tenant identity within the developer's application domain
- `service_user_id`: user identity within `service_tenant_id`
- `db` or equivalent request-scoped resources (unchanged by Unit-1)

### Unit-1 Invariants
- For user-scoped routes, `service_tenant_id` and `service_user_id` must both be non-empty.
- Valid context is returned unchanged to preserve downstream contracts.

## Entity: require_user_context Dependency (New Shared Behavior)
A reusable dependency function operating on `TenantContext`.

### Responsibility
- Validate user-scope identity dimensions.
- Enforce fail-fast semantics with HTTP 400 on invalid context.
- Return canonical `TenantContext` on success.

### Composition Role
Acts as one layer in a dependency chain:
- Upstream context resolution dependency
- `require_user_context` (Unit-1)
- Future authorization dependency layers (planned extension seam)

## Value Object: Validation Failure Descriptor (Conceptual)
No separate class is required in Unit-1, but failure states are logically distinct.

### Failure Types
- Missing/empty `service_tenant_id`
- Missing/empty `service_user_id`

### Output Constraint
- HTTP 400 with transport-agnostic generic detail text.

## Boundary Notes
- No database schema or migration entity changes in Unit-1.
- No memory-resource-specific models are introduced in Unit-1.
- Downstream Units (U2/U3) consume this behavior for runtime and schema alignment.
