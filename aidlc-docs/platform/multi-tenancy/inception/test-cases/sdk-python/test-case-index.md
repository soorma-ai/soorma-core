# Test Case Index
## Unit: sdk-python
## Initiative: Multi-Tenancy Model Implementation
## Scope: happy-path-negative
**Unit abbreviation**: SP = sdk-python

---

| TC ID | Title | Scope | Priority | Source FR | Narrative | Gherkin | Tabular |
|---|---|---|---|---|---|---|---|
| TC-SP-001 | SDK client sends X-Tenant-ID on every request | happy-path | High | FR-7.1 | ✅ | ✅ | ✅ |
| TC-SP-002 | Memory client sends per-call X-Service-Tenant-ID and X-User-ID | happy-path | High | FR-7.2 | ✅ | ✅ | ✅ |
| TC-SP-003 | Tracker client sends per-call X-Service-Tenant-ID and X-User-ID | happy-path | High | FR-7.3 | ✅ | ✅ | ✅ |
| TC-SP-004 | PlatformContext wrappers hide platform_tenant_id from agent code | happy-path | High | FR-7.4 | ✅ | ✅ | ✅ |
| TC-SP-005 | soorma init CLI stores platform_tenant_id in config | happy-path | Medium | FR-7.5 | ✅ | ✅ | ✅ |
| TC-SP-006 | SDK tests cover per-call header injection | happy-path | High | FR-7.6 | ✅ | ✅ | ✅ |
| TC-SP-007 | ARCHITECTURE_PATTERNS.md Section 1 documents two-tier model | happy-path | Medium | FR-8.1 | ✅ | ✅ | ✅ |
| TC-SP-008 | ARCHITECTURE_PATTERNS.md Section 2 shows per-call identity | happy-path | Medium | FR-8.2 | ✅ | ✅ | ✅ |
| TC-SP-009 | SDK without platform_tenant_id uses DEFAULT_PLATFORM_TENANT_ID | negative | Medium | FR-7.1, FR-3a.2 | ✅ | ✅ | ✅ |
| TC-SP-010 | PlatformContext.bus.publish does not forward platform_tenant_id | negative | High | FR-7.4, FR-6.3 | ✅ | ✅ | ✅ |

**Total test cases**: 10
**Happy path**: 8 (TC-SP-001 to TC-SP-008)
**Negative**: 2 (TC-SP-009, TC-SP-010)

**FR coverage**:
- FR-7.1 (platform_tenant_id at init): TC-SP-001, TC-SP-009
- FR-7.2 (Memory per-call headers): TC-SP-002
- FR-7.3 (Tracker per-call headers): TC-SP-003
- FR-7.4 (PlatformContext wrappers): TC-SP-004, TC-SP-010
- FR-7.5 (CLI init): TC-SP-005
- FR-7.6 (SDK tests updated): TC-SP-006
- FR-8.1 (ARCHITECTURE_PATTERNS.md Section 1): TC-SP-007
- FR-8.2 (ARCHITECTURE_PATTERNS.md Section 2): TC-SP-008
- FR-6.3 (SDK must not set platform_tenant_id): TC-SP-010
- FR-3a.2 (default fallback): TC-SP-009
