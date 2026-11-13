# L1 Coverage Matrix: U4 `env-human-access`

**Sources** (registered in `aidlc-state.md` `## PRD Intake`, each read at its tag):
- ID: soorma-prd/aiprd-docs/identity/requirements/prd.md @ `prd-identity-v1.0`, the main source
  for this unit
- PF: soorma-prd/aiprd-docs/platform-foundations/requirements/prd.md @ `prd-platform-foundations-v1.3`

**Status values**: `Covered` (design traced; implementation and verification targets set) ·
`N/A` (with a reason) · `Missing` (blocking). Code Generation moves rows to `Implemented`;
Build and Test moves them to `Verified`.

**Verification targets**: `TC-EHA-001` to `024` are the inception specs
(`inception/test-cases/env-human-access/`). *QA enrichment* marks a verification the QA
construction enrichment adds as a test case before the Construction Design PR gate; it replaces
each marker with a test-case ID.

**Result**: 33 applicable rows, all `Covered`. One (L1-17) rests on the **GAP-INT-006
work-around** (Open, soorma-prd#24). Two (L1-05, L1-09) rest on **GAP-EHA-001**, resolved —
clarified, no PRD change (D-EHA-01). 20 `N/A` rows. **0 `Missing`.**

**Code Generation (2026-11-11)**: all 33 applicable rows `Implemented`. The implementation
targets are as named, in `packages/service-kit` (the moved runtime), `packages/env-store`
(`migrations/0001_init.sql`, with the app role's column-level privileges), `packages/registry`
(P4), `packages/credentials` (P5), `packages/attribution` (P7), `packages/authority` (P3's
`evaluateHuman`, `holdsAnyGrant`), `packages/perimeter` (P1), `packages/config` (P9),
`services/control-gateway` (S2), A7 in `services/org-gateway` (S1), and
`contract/control-gateway.openapi.yaml`, on the local stack's `e` and `e2`. Every verification
target is a test, or a check in the stack smoke test or the S1-stopped demonstration, naming
its TC ID (TC-EHA-001 to 091; see `construction/env-human-access/code/code-summary.md`,
*Test Cases*). L1-17 still rests on the GAP-INT-006 work-around (Open, soorma-prd#24). Build and
Test moves rows to `Verified`.

---

## Applicable to U4

| # | L1 requirement | Design coverage | Implementation target | Verification target | Status |
|---|---|---|---|---|---|
| L1-01 | ID §7a *Human Environment Credential*: subject, environment, issued-from (the sign-in), expiry, revocation state; issued → expired / revoked | domain-entities *Human Environment Credential*; BR-EC-01, 07; D-EHA-30 | P5 `credentials`; env store | TC-EHA-002; TC-EHA-004; TC-EHA-014 | Verified |
| L1-02 | ID FR-010: issued **by E**, against a **live sign-in**, to an `active` principal holding **at least one grant in E** | BR-IS-01 to 04; BR-EC-01; BR-EV-02; D-EHA-02 | S2 issuance; P1; P3 `holdsAnyGrant`; the S1 caller | TC-EHA-002; TC-EHA-011; TC-EHA-025 (assigned at QA construction enrichment, 2026-11-11): issuance from an ended sign-in is refused | Verified |
| L1-03 | ID FR-010, O4: accepted **only in E** | BR-EC-02, 03; D-EHA-12 | P5 verification with E's material; P1 | TC-EHA-010 | Verified |
| L1-04 | ID FR-010: short-lived and renewable; **renewal never widens authority** | D-EHA-10 (no permissions in the credential); BR-EC-05 | P5; S2 renewal | TC-EHA-003; TC-EHA-026 (assigned at QA construction enrichment, 2026-11-11): a grant made after issuance applies at once, and renewal adds nothing | Verified |
| L1-05 | ID FR-010: renewal **never outlives** revocation, **its sign-in**, or the principal's `active` state | **D-EHA-01 (GAP-EHA-001, R2)**; D-EHA-02 (A7); BR-EC-04, 05, 08 | S2 renewal; the S1 caller; P10 `signInStatus` (A7) | TC-EHA-019; TC-EHA-020; TC-EHA-017; TC-EHA-028, 029 (assigned at QA construction enrichment, 2026-11-11): a renewed sign-in extends renewal; a credential stays usable after its sign-in ends, to its own expiry | Verified (GAP-EHA-001 resolved) |
| L1-06 | ID FR-011 (credential half): without a grant, a human renews and **ends** their own environment credential; an ended credential is refused thereafter (O3) | BR-EC-05, 07, 09; D-EHA-26 | S2 renewal and ending; P5 | TC-EHA-004; TC-EHA-014; TC-EHA-030 (assigned at QA construction enrichment, 2026-11-11): renewal racing an end | Verified |
| L1-07 | ID FR-009: the sign-in is **refused at every environment's perimeter except that environment's credential issuance** | BR-PR-02, 03 | P1 at S2 | TC-EHA-009 | Verified |
| L1-08 | ID FR-009, PF §6 *Rejected* (v1.3): environments hold **verify-only** material for the sign-in, never material that can mint | BR-IS-01, 05; domain-entities *Verify Keys* | The S1 caller's key cache | TC-EHA-022 | Verified |
| L1-09 | ID FR-009, §9 *Failure Modes*, §10 *NFR Profile*, §18 *Organization level*: the organization level is **on no per-request path**; its outage stops new sign-ins and organization operations | **D-EHA-01**, D-EHA-23; BR-OL-04 | The S1 caller, called only at issuance, renewal, and a grant's target | TC-EHA-031, 084, 085 (assigned at QA construction enrichment, 2026-11-11): ending, O3, and authority make no organization-level call; with S1 down, ending succeeds, and `grantToHuman` passes every step before its target check | Verified (GAP-EHA-001 resolved) |
| L1-10 | ID §8b *Human credentials at the perimeter*, environment-credential column: O1 to O3 apply; O4 as written; O5 to O7 N/A (no envelope); O8 the human's grants in E; O9, O10, O11 apply. Sign-in column: refused except at issuance | BR-PR; BR-IS; BR-EC-02; BR-EV-01; §11 | P1; P5; P3 | TC-EHA-009; TC-EHA-010; TC-EHA-014; TC-EHA-017; TC-EHA-021; TC-EHA-023 | Verified |
| L1-11 | ID §8b *Entry points by principal* and ID FR-023, the Gateway column at S2: sign-in reached only at issuance; environment credential reached in its own environment, refused in another; an agent credential beside a human's refused; a delegation credential refused | BR-PR-01 to 05 | P1 at S2 | TC-EHA-009; TC-EHA-010; TC-EHA-015; TC-EHA-016; TC-EHA-032 (assigned at QA construction enrichment, 2026-11-11): the `Soorma-Delegation` header | Verified |
| L1-12 | ID FR-022: the Gateway validates human credentials against O1 to O4 and O8 to O11 by kind; a direct human operation **carries no envelope**; its attribution names the human | §11 (steps 7, 8, 10 do not apply); BR-AT-02 | S2; P7 | TC-EHA-021 | Verified |
| L1-13 | ID §7b *Obligations*: an environment credential is presented only in its own environment; a sign-in only at the organization level or an environment's issuance; a human's credential never beside an agent's | BR-PR-02, 05; BR-EC-03 | P1 | TC-EHA-009; TC-EHA-010; TC-EHA-016 | Verified |
| L1-14 | ID §7b *Recoverability*: scope = the environment; actor by a human = the principal and the credential or sign-in presented; **a direct human operation has no origin mode** | D-EHA-03, 04; BR-AT-02, 06 | P7 | TC-EHA-005; TC-EHA-021 | Verified |
| L1-15 | ID FR-004: the environment's configuration names its first Admin and grants `grant:human` and `human:manage` there; configured, never inferred; the trust root is configuration | D-EHA-07; BR-FG-01 to 06; D-EHA-28 | P9 (environment half); S2 start-up; P4 | TC-EHA-001; TC-EHA-035 (assigned at QA construction enrichment, 2026-11-11): two concurrent start-ups write one configuration grant and one record; a restart writes nothing | Verified |
| L1-16 | ID FR-015: a holder of `grant:human` in E grants **any permission valid in E** to **any human, themselves included**; never requires holding it; **every self-grant recorded** | BR-GR-03, 05, 06, 07; D-EHA-16 | S2 `grantToHuman`; P4; P7 | TC-EHA-005; TC-EHA-006; TC-EHA-007; TC-EHA-008 | Verified |
| L1-17 | ID FR-015 *valid in E*: only plane-declared identifiers are accepted (**GAP-INT-006 work-around**) | BR-ACC-01 to 03; D-EHA-06 | P4 accepted set; S2 step 6 | TC-EHA-013; TC-EHA-038 (assigned at QA construction enrichment, 2026-11-11): pointers, at most 10 | Verified (work-around; GAP-INT-006 Open) |
| L1-18 | ID FR-013: `human:manage` and `agent:delegate` are human-only, joining `grant:human`; grantable to humans | BR-EV-03; BR-GR-07 | P3 (no human-only refusal for humans) | TC-EHA-008 | Verified |
| L1-19 | ID §8a and PF §8a *Grant permissions to a human principal*: `grant:human` in E; Admin only; **never an agent** | BR-GR-03; BR-PR-04; BR-EV-01 | P3 `evaluateHuman`; P1 | TC-EHA-012; TC-EHA-015 | Verified |
| L1-20 | ID §8a: obtain an environment credential (a live sign-in; `active`; a grant in E); renew or end one's own (self) | BR-EV *Required authority per operation*; BR-EC-01, 05, 07 | S2 | TC-EHA-002; TC-EHA-003; TC-EHA-004; TC-EHA-011 | Verified |
| L1-21 | ID §6: the human environment credential, its identifiers, human grants, the first grant, and credential validation caches **key on the environment**; credentials and issuance never cross it | D-EHA-29, 30; BR-EC-03; domain-entities *Relationships* | env store; P5; P4 | TC-EHA-010; TC-EHA-022; TC-EHA-040 (assigned at QA construction enrichment, 2026-11-11): every env-store access path constrains on the environment | Verified |
| L1-22 | ID §6, FR-001: the human principal identifier is organization-scoped, composed, never allocated; a target is `{ organization, principal }`, compared exactly; another organization's principal does not exist for E | BR-GR-04; D-EHA-16; BR-ID-08 | S2 `grantToHuman`; the S1 caller | TC-EHA-018; TC-EHA-041 (assigned at QA construction enrichment, 2026-11-11): a target in another organization, with no organization-level call | Verified |
| L1-23 | ID FR-001: a human principal is never deleted or pruned (a resolution target) | U4 holds principal references only and never deletes a Grant, credential, or record (BR-GR-09; BR-AT-08) | P4; P5; P7 | Code Generation review | Verified |
| L1-24 | ID §10 *NFR Profile*: read-your-writes for the actor; every operation recorded in the affected environment; interactive latency at credential issuance | BR-GR-08; D-EHA-14; BR-AT-01; latency: NFR Requirements | P4 (uncached); P7. *Updated at NFR Design (2026-11-11)*: latency NFR-EHA-15 (reported); the held-set read NP-EHA-10; records NP-EHA-07, written in one `env-store` transaction (NP-EHA-06) | TC-EHA-005; TC-EHA-027 (assigned at QA construction enrichment, 2026-11-11): a self-grant usable on the next request | Verified |
| L1-25 | ID §10 *Failure Modes* and §8b O3: fail closed when state cannot be read | BR-IS-03; BR-EC-02, 05; BR-EV-06; D-EHA-27 | P1; P5; P4; the S1 caller | TC-EHA-023; TC-EHA-043 (assigned at QA construction enrichment, 2026-11-11): S1 unreachable at issuance and at renewal is `unavailable` | Verified |
| L1-26 | PF §7a *Permission Grant*: principal reference, environment scope, permission set, granted-at, granted-by (a principal or **the environment's configuration**) | domain-entities *Grant*; BR-GR-05; BR-FG-01 | P4; env store | TC-EHA-001; TC-EHA-005 | Verified |
| L1-27 | PF FR-018: flat, opaque identifiers with set semantics, deny-by-default environment scoping | BR-EV-01, 05; BR-GR-01 | P11 over P4's source | TC-EHA-012 | Verified |
| L1-28 | PF §8b O8, O9; I5: effective authority for a direct human operation is the human's grants in E, **computed in one place**; deny by default | D-EHA-13; BR-EV-01 to 06 | P3 `evaluateHuman`, `holdsAnyGrant` | TC-EHA-012; TC-EHA-044 (assigned at QA construction enrichment, 2026-11-11): S2 imports no other evaluator | Verified |
| L1-29 | PF FR-012, O3: revocation state read on every request, never staler than the bound; unreadable denies | D-EHA-11; BR-EC-02 | P5 (uncached record read) | TC-EHA-014; TC-EHA-023 | Verified |
| L1-30 | PF FR-021, FR-022, O11: grants, credentials, revocation state, identifiers key on environment; environment identity configured, never inferred | D-EHA-12, 29; domain-entities *Environment Configuration* | P9; P5; P4 | TC-EHA-010; TC-EHA-045 (assigned at QA construction enrichment, 2026-11-11): a credential asserting another environment, signed with E's material, is refused | Verified |
| L1-31 | PF FR-025 (recording): every platform-resource operation produces a record carrying scope, actor, chain, origin; sponsorship resolvable; **whatever the read would return recoverable from the record alone** | D-EHA-03, 04, 31; BR-AT-01 to 09 | P7 | TC-EHA-005; TC-EHA-021; TC-EHA-046, 047 (assigned at QA construction enrichment, 2026-11-11): each actor kind reconstructed from the record alone, at zero hops and across a multi-hop chain; the inconsistent record refused | Verified |
| L1-32 | PF §10 *NFR Profile*: read-your-writes for the acting principal; every operation attributed; grant durability | BR-GR-08; BR-AT-01; D-EHA-17; durability: NFR Requirements | P4; P7. *Updated at NFR Design (2026-11-11)*: durability NFR-EHA-10, 11; one `env-store` transaction per operation (NP-EHA-06); append-only grants and records (NP-EHA-07, 10) | TC-EHA-005 | Verified |
| L1-33 | PF O10: no entry point treats another's traffic as pre-validated: S2 verifies the sign-in S1 issued, never trusting it as S1's | BR-IS-01, 03 | P1 at S2 | TC-EHA-009; TC-EHA-049, 064 (assigned at QA construction enrichment, 2026-11-11): a sign-in signed with an unknown key | Verified |

## Not Applicable to U4

| L1 requirement | Reason |
|---|---|
| ID FR-002, FR-003, FR-005, FR-012, FR-016 to FR-018, FR-024 to FR-026, FR-028, FR-029 | Absent from M1 (requirements, *Absent from M1*) |
| ID FR-006 to FR-008; FR-011 (sign-in and material half) | S1, U2 |
| ID FR-014 *Coverage* | Every U4 effect is confined to E, so it reduces to authority in E (BR-EV); organization-wide coverage belongs to absent operations |
| ID FR-019 to FR-021; ID §9 | Delegation: out of M1 (A-4) |
| ID FR-027 | The identity-resolution seam: U2 (human half), U6 |
| ID §7a *Delegation Credential*, *Organization-Level Attribution*, *Configured Identity Source*, *Grant Mapping* | Absent from M1 |
| ID §8b *Entry points*, Event ingest column | U7 (S4); U6 for S3 |
| ID §8b *Entry points*, configured source row | Absent (FR-024) |
| ID §11, §17 (harness) | No client library for the human side (ID §11) |
| PF §7b *Envelope Fields* | No envelope on a direct human operation (PF FR-001 v1.3; ID FR-022) |
| PF §8a *Grant at project scope (expanded at grant time)* | **Not built**: a delivery limit (D-EHA-19), added to *Absent from M1* |
| PF §8a, the registration and secret rows | U5 |
| PF FR-007, FR-008, FR-016, FR-017 | U5 |
| PF FR-009, FR-010, FR-027 | U6 |
| PF FR-011 | Revocation initiation is absent (agent); a human's own end is ID FR-011 (L1-06) |
| PF FR-013 | Retention and pruning: absent |
| PF FR-014, FR-015, FR-017 (evaluation), §8b *Re-broadening*, O5 to O7, O12 | Agent evaluation and the envelope: U3, U7 |
| PF FR-020 at Event ingest | U7 |
| PF FR-025 (the read) | Absent from M1. Its content is recoverable from the record (L1-31) |
| PF §9 | The data face: U6, U7 |

## PRD-Sourced Gaps

| Gap | Rows | Status |
|---|---|---|
| GAP-EHA-001 | L1-05, L1-09 | **Resolved — clarified, no PRD change** (R2; D-EHA-01). No row is `Missing` |
| GAP-INT-006 (inherited) | L1-17 | Open, soorma-prd#24. Worked around (plane-declared identifiers only) |

**Build and Test (2026-11-13)**: every applicable row `Verified` against the stage run (every suite, the e2e proofs on a fresh stack, the smoke and outage runs, the image checks). Evidence per row: [`../../build-and-test/l1-conformance-test-instructions.md`](../../build-and-test/l1-conformance-test-instructions.md).
