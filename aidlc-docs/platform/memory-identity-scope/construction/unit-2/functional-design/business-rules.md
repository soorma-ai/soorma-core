# Unit-2 Business Rules

## BR-01: Router-Level User Context Enforcement
All user-scoped memory routers must apply `require_user_context` at router level.

- Applies to semantic, episodic, procedural, working, plans, sessions, task_context, plan_context routers.
- Must not rely on per-endpoint manual attachment for this initiative.

## BR-02: Admin Route Exemption Boundary
Admin routes must remain exempt from `require_user_context`.

- Admin routes are tenant-scoped operational/system endpoints.
- Endpoints requiring end-user ownership semantics must not be placed in admin routes.

## BR-03: Explicit Admin Authorization Requirement
Every admin endpoint must have explicit server-side admin authorization checks.

- Authorization must be enforced server-side, not by client/UI behavior.
- Lack of explicit admin auth check is a security violation.

## BR-04: Full Identity Signature Propagation
Affected service and CRUD methods must require `service_tenant_id` and `service_user_id` as mandatory parameters.

- Optional identity parameters are not allowed in aligned call chains.
- No runtime-only null checking as a substitute for required signatures.

## BR-05: Full Identity Predicate Consistency
Plans, sessions, task_context, and plan_context list/get/update/delete operations must filter by full identity tuple.

- Required dimensions: `platform_tenant_id`, `service_tenant_id`, `service_user_id`, plus resource key.
- Read and write paths must use the same identity dimensions.

## BR-06: Semantic Runtime Conflict-Target Alignment (Unit-2 Scope)
Semantic upsert runtime conflict-target logic must be updated in Unit-2 to match approved identity scope rules.

- Runtime logic changes are in-scope now.
- Schema/index migration alignment remains deferred to Unit-3.

## BR-07: Shared Dependency Error Contract Preservation
When user context is missing on user-scoped routes, preserve shared dependency generic HTTP 400 responses.

- No route-layer message rewriting.
- No status code conversion (e.g., to 422) in Unit-2.

## BR-08: Backward-Compatible Admin Behavior
Admin endpoint behavior must remain intentional and explicit after user-scoped hardening.

- User-scoped route hardening must not break admin route operational use cases.

## BR-09: Testability Coverage Rule
Functional design must define behavior scenarios and expected test module mapping.

- Scenario coverage must include route validation, propagation, predicate correctness, and admin-boundary behavior.
- Mapping must point to expected memory service API/service/CRUD test locations.
