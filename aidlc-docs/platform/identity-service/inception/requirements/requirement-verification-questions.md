# Requirements Verification Questions

Please answer all questions by filling the [Answer]: line for each question.

## Question 1
What should be the primary scope boundary for the new Identity Service in soorma-core?

A) Tier 1 only: Developer tenant onboarding and platform-level identity admin

B) Tier 2 only: End-user and application tenant token issuance

C) Both tiers in one service with explicit domain separation

D) Keep current flows; document only, no new service implementation now

X) Other (please describe after [Answer]: tag below)

[Answer]: X
Other detail:
- Scope model: Identity Service owns platform-tenant identity domain and identities under that platform tenant.
- Principal types in scope:
	- Developer user accounts with roles: `admin`, `developer`
	- Machine accounts for agents/tools: `planner`, `worker`, `tool`
- Tier relationship:
	- Tier 2 (`service_tenant`, `service_user`) identities are owned within the platform tenant boundary.
	- Current trust model accepts tier-2 identities as asserted by authenticated trusted developer-tenant agents.
- Future model:
	- Developer tenants may issue signed JWTs containing `service_tenant` and `service_user`.
	- JWT issuer metadata/keys must be registered under the platform tenant profile in Identity Service.
	- This enables validation for direct gateway access paths outside trusted agents (future capability).

Rationale:
- Preserves Soorma two-tier tenancy while keeping trust anchored in platform-tenant identity governance.
- Supports current trusted-agent operating model and provides a migration path to externally validated end-user access.

## Question 2
How should Google Customer Identity Platform (GCIP) be used?

A) GCIP as source of truth for tenant/user identities; soorma Identity Service as admin and token broker

B) GCIP only for authentication; soorma stores canonical identity records and issues all tokens

C) Hybrid by principal type: users in GCIP, machine identities in soorma

D) Start with local stub provider and defer GCIP integration

X) Other (please describe after [Answer]: tag below)

[Answer]: X
Other detail:
- GCIP is out of current scope and treated as obsolete in the original brief for open-core soorma-core.
- Implement a local identity provider as the initial/default provider.
- Design for extensibility via provider abstraction:
	- Define an identity-provider interface/port.
	- Implement LocalIdentityProvider as the first concrete adapter.
	- Keep extension path open for alternate providers (for example GCIP adapter) in self-hosted deployments and soorma-cloud.
- Provider selection should be configuration-driven to avoid changing business-layer identity flows when swapping providers.

Rationale:
- Aligns with current open-source/open-core direction.
- Minimizes initial complexity under the scope defined in Question 1.
- Preserves forward compatibility for hosted/cloud and partner-specific identity backends.

## Question 3
For tenant onboarding, which minimum capabilities are required in v1?

A) Create platform customer tenant and bootstrap admin user

B) A + machine principal bootstrap for BYO agents/tools

C) B + API key lifecycle (create, rotate, revoke)

D) C + delegated external identity-provider registration per tenant

X) Other (please describe after [Answer]: tag below)

[Answer]: D) Tenant-level delegated issuer registration for validating JWTs that represent service-tenant and service-user identities. This is about trust setup per platform tenant for future direct-access paths.

Clarification for Question 3 Option D:
- This means tenant-level delegated issuer registration for validating service-tenant/service-user JWT assertions (future direct-access flows).
- This is not the same as platform deployment provider selection (for example Local provider vs GCIP adapter), which is covered by Question 2 architecture direction.

## Question 4
Which token types are in v1 scope?

A) Human-user access JWT only

B) Human-user JWT + machine JWT

C) Human-user JWT + machine JWT + delegated token for tenant identity service

D) All above + refresh tokens and token introspection endpoint

X) Other (please describe after [Answer]: tag below)

[Answer]: C) Given Q1/Q2 direction (local-first, simpler initial model), C is a sensible default for v1, with D as a planned phase-2 hardening step.

## Question 5
For delegated tenant identity service tokens (opaque tenant user IDs), what trust model is required?

A) Trust per tenant via static allowlist of issuer keys

B) Trust via OIDC discovery and JWKS per tenant

C) Trust via signed assertion exchange (tenant service to platform identity)

D) Trust via mTLS + signed JWT

X) Other (please describe after [Answer]: tag below)

[Answer]: X)
Other detail:
- Phase 1: Use option A (static per-tenant issuer key allowlist) for local-first implementation simplicity.
- Phase 2 target: Evolve to option B (OIDC discovery + JWKS per tenant) as default production trust model for delegated tenant identity JWT validation.
- Optional future mode: Add option C for assertion-exchange workflows when strict brokered token exchange is required.
- High-security profile: Keep option D optional for environments that require mTLS in addition to signed JWT.

Rationale:
- Matches open-core local-first delivery while preserving a standards-based migration path.
- Reduces v1 operational complexity and still enables production-grade trust hardening in phased rollout.

## Question 6
How strict should namespace enforcement be for external tenant user identifiers?

A) Required canonical format: customer_id:opaque_external_user_id

B) Required canonical format: customer_id:external_tenant_id:external_user_id

C) Accept opaque external principal string; prefix only customer_id

D) Configurable per customer tenant using mapping rules

X) Other (please describe after [Answer]: tag below)

[Answer]: D) Rationale:
- Authorization remains tuple-authoritative (`platform_tenant_id`, `service_tenant_id`, `service_user_id`).
- Configurable mapping rules provide stable canonical principal keys for storage/audit/correlation without hardcoding one namespace scheme for all tenants.
- Supports local-first v1 while preserving flexibility for future direct-access and heterogeneous tenant identity formats.

## Question 7
What is the required claim set for platform-issued JWTs in v1?

