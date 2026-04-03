# Business Rules - uow-shared-auth-foundation

## Rule Group 1: Auth Source Precedence
1. If JWT exists in the request, JWT path is mandatory and authoritative.
2. If JWT exists and fails validation, reject immediately with no header fallback.
3. Header-based context is evaluated only when JWT is absent.

## Rule Group 2: Tenant and Context Normalization
1. Canonical context must always include platform_tenant_id.
2. For current ingress use cases, service_tenant_id and service_user_id are expected in canonical context.
3. Principal fields may be absent unless route/workflow requires platform actor semantics.

## Rule Group 3: Delegated Claim Structural Validation
1. If delegated claims are present, validate type/format and required constraints.
2. Structural validation alone is insufficient for trust acceptance.
3. Delegated claims must pass trust-policy hook evaluation before route execution.

## Rule Group 4: Trust-Policy Hook Contract
1. Shared dependency invokes trust-policy hook using canonical context plus route policy.
2. Hook returns decision with allowed flag, provenance classification, and reason.
3. If decision is denied, request fails closed.
4. If decision is allowed, provenance is attached to request context for downstream authorization decisions.

## Rule Group 5: Route Ownership Boundaries
1. Services own route-level auth requirements and public endpoint declarations.
2. Shared dependency provides common validation, normalization, and trust gating primitives.
3. Shared dependency must not become the owner of service business authorization policy.

## Rule Group 6: Error Semantics
1. Return 401 for authentication failures (invalid token, missing required auth).
2. Return 403 for authorization/policy denials (role/policy/trust decision denied).
3. Error envelopes must be consistent and safe for production responses.

## Rule Group 7: Telemetry and Audit
1. Emit timestamp, route, decision status, and reason.
2. Emit platform_tenant_id, principal fields when present, and correlation_id when available.
3. Emit delegated claim presence and trust-policy outcome metadata.
4. Never log raw tokens, secrets, or sensitive claim payloads.

## Rule Group 8: Rollout Control Strategy
1. Auth-path behavior is controlled by phased code evolution, not runtime feature toggles.
2. Allowed runtime toggles are observability-only and must not alter allow/deny outcomes.
3. Phase sequence:
   - Phase 1: dual-path support with JWT authoritative when present
   - Phase 2: SDK emits JWT consistently
   - Phase 3: header-auth support removed

## Rule Group 9: Testability and Coverage
1. Unit test coverage must include all precedence and fail-closed branches.
2. Integration tests must cover auth entry paths for consuming services.
3. Regression tests must cover coexistence behavior and mismatch/error paths.
4. Failure-injection tests must include invalid signature, expiry, malformed claims, issuer mismatch, trust denial, and policy-denied routes.

## Security Baseline Mapping for This Stage
- SECURITY-03: Structured logging rules defined and secret-safe logging constraints enforced.
- SECURITY-08: Application-level access control boundaries defined (service-owned route authorization + shared trust gating).
- SECURITY-11: Security-critical logic isolated in shared dependency contracts.
- SECURITY-15: Explicit fail-closed and safe exception/error envelope rules defined.
