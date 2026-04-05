# Functional Design Plan - uow-identity-core-domain

## Unit Context
- Unit: uow-identity-core-domain
- Purpose: Implement identity core domain capabilities for onboarding, principals, token issuance, delegated trust, and external identity mapping.
- Unit dependency: uow-shared-auth-foundation completed.
- Story coverage: US-1.1, US-1.2, US-2.1, US-2.2, and identity-core portion of US-3.1 and US-3.2.

## Architecture Pattern Alignment
- Section 1 (Authentication model): preserve platform-tenant and service-tenant/user context boundaries.
- Section 2 (Two-layer SDK): expose service capabilities through wrapper-consumable service contracts; no direct service-client leakage to handlers.
- Section 3 (Event choreography): keep explicit response/event contracts where async coordination is used.
- Section 4 (Multi-tenancy/RLS): enforce tenant isolation and identity ownership boundaries.
- Section 6 (Error handling): fail-closed auth/trust outcomes with safe error envelopes.
- Section 7 (Testing): unit + integration coverage for identity and trust critical paths.

## Execution Checklist
- [x] Step 1 - Analyze unit scope, stories, and predecessor outputs.
- [x] Step 2 - Create functional design planning checklist for this unit.
- [x] Step 3 - Generate clarifying questions for business logic/domain rules.
- [x] Step 4 - Store this planning artifact.
- [x] Step 5 - Validate all answers and resolve ambiguities.
- [x] Step 6 - Generate functional design artifacts.
- [x] Step 7 - Present functional design completion review gate.

## Functional Design Clarifying Questions
Please answer each question by filling in the [Answer]: line.

## Question 1
What is the canonical onboarding transaction boundary for v1 identity core?

A) Single transaction: tenant domain + bootstrap admin + optional machine principals all-or-nothing

B) Two-step: tenant domain first, then principal bootstrap as separate transaction

C) Saga-style orchestrated steps with compensations for partial failures

X) Other (please describe after [Answer]: tag below)

[Answer]: X) Other detail:
- Atomic onboarding boundary: create platform-tenant identity domain plus one bootstrap admin principal in a single transaction.
- Optional machine principal bootstrap remains optional and disabled by default for v1.
- Onboarding authority must be trusted (operator/admin control-plane path, or controlled self-service using signed one-time onboarding claim/invite token).
- After onboarding completes, additional human and machine principals are created through authenticated tenant-admin principal lifecycle APIs.
- Do not bootstrap all tenants/principals during soorma-core startup or deployment; onboarding is a runtime operation.

Rationale:
- Preserves strong initial consistency for tenant boundary and first admin (FR-1, FR-4).
- Minimizes blast radius and avoids deployment-time coupling to customer-specific principal inventories.
- Enforces least-privilege and explicit trust for tenant creation while enabling self-service tenant operations post-bootstrap.
- Aligns with incremental unit delivery and fail-closed security posture.

## Question 2
How should role assignment constraints be enforced for principal lifecycle operations?

A) Static allowlist in code (`admin`, `developer`, `planner`, `worker`, `tool`) with strict rejection

B) Tenant-configurable role catalog with baseline reserved roles

C) Hybrid: static baseline + optional tenant-defined extension roles under prefix/namespace policy

X) Other (please describe after [Answer]: tag below)

[Answer]: C)

Rationale:
- soorma-core authorization remains anchored to platform baseline roles (`admin`, `developer`, `planner`, `worker`, `tool`) for core service access control.
- tenant-defined extension roles are allowed as namespaced roles/claims for delegated flows and tenant-owned services/agents, not as implicit platform authorization grants.
- extension roles must never auto-map to privileged platform roles; any mapping requires explicit route-scoped policy and deny-by-default behavior.
- this preserves stable core semantics while enabling tenant-specific access-control models without forcing frequent platform role-set changes.

## Question 3
For delegated issuer registration (v1 static allowlist), what minimum issuer identity fields are mandatory?

A) issuer_id + display_name only

B) issuer_id + jwk_set (or signing key material) + status + created_by

C) B + audience policy + claim mapping policy reference

X) Other (please describe after [Answer]: tag below)

[Answer]: C)

Rationale:
- v1 delegated trust should include verification metadata (keys + issuer status) and policy boundaries (audience + claim mapping reference) to avoid over-trusting external assertions.
- day-1 tenant operation is not blocked: platform principals and baseline soorma-core token issuance remain available out-of-box without tenant-side custom build/setup.
- delegated issuer flows are opt-in; audience/mapping policy can use platform-managed safe defaults until tenant-specific customization is needed.
- this keeps onboarding friction low while preserving least-privilege controls for delegated JWT activation.

## Question 4
How should token issuance authorization be scoped in this unit before SDK JWT integration is complete?

A) Identity service internal/admin paths only (no external caller token grant yet)

B) Platform principal token issuance allowed for existing trusted call paths; delegated issuance gated by registered issuer policy

C) Full issuance matrix active now (platform user, machine, delegated service identities)

