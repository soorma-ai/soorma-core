# Construction Design PR Checkpoint Instructions

## Context
- Initiative: platform / identity-service
- Checkpoint Type: Construction Design PR Gate - uow-sdk-jwt-integration
- Branch: dev
- Generated: 2026-04-13T22:00:02Z

## Steps

1. Stage all initiative artifacts (design artifacts, state, audit, plans, and updated inception test-case specs):

```bash
git add aidlc-docs/platform/identity-service/
```

2. Commit:

```bash
git commit -m "feat: construction design complete for uow-sdk-jwt-integration (platform/identity-service)"
```

3. Push branch:

```bash
git push -u origin dev
```

4. Open a pull request on your git host from `dev` targeting `main` (or your default branch).
Use the PR Title and PR Description provided below.

5. Share the PR with your engineering team for design review before code generation begins.

## PR Title
`feat(construction-design): platform/identity-service - uow-sdk-jwt-integration design complete`

## PR Description

```markdown
## Unit Summary
uow-sdk-jwt-integration delivers the compatibility-phase SDK and identity-service JWT integration design for canonical JWT tenant propagation, deterministic verifier precedence, bounded fallback behavior, issuance-policy traceability, and idempotent bootstrap safety. This design package is the pre-code-generation contract for migration-safe implementation before final cutover hardening.

## Design Artifacts - uow-sdk-jwt-integration

- Functional Design:
  - `aidlc-docs/platform/identity-service/construction/uow-sdk-jwt-integration/functional-design/business-logic-model.md`
  - `aidlc-docs/platform/identity-service/construction/uow-sdk-jwt-integration/functional-design/business-rules.md`
  - `aidlc-docs/platform/identity-service/construction/uow-sdk-jwt-integration/functional-design/domain-entities.md`
- NFR Requirements:
  - `aidlc-docs/platform/identity-service/construction/uow-sdk-jwt-integration/nfr-requirements/nfr-requirements.md`
  - `aidlc-docs/platform/identity-service/construction/uow-sdk-jwt-integration/nfr-requirements/tech-stack-decisions.md`
- NFR Design:
  - `aidlc-docs/platform/identity-service/construction/uow-sdk-jwt-integration/nfr-design/nfr-design-patterns.md`
  - `aidlc-docs/platform/identity-service/construction/uow-sdk-jwt-integration/nfr-design/logical-components.md`
- Infrastructure Design:
  - `aidlc-docs/platform/identity-service/construction/uow-sdk-jwt-integration/infrastructure-design/infrastructure-design.md`
  - `aidlc-docs/platform/identity-service/construction/uow-sdk-jwt-integration/infrastructure-design/deployment-architecture.md`

## QA Test Case Enrichment (Pre-Codegen Gate)
- `aidlc-docs/platform/identity-service/inception/test-cases/uow-sdk-jwt-integration/test-specs-narrative.md`
- `aidlc-docs/platform/identity-service/inception/test-cases/uow-sdk-jwt-integration/test-specs-gherkin.md`
- `aidlc-docs/platform/identity-service/inception/test-cases/uow-sdk-jwt-integration/test-specs-tabular.md`
- `aidlc-docs/platform/identity-service/inception/test-cases/uow-sdk-jwt-integration/test-case-index.md`
- `aidlc-docs/platform/identity-service/inception/test-cases/uow-sdk-jwt-integration/enrichment-delta.md`
```

Once your PR has been reviewed and approved by your team, return to your AI IDE and confirm approval to continue the AI-DLC workflow.
