# Test Specifications — Tabular
## Unit: sdk-python
## Initiative: Multi-Tenancy Model Implementation
## Scope: happy-path-negative
**Unit abbreviation**: SP = sdk-python

---

| TC ID | Title | Preconditions | Input | Expected Outcome | Scope | Priority | Source FR |
|---|---|---|---|---|---|---|---|
| TC-SP-001 | SDK client sends X-Tenant-ID on every request | SoormaClient instantiated with platform_tenant_id="spt_acme"; mock transport | Any service method call | X-Tenant-ID: spt_acme present in every outgoing request | happy-path | High | FR-7.1 |
| TC-SP-002 | Memory client sends per-call service identity headers | MemoryServiceClient instantiated; mock transport | store_task_context(service_tenant_id="t1", service_user_id="u1") | X-Tenant-ID: spt_acme, X-Service-Tenant-ID: t1, X-User-ID: u1 in headers | happy-path | High | FR-7.2 |
| TC-SP-003 | Tracker client sends per-call service identity headers | TrackerServiceClient instantiated; mock transport | create_plan(service_tenant_id="t2", service_user_id="u2") | X-Tenant-ID: spt_acme, X-Service-Tenant-ID: t2, X-User-ID: u2 in headers | happy-path | High | FR-7.3 |
| TC-SP-004 | PlatformContext wrappers hide platform_tenant_id from agent code | PlatformContext instantiated; wrapper inspected | context.memory.store_task_context(...) — no platform_tenant_id arg | Method has no platform_tenant_id param; X-Tenant-ID still sent; agent code runs without it | happy-path | High | FR-7.4 |
| TC-SP-005 | soorma init CLI stores platform_tenant_id in config | temp directory; soorma CLI installed | soorma init; user enters "spt_myorg" | config file contains platform_tenant_id: spt_myorg | happy-path | Medium | FR-7.5 |
| TC-SP-006 | SDK tests cover header injection for Memory and Tracker | SDK test suite present | pytest sdk/python/tests/ | ≥1 test per client asserting all 3 headers; all tests pass | happy-path | High | FR-7.6 |
| TC-SP-007 | ARCHITECTURE_PATTERNS.md Section 1 documents two-tier model | docs/ARCHITECTURE_PATTERNS.md post-impl | Read Section 1 | platform_tenant_id, X-Tenant-ID, service_tenant_id, X-Service-Tenant-ID, service_user_id, X-User-ID all mentioned | happy-path | Medium | FR-8.1 |
| TC-SP-008 | ARCHITECTURE_PATTERNS.md Section 2 shows per-call identity | docs/ARCHITECTURE_PATTERNS.md post-impl | Read Section 2 | Code example shows platform_tenant_id at init; per-call service_tenant_id/service_user_id | happy-path | Medium | FR-8.2 |
| TC-SP-009 | SDK without platform_tenant_id uses default | SoormaClient instantiated without platform_tenant_id | Any service method call | X-Tenant-ID: DEFAULT_PLATFORM_TENANT_ID in headers; no exception at init | negative | Medium | FR-7.1, FR-3a.2 |
| TC-SP-010 | PlatformContext.bus.publish does not forward platform_tenant_id | Agent handler using context.bus.publish | publish(platform_tenant_id="spt_attempt", ...) | HTTP body to Event Service has platform_tenant_id=None or absent; "spt_attempt" not forwarded | negative | High | FR-7.4, FR-6.3 |
