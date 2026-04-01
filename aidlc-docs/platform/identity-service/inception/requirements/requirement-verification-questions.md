# Requirements Verification Questions

Please answer all questions by filling the [Answer]: line for each question.

## Question 1
What should be the primary scope boundary for the new Identity Service in soorma-core?

A) Tier 1 only: Developer tenant onboarding and platform-level identity admin

B) Tier 2 only: End-user and application tenant token issuance

C) Both tiers in one service with explicit domain separation

D) Keep current flows; document only, no new service implementation now

X) Other (please describe after [Answer]: tag below)

[Answer]: 

## Question 2
How should Google Customer Identity Platform (GCIP) be used?

A) GCIP as source of truth for tenant/user identities; soorma Identity Service as admin and token broker

B) GCIP only for authentication; soorma stores canonical identity records and issues all tokens

C) Hybrid by principal type: users in GCIP, machine identities in soorma

D) Start with local stub provider and defer GCIP integration

X) Other (please describe after [Answer]: tag below)

[Answer]: 

## Question 3
For tenant onboarding, which minimum capabilities are required in v1?

A) Create platform customer tenant and bootstrap admin user

B) A + machine principal bootstrap for BYO agents/tools

C) B + API key lifecycle (create, rotate, revoke)

D) C + delegated external identity-provider registration per tenant

X) Other (please describe after [Answer]: tag below)

[Answer]: 

## Question 4
Which token types are in v1 scope?

A) Human-user access JWT only

B) Human-user JWT + machine JWT

C) Human-user JWT + machine JWT + delegated token for tenant identity service

D) All above + refresh tokens and token introspection endpoint

X) Other (please describe after [Answer]: tag below)

[Answer]: 

## Question 5
For delegated tenant identity service tokens (opaque tenant user IDs), what trust model is required?

A) Trust per tenant via static allowlist of issuer keys

B) Trust via OIDC discovery and JWKS per tenant

C) Trust via signed assertion exchange (tenant service to platform identity)

D) Trust via mTLS + signed JWT

X) Other (please describe after [Answer]: tag below)

[Answer]: 

## Question 6
How strict should namespace enforcement be for external tenant user identifiers?

A) Required canonical format: customer_id:opaque_external_user_id

B) Required canonical format: customer_id:external_tenant_id:external_user_id

C) Accept opaque external principal string; prefix only customer_id

D) Configurable per customer tenant using mapping rules

X) Other (please describe after [Answer]: tag below)

[Answer]: 

## Question 7
What is the required claim set for platform-issued JWTs in v1?

A) Minimal: iss, sub, aud, exp, iat, jti, platform_tenant_id

B) A + service_tenant_id and user_id claims where applicable

C) B + principal_type, scopes, actor/source claims

D) C + session and correlation claims for tracing

X) Other (please describe after [Answer]: tag below)

[Answer]: 

## Question 8
Which gateways/proxies must validate these tokens in v1?

A) API gateway only

B) API gateway + connection gateway

C) API gateway + connection gateway + tenant-aware BYO proxy

D) All ingress and internal service-to-service hops

X) Other (please describe after [Answer]: tag below)

[Answer]: 

## Question 9
How should current header-based context coexist with JWT rollout?

A) JWT required immediately; remove header fallback

B) Dual-mode transition: validate JWT and derive current headers for existing services

C) Keep headers as source of truth; JWT optional until later release

D) Service-by-service migration with feature flags

X) Other (please describe after [Answer]: tag below)

[Answer]: 

## Question 10
What operational and security controls are mandatory for v1?

A) Key rotation + revocation + audit logging

B) A + rate limiting + anomaly detection

C) B + tenant-level policy controls (token TTL/scopes)

D) C + break-glass and emergency key disable workflows

X) Other (please describe after [Answer]: tag below)

[Answer]: 

## Question 11
What delivery target should the specification optimize for?

A) Spec only (no code generation this cycle)

B) Spec + API contracts + data model + sequence diagrams

C) B + implementation-ready unit breakdown and phased rollout plan

D) C + initial scaffolding tasks for services and SDK wrappers

X) Other (please describe after [Answer]: tag below)

[Answer]: 

## Question 12
Question: JIRA Tickets Extension
Should JIRA ticket content be generated at the end of the Inception phase?

A) Yes - generate JIRA tickets at end of Inception (recommended for team-based projects using JIRA)

B) No - skip JIRA ticket generation (suitable for solo projects or non-JIRA workflows)

X) Other (please describe after [Answer]: tag below)

[Answer]: 

## Question 13
Question: Team Collaboration Review Gates
Is this initiative a solo effort or a team-based project requiring PR checkpoints?

A) Enable team review gates - I am working with a team and we use PRs as collaboration checkpoints

B) Skip review gates - This is a solo project or my team does not use PR-based review checkpoints

X) Other (please describe after [Answer]: tag below)

[Answer]: 

## Question 14
Question: QA Test Cases Extension
Should structured test case specifications be generated from units and functional requirements?

A) Yes - generate QA test case specs (A1 happy path, A2 happy path + basic negative, A3 comprehensive)

B) No - skip QA test case generation

X) Other (please describe after [Answer]: tag below)

[Answer]: 

## Question 15
Question: Security Extensions
Should security extension rules be enforced for this project?

A) Yes - enforce all SECURITY rules as blocking constraints (recommended for production-grade applications)

B) No - skip all SECURITY rules (suitable for PoCs, prototypes, and experimental projects)

X) Other (please describe after [Answer]: tag below)

[Answer]: 