# Test Case Index
## Unit: soorma-common
## Initiative: Multi-Tenancy Model Implementation

**Unit abbreviation**: SC = soorma-common

| Test Case ID | Title | Source | Scope | Priority |
|---|---|---|---|---|
| TC-SC-001 | DEFAULT_PLATFORM_TENANT_ID accessible with correct value | soorma-common / FR-1.1 | happy-path | High |
| TC-SC-002 | SOORMA_PLATFORM_TENANT_ID env var overrides default | soorma-common / FR-1.2 | happy-path | High |
| TC-SC-003 | DEFAULT_PLATFORM_TENANT_ID has deprecation comment | soorma-common / FR-1.3 | happy-path | Medium |
| TC-SC-004 | EventEnvelope platform_tenant_id field is Optional[str] | soorma-common / FR-6.3 | happy-path | High |
| TC-SC-005 | EventEnvelope field docstrings describe two-tier semantics | soorma-common / FR-6.4 | happy-path | Medium |
| TC-SC-006 | No UUID format validation on tenant/user IDs | soorma-common / FR-1.4 | happy-path | High |
| TC-SC-007 | Absent env var falls back to hardcoded default | soorma-common / FR-1.2 | happy-path-negative | High |
| TC-SC-008 | EventEnvelope rejects platform_tenant_id >64 chars | soorma-common / NFR-3.1 | happy-path-negative | High |
| TC-SC-009 | Empty string env var does not override to empty value | soorma-common / FR-1.2 | happy-path-negative | Medium |
