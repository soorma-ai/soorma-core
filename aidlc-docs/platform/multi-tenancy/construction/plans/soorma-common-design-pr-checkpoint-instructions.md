# Construction Design PR Gate — soorma-common (U1)
## Initiative: Multi-Tenancy Model Implementation
**Checkpoint Type**: Construction Design PR Gate
**Unit**: soorma-common (U1)
**Branch**: `dev`
**Date Generated**: 2026-03-22T07:28:46Z

---

## Steps

**1. Stage all initiative artifacts:**
```
git add aidlc-docs/platform/multi-tenancy/
```

**2. Commit:**
```
git commit -m "feat: construction design complete for soorma-common (platform/multi-tenancy)"
```

**3. Push branch:**
```
git push -u origin dev
```

**4. Open a pull request** on your git host from `dev` targeting `main` (or your default branch). Use the PR Title and PR Description provided below.

**5. Share the PR with your engineering team** for design review before code generation begins.

---

## PR Title

`feat(construction/design): soorma-common — multi-tenancy U1 design complete`

---

## PR Description

```
## Unit: soorma-common (U1) — Construction Design Review

### Unit Summary

This PR covers the completed construction design for `libs/soorma-common` (U1), the
foundational unit of the multi-tenancy initiative. U1 is a **Wave 1 / Minor** change that
unblocks all other units (U2–U7). It introduces one new module and modifies one existing
shared DTO.

The changes establish the authoritative platform tenant ID constant and add the
`platform_tenant_id` field to `EventEnvelope` — the mechanism by which the Event Service
injects the authenticated platform tenant identity into every event flowing through the
event bus. All downstream units depend on these contracts being stable before they can
proceed.

### Design Artifacts — soorma-common

**Functional Design** (all three required; no other design stages applicable for this unit):
- `aidlc-docs/platform/multi-tenancy/construction/soorma-common/functional-design/business-logic-model.md`
- `aidlc-docs/platform/multi-tenancy/construction/soorma-common/functional-design/business-rules.md`
- `aidlc-docs/platform/multi-tenancy/construction/soorma-common/functional-design/domain-entities.md`

**NFR Requirements**: N/A — not applicable for this library unit (no data stores, no network, no runtime)
**NFR Design**: N/A — not applicable
**Infrastructure Design**: N/A — not applicable

### Code Generation Plan (for awareness)
- `aidlc-docs/platform/multi-tenancy/construction/plans/soorma-common-code-generation-plan.md`

### Key Design Decisions

1. **New module `soorma_common/tenancy.py`**: exports `DEFAULT_PLATFORM_TENANT_ID` constant
   resolved at import time from `SOORMA_PLATFORM_TENANT_ID` env var (fallback:
   `"spt_00000000-0000-0000-0000-000000000000"`). No format validation — opaque string (NFR-3.2).
   Code comment warns against production use (NFR-3.3).

2. **`EventEnvelope.platform_tenant_id: Optional[str]`**: new field defaulting to `None`.
   Authoritative value is injected by Event Service from `X-Tenant-ID` auth header at publish
   time (FR-6.3/6.6). SDK agents MUST NOT set this field. Existing `tenant_id` and `user_id`
   fields retain their values but docstrings are updated to clarify they are service-scoped
   (FR-6.1, FR-6.2, FR-6.4).

3. **No FastAPI/Starlette imports** in `soorma_common/tenancy.py` — SDK compatibility boundary
   enforced (C1 Boundary constraint).

### Reviewers

**Engineering team** — please review:
- Business rules in `business-rules.md` (11 rules BR-U1-01 to BR-U1-11)
- Field semantics and identity dimension model in `business-logic-model.md`
- Files-changed scope in `domain-entities.md`
- Code generation plan step sequence in `soorma-common-code-generation-plan.md`
```

---

Once your PR has been reviewed and approved by your team, return to your AI IDE and confirm approval to continue the AI-DLC workflow.
