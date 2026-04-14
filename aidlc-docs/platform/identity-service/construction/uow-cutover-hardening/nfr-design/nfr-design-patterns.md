# NFR Design Patterns - uow-cutover-hardening

## Scope and Inputs
This design incorporates the approved NFR design answers for hard cutover:
- Q1: A
- Q2: A
- Q3: B
- Q4: A
- Q5: A
- Q6: A
- Q7: A

Source artifacts:
- aidlc-docs/platform/identity-service/construction/uow-cutover-hardening/nfr-requirements/nfr-requirements.md
- aidlc-docs/platform/identity-service/construction/uow-cutover-hardening/nfr-requirements/tech-stack-decisions.md

## Pattern ND-1: Strict JWKS Verification with Bounded Last-Known-Good Cache
Design intent:
- Always resolve verifier material from trusted JWKS/public-key sources.
- Keep a bounded last-known-good key cache for temporary upstream issues.
- Enforce deterministic fail-closed behavior once cache TTL is exceeded.

Design constraints:
- No permissive fallback to alternate verifier modes.
- Cache usage is resilience-only, not policy downgrade.

Traceability:
- NFR-3, NFR-4
- SECURITY-08, SECURITY-15

## Pattern ND-2: Typed Denial Taxonomy and Fail-Closed Decisioning
Design intent:
- Unknown `kid` and invalid signature both terminate with explicit deny decisions.
- Denials are tagged with typed reason codes for telemetry and alerts.

Minimum reason code set:
- `unknown_kid`
- `invalid_signature`
- `jwks_unavailable_cache_expired`
- `issuer_trust_validation_failed`

Traceability:
- NFR-5, NFR-6
- SECURITY-03, SECURITY-14, SECURITY-15

## Pattern ND-3: Rotation Freshness via Event Invalidation plus Polling Backstop
Design intent:
- Primary freshness mechanism is event-triggered cache invalidation.
- Secondary safety mechanism is bounded polling refresh.
- End-to-end key propagation objective remains <= 5 minutes.

Design constraints:
- Refresh strategy must be deterministic and measurable.
- Overlap windows are explicit; stale key acceptance past overlap is disallowed.

Traceability:
- NFR-4
- SECURITY-14, SECURITY-15

## Pattern ND-4: Canonical Alert Signal Contracts with Thresholds
Design intent:
- Define stable alert signal names and threshold contracts now.
- Keep monitoring-vendor implementation decoupled from alert semantics.

Required signal families:
- Denial spike alerts
- Admin override anomaly alerts
- Unknown `kid` and signature failure spike alerts

Traceability:
- NFR-5, NFR-6
- SECURITY-03, SECURITY-14

## Pattern ND-5: Deterministic Deployment Rollback Safety
Design intent:
- Rollback is release/deployment based, not runtime mode switching.
- Use a deterministic runbook with explicit entry criteria and post-rollback verification matrix.

Design constraints:
- Rollback paths retain fail-closed semantics.
- Post-rollback verification covers auth correctness and isolation safety.

Traceability:
- NFR-7
- SECURITY-08, SECURITY-15

## Pattern ND-6: Local Bootstrap Parity with Production Trust Model
Design intent:
- `soorma dev` defaults to asymmetric RS256 keypair and JWKS bootstrap automation.
- HS256 exists only as an explicit non-default test path.

Design constraints:
- Local defaults must not weaken production-aligned trust contracts.

Traceability:
- NFR-8
- SECURITY-11, SECURITY-15

## Pattern ND-7: Bounded Delegated Issuer Trust Finalization
Design intent:
- Finalize delegated issuer OIDC/JWKS trust for this unit within approved boundaries.
- Scope is limited to trust metadata validation, JWKS retrieval/cache/rotation, and policy-gated delegated claim acceptance.

Design constraints:
- No product-surface expansion beyond approved unit boundaries.
- Delegated claims remain deny-by-default unless trust and policy checks pass.

Traceability:
- NFR-9
- SECURITY-08, SECURITY-11, SECURITY-15

## Security Baseline Alignment Summary
- SECURITY-03: Compliant in design (structured auth/verification logging and alert signal contract requirements).
- SECURITY-08: Compliant in design (deny-by-default authorization and strict token validation expectations).
- SECURITY-11: Compliant in design (security controls are layered and isolated as dedicated patterns).
- SECURITY-14: Compliant in design (explicit security event alerting and measurable telemetry contracts).
- SECURITY-15: Compliant in design (error and trust-source failures resolve fail-closed).

All other SECURITY rules are tracked as N/A at this stage because no code or infrastructure resources are produced in this artifact.