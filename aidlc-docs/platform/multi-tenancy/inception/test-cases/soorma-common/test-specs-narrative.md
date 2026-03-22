# Test Specifications — Narrative
## Unit: soorma-common
## Initiative: Multi-Tenancy Model Implementation
## Scope: happy-path-negative
**Unit abbreviation**: SC = soorma-common

---

### TC-SC-001 — DEFAULT_PLATFORM_TENANT_ID constant is accessible with correct value

**Context**: Validates that the foundational tenancy constant is correctly defined and importable. This is the single most-depended-on constant in the initiative — all services and the SDK depend on it. Covers FR-1.1.

**Scenario description**: A developer (or service at startup) imports the constant from `soorma_common.tenancy` and reads its value.

**Steps**:
1. Import `DEFAULT_PLATFORM_TENANT_ID` from `soorma_common.tenancy`
2. Read the value of the constant

**Expected outcome**: The constant value equals `"spt_00000000-0000-0000-0000-000000000000"` exactly.

**Scope tag**: happy-path
**Priority**: High
**Source**: soorma-common / FR-1.1
**Construction artifacts**: aidlc-docs/platform/multi-tenancy/construction/soorma-common/

---

### TC-SC-002 — SOORMA_PLATFORM_TENANT_ID env var overrides the default constant

**Context**: Ensures the runtime override mechanism works correctly so operators can configure platform tenant identity via environment variable. Covers FR-1.2.

**Scenario description**: The `SOORMA_PLATFORM_TENANT_ID` environment variable is set before the module is loaded (or a reload occurs). The returned value reflects the env var, not the hardcoded default.

**Steps**:
1. Set environment variable `SOORMA_PLATFORM_TENANT_ID=spt_custom_tenant_abc123`
2. Re-import or reload `soorma_common.tenancy` to pick up the env var
3. Read the effective platform tenant ID (via the env-var-aware getter)

**Expected outcome**: The effective platform tenant ID equals `"spt_custom_tenant_abc123"`.

**Scope tag**: happy-path
**Priority**: High
**Source**: soorma-common / FR-1.2
**Construction artifacts**: aidlc-docs/platform/multi-tenancy/construction/soorma-common/

---

### TC-SC-003 — DEFAULT_PLATFORM_TENANT_ID has deprecation/warning comment in source

**Context**: Ensures the code carries a human-readable and tooling-readable warning that prevents accidental production use of the hardcoded default constant. Covers FR-1.3.

**Scenario description**: A developer reads the source of `soorma_common/tenancy.py` to check whether misuse of the constant is warned against.

