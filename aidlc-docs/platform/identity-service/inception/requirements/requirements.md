# Requirements Specification - Identity Service (Soorma Core)

## Intent Analysis Summary
- **User Request**: Design and implement an identity service for soorma-core that aligns with current architecture (not legacy brief assumptions), enforces two-tier tenancy, supports platform-tenant onboarding and principal management, and issues JWTs for multiple access modes.
- **Request Type**: New feature with architectural impact.
- **Scope Estimate**: Multiple components (new service + SDK/common-library auth updates + ingress auth pattern).
- **Complexity Estimate**: Complex (security-critical, tenancy-critical, staged rollout, extension-enabled workflow).

## Architectural Alignment (docs/ARCHITECTURE_PATTERNS.md)
- **Section 1 (Two-tier tenancy)**: Identity service anchors platform-tenant identity and governs delegated service-tenant/service-user trust context.
- **Section 2 (Two-layer SDK)**: Agent handlers must use `PlatformContext` wrappers; identity capabilities must be exposed via wrapper layer, not direct low-level imports.
- **Section 3 (Event choreography)**: Event paths continue explicit response-event/correlation conventions; event-service remains trust boundary for event ingress sanitization.
- **Section 4 (Multi-tenancy/RLS)**: Authorization context must preserve platform-tenant isolation; delegated identities handled as scoped claims under platform governance.
- **Section 6 (Error handling)**: Auth failures must be fail-closed and safely surfaced.
- **Section 7 (Testing)**: Unit + integration coverage required for wrappers, service APIs, and auth flows.

## Scope Decisions (From Clarification Answers)
1. Identity Service owns platform-tenant identity domain and principals under that tenant.
2. In-scope principal types:
- Developer users with roles `admin`, `developer`.
- Machine principals for agents/tools with roles like `planner`, `worker`, `tool`.
3. GCIP is out of current scope. Local provider is default in v1.
4. Provider architecture must be extensible via interface/adapter model for future alternate providers (for example GCIP adapter in self-hosted/cloud variants).
5. v1 onboarding minimum includes delegated issuer registration per platform tenant.
6. v1 token scope uses option C baseline (no refresh token/introspection in v1; phase-2 hardening planned).
7. Delegated trust model is phased:
- Phase 1: static issuer key allowlist per tenant.
- Phase 2: OIDC discovery + JWKS per tenant.
8. Namespace handling for external user IDs is configurable per tenant via mapping rules while auth remains tuple-authoritative.
9. Claim model uses mandatory platform-principal claims plus optional delegated service context claims in trusted/validated flows.
10. Ingress validation scope: all soorma-core service API ingress (future gateways/proxies must follow same auth pattern via SDK/common library support).
11. JWT migration sequence is incremental and mergeable:
- Add JWT in `soorma-service-common` with temporary header coexistence.
- Update SDK clients/wrappers to send JWT.
- Remove header auth support.
12. Full scope delivery requested: complete specification and actual implementation in Construction phase.

## Functional Requirements

### FR-1 Platform Tenant Identity Domain
Identity service shall create and manage platform-tenant identity domains used as root trust boundaries for soorma-core access.

### FR-2 Principal Management
Identity service shall support CRUD/lifecycle operations for:
- Human principals (developer users)
- Machine principals (planner/worker/tool)
and role assignment under each platform tenant.

### FR-3 Role Model Enforcement
Identity service shall enforce role-based authorization semantics with at minimum:
- `admin`
- `developer`
- machine role family (`planner`, `worker`, `tool`)

### FR-4 Tenant Onboarding
Identity service shall onboard a new platform tenant with bootstrap configuration including:
- Initial admin principal
- Optional machine principal bootstrap
- Delegated issuer registration metadata slot(s)

### FR-5 Delegated Issuer Registration
Identity service shall register delegated issuer trust metadata per platform tenant for future validation of externally asserted service-tenant/service-user identities.

### FR-6 Token Issuance (v1)
Identity service shall issue JWTs for:
- Platform human principals
- Platform machine principals
- Delegated token flow where tenant identity service assertions are accepted under configured trust policy

### FR-7 Claim Contract (Mandatory + Optional)
Issued JWTs shall include mandatory base claims:
- `iss`, `sub`, `aud`, `exp`, `iat`, `jti`
- `platform_tenant_id`, `principal_id`, `principal_type`, `roles`
Optional delegated context claims (`service_tenant_id`, `service_user_id`) may be included only for trusted/validated delegated flows.

