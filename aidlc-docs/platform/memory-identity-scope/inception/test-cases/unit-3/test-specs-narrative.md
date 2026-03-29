# Unit Test Specs Narrative - unit-3

Unit abbreviation: U3 = unit-3
Scope profile: happy-path-negative

### TC-U3-001 - Apply working memory unique-constraint migration successfully
Context: Verifies FR-8 and NFR-3 upgrade path for working-memory scoped uniqueness.
Scenario: Migration upgrade is executed for working_memory constraint alignment.
Preconditions:
1. Database is at pre-migration revision.
2. Existing schema uses old constraint.
Steps:
1. Execute Alembic upgrade to target revision.
2. Inspect resulting working_memory constraints.
Expected outcome: New unique constraint includes platform_tenant_id + service_tenant_id + service_user_id + plan_id + key.
Scope: happy-path
Priority: High
Source: unit-3 / FR-8
Construction artifacts: aidlc-docs/platform/memory-identity-scope/construction/unit-3/
Technical references:
- aidlc-docs/platform/memory-identity-scope/inception/requirements/requirements.md
- aidlc-docs/platform/memory-identity-scope/inception/application-design/unit-of-work.md

### TC-U3-002 - Prevent cross-identity write collisions post-migration
Context: Confirms acceptance criteria for collision prevention after schema/index alignment.
Scenario: Two distinct identities write same logical key values.
Preconditions:
1. Migrated schema active.
2. Identity A row exists.
Steps:
1. Write same logical key as identity B.
2. Validate resulting rows and ownership boundaries.
Expected outcome: No cross-identity overwrite; records remain isolated by scoped unique keys.
Scope: negative
Priority: High
Source: unit-3 / FR-11
Construction artifacts: aidlc-docs/platform/memory-identity-scope/construction/unit-3/
Technical references:
- aidlc-docs/platform/memory-identity-scope/inception/requirements/requirements.md

### TC-U3-003 - Validate semantic index alignment with conflict targets
Context: Verifies FR-9 schema/index parity with runtime upsert conflict targets.
Scenario: Semantic upsert executes in both public and private modes.
Preconditions:
1. Semantic indexes migrated/available.
2. Upsert conflict targets are configured.
Steps:
1. Perform private upsert with existing external_id/content_hash.
2. Perform public upsert with existing external_id/content_hash.
3. Validate behavior against scoped uniqueness rules.
Expected outcome: Upsert behavior matches corresponding partial unique indexes; no mismatch errors.
Scope: negative
Priority: High
Source: unit-3 / FR-9
Construction artifacts: aidlc-docs/platform/memory-identity-scope/construction/unit-3/
Technical references:
- aidlc-docs/platform/memory-identity-scope/inception/requirements/requirements.md

### TC-U3-004 - Verify migration downgrade restores prior constraints deterministically
Context: Verifies NFR-3 rollback safety and deterministic schema transitions.
Scenario: Migration downgrade is run after successful upgrade.
Preconditions:
1. Database at post-upgrade revision.
Steps:
1. Execute Alembic downgrade one revision.
2. Inspect restored constraints.
3. Re-run upgrade to confirm deterministic transitions.
Expected outcome: Prior constraint is restored as expected; downgrade/upgrade paths are reversible and stable.
Scope: negative
Priority: Medium
Source: unit-3 / NFR-3
Construction artifacts: aidlc-docs/platform/memory-identity-scope/construction/unit-3/
Technical references:
- aidlc-docs/platform/memory-identity-scope/inception/requirements/requirements.md
