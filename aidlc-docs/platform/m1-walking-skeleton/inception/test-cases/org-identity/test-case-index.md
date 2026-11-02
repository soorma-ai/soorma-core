# Test Case Index: org-identity

Unit abbreviation: OI = org-identity

Canonical source: [test-specs-narrative.md](test-specs-narrative.md). 25 test cases, comprehensive scope.

| Test Case ID | Title | Source | Scope | Priority |
|---|---|---|---|---|
| TC-OI-001 | A configured first Admin is registered as pending, with enrollment material | org-identity / M1-FR-14, M1-FR-16 | happy-path | High |
| TC-OI-002 | First authentication sets H's own K and activates H | org-identity / M1-FR-17, M1-FR-16 | happy-path | High |
| TC-OI-003 | Signing in with K yields an organization sign-in | org-identity / M1-FR-19 | happy-path | High |
| TC-OI-004 | Once P is enrolled, sign-in needs K and P | org-identity / M1-FR-17 | happy-path | High |
| TC-OI-005 | H renews their own sign-in | org-identity / M1-FR-21 | happy-path | Medium |
| TC-OI-006 | H ends their own sign-in, the logout | org-identity / M1-FR-21 | happy-path | High |
| TC-OI-007 | H changes their own K by presenting the current K | org-identity / M1-FR-21 | happy-path | Medium |
| TC-OI-008 | Where P is required, H enrolls P without a sign-in by presenting K | org-identity / M1-FR-17 | happy-path | High |
| TC-OI-009 | Reused enrollment material is refused | org-identity / M1-FR-17 | negative | High |
| TC-OI-010 | A wrong K is refused, and the failure recorded against H | org-identity / M1-FR-18 | negative | High |
| TC-OI-011 | Attempts beyond the bound are refused | org-identity / M1-FR-18 | negative | High |
| TC-OI-012 | A K shorter than 8 characters is refused | org-identity / M1-FR-17 (M1-NFR-09) | negative | Medium |
| TC-OI-013 | A K on a breached-secret list is refused | org-identity / M1-FR-17 (M1-NFR-09) | negative | Medium |
| TC-OI-014 | Where P is required and not enrolled, sign-in is refused | org-identity / M1-FR-17 | negative | High |
| TC-OI-015 | Changing material without the current material is refused | org-identity / M1-FR-21 | negative | High |
| TC-OI-016 | K alone is refused once P is enrolled | org-identity / M1-FR-17 | negative | High |
| TC-OI-017 | Re-applying configuration does not re-register an existing first Admin | org-identity / M1-FR-14 | edge-boundary | High |
| TC-OI-018 | A principal's identifier is composed with its organization | org-identity / M1-FR-16 | edge-boundary | Medium |
| TC-OI-019 | Organization identity comes from configuration only | org-identity / M1-FR-10, M1-FR-14 | edge-boundary | High |
| TC-OI-020 | An expired sign-in cannot be renewed | org-identity / M1-FR-19, M1-FR-21 | edge-boundary | Medium |
| TC-OI-021 | Sign-ins and material changes are recorded | org-identity / M1-FR-12 | edge-boundary | Medium |
| TC-OI-022 | No operation deletes a human principal | org-identity / M1-FR-16 | edge-boundary | Low |
| TC-OI-023 | This unit's operations are defined in the contract and validated against it | org-identity / M1-FR-02 | happy-path | High |
| TC-OI-024 | A sign-in that fails verification is refused at the organization level | org-identity / M1-FR-09 | negative | High |
| TC-OI-025 | Material of a class core does not accept is rejected | org-identity / M1-FR-13 | negative | Medium |
