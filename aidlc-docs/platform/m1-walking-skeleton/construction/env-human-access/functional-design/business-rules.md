# Business Rules: U4 `env-human-access`

**Unit**: U4 `env-human-access` (soorma-core#7). Control face, environment level. Adds S2
`control-gateway` (its human operations)
**Built against**: ID @ `prd-identity-v1.0` (the main source), PF @ `prd-platform-foundations-v1.3`
**Decisions from**: the Functional Design plan, Q1 to Q7 and proposals P-01 to P-15, answered
2026-11-11T03:59:19Z (recorded verbatim in `audit.md`)
**Entities**: [domain-entities.md](domain-entities.md). **Logic**:
[business-logic-model.md](business-logic-model.md)
**Inherited rules**: U1's credential, identifier, versioning and error rules
(`construction/wire-contract/functional-design/business-rules.md`: BR-CR, BR-ID, BR-VER,
BR-ERR); U2's internal interface and sign-in rules (`construction/org-identity/`: BR-INT,
BR-SI, P-01, P-02, P-06; obligations F-1 to F-3); U3's seam, `evaluateAgent`, the human-only
class, and Problem emission (`construction/authority-evaluation/`: BR-SEAM, BR-AU-01, D-AE-03,
BR-PE). This document does not restate them except where U4 changes them (U2 amendment A7)
**Specification gaps**: GAP-EHA-001 (**Resolved — clarified, no PRD change**: R2, D-EHA-01).
Inherited: GAP-INT-006 (Open, soorma-prd#24; only plane-declared identifiers accepted, BR-ACC).
GAP-INT-001, 002, 005 resolved (recorded for traceability)

Module names are the Application Design's: P1 `perimeter`, P3 `authority`, P4 `registry`, P5
`credentials`, P7 `attribution`, P9 `config`, P10 `org-identity` (S1's, called through its
internal interface), P11 `policy-decision`.

---

## 1. Decisions

| ID | Decision | Source | Class |
|---|---|---|---|
| **D-EHA-01** | **Ending a sign-in bars renewal and any new issuance; it does not refuse the environment credentials already issued from it** (R2). (1) The organization level is consulted at issuance and renewal only (`signInStatus`). (2) An ended sign-in bars renewal and any new issuance. (3) The credential lives to its own expiry, capped by D-EHA-02. (4) A full logout is ending both, per ID FR-011. **SECURITY-12's reading: ending the environment credential is its own logout.** R1 (cascade) contradicts ID FR-009, §9 *Failure Modes*, §10 *NFR Profile*, the §18 glossary entry *Organization level*, and U2 BR-INT-08 (see GAP-EHA-001) | Q1 D; ID FR-009, FR-010, FR-003, FR-011 | **Specification gap**, resolved — clarified, no PRD change (GAP-EHA-001) |
| **D-EHA-02** | **U2 amendment A7, `signInStatus`**: it answers `{ status: 'live', expiresAt }` only when the sign-in record is `live`, its current expiry has not passed, and its principal is `active`; otherwise `{ status: 'ended' }`; and `{ status: 'unknown' }` when no sign-in with that id exists in the organization. **E caps every credential's expiry**, at issuance and at each renewal, at the earlier of *now + the credential lifetime* and *the sign-in's current `expiresAt`*. Renewing the sign-in at S1 then lets the credential be renewed further. Suspension, when a later slice adds it, is already honoured. An unpublished interface: no contract change | Q2 A; ID FR-010 | Technology |
| **D-EHA-03** | **Every state-changing operation writes an attribution record**: issuing, renewing, and ending a credential; a grant; and the configured first grant. Each names the actor (the human and the credential or sign-in presented, or the configuration), scope E, and no origin mode. The credential record still holds the credential's own lifecycle | Q3 A; PF FR-025, §10; ID §10 *Auditability* | Technology |
| **D-EHA-04** | **P7 defines the whole Attribution Record once**: scope; actor (human, configuration, or agent); chain; origin; operation; target; flags; **plus the resolved sponsor for an agent actor, and U3's re-broadening outcome** (whether it was load-bearing, and at which hop; U3 BR-ST-08) beside the chain and origin. FR-025's grant-scoped read is out of M1, but **whatever it would return is recoverable from the record alone**. U4 builds and tests the writer for all three actor kinds, with constructed inputs for the agent kind; the I4 evidence is written once, here. U5 to U7 only call it | Q4 A plus the user's two fields; PF FR-025, §7b *Recoverability*; I4 | Technology |
| **D-EHA-05** | **`unknown_principal`** (400): a grant target that is not a principal of E's organization. `errors[]` has one entry, `pointer` `/target`. Reached only after the `grant:human` check, so only an Admin in E learns whether a principal exists. A new code: compatible (the code set is open) | Q5 A; U2 obligation 5 | Technology |
| **D-EHA-06** | **`unknown_permission`** (400): a well-formed permission identifier that is not accepted. `errors[]` points at each one (`/permissions/{i}`), ordered by pointer, at most 10. Checked at step 6, before authority, as validation; the accepted set is public (pre-release statement 4). U5's standing sets use the same code | Q6 A; GAP-INT-006; TC-EHA-013 | Technology |
| **D-EHA-07** | **The first grant is applied by E's S2 at start-up**: if E holds no configuration grant for the configured first Admin, S2 writes one (`grant:human`, `human:manage`; *granted-by* = the environment's configuration) **with its attribution record, in one transaction**. Idempotent on every restart. **S2 does not call S1 for it**: configuration is the trust root (ID FR-004), and S1 registers the principal from the same file. A later configuration naming another first Admin grants them too; earlier grants stay (revocation is absent). **Concurrent start-ups write at most one configuration grant per principal in E: the store enforces it with a uniqueness constraint** on (environment, principal) over configuration grants. A start-up whose write loses the race writes nothing, its attribution record included, and continues. **Tested with two start-ups at the same time** | Q7 A plus the user's addition; ID FR-004 | Technology |
| D-EHA-08 | **Presenter matrix at S2** (BR-PR) | P-01; ID §8b, FR-023 | Technology |
| D-EHA-09 | **The sign-in at issuance** is verified per U2 F-2, then `signInStatus` (BR-IS) | P-02; ID FR-009 | Technology |
| D-EHA-10 | **The environment credential carries no permissions**: authority is read per request from the Grants, so a fresh grant counts at once (read-your-writes) and renewal cannot widen authority. **Renewal keeps the credential** (id, subject, issued-from) and mints a new token with a later expiry, as U2's sign-in renewal does (D-OI-17). **Ending ends every token of it** | P-03; ID FR-010, §7a | Technology |
| D-EHA-11 | **O3 for the environment credential reads its record on every request, uncached.** An unreadable store is `unavailable`. S2 needs no propagation-bound cache; U6 adds the agent revocation cache, and the bound's value stays U6's | P-04; PF FR-012 | Technology |
| D-EHA-12 | **O4**: the credential verifies only with E's material, **and** its asserted environment must equal E's configured identity, or `credential_refused` | P-05; ID §8b O4, O11 | Technology |
| D-EHA-13 | **`evaluateHuman` and `holdsAnyGrant` live in P3** (`packages/authority`), over the seam (`grantedSet`, then `contains`). **No human-only refusal for a human.** No other module composes or tests a human's set | P-06; U3 BR-AU-01; I5 | Technology |
| D-EHA-14 | **P4's human `GrantSource`** is the union of every Grant to that principal in E, read on every call, **uncached** (U3 NFR-AE-14). A read failure rejects; the operation is `unavailable` | P-07; ID §10 read-your-writes | Technology |
| D-EHA-15 | **Grant semantics** (BR-GR) | P-08; PF FR-018, §7a; ID FR-015 | Technology |
| D-EHA-16 | **A grant may target any principal of E's organization, `pending` included.** A target in another organization does not exist for E (`unknown_principal`) | P-09; ID FR-015, §6 | Technology |
| D-EHA-17 | **An operation's write and its attribution record are one transaction.** If either fails, neither is written, and the operation is `unavailable` | P-10; I4; SECURITY-15 | Technology |
| D-EHA-18 | **Refusals are not attribution records.** They go to the security log, naming a human only by E's log pseudonym (`hp_…`, under E's own key, never the organization's) | P-11; SECURITY-03; ID §6 | Technology |
| D-EHA-19 | **Project-scope grants (PF §8a, "expanded at grant time") are not built.** M1-FR-15 builds environment-scope grants only, and no *done when* item needs them. A delivery limit, added to the requirements' *Absent from M1* list as a consistency fix (§14). PF §8a specifies it fully, so it is not a gap | P-12; delivery scope (brief) | Delivery decision |
| D-EHA-20 | **E does not re-check the organization's second-factor requirement at issuance.** S1 owns it (U2 BR-SI-05). A K-only sign-in left from before the requirement turned on lives at most to its expiry, which caps any credential issued from it (D-EHA-02) | P-13; ID FR-006 | Technology |
| D-EHA-21 | **S2 emits every Problem through P1** (`problemResponse`), and its tests run `assertProblem` on every Problem | P-14; U3 BR-PE | Technology |
| D-EHA-22 | **Responses**: issuance and renewal return `{ credential, expiresAt }` (RFC 3339); `grantToHuman` returns the Grant (`id`, `target` as `HumanPrincipalReference`, `permissions`, `grantedAt`, `selfGrant`); ending returns no body. Every S2 operation names exactly one security scheme | P-15; credentials.md; U2 obligation 6 | Technology |
| D-EHA-23 | **Where the organization level is consulted** (made at design, to be confirmed at review): `signInStatus` at issuance and at renewal (D-EHA-01); `principalExists` in `grantToHuman`, after its authority check, because a grant needs a real target (Application Design, services.md US-04; U2 obligation 5). **Never** for the environment credential's O1 to O4, never at ending, and never per request. Verify keys are cached and refreshed off the request path (U2 F-1) | ID FR-009; U2 BR-INT-08 | Technology |
| D-EHA-24 | **The three credential operations take no request body**: a body is `malformed_request` with `pointer` `''`, after the contract version, as S1's `renewSignIn` and `endSignIn` do | S1's convention | Technology |
| D-EHA-25 | **Statuses**: `200` for issuance, renewal, and `grantToHuman`; `204` for ending. As S1 (`authenticate` 200, `endSignIn` 204) | S1's convention | Technology |
| D-EHA-26 | **Renewal and ending each change the record only while it is `live`**, atomically. Of a renewal and an end racing on one credential, whichever commits second finds it not `live` and is `credential_refused` (an ended credential), writing nothing | ID FR-011; SECURITY-15 | Technology |
| D-EHA-27 | **The S1 caller fails closed.** S1 unreachable, a timeout, a non-200 answer, or an answer that does not match its expected shape: `unavailable` (503, `Retry-After`). S1 is authenticated by its TLS certificate under the local CA (`org-gateway.soorma.internal`, shared-infrastructure.md *TLS*); each request is signed with E's caller key (U2 F-3). Nothing from S1 is cached except the verify keys | U2 obligation 4; SECURITY-15; I3 | Technology |
| D-EHA-28 | **Start-up fails closed**: an invalid environment configuration, a missing secret, or a first grant that cannot be written stops S2 from starting, as S1 does (U2 BR-CFG-08) | ID FR-004; SECURITY-15 | Technology |
| D-EHA-29 | **Every environment-store record carries its environment, and every read and write constrains on it**, in addition to the store being per environment. The environment is never a label only (I1) | I1; PF FR-021 | Technology |
| D-EHA-30 | **Identifiers**: a credential, grant, or attribution record id has at least 128 random bits and is unique within E (BR-ID-07). Its encoding is NFR Design's | ID §6; BR-ID-07 | Technology |
| D-EHA-31 | **The sponsor on an agent actor is the registration's sponsor as resolved when the record is written**, beside the registration reference, so the sponsor is also resolvable through the registration (PF §7b, two hops). They cannot differ in M1, where no sponsor transfer exists. **The unit that adds a sponsor transfer decides which one the read returns** | D-EHA-04; PF §7b | Technology |

