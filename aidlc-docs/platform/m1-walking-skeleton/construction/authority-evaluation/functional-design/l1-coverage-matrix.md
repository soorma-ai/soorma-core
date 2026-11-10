# L1 Coverage Matrix: U3 `authority-evaluation`

**Sources** (registered in `aidlc-state.md` `## PRD Intake`, each read at its tag):
- PF: soorma-prd/aiprd-docs/platform-foundations/requirements/prd.md @ `prd-platform-foundations-v1.3`,
  the main source for this unit
- ID: soorma-prd/aiprd-docs/identity/requirements/prd.md @ `prd-identity-v1.0`

**Status values**: `Covered` (design traced; implementation and verification targets set) ·
`N/A` (with a reason) · `Missing` (blocking). Code Generation moves rows to `Implemented`;
Build and Test moves them to `Verified`.

**Code Generation (2026-11-10)**: all 38 applicable rows moved to `Implemented`, each built at
the step its implementation target names and verified by its test cases, which pass in the local
run (`construction/authority-evaluation/code/code-summary.md`). Build and Test moves them to
`Verified`.

**Verification targets**: `TC-AE-001` to `022` are the inception specs
(`inception/test-cases/authority-evaluation/`). `TC-AE-023` to `039` were added by the QA
construction enrichment (2026-11-10), which replaced every *QA enrichment* marker below with a
test-case ID.

