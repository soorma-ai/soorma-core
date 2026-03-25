# NFR Requirements — U7: services/event-service
## Initiative: Multi-Tenancy Model Implementation
**Date**: 2026-03-25

---

## Overview

The dominant NFR for the Event Service multi-tenancy update is Security: the service becomes the trust boundary for event-bus platform identity and event metadata sanitization. Secondary NFRs are Reliability (fail-closed publish behavior) and Maintainability (dependency-injected identity resolution to allow future authentication transport changes).

---

## NFR-ES-01: Authoritative Platform Identity Injection (SECURITY — BLOCKING)

**Category**: Security  
**Priority**: Critical  
**Source**: FR-6.3, FR-6.6, NFR-1.1, SECURITY-08

**Requirement**:  
Event Service MUST inject and overwrite `event.platform_tenant_id` from authenticated request context on every publish. Payload-supplied `platform_tenant_id` MUST never be trusted or forwarded unchanged.

**Acceptance Criteria**:
- Publish path resolves platform identity from DI helper only
- `event.platform_tenant_id` is overwritten unconditionally before publish
- TC-ES-002 and TC-ES-003 pass
- No route/body/query parameter accepts authoritative platform identity as a user-controlled input

---

## NFR-ES-02: Central Metadata Sanitization (SECURITY — BLOCKING)

**Category**: Security / Data Integrity  
**Priority**: Critical  
**Source**: Q5 design decision, SECURITY-05, SECURITY-15

**Requirement**:  
Event Service MUST sanitize event metadata centrally before publish:
- trim whitespace on `tenant_id` and `user_id`
- normalize empty strings to `None`
- require a non-empty `tenant_id` subject scope after sanitization
- require a non-empty `user_id` actor identity after sanitization
- enforce max length 64 for `platform_tenant_id`, `tenant_id`, and `user_id` when present
- fail closed on invalid values

**Acceptance Criteria**:
- Oversized identity metadata causes validation error and no publish
- Events without `tenant_id` are rejected; every event must carry a service-tenant scope
- Events without `user_id` are rejected; machine/service actors must provide an explicit actor identity
- TC-ES-005 and TC-ES-008 pass
- No truncation behavior is allowed

---

## NFR-ES-03: Dependency-Injected Identity Resolution (MAINTAINABILITY / SECURITY — BLOCKING)

**Category**: Maintainability / Security  
**Priority**: High  
**Source**: Q3 design decision, ARCHITECTURE_PATTERNS Section 1

**Requirement**:  
Publish route MUST obtain authoritative platform identity through a dependency-injection abstraction rather than direct header parsing in endpoint code.

**Rationale**:
- Allows migration from `X-Tenant-ID` headers to API key / JWT / service-to-service auth without changing route business logic
- Keeps auth-source mechanics outside endpoint behavior

**Acceptance Criteria**:
- Publish route signature uses `Depends(get_platform_tenant_id)` or equivalent abstraction
- Endpoint implementation does not inspect raw authentication headers directly
- Auth-transport migration can be satisfied by changing dependency/middleware implementation only

---

## NFR-ES-04: Temporary Default Platform Tenant Fallback (RELIABILITY / TRANSITIONAL)

**Category**: Reliability / Transitional Compatibility  
**Priority**: Medium  
**Source**: Q1 decision, FR-1.1

**Requirement**:  
While current pre-identity-service mode remains active, missing platform identity may fall back to `DEFAULT_PLATFORM_TENANT_ID`. This is transitional and must be removable later.

**Acceptance Criteria**:
- Fallback behavior is explicit and isolated in publish path logic
- TC-ES-004 passes
- Design notes mark this as temporary and subject to hardening after identity service rollout

---

## NFR-ES-05: Fail-Closed Publish Semantics (RELIABILITY / SECURITY — BLOCKING)

**Category**: Reliability / Security  
**Priority**: Critical  
**Source**: SECURITY-15, TC-ES-007, TC-ES-008

**Requirement**:  
Event Service MUST not publish any event when request schema validation or identity metadata validation fails.

**Acceptance Criteria**:
- Invalid request body returns client error before publish
- Missing required `tenant_id` returns client error before publish
- Missing required `user_id` returns client error before publish
- Invalid identity metadata returns client error before publish
- Event manager publish call is not invoked on validation failure
- TC-ES-007 and TC-ES-008 pass

---

## NFR-ES-06: Logging Hygiene at Trust Boundary (SECURITY — BLOCKING)

**Category**: Security / Observability  
**Priority**: High  
**Source**: SECURITY-03, SECURITY-14

**Requirement**:  
Validation failures and publish rejections MUST be logged with structured metadata only. Full payload dumps and sensitive data leakage are prohibited.

**Acceptance Criteria**:
- Logs include event id, event type, and correlation context when available
- Logs do not include raw full payload bodies for rejected events
- Spoofed `platform_tenant_id` input is not echoed back as trusted identity

---

## NFR-ES-07: Existing Event Service Availability and Throughput Baseline Unchanged (NON-BLOCKING)

**Category**: Performance / Availability  
**Priority**: Medium  
**Source**: Existing service architecture

**Requirement**:  
The multi-tenancy changes must not materially alter Event Service availability model or publish throughput characteristics beyond minimal validation overhead.

**Acceptance Criteria**:
- No new external network hop introduced in publish path
- No database dependency added
- Sanitization and overwrite steps are in-memory only
- Expected overhead remains negligible relative to existing publish call

---

## Security Baseline Coverage Summary

| Security Rule | Applicability | Coverage in U7 NFR |
|---|---|---|
| SECURITY-03 Application logging | Applicable | NFR-ES-06 |
| SECURITY-05 Input validation | Applicable | NFR-ES-02, NFR-ES-05 |
| SECURITY-08 Access control / trusted identity source | Applicable | NFR-ES-01, NFR-ES-03 |
| SECURITY-11 Secure design | Applicable | NFR-ES-01 through NFR-ES-05 |
| SECURITY-14 Alerting/monitoring | Partially applicable | structured reject logging required now; alerting remains existing service baseline |
| SECURITY-15 Fail-safe defaults | Applicable | NFR-ES-05 |

Non-applicable at this stage for U7: encryption-at-rest, RLS, network configuration, least-privilege IAM, authentication credential storage, because U7 introduces no new persistence or infrastructure resources.
