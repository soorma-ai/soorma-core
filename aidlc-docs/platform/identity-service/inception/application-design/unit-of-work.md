# Unit of Work

## Decomposition Decision
- **Approach**: Hybrid capability-first with explicit layer subphases.
- **Unit Count**: 4 units (balanced PR cadence).
- **Critical Path Principle**: Each unit is mergeable to main with predecessors completed and without requiring full-project completion.

## Unit 1 - Shared Auth Context Foundation
- **Unit Name**: uow-shared-auth-foundation
- **Purpose**: Establish JWT-capable shared dependency layer while preserving existing DI/router call sites.
- **Scope**:
  - Evolve shared auth context/dependency abstractions in common library.
  - Implement compatibility adapter behavior for coexistence.
  - Provide policy hooks for mandatory/optional claim validation.
- **Primary Artifacts/Targets**:
  - Shared dependency/middleware contracts.
  - Auth context normalization interfaces.
- **Why first**: Enables non-breaking downstream service and SDK updates.
- **Mergeability**: Can be merged independently with coexistence mode and tests.

## Unit 2 - Identity Service Core Domain
- **Unit Name**: uow-identity-core-domain
- **Purpose**: Implement core identity domain capabilities for tenant onboarding, principal lifecycle, token issuance, and delegated trust registration.
- **Scope**:
  - Tenant onboarding and principal lifecycle APIs.
  - Token issuance with mandatory claims.
  - Delegated issuer static-key trust model (v1) with extension points.
  - Claim context policy and mapping-rule support.
- **Primary Artifacts/Targets**:
  - Identity service components and methods.
  - Policy and trust components.
- **Dependencies**: Requires Unit 1 shared context foundation.
- **Mergeability**: Mergeable after Unit 1 with feature-complete core APIs and tests.

## Unit 3 - SDK and Wrapper JWT Integration
- **Unit Name**: uow-sdk-jwt-integration
- **Purpose**: Upgrade SDK wrappers/clients to use JWT-authenticated flows without changing handler call signatures.
- **Scope**:
  - Wrapper/client JWT request support.
  - Preserve two-layer SDK contracts and handler ergonomics.
  - Validate wrapper compatibility with identity core APIs.
- **Primary Artifacts/Targets**:
  - SDK wrapper/client integration updates.
  - Integration tests across SDK and service boundaries.
- **Dependencies**: Requires Unit 1 and Unit 2.
- **Mergeability**: Mergeable independently once integration tests pass.

## Unit 4 - Cutover, Hardening, and Legacy Header Removal
- **Unit Name**: uow-cutover-hardening
- **Purpose**: Complete FR-11 phase 3 cutover and operational hardening baseline.
- **Scope**:
  - Remove header-only auth path.
  - Enforce JWT-only ingress behavior.
  - Finalize security controls, telemetry completeness, and rollout verification.
- **Primary Artifacts/Targets**:
  - Cutover configuration and validation paths.
  - Build/test coverage for rollback and fail-closed behavior.
- **Dependencies**: Requires Unit 1, Unit 2, Unit 3.
- **Mergeability**: Final merge after full validation; still structured as one bounded unit.

## Unit Quality Rules
- Each unit includes embedded compatibility acceptance checks (FR-11).
- Each unit includes security and QA checks (per enabled extensions).
- Each unit produces reviewable PR-scope outputs with clear done criteria.
- No unit depends on unplanned hidden work outside predecessor chain.