**Result**: 38 applicable rows, all `Implemented` (Code Generation, 2026-11-10). Four of them (L1-07, L1-21, L1-25, L1-38)
rest on the **GAP-AE-001 work-around** (Open, soorma-prd#30), and one (L1-27) on the
GAP-INT-007 work-around (Open, soorma-prd#25). 17 `N/A`. **0 `Missing`.**

---

## Applicable to U3

| # | L1 requirement | Design coverage | Implementation target | Verification target | Status |
|---|---|---|---|---|---|
| L1-01 | PF FR-001, §7b: the envelope's seven fields, with their requiredness | BR-ST-01, 02; domain-entities *Stamped Envelope* | P2 `stamp` | TC-AE-001 | Implemented |
| L1-02 | PF FR-002, O5: stamped fields are written by the perimeter; a draft setting one is **rejected, not overwritten**; an envelope is never usable to act | BR-DV-02, 04, 05; BR-FX-06 | P2 `validateDraft`; the entry point requires a Checked Agent Context | TC-AE-009; TC-AE-014; TC-AE-020; TC-AE-023 | Implemented |
| L1-03 | PF FR-005 (a), §7b: unknown fields **preserved and forwarded**, at every level, `traceContext` included | D-AE-05, D-AE-14; BR-ST-02, 03 (U1 amendment A6) | P2 `stamp` | TC-AE-008; TC-AE-027 | Implemented |
| L1-04 | PF FR-005 (b): an unknown enumerated value is not fatal | D-AE-07; BR-OR-05 | P3 `resolveOrigin` | TC-AE-008; TC-AE-025 | Implemented |
| L1-05 | PF FR-006, O7: the full chain, most recent last, appended per hop; `maxChainDepth` enforced, never truncated | D-AE-13; BR-CD-01, 02; BR-ST-02 | P2 `checkChainDepth`, `stamp` | TC-AE-003; TC-AE-017 | Implemented |
| L1-06 | PF FR-014, §8b *Intersection*: `standing ∩ authority(hop1) ∩ …`; an agent never acquires its delegator's authority | BR-AU-01, 02; business-logic-model §3 | P3 `evaluateAgent` | TC-AE-004; TC-AE-015; TC-AE-020 | Implemented |
| L1-07 | PF FR-015: origin stamped where derivable, **propagated unchanged** from inbound; with no forwarded context, an undeclared agent is **denied** | BR-OR-01 to 04; **D-AE-01 (GAP-AE-001 work-around: also denied when forwarding an autonomous envelope)** | P3 `resolveOrigin` | TC-AE-002; TC-AE-003; TC-AE-011; TC-AE-023 | Implemented (work-around; GAP-AE-001 Open) |
| L1-08 | PF FR-017, §8b *Re-broadening*: declared at registration; at the declaring hop `standing ∩ P ∩ (upstream ∪ declared)`; only when load-bearing; local to its hop; recorded, never requested; an agent-set record rejected | BR-AU-04 to 07; BR-ST-04; BR-DV-04; D-AE-20 | P3 `evaluateAgent`; P2 `stamp`, `validateDraft` | TC-AE-005; TC-AE-014; TC-AE-016; TC-AE-018; TC-AE-019; TC-AE-022 | Implemented |
| L1-09 | PF FR-018 (evaluation): flat, opaque identifiers with set semantics; deny-by-default environment scoping | BR-SEAM-03; BR-AU-08 | P11 | TC-AE-021; TC-AE-006 | Implemented |
| L1-10 | PF FR-019, §8b: the model satisfies L1 to L5 | D-AE-16; domain-entities *Permission Set* | P3, P11 | TC-AE-035 | Implemented |
| L1-11 | PF FR-021: everything keys on environment | BR-SEAM-03 (the default answers only for E); BR-FX-02, 04 | P11; P2 `verifyInbound` | TC-AE-006; TC-AE-024; TC-AE-034 | Implemented |
| L1-12 | PF FR-022, §7b: scope from the **presented credential**, never from deployment | D-AE-08, D-AE-23; BR-ST-01 | The entry point; P2 `stamp` | TC-AE-001; TC-AE-039 | Implemented |
| L1-13 | PF FR-026; M1-FR-13: the code is shaped at the policy-decision seam line; unpublished; no configuration selection | D-AE-02; BR-SEAM-01 | `seams/policy-decision`; P11 | TC-AE-006; TC-AE-039 | Implemented |
| L1-14 | PF §7a *Logical Agent Registration*: standing set, re-broadening declaration, **autonomy declared, default no** (as read) | domain-entities *Registration View*; BR-OR | P3, from the agent-facts read (NFR Design NP-04) | TC-AE-002; TC-AE-011 | Implemented |
| L1-15 | PF §7a *Permission Grant*: principal, environment, permission set (evaluation side) | D-AE-02; BR-SEAM-04 | P11 `grantedSet` over `GrantSource` (agents from the agent-facts snapshot, humans from U4; NP-04) | TC-AE-006; TC-AE-034 | Implemented |
| L1-16 | PF §7b *Envelope Fields*: setter per field; trace context agent-asserted, validated | BR-ST; BR-DV; D-AE-17 | P2 | TC-AE-001; TC-AE-007; TC-AE-012 | Implemented |
| L1-17 | PF §7b obligations: preserve unknown fields; tolerate unknown values; propagate origin unchanged; append the chain; enforce `maxChainDepth` | L1-03, 04, 05, 07 | P2, P3 | As L1-03, 04, 05, 07 | Implemented |
| L1-18 | PF §7b *Recoverability*: scope, actor, chain, origin at zero hops | BR-ST-01 to 05; BR-ST-08 | P2 `stamp`; the Admitted outcome | TC-AE-001; TC-AE-003 | Implemented |
| L1-19 | PF §8a: publish requires `event:publish`, subscribe `event:subscribe`; in autonomous origin the standing set is the ceiling | D-AE-10; domain-entities *Required Authority* | The entry point's input; P3 | TC-AE-004; TC-AE-020 | Implemented |
| L1-20 | PF §8b *Origin stamping*: inbound propagated unchanged; no context and declared, `autonomous`; no context and undeclared, denied. (The delegated first-hop row is absent in M1: L1-N/A) | BR-OR-01 to 03 | P3 `resolveOrigin` | TC-AE-002; TC-AE-003; TC-AE-011 | Implemented |
| L1-21 | PF §8b *Declared autonomy against forwarded context*: No/No denied; Yes/No `autonomous`. **The forwarded rows give `delegated`, which contradicts FR-015 for an autonomous inbound envelope** | BR-OR-01, 02; **forwarded rows: D-AE-01, BR-OR-03, 04 (GAP-AE-001 work-around)** | P3 `resolveOrigin` | TC-AE-002; TC-AE-011; TC-AE-023 | Implemented (work-around; GAP-AE-001 Open) |
| L1-22 | PF §8b *Re-broadening* case table: all four rows | business-logic-model §3 | P3 `evaluateAgent` | TC-AE-022 | Implemented |
| L1-23 | PF §8b O5, O6: stamped fields written by the perimeter; origin from inbound context; an asserted origin rejected | BR-DV-02, 04; BR-OR-03 | P2, P3 | TC-AE-009; TC-AE-010 | Implemented |
| L1-24 | PF §8b O8, O9: effective authority evaluated against required authority; **deny by default** | BR-AU; D-AE-09, 10 | P3 | TC-AE-004; TC-AE-021 | Implemented |
| L1-25 | PF §8b O12: autonomous origin denied unless the presenter's registration declares autonomy | BR-OR-02, 04; D-AE-01 | P3 `resolveOrigin` | TC-AE-011; TC-AE-023 | Implemented (work-around for the forwarded case; GAP-AE-001 Open) |
| L1-26 | PF §8b *Core Baseline*; §17 *Policy Grammar*: flat opaque identifiers, set semantics, deny by default | BR-SEAM-03 | P11 | TC-AE-021 | Implemented |
| L1-27 | GAP-INT-007 work-around: origin mode never accepted from a draft, the autonomous first hop included | BR-DV-04 | P2 `validateDraft` | TC-AE-010 | Implemented (work-around; GAP-INT-007 Open) |
| L1-28 | PF §8b human-only class; PF FR-016 (*whatever the sponsor holds*); ID FR-013 (`human:manage`, `agent:delegate`); ID OB-16 (matched only explicitly): never an agent's | D-AE-03; BR-AU-03 (defence in depth; U5 owns the registration check) | `packages/authority` (the class); P3 | TC-AE-026 | Implemented |
| L1-29 | PF §9 *Failure Modes*: chain depth exceeded, rejected; malformed or stamped field, rejected; asserted `autonomous` with inbound context, rejected; no forwarded context and undeclared, denied | BR-CD-01; BR-DV-02, 04; BR-OR-02 | P2, P3 | TC-AE-017; TC-AE-009; TC-AE-010; TC-AE-011 | Implemented |
| L1-30 | PF §9 *NFR Profile*: the per-request hot path, for the evaluation | Carried to U3's NFR Requirements (business-rules §16) | U3 NFR Requirements and NFR Design (NFR-AE-06, 07) | TC-AE-034 (structural, gated); TC-AE-040 (p99, reported) | Implemented (TC-AE-034 gated; TC-AE-040 reported at Build and Test) |
| L1-31 | PF §11 *What the SDK may not populate*: stamped fields rejected; envelope version rejected and the client contract version expected | BR-DV-02; BR-VR-02 | P2 | TC-AE-009; TC-AE-013 | Implemented |
| L1-32 | PF §11 *Forward inbound context*: origin from the forwarded context; chain appended; `maxChainDepth`; O12 with no forwarded context | BR-FX; BR-OR; BR-CD | P2, P3 | TC-AE-003; TC-AE-011; TC-AE-017 | Implemented |
| L1-33 | PF §11 *Populate trace context*: well-formedness only, against an open standard | D-AE-17 | P2 `validateDraft` | TC-AE-007; TC-AE-012 | Implemented |
| L1-34 | PF §11, §17: effective-authority evaluation is **internal**, never edge-reachable | business-logic-model §1 (modules only; no surface imports P2) | `packages/` only | TC-AE-039 | Implemented |
| L1-35 | PF §12 *Seam Declarations*, policy decision: both halves of the interface; default deny-by-default, literal containment, environment-scoped grant storage | D-AE-02; BR-SEAM-01 to 04 | `seams/policy-decision`; P11 | TC-AE-006 | Implemented |
| L1-36 | PF §12 *Seam containment*: the intersection, origin stamping (O12 included), chain append and `maxChainDepth` stay in core; **containment, never composition** | BR-SEAM-02, 05; BR-AU-01, 02 | P2, P3 | TC-AE-006; TC-AE-039 | Implemented |
| L1-37 | PF §17 *The envelope*: not self-authenticating; verified before use | BR-FX-02; BR-FX-06 | P2 `verifyInbound`; the Sealer | TC-AE-024; TC-AE-032 | Implemented |
| L1-38 | **GAP-AE-001 work-around**: an autonomous origin, propagated, requires the presenter's declaration | D-AE-01; BR-OR-04; pre-release statement 9 | P3 `resolveOrigin`; `conventions/pre-release.md` | TC-AE-023 | Implemented (work-around; GAP-AE-001 Open) |

## Inherited Obligations (not L1, carried from U1)

| Obligation | Design coverage | Verification target | Status |
|---|---|---|---|
| BR-ERR-08: every Problem soorma-core emits carries `type`, `title`, `status`, `code`, `instance`, in the `urn:soorma:` forms, `instance` equal to `Soorma-Request-Id` | D-AE-06; BR-PE-01 to 06 | TC-AE-031 (every code in P1's table; S1's edge tests through the shared assertion) | Implemented |
| D-CG-05: the Ajv runtime regex engine | Decided at U3's NFR Requirements: V8's default `RegExp` (T-AE-01) | TC-AE-038 | Implemented |
| BR-ENV-03, 04, 08, 10; BR-DR-01 to 10; BR-FC-01 to 05 | BR-FX, BR-CD, BR-DV, BR-ST, BR-OR | TC-AE-001 to 030 | Implemented |

## Not Applicable to U3

| L1 requirement | Reason |
|---|---|
| PF FR-003, FR-004 | The envelope's single definition and compatibility policy: U1 |
| PF FR-007, FR-008, FR-013, FR-016 (the check) | Registration, secret issuance, retention, the sponsorship ceiling: U5. U3 reads the result, and supplies the human-only class (L1-28) |
| PF FR-009 to FR-012, FR-027 | Bootstrap, credential lifetime, renewal, revocation: U6 |
| PF FR-020 | Discharge at each entry point: U6 (S3) and U7 (S4). U3 supplies steps 5 to 10 |
| PF FR-023, FR-024 | Out of M1 |
| PF FR-025 | The attribution record: U4, U7. U3 returns the outcome it records (BR-ST-08) |
| PF §8b *Origin stamping*, delegated first-hop row | A delegation credential is absent in M1 (ID FR-019 to 021 out; A-4). A forwarded `delegated` origin is refused (D-AE-07) |
| PF §8b *Sponsorship*, *Bootstrap*, *What a credential asserts* | U5; U6 |
| PF §8b O1 to O4, O10, O11 | Steps 1 to 4 and the entry points: P1 at U6, U7 |
| PF §9 *Operations* | Exchange, renewal, revocation read: U6 |
| PF §10 | The control face |
| ID §7a, §8a, §8b; ID FR-022 | Human evaluation (`evaluateHuman`): U4 |
| ID FR-019 to FR-021 | Delegation: out of M1 |
| ID FR-015 | The human-grant ceiling: U4 |
| ID FR-001 to FR-012 | Human identity and material: U2, U4 |
| PF §6 (beyond keying on environment) | Isolation of deployment and material: U2, U6, Infrastructure Design |
| PF §16 | The managed-runtime impact statement; no U3 behaviour |

## PRD-Sourced Gaps

| Gap | Rows | Status |
|---|---|---|
| GAP-AE-001 | L1-07, L1-21, L1-25, L1-38 | Open, soorma-prd#30. Worked around (deny); no row is `Missing` |
| GAP-INT-007 (inherited) | L1-27 | Open, soorma-prd#25. Worked around (reject and stamp) |
