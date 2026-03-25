# Code Generation Plan — U7: services/event-service
## Initiative: Multi-Tenancy Model Implementation
**Date**: 2026-03-25
**Unit**: U7 — `services/event-service` (Wave 3)
**Depends On**: U1 (`libs/soorma-common` ✅), U2 (`libs/soorma-service-common` ✅)
**Change Type**: Moderate

---

## Architecture Alignment (docs/ARCHITECTURE_PATTERNS.md)

This plan aligns with:
- Section 1: Authentication and authorization trust boundary (authoritative platform identity)
- Section 3: Event choreography integrity (no spoofed metadata propagation)
- Section 6: Fail-closed error handling prior to publish
- Section 7: Testing with explicit negative-path coverage

---

## Unit Context

U7 updates Event Service publish ingress so it becomes the trust boundary for event metadata:
- Authoritative `platform_tenant_id` injection/overwrite from DI-resolved tenant context
- Central sanitization and validation of `tenant_id` and `user_id`
- Mandatory `tenant_id` and `user_id` for all events (including machine actors)
- Fail-closed publish behavior on malformed/oversized/missing identity fields
- Transitional fallback to `DEFAULT_PLATFORM_TENANT_ID` when platform context is absent

Primary artifacts driving this plan:
- `construction/event-service/functional-design/business-rules.md`
- `construction/event-service/functional-design/business-logic-model.md`
- `construction/event-service/nfr-requirements/nfr-requirements.md`
- `construction/event-service/nfr-design/nfr-design-patterns.md`

---

## Part 1 — Planning Status

- [x] Step 1 — Analyze U7 design/NFR artifacts and test mappings (TC-ES-001..008)
- [x] Step 2 — Identify exact brownfield files to modify/create
- [x] Step 3 — Define executable step sequence with FR/NFR/TC traceability
- [x] Step 4 — Create this code-generation plan document
- [x] Step 5 — Summarize plan for user review
- [x] Step 6 — Log approval prompt in audit.md
- [x] Step 7 — Wait for explicit user approval to execute Part 2
- [x] Step 8 — Record user approval in audit.md
- [x] Step 9 — Update aidlc-state.md for Part 2 execution start

---

## Planned Execution Steps (Part 2 — after approval)

### Group 1: Dependency and App Wiring

- [x] Step 10 — Update `services/event-service/pyproject.toml` to include `soorma-service-common` dependency required for shared tenancy middleware/dependency helpers
- [x] Step 11 — Update `services/event-service/src/main.py` to register `TenancyMiddleware` from `soorma_service_common`
- [x] Step 12 — Create `services/event-service/src/api/dependencies.py` exposing `get_platform_tenant_id` for route-level DI

### Group 2: Publish Route Identity Boundary

- [x] Step 13 — Refactor `services/event-service/src/api/routes/events.py` publish route signature to use distinct payload parameter and DI-resolved `platform_tenant_id`
- [x] Step 14 — Implement metadata sanitization utility in publish flow (trim and empty-to-None for `tenant_id` and `user_id`)
- [x] Step 15 — Enforce required identity fields after sanitization (`tenant_id` and `user_id` must both be present)
- [x] Step 16 — Enforce max length 64 validation on `platform_tenant_id`, `tenant_id`, and `user_id` (fail closed)
- [x] Step 17 — Apply anti-spoofing overwrite (`event.platform_tenant_id = resolved_platform_tenant_id`) before publish
- [x] Step 18 — Isolate and apply transitional fallback (`DEFAULT_PLATFORM_TENANT_ID`) if DI resolution yields missing/empty platform identity
- [x] Step 19 — Add structured validation/rejection logging with no full payload dumps

### Group 3: Tests (STUB -> RED -> GREEN -> REFACTOR execution discipline)

- [x] Step 20 — Update `services/event-service/tests/test_api.py` for DI signature behavior and validation failures (422 paths) covering TC-ES-002/003/007/008
- [x] Step 21 — Add targeted tests in `services/event-service/tests/test_multi_tenancy.py` for anti-spoofing overwrite, fallback behavior, and required identity enforcement (TC-ES-001..006)
- [x] Step 22 — Update `services/event-service/tests/conftest.py` fixtures/helpers for tenancy header setup and deterministic assertions
- [x] Step 23 — Run event-service test suite and capture pass/fail output; iterate until green for affected test scope

### Group 4: Documentation and Traceability

- [x] Step 24 — Update `services/event-service/CHANGELOG.md` with U7 multi-tenancy trust-boundary changes
- [x] Step 25 — Create `aidlc-docs/platform/multi-tenancy/construction/event-service/code/code-summary.md` with modified/created file inventory and test outcomes

### Group 5: Progress and Gate Readiness

- [x] Step 26 — Mark completed execution steps [x] in this plan as work completes
- [x] Step 27 — Update `aidlc-state.md` with U7 Code Generation execution progress and completion state
- [x] Step 28 — Ensure artifacts are ready for Build and Test phase sequencing after user approval

---

## Stories / Requirement / Test Traceability

- FR-6.1, FR-6.2 -> Steps 14-16, 20-22
- FR-6.3, FR-6.6 -> Steps 13, 17, 20-21
- FR-6.5 -> Steps 11-13, 18, 21
- NFR-ES-01..06 -> Steps 13-23
- NFR-ES-07 -> Steps 11, 13-19 (in-memory validation only, no new external hop)
- TC-ES-001..008 -> Steps 20-23

---

## Brownfield File Touch List

Expected modified files:
- `services/event-service/pyproject.toml`
- `services/event-service/src/main.py`
- `services/event-service/src/api/routes/events.py`
- `services/event-service/tests/test_api.py`
- `services/event-service/tests/conftest.py`
- `services/event-service/CHANGELOG.md`

Expected created files:
- `services/event-service/src/api/dependencies.py`
- `services/event-service/tests/test_multi_tenancy.py`
- `aidlc-docs/platform/multi-tenancy/construction/event-service/code/code-summary.md`
