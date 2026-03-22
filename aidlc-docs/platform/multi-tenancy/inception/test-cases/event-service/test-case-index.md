# Test Case Index
## Unit: event-service
## Initiative: Multi-Tenancy Model Implementation
## Scope: happy-path-negative
**Unit abbreviation**: ES = event-service

---

| TC ID | Title | Scope | Priority | Source FR | Narrative | Gherkin | Tabular |
|---|---|---|---|---|---|---|---|
| TC-ES-001 | TenancyMiddleware populates request.state | happy-path | High | FR-6.5 | ✅ | ✅ | ✅ |
| TC-ES-002 | publish_event injects platform_tenant_id from request.state | happy-path | High | FR-6.6 | ✅ | ✅ | ✅ |
| TC-ES-003 | SDK-supplied platform_tenant_id overwritten with authenticated value | happy-path | High | FR-6.3, FR-6.6 | ✅ | ✅ | ✅ |
| TC-ES-004 | Missing X-Tenant-ID falls back to DEFAULT_PLATFORM_TENANT_ID | happy-path | Medium | FR-6.5, FR-3a.2 | ✅ | ✅ | ✅ |
| TC-ES-005 | tenant_id and user_id pass through unmodified | happy-path | High | FR-6.1, FR-6.2 | ✅ | ✅ | ✅ |
| TC-ES-006 | publish_event route parameter naming correct | happy-path | Medium | FR-6.6 | ✅ | ✅ | ✅ |
| TC-ES-007 | Malformed publish body rejected with HTTP 422 | negative | High | FR-6.6 | ✅ | ✅ | ✅ |
| TC-ES-008 | Oversized X-Tenant-ID rejected or blocked | negative | High | NFR-3.1 | ✅ | ✅ | ✅ |

**Total test cases**: 8
**Happy path**: 6 (TC-ES-001 to TC-ES-006)
**Negative**: 2 (TC-ES-007, TC-ES-008)

**FR coverage**:
- FR-6.1, FR-6.2 (pass-through fields): TC-ES-005
- FR-6.3 (SDK must not set platform_tenant_id): TC-ES-003
- FR-6.5 (TenancyMiddleware in event-service): TC-ES-001, TC-ES-004
- FR-6.6 (publish_event injection): TC-ES-002, TC-ES-003, TC-ES-006, TC-ES-007
- FR-3a.2 (default fallback): TC-ES-004
- NFR-3.1 (max length): TC-ES-008
