# NFR Design Patterns - uow-shared-auth-foundation

## Purpose
This document maps approved NFR requirements to concrete design patterns for the shared auth foundation unit.

## Pattern 1: Trust Policy Source Resilience
- Selected pattern: cache-aside with bounded TTL and strict fail-closed post-expiry.
- Design intent:
  - Keep trust-policy source load bounded.
  - Preserve deterministic denial when cached policy is stale beyond allowed TTL.
- Components involved:
  - PolicySourceAdapter
  - PolicyCache (in-memory, optional shared backing if introduced later)
  - StalenessGuard
- Failure semantics:
  - cache hit within TTL: proceed
  - cache miss or source fetch failure: use last-known-good only if within bounded validity
  - post-expiry: deny delegated-dependent flows fail-closed

## Pattern 2: Observability Correlation Depth
- Selected pattern: full tracing boundary with per-decision structured event correlation.
- Design intent:
  - Provide end-to-end diagnosability for auth decisions.
  - Correlate decision events with traces for security and operational investigation.
- Components involved:
  - AuthTraceAdapter
  - DecisionEventEmitter
  - CorrelationContextPropagator
- Required trace boundaries:
  - dependency entry/exit
  - trust-policy evaluation
  - delegated-claim validation
  - per-decision event correlation

## Pattern 3: Performance Validation Guardrails (Non-Adaptive Runtime)
- Selected pattern: metrics tier tagging + policy-driven threshold object.
- Design intent:
  - Support profile-based validation without runtime behavior adaptation.
  - Keep open-core portability and avoid assumptions about deployment topology.
- Components involved:
  - TierMetricsTagger
  - GuardrailThresholdsPolicy
  - ValidationReporter
- Tier model:
  - 100 / 500 / 1000 RPS per instance (+ optional burst tier)

## Pattern 4: Refactor Safety Under Compatibility Override
- Selected pattern: incremental slices + service-wide regression checkpoint per slice.
- Design intent:
  - Allow pre-release direct refactors while controlling blast radius.
  - Replace compatibility wrappers with stricter regression checkpoints.
- Components/process:
  - SliceBoundaryPlan
  - ContractAssertions per slice
  - CrossServiceRegressionGate per slice
- Note:
  - This pattern is the compensating control for approved FR-11 compatibility override in this unit.

## Pattern 5: Issuer Pinning + Replay Resistance
- Selected pattern: issuer allowlist + replay hook + bounded replay-store abstraction with expiry policy.
- Design intent:
  - Enforce trust provenance and prevent token replay in bounded windows.
- Components involved:
  - IssuerPinningPolicy
  - ReplayCheckHook
  - ReplayStoreAdapter
  - ReplayExpiryPolicy
- Security outcome:
  - replay risk reduced with explicit lifecycle-managed replay state.

## Pattern 6: Trust Hook Error Handling
- Selected pattern: uniform deny + classified error taxonomy.
- Error classes:
  - source_unavailable
  - invalid_policy
  - timeout
- Design intent:
  - Preserve fail-closed semantics.
  - Improve diagnosability and alert routing with explicit reason classes.
- Response behavior:
  - authentication errors map to 401 where applicable
  - trust/authorization denials map to 403
  - no service-specific permissive fallback

## Security Baseline Mapping (Design Stage)
- SECURITY-03: Structured logging/tracing/event correlation patterns included.
- SECURITY-08: Access-control/trust-gating boundaries explicit.
- SECURITY-11: Security-critical concerns decomposed into explicit components.
- SECURITY-15: Fail-closed and classified-error handling patterns defined.
- Other SECURITY rules: N/A at this stage unless tied to explicit design choices above.
