# Enrichment Delta — registry
## Initiative: Multi-Tenancy Model Implementation
**Unit**: U3 — `services/registry`
**Enrichment Date**: 2026-03-22
**Source Artifacts**: `construction/registry/functional-design/`

---

## Modified Test Cases

| TC ID | Change Summary | Reason | Source Artifact | Finding Reference |
|-------|---------------|--------|-----------------|-------------------|
| TC-R-001 | Title updated to name migration 004 explicitly; steps expanded to verify column *rename* (`tenant_id → platform_tenant_id`), not just type change; unique constraint rebuild added to steps and expected outcome | Inception spec described only the type change. Functional design revealed the column is also renamed and composite unique constraints must be dropped and recreated | `construction/registry/functional-design/business-rules.md` | BR-R10, BR-R11, BR-R12 |
| TC-R-006 | Title and all references updated from `tenant_id / Column(String(64))` to `platform_tenant_id: Mapped[str] / String(64)`; absence of `tenant_id` attribute added to expected outcome | Inception spec used the old attribute name. Functional design confirms the ORM attribute is renamed, not just retyped | `construction/registry/functional-design/business-rules.md` | BR-R15 |
| TC-R-009 | Title updated to emphasise DB-layer enforcement; context expanded with SOC2 evidence framing and `get_tenanted_db → set_config → RLS` activation chain; additional optional step added to verify DB-layer directly; expected outcome updated to reference RLS policy as the enforcement mechanism; technical references added | The functional design added PostgreSQL RLS to Registry (deviation from inception spec). TC-R-009 tests cross-tenant isolation and must now reflect that the isolation mechanism is DB-layer RLS, not only application-layer WHERE clauses. BR-R07b explicitly designates this as the primary SOC2 evidence test | `construction/registry/functional-design/business-rules.md`, `construction/registry/functional-design/business-logic-model.md` | BR-R07b, Design Decision: Adding RLS to Registry |

---

## Added Test Cases

| TC ID | Title | Reason | Source Artifact | Finding Reference |
|-------|-------|--------|-----------------|-------------------|
| TC-R-010 | All Registry v1 route handlers use get_tenanted_db, not bare get_db | Inception spec did not capture the route handler DB dependency requirement. Functional design mandates `Depends(get_tenanted_db)` on all v1 handlers — this is the wiring that activates RLS at runtime. Without this test, the RLS deployment validated by TC-R-011 would never be exercised | `construction/registry/functional-design/business-rules.md` | BR-R06 |
| TC-R-011 | Migration 004 deploys ENABLE and FORCE ROW LEVEL SECURITY with isolation policies on all three Registry tables | RLS was not in the inception spec for Registry (C3 stated no RLS). The functional design added RLS as a SOC2 auditability control (deviation documented in business-logic-model.md). TC-R-001 covers the column rename/retype; TC-R-011 covers the RLS structural deployment — a distinct concern requiring its own test | `construction/registry/functional-design/business-rules.md`, `construction/registry/functional-design/business-logic-model.md` | BR-R07, BR-R07a |

---

## Removed Test Cases

(none)
