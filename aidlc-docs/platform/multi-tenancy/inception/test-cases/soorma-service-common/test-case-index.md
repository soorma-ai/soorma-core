# Test Case Index
## Unit: soorma-service-common
## Initiative: Multi-Tenancy Model Implementation

**Unit abbreviation**: SSC = soorma-service-common

| Test Case ID | Title | Source | Scope | Priority |
|---|---|---|---|---|
| TC-SSC-001 | TenancyMiddleware extracts all three headers to request.state | soorma-service-common / FR-3a.2 | happy-path | High |
| TC-SSC-002 | Missing X-Tenant-ID defaults to DEFAULT_PLATFORM_TENANT_ID | soorma-service-common / FR-3a.2 | happy-path | High |
| TC-SSC-003 | get_tenanted_db calls set_config for all three session variables | soorma-service-common / FR-3a.3 | happy-path | High |
| TC-SSC-004 | get_tenant_context bundles all three dims plus tenanted DB | soorma-service-common / FR-3a.4 | happy-path | High |
| TC-SSC-005 | PlatformTenantDataDeletion enforces abstract methods | soorma-service-common / FR-3a (ABC) | happy-path | Medium |
| TC-SSC-006 | set_config_for_session activates RLS for NATS-path | soorma-service-common / FR-3a.3 | happy-path | High |
| TC-SSC-007 | Missing optional service headers result in None | soorma-service-common / FR-3a.2 | happy-path-negative | High |
| TC-SSC-008 | get_tenanted_db does not yield session when set_config raises | soorma-service-common / FR-3a.3 | happy-path-negative | High |
| TC-SSC-009 | soorma-service-common is not in SDK dependency tree | soorma-service-common / FR-3a.1 | happy-path-negative | High |
