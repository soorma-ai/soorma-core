# Application Design Plan

## Objective
Design high-level application components, component methods, service orchestration, and dependencies for the identity-service initiative before units decomposition and construction.

## Execution Checklist
- [x] Step 1 - Confirm component boundary strategy
- [x] Step 2 - Confirm service orchestration approach
- [x] Step 3 - Finalize method signature conventions
- [x] Step 4 - Generate components.md
- [x] Step 5 - Generate component-methods.md
- [x] Step 6 - Generate services.md
- [x] Step 7 - Generate component-dependency.md
- [x] Step 8 - Generate consolidated application-design.md
- [x] Step 9 - Validate cross-artifact consistency and completeness

## Mandatory Artifacts
- [x] Generate components.md with component definitions and high-level responsibilities
- [x] Generate component-methods.md with method signatures
- [x] Generate services.md with service definitions and orchestration patterns
- [x] Generate component-dependency.md with dependency relationships and communication patterns
- [x] Validate design completeness and consistency

## Context-Specific Questions (fill all [Answer] tags)

## Question 1
What should be the primary component partitioning strategy?

A) Layer-based (`api`, `service`, `repository`, `provider`, `policy`)

B) Capability-based (`tenant-onboarding`, `principal-management`, `token-issuance`, `delegated-trust`, `audit`)

C) Hybrid capability + shared cross-cutting modules (recommended)

X) Other (please describe after [Answer]: tag below)

[Answer]: c)

## Question 2
How should provider abstraction be placed in component design?

A) Single provider interface for entire identity domain

B) Separate interfaces per capability (`principal_provider`, `token_provider`, `issuer_trust_provider`)

C) Hybrid: domain-level provider facade with capability-specific internal adapters (recommended)

X) Other (please describe after [Answer]: tag below)

[Answer]: c)

## Question 3
For FR-11 phased rollout, where should compatibility logic live?

A) Inside route handlers (explicit branch logic per endpoint)

B) Inside shared dependencies/middleware only (recommended)

C) Mixed between handlers and dependencies

X) Other (please describe after [Answer]: tag below)

[Answer]: b)

## Question 4
What should be the default interaction style between components/services?

A) Synchronous service-call orchestration only

B) Event-assisted orchestration for audit/async side effects + synchronous core paths (recommended)

C) Event-first orchestration for all identity operations

X) Other (please describe after [Answer]: tag below)

[Answer]: b) keep core path synchronous and publish events for audit etc.

## Question 5
How should delegated trust validation components be scoped in v1?

A) Minimal static-key allowlist validator only

B) Static-key validator + OIDC/JWKS-ready extension points (recommended)

C) Full OIDC/JWKS implementation now

X) Other (please describe after [Answer]: tag below)

[Answer]: b)

## Question 6
How should component methods express claim/context contracts?

A) Keep existing tuple/header contracts and defer JWT-centric signatures

B) JWT-centric method contracts with adapter layer translating during coexistence (recommended)

C) Dual signatures on each method for both modes

X) Other (please describe after [Answer]: tag below)

[Answer]: b)

## Approval
After filling all answers, confirm in chat:
"application design plan approved"

Then Application Design artifact generation will start.