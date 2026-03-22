# Construction Design PR Gate — soorma-service-common (U2)
## Initiative: Multi-Tenancy Model Implementation
**Date**: 2026-03-22

---

## Context

- **Initiative**: Multi-Tenancy Model Implementation
- **Checkpoint Type**: Construction Design PR Gate (per unit)
- **Unit**: U2 — soorma-service-common
- **Branch**: `dev`
- **Date Generated**: 2026-03-22

---

## Steps

1. Stage the U2 design artifacts:
   ```
   git add aidlc-docs/platform/multi-tenancy/construction/soorma-service-common/
   git add aidlc-docs/platform/multi-tenancy/construction/plans/soorma-service-common-functional-design-plan.md
   git add aidlc-docs/platform/multi-tenancy/construction/plans/soorma-service-common-nfr-requirements-plan.md
   git add aidlc-docs/platform/multi-tenancy/construction/plans/soorma-service-common-nfr-design-plan.md
   git add aidlc-docs/platform/multi-tenancy/aidlc-state.md
   git add aidlc-docs/platform/multi-tenancy/audit.md
   ```

2. Commit:
   ```
   git commit -m "feat(construction): U2 soorma-service-common design complete"
   ```

3. Push branch:
   ```
   git push -u origin dev
   ```

4. Open a pull request on your git host from `dev` targeting `main` (or your default branch).
   Use the PR Title and PR Description provided below.

5. Share the PR with your team:
   - Engineering team: review U2 design artifacts (Functional Design, NFR Requirements, NFR Design)
   - Security reviewer: pay special attention to NFR-U2-SEC-01 through SEC-03 and NFR Design Patterns 1–5

---

## PR Title

`feat(construction): multi-tenancy U2 soorma-service-common — design complete`

---

## PR Description

```
### Initiative Summary

This PR delivers the complete design for **U2 — `libs/soorma-service-common`**, a new shared
FastAPI/Starlette infrastructure library at the heart of soorma-core's multi-tenancy model.

`soorma-service-common` centralises three critical runtime concerns that all backend services
must implement consistently:
1. **Header-based identity extraction** (`TenancyMiddleware`)
2. **PostgreSQL RLS activation** via transaction-scoped `set_config` (`get_tenanted_db`, `set_config_for_session`)
3. **GDPR platform-scoped data deletion contract** (`PlatformTenantDataDeletion` ABC)

This library unblocks Wave 3 units: Memory Service (U4), Tracker Service (U5), and Event Service (U7).

### Key Design Decisions Documented

| Decision | Resolution |
|----------|-----------|
| Q1 — set_config scope | Split: Middleware = headers only; `get_tenanted_db` = set_config + DB session |
| Q3 — GDPR interface | ABC in `soorma-service-common`; concrete impls per service (U4, U5) |
| set_config lifetime | Transaction-scoped (`is_local = true`) — connection pool safety |
| None sentinel | Converted to `''` before `set_config` — PostgreSQL requires string value |

### Security NFRs (Blocking)

Three blocking security NFRs defined and addressed by design:
- **NFR-U2-SEC-01**: RLS activation completeness (set_config x3 before every RLS-protected query)
- **NFR-U2-SEC-02**: No platform_tenant_id leakage (header-only source; never per-call parameter)
- **NFR-U2-SEC-03**: Cross-tenant isolation invariant (composite key mandatory on all operations)

### Engineering Team Review

Functional Design:
- `aidlc-docs/platform/multi-tenancy/construction/soorma-service-common/functional-design/business-logic-model.md`
- `aidlc-docs/platform/multi-tenancy/construction/soorma-service-common/functional-design/business-rules.md`
- `aidlc-docs/platform/multi-tenancy/construction/soorma-service-common/functional-design/domain-entities.md`

NFR Requirements:
- `aidlc-docs/platform/multi-tenancy/construction/soorma-service-common/nfr-requirements/nfr-requirements.md`
- `aidlc-docs/platform/multi-tenancy/construction/soorma-service-common/nfr-requirements/tech-stack-decisions.md`

NFR Design:
- `aidlc-docs/platform/multi-tenancy/construction/soorma-service-common/nfr-design/nfr-design-patterns.md`
- `aidlc-docs/platform/multi-tenancy/construction/soorma-service-common/nfr-design/logical-components.md`

Plans:
- `aidlc-docs/platform/multi-tenancy/construction/plans/soorma-service-common-functional-design-plan.md`
- `aidlc-docs/platform/multi-tenancy/construction/plans/soorma-service-common-nfr-requirements-plan.md`
- `aidlc-docs/platform/multi-tenancy/construction/plans/soorma-service-common-nfr-design-plan.md`
```
---

Once your PR has been reviewed and approved by your team, return to your AI IDE and confirm approval to continue the AI-DLC workflow.
