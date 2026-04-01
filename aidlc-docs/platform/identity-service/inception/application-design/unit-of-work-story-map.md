# Unit of Work Story Map

## Mapping Table

| Story ID | Story Title | Persona(s) | Mapped Unit(s) | Notes |
|---|---|---|---|---|
| US-1.1 | Tenant Onboarding Bootstrap | Platform Administrator | uow-identity-core-domain | Core onboarding API and bootstrap flow |
| US-1.2 | Principal Lifecycle Management | Platform Administrator, Machine Principal Operator | uow-identity-core-domain | Principal CRUD/state and role enforcement |
| US-2.1 | Delegated Issuer Registration | Platform Administrator, Delegated Issuer Administrator | uow-identity-core-domain | v1 static allowlist + extension points |
| US-2.2 | External Principal Mapping Policy | Delegated Issuer Administrator | uow-identity-core-domain | Mapping-rule support and policy integration |
| US-3.1 | Platform Principal JWT Issuance | Platform Administrator, Platform Developer | uow-identity-core-domain, uow-shared-auth-foundation | Claim contract + shared auth context |
| US-3.2 | Delegated Context Claim Handling | Machine Principal Operator, Delegated Issuer Administrator | uow-identity-core-domain, uow-shared-auth-foundation | Delegated claim policy gating |
| US-4.1 | Shared Dependency JWT Coexistence | Platform Developer | uow-shared-auth-foundation | Primary story for coexistence layer |
| US-4.2 | SDK JWT Client Upgrade | Platform Developer | uow-sdk-jwt-integration | Wrapper/client JWT integration |
| US-4.3 | Header Auth Removal Cutover | Platform Developer, Platform Administrator | uow-cutover-hardening | Final phase cutover and hardening |

## Coverage Validation
- All stories mapped: Yes (9 of 9).
- Stories with multi-unit dependency: US-3.1, US-3.2.
- FR-11 compatibility represented:
  - Dedicated compatibility unit: uow-shared-auth-foundation.
  - Embedded criteria across dependent units: uow-identity-core-domain, uow-sdk-jwt-integration, uow-cutover-hardening.

## QA and Security Alignment
- QA/security checks are attached to each functional unit, not deferred to a single terminal unit.
- Security baseline obligations and test-case scope (`happy-path-negative`) are carried forward per unit.

## Implementation Order Summary
1. uow-shared-auth-foundation
2. uow-identity-core-domain
3. uow-sdk-jwt-integration
4. uow-cutover-hardening