A) Minimal: iss, sub, aud, exp, iat, jti, platform_tenant_id

B) A + service_tenant_id and user_id claims where applicable

C) B + principal_type, scopes, actor/source claims

D) C + session and correlation claims for tracing

X) Other (please describe after [Answer]: tag below)

[Answer]: X) Other detail:
- Mandatory base claims in v1:
	- `iss`, `sub`, `aud`, `exp`, `iat`, `jti`
	- `platform_tenant_id`
	- `principal_id`
	- `principal_type` (human or machine)
	- `roles` (for example admin/developer or machine role)
- Optional delegated context claims:
	- `service_tenant_id`, `service_user_id`
	- include only when asserted by trusted machine principals or validated delegated issuers.

Rationale:
- Identity service owns platform-tenant principals and role assignment.
- Service-tenant/service-user context may be carried for authorized delegated flows without implying ownership by identity service.
- Keeps token semantics aligned with current trust model and future direct-access migration paths.

## Question 8
Which gateways/proxies must validate these tokens in v1?

A) API gateway only

B) API gateway + connection gateway

C) API gateway + connection gateway + tenant-aware BYO proxy

D) All ingress and internal service-to-service hops

X) Other (please describe after [Answer]: tag below)

[Answer]: X) Other detail:
- Validation scope: all ingress to soorma-core service APIs.
- Current state:
	- No service-to-service API interaction yet (except event propagation).
	- Event flows are sanitized/enforced at Event Service boundary.
	- API Gateway, Connection Gateway, and tenant-aware BYO proxy are not implemented yet.
- Design requirement for v1:
	- Add SDK and shared common-library authentication support now so future ingress components can follow a consistent authentication design pattern.

Rationale:
- Enforces security at the real trust boundary that exists today (service API ingress).
- Avoids over-specifying non-existent infrastructure while ensuring forward-compatible auth primitives for planned gateways/proxies.

## Question 9
How should current header-based context coexist with JWT rollout?

A) JWT required immediately; remove header fallback

B) Dual-mode transition: validate JWT and derive current headers for existing services

C) Keep headers as source of truth; JWT optional until later release

D) Service-by-service migration with feature flags

X) Other (please describe after [Answer]: tag below)

[Answer]: X) Other detail:
- Implement incrementally in mergeable units of work:
	1. Introduce JWT authentication support in `soorma-service-common` while keeping current header-based context active.
	2. Update SDK clients/wrappers to send JWT-authenticated requests.
	3. Remove header-based auth support once JWT path is complete.
- This sequencing is for incremental development and mergeability to main, not for long-term migration compatibility constraints.

Rationale:
- Current auth/tenant context abstraction in `soorma-service-common` enables isolated auth-mechanism replacement.
- Allows small, reviewable PRs that deliver end-to-end progress without waiting for full cutover completion.

## Question 10
What operational and security controls are mandatory for v1?

A) Key rotation + revocation + audit logging

B) A + rate limiting + anomaly detection

C) B + tenant-level policy controls (token TTL/scopes)

D) C + break-glass and emergency key disable workflows

X) Other (please describe after [Answer]: tag below)

[Answer]: C) Rationale:
- Balances local-first incremental delivery with production-relevant security controls.
- Includes revocation/audit and baseline abuse controls (rate limiting, anomaly detection).
- Adds tenant-level token policy control (`TTL`, scopes) which is important for platform-of-platforms tenancy governance.
- Defers break-glass workflows (option D) to a later hardening phase after core identity flows are stable.

## Question 11
What delivery target should the specification optimize for?

A) Spec only (no code generation this cycle)

B) Spec + API contracts + data model + sequence diagrams

C) B + implementation-ready unit breakdown and phased rollout plan

D) C + initial scaffolding tasks for services and SDK wrappers

E) D + proceed into Construction phase for actual identity service implementation (code, tests, and build/test instructions)

X) Other (please describe after [Answer]: tag below)

[Answer]: E) Rationale:
- We want full scope delivery: complete specification artifacts plus actual identity service implementation in Construction.
- Includes code, tests, and build/test instructions rather than design-only outputs.

Clarification:
- Options A-D scope the depth of Inception deliverables.
- Option E explicitly includes moving forward into Construction to implement the service.

## Question 12
Question: JIRA Tickets Extension
Should JIRA ticket content be generated at the end of the Inception phase?

A) Yes - generate JIRA tickets at end of Inception (recommended for team-based projects using JIRA)

B) No - skip JIRA ticket generation (suitable for solo projects or non-JIRA workflows)

X) Other (please describe after [Answer]: tag below)

[Answer]: A)

## Question 13
Question: Team Collaboration Review Gates
Is this initiative a solo effort or a team-based project requiring PR checkpoints?

A) Enable team review gates - I am working with a team and we use PRs as collaboration checkpoints

B) Skip review gates - This is a solo project or my team does not use PR-based review checkpoints

X) Other (please describe after [Answer]: tag below)

[Answer]: A)

## Question 14
Question: QA Test Cases Extension
Should structured test case specifications be generated from units and functional requirements?

A) Yes - generate QA test case specs (A1 happy path, A2 happy path + basic negative, A3 comprehensive)

B) No - skip QA test case generation

X) Other (please describe after [Answer]: tag below)

[Answer]: A2)

## Question 15
Question: Security Extensions
Should security extension rules be enforced for this project?

A) Yes - enforce all SECURITY rules as blocking constraints (recommended for production-grade applications)

B) No - skip all SECURITY rules (suitable for PoCs, prototypes, and experimental projects)

X) Other (please describe after [Answer]: tag below)

[Answer]: A)