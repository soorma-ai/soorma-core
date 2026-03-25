# Business Rules — U7: services/event-service
## Initiative: Multi-Tenancy Model Implementation
**Date**: 2026-03-25

---

## BR-U7-01: Event Service is authoritative for platform tenant identity

**Rule**: Event Service must always inject/overwrite `event.platform_tenant_id` from authenticated context before publish.

**Rationale**: Prevents platform-tenant spoofing by clients and enforces trust boundary at publish ingress.

**Enforcement**: Unconditional overwrite on publish path.

---

## BR-U7-02: Dependency injection is the identity-resolution interface

**Rule**: Publish route resolves platform identity through DI helper (`Depends(get_platform_tenant_id)`) rather than direct header parsing in endpoint code.

**Rationale**: Future-proofs auth extraction changes (header -> API key/JWT) while preserving endpoint contract.

**Enforcement**: Route signature includes DI parameter for platform tenant resolution.

---

## BR-U7-03: Temporary default fallback is allowed for missing platform identity

**Rule**: If resolved platform identity is missing, use `DEFAULT_PLATFORM_TENANT_ID` for current phase.

**Rationale**: Maintains current compatibility baseline until full identity service and service-to-service auth are introduced.

**Enforcement**: Explicit fallback branch before publish.

**Follow-up**: Tighten to reject-missing mode in post-identity-service hardening iteration.

---

## BR-U7-04: Service metadata is sanitized centrally before publish

**Rule**: Event Service must sanitize payload `tenant_id` and `user_id` centrally:
- trim whitespace
- normalize empty string to `None`
- validate max length 64 when present

**Rationale**: Single trust-boundary sanitization policy prevents inconsistent metadata quality across producers.

**Enforcement**: Normalization + validation step runs on every publish.

---

## BR-U7-05: `tenant_id` and `user_id` are mandatory for all events

**Rule**: Every event must include both a `tenant_id` subject scope and a `user_id` actor identity. Human-originated events use end-user identities; automation/system-originated events must use a provisioned service tenant and machine/service actor identity.

**Rationale**: Preserves complete subject scoping and actor traceability and avoids mixing fully-scoped events with partially-scoped ones.

**Enforcement**: After sanitization, missing/empty `tenant_id` or `user_id` is a validation failure and blocks publish.

---

## BR-U7-06: Fail closed on malformed or oversized metadata

**Rule**: Do not publish when request schema is invalid, `tenant_id` or `user_id` is missing after sanitization, or any identity dimension exceeds max length.

**Rationale**: Prevents propagation of invalid metadata and aligns with secure input-validation baseline.

**Enforcement**: Return validation/client error; skip event manager publish call.

---

## BR-U7-07: No semantic mutation of service tenant/user values

**Rule**: Beyond sanitization normalization, Event Service must not remap or reinterpret `tenant_id`/`user_id` semantics.

**Rationale**: Producer semantics must remain stable; Event Service only guarantees metadata hygiene and platform identity integrity.

**Enforcement**: No transformation beyond trim/empty normalization and length checks.

---

## BR-U7-08: Observable anti-spoofing behavior must be test-covered

**Rule**: Tests must prove SDK-supplied `platform_tenant_id` is overwritten and never reaches bus unchanged.

**Rationale**: This is the core security property for U7.

**Enforcement**: Unit/integration tests mapped to TC-ES-003 and related publish-path checks.

---

## BR-U7-09: Logging must be structured and non-sensitive

**Rule**: Validation and rejection logs include event id/type and correlation context, but must not dump full sensitive payloads.

**Rationale**: Supports operations while meeting logging hygiene requirements.

**Enforcement**: Structured warning/error logs only.

---

## Traceability

- FR-6.3 -> BR-U7-01, BR-U7-08
- FR-6.5 -> BR-U7-02
- FR-6.6 -> BR-U7-01, BR-U7-02, BR-U7-06
- NFR-1.1 -> BR-U7-01, BR-U7-02
- TC-ES-001..008 -> BR-U7-01..09 coverage points