**Steps**:
1. Open or read the source file `soorma_common/tenancy.py` (or inspect the constant's `__doc__` if exposed)
2. Locate the `DEFAULT_PLATFORM_TENANT_ID` constant definition

**Expected outcome**: A comment or docstring adjacent to the constant clearly states it MUST NOT be used in production and is only a placeholder until the Identity Service is implemented.

**Scope tag**: happy-path
**Priority**: Medium
**Source**: soorma-common / FR-1.3
**Construction artifacts**: aidlc-docs/platform/multi-tenancy/construction/soorma-common/

---

### TC-SC-004 — EventEnvelope gains platform_tenant_id field as Optional[str]

**Context**: Validates the new `platform_tenant_id` field on the shared `EventEnvelope` DTO. This field is the mechanism through which the Event Service stamps platform identity onto published events. Covers FR-6.3 / FR-1 (EventEnvelope docstring update).

**Scenario description**: A developer constructs an `EventEnvelope` and either leaves `platform_tenant_id` unset (None) or sets it explicitly.

**Steps**:
1. Construct `EventEnvelope(topic="test", data={})` without specifying `platform_tenant_id`
2. Inspect `envelope.platform_tenant_id`
3. Construct `EventEnvelope(topic="test", data={}, platform_tenant_id="spt_abc")` 
4. Inspect `envelope.platform_tenant_id`

**Expected outcome**: In step 2, `platform_tenant_id` is `None`. In step 4, `platform_tenant_id` is `"spt_abc"`. The field is accepted by the model without error in both cases.

**Scope tag**: happy-path
**Priority**: High
**Source**: soorma-common / FR-6.3
**Construction artifacts**: aidlc-docs/platform/multi-tenancy/construction/soorma-common/

---

### TC-SC-005 — EventEnvelope field docstrings accurately describe two-tier semantics

**Context**: Ensures that the docstrings on `platform_tenant_id`, `tenant_id`, and `user_id` are updated to accurately describe their roles in the two-tier model, helping future developers avoid misuse. Covers FR-6.4 / FR-1.

**Scenario description**: A developer reads the `EventEnvelope` model definition or generated documentation to understand what each identity field represents.

**Steps**:
1. Inspect the Pydantic field definitions on `EventEnvelope` for `platform_tenant_id`, `tenant_id`, and `user_id`
2. Read the `description` or docstring on each field

**Expected outcome**: `platform_tenant_id` docstring states it is injected by the Event Service from the authenticated header and must not be set by SDK/agent code. `tenant_id` docstring references "service tenant". `user_id` docstring references "service user".

**Scope tag**: happy-path
**Priority**: Medium
**Source**: soorma-common / FR-6.4
**Construction artifacts**: aidlc-docs/platform/multi-tenancy/construction/soorma-common/

---

### TC-SC-006 — soorma_common imposes no UUID format validation on tenant/user IDs

**Context**: Validates that `soorma_common` treats all identity strings as opaque — no UUID parsing, no prefix enforcement, no regex validation. This is a deliberate design choice that keeps all format rules in the future Identity Service. Covers FR-1.4.

**Scenario description**: An arbitrary non-UUID, non-prefixed string is assigned as a tenant ID on `EventEnvelope` without any validation error being raised.

**Steps**:
1. Construct `EventEnvelope(topic="test", data={}, tenant_id="arbitrary-string-123", user_id="user!@#", platform_tenant_id="no-prefix-here")`
2. Inspect each field value

**Expected outcome**: No `ValidationError` is raised. All three fields store the provided strings verbatim. `soorma_common` applies no format, prefix, or UUID validation.

**Scope tag**: happy-path
**Priority**: High
**Source**: soorma-common / FR-1.4
**Construction artifacts**: aidlc-docs/platform/multi-tenancy/construction/soorma-common/

---

### TC-SC-007 — SOORMA_PLATFORM_TENANT_ID env var absent falls back to default

**Context**: Negative case: verifies the fallback behavior when the override env var is not set. Without this fallback, services that never configure the env var would fail. Covers FR-1.2.

**Scenario description**: On a system where `SOORMA_PLATFORM_TENANT_ID` is not set in the environment, the constant resolves to the hardcoded default.

**Steps**:
1. Ensure `SOORMA_PLATFORM_TENANT_ID` is not present in the environment (unset)
2. Import the effective platform tenant ID getter from `soorma_common.tenancy`
3. Call it and read the returned value

**Expected outcome**: The returned value equals `"spt_00000000-0000-0000-0000-000000000000"` (the hardcoded default).

**Scope tag**: happy-path-negative
**Priority**: High
**Source**: soorma-common / FR-1.2
**Construction artifacts**: aidlc-docs/platform/multi-tenancy/construction/soorma-common/

---

### TC-SC-008 — EventEnvelope rejects platform_tenant_id longer than 64 chars

**Context**: Negative case: validates that the 64-character maximum length constraint (NFR-3.1) is enforced at the model level, preventing oversized tenant IDs from entering the system.

**Scenario description**: Constructing an `EventEnvelope` with a `platform_tenant_id` that exceeds 64 characters should fail validation.

**Steps**:
1. Construct a string of 65 characters: `"a" * 65`
2. Attempt to construct `EventEnvelope(topic="test", data={}, platform_tenant_id="a" * 65)`

**Expected outcome**: A `ValidationError` (or equivalent constraint violation) is raised, indicating the `platform_tenant_id` value exceeds the maximum allowed length.

**Scope tag**: happy-path-negative
**Priority**: High
**Source**: soorma-common / NFR-3.1
**Construction artifacts**: aidlc-docs/platform/multi-tenancy/construction/soorma-common/

---

### TC-SC-009 — SOORMA_PLATFORM_TENANT_ID set to empty string does not override default

**Context**: Negative/edge case: an empty string env var should not override the default with an empty value, as an empty platform tenant ID would break all downstream tenant isolation. Covers FR-1.2.

**Scenario description**: `SOORMA_PLATFORM_TENANT_ID` is set to an empty string. The effective platform tenant ID should either remain the default or raise a clear configuration error.

**Steps**:
1. Set `SOORMA_PLATFORM_TENANT_ID=""` in the environment
2. Import/reload the `soorma_common.tenancy` module
3. Read the effective platform tenant ID

**Expected outcome**: The effective platform tenant ID is either the hardcoded default (empty string ignored) or a configuration error is raised — it MUST NOT be an empty string.

**Scope tag**: happy-path-negative
**Priority**: Medium
**Source**: soorma-common / FR-1.2
**Construction artifacts**: aidlc-docs/platform/multi-tenancy/construction/soorma-common/
