# Requirements Verification Questions
## Memory Service Identity-Scope Consistency Fix

Please answer the questions below by filling in the `[Answer]:` tag under each question.

---

## Question 1: Scope Model Decision (Core Architecture)

The issue presents two options for how `task_context` and `plan_context` should be scoped. All other resource types (semantic, episodic, procedural, working memory, plans, sessions) will follow user-scoped semantics (Option A). The decision here is specifically for orchestration state tables.

**Option A (recommended)** — full user-scope consistency:
- `task_context` and `plan_context` operations require `service_user_id`
- All get/update/delete predicates include `service_user_id`
- Benefit: uniform security model, no exceptions

**Option B** — tenant-shared orchestration state:
- `task_context` and `plan_context` remain tenant-scoped on get/update/delete
- `service_user_id` stored on write for audit only, NOT used for read/update/delete filtering
- Benefit: simpler worker-to-worker state passing without user propagation
- Tradeoff: different scope rules for orchestration vs memory tables

A) Option A — full user-scoped (require `service_user_id` for ALL memory operations including task_context / plan_context)

B) Option B — tenant-shared orchestration: keep task_context and plan_context tenant-scoped for get/update/delete; require user for all other resource types

X) Other (please describe after `[Answer]:` tag below)

[Answer]: A

**Rationale**: The Soorma two-tier tenancy model guarantees that every interaction — including automation, triggers, and machine-initiated tasks — carries a concrete `service_user_id` (e.g., a machine user identity). This is an architectural premise, not an implementation detail. Given this guarantee:

- The main concern with Option A (Worker-to-Worker handoffs losing user context) is a non-issue: the SDK event envelope always propagates identity, and any failure to do so is a **developer bug that Option A surfaces loudly** (404/400) rather than silently writing to wrong scope.
- System-initiated tasks use machine user identities (e.g., `agent-scheduler`), so `service_user_id` is never `None` for legitimate callers.
- A uniform model (Option A) means no exceptions table to maintain, stronger audit trail, and fail-fast on propagation bugs.

Option B was the issue's conservative recommendation anticipating environments where machine-user propagation is not guaranteed. Since Soorma's architecture does guarantee it, Option A is the stronger and simpler choice.

---

## Question 2: Plans and Sessions CRUD Alignment

Currently `list` is user-filtered but `get` / `update` / `delete` are tenant-only scoped. The fix aligns them. The question is the alignment direction:

A) Add `service_user_id` filter to `get` / `update` / `delete` — user can only touch their own plans/sessions (stricter, consistent with user-owned semantics)

B) Remove `service_user_id` filter from `list` — make plans/sessions fully tenant-scoped in all operations (looser; tenant admin can see all)

C) Keep the inconsistency as-is — do NOT touch plans/sessions CRUD for now

X) Other (please describe after `[Answer]:` tag below)

[Answer]: A

---

## Question 3: Working Memory — Unique Constraint Fix

Currently the unique constraint on `working_memory` is `(plan_id, key)` only, but reads/deletes filter on `service_user_id`. This allows cross-user overwrite. Fix options:

A) Change unique constraint to `(platform_tenant_id, service_user_id, plan_id, key)` — fully user-isolated; requires a migration to drop old constraint and create new one

B) Remove `service_user_id` filter from reads/deletes — make working memory plan-scoped (any user in tenant can read/write a plan's working state; consistent with orchestration-internal use)

C) Keep `(plan_id, key)` unique, keep user filter on reads/deletes — document the known collision risk as acceptable for now

X) Other (please describe after `[Answer]:` tag below)

[Answer]: A

---

## Question 4: Missing `service_user_id` Validation — Response Code

When a user-required endpoint is called without `X-User-ID` header, what HTTP error should be returned?

A) `400 Bad Request` with body `{"detail": "service_user_id is required for this operation"}`

B) `401 Unauthorized` with body `{"detail": "Missing required identity: X-User-ID header"}`

C) `403 Forbidden`

X) Other (please describe after `[Answer]:` tag below)

[Answer]: A. lets keep the error generic, we might change mechanics from header to something else.

---

## Question 5: Where to Enforce Missing User Validation

A) In each individual route handler via a helper dependency (keeps soorma-service-common unchanged)

B) In soorma-service-common as a new `require_user_id` FastAPI dependency that raises on `None` service_user_id (shared utility; changes the shared lib)

C) In the service layer (not at the API/route layer)

X) Other (please describe after `[Answer]:` tag below)

[Answer]: would like this a shared lib so that other services can also use it. will be new dep, so that only enforce when needed. also, signature / design might change later, e.g. may introduce role in future, so another reason why this needs to be shared and reusable.

---

## Question 6: Backfill Strategy for Existing Data

Existing records in `working_memory` that were written under the old `(plan_id, key)` constraint may have ambiguous user ownership.

A) Write-only migration — add new constraint, do NOT backfill; old records without a concrete user_id get NULL/empty (acceptable since this is development data)

B) Soft migration — add constraint but allow existing NULL-user records to coexist; new writes must have user; old records are not altered

C) No migration to working_memory unique constraint for now — only fix CRUD predicates and API validation; leave constraint change as a separate follow-up

X) Other (please describe after `[Answer]:` tag below)

[Answer]: A

---

## Question 7: Extensions
### Team Collaboration Review Gates

Is this fix a **solo effort** (one developer) or a **team-based project** requiring PR review gates?

AI-DLC supports team-based development by enabling **human review gates** at critical workflow checkpoints:
1. **After Inception** — scope, requirements, and planned units reviewed via PR before construction begins
2. **After each unit's design** — detailed functional design reviewed per unit before code generation

A) Enable team review gates — I am working with a team and we use PRs as collaboration checkpoints

B) Skip team review gates — this is a solo effort; no PR gates needed at AI-DLC checkpoints

X) Other (please describe after `[Answer]:` tag below)

[Answer]: a

---

## Question 8: JIRA Tickets Extension

Should JIRA ticket content be generated at the end of the Inception phase?

A) Yes — generate JIRA tickets at end of Inception (Epic + Story per unit)

B) No — skip JIRA ticket generation

X) Other (please describe after `[Answer]:` tag below)

[Answer]: b

---

## Question 9: QA Test Cases Extension

Should structured QA test case specifications be generated from the units of work and functional requirements?

A) Yes — generate QA test case specs (A3: comprehensive — happy path, negative, edge cases, boundary conditions)

B) Yes — but happy path + basic negative cases only (A2)

C) Yes — happy path only (A1)

D) No — skip QA test case generation

X) Other (please describe after `[Answer]:` tag below)

[Answer]: b, scope of QA test plans should not be unit tests (that should be part of code generation and development). this QA test plan is for formal QA of end to end functionality.

---

## Question 10: Security Extension

Should security baseline rules be enforced as blocking constraints throughout this initiative?

A) Yes — enforce all SECURITY rules as blocking constraints (recommended; this is a security-sensitive identity fix)

B) No — skip security rules

X) Other (please describe after `[Answer]:` tag below)

[Answer]: a
