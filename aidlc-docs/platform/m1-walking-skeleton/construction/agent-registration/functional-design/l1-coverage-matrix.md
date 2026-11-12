# L1 Coverage Matrix: U5 `agent-registration`

**Sources** (registered in `aidlc-state.md` `## PRD Intake`, each read at its tag):
- PF: soorma-prd/aiprd-docs/platform-foundations/requirements/prd.md @ `prd-platform-foundations-v1.3`,
  the main source for this unit
- ID: soorma-prd/aiprd-docs/identity/requirements/prd.md @ `prd-identity-v1.0`

**Status values**: `Covered` (design traced; implementation and verification targets set) ·
`N/A` (with a reason) · `Missing` (blocking). Code Generation moves rows to `Implemented`;
Build and Test moves them to `Verified`.

**Verification targets**: `TC-AR-001` to `022` are the inception specs
(`inception/test-cases/agent-registration/`). *QA enrichment* marks a verification the QA
construction enrichment adds as a test case before the Construction Design PR gate; it replaces
each marker with a test-case ID.

**QA construction enrichment (2026-11-11)**: every *QA enrichment* marker is replaced by its TC id
(`inception/test-cases/agent-registration/`, TC-AR-001 to 072).

**Result**: 32 applicable rows, all `Covered`. Two (L1-17, L1-31) rest on the **GAP-INT-006
work-around** (Open, soorma-prd#24). L1-18 rests on D-AR-01, classified as specified (ID §3 with
PF §8a). **0 `Missing`.**

**Updated at NFR Design (2026-11-11)**: implementation targets made concrete, no row's status
changed. L1-01, L1-02: the four-column primary key of `registrations` (NP-AR-01). L1-04, L1-11:
the `<@ ceiling_snapshot` constraint beside P3's check. L1-06: the `<@ standing_permissions`
constraint. L1-09, L1-10: the app role's `SELECT, INSERT` only on both tables, in migration
`0002`. L1-13: the agent-facts statement reads neither snapshot nor sponsor (NP-AR-04). L1-18,
L1-19: `registration_secrets` with its foreign key and 32-byte digest; the secret module in
`packages/registry` (NP-AR-02). L1-21: backup and restore (NP-AR-08, 09). L1-24: `evaluateHeld`,
`readHumanAuthority` (NP-AR-05).

---

## Applicable to U5

