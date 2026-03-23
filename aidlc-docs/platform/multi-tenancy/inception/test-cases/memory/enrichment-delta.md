# Enrichment Delta — memory
## Unit: memory
## Initiative: Multi-Tenancy Model Implementation
## Enrichment performed: Construction Phase — U4 (services/memory)
## Sources used:
- `aidlc-docs/platform/multi-tenancy/construction/memory/functional-design/domain-entities.md`
- `aidlc-docs/platform/multi-tenancy/construction/memory/functional-design/business-rules.md`
- `aidlc-docs/platform/multi-tenancy/construction/memory/functional-design/business-logic-model.md`
- `aidlc-docs/platform/multi-tenancy/construction/memory/nfr-design/nfr-design-patterns.md`

---

## Modified Test Cases

| TC ID | Change Summary | Reason | Source Artifact | Finding Reference |
|-------|---------------|--------|-----------------|-------------------|
| TC-M-001 | Added migration filename (`008_multi_tenancy_three_column_identity.py`), exact drop ordering (RLS → FK constraints → tables), specific info_schema assertion query | Inception lacked technical execution details needed by implementers | business-logic-model.md (Section 1), domain-entities.md (Dropped Entities) | business-rules.md BR-U4-04 |
| TC-M-002 | Added all 8 table names explicitly, exact column spec (`String(64)` = `VARCHAR(64)`), ORM module path, migration step numbers, updated unique constraint list | Inception specified generic column types; construction defined exact `VARCHAR(64)` type and `String(64)` ORM type per BR-U4-05; also confirmed `SemanticMemory.user_id` was truncated from String(255) | domain-entities.md (Updated Entities, Identity Summary Table), business-logic-model.md (Step 3–8) | business-rules.md BR-U4-05 |
| TC-M-003 | Added `get_tenanted_db` module path, `set_config` call with `transaction=true` (3rd arg), RLS policy name pattern (`{table_name}_platform_rls`), `missing_ok=true` semantics | Inception said "set session variable via set_config" — construction specifies exact dependency module and set_config signature (transaction-scoped = `true`); RLS policy name pattern was undefined at inception | functional-design/business-logic-model.md (Section 3), nfr-design-patterns.md (Pattern 1 & 2) | business-rules.md BR-U4-03 |
| TC-M-004 | Added TenancyMiddleware source module, exact header-to-state mapping, semantic router module path, DTO field requirement (BR-U4-11) | Inception said "TenancyMiddleware registered" — construction specifies it must come from `soorma_service_common`, the exact header names, and that response DTOs must expose the three-column identity | domain-entities.md (SemanticMemory), nfr-design-patterns.md (Pattern 2) | business-rules.md BR-U4-09, BR-U4-11 |
| TC-M-005 | Added `MemoryDataDeletion` class path, parent class (`PlatformTenantDataDeletion`), exact 6 covered tables, explicit note that `plans`/`sessions` are NOT covered | Construction defined the exact 6-table scope for GDPR deletion (BR-U4-06); parent class from `soorma_service_common` was not known at inception | domain-entities.md (New Entity: MemoryDataDeletion), business-rules.md BR-U4-06 | business-rules.md BR-U4-06 |
| TC-M-006 | Added method signature, exact WHERE pattern (Pattern 3: composite key) | Inception described the behaviour; construction defines the exact method signature and composite WHERE enforcement mechanism | nfr-design-patterns.md (Pattern 3) | business-rules.md BR-U4-02 |
| TC-M-007 | Corrected expected outcome: file is DELETED (not just empty); added full module path for deleted file, exact import statement, `app.add_middleware` call | Construction specifies file deletion (BR-U4-09 — "no two middleware instances"); inception step was "check if file exists" without specifying expected path | business-logic-model.md (Section 4: middleware replacement), business-rules.md BR-U4-09 | business-rules.md BR-U4-09 |
| TC-M-008 | Added exact policy name pattern, full SQL expression with `missing_ok=true`, `FORCE ROW LEVEL SECURITY` requirement, migration step references (step 13+14) | Inception specified "string comparison" generically; construction defines exact SQL and the critical `FORCE ROW LEVEL SECURITY` clause (prevents superuser test env bypass) | nfr-design-patterns.md (Pattern 1) | business-rules.md BR-U4-04, nfr-design-patterns.md Pattern 1 |
| TC-M-009 | Added `missing_ok=true` → `''` return value explanation, test implementation (raw `AsyncSession` via `create_async_engine`), confirmation no PostgreSQL error is raised | Construction defines the RLS policy with `missing_ok=true` which prevents errors — this is a key behaviour change from the old `::UUID`-based policies; inception step was vague ("direct query without set_config") | nfr-design-patterns.md (Pattern 1, `missing_ok` semantics) | business-rules.md BR-U4-03 |
| TC-M-010 | Added `TenancyMiddleware` behaviour when header absent (`service_tenant_id=""`), BR-U4-02 composite key rule, clarified expected HTTP status (422 or 400 — either accepted) | Construction confirms the exact middleware behaviour and the business rule that drives validation; inception said "400 or 422" which remains correct | nfr-design-patterns.md (Pattern 2), business-rules.md BR-U4-02 | business-rules.md BR-U4-02 |
| TC-M-011 | Added full method signature, exact WHERE pattern (Pattern 3 — all 3 columns), scope note that all 6 covered tables apply the same pattern | Construction defines composite WHERE enforcement for all three dimensions; inception step referenced `delete_by_service_user` without method signature | nfr-design-patterns.md (Pattern 3) | business-rules.md BR-U4-02 |

---

## Added Test Cases

| TC ID | Title | Reason | Source Artifact | Finding Reference |
|-------|-------|--------|-----------------|-------------------|
| TC-M-012 | MemoryDataDeletion does not delete plans or sessions rows | BR-U4-06 explicitly restricts `MemoryDataDeletion` to 6 tables and excludes `plans`/`sessions`; this boundary was implicit at inception (TC-M-005 tests deletion but does not explicitly validate the non-deletion of lifecycle tables); construction revealed the need for a dedicated boundary test | domain-entities.md (Identity Summary Table), business-rules.md BR-U4-06 | business-rules.md BR-U4-06 |
| TC-M-013 | Admin deletion endpoint activates RLS session before bulk delete | Construction defines a new `admin.py` API route with a unique RLS activation pattern (Pattern 4): unlike normal routes it uses bare `get_db` + manual `set_config_for_session` rather than `get_tenanted_db`; this code path was entirely absent at inception (no admin HTTP endpoint was designed) | nfr-design-patterns.md (Pattern 4), business-rules.md BR-U4-08 | business-rules.md BR-U4-08, nfr-design-patterns.md Pattern 4 |

---

## Removed Test Cases

(none — all 11 inception test cases are preserved unchanged in ID and scope)
