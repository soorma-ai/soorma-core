# Test Case Index: env-human-access

Unit abbreviation: EHA = env-human-access

Canonical source: [test-specs-narrative.md](test-specs-narrative.md). 24 test cases, comprehensive scope.

| Test Case ID | Title | Source | Scope | Priority |
|---|---|---|---|---|
| TC-EHA-001 | Configuration grants the first Admin `grant:human` and `human:manage` in E | env-human-access / M1-FR-14, M1-FR-12 | happy-path | High |
| TC-EHA-002 | An environment credential is issued from a live sign-in | env-human-access / M1-FR-20 | happy-path | High |
| TC-EHA-003 | H renews their environment credential | env-human-access / M1-FR-20 | happy-path | Medium |
| TC-EHA-004 | H ends their own environment credential | env-human-access / M1-FR-21 | happy-path | High |
| TC-EHA-005 | H self-grants Developer permissions, recorded as self-grants | env-human-access / M1-FR-15, M1-FR-12 | happy-path | High |
| TC-EHA-006 | A grant to another human succeeds | env-human-access / M1-FR-15 | happy-path | Medium |
| TC-EHA-007 | Granting does not require holding the permission | env-human-access / M1-FR-15 | happy-path | High |
| TC-EHA-008 | Human-only permissions can be granted to a human | env-human-access / M1-FR-15 | edge-boundary | Medium |
| TC-EHA-009 | The organization sign-in is refused everywhere in E except issuance | env-human-access / M1-FR-09, M1-FR-19 | negative | High |
| TC-EHA-010 | E's credential is refused in E2 | env-human-access / M1-FR-20, M1-FR-10 | negative | High |
| TC-EHA-011 | A principal holding no grant in E gets no credential | env-human-access / M1-FR-20 | negative | High |
| TC-EHA-012 | Granting without `grant:human` is denied | env-human-access / M1-FR-15, M1-FR-08 | negative | High |
| TC-EHA-013 | A permission identifier that is not plane-declared is rejected | env-human-access / M1-FR-15 (GAP-INT-006) | negative | High |
| TC-EHA-014 | An ended environment credential is refused on the next request | env-human-access / M1-FR-21, M1-FR-07 | negative | High |
| TC-EHA-015 | An agent credential is refused at the control gateway | env-human-access / M1-FR-09 | negative | High |
| TC-EHA-016 | An agent credential presented beside a human credential is refused | env-human-access / M1-FR-09 | negative | High |
| TC-EHA-017 | An expired environment credential is refused, and cannot be renewed | env-human-access / M1-FR-20 | negative | Medium |
| TC-EHA-018 | A grant to a non-existent principal is rejected | env-human-access / M1-FR-15 | negative | Medium |
| TC-EHA-019 | An environment credential never outlives its sign-in | env-human-access / M1-FR-20 | edge-boundary | High |
| TC-EHA-020 | Renewal after the sign-in has ended is refused | env-human-access / M1-FR-20, M1-FR-21 | edge-boundary | High |
| TC-EHA-021 | A direct human operation carries no envelope, and is attributed to the human | env-human-access / M1-FR-12, M1-FR-09 | edge-boundary | Medium |
| TC-EHA-022 | E holds only verify-only material for the organization sign-in | env-human-access / M1-FR-10 | edge-boundary | High |
| TC-EHA-023 | If revocation state cannot be read, a control request is refused | env-human-access / M1-FR-07 | edge-boundary | High |
| TC-EHA-024 | This unit's operations are defined in the contract and validated against it | env-human-access / M1-FR-02 | happy-path | High |
