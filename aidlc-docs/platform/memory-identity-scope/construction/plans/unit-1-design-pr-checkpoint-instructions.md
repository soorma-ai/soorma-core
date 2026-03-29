# Construction Design PR Checkpoint Instructions

- Initiative: Memory Service Identity-Scope Consistency Fix
- Checkpoint: Construction Design PR Gate - unit-1
- Branch: dev
- Generated: 2026-03-29T22:27:23Z

1. Stage all initiative artifacts (design artifacts, state, audit, plans, and any updated inception artifacts):

```bash
git add aidlc-docs/platform/memory-identity-scope/
```

2. Commit:

```bash
git commit -m "feat: construction design complete for unit-1 (platform/memory-identity-scope)"
```

3. Push branch:

```bash
git push -u origin dev
```

4. Open a pull request on your git host from `dev` targeting `main` (or your default branch).
Use the PR Title and PR Description provided below.

5. Share the PR with your engineering team for design review before code generation begins.

## PR Title
`feat(construction-design): platform/memory-identity-scope - unit-1 design complete`

## PR Description
```markdown
## Unit Summary
Unit `unit-1` defines the shared identity dependency design for `soorma-service-common`, including validation behavior, NFR requirements, and NFR design patterns needed before code generation. Scope is intentionally constrained to shared dependency boundaries while preparing extension-safe patterns for downstream units.

## Design Artifacts - unit-1
- Functional Design:
  - `aidlc-docs/platform/memory-identity-scope/construction/unit-1/functional-design/business-logic-model.md`
  - `aidlc-docs/platform/memory-identity-scope/construction/unit-1/functional-design/business-rules.md`
  - `aidlc-docs/platform/memory-identity-scope/construction/unit-1/functional-design/domain-entities.md`
- NFR Requirements:
  - `aidlc-docs/platform/memory-identity-scope/construction/unit-1/nfr-requirements/nfr-requirements.md`
  - `aidlc-docs/platform/memory-identity-scope/construction/unit-1/nfr-requirements/tech-stack-decisions.md`
- NFR Design:
  - `aidlc-docs/platform/memory-identity-scope/construction/unit-1/nfr-design/nfr-design-patterns.md`
  - `aidlc-docs/platform/memory-identity-scope/construction/unit-1/nfr-design/logical-components.md`
- Infrastructure Design:
  - N/A - not applicable for this unit

## Notes
- `qa-test-cases` inception specs were generated and unit-1 enrichment completed before this PR gate.
- This PR is the required design checkpoint before Unit-1 code generation.
```

Once your PR has been reviewed and approved by your team, return to your AI IDE and confirm approval to continue the AI-DLC workflow.
