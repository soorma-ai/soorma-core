# Test Case Index: agent-credentials

Unit abbreviation: AC = agent-credentials

Canonical source: [test-specs-narrative.md](test-specs-narrative.md). 22 test cases, comprehensive scope.

| Test Case ID | Title | Source | Scope | Priority |
|---|---|---|---|---|
| TC-AC-001 | Bootstrap returns a short-lived credential bound to the registration and E | agent-credentials / M1-FR-05 | happy-path | High |
| TC-AC-002 | The instance identifier is recorded, not verified | agent-credentials / M1-FR-05 | happy-path | Medium |
| TC-AC-003 | A valid credential is renewed | agent-credentials / M1-FR-06 | happy-path | High |
| TC-AC-004 | Bootstrap and renewal carry no envelope | agent-credentials / M1-FR-05, M1-FR-06 (GAP-INT-008) | happy-path | Medium |
| TC-AC-005 | Bootstrap and renewal are attributed | agent-credentials / M1-FR-12 | happy-path | Medium |
| TC-AC-006 | An unrevoked credential passes the revocation read | agent-credentials / M1-FR-07 | happy-path | High |
| TC-AC-007 | A wrong secret is refused, and the failure recorded against the registration | agent-credentials / M1-FR-05 | negative | High |
| TC-AC-008 | Bootstrap attempts beyond the bound are refused | agent-credentials / M1-FR-05 | negative | High |
| TC-AC-009 | A revoked credential is refused at renewal | agent-credentials / M1-FR-07, M1-FR-06 | negative | High |
| TC-AC-010 | Unconfirmable revocation state fails closed | agent-credentials / M1-FR-07 | negative | High |
| TC-AC-011 | An expired credential cannot be renewed; the instance re-bootstraps | agent-credentials / M1-FR-06 | negative | High |
| TC-AC-012 | A human credential is refused by kind | agent-credentials / M1-FR-09 | negative | High |
| TC-AC-013 | A credential from E2 is refused at E's data gateway | agent-credentials / M1-FR-10, M1-FR-09 | negative | High |
| TC-AC-014 | Bootstrap for an unknown registration is refused | agent-credentials / M1-FR-05 | negative | Medium |
| TC-AC-015 | A change of revocation state takes effect within the bound | agent-credentials / M1-FR-07 | edge-boundary | High |
| TC-AC-016 | Renewal is never a weaker check than issuance | agent-credentials / M1-FR-06 | edge-boundary | High |
| TC-AC-017 | Bootstrap and renewal keep working while the organization level is down | agent-credentials / M1-FR-05, M1-FR-06 (M1-NFR-08) | edge-boundary | High |
| TC-AC-018 | No edge operation exposes revocation state | agent-credentials / M1-FR-07 | edge-boundary | High |
| TC-AC-019 | The internal revocation read writes no attribution record | agent-credentials / M1-FR-12 (GAP-INT-009) | edge-boundary | Medium |
| TC-AC-020 | E's credentials are verified only with E's own material | agent-credentials / M1-FR-10 | edge-boundary | High |
| TC-AC-021 | This unit's operations are defined in the contract and validated against it | agent-credentials / M1-FR-02 | happy-path | High |
| TC-AC-022 | Bootstrap material of an unsupported type is rejected | agent-credentials / M1-FR-13 | negative | Medium |
