# Unit-2 Business Logic Model

## Purpose
Apply identity-scope enforcement across Memory Service runtime behavior by combining route-level user-context validation with full-identity CRUD/service predicates.

## Scope
- In scope: API router dependency application, service/CRUD signature propagation, predicate alignment for plans/sessions/task_context/plan_context, and semantic upsert conflict-target runtime alignment.
- Out of scope: database schema/index migration execution (deferred to Unit-3), infrastructure changes.

## Chosen Design Decisions
- Q1: A - Apply `require_user_context` as router-level dependency on all user-scoped routers.
- Q2: A - Keep admin routes exempt from `require_user_context`; enforce explicit admin authorization server-side.
- Q3: A - Keep `service_tenant_id` and `service_user_id` mandatory in service and CRUD method signatures.
- Q4: A - Update semantic runtime conflict-target logic in Unit-2; defer schema/index migration to Unit-3.
- Q5: A - Preserve generic HTTP 400 error messages from shared dependency.
- Q6: B - Include behavior scenarios and expected test-module mapping in design artifacts.

## Runtime Flow
1. Request enters a user-scoped memory router.
2. Router-level `require_user_context` validates `service_tenant_id` and `service_user_id`.
3. API handler forwards full identity tuple to service layer.
4. Service layer forwards full identity tuple to CRUD layer without dropping dimensions.
5. CRUD executes list/get/update/delete predicates using full identity tuple:
   - `platform_tenant_id`
   - `service_tenant_id`
   - `service_user_id`
   - resource key (`plan_id`, `session_id`, `task_id`, `plan_id` as applicable)
6. Semantic upsert selects runtime conflict target based on scope rules aligned with approved identity model.

## Admin Boundary Flow
1. Request enters admin router.
2. `require_user_context` is not applied.
3. Route must pass explicit server-side admin authorization checks.
4. Only system/operational actions remain in admin routes.
5. End-user ownership/identity scoped actions are handled by user-scoped routers.

## Signature and Predicate Contract
### Mandatory identity contract
All affected service and CRUD operations must require:
- `platform_tenant_id: str`
- `service_tenant_id: str`
- `service_user_id: str`

### Affected operation groups
- Plans: list/get/update/delete
- Sessions: list/get/update/delete
- Task context: upsert/get/update/delete
- Plan context: upsert/get/update/delete
- Semantic: runtime conflict-target selection and private-scope filtering

## Failure Contract
- Missing user context at user-scoped routes: HTTP 400 from shared dependency with generic message.
- No route-layer message wrapping or status translation in Unit-2.

## Unit-2 Testability Scenarios (Design-Level)
- Scenario U2-S1: Missing identity on user-scoped route returns 400 (generic message, no transport details).
- Scenario U2-S2: Plans and sessions get/list/update/delete enforce full identity tuple.
- Scenario U2-S3: Task context and plan context operations enforce full identity tuple across read/write paths.
- Scenario U2-S4: Admin routes remain exempt from `require_user_context` but require explicit admin authorization checks.
- Scenario U2-S5: Semantic runtime conflict-target behavior matches approved scope decisions pending Unit-3 migration alignment.

## Expected Test Module Mapping
- `services/memory/tests/api/v1/` for route dependency behavior and status contracts.
- `services/memory/tests/services/` for propagation through service layer.
- `services/memory/tests/crud/` for predicate and conflict-target runtime behavior.
- `services/memory/tests/integration/` (if present) for end-to-end scope isolation checks.
