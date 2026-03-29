# Unit-2 Domain Entities

## Overview
Unit-2 introduces no new persisted business entities. It strengthens how existing identity and memory entities interact across API, service, and CRUD boundaries.

## Identity Tuple (Value Object Contract)
Canonical runtime identity dimensions used across aligned operations:
- `platform_tenant_id`
- `service_tenant_id`
- `service_user_id`

### Invariants
- For user-scoped operations, all three dimensions are required.
- Tuple values must be propagated unchanged from API to service to CRUD layers.

## Entity: Route Scope Category (Conceptual)
Defines which identity/authorization policy applies.

### Categories
- User-scoped routes: require `require_user_context`.
- Admin routes: exempt from `require_user_context`, but require explicit admin authorization.

## Entity: Plan (Existing)
### Identity ownership contract
- CRUD operations are scoped by full identity tuple plus `plan_id` for single-resource operations.
- List operations are scoped by full identity tuple.

## Entity: Session (Existing)
### Identity ownership contract
- CRUD operations are scoped by full identity tuple plus `session_id` for single-resource operations.
- List operations are scoped by full identity tuple.

## Entity: TaskContext (Existing)
### Identity ownership contract
- Upsert/get/update/delete are scoped by full identity tuple plus `task_id`.
- Runtime conflict-target behavior must align with full identity semantics.

## Entity: PlanContext (Existing)
### Identity ownership contract
- Upsert/get/update/delete are scoped by full identity tuple plus `plan_id`.
- Runtime conflict-target behavior must align with full identity semantics.

## Entity: SemanticMemory (Existing)
### Identity ownership contract
- Private-scope runtime behavior must apply full identity semantics.
- Unit-2 updates runtime conflict-target selection logic only.
- Constraint/index physical alignment is completed in Unit-3.

## Entity: require_user_context Dependency (Imported Behavior)
### Responsibility in Unit-2
- Serves as gatekeeper for all user-scoped routers.
- Ensures missing identity is rejected with generic HTTP 400 before service/CRUD execution.

## Entity: Admin Authorization Policy (Conceptual)
Defines minimum authorization behavior for admin routes.

### Policy constraints
- Must be explicit and server-enforced per endpoint.
- Must be separate from user ownership enforcement rules.
- Must not depend on client-side hiding or trust assumptions.

## Boundary Notes
- Unit-2 does not alter database schema definitions.
- Unit-2 prepares runtime parity; Unit-3 finalizes schema/index migration parity.
