# Components

## Design Strategy
Primary partitioning: hybrid capability modules with shared cross-cutting modules.

## Component 1: TenantOnboardingComponent
- Purpose: Create and initialize platform-tenant identity domain.
- Responsibilities:
  - Create tenant identity boundary.
  - Bootstrap admin principal.
  - Optionally bootstrap machine principals.
  - Initialize tenant policy defaults.
- Interfaces:
  - Internal service API for onboarding orchestration.
  - Validation hooks for tenant bootstrap rules.

## Component 2: PrincipalManagementComponent
- Purpose: Manage lifecycle of human and machine principals.
- Responsibilities:
  - Create/update/deactivate principals.
  - Assign and validate roles.
  - Enforce principal state transitions.
- Interfaces:
  - Principal CRUD and role assignment methods.
  - Status and revocation checks.

## Component 3: TokenIssuanceComponent
- Purpose: Issue platform JWTs for human and machine principals.
- Responsibilities:
  - Validate principal eligibility.
  - Build mandatory claim sets.
  - Apply tenant-level token policy constraints.
- Interfaces:
  - Token issue/validate metadata methods.
  - Claim composition helpers.

## Component 4: DelegatedTrustComponent
- Purpose: Manage trusted delegated issuer configuration and delegated context validation.
- Responsibilities:
  - Register/update issuer metadata and keys.
  - Validate delegated assertions using v1 static-key model.
  - Expose extension points for future OIDC/JWKS.
- Interfaces:
  - Issuer registration and trust-evaluation methods.
  - Delegated claim acceptance policy checks.

## Component 5: ClaimContextPolicyComponent
- Purpose: Normalize and evaluate context claims for ingress authorization.
- Responsibilities:
  - Enforce mandatory and optional claim contract.
  - Evaluate route/policy conditions for delegated context claims.
  - Normalize external principal identifiers using tenant mapping rules.
- Interfaces:
  - Claim validation and mapping policy methods.

## Component 6: AuditTelemetryComponent
- Purpose: Emit structured audit and security telemetry events.
- Responsibilities:
  - Log identity lifecycle and trust changes.
  - Emit token issuance and authorization decision events.
  - Preserve correlation identifiers and tenant context.
- Interfaces:
  - Structured event recording methods.
  - Audit query integration hooks.

## Component 7: ProviderFacadeComponent
- Purpose: Provide domain-level provider abstraction with capability adapters.
- Responsibilities:
  - Route provider calls through common facade.
  - Encapsulate local-provider implementation.
  - Support future adapter additions without changing business components.
- Interfaces:
  - Domain facade contracts for principals, tokens, and issuer trust.

## Component 8: CompatibilityAdapterComponent
- Purpose: Encapsulate FR-11 phased compatibility behavior.
- Responsibilities:
  - Keep route/DI call sites stable while JWT path is introduced.
  - Translate legacy context into JWT-centric internal contract during coexistence.
  - Support phase-3 cleanup for header-path removal.
- Interfaces:
  - Shared dependency/middleware integration points only (no route-level branch logic).