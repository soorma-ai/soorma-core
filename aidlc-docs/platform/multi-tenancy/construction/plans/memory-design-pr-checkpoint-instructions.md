# Construction Design PR Checkpoint — memory
## Initiative: Multi-Tenancy Model Implementation
**Checkpoint Type**: Construction Design PR Gate  
**Unit**: U4 — `services/memory`  
**Branch**: `dev`  
**Date Generated**: 2026-03-23

---

## Instructions

Follow these steps to submit your design for team review before code generation begins.

1. Stage all initiative artifacts (design artifacts, state, audit, plans):
   ```
   git add aidlc-docs/platform/multi-tenancy/
   ```

2. Commit:
   ```
   git commit -m "feat: construction design complete for memory (platform/multi-tenancy)"
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

`feat(construction): memory — construction design complete (platform/multi-tenancy)`

---

## PR Description

```markdown
## Unit Summary

**Unit**: U4 — `services/memory`  
**Wave**: 3 (parallel with U5 `services/tracker`, U7 `services/event-service`)  
**Change Type**: Major  
**Depends On**: U1 (`libs/soorma-common`, complete), U2 (`libs/soorma-service-common`, complete)

This is the largest unit in the multi-tenancy initiative. The Memory Service transitions
from a two-column UUID FK identity model (`tenant_id`, `user_id` FKs to reference tables)
to a three-column opaque-string model (`platform_tenant_id`, `service_tenant_id`,
`service_user_id` as `VARCHAR(64)` plain columns) with rebuilt PostgreSQL Row-Level Security.

**Key changes**:

- **Alembic migration 008**: Drop `tenants` and `users` reference tables; drop all FK
  constraints; add three-column identity on 8 tables; rebuild RLS policies with string
  comparison (no `::UUID` cast); `ENABLE ROW LEVEL SECURITY` + `FORCE ROW LEVEL SECURITY`
  on all 8 tables.
- **ORM models** (`models/memory.py`): Remove `Tenant` and `User` model classes; update
  all 8 table classes to use `String(64)` columns instead of `UUID(as_uuid=True)` FKs.
- **Middleware**: Replace local `TenancyMiddleware` with shared `soorma_service_common.TenancyMiddleware`;
  delete `memory_service/core/middleware.py`.
- **Dependencies** (`core/dependencies.py`): Thin re-export of `TenantContext`, `get_tenanted_db`,
  `get_tenant_context` from `soorma-service-common` using factory pattern.
- **Database** (`core/database.py`): Remove `ensure_tenant_exists()` and `set_session_context()`.
- **CRUD layer** (8 files): `(tenant_id: UUID, user_id: UUID)` → `(platform_tenant_id: str,
  service_tenant_id: str, service_user_id: str)` across all signatures and WHERE clauses.
- **Service layer** (8 files): Same signature migration; call sites updated.
- **API routes** (8 + 1 files): `context.tenant_id` / `context.user_id` → `context.platform_tenant_id`
  / `context.service_tenant_id` / `context.service_user_id`; new `admin.py` with 3 GDPR deletion endpoints.
- **MemoryDataDeletion** (`services/data_deletion.py`): New `PlatformTenantDataDeletion` implementation
  covering 6 tables (semantic, episodic, procedural, working memory, task context, plan context).
- **Config**: Remove `is_local_testing`, `default_tenant_name`, `default_user_id`, `default_username`;
  update `default_tenant_id` to `spt_00000000-0000-0000-0000-000000000000`.
- **Tests** (~15 files): Update all fixtures and assertions to three-column identity model.

**RLS Policy Pattern**:
```sql
CREATE POLICY {table}_platform_rls ON {table}
  USING (platform_tenant_id = current_setting('app.platform_tenant_id', true));
```
String comparison — no `::UUID` cast. `missing_ok=true` means unset session variables return
0 rows (defence-in-depth for TC-M-009).

**Security NFRs enforced by this unit**:
- NFR-M-01: RLS enabled on all 8 tables
- NFR-M-03: Transaction-scoped `set_config` via `get_tenanted_db`
- NFR-M-04: Composite key enforcement in all CRUD WHERE clauses

## Design Artifacts — memory

- Functional Design:
  - `aidlc-docs/platform/multi-tenancy/construction/memory/functional-design/domain-entities.md`
  - `aidlc-docs/platform/multi-tenancy/construction/memory/functional-design/business-logic-model.md`
  - `aidlc-docs/platform/multi-tenancy/construction/memory/functional-design/business-rules.md`
- NFR Requirements:
  - `aidlc-docs/platform/multi-tenancy/construction/memory/nfr-requirements/nfr-requirements.md`
  - `aidlc-docs/platform/multi-tenancy/construction/memory/nfr-requirements/tech-stack-decisions.md`
- NFR Design:
  - `aidlc-docs/platform/multi-tenancy/construction/memory/nfr-design/nfr-design-patterns.md`
  - `aidlc-docs/platform/multi-tenancy/construction/memory/nfr-design/logical-components.md`
- Infrastructure Design: N/A — not applicable for this unit

## Security Compliance Summary

| Rule | Status | Rationale |
|------|--------|-----------|
| SECURITY-01 (Encryption at rest/in transit) | N/A | No new infrastructure resources defined in this unit |
| SECURITY-02 (Access logging on network intermediaries) | N/A | No load balancer / API gateway resources defined |
| SECURITY-03 (Application-level logging) | Compliant | Existing logging retained; no PII/secrets in logs |
| SECURITY-04+ | N/A | Not applicable to this unit's scope |
| NFR-M-01 (RLS enforcement) | Compliant — see design artifacts |
| NFR-M-03 (Transaction-scoped set_config) | Compliant — via soorma-service-common |
| NFR-M-04 (Composite key enforcement) | Compliant — CRUD WHERE clauses |
```

---

## Review Checklist

**Engineering/Architecture Review**:
- [ ] Migration 008 ordering correct (drop old policies → FK constraints → columns → tables → rebuild)?
- [ ] RLS policy pattern matches soorma-service-common's expected `set_config` variable names?
- [ ] `MemoryDataDeletion` covers exactly 6 tables (not 8)?
- [ ] Admin endpoints use correct `set_config_for_session` pattern for RLS bypass?
- [ ] Three-column identity covers all 8 ORM models?
- [ ] Re-export pattern in `dependencies.py` maintains backward compatibility for existing imports?

**Security Review**:
- [ ] RLS `FORCE` keyword included (prevents superuser bypass)?
- [ ] `current_setting('app.platform_tenant_id', true)` uses `missing_ok=true`?
- [ ] No partial-key deletion possible without `platform_tenant_id`?
