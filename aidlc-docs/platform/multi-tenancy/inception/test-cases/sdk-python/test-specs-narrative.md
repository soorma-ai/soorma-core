# Test Specifications — Narrative
## Unit: sdk-python
## Initiative: Multi-Tenancy Model Implementation
## Scope: happy-path-negative
**Unit abbreviation**: SP = sdk-python

---

### TC-SP-001 — SDK client initialised with platform_tenant_id sends X-Tenant-ID on every request

**Context**: The SDK's `SoormaClient` (and service-specific clients) must accept `platform_tenant_id` at initialisation time and inject it as the `X-Tenant-ID` header on every HTTP request to Soorma services. Covers FR-7.1.

**Scenario description**: A client is initialised with `platform_tenant_id="spt_acme"`. Every subsequent request (e.g., `memory.store`, `registry.register_worker`) includes `X-Tenant-ID: spt_acme`.

**Steps**:
1. Instantiate `SoormaClient(platform_tenant_id="spt_acme", base_url=...)`
2. Call any service method (e.g., `await client.memory.store_task_context(...)`)
3. Capture the outgoing HTTP request headers (via mock transport or httpx.MockTransport)

**Expected outcome**: `X-Tenant-ID: spt_acme` is present in the captured request headers for every service call.

**Scope tag**: happy-path
**Priority**: High
**Source**: sdk-python / FR-7.1
**Construction artifacts**: aidlc-docs/platform/multi-tenancy/construction/sdk-python/

---

### TC-SP-002 — Memory service client sends per-call X-Service-Tenant-ID and X-User-ID headers

**Context**: Service tenant and user identity must be supplied per-call (not at init time) on the Memory service client, supporting multi-tenancy within a single SDK instance. Covers FR-7.2.

**Scenario description**: `MemoryServiceClient.store_task_context` is called with `service_tenant_id="t1"` and `service_user_id="u1"`. The outgoing request carries both headers.

**Steps**:
1. Instantiate `MemoryServiceClient(platform_tenant_id="spt_acme", base_url=...)`
2. Call `await client.store_task_context(task_id="t", service_tenant_id="t1", service_user_id="u1", ...)`
3. Capture outgoing request headers

**Expected outcome**: `X-Service-Tenant-ID: t1` and `X-User-ID: u1` are present in the captured headers alongside `X-Tenant-ID: spt_acme`.

**Scope tag**: happy-path
**Priority**: High
**Source**: sdk-python / FR-7.2
**Construction artifacts**: aidlc-docs/platform/multi-tenancy/construction/sdk-python/

---

### TC-SP-003 — Tracker service client sends per-call X-Service-Tenant-ID and X-User-ID headers

**Context**: Same per-call header pattern applies to the Tracker service client. Covers FR-7.3.

**Scenario description**: `TrackerServiceClient.create_plan` is called with `service_tenant_id="t2"` and `service_user_id="u2"`. The outgoing request carries both headers.

**Steps**:
1. Instantiate `TrackerServiceClient(platform_tenant_id="spt_acme", base_url=...)`
2. Call `await client.create_plan(plan=..., service_tenant_id="t2", service_user_id="u2")`
3. Capture outgoing request headers

**Expected outcome**: `X-Service-Tenant-ID: t2` and `X-User-ID: u2` are present in the captured headers alongside `X-Tenant-ID: spt_acme`.

**Scope tag**: happy-path
**Priority**: High
**Source**: sdk-python / FR-7.3
**Construction artifacts**: aidlc-docs/platform/multi-tenancy/construction/sdk-python/

---

### TC-SP-004 — PlatformContext wrappers do not expose platform_tenant_id to agent handler code

**Context**: `PlatformContext` wraps service clients and must extract all identity dimensions automatically from the event envelope. Agent handlers must never receive or pass `platform_tenant_id` directly. Covers FR-7.4.

**Scenario description**: An agent handler uses `context.memory.store_task_context(...)`. The method signature does not have a `platform_tenant_id` parameter.

**Steps**:
1. Inspect the `PlatformContext.memory.store_task_context` method signature
2. Confirm no `platform_tenant_id` parameter is present
3. Call the method from an agent handler without passing `platform_tenant_id`
4. Capture outgoing HTTP request headers

**Expected outcome**: The method signature has no `platform_tenant_id` parameter. The header is still sent (extracted from internal context). Agent code compiles and runs without needing to supply `platform_tenant_id`.

**Scope tag**: happy-path
**Priority**: High
**Source**: sdk-python / FR-7.4
**Construction artifacts**: aidlc-docs/platform/multi-tenancy/construction/sdk-python/

---

### TC-SP-005 — SDK cli/init.py prompts for platform_tenant_id and stores it in config

**Context**: The `soorma` CLI initialisation flow must prompt the user for `platform_tenant_id` and persist it in the project configuration so SDK clients can be instantiated from config. Covers FR-7.5.

**Scenario description**: `soorma init` is run interactively. The user provides `platform_tenant_id`. The config file contains the value.

**Steps**:
1. Run `soorma init` in a temp directory
2. When prompted for `platform_tenant_id`, enter `"spt_myorg"`
3. Inspect the generated config file (e.g., `.soorma/config.yaml`)

**Expected outcome**: The config file contains `platform_tenant_id: spt_myorg`.

