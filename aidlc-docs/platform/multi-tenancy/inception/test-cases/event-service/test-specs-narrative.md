# Test Specifications — Narrative
## Unit: event-service
## Initiative: Multi-Tenancy Model Implementation
## Scope: happy-path-negative
**Unit abbreviation**: ES = event-service

---

### TC-ES-001 — TenancyMiddleware is registered in Event Service and populates request.state

**Context**: The Event Service must register `TenancyMiddleware` so `platform_tenant_id` is available on `request.state` for every publish request. This is the prerequisite for the injection step. Covers FR-6.5.

**Scenario description**: A publish request reaches the Event Service with an `X-Tenant-ID` header. The middleware populates `request.state.platform_tenant_id`.

**Steps**:
1. Start the Event Service with `TenancyMiddleware` registered
2. Send a `POST /publish` request with `X-Tenant-ID: spt_test`
3. Inspect (via test instrument or log) `request.state.platform_tenant_id` in the route handler

**Expected outcome**: `request.state.platform_tenant_id` equals `"spt_test"`.

**Scope tag**: happy-path
**Priority**: High
**Source**: event-service / FR-6.5
**Construction artifacts**: aidlc-docs/platform/multi-tenancy/construction/event-service/

---

### TC-ES-002 — publish_event route injects platform_tenant_id from request.state onto the EventEnvelope

**Context**: The publish route must overwrite `event.platform_tenant_id` with the value from `request.state` (set by `TenancyMiddleware`), making the Event Service the trust boundary. Covers FR-6.6.

**Scenario description**: A publish request is sent with an `EventEnvelope` that either has no `platform_tenant_id` or has one set to a different value. After the Event Service processes it, the published envelope carries the authenticated value.

**Steps**:
1. Start the Event Service
2. Send `POST /publish` with `X-Tenant-ID: spt_authentic` and an `EventEnvelope` with `platform_tenant_id=None`
3. Capture the `EventEnvelope` delivered to NATS (via mock or subscriber)
4. Inspect `platform_tenant_id` on the delivered envelope

**Expected outcome**: The delivered `EventEnvelope.platform_tenant_id` equals `"spt_authentic"`. The `None` value sent by the caller is overwritten.

**Scope tag**: happy-path
**Priority**: High
**Source**: event-service / FR-6.6
**Construction artifacts**: aidlc-docs/platform/multi-tenancy/construction/event-service/

---

### TC-ES-003 — Event Service overwrites SDK-supplied platform_tenant_id with authenticated value

**Context**: An SDK client that incorrectly sets `platform_tenant_id` on the request must have that value overwritten by the Event Service. This is the anti-spoofing guarantee. Covers FR-6.3 (SDK must not set it), FR-6.6.

**Scenario description**: An `EventEnvelope` is published with `platform_tenant_id="spt_spoofed"` by the SDK. The authenticated header carries `spt_real`. The delivered event must carry `spt_real`.

**Steps**:
1. Send `POST /publish` with `X-Tenant-ID: spt_real` and `EventEnvelope.platform_tenant_id="spt_spoofed"`
2. Capture the NATS-delivered `EventEnvelope`

**Expected outcome**: `platform_tenant_id` on the delivered envelope equals `"spt_real"`, not `"spt_spoofed"`.

**Scope tag**: happy-path
**Priority**: High
**Source**: event-service / FR-6.3, FR-6.6
**Construction artifacts**: aidlc-docs/platform/multi-tenancy/construction/event-service/

---

### TC-ES-004 — Missing X-Tenant-ID on publish request falls back to DEFAULT_PLATFORM_TENANT_ID

**Context**: For backward compatibility during the migration period, a publish request without `X-Tenant-ID` must fall back to the default via middleware, not fail. Covers FR-6.5, FR-3a.2.

**Scenario description**: A publish request without `X-Tenant-ID` is sent to the Event Service. The published envelope carries the default platform tenant ID.

**Steps**:
1. Send `POST /publish` without `X-Tenant-ID` with a valid `EventEnvelope`
2. Capture the NATS-delivered `EventEnvelope`

**Expected outcome**: `platform_tenant_id` on the delivered envelope equals `DEFAULT_PLATFORM_TENANT_ID`.

**Scope tag**: happy-path
**Priority**: Medium
**Source**: event-service / FR-6.5, FR-3a.2
**Construction artifacts**: aidlc-docs/platform/multi-tenancy/construction/event-service/

---

### TC-ES-005 — Event Service normalizes tenant_id and user_id without semantic remapping

**Context**: Event Service must sanitize `tenant_id` and `user_id` (trim and empty-to-None), enforce both as mandatory, and avoid semantic remapping. Only `platform_tenant_id` is authoritative overwrite. Covers FR-6.1, FR-6.2, BR-U7-04, BR-U7-05.

**Scenario description**: An `EventEnvelope` is published with padded `tenant_id` and `user_id`. Event Service trims values and publishes normalized identities with no semantic reinterpretation.

