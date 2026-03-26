# Test Case Index
## Unit: sdk-python
## Initiative: Multi-Tenancy Model Implementation
## Scope: happy-path-negative
**Unit abbreviation**: SP = sdk-python

---

| Test Case ID | Title | Source | Scope | Priority |
|---|---|---|---|---|
| TC-SP-001 | SDK client sends X-Tenant-ID on every request | sdk-python / FR-7.1 | happy-path | High |
| TC-SP-002 | Memory client sends per-call service identity headers | sdk-python / FR-7.2 | happy-path | High |
| TC-SP-003 | Tracker client sends per-call service identity headers | sdk-python / FR-7.3 | happy-path | High |
| TC-SP-004 | Wrappers hide platform tenant and honor explicit override precedence | sdk-python / FR-7.4 | happy-path | High |
| TC-SP-005 | CLI init relies on env/default path without new platform prompt | sdk-python / FR-7.5 | happy-path | Medium |
| TC-SP-006 | SDK tests cover identity header behavior for Memory and Tracker | sdk-python / FR-7.6 | happy-path | High |
| TC-SP-007 | Section 1 docs include two-tier model and three-header mapping | sdk-python / FR-8.1 | happy-path | Medium |
| TC-SP-008 | Section 1 docs include init/per-call split and Event Service injection note | sdk-python / FR-8.2, FR-8.3 | happy-path | Medium |
| TC-SP-009 | Client without explicit platform tenant uses env/default fallback | sdk-python / FR-7.1 | happy-path-negative | Medium |
| TC-SP-010 | Publish payload does not forward platform_tenant_id from SDK | sdk-python / FR-6.3, FR-7.4 | happy-path-negative | High |
| TC-SP-011 | EventClient publish sends X-Tenant-ID header | sdk-python / FR-8.3 | happy-path | High |
