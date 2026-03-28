# Application Design Plan

## Stage Objective
Define high-level component boundaries, service responsibilities, interfaces, and dependency patterns for the memory identity-scope consistency fix.

## Plan Checklist
- [x] Confirm design scope and assumptions from requirements.md
- [x] Confirm shared dependency design approach for `require_user_context`
- [x] Define components and responsibilities in `components.md`
- [x] Define component method signatures in `component-methods.md`
- [x] Define services and orchestration in `services.md`
- [x] Define dependency matrix and communication patterns in `component-dependency.md`
- [x] Generate consolidated `application-design.md`
- [x] Validate design consistency across all artifacts

## Clarifying Questions

### Question 1: Shared dependency naming and shape
For the shared dependency in `soorma-service-common`, choose the API style:

A) Single dependency `require_user_context` that validates both `service_tenant_id` + `service_user_id`

B) Two composable dependencies (`require_service_tenant_id`, `require_service_user_id`) and routes compose both

C) Keep current naming (`require_user_id`) but expand behavior to validate both fields

X) Other (please describe after [Answer]:)

[Answer]: A. a user context will always have service tenant and service user.

### Question 2: Validation application strategy in memory API
Where should the dependency be applied in memory service routers?

A) Router-level dependencies for each user-scoped router module (semantic/episodic/procedural/working/plans/sessions/task_context/plan_context)

B) Per-endpoint dependencies on each user-scoped route

C) Mixed approach: router-level by default, per-endpoint overrides where needed

X) Other (please describe after [Answer]:)

[Answer]: A

### Question 3: Semantic public-memory uniqueness scope
For `semantic_memory` entries where `is_public = TRUE`, should uniqueness remain tenant-wide?

A) Yes — public entries unique by platform tenant (`platform_tenant_id + external_id/content_hash`)

B) No — include service tenant too for public entries (`platform_tenant_id + service_tenant_id + external_id/content_hash`)

X) Other (please describe after [Answer]:)

[Answer]: B

### Question 4: Backward compatibility for existing API callers
For clients that currently omit service tenant/user context on user-scoped endpoints:

A) Immediate enforcement: return 400 without compatibility window

B) Temporary compatibility mode with warnings, then enforce in later release

X) Other (please describe after [Answer]:)

[Answer]: A

## Completion Criteria
- All [Answer]: tags completed
- No unresolved ambiguity in dependency strategy, uniqueness scope, or rollout behavior
- All mandatory artifacts generated and internally consistent
