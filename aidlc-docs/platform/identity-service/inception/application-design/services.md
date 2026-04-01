# Services

## Service Architecture
The application design uses one primary identity service with shared dependency abstractions and SDK wrapper integrations.

## Service 1: Identity Domain Service
- Responsibilities:
  - Tenant onboarding and principal lifecycle.
  - Token issuance and claim policy enforcement.
  - Delegated issuer trust registration and validation.
- Core Interactions:
  - Calls ProviderFacadeComponent for provider-backed operations.
  - Uses CompatibilityAdapterComponent for phased rollout behavior.
  - Emits events to AuditTelemetryComponent.

## Service 2: Auth Context Dependency Service (Shared)
- Responsibilities:
  - Parse incoming auth material.
  - Build canonical auth context for downstream components.
  - Keep service/router DI call sites stable during coexistence.
- Orchestration Pattern:
  - Synchronous in request path.
  - No route-specific branching logic.

## Service 3: Policy Evaluation Service
- Responsibilities:
  - Evaluate route-level and tenant-level access policy.
  - Enforce delegated context acceptance rules.
  - Validate token TTL and scope constraints.
- Orchestration Pattern:
  - Synchronous in core auth path.

## Service 4: Audit and Security Telemetry Service
- Responsibilities:
  - Capture identity lifecycle and trust changes.
  - Publish structured security events.
  - Support compliance and observability needs.
- Orchestration Pattern:
  - Event-assisted side effects for non-blocking telemetry where feasible.
  - Critical audit write failures handled per fail-closed policy requirements.

## Service Interactions and Orchestration
1. Request enters service API ingress.
2. Auth Context Dependency resolves canonical auth context.
3. Identity Domain Service executes core operation.
4. Policy Evaluation validates authorization and delegated context rules.
5. Provider facade performs persistence/signing/trust operations.
6. Audit service records structured events.

## Interaction Style Decision
- Core path: synchronous orchestration for deterministic auth behavior.
- Side effects: event-assisted for audit enrichment and asynchronous telemetry where policy permits.

## SDK Integration Pattern
- SDK wrappers call service APIs through existing stable method contracts.
- Internal contracts evolve JWT-centric; compatibility adapter protects existing caller surfaces during rollout phases.
- No direct service-client imports in agent handlers; wrappers remain required entrypoint.