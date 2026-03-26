# Test Specifications — Narrative
## Unit: sdk-python
## Initiative: Multi-Tenancy Model Implementation
## Scope: happy-path-negative
**Unit abbreviation**: SP = sdk-python

---

### TC-SP-001 — SDK client initialised with platform_tenant_id sends X-Tenant-ID on every request

**Context**: SDK service clients accept `platform_tenant_id` at initialization and project it as `X-Tenant-ID` on outbound calls. Covers FR-7.1.

**Scenario description**: A client is initialised with `platform_tenant_id="spt_acme"`. Subsequent service requests include `X-Tenant-ID: spt_acme`.

**Steps**:
1. Instantiate client with `platform_tenant_id="spt_acme"`
2. Call a service method
3. Capture outbound headers

**Expected outcome**: `X-Tenant-ID: spt_acme` is present on every request.

**Scope tag**: happy-path
**Priority**: High
**Source**: sdk-python / FR-7.1
**Construction artifacts**: aidlc-docs/platform/multi-tenancy/construction/sdk-python/

---

### TC-SP-002 — Memory service client sends per-call X-Service-Tenant-ID and X-User-ID headers

**Context**: Memory low-level client requires per-call service identity. Covers FR-7.2.

**Scenario description**: `store_task_context` called with `service_tenant_id` and `service_user_id` emits both headers.

**Steps**:
1. Instantiate `MemoryServiceClient(platform_tenant_id="spt_acme")`
2. Call method with `service_tenant_id="t1"`, `service_user_id="u1"`
3. Capture outbound headers

**Expected outcome**: Headers include `X-Tenant-ID`, `X-Service-Tenant-ID`, `X-User-ID` with expected values.

**Scope tag**: happy-path
**Priority**: High
**Source**: sdk-python / FR-7.2
**Construction artifacts**: aidlc-docs/platform/multi-tenancy/construction/sdk-python/

---

### TC-SP-003 — Tracker service client sends per-call X-Service-Tenant-ID and X-User-ID headers

**Context**: Tracker low-level client follows same per-call service identity model. Covers FR-7.3.

**Scenario description**: Tracker API method called with `service_tenant_id` and `service_user_id` emits both headers.

**Steps**:
1. Instantiate `TrackerServiceClient(platform_tenant_id="spt_acme")`
2. Call a tracker method with `service_tenant_id="t2"`, `service_user_id="u2"`
3. Capture outbound headers

**Expected outcome**: Headers include `X-Tenant-ID`, `X-Service-Tenant-ID`, and `X-User-ID`.

**Scope tag**: happy-path
**Priority**: High
**Source**: sdk-python / FR-7.3
**Construction artifacts**: aidlc-docs/platform/multi-tenancy/construction/sdk-python/

---

### TC-SP-004 — PlatformContext wrappers hide platform_tenant_id and honor explicit service identity overrides

**Context**: Wrappers should not expose platform tenant and should use metadata defaults only when explicit values are omitted. Covers FR-7.4.

**Scenario description**: Wrapper method signature has no `platform_tenant_id`; explicit `service_tenant_id`/`service_user_id` overrides metadata defaults.

**Steps**:
1. Inspect wrapper signature for absence of `platform_tenant_id`
2. Invoke wrapper with explicit service identity while metadata is bound
3. Capture delegated request identity values

**Expected outcome**: No `platform_tenant_id` parameter on wrapper API; explicit service identity values take precedence over metadata defaults.

**Scope tag**: happy-path
**Priority**: High
**Source**: sdk-python / FR-7.4
**Construction artifacts**: aidlc-docs/platform/multi-tenancy/construction/sdk-python/

---

### TC-SP-005 — CLI init uses env/default platform tenant path without prompting for platform_tenant_id

**Context**: Approved U6 design decision sets CLI behavior to rely on existing env/default resolution, not a new prompt/flag. Covers FR-7.5.

**Scenario description**: CLI init runs successfully without interactive platform-tenant prompt; clients still resolve platform tenant through env/default behavior.

**Steps**:
1. Run `soorma init`
2. Verify no mandatory platform-tenant prompt is introduced
3. Instantiate SDK client without explicit platform tenant and inspect resolved `X-Tenant-ID`

**Expected outcome**: No new CLI prompt/flag requirement for platform tenant; platform tenant resolution still works via env/default path.

**Scope tag**: happy-path
**Priority**: Medium
**Source**: sdk-python / FR-7.5
**Construction artifacts**: aidlc-docs/platform/multi-tenancy/construction/sdk-python/

---

