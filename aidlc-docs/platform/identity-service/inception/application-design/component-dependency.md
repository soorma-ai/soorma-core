# Component Dependency

## Dependency Matrix

| Consumer Component | Depends On | Dependency Type | Purpose |
|---|---|---|---|
| TenantOnboardingComponent | PrincipalManagementComponent | Direct service dependency | Bootstrap admin/machine principals |
| TenantOnboardingComponent | ClaimContextPolicyComponent | Validation dependency | Validate onboarding policy constraints |
| PrincipalManagementComponent | ProviderFacadeComponent | Adapter dependency | Persist/retrieve principal state |
| TokenIssuanceComponent | PrincipalManagementComponent | Read dependency | Validate principal eligibility |
| TokenIssuanceComponent | ClaimContextPolicyComponent | Policy dependency | Enforce claim contract and route policy |
| TokenIssuanceComponent | ProviderFacadeComponent | Adapter dependency | Sign and issue tokens |
| DelegatedTrustComponent | ProviderFacadeComponent | Adapter dependency | Store/evaluate issuer trust metadata |
| DelegatedTrustComponent | ClaimContextPolicyComponent | Policy dependency | Validate delegated context rules |
| ClaimContextPolicyComponent | CompatibilityAdapterComponent | Context dependency | Normalize legacy/JWT context during coexistence |
| Identity Domain Service | CompatibilityAdapterComponent | Shared dependency | Stable DI integration during FR-11 rollout |
| Identity Domain Service | AuditTelemetryComponent | Side-effect dependency | Emit lifecycle/audit events |
| AuditTelemetryComponent | Event service boundary | External integration | Publish async telemetry events |

## Communication Patterns
- Synchronous:
  - Request validation, policy evaluation, principal state checks, token issuance, trust validation.
- Event-assisted:
  - Audit enrichment, security telemetry distribution, optional async reporting.

## Data Flow (Text)
1. API ingress request enters existing DI pipeline.
2. CompatibilityAdapter resolves auth context (JWT first, legacy translation during coexistence).
3. Business component executes capability workflow.
4. Provider facade invokes local provider adapters.
5. Response returns synchronously.
6. Audit/telemetry side effects are emitted.

## FR-11 Compatibility Constraint Mapping
- Compatibility logic is centralized in shared dependencies/middleware and adapter components.
- Route handlers do not contain explicit branch logic per auth mode.
- Existing service/router dependency injection call sites remain stable until legacy path is retired.

## External Dependencies
- `libs/soorma-service-common`: auth dependency abstractions and middleware hooks.
- `libs/soorma-common`: shared models and claim schema contracts.
- `sdk/python/soorma`: wrapper and client invocation surfaces.
- `services/event-service`: telemetry/event boundary for async side effects.