| # | L1 requirement | Design coverage | Implementation target | Verification target | Status |
|---|---|---|---|---|---|
| L1-01 | PF §7a *Identifier*: unique within the environment | domain-entities *Registration*; D-AR-02, 26; BR-RG-02 | P4 write; env store uniqueness | TC-AR-001; TC-AR-023, 024 (assigned at QA construction enrichment, 2026-11-11): a taken `agent` is `registration_exists`, and two concurrent registrations of one `agent` write one record and one attribution record | Covered |
| L1-02 | PF §7a *Environment scope*; FR-007: registered in **exactly one** environment | domain-entities; BR-RG-02; BR-AF-02 | P4; env store (three columns) | TC-AR-001; TC-AR-025 (assigned at QA construction enrichment, 2026-11-11): the same `agent` registered in E and E2 is two independent registrations | Covered |
| L1-03 | PF §7a *Sponsor reference*: the principal answerable for the standing authority; ID §1 trace step 6: sponsor = H | D-AR-09; BR-RG-01 | S2; P4 | TC-AR-001; TC-AR-008; TC-AR-026 (assigned at QA construction enrichment, 2026-11-11): a body naming a `sponsor` is `malformed_request` | Covered |
| L1-04 | PF §7a *Sponsor ceiling snapshot*; FR-016: what the sponsor held **at the moment of granting**, recorded | D-AR-07, 11; BR-SP-05 | P3 `readHumanAuthority().snapshot()`; P4 | TC-AR-002; TC-AR-019 | Covered |
| L1-05 | PF §7a *Standing permission set* | domain-entities; D-AR-06, 14 | P4 | TC-AR-001; TC-AR-018 | Covered |
| L1-06 | PF §7a, FR-017 *Re-broadening declaration*: a set, possibly empty, **within the standing set**; declaring more is rejected | BR-RQ-04, 05; D-AR-03, 10 | P3 request check; P4 | TC-AR-004; TC-AR-005; TC-AR-012 | Covered |
| L1-07 | PF §7a *Autonomy declared*: boolean, default no | BR-RQ-05; D-AR-14 | S2 schema; P4 | TC-AR-003 | Covered |
| L1-08 | PF §7a *Registration timestamp* | BR-RG-01 | P4 | TC-AR-001 | Covered |
| L1-09 | PF §7a *State transitions*; FR-007: retirement is a state transition, **never a deletion** | domain-entities `state`; D-AR-15; business-logic-model §6 | P4; env store privileges (no `DELETE`) | TC-AR-001; TC-AR-027 (assigned at QA construction enrichment, 2026-11-11): the app role cannot update or delete a registration | Covered |
| L1-10 | PF FR-013: registrations are resolution targets, **never pruned** | D-AR-15; BR-AF-04 | P4; env store | TC-AR-027, 028 (assigned at QA construction enrichment, 2026-11-11): no code path deletes a registration (review check plus the privilege test) | Covered |
| L1-11 | PF FR-016, §8a *Grant standing permissions at registration*: standing ⊆ the sponsor's **held** set; **checked once at registration, never per request** | D-AR-07, 12; BR-SP-03, 04 | P3 `readHumanAuthority().allows` (`evaluateHeld`) | TC-AR-009; TC-AR-018; TC-AR-029 (assigned at QA construction enrichment, 2026-11-11): `exceeds_sponsor_ceiling` pointers; the ceiling is never reached without `agent:register` | Covered |
| L1-12 | PF FR-016, §8b: a standing set containing a **human-only** permission is rejected **whatever the sponsor holds**; the class is the union planes declare (PF `grant:human`; ID FR-013 `human:manage`, `agent:delegate`) | D-AR-03, 10; BR-RQ-03 | P3 request check over `HUMAN_ONLY_PERMISSIONS` | TC-AR-010; TC-AR-011; TC-AR-030, 031 (assigned at QA construction enrichment, 2026-11-11): pointers; P4 and S2 import the class from P3 only | Covered |
| L1-13 | PF FR-016, §8b, §7b: sponsorship resolved **by reference through the registration**, not carried on the envelope; the sponsor's live permissions **never consulted per request** | BR-SP-04; BR-AT-AR-02; D-AR-19 (the snapshot is not in agent facts) | P4 agent-facts query; P7 | TC-AR-032 (assigned at QA construction enrichment, 2026-11-11): the agent-facts result carries no snapshot or sponsor; U3 reads no sponsor set | Covered |
| L1-14 | PF §8a *Register logical agent*: `agent:register` in the environment; enforcement Gateway; control | BR-SP-02 | P3; S2 | TC-AR-014 | Covered |
| L1-15 | PF §8a *Issue a registration secret*, §10, §11: `agent:register`; **Admin or sponsoring Developer**; Admin per ID §3 (`grant:human` and `human:manage`) | **D-AR-01**; BR-SE-02, 04; D-AR-27 | P3; S2 | TC-AR-015; TC-AR-033 (assigned at QA construction enrichment, 2026-11-11): a non-sponsor with only `agent:register` is `forbidden`; a non-sponsor Admin with `agent:register` issues; an Admin without `agent:register` is `forbidden` | Covered |
| L1-16 | PF FR-008 (issuance): a secret per logical agent, with a lifecycle **independent of any credential's** | D-AR-04; BR-SE-05, 06 | P4; S2 | TC-AR-006; TC-AR-034 (assigned at QA construction enrichment, 2026-11-11): two secrets for one registration are both active | Covered |
| L1-17 | M1-FR-15, PF §8a: standing sets accept **only plane-declared identifiers** (**GAP-INT-006 work-around**) | D-AR-14; BR-RQ-02 | U4's BR-ACC set in P4; S2 step 6 | TC-AR-013; TC-AR-035 (assigned at QA construction enrichment, 2026-11-11): an unaccepted identifier in the declaration | Covered (work-around; GAP-INT-006 Open) |
| L1-18 | PF §7a *Registration Secret* (v1.3); ID FR-026 (issuer half): bound to **one** registration; records its **issuer**, a lower bound on who knows it | domain-entities *Registration Secret*; BR-SE-05 | P4 | TC-AR-006 | Covered |
| L1-19 | PF §8b *Bootstrap*: a **locally-verified** registration secret; the record holds verification material only | D-AR-16; BR-SE-05, 07 | P4; S2 (verifier: NFR Requirements) | TC-AR-006; TC-AR-020; TC-AR-036 (assigned at QA construction enrichment, 2026-11-11): no log line or record contains the value | Covered |
| L1-20 | PF §10 *Failure Modes*: the four registration rejections (exceeds held; human-only; declaration exceeds standing; held set unresolvable) | D-AR-03, 13; BR-RQ-03, 04; BR-SP-03 | S2; P3 | TC-AR-009 to 012; TC-AR-021 | Covered |
| L1-21 | PF §10 *NFR Profile*: read-your-writes for the actor; every operation attributed; registrations the **highest durability** | BR-SP-06; D-AR-17, 18; durability: NFR Requirements | P4 (uncached held set); P7 | TC-AR-007; TC-AR-037 (assigned at QA construction enrichment, 2026-11-11): a self-grant of `agent:register` is usable for registration on the next request | Covered |
| L1-22 | PF §7a *Permission Grant*, agent-principal form: principal, environment scope, permission set, granted-at, granted-by | **D-AR-06** (the registration is the agent's grant) | P4 registration | TC-AR-001 | Covered |
| L1-23 | PF FR-018: flat, opaque identifiers with set semantics; deny by default | D-AR-14 (unique; sets); BR-SP-02 | P3; P11 | TC-AR-014 | Covered |
| L1-24 | PF §8b O8, O9; I5: authority computed **in one place**; deny by default | **D-AR-07**; BR-HA-01 to 04; BR-SP-07 | P3 `evaluateHeld`, `evaluateHuman`, `readHumanAuthority` | TC-AR-031, 038 (assigned at QA construction enrichment, 2026-11-11): S2 and P4 import no evaluator but P3's; `evaluateHuman`'s tests unchanged; one held-set read per operation (a counting source) | Covered |
| L1-25 | PF §6, FR-021, FR-022, O11: registrations, secrets, and identifiers key on the environment; environment identity configured | D-AR-15, 19; BR-AF-02; BR-RG-02 | env store (three columns on every statement); P9 | TC-AR-039, 042 (assigned at QA construction enrichment, 2026-11-11): a principal of E cannot register into, issue for, or read facts of E2's registrations; E2's credential is refused at E | Covered |
| L1-26 | PF §7b *Recoverability*: sponsorship, two hops (actor → instance → logical agent → registration's sponsor) | BR-AT-AR-02; business-logic-model §5.5 | P4; P7 | TC-AR-040 (assigned at QA construction enrichment, 2026-11-11): resolving the sponsor from an agent attribution record through the registration | Covered |
| L1-27 | PF FR-025 (recording); ID §7b *Recoverability*: each operation recorded; a human actor = the principal and the credential presented; **no origin mode** | D-AR-17, 18; BR-AT-AR-01, 03 | P7 | TC-AR-007; TC-AR-041 (assigned at QA construction enrichment, 2026-11-11): a failed attribution write leaves no registration or secret | Covered |
| L1-28 | ID FR-022: human credentials validated against O1 to O4, O8 to O11 by kind; **no envelope** on a direct human operation | BR-PR-AR-02; §10 (steps 7, 8, 10 do not apply) | S2; P1 | TC-AR-022 | Covered |
| L1-29 | ID §8b *Entry points*, the Gateway column at S2: environment credential reached in its own environment; refused in another; agent credential (and agent beside human) refused | BR-PR-AR-03; D-AR-08 | P1 at S2 | TC-AR-016; TC-AR-042 (assigned at QA construction enrichment, 2026-11-11): E2's credential at E; a sign-in on either operation | Covered |
| L1-30 | ID §1 trace steps 6 to 9 (*done when* 1): two agents in one environment, each with its own sponsor reference and snapshot, attributed to H | business-logic-model §5.1 | S2; P3; P4; P7; `e2e/` | TC-AR-008 (*done when* 1 by raw calls in `e2e/`) | Covered |
| L1-31 | ID FR-015, M1-FR-15: the accepted set includes ID's human-only identifiers, which are accepted **and** then refused in a standing set (GAP-INT-006 work-around) | BR-RQ-02, 03 (order) | S2 step 6 | TC-AR-011 | Covered (work-around; GAP-INT-006 Open) |
| L1-32 | PF §3 *Separation of Duties*, §12: core's single-actor form; the registrant sponsors | D-AR-09 | S2 | TC-AR-001 | Covered |

## Not Applicable to U5

| L1 requirement | Reason |
|---|---|
| PF FR-008 rotation and retirement; §8a *Rotate / retire a registration secret* | Absent from M1 (M1-FR-04) |
| PF §8a *Suspend / resume*, *Retire logical agent*; §7a's `suspended`, `retired` transitions | Absent from M1 (M1-FR-03): the state is carried (L1-09), no operation reaches another |
| PF §8a autonomous-origin column for registration and issuance (agent-registers-agent) | Absent from M1 (requirements, *Registration and secret issuance by an agent*); refused by kind (L1-29) |
| PF §8a, §10 *Revoke*; PF FR-011 | Absent from M1 (initiation) |
| PF §10 *Retire a registration with live credentials* | Retirement absent |
| PF FR-009, FR-010, FR-012, FR-027; §8b *Bootstrap* (the exchange) | U6 (L1-19 covers what U5 stores for it) |
| PF FR-014, FR-015, FR-017 (evaluation), §8b *Re-broadening* composition, O5 to O7, O12 | U3, U7: evaluation and the envelope. U5 records the declaration and autonomy they read |
| PF FR-025 (the read); §8a *Read attribution records* | Absent from M1 |
| PF §9 | The data face: U6, U7 |
| PF §11 *Portal Surface* | No portal in M1 (ID FR-029 absent); its scoping rule informs D-AR-01 |
| ID FR-026, the deactivation half (retire a deactivated issuer's secrets; replacement secrets) | ID FR-003 absent. **The FR-026 rule's divergence from ID §3 is a forward obligation** (business-rules §17), not resolved here |
| ID FR-014 *Coverage* | Both effects are confined to E, so it reduces to authority in E (D-AR-21) |
| ID FR-019 to FR-021 | Delegation: out of M1 |

## PRD-Sourced Gaps

| Gap | Rows | Status |
|---|---|---|
| GAP-INT-006 (inherited) | L1-17, L1-31 | Open, soorma-prd#24. Worked around (plane-declared identifiers only) |
| GAP-INT-004, GAP-INT-005 (inherited) | L1-06, L1-11 | Resolved — PRD amended at PF v1.2; built as amended |
| (none raised in U5) | — | Q1 classified as specified (D-AR-01) |
