# Construction Design PR Checkpoint Instructions

## Context
- Initiative: platform / identity-service
- Checkpoint Type: Construction Design PR Gate - uow-cutover-hardening
- Branch: dev
- Generated: 2026-04-15T05:16:43Z

## Steps

1. Stage all initiative artifacts (design artifacts, state, audit, plans, and updated inception test-case specs):

```bash
git add aidlc-docs/platform/identity-service/
```

2. Commit:

```bash
git commit -m "feat: construction design complete for uow-cutover-hardening (platform/identity-service)"
```

3. Push branch:

```bash
git push -u origin dev
```

4. Open a pull request on your git host from `dev` targeting `main` (or your default branch).
Use the PR Title and PR Description provided below.

5. Share the PR with your engineering team for design review before code generation begins.

## PR Title
`feat(construction-design): platform/identity-service - uow-cutover-hardening design complete`

## PR Description

```markdown
## Unit Summary
uow-cutover-hardening completes the FR-11 phase 3 cutover by removing header-only auth behavior, converging active contracts on canonical `tenant_id`, finalizing JWT-only ingress and trusted-caller issuance hardening, and locking in operational trust/telemetry controls for final migration. This design package defines the bounded pre-code-generation contract for hard cutover, verifier hardening, delegated issuer restrictions, and manual rollback readiness without introducing unnecessary new platform tooling.

## Design Artifacts - uow-cutover-hardening

- Functional Design:
  - `aidlc-docs/platform/identity-service/construction/uow-cutover-hardening/functional-design/business-logic-model.md`
  - `aidlc-docs/platform/identity-service/construction/uow-cutover-hardening/functional-design/business-rules.md`
  - `aidlc-docs/platform/identity-service/construction/uow-cutover-hardening/functional-design/domain-entities.md`
- NFR Requirements:
  - `aidlc-docs/platform/identity-service/construction/uow-cutover-hardening/nfr-requirements/nfr-requirements.md`
  - `aidlc-docs/platform/identity-service/construction/uow-cutover-hardening/nfr-requirements/tech-stack-decisions.md`
- NFR Design:
  - `aidlc-docs/platform/identity-service/construction/uow-cutover-hardening/nfr-design/nfr-design-patterns.md`
  - `aidlc-docs/platform/identity-service/construction/uow-cutover-hardening/nfr-design/logical-components.md`
- Infrastructure Design:
  - `aidlc-docs/platform/identity-service/construction/uow-cutover-hardening/infrastructure-design/infrastructure-design.md`
  - `aidlc-docs/platform/identity-service/construction/uow-cutover-hardening/infrastructure-design/deployment-architecture.md`

## QA Test Case Enrichment (Pre-Codegen Gate)
- `aidlc-docs/platform/identity-service/inception/test-cases/uow-cutover-hardening/test-specs-narrative.md`
- `aidlc-docs/platform/identity-service/inception/test-cases/uow-cutover-hardening/test-specs-gherkin.md`
- `aidlc-docs/platform/identity-service/inception/test-cases/uow-cutover-hardening/test-specs-tabular.md`
- `aidlc-docs/platform/identity-service/inception/test-cases/uow-cutover-hardening/test-case-index.md`
- `aidlc-docs/platform/identity-service/inception/test-cases/uow-cutover-hardening/enrichment-delta.md`
```

Once your PR has been reviewed and approved by your team, return to your AI IDE and confirm approval to continue the AI-DLC workflow.