# PR Checkpoint Instructions

## Context
- Initiative: Memory Service Identity-Scope Consistency Fix
- Checkpoint: Inception PR Gate
- Branch: dev
- Generated: 2026-03-29T19:44:27Z

## Steps

1. Stage inception artifacts:

```bash
git add aidlc-docs/platform/memory-identity-scope/
```

2. Commit:

```bash
git commit -m "feat: inception phase complete for platform/memory-identity-scope"
```

3. Push branch:

```bash
git push -u origin dev
```

4. Open a pull request on your git host from `dev` targeting `main` (or your default branch).
Use the PR Title and PR Description provided below.

5. Share the PR with your team:
- Scrum master / EM: review initiative scope, unit-of-work, and story map
- Engineering team: review requirements and application design artifacts

## PR Title
`feat(inception): platform/memory-identity-scope - inception phase complete`

## PR Description

```markdown
## Initiative Summary
This initiative fixes identity-scope inconsistencies in Soorma Core Memory Service by enforcing deterministic user-context requirements and aligning runtime/database scoping behavior. The work hardens private-memory isolation, prevents cross-scope overwrite/collision behavior, and standardizes identity handling via a shared reusable dependency.

Scope includes shared dependency design in soorma-service-common, memory API/service/CRUD predicate alignment, and schema/index/migration alignment with verification-focused tests.

## Key Requirements
- FR-1: Define authoritative identity scope matrix for all memory operations.
- FR-2: Add shared `require_user_context` dependency validating `service_tenant_id` + `service_user_id`.
- FR-3: Apply shared dependency to all user-scoped memory endpoints.
- FR-4/FR-5: Align plans and sessions CRUD predicates to full identity tuple.
- FR-6/FR-7: Align task_context and plan_context predicates and upsert conflict targets.
- FR-8: Update working_memory unique constraint to full scoped uniqueness.
- FR-9: Ensure semantic upsert conflict targets match scoped unique indexes.
- FR-10: Propagate full identity signatures through API -> service -> CRUD layers.
- FR-11: Align SQLAlchemy model unique constraints with scoped runtime behavior.

Non-functional highlights:
- Generic identity validation errors (transport-agnostic wording)
- Admin endpoint compatibility preserved
- Migration safety and reversibility
- Isolation/regression test coverage requirements
- RLS remains platform-tenant scoped by design

## Scrum Master / Engineering Manager Review
- Unit of Work: `aidlc-docs/platform/memory-identity-scope/inception/application-design/unit-of-work.md`
- Story Map: `aidlc-docs/platform/memory-identity-scope/inception/application-design/unit-of-work-story-map.md`

## Engineering Team Review
- Requirements: `aidlc-docs/platform/memory-identity-scope/inception/requirements/requirements.md`
- Application Design Artifacts:
  - `aidlc-docs/platform/memory-identity-scope/inception/application-design/application-design.md`
  - `aidlc-docs/platform/memory-identity-scope/inception/application-design/components.md`
  - `aidlc-docs/platform/memory-identity-scope/inception/application-design/component-methods.md`
  - `aidlc-docs/platform/memory-identity-scope/inception/application-design/services.md`
  - `aidlc-docs/platform/memory-identity-scope/inception/application-design/component-dependency.md`
  - `aidlc-docs/platform/memory-identity-scope/inception/application-design/unit-of-work.md`
  - `aidlc-docs/platform/memory-identity-scope/inception/application-design/unit-of-work-dependency.md`
  - `aidlc-docs/platform/memory-identity-scope/inception/application-design/unit-of-work-story-map.md`
```

Once your PR has been reviewed and approved by your team, return to your AI IDE and confirm approval to continue the AI-DLC workflow.
