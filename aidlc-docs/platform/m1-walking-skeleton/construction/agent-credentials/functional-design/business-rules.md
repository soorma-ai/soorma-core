# Business Rules: U6 `agent-credentials`

**Unit**: U6 `agent-credentials` (soorma-core#9). Data face, environment level. Adds the
deployable S3 `data-gateway`, with `exchangeBootstrap` and `renewAgentCredential`
**Built against**: PF @ `prd-platform-foundations-v1.3` (the main source), ID @ `prd-identity-v1.0`
**Decisions from**: the Functional Design plan, Q1 to Q9 and proposals P-01 to P-23, answered
2026-11-12T03:49:08Z (recorded verbatim in `audit.md`). Q6 with the user's addition (the lockout
residual, §16; the secret-record mitigation carried to the first hosted deployment, §17). P-12
with the user's precision (BR-AT-AC-02)
**Entities**: [domain-entities.md](domain-entities.md). **Logic**:
[business-logic-model.md](business-logic-model.md)
**Inherited rules**: U1's credential, identifier, versioning and error rules
(`construction/wire-contract/functional-design/business-rules.md`: BR-CR, BR-ID, BR-VER,
BR-ERR); U2's abuse bound and Failed Attempt writer (`construction/org-identity/`: BR-AB, P-11,
D-OI-16); U3's Checked Agent Context and Problem emission (`construction/authority-evaluation/`:
D-AE-08, BR-PE, NFR-AE-10); U4's presenter matrix, credential token pattern, environment store,
attribution, and check order (`construction/env-human-access/`: BR-PR, BR-EC, BR-AT, BR-RF,
D-EHA-29, 30, 31, NP-EHA-01, 05, 06, 07, 15); U5's secret format and verifier
(`construction/agent-registration/`: D-AR-02, 04, 15, 16, NFR-AR-01 to 05, NP-AR-01, 02). This
document does not restate them except where U6 extends them
**Specification gaps**: **none found in U6**. Inherited: GAP-INT-008 (Open, soorma-prd#27; neither
bootstrap nor renewal carries an envelope); GAP-INT-009 (Open, soorma-prd#28; the internal
revocation read writes no attribution record)

Module names are the Application Design's: P1 `perimeter`, P4 `registry`, P5 `credentials`, P6
`identity-resolution` (its agent half: `agent-identity`, D-AC-08), P7 `attribution`, P8
`abuse-bound`. Symbols for values set at NFR Requirements: **B** the propagation bound, **L** the
agent credential's lifetime, **M** a lineage's maximum age.

---

## 1. Decisions