X) Other (please describe after [Answer]: tag below)

[Answer]: B)

Rationale:
- aligns with FR-11 incremental rollout: issue platform-principal tokens on existing trusted call paths while SDK JWT request support is still being completed.
- preserves day-1 out-of-box operability for core platform usage without requiring full delegated integration upfront.
- delegated issuance remains available only under registered-issuer and policy-gated controls (audience + claim mapping), reducing over-issuance risk.
- defers full issuance matrix activation until later units complete SDK integration and hardening/cutover controls.

## Question 5
What should be the rule for external principal mapping policy collision handling?

A) Reject on collision always (strict uniqueness)

B) Last-writer-wins update semantics with audit trail

C) Configurable per tenant: reject by default, optional deterministic merge strategy

X) Other (please describe after [Answer]: tag below)

[Answer]: C)

Rationale:
- default policy is strict reject-on-collision to protect canonical identity integrity.
- tenant may opt into deterministic merge mode for delegated/machine contexts, but human principal remaps remain reject-only by default.
- deterministic precedence is explicit: trusted active issuer and verified existing binding take priority; silent canonical remap is never allowed.
- any remap path requires explicit admin override workflow with structured audit trail (old/new mapping, rule applied, actor, correlation id).
- this preserves secure defaults while allowing controlled tenant-specific flexibility where needed.

Deterministic merge policy template (recorded baseline):
- mode default: reject_on_collision.
- optional mode: deterministic_merge (tenant opt-in).
- scope guard: collisions must resolve within the same platform_tenant_id only; cross-tenant collision always rejects.
- principal guard: human principal mappings are immutable after first verified bind; delegated or machine mappings may use deterministic merge when enabled.
- precedence order:
	1. active trusted issuer over inactive or untrusted issuer.
	2. existing verified binding over new unverified binding.
	3. if both are verified, keep earliest canonical binding and reject automatic remap.
- remap safety: canonical principal remap requires explicit admin override operation; no silent background remap.
- audit requirement: emit collision_resolution event with prior mapping, proposed mapping, applied rule, actor, correlation id, and timestamp.

Reference glossary and delegated-collision scenarios (for later design/code stages):
- identity mapping: policy-driven normalization from external delegated claims to an internal canonical identity key.
- binding: persisted association between an external asserted identity key and a canonical principal record.
- canonical identity key: stable internal identity representation used by soorma-core for authorization and audit continuity.
- collision: conflict where a new mapping assertion would overwrite or ambiguously compete with an existing binding.

Delegated flow context:
- platform tenant can register one or more delegated issuers.
- delegated issuer provides signed JWT assertions containing delegated identity context.
- soorma-core validates issuer trust and signature, then applies mapping and binding rules.

Collision examples:
- same external key remap attempt: existing external key already bound to principal A; new assertion attempts to bind same key to principal B.
- competing issuer assertions: issuer-1 and issuer-2 produce claims that resolve to the same canonical key but with conflicting principal linkage.
- weak-namespace overlap: delegated identities from different issuers collide when issuer scope is not included in mapping policy.

Expected handling summary:
- reject by default.
- allow deterministic merge only for explicitly enabled delegated or machine contexts.
- require explicit admin override for canonical remap operations.
- always emit structured collision audit events for traceability.

## Question 6
What error contract should identity core APIs use for trust and lifecycle failures?

A) Domain-specific typed error codes + HTTP mapping (recommended)

B) Generic HTTP errors only

C) Generic HTTP errors plus free-form message fields

X) Other (please describe after [Answer]: tag below)

[Answer]: A)

## Question 7
How should write-side audit requirements be enforced for identity mutations?

A) Best effort async logging (operation succeeds even if audit write fails)

B) Fail-closed for critical mutations (issuer trust changes, key rotation, principal revocation), best effort for low-risk updates

C) Strict fail-closed for all mutation endpoints

X) Other (please describe after [Answer]: tag below)

[Answer]: B)

## Question 8
For persistence modeling, what boundary should this functional design target?

A) Pure domain model only (no repository-level concerns in this stage)

B) Domain model + repository contract definitions (without infrastructure specifics)

C) Full schema-level design details in functional design artifacts

X) Other (please describe after [Answer]: tag below)

[Answer]: B)

## Question 9
What testing contract should functional design lock for this unit?

A) Unit tests only for domain services and validators

B) Unit tests + API integration tests for onboarding, principal lifecycle, token issuance, and delegated trust checks

C) B + negative security regression matrix for unauthorized issuance, issuer mismatch, and mapping-collision paths

X) Other (please describe after [Answer]: tag below)

[Answer]: C)

## Question 10
Should this unit include async event emission for identity domain changes now, or defer to later units?

A) Defer all event emission to later units

B) Emit minimal critical events now (tenant onboarded, principal revoked, issuer changed)

C) Emit full event catalog now for all identity mutations

X) Other (please describe after [Answer]: tag below)

[Answer]: C)

## Approval
After completing all answers, reply in chat with:
"functional design plan answers provided"
