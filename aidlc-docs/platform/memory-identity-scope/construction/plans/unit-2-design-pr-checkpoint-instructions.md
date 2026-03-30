# Construction Design PR Checkpoint Instructions - unit-2

- Initiative: Memory Service Identity-Scope Consistency Fix
- Checkpoint: Construction Design PR Gate (unit-2)
- Branch: dev
- Generated: 2026-03-30T04:33:17Z

## Steps

1. Stage all initiative artifacts (design artifacts, state, audit, plans, and any updated inception artifacts):

```bash
git add aidlc-docs/platform/memory-identity-scope/
```

2. Commit:

```bash
git commit -m "feat: construction design complete for unit-2 (platform/memory-identity-scope)"
```

3. Push branch:

```bash
git push -u origin dev
```

4. Open a pull request on your git host from `dev` targeting `main` (or your default branch).
Use the PR Title and PR Description provided below.

5. Share the PR with your engineering team for design review before code generation begins.

## PR Title
`feat(construction-design): platform/memory-identity-scope - unit-2 design complete`

## PR Description
```markdown
## Unit Summary
Unit-2 (Memory Runtime Alignment) finalizes design for applying shared identity validation to user-scoped APIs and aligning runtime service/CRUD predicates with the full identity tuple. The design defines layered fail-closed enforcement, admin authorization boundaries, reusable predicate composition strategy, and NFR-driven traceability before implementation begins.

## Design Artifacts - unit-2

- Functional Design:
  - `aidlc-docs/platform/memory-identity-scope/construction/unit-2/functional-design/business-logic-model.md`
  - `aidlc-docs/platform/memory-identity-scope/construction/unit-2/functional-design/business-rules.md`
  - `aidlc-docs/platform/memory-identity-scope/construction/unit-2/functional-design/domain-entities.md`

- NFR Requirements:
  - `aidlc-docs/platform/memory-identity-scope/construction/unit-2/nfr-requirements/nfr-requirements.md`
  - `aidlc-docs/platform/memory-identity-scope/construction/unit-2/nfr-requirements/tech-stack-decisions.md`

- NFR Design:
  - `aidlc-docs/platform/memory-identity-scope/construction/unit-2/nfr-design/nfr-design-patterns.md`
  - `aidlc-docs/platform/memory-identity-scope/construction/unit-2/nfr-design/logical-components.md`

- Infrastructure Design:
  - N/A - not applicable for this unit
```

Once your PR has been reviewed and approved by your team, return to your AI IDE and confirm approval to continue the AI-DLC workflow.
