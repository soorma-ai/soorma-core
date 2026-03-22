# Test Case Index
## Unit: tracker
## Initiative: Multi-Tenancy Model Implementation

**Unit abbreviation**: T = tracker

| Test Case ID | Title | Source | Scope | Priority |
|---|---|---|---|---|
| TC-T-001 | Alembic migration renames columns and adds platform_tenant_id | tracker / FR-5.1-5.5 | happy-path | High |
| TC-T-002 | TenantContext replaces per-route Header parsing | tracker / FR-5.6 | happy-path | High |
| TC-T-003 | Tracker API queries filter by all three identity dims | tracker / FR-5.7, NFR-1.3 | happy-path | High |
| TC-T-004 | NATS handler extracts platform_tenant_id from event envelope | tracker / FR-6.7, FR-5.6 | happy-path | High |
| TC-T-005 | set_config_for_session called before DB query in NATS path | tracker / FR-5.6, FR-3a.3 | happy-path | High |
| TC-T-006 | TrackerDataDeletion removes all rows for platform tenant | tracker / FR-5.8 | happy-path | High |
| TC-T-007 | Tracker API rejects service_tenant_id >64 chars | tracker / NFR-3.1 | happy-path-negative | High |
| TC-T-008 | NATS event with null platform_tenant_id does not create NULL row | tracker / FR-6.7 | happy-path-negative | High |
