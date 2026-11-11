# Test Case Index: env-human-access

Unit abbreviation: EHA = env-human-access

Canonical source: [test-specs-narrative.md](test-specs-narrative.md). 91 test cases, comprehensive scope (24 from the inception pass; 67 added by the construction pass, 2026-11-11).

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
| TC-EHA-025 | Issuance from an ended sign-in is refused | env-human-access / M1-FR-20 (BR-IS-03) | negative | High |
| TC-EHA-026 | A grant made after issuance applies at once, and renewal adds nothing | env-human-access / M1-FR-20, M1-FR-15 (D-EHA-10, 14) | edge-boundary | High |
| TC-EHA-027 | A self-grant is usable on the next request | env-human-access / M1-FR-15 (BR-GR-08; NFR-EHA-10) | edge-boundary | High |
| TC-EHA-028 | A renewed sign-in extends renewal of the credential | env-human-access / M1-FR-20 (D-EHA-02; A7) | happy-path | High |
| TC-EHA-029 | A credential stays usable after its sign-in ends, until its own expiry | env-human-access / M1-FR-21 (D-EHA-01; NFR-EHA-02) | edge-boundary | High |
| TC-EHA-030 | Renewal racing an end, and two concurrent ends, each commit exactly one outcome | env-human-access / M1-FR-21 (D-EHA-26) | edge-boundary | High |
| TC-EHA-031 | Ending, O3, and authority make no organization-level call | env-human-access / M1-FR-09 (D-EHA-23; BR-OL-04) | edge-boundary | High |
| TC-EHA-032 | A delegation header, or a second Authorization header, is refused | env-human-access / M1-FR-09 (BR-PR-01) | negative | High |
| TC-EHA-033 | An environment credential is refused at issuance | env-human-access / M1-FR-09 (BR-PR-03) | negative | Medium |
| TC-EHA-034 | Malformed or unknown-kind credentials are refused by kind | env-human-access / M1-FR-09 (BR-PR-04, 06) | negative | High |
| TC-EHA-035 | Two concurrent start-ups write one configuration grant and one record; a restart writes nothing | env-human-access / M1-FR-14 (D-EHA-07; BR-FG-02) | edge-boundary | High |
| TC-EHA-036 | S2 refuses to start on a bad key ring | env-human-access / M1-FR-10 (NP-EHA-02; D-EHA-28) | negative | High |
| TC-EHA-037 | S2 refuses to start if the first grant cannot be written | env-human-access / M1-FR-14 (BR-FG-05) | negative | Medium |
| TC-EHA-038 | `unknown_permission` reports at most 10 pointers | env-human-access / M1-FR-15 (D-EHA-06) | edge-boundary | Medium |
| TC-EHA-039 | A malformed grant body is rejected with pointers | env-human-access / M1-FR-15 (BR-GR-01) | negative | High |
| TC-EHA-040 | Every environment-store access path constrains on the environment | env-human-access / M1-FR-10 (D-EHA-29; I1) | edge-boundary | High |
| TC-EHA-041 | A grant target in another organization is `unknown_principal`, with no organization-level call | env-human-access / M1-FR-15 (BR-GR-04) | negative | High |
| TC-EHA-042 | A non-Admin cannot probe whether a principal exists | env-human-access / M1-FR-15 (BR-RF-02) | negative | High |
| TC-EHA-043 | An unreachable or misbehaving S1 makes S2 answer `unavailable`, after one attempt | env-human-access / M1-FR-07 (D-EHA-27; NFR-EHA-07, 23) | negative | High |
| TC-EHA-044 | S2 computes a human's authority only through P3 | env-human-access / M1-FR-08 (BR-EV-04; I5) | edge-boundary | High |
| TC-EHA-045 | A credential asserting another environment, signed with E's key, is refused | env-human-access / M1-FR-10 (D-EHA-12) | negative | High |
| TC-EHA-046 | Each actor kind is recoverable from its attribution record alone | env-human-access / M1-FR-12 (BR-AT-07; I4) | happy-path | High |
| TC-EHA-047 | The store refuses an inconsistent attribution record | env-human-access / M1-FR-12 (BR-AT-05) | negative | High |
| TC-EHA-048 | A failed attribution write rolls back its operation, and refusals write no record | env-human-access / M1-FR-12 (D-EHA-17; BR-AT-09) | edge-boundary | High |
| TC-EHA-049 | A forged sign-in and a forged environment credential, sent raw, are refused | env-human-access / M1-FR-09 (I2; O10) | negative | High |
| TC-EHA-050 | Identity comes from the credential alone, never the network | env-human-access / M1-FR-10 (BR-EC-10; I3) | negative | High |
| TC-EHA-051 | Nothing of E2's is reachable from E | env-human-access / M1-FR-10 (I1) | negative | High |
| TC-EHA-052 | Body-less operations refuse a body, and the contract version is checked | env-human-access / M1-FR-02 (D-EHA-24) | negative | Medium |
| TC-EHA-053 | Logs carry no token, key, or principal identifier | env-human-access / NFR-EHA-18 (SECURITY-03) | edge-boundary | High |
| TC-EHA-054 | Every S2 security event is emitted by its flow | env-human-access / NFR-EHA-19 (SECURITY-14) | happy-path | Medium |
| TC-EHA-055 | The credential lives 15 minutes, capped at the sign-in | env-human-access / NFR-EHA-01 | edge-boundary | High |
| TC-EHA-056 | E's credentials have no `exp` leeway, and `iat` up to 30 seconds ahead | env-human-access / NFR-EHA-03 | edge-boundary | High |
| TC-EHA-057 | Sign-in leeway at issuance: the token check allows 30 seconds, A7 judges expiry on S1's clock | env-human-access / NFR-EHA-03 (U2 F-2) | edge-boundary | High |
| TC-EHA-058 | The request throttle refuses the 65th request after 1 second | env-human-access / NFR-EHA-04 (SECURITY-11) | edge-boundary | High |
| TC-EHA-059 | Aborted requests release their slots exactly once | env-human-access / NFR-EHA-04 (NP-EHA-05) | edge-boundary | High |
| TC-EHA-060 | The S1-call throttle refuses the 9th call after 1 second; key fetches are not throttled | env-human-access / NFR-EHA-05 (NP-EHA-04) | edge-boundary | High |
| TC-EHA-061 | Verify keys refresh every 5 minutes; on-demand fetches are limited to one per 30 seconds | env-human-access / NFR-EHA-08 (U2 F-1) | edge-boundary | High |
| TC-EHA-062 | Rotation at S1: after the 5-minute wait, issuance under the new key needs no on-demand fetch | env-human-access / NFR-EHA-08a (U2 R-1) | edge-boundary | High |
| TC-EHA-063 | Rotation at S1: a refresh that failed during step 1 is covered by one on-demand fetch | env-human-access / NFR-EHA-08a | edge-boundary | High |
| TC-EHA-064 | The unknown-`kid` flow through P1: refetch, then verify exactly once more | env-human-access / NFR-EHA-08 (NP-EHA-03, 15) | edge-boundary | High |
| TC-EHA-065 | The key source is read on every verification | env-human-access / NFR-EHA-08 (NP-EHA-15) | edge-boundary | High |
| TC-EHA-066 | Issuance makes exactly one `signInStatus` call and caps at its answer | env-human-access / M1-FR-20 (NP-EHA-15; BR-EC-04) | edge-boundary | High |
| TC-EHA-067 | E's store credentials cannot reach E2's store | env-human-access / NFR-EHA-09 (I1) | negative | High |
| TC-EHA-068 | Environment migrations are locked, checksummed, and run only by `{env}-migrate` | env-human-access / NFR-EHA-14 | edge-boundary | High |
| TC-EHA-069 | Code checks pass over U4's packages, and `===` on a secret token fails them | env-human-access / NFR-EHA-13, 25 (NP-EHA-14) | edge-boundary | High |
| TC-EHA-070 | S2 latency is measured and reported | env-human-access / NFR-EHA-15 | edge-boundary | Medium |
| TC-EHA-071 | Request bodies are bounded at 16 KiB | env-human-access / NFR-EHA-16, 17 (SECURITY-05) | edge-boundary | Medium |
| TC-EHA-072 | Identifiers are 128 random bits, base64url | env-human-access / M1-FR-20 (D-EHA-30) | edge-boundary | Low |
| TC-EHA-073 | Each malformed or altered environment credential is refused at its verification step | env-human-access / M1-FR-20 (NP-EHA-01) | negative | High |
| TC-EHA-074 | A token minted before a renewal stays valid until its own expiry | env-human-access / M1-FR-20 (NP-EHA-01) | edge-boundary | Medium |
| TC-EHA-075 | E's minting key rotates by configuration | env-human-access / M1-FR-20 (NP-EHA-02) | happy-path | Medium |
| TC-EHA-076 | The held set is the union of a human's grants | env-human-access / M1-FR-15 (BR-GR-06) | happy-path | Medium |
| TC-EHA-077 | A client-sent request id is replaced | env-human-access / M1-FR-02 (NP-EHA-12) | edge-boundary | Low |
| TC-EHA-078 | The shared-code move keeps U2 green, and S2 never links `@soorma/org-identity` | env-human-access / NFR-EHA-22 (NP-EHA-15) | edge-boundary | High |
| TC-EHA-079 | Secrets are mounted files only, and never cross a level (Compose-model test) | env-human-access / Infrastructure Design §3 (O-4; ID §6) | negative | High |
| TC-EHA-080 | The app role holds only its granted table and column privileges | env-human-access / Infrastructure Design §6 (O-2) | negative | High |
| TC-EHA-081 | S1's README says "wait at least 5 minutes" in its rotation steps | env-human-access / Infrastructure Design §10 (O-1) | edge-boundary | Medium |
| TC-EHA-082 | S1 refuses an ambiguous internal-caller configuration | env-human-access / Infrastructure Design §4 (I1) | negative | High |
| TC-EHA-083 | A caller key rotates with no outage, and a call is attributed only to its own environment | env-human-access / Infrastructure Design §4 | happy-path | Medium |
| TC-EHA-084 | Outage case 1: S1 stops under a running S2 | env-human-access / M1-FR-09 (D-EHA-23) | edge-boundary | High |
| TC-EHA-085 | Outage case 2: E's S2 starts while S1 is stopped | env-human-access / M1-FR-09 (D-EHA-23) | edge-boundary | High |
| TC-EHA-086 | Stack smoke test: sign in, issue, renew, grant, end, and cross-environment refusal | env-human-access / M1-FR-20, M1-FR-21 | happy-path | High |
| TC-EHA-087 | Alert rules and dashboard validate, and name only defined events | env-human-access / NFR-EHA-19 (O-3) | happy-path | Medium |
| TC-EHA-088 | The S2 image holds no secret | env-human-access / Infrastructure Design §2 | negative | High |
| TC-EHA-089 | No network spans two environments, and only edges are published, on loopback | env-human-access / Infrastructure Design §7 (I1) | negative | High |
| TC-EHA-090 | S1's `signInStatus` answers A7's shape | env-human-access / M1-FR-20 (A7) | happy-path | High |
| TC-EHA-091 | A `pending` principal may be a grant target | env-human-access / M1-FR-15 (BR-GR-07) | edge-boundary | Medium |