### FR-8 Delegated Context Policy
Identity service and ingress validation logic shall enforce route/policy controls defining when delegated context claims are accepted.

### FR-9 External Principal Namespace Mapping
Identity workflows shall support per-tenant configurable mapping rules that normalize external identities into canonical principal keys without overriding tuple-authoritative auth context.

### FR-10 Ingress Authentication Pattern
All soorma-core service API ingress shall validate identity tokens per defined auth pattern. Future ingress components (API gateway, connection gateway, tenant-aware proxy) must adopt this pattern through SDK/common-library support.

### FR-11 Incremental JWT Rollout
System shall support three phased units of work:
1. JWT capability in `soorma-service-common` with temporary header coexistence.
2. SDK wrapper/client JWT request support.
3. Header-based auth removal.

FR-11 Compatibility Constraint:
- During phases 1 and 2, implement JWT by evolving existing dependency methods and existing DI integration points rather than introducing parallel router/dependency contracts.
- Service route handlers and router dependency-injection wiring should remain unchanged at call sites during coexistence; auth behavior changes should be encapsulated within existing shared dependencies/middleware abstractions.
- Any unavoidable signature changes must be backward-compatible and non-breaking for existing service/router usage until phase 3 cleanup.

### FR-12 SDK Two-Layer Compliance
Identity capabilities exposed to developer code shall be available via `PlatformContext` wrapper APIs and must delegate to underlying service clients; direct service-client usage in agent handlers is prohibited.

### FR-13 Auditability
Identity service shall emit structured audit events for key identity actions:
- principal creation/update/revocation
- token issuance/revocation
- delegated issuer registration changes
- authorization failures on ingress

## Non-Functional Requirements

### NFR-1 Security Baseline Enforcement
Security baseline extension is enabled and must be treated as blocking constraints for applicable stages.

### NFR-2 Fail-Closed Authorization
All authn/authz validation failures must deny access by default and return safe error responses.

### NFR-3 Performance Baseline
Token verification and principal authorization checks should be designed for low-latency ingress impact (target SLOs to be finalized in construction NFR stage).

### NFR-4 Observability
Structured logs must include timestamp, correlation/request ID, principal type, platform tenant context, and decision outcome while avoiding sensitive token leakage.

### NFR-5 Extensibility
Provider abstraction must allow alternate identity-provider adapters without changing core business flows and wrapper contracts.

### NFR-6 Testability
Design must support deterministic unit tests for claim validation/policy logic and integration tests for ingress + SDK wrapper flows.

### NFR-7 Backward-Compatible Development Sequence
Development sequencing must support incremental PR mergeability during rollout stages even when temporary dual auth paths exist.

## Security Requirements (Applicable Baseline Rules)
- **SECURITY-03, SECURITY-08, SECURITY-15** apply directly in v1 design and implementation:
  - structured logging
  - application-level access control and server-side token validation
  - safe exception handling with fail-closed defaults
- **SECURITY-10, SECURITY-11, SECURITY-14** apply to implementation and CI/CD/test instructions:
  - dependency and supply-chain controls
  - secure design modularization
  - alerting/monitoring coverage
- **Infrastructure-specific controls** (for example SECURITY-01, SECURITY-02, SECURITY-07) are design-time N/A in this inception requirements artifact and must be evaluated in infrastructure-focused stages when concrete deployment resources are defined.

## Out of Scope (Current Cycle)
- Immediate GCIP integration in core implementation.
- Immediate refresh-token and introspection endpoint implementation (deferred to hardening phase).
- Full direct external end-user gateway productization (future gateway components not yet implemented).

## Implementation Success Criteria
1. Identity service domain and APIs are specified and approved.
2. Provider abstraction and local provider strategy are specified and approved.
3. JWT claim contract and delegated trust policy are specified and approved.
4. Incremental rollout plan (service-common -> SDK -> header removal) is approved.
5. Construction phase can proceed with implementation-ready scope and security constraints.

## Traceability Summary
- Q1-Q11 resolved with explicit rationale and no unresolved ambiguities.
- Extension decisions:
  - JIRA tickets: Enabled
  - PR checkpoints: Enabled
  - QA test cases: Enabled (scope `happy-path-negative`)
  - Security baseline: Enabled
- Next expected inception stage: User Stories (required due multi-principal user impact and acceptance-criteria needs).