# Test Specifications — Tabular
## Unit: event-service
## Initiative: Multi-Tenancy Model Implementation
## Scope: happy-path-negative
**Unit abbreviation**: ES = event-service

---

| TC ID | Title | Preconditions | Input | Expected Outcome | Scope | Priority | Source FR |
|---|---|---|---|---|---|---|---|
| TC-ES-001 | TenancyMiddleware populates request.state | Event Service running; TenancyMiddleware registered | POST /publish; X-Tenant-ID: spt_test | request.state.platform_tenant_id = "spt_test" | happy-path | High | FR-6.5 |
| TC-ES-002 | publish_event injects platform_tenant_id | Event Service running; NATS subscriber active | POST /publish; X-Tenant-ID: spt_authentic; envelope.platform_tenant_id=None | NATS envelope.platform_tenant_id = "spt_authentic" | happy-path | High | FR-6.6 |
| TC-ES-003 | SDK-supplied platform_tenant_id overwritten | Event Service running; NATS subscriber active | POST /publish; X-Tenant-ID: spt_real; envelope.platform_tenant_id="spt_spoofed" | NATS envelope.platform_tenant_id = "spt_real" | happy-path | High | FR-6.3, FR-6.6 |
| TC-ES-004 | Missing X-Tenant-ID falls back to default | DEFAULT_PLATFORM_TENANT_ID configured | POST /publish without X-Tenant-ID header | NATS envelope.platform_tenant_id = DEFAULT_PLATFORM_TENANT_ID | happy-path | Medium | FR-6.5, FR-3a.2 |
| TC-ES-005 | tenant_id and user_id normalized without remapping | Event Service running; NATS subscriber active | POST /publish; envelope.tenant_id="  svc_xyz  "; envelope.user_id="  usr_abc  " | NATS envelope.tenant_id="svc_xyz"; user_id="usr_abc" after trim normalization | happy-path | High | FR-6.1, FR-6.2 |
| TC-ES-006 | publish_event route uses DI tenant resolution | Source code is inspectable | Inspect src/api/dependencies.py and route signature | Route includes Depends(get_platform_tenant_id); endpoint does not parse raw X-Tenant-ID directly | happy-path | Medium | FR-6.5, FR-6.6 |
| TC-ES-007 | Malformed publish body rejected with 422 | Event Service running | POST /publish; X-Tenant-ID: spt_test; body={} | HTTP 422; no NATS publish | negative | High | FR-6.6 |
| TC-ES-008 | Oversized X-Tenant-ID is rejected | Event Service running | POST /publish; X-Tenant-ID: 65-char string; valid envelope | HTTP 422; no NATS publish | negative | High | NFR-3.1 |
| TC-ES-009 | Missing tenant_id after sanitization rejected | Event Service running | POST /publish; X-Tenant-ID valid; envelope.tenant_id="   "; envelope.user_id="usr_abc" | HTTP 422; no NATS publish | negative | High | FR-6.1, NFR-ES-02 |
| TC-ES-010 | Missing user_id after sanitization rejected | Event Service running | POST /publish; X-Tenant-ID valid; envelope.tenant_id="svc_xyz"; envelope.user_id="   " | HTTP 422; no NATS publish | negative | High | FR-6.2, NFR-ES-02 |
