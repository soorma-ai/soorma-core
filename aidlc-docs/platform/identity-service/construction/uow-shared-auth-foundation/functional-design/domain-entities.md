# Domain Entities - uow-shared-auth-foundation

## Scope
This unit defines the shared authentication context and trust-decision domain objects used by service dependencies during JWT/header coexistence.

## Entity 1: AuthEnvelope
Purpose: raw request authentication material before normalization.

Fields:
- jwt_token: optional string
- legacy_headers:
  - x_tenant_id: optional string
  - x_service_tenant_id: optional string
  - x_user_id: optional string
- route_id: string
- method: string
- request_id: optional string
- source_hint: optional string

Rules:
- JWT is authoritative when present.
- If JWT is present and invalid, processing fails immediately.
- Header fallback is only possible when JWT is absent.

## Entity 2: CanonicalAuthContext
Purpose: normalized authentication context passed to service authorization logic.

Fields:
- platform_tenant_id: string
- service_tenant_id: optional string
- service_user_id: optional string
- principal_id: optional string
- principal_type: optional string
- roles: list of string, optional
- issuer: string
- audience: string
- flow_type: one of internal_agent, delegated_issuer
- correlation_id: optional string
- source: optional string
- delegated_claims_present: boolean

Rules:
- Tuple-first context is primary for current ingress paths: platform_tenant_id + service_tenant_id + service_user_id.
- Principal fields are optional and only required by workflows that need platform actor identity or delegated role semantics.

## Entity 3: RouteAuthPolicy
Purpose: per-service route policy input to trust evaluation.

Fields:
- route_id: string
- auth_required: boolean
- allow_delegated_context: boolean
- allowed_flows: list of string
- allowed_issuers: list of string, optional
- required_roles: list of string, optional

Rules:
- Route policy ownership remains with each service.
- Shared dependency does not centralize route exception ownership.

## Entity 4: TrustDecision
Purpose: outcome of trust-policy hook evaluation before route execution.

Fields:
- allowed: boolean
- provenance: one of trusted_internal, trusted_delegated, denied
- reason: string
- policy_id: optional string

Rules:
- denied always triggers fail-closed response.
- allowed must include provenance classification.

## Entity 5: AuthErrorEnvelope
Purpose: unified error shape for auth failures.

Fields:
- status_code: integer
- error_code: string
- message: string
- request_id: optional string
- reason: string

Rules:
- Use 401 for authentication failures.
- Use 403 for authorization or policy denials.
- Message must be safe and not leak secret/token internals.
