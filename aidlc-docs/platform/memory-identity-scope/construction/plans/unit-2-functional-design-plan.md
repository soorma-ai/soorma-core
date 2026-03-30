# Unit-2 Functional Design Plan

## Stage
- Initiative: Memory Service Identity-Scope Consistency Fix
- Unit: unit-2 (Memory Runtime Alignment)
- Phase: CONSTRUCTION
- Stage: Functional Design

## Objective
Design detailed business logic for applying shared identity validation to user-scoped memory APIs and aligning runtime service/CRUD predicates with the full identity tuple.

## Inputs Reviewed
- `inception/application-design/unit-of-work.md`
- `inception/application-design/unit-of-work-story-map.md`
- `inception/requirements/requirements.md`
- Unit-1 code-generation outputs (shared dependency is available for adoption)

## Functional Design Plan Checklist
- [x] Step 1: Analyze unit-2 scope, boundaries, and requirement ownership.
- [x] Step 2: Identify affected routers, services, and CRUD modules for runtime alignment.
- [x] Step 3: Capture clarifications via [Answer] questions below.
- [x] Step 4: Generate functional design artifacts:
  - `construction/unit-2/functional-design/business-logic-model.md`
  - `construction/unit-2/functional-design/business-rules.md`
  - `construction/unit-2/functional-design/domain-entities.md`
- [x] Step 5: Present functional design completion gate for explicit approval.

## Clarification Questions
Please fill all `[Answer]:` fields.

### Question 1
For unit-2 route adoption, what is the preferred enforcement scope for `require_user_context` in memory API routers?

A) Apply as router-level dependency for all user-scoped routers (semantic, episodic, procedural, working, plans, sessions, task_context, plan_context)

B) Apply per-endpoint dependency only on write operations first, then extend later

C) Apply per-endpoint dependency for all operations (read/write) instead of router-level

X) Other (please describe after [Answer]: tag below)

[Answer]: Option A for consistency and safety

### Question 2
For admin route behavior, which policy should functional design enforce?

A) Keep admin endpoints exempt from `require_user_context` and explicitly tenant-scoped only

B) Apply `require_user_context` to admin endpoints too for consistency

C) Split admin endpoints: only destructive admin operations require user context

X) Other (please describe after [Answer]: tag below)

[Answer]: A — Keep admin endpoints exempt from `require_user_context` and explicitly tenant-scoped only. Establish admin pattern now as: (1) admin routes are system/operational scope only, (2) every admin endpoint must have explicit server-side admin authorization checks, (3) no endpoint requiring end-user ownership checks belongs in admin routes.

### Question 3
For plans/sessions/task_context/plan_context CRUD alignment, which signature policy should be designed?

A) Require `service_tenant_id` and `service_user_id` as mandatory parameters across service + CRUD call chains for all affected operations

B) Keep parameters optional in signatures but enforce non-null in runtime guards

C) Introduce a context object parameter instead of explicit tuple parameters in CRUD/service layers

X) Other (please describe after [Answer]: tag below)

[Answer]: A)

### Question 4
For semantic upsert conflict-target alignment in unit-2, what implementation boundary should be used now?

A) Update runtime conflict-target selection logic in CRUD only (schema/index migration deferred to unit-3)

B) Include runtime changes and immediate index migration in unit-2

C) Keep runtime unchanged until unit-3 schema work is complete

X) Other (please describe after [Answer]: tag below)

[Answer]: A)

### Question 5
For failure response behavior when identity is missing on user-scoped routes, which design contract should be explicit?

A) Preserve generic 400 messages from shared dependency as-is

B) Wrap dependency errors at route layer with memory-specific error text

C) Return 422 validation errors to match schema validation style

X) Other (please describe after [Answer]: tag below)

[Answer]: A)

### Question 6
For unit-2 functional design testability guidance (not full test authoring), what should be included in design artifacts?

A) Include behavior scenarios only (no specific test file mapping)

B) Include behavior scenarios plus explicit expected test module mapping in memory service test suite

C) Include only acceptance criteria references, defer scenario details to unit-3

X) Other (please describe after [Answer]: tag below)

[Answer]: B)

## Notes
- If any answer is ambiguous, follow-up clarification questions will be added before artifact generation.
- This file is the source of truth for unit-2 functional design clarifications.
