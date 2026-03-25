# Construction Design PR Checkpoint — event-service
## Initiative: Multi-Tenancy Model Implementation
**Checkpoint Type**: Construction Design PR Gate  
**Unit**: U7 — `services/event-service`  
**Branch**: `dev`  
**Date Generated**: 2026-03-25

---

## Instructions

Follow these steps to submit your design for team review before code generation begins.

1. Stage all initiative artifacts (design artifacts, state, audit, plans, and updated inception test-case artifacts):
   ```
   git add aidlc-docs/platform/multi-tenancy/
   ```

2. Commit:
   ```
   git commit -m "feat: construction design complete for event-service (platform/multi-tenancy)"
   ```

3. Push branch:
   ```
   git push -u origin dev
   ```

4. Open a pull request on your git host from `dev` targeting `main` (or your default branch).
   Use the PR Title and PR Description provided below.

5. Share the PR with your engineering team for design review before code generation begins.

---

## PR Title

`feat(construction): event-service — construction design complete (platform/multi-tenancy)`

---

## PR Description

```markdown
## Unit Summary

**Unit**: U7 — `services/event-service`  
**Wave**: 3 (parallel wave with U4/U5)  
**Change Type**: Moderate  
**Depends On**: U1 (`libs/soorma-common`), U2 (`libs/soorma-service-common`) — complete

This unit defines the Event Service trust-boundary behavior for multi-tenancy event metadata.
Key design outcomes:

- Event Service is authoritative for `platform_tenant_id` and always overwrites payload-supplied values.
- Route-level platform identity uses dependency injection (`Depends(get_platform_tenant_id)`) to preserve auth-source abstraction.
- Central sanitization and validation pipeline enforces:
  - trim and empty-to-None normalization for `tenant_id`/`user_id`
  - mandatory `tenant_id` and `user_id` for all events (including machine actors)
  - max length 64 across identity dimensions
- Transitional fallback to `DEFAULT_PLATFORM_TENANT_ID` remains explicitly isolated.
- Publish path is fail-closed: validation failures return client error and do not publish to bus.
- Structured rejection logging avoids full payload leakage.
- Inception QA specs enriched with design-level assertions; new negative test cases added for mandatory identity checks.

## Design Artifacts — event-service

- Functional Design:
  - `aidlc-docs/platform/multi-tenancy/construction/event-service/functional-design/domain-entities.md`
  - `aidlc-docs/platform/multi-tenancy/construction/event-service/functional-design/business-logic-model.md`
  - `aidlc-docs/platform/multi-tenancy/construction/event-service/functional-design/business-rules.md`
- NFR Requirements:
  - `aidlc-docs/platform/multi-tenancy/construction/event-service/nfr-requirements/nfr-requirements.md`
  - `aidlc-docs/platform/multi-tenancy/construction/event-service/nfr-requirements/tech-stack-decisions.md`
- NFR Design:
  - `aidlc-docs/platform/multi-tenancy/construction/event-service/nfr-design/nfr-design-patterns.md`
  - `aidlc-docs/platform/multi-tenancy/construction/event-service/nfr-design/logical-components.md`
- Infrastructure Design: `N/A — not applicable for this unit`
- QA Test Specifications (enriched):
  - `aidlc-docs/platform/multi-tenancy/inception/test-cases/event-service/test-specs-narrative.md`
  - `aidlc-docs/platform/multi-tenancy/inception/test-cases/event-service/test-specs-gherkin.md`
  - `aidlc-docs/platform/multi-tenancy/inception/test-cases/event-service/test-specs-tabular.md`
  - `aidlc-docs/platform/multi-tenancy/inception/test-cases/event-service/test-case-index.md`
  - `aidlc-docs/platform/multi-tenancy/inception/test-cases/event-service/enrichment-delta.md`
```

---

Once your PR has been reviewed and approved by your team, return to your AI IDE and confirm approval to continue the AI-DLC workflow.
