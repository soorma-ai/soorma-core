# Test Case Index: agent-credentials

Unit abbreviation: AC = agent-credentials

Canonical source: [test-specs-narrative.md](test-specs-narrative.md). 93 test cases, comprehensive scope (TC-AC-001 to 022 at inception; TC-AC-023 to 093 added at the construction pass, 2026-11-12).

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
| TC-AC-023 | A lineage ends at M; renewal never extends past it | agent-credentials / M1-FR-06 (D-AC-02) | edge-boundary | High |
| TC-AC-024 | Two live credentials may assert the same instance identifier | agent-credentials / M1-FR-05 (D-AC-07) | edge-boundary | Medium |
| TC-AC-025 | A revoked agent cannot bootstrap, and its credentials cannot renew | agent-credentials / M1-FR-07 (BR-RV-01) | negative | High |
| TC-AC-026 | The seam's agent half decides identity only | agent-credentials / M1-FR-13 (D-AC-20) | happy-path | High |
| TC-AC-027 | Renewal never consults the registration secret | agent-credentials / M1-FR-06 (D-AC-15) | edge-boundary | Medium |
| TC-AC-028 | Revocation is terminal; reinstatement is a new issuance | agent-credentials / M1-FR-07 (BR-RV-02) | edge-boundary | High |
| TC-AC-029 | Bootstrap refuses a credential header with `malformed_request` | agent-credentials / M1-FR-05 (BR-PR-AC-02) | negative | Medium |
| TC-AC-030 | Any other path or method on S3 is a bare 404 | agent-credentials / M1-FR-09 (O9) | negative | Low |
| TC-AC-031 | The credential's environment is E's configured identity, whatever serves it | agent-credentials / M1-FR-10 (O11) | edge-boundary | Medium |
| TC-AC-032 | An agent without autonomy declared bootstraps and renews | agent-credentials / M1-FR-05, 06 (O12 N/A) | edge-boundary | High |
| TC-AC-033 | E's reads and writes never reach E2's rows, on every access path | agent-credentials / M1-FR-10 (I1) | negative | High |
| TC-AC-034 | The cache key includes the environment | agent-credentials / M1-FR-10 (BR-RC-04) | edge-boundary | Medium |
| TC-AC-035 | A bootstrap's and a renewal's records say everything from the record alone | agent-credentials / M1-FR-12 (I4) | happy-path | High |
| TC-AC-036 | An envelope-free operation's record cannot carry envelope facts | agent-credentials / M1-FR-12 (D-AC-33) | negative | High |
| TC-AC-037 | A draft envelope in the bootstrap body is refused | agent-credentials / M1-FR-01 (GAP-INT-008) | negative | Medium |
| TC-AC-038 | The contract publishes B, L, and M from the code's constants | agent-credentials / M1-FR-07 (NFR-AC-05) | happy-path | High |
| TC-AC-039 | Every presenter row of ID §8b is refused or reached at S3 | agent-credentials / M1-FR-09 (ID FR-023) | negative | High |
| TC-AC-040 | S3's production closure holds no organization-level code | agent-credentials / M1-NFR-08 (D-AC-11) | negative | High |
| TC-AC-041 | Nothing reads code identity or deployment topology | agent-credentials / M1-FR-05 (I10) | edge-boundary | Medium |
| TC-AC-042 | Every S3 refusal holds for a raw call | agent-credentials / M1-FR-09 (I2) | negative | High |
| TC-AC-043 | The same credential from another address resolves the same; no credential is refused anywhere | agent-credentials / M1-FR-05 (I3) | negative | High |
| TC-AC-044 | Each surface document holds one face only | agent-credentials / M1-NFR-03 (I6) | edge-boundary | Medium |
| TC-AC-045 | The changed contract passes U1's compatibility check | agent-credentials / M1-NFR-04 (I7) | happy-path | Medium |
| TC-AC-046 | No commercial or unassigned capability, and no seeding path, ships | agent-credentials / M1-FR-07 (I8) | negative | High |
| TC-AC-047 | No tenant constant in the platform's code | agent-credentials / M1-FR-05 (I9) | edge-boundary | Low |
| TC-AC-048 | Every bootstrap failure is the same response | agent-credentials / M1-FR-05 (BR-BS-07) | negative | High |
| TC-AC-049 | Failed attempts are recorded only for an existing registration, off the response path | agent-credentials / M1-FR-05 (BR-FA-01, 02) | edge-boundary | High |
| TC-AC-050 | A token whose record is missing or names another instance is refused | agent-credentials / M1-FR-06 (BR-RN-02) | negative | Medium |
| TC-AC-051 | Concurrent renewals of one lineage all succeed | agent-credentials / M1-FR-06 (D-AC-15) | edge-boundary | Medium |
| TC-AC-052 | With the store down, both operations fail closed and write nothing | agent-credentials / M1-FR-07 (NFR-AC-14) | negative | High |
| TC-AC-053 | An earlier token of a lineage stays valid until its own expiry | agent-credentials / M1-FR-06 (BR-CR-AC-06) | edge-boundary | Low |
| TC-AC-054 | B is 60 seconds, from the one constant, with no configuration key | agent-credentials / M1-FR-07 (NFR-AC-01) | edge-boundary | High |
| TC-AC-055 | L is 15 minutes at bootstrap and renewal | agent-credentials / M1-FR-06 (NFR-AC-02) | edge-boundary | Medium |
| TC-AC-056 | B < L ≤ M holds over the constants | agent-credentials / M1-FR-07 (NFR-AC-04) | edge-boundary | Low |
| TC-AC-057 | The bound's window admits 60 live attempts per agent in 60 seconds | agent-credentials / M1-FR-05 (NFR-AC-06) | edge-boundary | High |
| TC-AC-058 | The bound's backoff doubles from 1 second to a 60-second cap | agent-credentials / M1-FR-05 (NFR-AC-07) | edge-boundary | High |
| TC-AC-059 | `Retry-After` is the later of the two waits | agent-credentials / M1-FR-05 (NFR-AC-08) | edge-boundary | Low |
| TC-AC-060 | Admission is atomic per slot, and each environment has its own table | agent-credentials / M1-FR-05 (NFR-AC-09) | edge-boundary | High |
| TC-AC-061 | The lockout lasts at most 60 seconds after an attack stops | agent-credentials / M1-FR-05 (NFR-AC-10) | edge-boundary | High |
| TC-AC-062 | The Failed Bootstrap Attempt writer keeps U2's behaviour | agent-credentials / M1-FR-05 (NFR-AC-11) | edge-boundary | Medium |
| TC-AC-063 | S3 holds at most 64 requests in flight | agent-credentials / SECURITY-11 (NFR-AC-12) | edge-boundary | Medium |
| TC-AC-064 | Body bounds at S3 | agent-credentials / SECURITY-05 (NFR-AC-13) | negative | Low |
| TC-AC-065 | The cache is bounded, shares misses, and never admits by eviction | agent-credentials / M1-FR-07 (NFR-AC-15) | edge-boundary | High |
| TC-AC-066 | The revocation read's cost is reported | agent-credentials / M1-NFR-01 (NFR-AC-16) | edge-boundary | Low |
| TC-AC-067 | Bootstrap and renewal latency is reported | agent-credentials / M1-NFR-01 (NFR-AC-17) | edge-boundary | Low |
| TC-AC-068 | Token time rules: no leeway on expiry, 30 seconds on issue | agent-credentials / M1-FR-06 (NFR-AC-18) | edge-boundary | Medium |
| TC-AC-069 | A key rotation keeps old tokens verifying, and the README says wait at least 15 minutes | agent-credentials / M1-FR-06 (NFR-AC-19) | happy-path | Medium |
| TC-AC-070 | Constant-time comparison covers U6's code | agent-credentials / SECURITY-12 (NFR-AC-20) | edge-boundary | Low |
| TC-AC-071 | TLS 1.3 at S3's edge and to its store | agent-credentials / SECURITY-01 (NFR-AC-21) | negative | Medium |
| TC-AC-072 | S3's logs name events, never a secret or a human | agent-credentials / SECURITY-03 (NFR-AC-22) | negative | High |
| TC-AC-073 | S3's alert rules validate | agent-credentials / SECURITY-14 (NFR-AC-23) | happy-path | Low |
| TC-AC-074 | Nothing is pruned, and the store keeps U4's guarantees | agent-credentials / M1-FR-12 (NFR-AC-24) | edge-boundary | Low |
| TC-AC-075 | No new dependency | agent-credentials / SECURITY-10 (NFR-AC-25) | happy-path | Low |
| TC-AC-076 | The two new migrations apply, and 0001 and 0002 are unchanged | agent-credentials / NP-AC-02 | happy-path | High |
| TC-AC-077 | `agent_credentials` refuses an expiry past the lineage end, and a row of another environment | agent-credentials / NP-AC-03 | negative | Medium |
| TC-AC-078 | A revocation can only name a target in its own environment | agent-credentials / NP-AC-04 | negative | High |
| TC-AC-079 | S2's role has nothing on U6's tables | agent-credentials / SECURITY-06 (NP-AC-06) | negative | High |
| TC-AC-080 | S3's role can run exactly its statements, and nothing else | agent-credentials / SECURITY-06 (D-ID-AC-07) | negative | High |
| TC-AC-081 | P8's generic core keeps U2's API, and the agent slot has its own vectors | agent-credentials / NP-AC-07 | happy-path | High |
| TC-AC-082 | Each credential kind is refused by the other's verifier | agent-credentials / D-AC-03 (NP-AC-09) | negative | High |
| TC-AC-083 | Built images hold none of the forbidden packages | agent-credentials / M1-NFR-08 (NP-AC-10) | negative | High |
| TC-AC-084 | The secret check finds agent credentials and registration secrets, never fake ones | agent-credentials / SECURITY-12 (NP-AC-12) | negative | High |
| TC-AC-085 | `checkAgentRequest` takes callbacks, and P1 gains no dependency | agent-credentials / D-AC-27 (NP-AC-11) | happy-path | Medium |
| TC-AC-086 | U4's Compose-model rules hold for every service under every profile | agent-credentials / D-ID-AC-13 | edge-boundary | High |
| TC-AC-087 | S3's secrets, roles, and networks are separated as designed | agent-credentials / D-ID-AC-09 | negative | High |
| TC-AC-088 | The restore services mount their own `restore/` subdirectory | agent-credentials / D-ID-AC-14 | happy-path | Medium |
| TC-AC-089 | `stack:init` generates U6's secrets safely | agent-credentials / D-ID-AC-05 | happy-path | Medium |
| TC-AC-090 | The data role exists in a fresh store and S3 connects as it | agent-credentials / D-ID-AC-07 | happy-path | High |
| TC-AC-091 | U5's backup round trip still passes with S3 on the stack | agent-credentials / D-ID-AC-16 | happy-path | Medium |
| TC-AC-092 | The stack smoke test covers S3 in both environments | agent-credentials / D-ID-AC-18 | happy-path | High |
| TC-AC-093 | *Done when* 2, by raw calls | agent-credentials / M1-FR-05, 06 (done when 2) | happy-path | High |
