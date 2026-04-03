# Business Logic Model - uow-shared-auth-foundation

## Objective
Define the auth dependency decision flow for coexistence mode where JWT is authoritative when present and legacy headers are transitional fallback only when JWT is absent.

## Flow 1: Resolve Authentication Context
1. Read raw request auth material into AuthEnvelope.
2. If JWT exists:
   - Validate signature, issuer, audience, expiry, and mandatory claims.
   - On failure: return AuthErrorEnvelope with 401.
   - On success: construct CanonicalAuthContext from JWT claims.
3. If JWT absent:
   - Parse legacy headers.
   - Construct CanonicalAuthContext from headers.
4. Normalize context fields and attach correlation metadata.

## Flow 2: Validate Delegated Claim Structure
1. Detect whether service_tenant_id and service_user_id are present as delegated tuple.
2. Validate delegated tuple shape/format.
3. Mark delegated_claims_present in CanonicalAuthContext.
4. On structural invalidity: fail closed with 401.

## Flow 3: Evaluate Trust Decision
1. Service provides RouteAuthPolicy for current endpoint.
2. Shared dependency calls trust-policy hook with CanonicalAuthContext and RouteAuthPolicy.
3. Hook evaluates:
   - flow_type eligibility for route
   - issuer allowlist/policy
   - delegated-context allowance for route
4. Receive TrustDecision.
5. If TrustDecision.allowed is false: fail closed with 403.
6. If allowed: attach provenance and continue.

## Flow 4: Service Authorization Boundary
1. Shared dependency returns canonical context plus trust decision metadata.
2. Service-level handler/middleware performs endpoint-specific authorization.
3. Service enforces role/resource/business rules.
4. Service may apply additional checks based on provenance marker.

## Flow 5: Telemetry Emission
1. Emit structured auth decision event for each request.
2. Include route, status, reason, tenant context, principal context when available, correlation id, and trust outcome.
3. Redact or omit sensitive token internals.

## Decision Table
| Condition | Outcome | Status |
|---|---|---|
| JWT present and valid, trust allowed | Continue with JWT-derived context | Allow |
| JWT present and invalid | Fail immediately, no fallback | 401 |
| JWT absent, headers valid, trust allowed | Continue with header-derived context (coexistence only) | Allow |
| Delegated claims malformed | Fail closed | 401 |
| Trust-policy hook denied | Fail closed | 403 |

## Invariants
1. JWT takes precedence whenever present.
2. No silent fallback from invalid JWT to headers.
3. Route policy ownership remains with each service.
4. Shared dependency owns normalization, trust gate invocation, and safe failure behavior.
5. Authorization decisions are auditable and deterministic for this rollout.
