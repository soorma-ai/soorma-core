# Test Case Index
## Unit: event-service
## Initiative: Multi-Tenancy Model Implementation
## Scope: happy-path-negative
**Unit abbreviation**: ES = event-service

---

| Test Case ID | Title | Source | Scope | Priority |
|---|---|---|---|---|
| TC-ES-001 | TenancyMiddleware populates request.state | event-service / FR-6.5 | happy-path | High |
| TC-ES-002 | publish_event injects platform_tenant_id from request.state | event-service / FR-6.6 | happy-path | High |
| TC-ES-003 | SDK-supplied platform_tenant_id overwritten with authenticated value | event-service / FR-6.3, FR-6.6 | happy-path | High |
| TC-ES-004 | Missing X-Tenant-ID falls back to DEFAULT_PLATFORM_TENANT_ID | event-service / FR-6.5, FR-3a.2 | happy-path | Medium |
| TC-ES-005 | tenant_id and user_id normalized without remapping | event-service / FR-6.1, FR-6.2 | happy-path | High |
| TC-ES-006 | publish_event route uses DI tenant resolution | event-service / FR-6.5, FR-6.6 | happy-path | Medium |
| TC-ES-007 | Malformed publish body rejected with HTTP 422 | event-service / FR-6.6 | negative | High |
| TC-ES-008 | Oversized X-Tenant-ID rejected | event-service / NFR-3.1 | negative | High |
| TC-ES-009 | Missing tenant_id after sanitization rejected | event-service / FR-6.1, NFR-ES-02 | negative | High |
| TC-ES-010 | Missing user_id after sanitization rejected | event-service / FR-6.2, NFR-ES-02 | negative | High |

**Total test cases**: 10
**Happy path**: 6 (TC-ES-001 to TC-ES-006)
**Negative**: 4 (TC-ES-007 to TC-ES-010)

**FR coverage**:
- FR-6.1, FR-6.2 (normalized required fields): TC-ES-005, TC-ES-009, TC-ES-010
- FR-6.3 (SDK must not set platform_tenant_id): TC-ES-003
- FR-6.5 (TenancyMiddleware in event-service): TC-ES-001, TC-ES-004
- FR-6.6 (publish_event injection): TC-ES-002, TC-ES-003, TC-ES-006, TC-ES-007
- FR-3a.2 (default fallback): TC-ES-004
- NFR-3.1 (max length): TC-ES-008
