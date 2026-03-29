# Unit Test Specs Narrative - unit-2

Unit abbreviation: U2 = unit-2
Scope profile: happy-path-negative

### TC-U2-001 - Enforce require_user_context on user-scoped routers
Context: Verifies FR-3 adoption so user-scoped memory routes enforce shared dependency consistently.
Scenario: Request without required user identity reaches a user-scoped memory router.
Preconditions:
1. Router is user-scoped.
2. Dependency `require_user_context` is attached.
Steps:
1. Send request with missing service tenant or user.
2. Observe router response.
Expected outcome: Router fails fast with HTTP 400 and does not execute handler logic.
Scope: happy-path
Priority: High
Source: unit-2 / FR-3
Construction artifacts: aidlc-docs/platform/memory-identity-scope/construction/unit-2/
Technical references:
- aidlc-docs/platform/memory-identity-scope/inception/requirements/requirements.md
- aidlc-docs/platform/memory-identity-scope/inception/application-design/unit-of-work.md

### TC-U2-002 - Keep admin endpoints exempt from user-context dependency
Context: Validates NFR-2 and FR-3 carveout for admin/system-scoped endpoints.
Scenario: Admin endpoint is called without service user identity.
Preconditions:
1. Endpoint is under admin router.
2. Admin router does not include require_user_context.
Steps:
1. Invoke admin endpoint without service_user_id.
2. Observe behavior.
Expected outcome: No 400 caused by require_user_context; admin behavior remains intentionally tenant/system scoped.
Scope: negative
Priority: High
Source: unit-2 / NFR-2
Construction artifacts: aidlc-docs/platform/memory-identity-scope/construction/unit-2/
Technical references:
- aidlc-docs/platform/memory-identity-scope/inception/requirements/requirements.md

### TC-U2-003 - Enforce full identity tuple in plans and sessions CRUD
Context: Verifies FR-4 and FR-5 query predicate alignment in runtime path.
Scenario: Two users in same platform tenant access same resource ID namespace.
Preconditions:
1. Data exists for user A.
2. User B has different service_user_id and/or service_tenant_id.
Steps:
1. Execute list/get/update/delete via user B for user A records.
2. Observe query results.
Expected outcome: User B cannot read or mutate user A records; predicates enforce platform_tenant_id + service_tenant_id + service_user_id.
Scope: negative
Priority: High
Source: unit-2 / FR-4
Construction artifacts: aidlc-docs/platform/memory-identity-scope/construction/unit-2/
Technical references:
- aidlc-docs/platform/memory-identity-scope/inception/requirements/requirements.md

### TC-U2-004 - Align upsert conflict targets to scoped identity
Context: Validates FR-6, FR-7, and FR-9 runtime conflict target behavior for context/semantic paths.
Scenario: Two identities attempt upserts for same task/plan semantic keys.
Preconditions:
1. Existing record for identity A.
2. Identity B uses same task/plan key values.
Steps:
1. Perform upsert as identity B.
2. Verify resulting row behavior.
Expected outcome: No cross-identity overwrite; conflict targets include scoped identity dimensions.
Scope: negative
Priority: High
Source: unit-2 / FR-6
Construction artifacts: aidlc-docs/platform/memory-identity-scope/construction/unit-2/
Technical references:
- aidlc-docs/platform/memory-identity-scope/inception/requirements/requirements.md
