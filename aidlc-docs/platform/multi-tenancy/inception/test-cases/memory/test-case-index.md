# Test Case Index
## Unit: memory
## Initiative: Multi-Tenancy Model Implementation

**Unit abbreviation**: M = memory

| Test Case ID | Title | Source | Scope | Priority |
|---|---|---|---|---|
| TC-M-001 | Alembic migration drops tenants and users tables | memory / FR-3.1, FR-3.2 | happy-path | High |
| TC-M-002 | All 8 tables have three-column identity after migration | memory / FR-3.3, FR-3.5 | happy-path | High |
| TC-M-003 | RLS policies enforce platform_tenant_id isolation | memory / FR-3b.2, FR-3b.4 | happy-path | High |
| TC-M-004 | Memory API stores and retrieves with three-column identity | memory / FR-3.8, FR-3.9 | happy-path | High |
| TC-M-005 | delete_by_platform_tenant removes all rows for that tenant | memory / FR-4.1, FR-4.2 | happy-path | High |
| TC-M-006 | delete_by_service_tenant scoped within platform tenant | memory / FR-4.1, NFR-1.3 | happy-path | High |
| TC-M-007 | Memory Service uses shared TenancyMiddleware | memory / FR-3.6 | happy-path | High |
| TC-M-008 | Rebuilt RLS policies use string comparison | memory / FR-3b.1, FR-3b.2 | happy-path | High |
| TC-M-009 | Query without RLS session variables returns 0 rows | memory / FR-3b.2, FR-3b.4 | happy-path-negative | High |
| TC-M-010 | Memory API rejects missing service tenant for user-scoped ops | memory / FR-3.8 | happy-path-negative | High |
| TC-M-011 | delete_by_service_user only deletes the specific user | memory / FR-4.1, NFR-1.3 | happy-path-negative | High |
