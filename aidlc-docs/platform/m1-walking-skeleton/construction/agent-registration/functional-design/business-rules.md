# Business Rules: U5 `agent-registration`

**Unit**: U5 `agent-registration` (soorma-core#8). Control face, environment level. Adds
`registerAgent` and `issueRegistrationSecret` to S2 `control-gateway`
**Built against**: PF @ `prd-platform-foundations-v1.3` (the main source), ID @ `prd-identity-v1.0`
**Decisions from**: the Functional Design plan, Q1 to Q6 and proposals P-01 to P-19, answered
2026-11-11T21:50:31Z (recorded verbatim in `audit.md`). P-03 accepted with the user's condition
(D-AR-07); P-08 recorded as following PF §8a (D-AR-12)
**Entities**: [domain-entities.md](domain-entities.md). **Logic**:
[business-logic-model.md](business-logic-model.md)
**Inherited rules**: U1's credential, identifier, versioning and error rules
(`construction/wire-contract/functional-design/business-rules.md`: BR-CR, BR-ID, BR-VER,
BR-ERR); U3's seam, the human-only class, the agent-facts port, and Problem emission
(`construction/authority-evaluation/`: BR-SEAM, D-AE-03, D-AE-09, NP-04, BR-PE); U4's presenter
matrix, environment-credential checks, human authority, accepted identifiers, attribution, and
check order (`construction/env-human-access/functional-design/business-rules.md`: BR-PR, BR-EC,
BR-EV, BR-ACC, BR-AT, BR-RF, D-EHA-14, 17, 18, 29, 30). This document does not restate them
except where U5 extends them
**Specification gaps**: **none found in U5**. Inherited: GAP-INT-006 (Open, soorma-prd#24; standing
sets accept plane-declared identifiers only, BR-ACC). GAP-INT-004 and GAP-INT-005 resolved
(recorded for traceability)

Module names are the Application Design's: P1 `perimeter`, P3 `authority`, P4 `registry`, P7
`attribution`, P9 `config`, P11 `policy-decision`.

---

## 1. Decisions

| ID | Decision | Source | Class |
|---|---|---|---|
| **D-AR-01** | **Who may issue a registration secret** (R1): the presenter holds **`agent:register` in E**, and is either **the registration's sponsor** or **an Admin in E**, where Admin means a holder of **`grant:human` and `human:manage`** in E (ID §3). Decided in P3 from one read (D-AR-07). A Developer's reach is the agents they sponsor (PF §11) | Q1 A; PF §8a, §10, §11; ID §3 | **Specified** (answered by ID §3 with PF §8a); no gap |
| **D-AR-02** | **The client chooses the logical agent's identifier** (`agent`, required; `LogicalAgentIdentifier`). It is also the registration's reference. A second registration with the same `agent` in E is refused with **`registration_exists`** (409, `errors[]` with one entry, `pointer` `/agent`), decided at the write, after authority and the ceiling, so only a holder of `agent:register` whose request is otherwise valid learns that an identifier is taken. A retried request after a lost response gets `registration_exists`, not a second agent. Identifiers are tenant data: they appear in chains and logs as given, never as platform constants (I9) | Q2 A; U1 BR-ID-02 | Technology |
| **D-AR-03** | **Three new codes for the registration-specific rejections**, each with `errors[]` pointers, ordered by pointer, at most 10: **`human_only_permission`** (400, step 6): each standing entry in the human-only class; **`declaration_outside_standing`** (400, step 6): each declared entry not in the standing set; **`exceeds_sponsor_ceiling`** (403, step 9, after `agent:register` passes): each standing entry the presenter does not hold. The last discloses only the caller's own held set, to the caller. All compatible: the code set is open | Q3 A; PF §10; TC-AR-009 ("citing the ceiling") | Technology |
| **D-AR-04** | **A registration may hold several active secrets.** Each issuance creates an independent active secret with its own record and issuer; bootstrap (U6) accepts any active secret of the registration. **The cap on active secrets per registration, and the refusal when it is reached, are set at NFR Requirements.** A lost secret is recovered by issuing another | Q4 A; PF §7a v1.3; ID FR-026 ("every active secret whose issuer is the human") | Technology |
| **D-AR-05** | **An unknown registration** on issuance is **`unknown_registration`** (400, `errors[]` with one entry, `pointer` `/registration`), to any holder of `agent:register` in E. A registration that exists, where the presenter is neither its sponsor nor an Admin, is **`forbidden`**. Consistent with D-AR-02, where an identifier's existence is already learnable by `registerAgent` | Q5 A; TC-AR-017 | Technology |
| **D-AR-06** | **The standing set is recorded on the registration only.** The registration is the agent's grant (PF §7a *Permission Grant*, agent-principal form): principal = `agent`, scope = E, set = `standingPermissions`, granted-at = `registeredAt`, granted-by = `sponsor`. The agent-facts query reads one row per agent. U4's Grant record stays human-only | Q6 A; PF §7a | Technology |
| **D-AR-07** | **One read, one evaluator.** Each operation reads the presenter's held set **once** (P11 over P4's uncached human `GrantSource`). **U4's `evaluateHuman` is refactored to take an already-read held set**: its evaluating step becomes **`evaluateHeld({ policy, held, required })`**, the one evaluator, and `evaluateHuman` becomes "read, then `evaluateHeld`", with its signature and behaviour unchanged. A new P3 function, **`readHumanAuthority`**, reads once and returns the Human Authority (domain-entities), whose `allows` **is** `evaluateHeld` over that set; the ceiling, the `agent:register` check, and the Admin test all go through it. **This keeps U4's obligation ("call `evaluateHuman(agent:register)`") in substance**: the same code path decides `agent:register`, in P3, over the same uncached read; only the read is shared rather than repeated, so the snapshot is exactly the set the check judged. No second implementation of a human's evaluation exists | P-03 with the user's condition; I5; U4 BR-EV-04, D-EHA-13, 14; PF FR-016 ("at the moment of granting") | Technology |
| D-AR-08 | **Presenter at S2** (U4 BR-PR extended): `soorma_ec_` is accepted on `registerAgent` and `issueRegistrationSecret`. `soorma_si_`, `soorma_ac_`, `soorma_dc_`, any other prefix, or two credentials: `credential_refused`, by kind, without verifying. So **registration and issuance by an agent are refused** (TC-AR-016) | P-01; ID §8b *Entry points*; requirements *Absent from M1* | Technology |
| D-AR-09 | **The sponsor is always the presenting human.** The request names no sponsor; the closed schema refuses a body that does (`malformed_request`). Who may sponsor, and whether the sponsor may differ from the registrant, is commercial | P-02; PF §3 *Separation of Duties*, FR-007, §12; ID §1 trace step 6 | Technology |
| D-AR-10 | **The human-only refusal and declaration ⊆ standing are computed in P3**: the class is P3's `HUMAN_ONLY_PERMISSIONS` (D-AE-03), imported, never copied; containment is the seam's `contains`, because what containment means belongs to the permission model (PF FR-019). P4 and S2 compare no permission sets | P-04; D-AE-03; PF FR-018, FR-019; I5 | Technology |
| D-AR-11 | **The ceiling snapshot is the whole held set** as read (D-AR-07), human-only permissions included, stored as a set and never recomputed (TC-AR-002, 019) | P-05; PF §7a, FR-016 | Technology |
| D-AR-12 | **Standing permissions are granted at registration, as PF §8a's row *Grant standing permissions at registration* states.** PF §10's row *Grant standing permissions* is the same operation. `registerAgent` performs both, and nothing is deferred. So no M1 operation changes a registration after it is written, and NFR-AE-16's staleness note is not triggered by U5 | P-08, as recorded by the user; PF §8a, §10, FR-016 | Technology |
| D-AR-13 | **An unreadable held set** (PF §10, *Sponsor's held set unresolvable*: "Rejected") is `unavailable` (503, `Retry-After`), and nothing is written (TC-AR-021). In M1 it cannot be unresolvable otherwise: the sponsor is the presenter, verified at steps 3 and 4 | P-06; PF §10; SECURITY-15; U4 BR-EV-06 | Technology |
| D-AR-14 | **The request's sets**: `standingPermissions` 0 to 32, unique (empty allowed: the bottom element); `reBroadeningDeclaration` 0 to 32, unique, optional, **default empty**; `autonomyDeclared` optional, **default `false`**. A duplicate: `malformed_request`. Every identifier in either set must be accepted (BR-ACC): `unknown_permission`, pointers `/standingPermissions/{i}` and `/reBroadeningDeclaration/{i}`, ordered, at most 10 | P-07; PF §7a, FR-017; L3; U4 D-EHA-06 | Technology |
| D-AR-15 | **A registration is never modified or deleted in M1**; nor is a secret. The app role holds no `UPDATE` or `DELETE` on either (physical form: NFR Design) | P-09; PF FR-013; D-AE-09 | Technology |
| D-AR-16 | **The secret**: `soorma_rs_`, at most 256 characters, **returned exactly once**; the record holds verification material only; issuer = the presenter; state `active`. Entropy, encoding, and the verifier are NFR Requirements'. *Added at approval (2026-11-11)*: the value carries its record's `id` and at least 256 random bits, and the stored verification material is a fast hash, not a slow password hash (§17). No log line, attribution record, or error carries it | P-10; PF §7a v1.3; ID FR-026; SECURITY-03, 12 | Technology |
| D-AR-17 | **Attribution**: one record per operation through P7, human actor (principal and `environmentCredential` presented), scope E, no chain, origin, or re-broadening. Operations `registerAgent`, `issueRegistrationSecret`; **target the registration** for both | P-11; PF FR-025, §10; ID §7b; U4 obligation | Technology |
| D-AR-18 | **One transaction per operation**: the registration (or secret) and its attribution record commit together. Any failure writes nothing and is `unavailable`; a uniqueness conflict on `agent` is `registration_exists` and writes nothing | P-12; U4 D-EHA-17; SECURITY-15 | Technology |
| D-AR-19 | **The agent-facts query**: one statement for a list of agents in one environment, constrained on all three environment columns, returning each found agent's `autonomyDeclared`, `reBroadeningDeclaration`, and `standingPermissions`; an agent not returned is not found; a failure rejects the whole call. U3's decorator caches only found agents, so **a new registration is visible to U3 at once** | P-13; U3 NP-04, NFR-AE-12; I1 | Technology |
| D-AR-20 | **No read surface** for registrations or secrets: PF §8a assigns none, so building one would put an unassigned capability in core (I8). Core's read of the ceiling snapshot is FR-025's grant-scoped attribution read, "readable by a holder of the attribution grant" (PF §12, *Recording versus exploiting*), which is absent from M1. *Done when* 1's raw-call proof reads `registerAgent`'s response; attribution is checked in the store in tests | P-14; I8; PF §12 | Technology |
| D-AR-21 | **Coverage** (ID FR-014): both operations' effects are confined to E; authority is required in E only | P-15; ID FR-014 | Technology |
| D-AR-22 | **Responses**: `200` for both, each naming the `environmentCredential` scheme only. `registerAgent` returns the registration (domain-entities, every attribute and `state`), `sponsor` as `HumanPrincipalReference`; `issueRegistrationSecret` returns `{ id, registration, secret, issuedAt }` | P-16; U4 D-EHA-22, 25 | Technology |
| D-AR-23 | **Problems through P1** (`problemResponse`); S2's tests run `assertProblem` on every Problem, the five new codes included | P-17; U3 BR-PE; U4 D-EHA-21 | Technology |
| D-AR-24 | **Refusals are security-log events, not attribution records**, with an internal reason (BR-RF-AR-03), the human named only by E's log pseudonym | P-18; U4 D-EHA-18 | Technology |
| D-AR-25 | **A secret's `id`** has at least 128 random bits, unique within E. The registration's identifier is the client's (D-AR-02) | P-19; U4 D-EHA-30 | Technology |
| D-AR-26 | **Concurrent registrations of one `agent`**: the store's uniqueness on (organization, project, environment, `agent`) decides; the loser is `registration_exists` and writes nothing, its attribution record included. Tested with two at the same time | Made at design, from D-AR-02 and D-AR-18 | Technology |
| D-AR-27 | **The sponsor test is exact**: the presenter's `{ organization, principal }` equals the registration's `sponsor`, both parts compared exactly (BR-ID-08). The presenter's organization is E's | Made at design; U1 BR-ID-08 | Technology |

---

## 2. Presenter (BR-PR-AR, step 2)

| ID | Rule | Source |
|---|---|---|
| BR-PR-AR-01 | U4 BR-PR-01, 06, 07 apply unchanged | U4 |
| BR-PR-AR-02 | `soorma_ec_` is accepted on `registerAgent` and `issueRegistrationSecret`, verified per U4 BR-EC-02 (E's own material; expiry; O4; O3, uncached) | D-AR-08 |
| BR-PR-AR-03 | `soorma_ac_` (an agent registering or issuing), `soorma_si_`, `soorma_dc_`, any other prefix: `credential_refused` by kind, without verifying | D-AR-08; TC-AR-016 |

## 3. The Registration Request (BR-RQ, step 6)

| ID | Rule | Source |
|---|---|---|
| BR-RQ-01 | **The body**, closed: `{ agent: LogicalAgentIdentifier, standingPermissions: [PermissionIdentifier], reBroadeningDeclaration?: [PermissionIdentifier], autonomyDeclared?: boolean }`. Bounds per D-AR-14. Any schema failure, a duplicate or an extra field (a `sponsor` included) among them: `malformed_request` with pointers | D-AR-09, 14; SECURITY-05 |
| BR-RQ-02 | Then **accepted identifiers** over both sets (BR-ACC): `unknown_permission` | D-AR-14; GAP-INT-006 |
| BR-RQ-03 | Then **the human-only class** over `standingPermissions` (P3, Registration Request Check): `human_only_permission`, whatever the presenter holds | PF FR-016, §8b; ID FR-013; D-AR-03, 10; TC-AR-010, 011 |
| BR-RQ-04 | Then **declaration ⊆ standing** (P3, the seam's `contains`): `declaration_outside_standing` | PF FR-017, §7a; D-AR-03, 10; TC-AR-012 |
| BR-RQ-05 | Omitted `reBroadeningDeclaration` is the empty set; omitted `autonomyDeclared` is `false`. Re-broadening and autonomy are never implicit | PF §7a; TC-AR-003, 005 |

The step-6 codes are decided before any state is read, so a caller without `agent:register`
can learn only what the public accepted set and the human-only class already say.

## 4. Authority and the Ceiling (BR-SP, step 9)

| ID | Rule | Source |
|---|---|---|
| BR-SP-01 | **One read**: `readHumanAuthority(presenter, E)` (D-AR-07). A read failure: `unavailable` (D-AR-13) | D-AR-07, 13 |
| BR-SP-02 | **`allows({ agent:register })`**: else `forbidden` (TC-AR-014) | PF §8a; D-AR-07 |
| BR-SP-03 | **The ceiling**: when `standingPermissions` is non-empty, `allows(standingPermissions)`; else `exceeds_sponsor_ceiling`, pointing at each entry in `exceeding(standingPermissions)`. An empty standing set is within any held set (TC-AR-009, 018) | PF FR-016, §8a, §8b; D-AR-03 |
| BR-SP-04 | **Checked once, at registration, never per request.** Nothing re-reads the sponsor's set for the agent later (PF §8b *Sponsorship*) | PF FR-016, §8b |
| BR-SP-05 | **The snapshot** is `snapshot()` from the same read, written with the registration (D-AR-11) | PF §7a; TC-AR-002 |
| BR-SP-06 | **Read-your-writes**: a grant made to the presenter on an earlier request counts at once, because the held set is read uncached (U4 D-EHA-14). H's self-grant of `agent:register` is usable on the next request | PF §10, ID §10 |
| BR-SP-07 | **No module but P3 tests a held set**: S2 and P4 call `readHumanAuthority` and its members only, and `evaluateHuman` and `evaluateHeld` remain the only evaluators of a human's authority (I5) | D-AR-07; U4 BR-EV-04 |

## 5. The Registration Write (BR-RG)

| ID | Rule | Source |
|---|---|---|
| BR-RG-01 | One registration record (domain-entities): `agent`; E's configured identity; `sponsor` = the presenter; `ceilingSnapshot`; `standingPermissions`; `reBroadeningDeclaration`; `autonomyDeclared`; `registeredAt`; `state` = `registered`. With its attribution record, in one transaction (D-AR-18) | PF §7a, FR-007; TC-AR-001 |
| BR-RG-02 | `agent` taken in E: `registration_exists` (D-AR-02, 26). Uniqueness is per environment only: the same `agent` in E2 is another registration | PF §6, §7a; identifiers.md |
| BR-RG-03 | Never modified, never deleted (D-AR-15) | PF FR-013 |
| BR-RG-04 | Two registrations by one sponsor are independent: each has its own record and snapshot (TC-AR-008) | ID §1 trace steps 6 to 8 |

## 6. Secret Issuance (BR-SE)

| ID | Rule | Source |
|---|---|---|
| BR-SE-01 | **The body**, closed: `{ registration: LogicalAgentIdentifier }`. Schema failures: `malformed_request` | SECURITY-05 |
| BR-SE-02 | **One read** (BR-SP-01); then `allows({ agent:register })`, else `forbidden` (TC-AR-015) | PF §8a; D-AR-07 |
| BR-SE-03 | Then **the registration** in E: absent, `unknown_registration` (D-AR-05; TC-AR-017). A store failure: `unavailable` | D-AR-05 |
| BR-SE-04 | Then **sponsor or Admin** (D-AR-01): the presenter equals the `sponsor` (D-AR-27), **or** `allows({ grant:human, human:manage })`. Else `forbidden` | PF §8a, §10, §11; ID §3 |
| BR-SE-05 | Then **one secret record** (domain-entities), issuer = the presenter, with its attribution record, in one transaction. The value is generated, its verification material stored, and **the value returned once** | PF §7a v1.3, FR-008; ID FR-026; TC-AR-006, 020 |
| BR-SE-06 | **Several active secrets** may exist for one registration, up to NFR Requirements' cap (D-AR-04). Issuing one changes no other secret and no credential | PF FR-008 (independent lifecycles) |
| BR-SE-07 | The secret never appears in a log, an attribution record, an error, or any response but its issuance | SECURITY-03, 12 |

## 7. Agent Facts (BR-AF)

| ID | Rule | Source |
|---|---|---|
| BR-AF-01 | P4 implements `AgentFactsSource.load(environment, agents)` with **one query**, per D-AR-19 | U3 NP-04 |
| BR-AF-02 | Every row returned matches the environment's three columns; an agent of E2 with the same identifier is never returned for E | I1; PF §6 |
| BR-AF-03 | All or nothing: a failure rejects the call, and U3 answers `unavailable` | U3 BR-AU-09 |
| BR-AF-04 | Registrations are never deleted, so an agent that has ever been registered in E is always found (D-AE-09) | PF FR-013 |

## 8. Attribution (BR-AT-AR)

| ID | Rule | Source |
|---|---|---|
| BR-AT-AR-01 | Each operation writes one record through P7 (D-AR-17), in the same transaction (D-AR-18). U4 BR-AT-02, 05, 06, 08, 09 apply | PF FR-025; U4 BR-AT |
| BR-AT-AR-02 | **Sponsorship is resolvable from any agent record**: actor → instance → logical agent → the registration's `sponsor` (PF §7b, two hops), because the registration is never deleted. U6 and U7 also write the resolved sponsor on agent records (U4 D-EHA-31) | PF §7b; I4 |
| BR-AT-AR-03 | Both registrations of *done when* 1 are attributed to H, with no origin mode (ID §1 trace step 9; TC-AR-007) | ID §7b |

## 9. Human Authority Refactor (BR-HA)

| ID | Rule | Source |
|---|---|---|
| BR-HA-01 | `evaluateHeld({ policy, held, required })`: `policy.contains(held, required)`, `required` non-empty (the U4 `RangeError` kept). The **one evaluator** of a human's held set | D-AR-07 |
| BR-HA-02 | `evaluateHuman(input)` = `grantedSet` once, then `evaluateHeld`. **Signature and results unchanged**: U4's tests of `evaluateHuman` and `holdsAnyGrant` stay as they are | D-AR-07; U4 BR-EV-01, 02 |
| BR-HA-03 | `readHumanAuthority({ policy, environment, principal })` = `grantedSet` once; returns the Human Authority whose `allows` calls `evaluateHeld` over that set, whose `exceeding` calls `allows({ p })` per entry, and whose `snapshot` returns the set as read | D-AR-07 |
| BR-HA-04 | No human-only refusal for a human (U4 BR-EV-03): `allows` never consults the class | ID FR-013, FR-015 |

## 10. Refusals and the Check Order (BR-RF-AR)

| Step | `registerAgent` | `issueRegistrationSecret` |
|---|---|---|
| 1 | Body size: `payload_too_large` | same |
| 2 | BR-PR-AR: a `soorma_ec_` | same |
| 3, 4 | U4 BR-EC-02 (verification, expiry, O4, O3) | same |
| 5 | Contract version (header) | same |
| 6 | BR-RQ-01 schema; BR-RQ-02 `unknown_permission`; BR-RQ-03 `human_only_permission`; BR-RQ-04 `declaration_outside_standing` | BR-SE-01 schema |
| 9 | BR-SP-01 read (`unavailable`); BR-SP-02 `forbidden`; BR-SP-03 `exceeds_sponsor_ceiling` | BR-SP-01 read; BR-SE-02 `forbidden`; BR-SE-03 `unknown_registration`; BR-SE-04 `forbidden` |
| write | Registration and attribution record; `registration_exists` on a taken `agent`; any other failure `unavailable` | Secret and attribution record; any failure `unavailable` |

Steps 7, 8, and 10 do not apply: no envelope (ID FR-022).

| ID | Rule | Source |
|---|---|---|
| BR-RF-AR-01 | **Specific for validation, generic for trust**: `malformed_request`, `unknown_permission`, `human_only_permission`, `declaration_outside_standing`, `unknown_registration`, `registration_exists` name a field; `exceeds_sponsor_ceiling` names the caller's own requested entries only (D-AR-03); `credential_refused`, `credential_expired`, `forbidden` name nothing | U1 BR-ERR-01 |
| BR-RF-AR-02 | **No response discloses another environment**, or whether a registration exists in another environment. Within E, whether an identifier is taken is learnable by a holder of `agent:register` (D-AR-02, 05; an accepted residual, §16) | U1 BR-ERR; PF §6 |
| BR-RF-AR-03 | Every refusal is logged as a security event with its internal reason: `ceiling_exceeded`, `human_only_in_standing`, `declaration_outside_standing`, `unknown_permission`, `authority_denied`, `not_sponsor_or_admin`, `unknown_registration`, `registration_exists`, `held_set_unreadable`, `store_unavailable`; never in a response. A human is named only by E's log pseudonym; no secret, token, or key in any log | SECURITY-03; D-AR-24 |
| BR-RF-AR-04 | `unavailable` carries `Retry-After`; a 401 carries `WWW-Authenticate: Bearer`; a 409 carries neither | U1 BR-ERR |

## 11. Problem Emission (BR-PE)

U3's BR-PE applies unchanged (D-AR-23). P1's Problem table gains the five codes (§13); S2's tests
run `assertProblem` on every Problem.

## 12. Two Faces and Packaging

- **I6**: both operations are control-face operations on S2 and live in
  `contract/control-gateway.openapi.yaml`. No data-face operation is added to S2, and S2 still
  serves no `soorma_ac_` (D-AR-08)
- **I8**: every capability U5 builds is assigned to core by PF §12 (registration, standing grant at
  registration, secret issuance). Nothing unassigned is built (D-AR-20). Not built, in any form:
  sponsorship policy (who may sponsor, registrant and role constraints; PF §12 commercial), secret
  rotation and retirement, suspend, resume, retire, and revocation (absent from M1)

## 13. Contract Changes

Made at U5's Code Generation, under contract `0.1.0` (unreleased), and recorded in
`contract/CHANGELOG.md`.

| Change | Where | Classification |
|---|---|---|
| **Two operations** in `contract/control-gateway.openapi.yaml`: `POST /registrations` (`registerAgent`, `environmentCredential`) and `POST /registration-secrets` (`issueRegistrationSecret`, `environmentCredential`), each referencing the shared components, naming one scheme, and validating every input (adding-an-operation.md). The secret's response is marked not cacheable (the header is NFR Design's) | the document; generated types | Compatible: new operations |
| **Five codes**: `human_only_permission` (400), `declaration_outside_standing` (400), `exceeds_sponsor_ceiling` (403), `registration_exists` (409), `unknown_registration` (400) | `ProblemCode` in `components.openapi.yaml`; `conventions/errors.md` (codes table; check order steps 6 and 9) | Compatible: the code set is open |
| **Check order text**: step 6 gains "for a registration, then the accepted identifiers, the human-only class, and declaration ⊆ standing"; step 9 gains "for a registration, then the ceiling, and at the write, a taken identifier; for a secret, then the registration, then sponsor or Admin" | `conventions/errors.md` | Compatible: documents new operations |
| **Disclosure**: a line stating that, within an environment, whether a logical agent identifier is taken is learnable by a holder of `agent:register` | `conventions/errors.md` *Disclosure* | Compatible: a statement |
| `credentials.md` already defines `soorma_rs_` (material, body only, at most 256 characters). No change | — | — |

## 14. Amendments and Corrections

| Document | Change | Decision |
|---|---|---|
| `packages/authority` (U4's code), `evaluateHuman` | **Refactored at U5's Code Generation**: `evaluateHeld` extracted as the one evaluator; `evaluateHuman`'s signature and results unchanged. **No U4 assertion changes** (the user's standing rule, class 1 or none); if one would, generation stops | D-AR-07; BR-HA-02 |
| `inception/application-design/component-methods.md`, S2 and P3, P4 | Correction note: `registerAgent` takes a **client-chosen** `agent` (the method's "if the contract allows" settled); `issueRegistrationSecret` names its registration in the body; P3 gains `evaluateHeld` and `readHumanAuthority`; P4 gains the registration and secret writes and the agent-facts query; P4's registration check uses P3, not its own comparison | D-AR-02, 07, 10, 19 |
| `inception/application-design/components.md`, P4 | Correction note: the human-only check and the ceiling are P3's, over the seam (U3 D-AE-03 already notes the class is P3's) | D-AR-10 |

## 15. Misuse Cases (SECURITY-11)

| Misuse | Rule that defeats it |
|---|---|
| An agent registers another agent, or issues a secret (absent from M1) | BR-PR-AR-03: `credential_refused` by kind |
| A Developer gives an agent more than they hold | BR-SP-03: `exceeds_sponsor_ceiling` |
| An Admin passes `grant:human`, `human:manage`, or `agent:delegate` to an agent they hold it for | BR-RQ-03: `human_only_permission`; and P3 refuses the class to any agent at evaluation (D-AE-03) |
| Declaring re-broadening beyond the standing set to widen later | BR-RQ-04; U3's `W = S ∩ P ∩ (U ∪ D)` also intersects with `S` |
| Widening autonomy by omission | BR-RQ-05: omitted is `false` |
| Naming another human as sponsor, to borrow their ceiling | BR-RQ-01, D-AR-09: no sponsor field |
| A Developer issuing a secret for someone else's agent, to run code as it | BR-SE-04: `forbidden` |
| Probing which agents exist in another environment | BR-AF-02, BR-RG-02: per-environment only; nothing crosses |
| Racing two registrations of one identifier | D-AR-26: one wins; the other writes nothing |
| A registration or secret write without its attribution record | D-AR-18: one transaction |
| A store outage, hoping the ceiling check is skipped | D-AR-13: `unavailable`, nothing written |
| Deleting a registration to break sponsorship resolution | D-AR-15: no `DELETE` privilege; no operation |
| Harvesting a secret from logs or a second read | BR-SE-07; no read surface (D-AR-20) |
| Flooding registrations or secrets | S2's per-instance throttle (U4 NFR-EHA) covers both; the secrets cap (D-AR-04) |

## 16. Accepted Residuals

| Residual | Bound | Decision |
|---|---|---|
| **Within E, a holder of `agent:register` can learn whether an identifier is taken** (`registration_exists`; `unknown_registration`) | Only such a holder, only in E, only after authority (and the ceiling, for registration) | D-AR-02, 05 (the user's answers) |
| **A registration made by mistake cannot be removed in M1** (retirement is absent and deletion never exists) | Its identifier is spent; it holds no secret until one is issued | D-AR-15; PF FR-013 |
| **Every active secret widens who may know a way in** | The cap (NFR Requirements); each secret names its issuer | D-AR-04 |
| **A lost secret's holder cannot be told apart from the agent** until retirement exists | Absent from M1 (PF FR-008 rotation and retirement) | M1-FR-04 |
| **A Developer may give an agent the whole of their non-human-only held set** | By design: the ceiling is the held set (PF FR-016) | PF §8b |

## 17. Forward Obligations

Posted on each unit's issue when this stage is approved.

| To | Obligation |
|---|---|
| **U5 NFR Requirements** | The secret's entropy, encoding within `soorma_rs_` and 256 characters, and its verification material; the cap on active secrets per registration and its refusal; S2's throttle over the two operations; registration durability (PF §10, the highest). **Added at approval (the user's, 2026-11-11)**: **each `soorma_rs_` value carries its secret record's `id`**, so bootstrap looks up and checks **exactly one** record, never every active secret of the registration: bootstrap is an unauthenticated surface (PF §10; M1-FR-05). **The value carries at least 256 random bits, so a fast hash of it is the stored verification material; no slow password hash.** **Infrastructure Design is decided at the end of NFR Requirements**: if the verifier needs a server-side key (for example, HMAC under a per-environment key), that key is a new secret delivered as a mounted file, and Infrastructure Design runs |
| **U5 NFR Design** | Tables, the uniqueness on (organization, project, environment, `agent`), column-level privileges (no `UPDATE` or `DELETE` on registrations or secrets); the agent-facts query's physical form; the issuance response's cache header; the Human Authority's shape in code |
| **U5 Code Generation** | The `evaluateHuman` refactor with no U4 assertion changed (BR-HA-02); the contract changes (§13); the concurrent-registration test (D-AR-26); *done when* 1 by raw calls in `e2e/` |
| **U6 (soorma-core#9)** | Bootstrap names the registration by its `agent` and accepts **any active secret** of that registration in E (D-AR-04), verifying against stored verification material only. **Added at approval (the user's, 2026-11-11)**: bootstrap **parses the secret record's `id` from the `soorma_rs_` value, loads that one record** (which must be `active` and belong to the named registration in E), and **compares in constant time**; a malformed value, an unknown id, a record of another registration or environment, a non-active record, or a mismatch are all **the same refusal as an unknown secret**. It never iterates over a registration's secrets; it requires the registration's `state` = `registered` (PF FR-009 "non-retired"), though M1 reaches no other state; agent attribution records resolve the sponsor from the registration (BR-AT-AR-02); U5 never updates a secret, so any per-secret bookkeeping U6 needs is its own record |
| **U7 (soorma-core#10)** | Agent attribution records resolve the sponsor from the registration (BR-AT-AR-02); an upstream agent in a chain always resolves (BR-AF-04) |
| **The slice that builds ID FR-026** (not M1) | **An observation recorded at the user's instruction, not resolved here**: ID @ `prd-identity-v1.0` FR-026's replacement rule, "a holder of `agent:register` and `human:manage` in E, or the agent's active sponsor holding `agent:register` there", **does not match ID §3's *Admin*** ("a holder of `grant:human` and `human:manage`"), which PF §8a's issuance rule uses and U5 builds (D-AR-01). U5 builds issuance only, so D-AR-01 stands. That slice must **classify the divergence through `prd-gap-classification.md`** before building the replacement |
| **The slice that adds suspend, resume, retire, or rotation** (not M1) | A registration's `state` and a secret's `state` become reachable; U3's term cache staleness (NFR-AE-16) applies to the first operation that changes a registration after it is written |
| **Build and Test** | *Done when* 1 run in full by raw calls; the misuse cases (§15) as tests; the residuals (§16) stated |

## 18. Specification Gaps

| Gap | Status | Effect |
|---|---|---|
| (none raised in U5) | — | Q1 classified as specified (D-AR-01); the FR-026 divergence recorded for a later slice (§17) |
| GAP-INT-006 (inherited) | Open, soorma-prd#24 | Worked around: standing sets and declarations accept plane-declared identifiers only (BR-RQ-02) |
| GAP-INT-004, GAP-INT-005 (inherited) | Resolved — PRD amended (PF v1.2) | The declaration is any set within the standing set (BR-RQ-04); grantable = held (BR-SP-03) |
