# Logical Components - uow-shared-auth-foundation

## Component Topology
Selected logical split:
1. AuthValidator
2. TrustEvaluator
3. ObservabilityAdapter
4. PolicySourceResilience

## 1) AuthValidator
Responsibilities:
- Validate JWT cryptographic/base claims.
- Normalize tuple-first canonical auth context.
- Perform delegated-claim structural validation.

Interfaces:
- validate_token(raw_token) -> token_claims
- normalize_context(token_claims, headers, route_context) -> canonical_context
- validate_delegated_claims(canonical_context) -> validation_result

Dependencies:
- Token crypto/verifier provider
- Claim schema validators

## 2) TrustEvaluator
Responsibilities:
- Evaluate trust-policy hook contract for route-specific decisions.
- Apply issuer pinning checks.
- Invoke replay-check hook and replay-store adapter.

Interfaces:
- evaluate(canonical_context, route_policy) -> trust_decision
- check_replay(canonical_context, token_id) -> replay_decision

Dependencies:
- PolicySourceResilience
- IssuerPinningPolicy
- ReplayStoreAdapter

## 3) ObservabilityAdapter
Responsibilities:
- Emit structured decision logs.
- Emit metrics with tier tags and decision dimensions.
- Emit and correlate tracing spans/events.

Interfaces:
- emit_decision_log(decision_event)
- emit_metrics(metric_event)
- trace_scope(context) / correlate_decision_event(trace_id, decision_id)

Dependencies:
- Logging backend
- Metrics backend
- Tracing backend

## 4) PolicySourceResilience
Responsibilities:
- Provide resilient trust-policy retrieval.
- Manage cache-aside lifecycle with bounded TTL.
- Enforce staleness guard and fail-closed post-expiry.

Interfaces:
- get_policy(policy_key, now) -> policy_result
- refresh_policy(policy_key) -> refresh_result
- is_policy_fresh(policy_record, now) -> bool

Dependencies:
- PolicySourceAdapter
- PolicyCache
- Clock/TTL policy config

## Cross-Component Control Flow
1. AuthValidator validates and normalizes request context.
2. TrustEvaluator requests route trust policy through PolicySourceResilience.
3. TrustEvaluator applies issuer pinning and replay checks.
4. Trust decision returned with classified reason/provenance.
5. ObservabilityAdapter emits correlated logs/metrics/traces for every decision.

## Error and Failure Boundaries
- AuthValidator errors: token/claim issues -> deny (401 where appropriate).
- TrustEvaluator denials: trust/policy/replay failure -> deny (403 where appropriate).
- PolicySourceResilience failures after TTL expiry -> deny delegated-dependent path.
- ObservabilityAdapter failures must not open auth path; auth decision remains authoritative.

## Performance/Validation Support Components
- TierMetricsTagger (within ObservabilityAdapter)
- GuardrailThresholdsPolicy (configuration object used by validation tooling)
- ValidationReporter (reports per-tier pass/fail for acceptance runs)

## Refactor Safety Components (Process-Logical)
- SliceBoundaryPlan (sequence of refactor slices)
- CrossServiceRegressionGate (mandatory checkpoint per slice)
- ContractAssertionSet (verifies expected behavior between slices)

## Traceability
- NFR requirements source:
  - aidlc-docs/platform/identity-service/construction/uow-shared-auth-foundation/nfr-requirements/nfr-requirements.md
  - aidlc-docs/platform/identity-service/construction/uow-shared-auth-foundation/nfr-requirements/tech-stack-decisions.md
- NFR design patterns source:
  - aidlc-docs/platform/identity-service/construction/uow-shared-auth-foundation/nfr-design/nfr-design-patterns.md
