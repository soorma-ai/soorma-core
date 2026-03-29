Feature: Unit-3 schema index migration and isolation validation

@happy-path @TC-U3-001
Scenario: Apply working memory unique-constraint migration successfully
  # Source: unit-3 / FR-8
  # Construction: aidlc-docs/platform/memory-identity-scope/construction/unit-3/
  Given the database is at the pre-migration revision
  When the migration upgrade is executed
  Then the working_memory unique constraint includes full scoped identity columns

@negative @TC-U3-002
Scenario: Prevent cross-identity write collisions post-migration
  # Source: unit-3 / FR-11
  # Construction: aidlc-docs/platform/memory-identity-scope/construction/unit-3/
  Given an existing row owned by identity A
  When identity B writes the same logical key
  Then no overwrite of identity A data occurs

@negative @TC-U3-003
Scenario: Validate semantic index alignment with conflict targets
  # Source: unit-3 / FR-9
  # Construction: aidlc-docs/platform/memory-identity-scope/construction/unit-3/
  Given semantic indexes and conflict targets are configured
  When private and public upserts are executed for duplicate keys
  Then behavior aligns with corresponding partial unique indexes

@negative @TC-U3-004
Scenario: Verify migration downgrade restores prior constraints deterministically
  # Source: unit-3 / NFR-3
  # Construction: aidlc-docs/platform/memory-identity-scope/construction/unit-3/
  Given the schema is at upgraded revision
  When downgrade then upgrade are executed
  Then constraints transition deterministically and reversibly
