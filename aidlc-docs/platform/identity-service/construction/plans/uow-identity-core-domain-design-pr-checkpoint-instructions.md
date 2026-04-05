# Construction Design PR Checkpoint Instructions

## Context
- Initiative: platform / identity-service
- Checkpoint Type: Construction Design PR Gate - uow-identity-core-domain
- Branch: dev
- Generated: 2026-04-05T00:33:43Z

## Steps

1. Stage all initiative artifacts (design artifacts, state, audit, plans, and any updated inception artifacts):

```bash
git add aidlc-docs/platform/identity-service/
```

2. Commit:

```bash
git commit -m "feat: construction design complete for uow-identity-core-domain (platform/identity-service)"
```

3. Push branch:

```bash
git push -u origin dev
```

4. Open a pull request on your git host from `dev` targeting `main` (or your default branch).
Use the PR Title and PR Description provided below.

5. Share the PR with your engineering team for design review before code generation begins.

## PR Title
`feat(construction-design): platform/identity-service - uow-identity-core-domain design complete`

## PR Description

```markdown
## Unit Summary
uow-identity-core-domain delivers the core identity-service design for platform tenant onboarding, principal lifecycle governance, token issuance, delegated issuer trust registration, and mapping/collision policy enforcement. This design package is the pre-code-generation contract for security, resilience, and infrastructure behavior before implementation begins.

## Design Artifacts - uow-identity-core-domain

- Functional Design:
  - `aidlc-docs/platform/identity-service/construction/uow-identity-core-domain/functional-design/business-logic-model.md`
  - `aidlc-docs/platform/identity-service/construction/uow-identity-core-domain/functional-design/business-rules.md`
  - `aidlc-docs/platform/identity-service/construction/uow-identity-core-domain/functional-design/domain-entities.md`
- NFR Requirements:
  - `aidlc-docs/platform/identity-service/construction/uow-identity-core-domain/nfr-requirements/nfr-requirements.md`
  - `aidlc-docs/platform/identity-service/construction/uow-identity-core-domain/nfr-requirements/tech-stack-decisions.md`
- NFR Design:
  - `aidlc-docs/platform/identity-service/construction/uow-identity-core-domain/nfr-design/nfr-design-patterns.md`
  - `aidlc-docs/platform/identity-service/construction/uow-identity-core-domain/nfr-design/logical-components.md`
- Infrastructure Design:
  - `aidlc-docs/platform/identity-service/construction/uow-identity-core-domain/infrastructure-design/infrastructure-design.md`
  - `aidlc-docs/platform/identity-service/construction/uow-identity-core-domain/infrastructure-design/deployment-architecture.md`

## QA Test Case Enrichment (Pre-Codegen Gate)
- `aidlc-docs/platform/identity-service/inception/test-cases/uow-identity-core-domain/test-specs-narrative.md`
- `aidlc-docs/platform/identity-service/inception/test-cases/uow-identity-core-domain/test-specs-gherkin.md`
- `aidlc-docs/platform/identity-service/inception/test-cases/uow-identity-core-domain/test-specs-tabular.md`
- `aidlc-docs/platform/identity-service/inception/test-cases/uow-identity-core-domain/test-case-index.md`
- `aidlc-docs/platform/identity-service/inception/test-cases/uow-identity-core-domain/enrichment-delta.md`
```

Once your PR has been reviewed and approved by your team, return to your AI IDE and confirm approval to continue the AI-DLC workflow.
