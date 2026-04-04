# Construction Design PR Checkpoint Instructions - uow-shared-auth-foundation

## Purpose
Open and merge a design-only PR checkpoint after completing Construction design stages and before Code Generation.

## Confirmed Branch
- Working branch: dev

## Design Artifact Scope (this checkpoint)
- aidlc-docs/platform/identity-service/construction/uow-shared-auth-foundation/functional-design/
- aidlc-docs/platform/identity-service/construction/uow-shared-auth-foundation/nfr-requirements/
- aidlc-docs/platform/identity-service/construction/uow-shared-auth-foundation/nfr-design/
- aidlc-docs/platform/identity-service/construction/uow-shared-auth-foundation/infrastructure-design/
- aidlc-docs/platform/identity-service/inception/test-cases/uow-shared-auth-foundation/
- aidlc-docs/platform/identity-service/construction/test-cases/uow-shared-auth-foundation/enrichment-delta.md
- aidlc-docs/platform/identity-service/aidlc-state.md
- aidlc-docs/platform/identity-service/audit.md

## Suggested Commands
```bash
# 1) Validate changes
cd /Users/amit/ws/github/soorma-ai/soorma-core
git status --short

# 2) Stage design-checkpoint artifacts
git add aidlc-docs/platform/identity-service/

# 3) Commit (example)
git commit -m "docs(identity-service): checkpoint construction design for uow-shared-auth-foundation"

# 4) Push branch
git push origin dev

# 5) Open PR from dev to main and request review
```

## Gate Rule
Do not start Code Generation for this unit until this design PR checkpoint is approved.