**Steps**:
1. Send `POST /publish` with `EventEnvelope(tenant_id="  service_tenant_xyz  ", user_id="  service_user_abc  ", ...)`
2. Capture the NATS-delivered `EventEnvelope`
3. Inspect `tenant_id` and `user_id` on the delivered envelope

**Expected outcome**: `tenant_id="service_tenant_xyz"` and `user_id="service_user_abc"` are published after normalization; no semantic remapping occurs.

**Scope tag**: happy-path
**Priority**: High
**Source**: event-service / FR-6.1, FR-6.2
**Construction artifacts**: aidlc-docs/platform/multi-tenancy/construction/event-service/

---

### TC-ES-006 — publish_event route uses DI-based platform identity resolution

**Context**: Publish route must resolve authoritative platform identity via DI helper and keep endpoint logic decoupled from transport-specific header parsing. Covers FR-6.5, FR-6.6, NFR-ES-03.

**Scenario description**: The Event Service publish route signature and imports are inspected for dependency-based tenant resolution.

**Steps**:
1. Inspect `src/api/dependencies.py` for `get_platform_tenant_id` import/export from `soorma_service_common`
2. Inspect `publish_event` route handler signature in Event Service source

**Expected outcome**: Route includes `platform_tenant_id: str = Depends(get_platform_tenant_id)` and does not parse `X-Tenant-ID` directly inside endpoint logic.

**Scope tag**: happy-path
**Priority**: Medium
**Source**: event-service / FR-6.6
**Construction artifacts**: aidlc-docs/platform/multi-tenancy/construction/event-service/

---

### TC-ES-007 — Event Service publish request without valid EventEnvelope is rejected

**Context**: Negative case: the injection logic must not mask existing input validation. A malformed publish request must still be rejected before injection occurs. Covers FR-6.6 (error path).

**Scenario description**: A `POST /publish` is sent with an invalid (empty or missing required fields) `EventEnvelope` body.

**Steps**:
1. Send `POST /publish` with `X-Tenant-ID: spt_test` and an empty JSON body `{}`

**Expected outcome**: HTTP 422 Unprocessable Entity. No event is published to NATS. The validation error is returned before any injection logic runs.

**Scope tag**: happy-path-negative
**Priority**: High
**Source**: event-service / FR-6.6
**Construction artifacts**: aidlc-docs/platform/multi-tenancy/construction/event-service/

---

### TC-ES-008 — Event Service rejects oversized platform_tenant_id (>64)

**Context**: Negative case: if the `X-Tenant-ID` header contains a value exceeding the 64-character limit, the Event Service must not inject an oversized value into the envelope. Covers NFR-3.1.

**Scenario description**: `X-Tenant-ID` header contains a 65-character value. The publish request is sent.

**Steps**:
1. Send `POST /publish` with `X-Tenant-ID: {"a" * 65}` and a valid `EventEnvelope`

**Expected outcome**: Request is rejected with HTTP 422 and no event is published.

**Scope tag**: happy-path-negative
**Priority**: High
**Source**: event-service / NFR-3.1
**Construction artifacts**: aidlc-docs/platform/multi-tenancy/construction/event-service/

---

### TC-ES-009 — Event Service rejects publish when tenant_id is missing after sanitization

**Context**: `tenant_id` is mandatory for every event after sanitization. Missing/empty values must fail closed before publish. Covers BR-U7-05 and NFR-ES-02.

**Scenario description**: A publish request sets `tenant_id` to whitespace-only value while `user_id` is present.

**Steps**:
1. Send `POST /publish` with valid `X-Tenant-ID`, `EventEnvelope(tenant_id="   ", user_id="service_user_abc", ...)`
2. Observe API response and verify no event is delivered to subscriber

**Expected outcome**: HTTP 422. Event is not published.

**Scope tag**: happy-path-negative
**Priority**: High
**Source**: event-service / FR-6.1, NFR-ES-02
**Construction artifacts**: aidlc-docs/platform/multi-tenancy/construction/event-service/code/

---

### TC-ES-010 — Event Service rejects publish when user_id is missing after sanitization

**Context**: `user_id` is mandatory for every event, including machine actors. Missing/empty values must fail closed before publish. Covers BR-U7-05 and NFR-ES-02.

**Scenario description**: A publish request sets `user_id` to whitespace-only value while `tenant_id` is present.

**Steps**:
1. Send `POST /publish` with valid `X-Tenant-ID`, `EventEnvelope(tenant_id="service_tenant_xyz", user_id="   ", ...)`
2. Observe API response and verify no event is delivered to subscriber

**Expected outcome**: HTTP 422. Event is not published.

**Scope tag**: happy-path-negative
**Priority**: High
**Source**: event-service / FR-6.2, NFR-ES-02
**Construction artifacts**: aidlc-docs/platform/multi-tenancy/construction/event-service/code/