| ID | Decision | Source | Class |
|---|---|---|---|
| **D-AC-01** | **Renewal reads revocation state directly**, uncached, inside its own transaction, at both granularities. A revocation is refused at the next renewal. **The fail-closed cache is built and tested in P5 now** (clock and outage tests at the package level) and **wired by U7 at S4**, the per-request path. Bootstrap reads the agent's revocation directly too. At S3 the cache would buy no availability: both operations write to the store | Q1 A; PF FR-012, §9 | Technology |
| **D-AC-02** | **A lineage has a maximum age M** (value at NFR Requirements). Renewal never sets an expiry past the lineage's start plus M. The last token of a lineage expires at that limit, so renewing it is `credential_expired` and the instance re-bootstraps with its secret: no new code. A stolen credential works at most until its lineage ends; a stolen secret is not affected | Q2 A; PF FR-010 | Technology |
| **D-AC-03** | **A separate agent key ring per environment.** S3 holds the agent signing key only; S2 keeps the human environment credential's only; S4 (U7) gets agent verify keys only. A compromised S3 cannot mint human environment credentials, and a compromised S2 cannot mint agent credentials. One new secret per environment (Infrastructure Design) | Q3 A; SECURITY-06; PF §6 | Technology |
| **D-AC-04** | **One `secret` field, typed by its prefix.** The schema checks the material's syntax and length, not its prefix. The agent half accepts `soorma_rs_` only; any other prefix (`soorma_em_`, a credential prefix, or none) is the one refusal (D-AC-05), **after the bound, and recorded against the named registration**. A material type added later is additive | Q4 A; `credentials.md`; PF §8b; TC-AC-022 | Technology |
| **D-AC-05** | **A failed bootstrap is `authentication_failed`** (403), widened to "every failure to authenticate a human … or an agent instance at bootstrap". One code for every cause, no detail. Compatible: the code set is open and the code's meaning for humans is unchanged | Q5 A; `errors.md` | Technology |
| **D-AC-06** | **The bootstrap bound is U2's shape, per environment**: keyed on the presented agent identifier, **known or not**, in fixed slots under an HMAC with a **per-environment counter secret** (a new secret; Infrastructure Design). Same response and same work whether or not the registration exists. Window, live-attempt limit, and backoff values are NFR Requirements'. **With the user's addition**: the lockout residual is recorded (§16), and the secret-record mitigation is carried to the first hosted deployment (§17) | Q6 A, with the user's addition; PF FR-027, §7a *Revocation State* | Technology |
| **D-AC-07** | **Two live credentials of one agent may assert the same instance identifier.** Every bootstrap is a new credential, whatever identifier it asserts: a restarted instance re-bootstraps under its old name while its earlier credential runs out. The platform records the identifier and never enforces it. `identifiers.md` is clarified in place (§13) | Q7 A; PF FR-009 | Technology |
| **D-AC-08** | **P6's agent half is a new package, `packages/agent-identity`**, implementing the seam's agent half over P4's reads and `registry`'s secret functions. `packages/identity-resolution` stays the human half, unchanged. S3 links the agent half only | Q8 A; U5 obligation; NP-EHA-15 | Technology |
| **D-AC-09** | **The endpoint names the environment**: E's S3 serves E's configured identity, the bootstrap body names no environment, and the credential asserts E. A bootstrap sent to another environment's S3 fails as an unknown secret, because the record is in another store | Q9 A; PF §9 *Inputs*, FR-009, O11 | Technology |
| D-AC-10 | **Presenter at S3** (U4 BR-PR extended): bootstrap names no scheme. Renewal accepts exactly one `Authorization: Bearer soorma_ac_`; `soorma_ec_`, `soorma_si_`, `soorma_dc_`, an unknown prefix, two credentials, a credential beside `Soorma-Delegation`, or a credential anywhere else: `credential_refused`, **by kind, without verifying**. S3 holds no human or organization verify material | P-01; ID §8b, FR-023; U4 obligation | Technology |
| D-AC-11 | **No organization-level dependency**: S3 has no S1 address and no sign-in keys; its production dependency closure excludes `@soorma/org-identity`, with a test, as S2's | P-02; M1-NFR-08; NP-EHA-15 | Technology |
| D-AC-12 | **P8's manifest**: `packages/abuse-bound` moves `@soorma/org-identity` from `dependencies` to `devDependencies`. Its source never imports it; its test harness keeps importing `org-identity`'s test database by relative path, unchanged. No test or helper changes; U2's P8 tests pass unchanged; S1's image build shows S1 still resolves it | P-03 | Technology |
| D-AC-13 | **The token**, NP-EHA-01's pattern for agents: `soorma_ac_` + a JWS compact JWT; header `typ` `soorma-ac+jwt`, `alg` `Ed25519` fixed in code, `kid`; claims `env` `{ organization, project, environment }`, `sub` the logical agent, `inst` the instance, `cid`, `jti`, `iat`, `exp`, every one required; no `iss` or `aud`. **The kind is the `typ` plus the prefix**: a `soorma-ec+jwt` behind `soorma_ac_` is refused | P-04; D-AE-08; PF §7a, §3 | Technology |
| D-AC-14 | **The lineage**: bootstrap creates a credential record with a new `cid`; **renewal keeps the `cid`**, mints a new token (new `jti`, later `exp`), and moves the record's expiry. Revocation at the credential granularity (PF FR-011, "a single credential (one instance)") reaches every renewal of it, so renewal never outlives revocation (FR-010). A new bootstrap by the same instance is a **new issuance**, a new `cid` (FR-011, "reinstatement is a new issuance"). *Flagged for review in the plan; accepted* | P-05; PF FR-010, FR-011 | Technology |
| D-AC-15 | **What renewal checks**: O1, O2, O4 on the token; the record by `cid` in E, naming the token's agent and instance; O3 at both granularities; the registration still `registered`; the lineage's end (D-AC-02). **Not the registration secret**: PF FR-008 makes its lifecycle "independent of any credential's". The binding is unchanged. Concurrent renewals of one lineage all succeed; the record keeps the latest expiry | P-06; PF FR-008, FR-010, §11 | Technology |
| D-AC-16 | **Revocation State**: two granularities (a `cid`; a logical agent, which refuses bootstrap too); environment-scoped; terminal. **No product writer in M1**: the app role holds `SELECT` only; tests seed it through a fixture using the owner role, never compiled into the product. No edge operation reads or reveals it | P-07; PF §7a, FR-011, FR-012; M1-FR-07 | Technology |
| D-AC-17 | **The revocation read writes no attribution record** (GAP-INT-009, option 1). A refusal it causes goes to the security log | P-08; GAP-INT-009 | Work-around (Open gap) |
| D-AC-18 | **The fail-closed cache** (behaviour; physical form at NFR Design): a `not_revoked` answer is served only while **younger than B**, its age counted from when its read was issued; a `revoked` answer is terminal and may be kept; **a failed read is never cached**; with the store unreadable, an answer still inside B is served, and past B the request is denied, `unavailable`. Keyed on E and the target. **B is one defined value**, read by this cache and by U3's term cache (NFR-AE-10; a code constant, *consistency fix from NFR Design, Q1 A*) | P-09; PF FR-012, §9; NFR-AE-10 | Technology |
| D-AC-19 | **The secret check is U5's obligation exactly**: `parseRegistrationSecret` and `registrationSecretMatches` imported from `packages/registry`; the one record by its `id`, `active`, of the named registration, in E, on the four-column key; compared in constant time; never iterated. Every failure is the one refusal. Nothing logs the value, its `id`, or its digest | P-10; U5 NFR-AR-01 to 05, NP-AR-02 | Technology |
| D-AC-20 | **The seam decides identity only**: the agent half returns the registration reference and the secret record's `id`, or a rejection that never says why. The registration's state, revocation, and what the credential asserts stay in core, behind no seam | P-11; PF §12; M1-FR-13 | Technology |
| **D-AC-21** | **Attribution**: bootstrap and renewal each write one record through P7, in the same transaction as their credential write. Agent actor: registration, instance, resolved sponsor, and the credential presented (renewal only). No chain, origin, or re-broadening. Operations `exchangeBootstrap`, `renewAgentCredential`; target the credential (`cid`). **With the user's precision**: the record states why it has none, through its `operation`: both are operations that **never carry an envelope** (GAP-INT-008), so a reader knows from the record alone that the absence is by definition, not an omission (BR-AT-AC-02). P7 holds that list and refuses envelope facts on it (D-AC-33) | P-12, with the user's precision; PF FR-025, §7b; U4 BR-AT-04, 05 | Technology |
| D-AC-22 | **Failed bootstrap attempts**: one record per failed or bound-refused attempt **for an existing registration** (environment, agent, time, refused-by-bound, internal reason class), written **off the response path** by U2's writer pattern; the writer itself decides existence, so the response does not. Nothing presented is in it. The credential record names the secret record that bootstrapped it | P-13; PF FR-027; U2 D-OI-16, P-11 | Technology |
| D-AC-23 | **The instance identifier**: required; `InstanceIdentifier`; asserted, recorded in the record and the token, never verified; unchanged by renewal | P-14; PF FR-009, §7a; I10 | Technology |
| D-AC-24 | **Responses**: `200` for both, `{ credential, agent, environment, instance, expiresAt }`; `Cache-Control: no-store`; the credential is a secret from minting to the body. Renewal names `agentCredential` only; bootstrap names none. A new `contract/data-gateway.openapi.yaml` | P-15; `credentials.md`; M1-FR-02 | Technology |
| D-AC-25 | **Problems through P1**; S3's tests run the shared assertion on every Problem | P-16; BR-PE-06 | Technology |
| D-AC-26 | **Refusals are security-log events** with an internal reason (BR-RF-AC-03), naming the agent and E. Never the secret, its `id`, its digest, or a token | P-17; SECURITY-03 | Technology |
| D-AC-27 | **`checkAgentRequest` in P1**: presentation, O1, O2, O4, then O3 through a revocation source the caller passes, returning the Checked Agent Context. S3's renewal passes the direct source (D-AC-01); S4 will pass the cache. One implementation, run independently by each surface | P-18; D-AE-08; PF O10 | Technology |
| D-AC-28 | **No envelope** (GAP-INT-008, option 1): the closed bootstrap body admits no draft; renewal takes no body; O5 to O7 and O12 do not apply. The contract states it on both operations | P-19; GAP-INT-008; PF §8b O12 | Work-around (Open gap) |
| D-AC-29 | **S3's throttle**: U4's per-instance throttle (NP-EHA-05), with S3's own values at NFR Requirements. Bootstrap is also under P8's bound | P-20; SECURITY-11 | Technology |
| D-AC-30 | **Accepted residuals** of secret holders and earlier tokens (§16) | P-21 | Technology |
| D-AC-31 | ***Done when* 2 by raw calls** in `e2e/` | P-22 | Technology |
| D-AC-32 | **Coverage**: both operations act in E only. A credential from E2 fails at O4; a secret from E2 is unknown in E's store | P-23; PF §6; M1-FR-10 | Technology |
| D-AC-33 | **P7's envelope-free agent operations**: P7 holds the closed list `exchangeBootstrap`, `renewAgentCredential`, and its writer refuses an agent record for either one that carries envelope facts (a programming error, fail closed; BR-AT-05 extended; the store's CHECK constraint repeats it, NFR Design). *At approval (the user's, 2026-11-12)*: **the store's repeat is a new migration in `env-store`'s sequence; `0001` and `0002` stay untouched**. The other direction (an agent record for any other operation **must** carry them) **stays U7's, under the standing rules** (§17) | Made at design, from the user's precision on P-12; approved with the user's migration rule | Technology |
| D-AC-34 | **Bootstrap's order of work**: the bound is admitted before any presented material is parsed or read (`errors.md`); the secret is parsed before any store read of the registration or the secret (U5 NFR-AR-03), and its digest computed whether or not a record is then found, so the work after the bound does not depend on existence | Made at design; `errors.md`; NFR-AR-03 | Technology |

---

## 2. Presenter (BR-PR-AC, step 2)

| ID | Rule | Source |
|---|---|---|
| BR-PR-AC-01 | U4 BR-PR-01, 06, 07 apply unchanged | U4 |
| BR-PR-AC-02 | **Bootstrap names no scheme**: an `Authorization` or `Soorma-Delegation` header, whatever it holds, is `malformed_request` naming the header (after step 1, before step 5) | `errors.md`; `credentials.md` |
| BR-PR-AC-03 | **Renewal** accepts exactly one `Bearer soorma_ac_` (D-AC-10), then verifies it (BR-CR-AC) | D-AC-10 |
| BR-PR-AC-04 | At renewal, `soorma_ec_`, `soorma_si_` (TC-AC-012), `soorma_dc_`, any other prefix, two credentials, or `Soorma-Delegation`: `credential_refused`, by kind, without verifying | ID §8b; FR-023 |

## 3. The Bootstrap Request (BR-BQ, step 6)

| ID | Rule | Source |
|---|---|---|
| BR-BQ-01 | **The body**, closed: `{ agent: LogicalAgentIdentifier, secret: string, instance: InstanceIdentifier }`, all required. `secret` is at most 256 characters of the material syntax (`credentials.md`); its prefix is not part of the schema (D-AC-04). Any schema failure or extra field (an `environment`, a draft envelope): `malformed_request` with pointers | D-AC-04, 09, 28; SECURITY-05 |
| BR-BQ-02 | The body is validated before the bound, and a schema failure is not counted: it presents no material for the bound to protect | `errors.md` (steps 5, 6 before the bound) |

## 4. The Bootstrap Bound (BR-AB-AC)

| ID | Rule | Source |
|---|---|---|
| BR-AB-AC-01 | **Admission before any material is parsed or read** (D-AC-34), keyed on (E, the presented `agent`), **known or not** (D-AC-06). Refused: `too_many_attempts` (429, `Retry-After`) | PF FR-027; `errors.md` |
| BR-AB-AC-02 | **Settle**: a successful bootstrap removes exactly its own reservation; every other outcome after admission (any cause of the one refusal, or `unavailable`) settles as a failure. A crash between leaves the reservation: fail closed (U2 BR-AB) | U2 BR-AB |
| BR-AB-AC-03 | The slot is an HMAC under E's counter secret, so a caller cannot aim attempts at another agent's slot. A collision can only over-count | U2 NFR-OI-05; D-AC-06 |
| BR-AB-AC-04 | **It limits rate and recovers with time; it never locks permanently.** Renewal is credentialed and is not under the bound | U2 BR-AB; PF FR-027 |
| BR-AB-AC-05 | One counter per presented agent in E; the bound in E2 is E2's own (one store per environment) | PF §6; I1 |

## 5. Resolution and Lifecycle at Bootstrap (BR-BS, step 9)

Every failure in this section is **the one refusal**, `authentication_failed` (D-AC-05), and
settles the bound as a failure.

| ID | Rule | Source |
|---|---|---|
| BR-BS-01 | **The material's type** (D-AC-04): a `secret` not starting `soorma_rs_` is refused (`unsupported_material`) | PF §8b; TC-AC-022 |
| BR-BS-02 | **Parse** with `parseRegistrationSecret` (D-AC-19): a malformed value is refused (`malformed_secret`) before any store read of the registration or secret; the digest is computed for a parsed value before the read (D-AC-34) | U5 NFR-AR-03 |
| BR-BS-03 | **The seam's agent half** (D-AC-20): the registration `agent` in E, and the secret record by its `id`, which must be **`active` and of that registration, in E**. Absent registration (`unknown_registration`), absent record (`unknown_secret`), a record of another registration (`unknown_secret`), not `active` (`secret_not_active`), or a mismatch through `registrationSecretMatches` (`secret_mismatch`). Never iterates a registration's secrets | PF FR-009; U5 obligations; TC-AC-007, 014 |
| BR-BS-04 | **The registration's state** is `registered` (PF FR-009, "non-retired"); M1 reaches no other state; checked anyway (`registration_not_registered`) | PF FR-009, §9 |
| BR-BS-05 | **The agent is not revoked** (logical-agent granularity), read directly (D-AC-01) (`agent_revoked`). A read failure: `unavailable` (503), settled as a failure | PF FR-009 ("non-revoked"), §9; D-AC-16 |
| BR-BS-06 | **Then the write** (one transaction): a credential record (new `cid`; E; agent; instance; the secret record's `id`; issued-at; lineage end = issued-at + M; expiry = min(issued-at + L, lineage end)) and its attribution record (BR-AT-AC). Then the token is minted with E's **agent** key ring. Any failure: `unavailable`, nothing written | PF FR-009; D-AC-02, 03, 14, 21 |
| BR-BS-07 | **The one refusal is uniform**: same status, code, body, and headers for every cause in BR-BS-01 to 05, so a caller cannot tell an unknown agent from a wrong secret, an inactive secret, or a revoked agent (PF §7a: revocation state "enumerates which agents exist") | D-AC-05; PF §7a |

## 6. The Agent Credential (BR-CR-AC)

| ID | Rule | Source |
|---|---|---|
| BR-CR-AC-01 | **Asserts** the logical agent, E's identity (all three parts), and the instance; plus `cid` and `jti` (D-AC-13). Nothing else: no permission, no sponsor, no secret reference | PF §7a, §3; D-AE-08 |
| BR-CR-AC-02 | **Minted and verified with E's agent key ring only** (D-AC-03). A token from E2 fails at its `kid` or signature before its expiry is read, so no expiry is disclosed (U4 BR-EC-03's rule) | PF §6; TC-AC-013, 020 |
| BR-CR-AC-03 | **Verification order** (NP-EHA-01's steps): prefix, length, syntax; header (`typ` `soorma-ac+jwt`, `alg` `Ed25519`, a `kid` E's agent ring holds); signature; every claim present and well typed; expiry, with no leeway (`credential_expired`, only after the signature verifies); `iat` at most U4's 30 seconds ahead; `env` equal to E's configured identity, field by field (O4). Any other failure: `credential_refused` | U4 NP-EHA-01; PF O1, O2, O4 |
| BR-CR-AC-04 | **Short-lived and renewable**: lifetime L; a lineage at most M (D-AC-02). L ≤ M, and B < L (NFR Requirements) | PF FR-010, §7a; D-AC-02 |
| BR-CR-AC-05 | **The record**: written at bootstrap; its expiry moved by renewal; otherwise never modified or deleted in M1. The app role may update only its expiry (NFR Design) | D-AC-14 |
| BR-CR-AC-06 | **Earlier tokens of a lineage stay valid until their own `exp`** (at most L). Liveness is the record's and revocation's, not the latest `jti` (§16) | U4's credential |

## 7. Renewal (BR-RN, steps 2 to 9)

| ID | Rule | Source |
|---|---|---|
| BR-RN-01 | **Presenter** (BR-PR-AC-03, 04), then **verification** (BR-CR-AC-03): O1, O2, O4 | PF FR-010, §11 |
| BR-RN-02 | **The record** by `cid` in E, uncached: it must exist and name the token's agent and instance; otherwise `credential_refused` (`no_record`, `record_mismatch`) | U4 BR-EC-02's pattern |
| BR-RN-03 | **O3 at both granularities**, read directly (D-AC-01): the `cid` revoked (`credential_revoked`) or the agent revoked (`agent_revoked`): `credential_refused`. A read failure: `unavailable` | PF FR-012, O3; TC-AC-009, 010 |
| BR-RN-04 | **The registration still `registered`**, else `credential_refused` (`registration_not_registered`): renewal is never weaker than issuance | PF FR-010 |
| BR-RN-05 | **Contract version** (step 5) and **no body** (step 6): a body is `malformed_request` | D-AC-28 |
| BR-RN-06 | **The new expiry** = min(now + L, the lineage end). The record's expiry becomes the later of its current value and the new one (concurrent renewals). The registration secret is **not** checked (D-AC-15) | D-AC-02, 15; PF FR-008 |
| BR-RN-07 | **Then the write** (one transaction): the record's expiry and the attribution record (BR-AT-AC); then a new token, same `cid`, agent, instance, and `env`, a new `jti`. Any failure: `unavailable`, nothing written | D-AC-14, 21 |
| BR-RN-08 | **The binding never changes and never widens** (TC-AC-016): the replacement asserts exactly what the presented token asserted, and its `exp` is never past the lineage end | PF FR-010 |
| BR-RN-09 | **A lapsed instance re-bootstraps**: an expired token is `credential_expired`, and nothing renews it (TC-AC-011) | PF FR-010, §9 |
| BR-RN-10 | **Steps 3 to 9 use `checkAgentRequest`** (D-AC-27) for presentation, O1, O2, O4, and O3 with the direct source; BR-RN-02, 04, 06 are S3's own | D-AC-27 |

## 8. Revocation (BR-RV) and the Cache (BR-RC)

| ID | Rule | Source |
|---|---|---|
| BR-RV-01 | **Two granularities**: a credential (`cid`), refusing that lineage; a logical agent, refusing every lineage of it and every future bootstrap | PF FR-011, §7a; D-AC-16 |
| BR-RV-02 | **Terminal**: nothing removes a revocation; reinstatement is a new bootstrap (a new `cid`), and for a revoked agent, none can succeed | PF FR-011 |
| BR-RV-03 | **Environment-scoped**: every revocation row carries E's three columns, and every read constrains on them. No global revocation list | PF §6, §9 *Isolation* |
| BR-RV-04 | **Readable by no principal**: no edge operation reads, lists, or reveals it; a revoked credential is plain `credential_refused` and a revoked agent at bootstrap the one refusal (TC-AC-018) | PF §7a, §8a |
| BR-RV-05 | **No product writer in M1** (D-AC-16): the app role holds `SELECT` only; tests seed it through a fixture using the owner role, outside the product's build | M1-FR-07; PF FR-011 (deferred) |
| BR-RV-06 | **The read writes no attribution record** (D-AC-17; TC-AC-019) | GAP-INT-009 |
| BR-RC-01 | **The cache answers** `revoked`, `not_revoked`, or **unknown → deny** (component-methods' `isRevoked`) for (E, `cid`, agent): `revoked` if either granularity is revoked | PF FR-012, O3 |
| BR-RC-02 | **Freshness**: a `not_revoked` answer is served while younger than B, its age from the issue of the read that produced it; at B it is re-read. A `revoked` answer is kept (terminal) | D-AC-18; NFR-AE-10 |
| BR-RC-03 | **Failure**: a failed read is never cached. With the store unreadable, an answer still younger than B is served; with none, or past B, the answer is unknown and the request is denied, `unavailable` (503, `Retry-After`) | PF FR-012, §9 *Revocation state unavailable* |
| BR-RC-04 | **Keyed on E and the target**; B is one value, platform-set, not tenant-configurable, the same value U3's term cache reads (NFR-AE-10). *Consistency fix from NFR Design (2026-11-12, Q1 A)*: B is **a constant in code**, `PROPAGATION_BOUND_MS` (formerly "configuration"), because a self-hosting deployer is typically the tenant (PF FR-012; NFR-AC-01) | PF FR-012, §6; I1 |
| BR-RC-05 | **Built and tested in P5 now; wired at S4 by U7** (D-AC-01). S3 does not use it | D-AC-01 |

## 9. Attribution (BR-AT-AC) and Failed Attempts (BR-FA)

| ID | Rule | Source |
|---|---|---|
| BR-AT-AC-01 | **Each successful bootstrap and renewal writes one record** through P7 (D-AC-21), in the same transaction as its credential write. U4 BR-AT-04 to 09 apply. Scope: E's configured identity. Actor `agent`: `registration` = the agent; `instance` = the asserted instance; `sponsor` = the registration's sponsor as resolved at the write (D-EHA-31); `credential` = the presented `cid` at renewal, none at bootstrap. Target: the credential (`cid`) | PF FR-025, §7b; M1-FR-12; TC-AC-005 |
| **BR-AT-AC-02** | **The record states why it has no chain, origin, or re-broadening, from the record alone** (the user's precision on P-12): its `operation` is `exchangeBootstrap` or `renewAgentCredential`, and **both are operations that never carry an envelope** (GAP-INT-008, option 1; the contract states it on both, D-AC-28). A reader who sees either operation knows the absence is by definition: there is no envelope to stamp a chain or origin from, and PF §8b's O12 excludes both. P7 holds the list of envelope-free agent operations and refuses envelope facts on them (D-AC-33) | GAP-INT-008; U4 obligation ("states why"); I4 |
| BR-AT-AC-03 | **Sponsorship is resolvable from the record**, and also through the registration (PF §7b, two hops), which is never deleted (D-AR-15) | PF §7b; I4 |
| BR-AT-AC-04 | **Refusals and the revocation read write no attribution record** (U4 BR-AT-09; D-AC-17) | U4; GAP-INT-009 |
| BR-FA-01 | **A Failed Bootstrap Attempt** is written for each failed or bound-refused attempt **on an existing registration in E** (D-AC-22): environment, agent, time, refused-by-bound, and an internal reason class. **Not** for an unknown agent: there is no registration to record it against (PF FR-027). The counter still bounds it (BR-AB-AC-01) | PF FR-027; TC-AC-007, 008, 022 |
| BR-FA-02 | **Off the response path**: queued, batched, and written by U2's writer pattern, which itself inserts only when the registration exists, so neither the response nor its timing says whether it does. A full queue or a failed batch drops records and reports the drop; the bound lives in the counters, not these records | U2 P-11, NFR-OI-21 |
| BR-FA-03 | **Nothing presented is in it**: no secret, secret `id`, or digest; no instance identifier from a failed attempt | SECURITY-03; NFR-AR-04 |

## 10. Refusals and the Check Order (BR-RF-AC)

| Step | `exchangeBootstrap` | `renewAgentCredential` |
|---|---|---|
| 1 | Body size: `payload_too_large` | same |
| 2 | BR-PR-AC-02: any credential header, `malformed_request` naming it | BR-PR-AC-03, 04: one `soorma_ac_`, else `credential_refused` |
| 3, 4 | — | BR-CR-AC-03 (O1, O2 `credential_expired`, O4); BR-RN-02 record; BR-RN-03 O3 (`credential_refused`; `unavailable`) |
| 5 | Contract version | same |
| 6 | BR-BQ-01 schema | BR-RN-05: no body |
| 9 | BR-AB-AC-01 `too_many_attempts`; BR-BS-01 to 05, each the one refusal `authentication_failed`; BR-BS-05 read failure `unavailable` | BR-RN-04 `credential_refused`; BR-RN-06 the expiry |
| write | Credential record and attribution record; any failure `unavailable` | Expiry and attribution record; any failure `unavailable` |

Steps 7, 8, and 10 do not apply: no envelope (D-AC-28). O12 does not apply (PF §8b).

| ID | Rule | Source |
|---|---|---|
| BR-RF-AC-01 | **Specific for validation, generic for trust**: `malformed_request` names a field or header; `authentication_failed`, `credential_refused`, `credential_expired`, `too_many_attempts` name nothing | U1 BR-ERR-01 |
| BR-RF-AC-02 | **No response discloses another environment, whether an agent exists, or revocation state** (BR-BS-07; BR-RV-04) | PF §6, §7a |
| BR-RF-AC-03 | Every refusal is a security-log event with its internal reason: `unsupported_material`, `malformed_secret`, `unknown_registration`, `unknown_secret`, `secret_not_active`, `secret_mismatch`, `registration_not_registered`, `agent_revoked`, `credential_revoked`, `no_record`, `record_mismatch`, `bound_refused`, `store_unavailable`, and U4's token reasons (`malformed`, `header`, `unknown_key`, `signature`, `claims`, `expired`, `issued_ahead`, `wrong_environment`). It names the agent and E; never the secret, its `id`, its digest, or a token | SECURITY-03; D-AC-26 |
| BR-RF-AC-04 | `unavailable` and `too_many_attempts` carry `Retry-After`; a renewal 401 carries `WWW-Authenticate: Bearer`; bootstrap never returns 401 (it names no scheme; `errors.md`) | U1 BR-ERR |

## 11. Problem Emission (BR-PE)

U3's BR-PE applies unchanged (D-AC-25). P1's Problem table needs no new code: `authentication_failed`
is widened (§13). S3's tests run the shared assertion on every Problem.

## 12. Two Faces, Packaging, and the Dependency Closure

- **I6**: both operations are data-face operations on S3, in `contract/data-gateway.openapi.yaml`.
  S3 serves no control-face operation and accepts no human credential (D-AC-10); S2 still serves
  no `soorma_ac_`. S3 has its own NFR configuration (PF §9)
- **I8**: every capability U6 builds is assigned to core by PF §12 (the bootstrap exchange,
  renewal, the revocation read and its bound, the abuse-resistant bootstrap, the identity seam's
  agent half). Not built, in any form: revocation initiation (PF FR-011, core, deferred), secret
  rotation and retirement (core, absent), anything commercial. The test-only seeding fixture is
  outside the product's build (BR-RV-05)
- **Closure** (D-AC-11): S3's production dependency closure excludes `@soorma/org-identity` and
  `@soorma/identity-resolution` (P6's human half); D-AC-08, 12 make that possible

## 13. Contract Changes

Made at U6's Code Generation, under contract `0.1.0` (unreleased), and recorded in
`contract/CHANGELOG.md`.

| Change | Where | Classification |
|---|---|---|
| **A new surface document**, `contract/data-gateway.openapi.yaml`: `POST /agent-credentials` (`exchangeBootstrap`, no scheme) and `POST /agent-credentials/current/renewal` (`renewAgentCredential`, `agentCredential`), each referencing the shared components, validating every input (adding-an-operation.md), stating that it carries **no envelope** (GAP-INT-008), and marking the response not cacheable | the document; generated types | Compatible: a new surface |
| **`authentication_failed` widened**: "every failure to authenticate a human … **or an agent instance at bootstrap**" (D-AC-05) | `conventions/errors.md` | Compatible: the code set is open; the code's meaning for humans unchanged |
| **`identifiers.md` clarified** (D-AC-07): an instance identifier is the agent's assertion, recorded and never enforced unique; two live credentials may assert the same one | `conventions/identifiers.md` | Compatible: a statement |
| **The propagation bound published** (its value from NFR Requirements): revocation reaches every request within B, and past B with revocation state unreadable a request is denied (PF §17). *Consistency fix from NFR Requirements (2026-11-12, NFR-AC-05, the user's precision on P-08)*: **B (60 s) is published as the platform's bound; L and M as upper bounds only**; the contract states that clients schedule renewal from the response's `expiresAt`, re-bootstrap when renewal answers `credential_expired` at the end of the credential's lifetime, and never hard-code L or M, so L and M can change without a contract break | `conventions/credentials.md`, a *Revocation and Lifetimes* section | Compatible: a statement |
| `credentials.md` already defines `soorma_ac_`, `soorma_rs_` (body only), and bootstrap naming no scheme. No change | — | — |

## 14. Amendments and Corrections

| Document | Change | Decision |
|---|---|---|
| `packages/attribution` (U4's code) | The closed list of envelope-free agent operations, and the writer's refusal of envelope facts on them, with the store's CHECK repeating it. **No U4 or U5 assertion changes**: U4's record test writes an agent record for `exchangeBootstrap` without an envelope (still accepted) and its refusal cases use `grantToHuman`; U5's constructed record uses another operation, without an envelope (still accepted). Class 1 under the standing rules | D-AC-33 |
| `packages/abuse-bound` (U2's manifest) | `@soorma/org-identity` to `devDependencies`; no code or test change | D-AC-12 |
| `inception/application-design/components.md`, P5, P6 | Correction notes: P5's agent kind is signed with **its own** key ring (D-AC-03); P6 is two packages, `identity-resolution` (human) and `agent-identity` (agent) (D-AC-08); S3 reads revocation directly and the cache serves S4 (D-AC-01) | D-AC-01, 03, 08 |
| `inception/application-design/component-methods.md`, S3, P1, P5, P8 | Correction notes: `exchangeBootstrap` takes `{ agent, secret, instance }` and no environment (D-AC-09); P1 gains `checkAgentRequest` with a caller-passed revocation source (D-AC-27); P5's `isRevoked` covers both granularities (BR-RC-01); P8's `admit` keys on the presented agent, known or not (D-AC-06) | D-AC-06, 09, 27 |

## 15. Misuse Cases (SECURITY-11)

| Misuse | Rule that defeats it |
|---|---|
| Guessing a registration secret at the edge | BR-AB-AC: the bound per agent; 256 random bits (U5); one record by `id`, constant-time compare |
| Enumerating which agents exist in E | BR-BS-07: one uniform refusal; BR-AB-AC-01: the bound applies known or not; BR-FA-02: failed-attempt writes off the response path |
| Aiming attempts at another agent's bound slot | BR-AB-AC-03: HMAC under E's counter secret |
| Bootstrapping a revoked agent | BR-BS-05: refused, and terminal (BR-RV-02) |
| Escaping a credential revocation by renewing | D-AC-14: the `cid` survives renewal; BR-RN-03 reads directly |
| Renewing forever with a stolen credential | D-AC-02: the lineage ends at M |
| Widening a credential at renewal (another instance, agent, or environment) | BR-RN-08: the binding is copied, never taken from the request |
| A human credential at the data gateway | BR-PR-AC-04: refused by kind, unverified |
| Minting a human environment credential from a compromised S3 | D-AC-03: S3 holds the agent key only |
| Using E's credential or secret in E2 | BR-CR-AC-02, D-AC-32: E2's keys and store know neither |
| A revocation-state outage, hoping for fail-open | BR-RN-03 (`unavailable`); BR-RC-03 (deny past B) |
| Reading revocation state through an error or timing | BR-RV-04; BR-BS-07 |
| Smuggling an envelope or a stamped field into bootstrap | BR-BQ-01: the body is closed |
| Flooding bootstrap with a valid secret | D-AC-29: S3's throttle; a residual (§16) |
| A secret, digest, or token in a log or failed-attempt record | BR-RF-AC-03; BR-FA-03 |

## 16. Accepted Residuals

| Residual | Bound | Decision |
|---|---|---|
| **The lockout** (the user's wording): **an outsider who knows an agent's identifier can stop its new instances from starting for the window, while running instances renew unaffected** | The bound's window and backoff cap (NFR Requirements); renewal is credentialed and outside the bound; the mitigation is carried to the first hosted deployment (§17) | D-AC-06, with the user's addition |
| **A holder of a valid secret can bootstrap as often as S3's throttle allows**; each success writes a credential record and an attribution record | S3's per-instance throttle only, in M1; per-registration issuance limits to the first hosted deployment | D-AC-30 (P-21) |
| **An earlier token of a lineage stays valid until its own `exp`** after renewal | At most L | BR-CR-AC-06 |
| **A stolen agent credential works until its lineage ends** unless revoked, and **M1 has no revocation initiation** (PF FR-011 deferred) | At most M from its bootstrap | D-AC-02 |
| **A stolen registration secret works until the stack is re-created**: M1 cannot retire a secret (PF FR-008 rotation and retirement absent) | Each secret names its issuer (U5); the cap of 10 per registration | U5 §16; M1-FR-04 |
| **A revocation is invisible at S4 for up to B** (U7) | B, published | PF FR-012, §17 |
| **Two instances may share an asserted name**; attribution records name the asserted instance only | By design: asserted, not verified (PF FR-009; I10) | D-AC-07 |

## 17. Forward Obligations

Posted on each unit's issue when this stage is approved.

| To | Obligation |
|---|---|
| **U6 NFR Requirements** | **B**, the propagation bound (one value; also U3's term-cache TTL, NFR-AE-10); **L**, the agent credential's lifetime; **M**, a lineage's maximum age (L ≤ M, B < L); the bootstrap bound's shape and values (window, live attempts, backoff), with the lockout residual (§16) stated beside them; S3's throttle values; the latency budget per class (the revocation read; exchange and renewal) |
| **U6 NFR Design** | Tables in `env-store`'s sequence: the agent credential (a sibling of `credentials` or its extension), revocation state, the bound's slots, failed bootstrap attempts, every row with E's three columns; privileges (revocation `SELECT` only; the credential's expiry the only update); the cache's physical form (per key, or a periodic snapshot of E's set); `packages/agent-identity`; P8 generalised over its subject; the closure test; P7's envelope-free list and its CHECK (D-AC-33), **in a new migration; `0001` and `0002` untouched** (the user's, at approval); the agent key ring's loading and rotation |
| **U6 Infrastructure Design** (expected to run) | S3 per environment in Compose (E, E2): network, port, health, migrations; the new secrets per environment (the agent signing key, D-AC-03; the bound's counter secret, D-AC-06); **U4's Compose-model rules applied to S3's services, rendering with every profile** (the user's rule 4); TC-AC-017 (S1 stopped) |
| **U6 Code Generation** | The contract changes (§13); P7's list (D-AC-33, class 1); P8's manifest (D-AC-12); the closure test; *done when* 2 by raw calls in `e2e/`; the test-only revocation fixture outside the product's build |
| **U7 (soorma-core#10)** | **Wire P5's cache at S4 with B** (D-AC-01); S4 verifies agent credentials with **agent verify keys only** (D-AC-03); **use `checkAgentRequest`** with the cached source (D-AC-27); revocation at either granularity refuses every request within B, and past B with the store unreadable denies (TC-AC-009, 010, 015 at S4). **P7's envelope-bearing agent operations**: U7 defines them (publish, subscribe) and decides whether P7's check becomes closed in both directions (an agent record for any other operation must carry envelope facts). If it does, U5's constructed record in `services/control-gateway/test/registration.test.ts` (operation `constructedAgentOperation`, no envelope) is affected, and that change goes through the standing rules |
| **The first hosted deployment** | **The user's Q6 addition: the secret-record mitigation.** An attempt carrying a real secret `id` is counted against that secret record, so legitimate restarts are not blocked by an outsider who knows only the agent's identifier. Also: per-registration issuance limits on bootstrap (§16) |
| **The slice that builds revocation initiation** (PF FR-011; not M1) | A product writer for revocation state at both granularities (`credential:revoke`; Admin or sponsoring Developer); the app role's privilege on it; the cache's terminal `revoked` answers; the propagation bound as published |
| **The slice that builds secret rotation and retirement** (PF FR-008; not M1) | Retiring a secret stops future exchanges only; live credentials expire or are revoked separately (FR-008), which renewal already honours (D-AC-15). The credential record names its bootstrapping secret, if that slice needs it |
| **Build and Test** | *Done when* 2 run in full by raw calls; TC-AC-017 with the organization level stopped; the misuse cases (§15) as tests; the residuals (§16) stated |

## 18. Specification Gaps

| Gap | Status | Effect |
|---|---|---|
| (none raised in U6) | — | Q1 to Q9 classified as technology |
| GAP-INT-008 (inherited) | Open, soorma-prd#27 | Worked around: neither operation carries an envelope (D-AC-28); attribution states why through the operation (BR-AT-AC-02) |
| GAP-INT-009 (inherited) | Open, soorma-prd#28 | Worked around: the revocation read writes no attribution record (D-AC-17) |