---

## 2. Presenter at S2 (BR-PR, step 2)

| ID | Rule | Source |
|---|---|---|
| BR-PR-01 | **Exactly one** `Authorization: Bearer {credential}` (counted on the raw header list), and **no** `Soorma-Delegation` header; otherwise `credential_refused` | BR-CR-01, 06; ID §8b |
| BR-PR-02 | `soorma_si_` is accepted **only on `issueEnvironmentCredential`**. Anywhere else at S2: `credential_refused` | ID FR-009; ID §7b; TC-EHA-009 |
| BR-PR-03 | `soorma_ec_` is accepted **only on** `renewEnvironmentCredential`, `endEnvironmentCredential`, `grantToHuman`. On issuance: `credential_refused` | ID §8b *Entry points by principal* |
| BR-PR-04 | `soorma_ac_` (no M1 agent operation exists at S2), `soorma_dc_` (reserved), and any other prefix: `credential_refused`, **by kind, without verifying** | ID FR-023; BR-CR-03; TC-EHA-015 |
| BR-PR-05 | **An agent credential beside a human's**: two credentials on one request, so `credential_refused` (BR-PR-01) | ID §8b, §7b; TC-EHA-016 |
| BR-PR-06 | The syntax: an RFC 6750 `b64token`, at most 4096 characters, else `credential_refused` | BR-CR-05 |
| BR-PR-07 | The prefix only selects how a credential is checked; it is accepted only after it verifies, and its verified kind must match its prefix (BR-CR-04) | I2 |

