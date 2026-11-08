# Test Case Index: org-identity

Unit abbreviation: OI = org-identity

Canonical source: [test-specs-narrative.md](test-specs-narrative.md). 62 test cases, comprehensive scope (25 from the inception pass; 37 added by the construction pass, 2026-11-08).

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
| TC-OI-026 | A credential header sent to an unauthenticated operation is a malformed request | org-identity / M1-FR-09 (D-OI-26; BR-RF-06) | negative | High |
| TC-OI-027 | A credential of the wrong kind is refused on the sign-in operations | org-identity / M1-FR-09 (D-OI-05) | negative | High |
| TC-OI-028 | An unknown principal, or another organization, is refused exactly like a known one | org-identity / M1-FR-18 (BR-AB-06; BR-RF-01) | negative | High |
| TC-OI-029 | Refusal timing does not reveal whether a principal exists | org-identity / M1-FR-18 (BR-RF-03) | edge-boundary | High |
| TC-OI-030 | A success does not restore the window's allowance | org-identity / M1-FR-18 (NFR-OI-02, 03) | edge-boundary | High |
| TC-OI-031 | Backoff doubles from the 5th failure, to a 15-minute cap, and Retry-After reports the later wait | org-identity / M1-FR-18 (NFR-OI-03, 04) | edge-boundary | Medium |
| TC-OI-032 | The three surfaces share one counter | org-identity / M1-FR-18 (BR-AB-01) | negative | High |
| TC-OI-033 | Concurrent attempts cannot exceed the bound, and a success removes only its own reservation | org-identity / M1-FR-18 (NFR-OI-05, 06) | edge-boundary | High |
| TC-OI-034 | Two concurrent first authentications with the same enrollment material succeed at most once | org-identity / M1-FR-17 (D-OI-04) | edge-boundary | High |
| TC-OI-035 | Where P is required, first authentication activates H and issues no sign-in | org-identity / M1-FR-17 (D-OI-23) | happy-path | High |
| TC-OI-036 | A material change ends every live sign-in | org-identity / M1-FR-21 (BR-MC-04) | happy-path | High |
| TC-OI-037 | Replacing P retires the old one | org-identity / M1-FR-21 (BR-P-05; D-OI-24) | happy-path | Medium |
| TC-OI-038 | A failed P confirmation is refused without counting, and a pending enrollment expires | org-identity / M1-FR-17 (BR-P-06; NFR-OI-10) | negative | Medium |
| TC-OI-039 | TOTP codes follow RFC 6238, with one step of drift, each accepted once | org-identity / M1-FR-17 (NFR-OI-07, 08) | edge-boundary | High |
| TC-OI-040 | Renewal is refused when P is required and the sign-in lacks it | org-identity / M1-FR-17 (BR-SI-05) | edge-boundary | Medium |
| TC-OI-041 | Renewal never passes the 12-hour absolute maximum | org-identity / M1-FR-19 (NFR-OI-01) | edge-boundary | High |
| TC-OI-042 | The K policy normalizes, measures, and rejects as specified | org-identity / M1-FR-17 (BR-K-01 to 07; NFR-OI-14) | edge-boundary | Medium |
| TC-OI-043 | K is stored only as Argon2id over the full normalized input | org-identity / M1-FR-17 (BR-K-08; NFR-OI-11) | edge-boundary | High |
| TC-OI-044 | Sign-in verification is strict, and the token asserts no environment | org-identity / M1-FR-19 (BR-SI-02; P-01) | negative | High |
| TC-OI-045 | The internal interface accepts only signed requests bound to their content | org-identity / M1-FR-10 (BR-INT-02; P-06; I3) | negative | High |
| TC-OI-046 | The internal interface discloses only what each operation states | org-identity / M1-FR-10 (BR-INT-03 to 05) | happy-path | High |
| TC-OI-047 | The listeners are separate | org-identity / M1-FR-10 (P-07; I6) | edge-boundary | Medium |
| TC-OI-048 | Configuration errors stop start-up, and no environment part carries material | org-identity / M1-FR-14 (BR-CFG-02, 03, 08) | negative | High |
| TC-OI-049 | Logs carry no secret and no human identifier | org-identity / M1-FR-12 (NFR-OI-22, 23; SECURITY-03) | negative | High |
| TC-OI-050 | The Failed Attempt writer stays off the response path | org-identity / M1-FR-18 (NFR-OI-21) | edge-boundary | Medium |
| TC-OI-051 | Migrations run once, in org-migrate, and S1 holds only the app role | org-identity / M1-FR-16 (NFR-OI-18; D-ID-OI-02) | edge-boundary | High |
| TC-OI-052 | S1 fails closed when the store or the hashing budget is exhausted | org-identity / M1-FR-18 (NFR-OI-20; P-09, P-15) | negative | Medium |
| TC-OI-053 | Retention prunes what it may, and never a principal or material | org-identity / M1-FR-16 (NFR-OI-25) | edge-boundary | Medium |
| TC-OI-054 | TOTP seeds are encrypted and bound to their row | org-identity / M1-FR-17 (NFR-OI-09; P-03) | negative | High |
| TC-OI-055 | Request bodies over 16 KiB are refused | org-identity / M1-FR-02 (NFR-OI-27) | negative | Low |
| TC-OI-056 | The local stack is TLS-only and minimally exposed | org-identity / M1-NFR-05 (Infrastructure Design §4, §6) | edge-boundary | High |
| TC-OI-057 | Secrets are generated safely and never reach the repository or the image | org-identity / M1-NFR-09 (Infrastructure Design §3, §8) | negative | High |
| TC-OI-058 | The breached-list artifact matches its manifest | org-identity / M1-NFR-09 (NFR-OI-13) | edge-boundary | Medium |
| TC-OI-059 | Sign-in meets its latency targets | org-identity / M1-FR-19 (NFR-OI-19) | edge-boundary | Medium |
| TC-OI-060 | The identity-resolution seam decides identity only | org-identity / M1-FR-13 (BR-SEAM-01, 02) | edge-boundary | Medium |
| TC-OI-061 | No tenant identifier is hard-coded in platform code | org-identity / M1-FR-14 (I9) | edge-boundary | Low |
| TC-OI-062 | Refusal timing for known and unknown principals is measured and reported | org-identity / M1-FR-18 (BR-RF-03) | edge-boundary | Low |
