# Test Case Index: wire-contract

Unit abbreviation: WC = wire-contract

Canonical source: [test-specs-narrative.md](test-specs-narrative.md). 11 test cases, comprehensive scope.

| Test Case ID | Title | Source | Scope | Priority |
|---|---|---|---|---|
| TC-WC-001 | A well-formed envelope validates against the envelope schema | wire-contract / M1-FR-02 | happy-path | High |
| TC-WC-002 | A Delivery validates against the Delivery schema | wire-contract / M1-FR-02 | happy-path | High |
| TC-WC-003 | Types are generated from the schema, never hand-written | wire-contract / M1-FR-02 | happy-path | High |
| TC-WC-004 | The contract declares its pre-release status | wire-contract / M1-FR-02 | happy-path | High |
| TC-WC-005 | The contract states that bootstrap and renewal carry no envelope | wire-contract / M1-FR-02 (GAP-INT-008, U1's inherited gaps) | happy-path | Medium |
| TC-WC-006 | An envelope missing a required field fails validation | wire-contract / M1-FR-02 | negative | High |
| TC-WC-007 | The draft schema does not admit platform-stamped fields | wire-contract / M1-FR-02 | negative | High |
| TC-WC-008 | Unknown fields are permitted by the envelope schema | wire-contract / M1-FR-02 | edge-boundary | Medium |
| TC-WC-009 | Every surface document references the one envelope definition | wire-contract / M1-FR-02 | edge-boundary | Medium |
| TC-WC-010 | The client contract version is distinct from the envelope version | wire-contract / M1-FR-02 | edge-boundary | Medium |
| TC-WC-011 | Contract files carry the Apache 2.0 licence | wire-contract / M1-FR-02 | edge-boundary | Medium |
