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

### TC-ES-005 — Event Service tenant_id and user_id fields pass through unmodified

**Context**: The Event Service must NOT modify `tenant_id` (service tenant) or `user_id` (service user) on the envelope — those are set by the SDK and represent the platform tenant's customers. Only `platform_tenant_id` is injected/overwritten. Covers FR-6.1, FR-6.2.

**Scenario description**: An `EventEnvelope` is published with specific `tenant_id` and `user_id` values. These values arrive unchanged at the NATS subscriber.

**Steps**:
1. Send `POST /publish` with `EventEnvelope(tenant_id="service_tenant_xyz", user_id="service_user_abc", ...)`
2. Capture the NATS-delivered `EventEnvelope`
3. Inspect `tenant_id` and `user_id` on the delivered envelope

**Expected outcome**: `tenant_id="service_tenant_xyz"` and `user_id="service_user_abc"` are unchanged. The Event Service only modified `platform_tenant_id`.

**Scope tag**: happy-path
**Priority**: High
**Source**: event-service / FR-6.1, FR-6.2
**Construction artifacts**: aidlc-docs/platform/multi-tenancy/construction/event-service/

---

### TC-ES-006 — publish_event route signature uses distinct parameter names (no collision)

**Context**: The route signature change introduces `http_request: Request` alongside the existing `request: PublishRequest`. The existing parameter is renamed to `publish_request` to avoid collision. Covers FR-6.6.

**Scenario description**: The Event Service publish route signature is inspected for correct parameter naming.

**Steps**:
1. Inspect the `publish_event` route handler function signature in the Event Service source

**Expected outcome**: The function has two parameters: `publish_request: PublishRequest` (the request body) and `http_request: Request` (the FastAPI HTTP request for header access). No parameter name collision.

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

### TC-ES-008 — Event Service publish with platform_tenant_id >64 chars injects truncated or validated value

**Context**: Negative case: if the `X-Tenant-ID` header contains a value exceeding the 64-character limit, the Event Service must not inject an oversized value into the envelope. Covers NFR-3.1.

**Scenario description**: `X-Tenant-ID` header contains a 65-character value. The publish request is sent.

**Steps**:
1. Send `POST /publish` with `X-Tenant-ID: {"a" * 65}` and a valid `EventEnvelope`

**Expected outcome**: Either the request is rejected with HTTP 422 (header length validation), or NATS-delivery is blocked by a downstream validation error. The oversized platform_tenant_id is never stored by subscribing services.

**Scope tag**: happy-path-negative
**Priority**: High
**Source**: event-service / NFR-3.1
**Construction artifacts**: aidlc-docs/platform/multi-tenancy/construction/event-service/