## 3. The Sign-In at Issuance (BR-IS, steps 3 and 4)

| ID | Rule | Source |
|---|---|---|
| BR-IS-01 | Verified with the **cached verify keys** only (public, verify-only). Per U2 F-2: the exact `typ: soorma-si+jwt`; `alg: Ed25519`, fixed in code; every claim required (`iss`, `sub`, `sid`, `jti`, `iat`, `exp`, `auth_time`, `amr`); **no `aud`**; at most 30 seconds' leeway on `exp` and `iat`; `iss` = `urn:soorma:org:{E's organization}`. Any failure: `credential_refused`. Expiry only after verification: `credential_expired` | ID FR-009; U2 F-2; BR-ERR-02 |
| BR-IS-02 | An unknown `kid` triggers one refetch of the verify keys, rate-limited (U2 F-1); still unknown: `credential_refused`. **With no verify keys loaded**, issuance is `unavailable`; the other operations do not use them and are unaffected | U2 F-1; SECURITY-15 |
| BR-IS-03 | Then **`signInStatus(sid)`** (A7): `live` continues, with the sign-in's `expiresAt`; `ended` or `unknown` is `credential_refused`; S1 unreachable or a bad answer is `unavailable` (D-EHA-27). **Never issue on a sign-in whose state could not be read** | U2 obligation 4; ID §8b O3; SECURITY-15 |
| BR-IS-04 | `live` from A7 also establishes that the principal is `active` (ID FR-010) | D-EHA-02 |
| BR-IS-05 | **E never mints a sign-in** and holds no material that can: it has no signing key for sign-ins | ID FR-009; PF §6; TC-EHA-022 |

## 4. The Environment Credential (BR-EC)

| ID | Rule | Source |
|---|---|---|
| BR-EC-01 | **Issuance** (`issueEnvironmentCredential`): after BR-IS and the contract version (step 5) and no body (D-EHA-24), the principal must hold **at least one grant in E** (`holdsAnyGrant`, P3), else `forbidden`. Then a new credential: `subject` = the sign-in's `sub` with E's organization; `issuedFrom` = `sid`; `expiresAt` per BR-EC-04; record and attribution record in one transaction | ID FR-010, §8a; TC-EHA-002, 011 |
| BR-EC-02 | **Verification** (steps 3 and 4) of a presented `soorma_ec_`: with **E's own material only**, then expiry (`credential_expired`, only after verifying); then the asserted environment equals E's configured identity (D-EHA-12); then **O3**: the record by `id`, uncached (D-EHA-11). No record, a record whose subject or environment differs from the token's, or `state` = `ended`: `credential_refused`. Store unreadable: `unavailable` | ID §8b O1 to O4; PF FR-012; TC-EHA-010, 014, 017, 023 |
| BR-EC-03 | **A credential from E2 does not verify in E**, so it is `credential_refused`, and its expiry is never disclosed | BR-ERR-02; ID §6; TC-EHA-010 |
| BR-EC-04 | **The expiry cap**: every new token's expiry is the earlier of *now + the credential lifetime* and *the sign-in's current `expiresAt`* from A7. Because a sign-in's expiry only moves later, a renewal never shortens the credential. The lifetime is NFR Requirements' | ID FR-010; D-EHA-02; TC-EHA-019 |
| BR-EC-05 | **Renewal** (`renewEnvironmentCredential`): after BR-EC-02, then **`signInStatus(issuedFrom)`** (still step 4): `live` continues; `ended` or `unknown` is `credential_refused`; S1 unreachable is `unavailable`. Then the contract version, no body, and the new expiry (BR-EC-04) written while the record is `live` (D-EHA-26), with the attribution record. **No grant check**: renewal is self-service (ID §8a), and the credential carries no authority to widen | ID FR-010, FR-011, §8a; TC-EHA-003, 020 |
| BR-EC-06 | **An expired credential cannot be renewed or ended**: `credential_expired` (BR-EC-02). The human obtains a new one from a live sign-in | TC-EHA-017 |
| BR-EC-07 | **Ending** (`endEnvironmentCredential`): after BR-EC-02, the contract version, and no body, `state` = `ended`, `endedAt`, `endedBy` = `self`, while `live` (D-EHA-26), with the attribution record. **Every token of the credential is refused thereafter** (O3). **No call to S1** | ID FR-011; O3; TC-EHA-004, 014 |
| BR-EC-08 | **Ending a sign-in at S1 does not end the credentials issued from it** (D-EHA-01). It bars their renewal (BR-EC-05) and any new issuance (BR-IS-03). They live to their own expiry, never later than the sign-in's (BR-EC-04). The same holds when S1 ends a sign-in on a material change (U2: `endedBy` = `materialChange`) | D-EHA-01; GAP-EHA-001 |
| BR-EC-09 | **Logout (SECURITY-12)**: ending the environment credential is its own logout, in E. A full logout is ending both the sign-in and each environment credential (ID FR-011: two acts) | D-EHA-01 |
| BR-EC-10 | A credential asserts a binding (subject, environment), **never a location or code identity**; nothing at S2 reads a network origin, host, or deployment label to decide identity | ID §8b; I3 |

## 5. Human Authority (BR-EV, step 9)

| ID | Rule | Source |
|---|---|---|
| BR-EV-01 | **`evaluateHuman({ policy, environment, principal, required })`**, in P3: `policy.grantedSet({ kind: 'human', principal }, E)`, then `policy.contains(set, required)`. `required` is non-empty. Denied: `forbidden` | ID §8b O8; U3 BR-AU-01 |
| BR-EV-02 | **`holdsAnyGrant({ policy, environment, principal })`**, in P3: the same read; true when the set is non-empty. Used only by issuance (ID FR-010 "holding at least one grant in E") | ID FR-010; D-EHA-13 |
| BR-EV-03 | **No human-only refusal for a human**: a human may hold `grant:human`, `human:manage`, `agent:delegate` (ID FR-013, FR-015). P3's human-only refusal applies to agents only (U3 BR-AU-03) | ID FR-013 |
| BR-EV-04 | **The one place**: no S2 module, P4, or P7 composes, intersects, or tests a human's permission set. S2 imports `evaluateHuman` and `holdsAnyGrant` and nothing that computes authority | I5; U3 BR-AU-01 |
| BR-EV-05 | P11 is built per request over the human `GrantSource` (D-EHA-14). Its agent half is empty at S2: no agent principal reaches S2 in M1 (BR-PR-04) | U3 NP-04 |
| BR-EV-06 | A read failure (the store) rejects; the operation is `unavailable`, never allowed | SECURITY-15; O9 |

**Required authority per operation** (ID §8a): issuance — a live sign-in, `active`, a grant in E
(BR-IS, BR-EV-02); renewal and ending — self; `grantToHuman` — `grant:human` in E (BR-EV-01).
**Coverage** (ID FR-014): every U4 effect is confined to E, so the authority is required in E
only.

## 6. Grants (BR-GR)

| ID | Rule | Source |
|---|---|---|
| BR-GR-01 | **The body**: `{ target: HumanPrincipalReferenceInput, permissions: [PermissionIdentifier] }`, closed; `permissions` 1 to 32 items, unique. Schema failures, a duplicate included: `malformed_request` with pointers | D-EHA-15; SECURITY-05; U2 obligation 6 |
| BR-GR-02 | Then **every identifier must be accepted** (BR-ACC): else `unknown_permission` (D-EHA-06). Still step 6, before authority | GAP-INT-006 |
| BR-GR-03 | Then **`evaluateHuman(actor, { grant:human })`**: else `forbidden`. **The actor need not hold what they grant** (ID FR-015); nothing compares the granted set with the actor's | ID FR-015, §8a; TC-EHA-007, 012 |
| BR-GR-04 | Then **the target**: an organization other than E's is `unknown_principal` with no call to S1; otherwise `principalExists` (D-EHA-23): `false` is `unknown_principal`; S1 unreachable is `unavailable` | D-EHA-05, 16; U2 obligation 5; TC-EHA-018 |
| BR-GR-05 | Then **one Grant record**: target, the set (as a set), `grantedAt`, `grantedBy` = the actor and the credential presented, `selfGrant` = target equals actor (both parts, exactly). With its attribution record, in one transaction (D-EHA-17) | PF §7a; ID FR-015; TC-EHA-005, 006 |
| BR-GR-06 | **Granting a permission already held is allowed** and recorded; the held set is a union, so nothing changes in authority | D-EHA-15 |
| BR-GR-07 | **Any principal of E's organization, `pending` included, may be a target**; any accepted permission may be granted to a human, human-only ones included | ID FR-013, FR-015; TC-EHA-008 |
| BR-GR-08 | **Read-your-writes**: the Grant is visible to the next request, because the held set is read uncached (D-EHA-14). H's self-grant of `agent:register` is usable at once (US-05) | ID §10; PF §10 |
| BR-GR-09 | A Grant is never modified or deleted in M1 (revocation, ID FR-016, is absent) | M1-FR-15 |
| BR-GR-10 | **Project-scope grants are not built** (D-EHA-19) | PF §8a |

## 7. Accepted Identifiers (BR-ACC; GAP-INT-006 work-around)

| ID | Rule | Source |
|---|---|---|
| BR-ACC-01 | The accepted set is **exactly the nine plane-declared identifiers** (domain-entities), defined once in P4 | M1-FR-15 |
| BR-ACC-02 | The schema accepts any identifier matching the permission pattern (BR-ID-06), so that widening later is compatible; acceptance is checked in code | BR-ID-06, 11 |
| BR-ACC-03 | **A recorded delivery limit, not specified behaviour.** Tenant-defined identifiers are unbuilt; widening is additive (pre-release statement 4) | GAP-INT-006, soorma-prd#24 |

## 8. The First Grant (BR-FG)

| ID | Rule | Source |
|---|---|---|
| BR-FG-01 | At S2's start-up, after the configuration is loaded: the configured first Admin of E receives **one** configuration grant of `grant:human` and `human:manage`, if E holds none for them (D-EHA-07) | ID FR-004 |
| BR-FG-02 | **At most one configuration grant per principal in E**, enforced by the store (a uniqueness constraint over configuration grants on environment and principal). A start-up that loses the race writes nothing (no grant, no attribution record) and continues | D-EHA-07 |
| BR-FG-03 | Its attribution record: actor `configuration`, operation `configureFirstGrant`, target the grant; same transaction | D-EHA-03, 17 |
| BR-FG-04 | **No call to S1**, and no enrollment material at E: E's configuration names the first Admin's identifier only (U2 D-OI-12) | ID FR-004; ID §6 |
| BR-FG-05 | If it cannot be written, **S2 does not start** (D-EHA-28) | SECURITY-15 |
| BR-FG-06 | **Recovery** of an environment where no one holds `grant:human` is by configuration only. In M1 no operation removes a grant, so it cannot arise; configuring a new first Admin grants them (BR-FG-01) | ID FR-004 |

## 9. Attribution (BR-AT)

| ID | Rule | Source |
|---|---|---|
| BR-AT-01 | **Every state-changing operation writes one record**, in the same transaction as its write: issuance, renewal, ending, `grantToHuman`, and the configured first grant (D-EHA-03, 17) | PF FR-025; ID §10 |
| BR-AT-02 | **A human actor** is the principal and the credential or sign-in presented (`signIn` at issuance; `environmentCredential` otherwise). **No chain, no origin, no re-broadening** | ID §7b *Recoverability*; FR-022 |
| BR-AT-03 | **The configuration actor** has no principal, chain, or origin | PF §7a *Granted-by*; ID FR-004 |
| BR-AT-04 | **An agent actor** (written by U6, U7) carries the logical agent, the instance, the credential where one was presented, the registration reference, and the **resolved sponsor** (D-EHA-31). On an envelope-bearing operation it also carries the stamped **chain**, **origin**, and **re-broadening outcome** (`loadBearing`, and `hop` exactly when load-bearing; U3 BR-ST-08) | D-EHA-04; PF FR-025, §7b |
| BR-AT-05 | The writer **refuses an inconsistent record** (a programming error, fail closed): a human or configuration actor with a chain, origin, or re-broadening; an agent actor without a sponsor; an envelope-bearing agent record without chain, origin, and outcome; `hop` without `loadBearing`, or outside the chain | I4 |
| BR-AT-06 | **Scope is E's configured identity**, the same value the credential's environment was compared with | ID §7b (Scope) |
| BR-AT-07 | **Scope, actor, chain, origin, and the resolved sponsor are recoverable from the record alone**, at zero hops and across a multi-hop chain (the I4 evidence, tested here with constructed agent records) | I4; PF §7b; FR-025 |
| BR-AT-08 | Records are **written once, never modified**. There is **no read surface** in M1, and no pruning (PF FR-013 is absent) | M1-FR-12 |
| BR-AT-09 | **Refusals write no record**; they go to the security log (D-EHA-18) | SECURITY-03 |

## 10. The Organization-Level Caller (BR-OL)

| ID | Rule | Source |
|---|---|---|
| BR-OL-01 | Three operations, nothing else: `verifyOnlyMaterial` (cached; BR-IS-02), `principalExists` (BR-GR-04), `signInStatus` (BR-IS-03, BR-EC-05) | U2 BR-INT |
| BR-OL-02 | **Every call is signed with E's caller key** (U2 F-3: `typ: soorma-internal+jwt`, `iss` = E, `aud` = `urn:soorma:org:{organization}:internal`, `htm`, `tgt` the full target with query, `bsh`, `iat`, `exp` at most 60 seconds later, `jti`) | U2 F-3; I3 |
| BR-OL-03 | **Never trusted because of the network**: S2 joins only `org-internal-{E}`, and the request is signed regardless; S1 is authenticated by its certificate (D-EHA-27) | I3; U2 Infrastructure Design |
| BR-OL-04 | **Off the per-request path**: called only where D-EHA-23 says. A failure is `unavailable`, never a pass (D-EHA-27) | ID FR-009, §9, §10 |
| BR-OL-05 | **Identifiers are values**: the principal is sent encoded in the query, never interpolated unencoded (BR-ID-09) | SECURITY-05 |

## 11. Refusals and the Check Order (BR-RF)

| Step | `issueEnvironmentCredential` | `renewEnvironmentCredential` | `endEnvironmentCredential` | `grantToHuman` |
|---|---|---|---|---|
| 1 | Body size: `payload_too_large` | same | same | same |
| 2 | BR-PR: a `soorma_si_` | BR-PR: a `soorma_ec_` | same as renewal | same as renewal |
| 3 | BR-IS-01, 02 | BR-EC-02 (verify, expiry) | same | same |
| 4 | BR-IS-03 (`signInStatus`) | BR-EC-02 (O4, O3), then BR-EC-05 (`signInStatus`) | BR-EC-02 (O4, O3) | BR-EC-02 (O4, O3) |
| 5 | Contract version (header) | same | same | same |
| 6 | No body (D-EHA-24) | No body | No body | BR-GR-01 schema, then BR-GR-02 accepted identifiers |
| 9 | `holdsAnyGrant`: `forbidden` | — (self) | — (self) | `evaluateHuman(grant:human)`: `forbidden`; then BR-GR-04 the target |
| write | credential + attribution | new expiry + attribution | ended + attribution | grant + attribution |

Steps 7, 8, and 10 do not apply: no envelope (ID FR-022).

| ID | Rule | Source |
|---|---|---|
| BR-RF-01 | **Specific for validation, generic for trust**: `malformed_request`, `unknown_permission`, and `unknown_principal` name a field; `credential_refused`, `credential_expired`, `forbidden` name nothing | BR-ERR-01 |
| BR-RF-02 | **No response discloses another environment**, or whether a principal exists to a caller without `grant:human` in E | ID FR-014; BR-ERR |
| BR-RF-03 | Every refusal is logged as a security event with its internal reason (for example `sign_in_ended`, `credential_ended`, `wrong_environment`, `no_grant_in_environment`, `authority_denied`, `org_level_unavailable`), never in a response. A human is named only by E's log pseudonym; no token, key, or identifier in any log | SECURITY-03; D-EHA-18 |
| BR-RF-04 | `unavailable` carries `Retry-After`; a 401 carries `WWW-Authenticate: Bearer` | BR-ERR |

## 12. Problem Emission (BR-PE)

U3's BR-PE applies unchanged (D-EHA-21). P1's Problem table gains `unknown_principal` and
`unknown_permission` (§13); S2's tests run `assertProblem` on every Problem, and over both new
codes.

## 13. Contract Changes

Made at U4's Code Generation, under contract `0.1.0` (unreleased), and recorded in
`contract/CHANGELOG.md`.

| Change | Where | Classification |
|---|---|---|
| **`contract/control-gateway.openapi.yaml`, new**, with S2's four human operations: `POST /environment-credentials` (`issueEnvironmentCredential`, `signIn`), `POST /environment-credentials/current/renewal` (`renewEnvironmentCredential`, `environmentCredential`), `POST /environment-credentials/current/end` (`endEnvironmentCredential`, `environmentCredential`), `POST /grants` (`grantToHuman`, `environmentCredential`). Each references the shared components, names one scheme, and validates every input (adding-an-operation.md). U5 adds its operations to the same document | the new document; generated types | Compatible: new operations |
| **`unknown_principal`** (400) and **`unknown_permission`** (400) | `ProblemCode` in `components.openapi.yaml`; `conventions/errors.md` (codes table; check order steps 6 and 9) | Compatible: the code set is open |
| `credentials.md`'s table already places `soorma_ec_` at S2 in its own environment, and `soorma_si_` at S2's issuance only. No change | — | — |

**U2 amendment A7 changes no published contract**: S1's internal interface is not part of it
(U2 BR-INT-01).

## 14. Amendments and Corrections

| Document | Change | Decision |
|---|---|---|
| U2 `functional-design/business-rules.md`, BR-INT-05 | **Amendment A7**: `signInStatus` answers `{ status: 'live', expiresAt }` only when the sign-in is `live`, unexpired, and its principal `active`; otherwise `ended`; `unknown` when absent. Applied to S1's code and U2's tests at U4's Code Generation (the image build joins the gate) | D-EHA-02 |
| `inception/requirements/requirements.md`, *Absent from M1* | **Consistency fix**: adds "PF §8a's project-scope grant (expanded at grant time)" to the PF behaviour absences | D-EHA-19 |
| `inception/application-design/component-methods.md`, P3, P4, P7, P10 | Correction note: P3 gains `evaluateHuman` (over the seam) and `holdsAnyGrant`; P4's `heldSet` is the human `GrantSource`; P7's `record` takes the actor kinds, the resolved sponsor, and the re-broadening outcome; P10's internal `signInStatus` (A7) | D-EHA-02, 04, 13 |
| `inception/application-design/services.md`, US-03 step 2 | Correction note: issuance checks `authority.holdsAnyGrant(H, E)`, not `registry.heldSet` directly (I5) | D-EHA-13 |

## 15. Misuse Cases (SECURITY-11)

| Misuse | Rule that defeats it |
|---|---|
| A sign-in presented to a control operation other than issuance | BR-PR-02: `credential_refused` |
| E's credential presented at E2 | BR-EC-03: it does not verify there |
| An agent credential at S2, alone or beside a human's | BR-PR-04, 05 |
| The reserved delegation header, to reach an unbuilt path | BR-PR-01 |
| A forged or altered environment credential | BR-EC-02: E's material; the record must match |
| Renewing from a sign-in that was ended, or whose principal is no longer `active` | BR-EC-05 (A7) |
| Renewing past the sign-in's life | BR-EC-04: the cap |
| Using a credential after ending it | BR-EC-07: O3 on every request |
| Racing a renewal against an end to keep a credential alive | D-EHA-26 |
| A non-Admin grants themselves or another | BR-GR-03: `forbidden` |
| An Admin probing which principals exist, or a non-Admin probing | BR-GR-04 after BR-GR-03: only an Admin in E learns existence; a non-Admin gets `forbidden` first |
| A grant naming a principal of another organization | BR-GR-04: `unknown_principal`, no call |
| Granting a tenant-defined or misspelled identifier | BR-GR-02: `unknown_permission` |
| An S1 outage, hoping issuance or renewal skips the sign-in check | BR-IS-03, BR-EC-05: `unavailable` |
| A store outage, hoping O3 or authority fails open | BR-EC-02, BR-EV-06: `unavailable` |
| A spoofed S1 on the internal network answering `live` | D-EHA-27: S1's certificate under the local CA; BR-OL-03 |
| Two S2 instances starting together, duplicating the first grant | BR-FG-02: the uniqueness constraint |
| An attribution write failing silently, leaving an unattributed grant | D-EHA-17: one transaction |
| Flooding issuance to load S1 | Rate limiting on S2: NFR Requirements (SECURITY-11) |

## 16. Accepted Residuals

| Residual | Bound | Decision |
|---|---|---|
| **After a sign-in ends** (logout at S1, or a material change), an environment credential issued from it stays usable in E until its own expiry, unless the human ends it | The credential lifetime (NFR Requirements), and never past the sign-in's expiry | D-EHA-01 (the user's, GAP-EHA-001); SECURITY-12 reading: ending the credential is its own logout |
| **An Admin may grant themselves any accepted permission** | Every self-grant is recorded | ID FR-015 by design; prohibiting it is commercial |
| **During an organization-level outage**, E's control face is partly unavailable. **Unavailable** (`unavailable`, 503, `Retry-After`): issuance and renewal (`signInStatus`), and `grantToHuman` (its target check, `principalExists`). **Unaffected**: ending a credential, and every O1 to O4 check on a presented environment credential, none of which calls the organization level. This goes slightly beyond ID §10's "stops new sign-ins and organization operations": `grantToHuman` is an environment operation whose own target lookup needs the organization level | The outage's duration; nothing is issued, renewed, or granted on unread state (fail closed) | **D-EHA-23** (the user's acceptance at approval: `principalExists` is the operation's own lookup, not a per-request freshness check); D-EHA-27 |

## 17. Forward Obligations

Posted on each unit's issue when this stage is approved.

| To | Obligation |
|---|---|
| **U4 NFR Requirements** | The environment store (PostgreSQL per environment); the environment credential lifetime; rate limiting on S2 (SECURITY-11); S2 latency (interactive at issuance, ID §10); the S1 call timeout; leeway on E's own tokens |
| **U4 NFR Design** | The credential format and E's minting key ring; the verify-key cache's schedule and refetch rate (U2 F-1); the internal-call signer (U2 F-3); the security log events (BR-RF-03); the uniqueness constraint's physical form (BR-FG-02) |
| **U4 Infrastructure Design** | S2 for E and E2; each environment's store and migrate service; `org-internal-{env}`; each environment's secrets volume and init container; E's caller key pair (public half to S1's `internalCallers`); E's minting key; E's log-pseudonym key; `tenancy.yaml` additions |
| **U4 Code Generation** | U2 amendment A7 in S1 and U2's tests, with S1's image build in the gate; the four contract operations and two codes; the concurrent start-up test (BR-FG-02) |
| **U2 (soorma-core#5)** | Amendment A7 to BR-INT-05, applied by U4 |
| **U5 (soorma-core#8)** | `registerAgent` and `issueRegistrationSecret` call **`evaluateHuman(agent:register)`**; the sponsor's held set is P4's human `GrantSource` (the same uncached read), recorded as the snapshot; standing sets use **BR-ACC** and **`unknown_permission`**; S2's presenter rules (BR-PR) and check order (§11) apply; each writes an attribution record with a human actor (operations `registerAgent`, `issueRegistrationSecret`; target the registration) |
| **U6 (soorma-core#9)** | S3 refuses `soorma_ec_` and `soorma_si_` by kind; P5 gains the agent kind and the propagation-bound revocation cache; bootstrap and renewal write attribution records with an **agent actor carrying the resolved sponsor and the registration reference**, and no chain, origin, or re-broadening (no envelope; GAP-INT-008), stating why; U6's tables join the environment store with D-EHA-29 |
| **U7 (soorma-core#10)** | S4 refuses `soorma_ec_` and `soorma_si_` by kind; publish and subscribe write attribution records with an agent actor, the **resolved sponsor**, and the stamped **chain**, **origin**, and **re-broadening outcome** from U3's result (BR-ST-08) |
| **Build and Test** | The residuals in §16; TC-EHA cases for A7 (a renewed sign-in extends renewal; a suspended principal cannot arise in M1). **With S1 stopped** (the organization-level outage residual, D-EHA-23): issuance, renewal, and `grantToHuman` return `unavailable` with `Retry-After`; ending a credential succeeds; and a presented environment credential still passes or fails O1 to O4 exactly as with S1 running (an ended, expired, or other-environment credential is refused; a live one reaches its operation) |

## 18. Specification Gaps

| Gap | Status | Effect |
|---|---|---|
| GAP-EHA-001 | **Resolved — clarified, no PRD change** (the user's decision; not raised) | D-EHA-01, BR-EC-05, 08, 09; `prd-gaps/specification-gaps.md` |
| GAP-INT-006 (inherited) | Open, soorma-prd#24 | Worked around: BR-ACC |
