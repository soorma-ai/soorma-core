# Construction Design PR Checkpoint — registry
## Initiative: Multi-Tenancy Model Implementation
**Checkpoint Type**: Construction Design PR Gate  
**Unit**: U3 — `services/registry`  
**Branch**: `dev`  
**Date Generated**: 2026-03-22

---

## Instructions

Follow these steps to submit your design for team review before code generation begins.

1. Stage all initiative artifacts (design artifacts, state, audit, plans, and any updated inception artifacts):
   ```
   git add aidlc-docs/platform/multi-tenancy/
   ```

2. Commit:
   ```
   git commit -m "feat: construction design complete for registry (platform/multi-tenancy)"
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

`feat(construction): registry — construction design complete (platform/multi-tenancy)`

---

## PR Description

```markdown
## Unit Summary

**Unit**: U3 — `services/registry`  
**Wave**: 2 (parallel with U2 `soorma-service-common`)  
**Change Type**: Moderate  
**Depends On**: U1 (`libs/soorma-common`, complete)

This unit migrates the Registry Service from a UUID-based tenant identity model to the
platform-wide `VARCHAR(64)` string model established by this initiative. Key changes:

- **Alembic migration** (004): renames `tenant_id UUID` → `platform_tenant_id VARCHAR(64)` on
  `AgentTable`, `EventTable`, and `PayloadSchemaTable` using a `::text` cast.
  Also adds PostgreSQL Row Level Security (RLS) with `ENABLE ROW LEVEL SECURITY`,
  `FORCE ROW LEVEL SECURITY`, and per-table isolation policies — a design-phase addition
  to the inception spec, motivated by SOC2 auditability requirements (consistent DB-layer
  control across all services).
- **ORM models**: `Uuid(as_uuid=True)` → `String(64)` mapped columns with column rename.
- **Dependency layer**: `api/dependencies.py` replaced with a re-export of
  `get_platform_tenant_id` from `soorma-service-common`; `TenancyMiddleware` registered
  in `main.py`.
- **CRUD and service layer**: all `tenant_id: UUID` → `platform_tenant_id: str` across
  agents, events, and schemas CRUD classes and service methods.
- **Configuration**: `IS_LOCAL_TESTING` flag and SQLite/CloudSQL path divergence removed;
  single `DATABASE_URL`-driven async engine.
- **Tests**: UUID-format sentinel replaced with `DEFAULT_PLATFORM_TENANT_ID`
  (`spt_00000000-0000-0000-0000-000000000000`).

## Design Artifacts — registry

- Functional Design:
  - `aidlc-docs/platform/multi-tenancy/construction/registry/functional-design/business-logic-model.md`
  - `aidlc-docs/platform/multi-tenancy/construction/registry/functional-design/business-rules.md`
  - `aidlc-docs/platform/multi-tenancy/construction/registry/functional-design/domain-entities.md`
- NFR Requirements: N/A — not applicable for this unit
- NFR Design: N/A — not applicable for this unit
- Infrastructure Design: N/A — not applicable for this unit
- QA Test Specifications (enriched — construction-phase update):
  - `aidlc-docs/platform/multi-tenancy/inception/test-cases/registry/test-specs-narrative.md` (TC-R-001 through TC-R-011)
  - `aidlc-docs/platform/multi-tenancy/inception/test-cases/registry/test-specs-gherkin.md`
  - `aidlc-docs/platform/multi-tenancy/inception/test-cases/registry/test-specs-tabular.md`
  - `aidlc-docs/platform/multi-tenancy/inception/test-cases/registry/test-case-index.md`
  - `aidlc-docs/platform/multi-tenancy/inception/test-cases/registry/enrichment-delta.md` (change log: TC-R-001/R-006/R-009 enriched; TC-R-010/R-011 added for RLS wiring and SOC2 policy verification)
```

---

Once your PR has been reviewed and approved by your team, return to your AI IDE and confirm approval to continue the AI-DLC workflow.
