# Test Case Index: authority-evaluation

Unit abbreviation: AE = authority-evaluation

Canonical source: [test-specs-narrative.md](test-specs-narrative.md). 22 test cases, comprehensive scope.

| Test Case ID | Title | Source | Scope | Priority |
|---|---|---|---|---|
| TC-AE-001 | A valid draft is stamped with all six platform fields | authority-evaluation / M1-FR-01 | happy-path | High |
| TC-AE-002 | Autonomous origin is stamped for a declaring agent with no inbound context | authority-evaluation / M1-FR-08 | happy-path | High |
| TC-AE-003 | Origin propagates unchanged from an inbound envelope, and the chain grows | authority-evaluation / M1-FR-08, M1-FR-01 | happy-path | High |
| TC-AE-004 | Authority is allowed when every term holds the permission | authority-evaluation / M1-FR-08 | happy-path | High |
| TC-AE-005 | Load-bearing re-broadening allows, and is recorded at the declaring hop | authority-evaluation / M1-FR-08, M1-FR-01 | happy-path | High |
| TC-AE-006 | The policy-decision boundary answers containment only | authority-evaluation / M1-FR-13 | happy-path | Medium |
| TC-AE-007 | A well-formed trace context is accepted and carried as asserted | authority-evaluation / M1-FR-01 | happy-path | Medium |
| TC-AE-008 | Unknown fields are preserved, and unknown enumerated values are non-fatal | authority-evaluation / M1-FR-01 | happy-path | Medium |
| TC-AE-009 | A draft setting any platform-stamped field is rejected | authority-evaluation / M1-FR-01 | negative | High |
| TC-AE-010 | A draft asserting origin `autonomous` is rejected | authority-evaluation / M1-FR-01 (GAP-INT-007) | negative | High |
| TC-AE-011 | With no inbound context and no declared autonomy, the agent is denied | authority-evaluation / M1-FR-08 | negative | High |
| TC-AE-012 | A malformed trace context is rejected | authority-evaluation / M1-FR-01 | negative | Medium |
| TC-AE-013 | A draft without a client contract version is rejected | authority-evaluation / M1-FR-01 | negative | Medium |
| TC-AE-014 | An agent-set re-broadening record is rejected | authority-evaluation / M1-FR-08 | negative | High |
| TC-AE-015 | Without re-broadening, an upstream gap denies | authority-evaluation / M1-FR-08 | negative | High |
| TC-AE-016 | Re-broadening never recovers what the delegating principal lacked | authority-evaluation / M1-FR-08 | edge-boundary | High |
| TC-AE-017 | The chain at maxChainDepth is accepted; one more hop is rejected | authority-evaluation / M1-FR-01 | edge-boundary | High |
| TC-AE-018 | Re-broadening is local to its hop | authority-evaluation / M1-FR-08 | edge-boundary | High |
| TC-AE-019 | Non-load-bearing re-broadening is not recorded | authority-evaluation / M1-FR-01, M1-FR-08 | edge-boundary | Medium |
| TC-AE-020 | A permission outside the standing set is always denied | authority-evaluation / M1-FR-08 | edge-boundary | High |
| TC-AE-021 | Evaluation is deny-by-default for an empty or unknown set | authority-evaluation / M1-FR-08 | edge-boundary | Medium |
| TC-AE-022 | Evaluation matches every row of the re-broadening case table | authority-evaluation / M1-FR-08 | edge-boundary | High |