### TC-SP-006 — SDK unit tests cover identity header behavior for Memory and Tracker clients

**Context**: Regression coverage for required identity header projection. Covers FR-7.6.

**Scenario description**: Test suite includes assertions for all required headers in Memory and Tracker calls.

**Steps**:
1. Run SDK tests
2. Verify coverage for Memory and Tracker header assertions

**Expected outcome**: Tests assert required headers and pass.

**Scope tag**: happy-path
**Priority**: High
**Source**: sdk-python / FR-7.6
**Construction artifacts**: aidlc-docs/platform/multi-tenancy/construction/sdk-python/

---

### TC-SP-007 — ARCHITECTURE_PATTERNS.md Section 1 documents two-tier model and three-header mapping

**Context**: Documentation must reflect approved two-tier model and header mapping. Covers FR-8.1.

**Scenario description**: Section 1 is inspected for `platform_tenant_id`, `service_tenant_id`, `service_user_id`, and header mapping.

**Steps**:
1. Open `docs/ARCHITECTURE_PATTERNS.md`
2. Read Section 1

**Expected outcome**: Section 1 correctly documents two-tier identity and three-header mapping.

**Scope tag**: happy-path
**Priority**: Medium
**Source**: sdk-python / FR-8.1
**Construction artifacts**: aidlc-docs/platform/multi-tenancy/construction/sdk-python/

---

### TC-SP-008 — ARCHITECTURE_PATTERNS.md Section 1 includes init-time vs per-call identity split and Event Service injection note

**Context**: Approved docs scope is Section 1 in-place updates, including parameter split and trust-boundary behavior. Covers FR-8.2, FR-8.3.

**Scenario description**: Section 1 is inspected for explicit init-time platform identity vs per-call service identity and Event Service platform injection note.

**Steps**:
1. Open `docs/ARCHITECTURE_PATTERNS.md`
2. Inspect Section 1 text/table/examples

**Expected outcome**: Section 1 includes init-time vs per-call identity split and states Event Service injects `platform_tenant_id` server-side.

**Scope tag**: happy-path
**Priority**: Medium
**Source**: sdk-python / FR-8.2, FR-8.3
**Construction artifacts**: aidlc-docs/platform/multi-tenancy/construction/sdk-python/

---

### TC-SP-009 — SDK initialised without explicit platform_tenant_id uses env/default fallback

**Context**: Pre-release default fallback behavior remains required for initialization without explicit platform tenant. Covers FR-7.1.

**Scenario description**: Client is instantiated without explicit platform tenant and still emits `X-Tenant-ID` using env/default path.

**Steps**:
1. Instantiate client without explicit platform tenant
2. Call service method
3. Capture outbound headers

**Expected outcome**: `X-Tenant-ID` is present and resolves through existing env/default model.

**Scope tag**: happy-path-negative
**Priority**: Medium
**Source**: sdk-python / FR-7.1
**Construction artifacts**: aidlc-docs/platform/multi-tenancy/construction/sdk-python/

---

### TC-SP-010 — context.bus/EventClient publish path does not forward platform_tenant_id in envelope payload

**Context**: SDK must not set `platform_tenant_id` in outbound envelope payload; Event Service is trust boundary authority. Covers FR-6.3, FR-7.4.

**Scenario description**: Publish path is inspected/captured to ensure no client-side `platform_tenant_id` envelope field forwarding.

**Steps**:
1. Publish event via `context.bus` or `EventClient`
2. Capture request payload body sent to Event Service

**Expected outcome**: Outbound payload does not set a client-provided `platform_tenant_id` field.

**Scope tag**: happy-path-negative
**Priority**: High
**Source**: sdk-python / FR-6.3, FR-7.4
**Construction artifacts**: aidlc-docs/platform/multi-tenancy/construction/sdk-python/

---

### TC-SP-011 — EventClient publish sends X-Tenant-ID header for Event Service middleware path

**Context**: Construction functional design identified this as a required alignment for correct platform-tenant injection trust boundary. Covers FR-8.3.

**Scenario description**: Event publish HTTP request includes `X-Tenant-ID` derived from SDK platform identity state.

**Steps**:
1. Instantiate `EventClient` with platform identity context
2. Call `publish(...)`
3. Capture outbound publish request headers

**Expected outcome**: Request includes `X-Tenant-ID`; Event Service can derive `request.state.platform_tenant_id` from middleware path.

**Scope tag**: happy-path
**Priority**: High
**Source**: sdk-python / FR-8.3
**Construction artifacts**: aidlc-docs/platform/multi-tenancy/construction/sdk-python/code/