**Scope tag**: happy-path
**Priority**: Medium
**Source**: sdk-python / FR-7.5
**Construction artifacts**: aidlc-docs/platform/multi-tenancy/construction/sdk-python/

---

### TC-SP-006 — SDK unit tests cover the new per-call header parameters for both Memory and Tracker clients

**Context**: Regression protection for the new header parameters. Covers FR-7.6.

**Scenario description**: After implementation, the SDK test suite includes tests that assert `X-Tenant-ID`, `X-Service-Tenant-ID`, and `X-User-ID` are sent by Memory and Tracker service clients.

**Steps**:
1. Run the SDK test suite (`pytest sdk/python/tests/`)
2. Check test names or marks for coverage of `X-Tenant-ID`, `X-Service-Tenant-ID`, and `X-User-ID` header injection

**Expected outcome**: At least one test per client (Memory, Tracker) that asserts all three headers are present in service calls. All tests pass.

**Scope tag**: happy-path
**Priority**: High
**Source**: sdk-python / FR-7.6
**Construction artifacts**: aidlc-docs/platform/multi-tenancy/construction/sdk-python/

---

### TC-SP-007 — ARCHITECTURE_PATTERNS.md Section 1 updated to reflect two-tier model

**Context**: After implementation, `docs/ARCHITECTURE_PATTERNS.md` Section 1 must describe the two-tier tenancy model (`platform_tenant_id` + `service_tenant_id` + `service_user_id`) and the authentication header mapping. Covers FR-8.1.

**Scenario description**: Section 1 of `ARCHITECTURE_PATTERNS.md` is inspected post-implementation for two-tier model documentation.

**Steps**:
1. Open `docs/ARCHITECTURE_PATTERNS.md`
2. Read Section 1 (Authentication & Authorization)

**Expected outcome**: Section 1 mentions `platform_tenant_id`, `X-Tenant-ID`, `service_tenant_id`, `X-Service-Tenant-ID`, `service_user_id`, and `X-User-ID` with correct descriptions.

**Scope tag**: happy-path
**Priority**: Medium
**Source**: sdk-python / FR-8.1
**Construction artifacts**: aidlc-docs/platform/multi-tenancy/construction/sdk-python/

---

### TC-SP-008 — ARCHITECTURE_PATTERNS.md Section 2 updated to show platform_tenant_id at init, per-call for service identity

**Context**: Section 2 must be updated to show the SDK two-layer architecture with `platform_tenant_id` at init and per-call service identity. Covers FR-8.2.

**Scenario description**: Section 2 of `ARCHITECTURE_PATTERNS.md` is inspected post-implementation for per-call identity documentation.

**Steps**:
1. Open `docs/ARCHITECTURE_PATTERNS.md`
2. Read Section 2 (SDK Two-Layer Architecture)

**Expected outcome**: Section 2 shows a code example where the SDK client is constructed with `platform_tenant_id` and service method calls include `service_tenant_id` and `service_user_id` as per-call parameters.

**Scope tag**: happy-path
**Priority**: Medium
**Source**: sdk-python / FR-8.2
**Construction artifacts**: aidlc-docs/platform/multi-tenancy/construction/sdk-python/

---

### TC-SP-009 — SDK initialised without platform_tenant_id uses DEFAULT_PLATFORM_TENANT_ID

**Context**: Negative/backward-compat case: if `platform_tenant_id` is not supplied at init time, the SDK must fall back to `DEFAULT_PLATFORM_TENANT_ID` rather than failing. Covers FR-7.1, FR-3a.2.

**Scenario description**: `SoormaClient` is instantiated without `platform_tenant_id`. A service call is made. The outgoing request carries `X-Tenant-ID: DEFAULT_PLATFORM_TENANT_ID`.

**Steps**:
1. Instantiate `SoormaClient(base_url=...)` without `platform_tenant_id`
2. Call any service method
3. Capture outgoing request headers

**Expected outcome**: `X-Tenant-ID` is present and equals `DEFAULT_PLATFORM_TENANT_ID`. No error is raised at init time.

**Scope tag**: happy-path-negative
**Priority**: Medium
**Source**: sdk-python / FR-7.1, FR-3a.2
**Construction artifacts**: aidlc-docs/platform/multi-tenancy/construction/sdk-python/

---

### TC-SP-010 — PlatformContext.bus.publish does not expose or accept platform_tenant_id

**Context**: Negative/architecture case: the `context.bus.publish` wrapper must not accept `platform_tenant_id` (since the Event Service injects it server-side). Agent code that tries to pass `platform_tenant_id` in the event envelope via the wrapper must be rejected at the wrapper layer or the field must be silently ignored. Covers FR-7.4, FR-6.3.

**Scenario description**: An agent handler attempts to call `context.bus.publish(...)` with `platform_tenant_id` set in the envelope. The field is not forwarded or is cleared before reaching the Event Service.

**Steps**:
1. Call `context.bus.publish(topic="...", data={...}, platform_tenant_id="spt_attempt")`
2. Capture the HTTP request body sent to the Event Service publish endpoint

**Expected outcome**: The `EventEnvelope` sent to the Event Service has `platform_tenant_id=None` (or the field absent). The value `"spt_attempt"` is not forwarded.

**Scope tag**: happy-path-negative
**Priority**: High
**Source**: sdk-python / FR-7.4, FR-6.3
**Construction artifacts**: aidlc-docs/platform/multi-tenancy/construction/sdk-python/
