# Invariant Coverage Matrix: U3 `authority-evaluation`

**Invariants source**: soorma-prd `references/platform/invariants.md` @ `prd-platform-foundations-v1.3`
and @ `prd-identity-v1.0`. The text is identical at both tags (checked 2026-11-08, at U2).
**PRD compliance table**: PF §15 @ `prd-platform-foundations-v1.3` (the main one for this
unit): **I1 to I11 Addressed, none N/A, none Gap**.

**Status values**: `Covered` · `N/A` (with a reason) · `Missing` (blocking). Code Generation
moves rows to `Implemented`; Build and Test to `Verified`. **QA enrichment** marks a
verification target the QA construction enrichment adds after this stage.

**Result**: I1 to I10 `Covered`; I11 `N/A`. **0 `Missing`.** I5 is this unit's centre.

| Code | PRD Status | Applies to Unit | Code-Level Risk in This Unit | Implementation Target | Verification Target | Status |
|---|---|---|---|---|---|---|
| I1 Isolation | Addressed | Yes | A forwarded envelope from another environment accepted; a grant or standing set read from another environment; scope taken from deployment, so two environments sharing a deployment stamp the same scope | BR-FX-02 (the seal is bound to this environment's material), BR-FX-04 (scope equal to E's); BR-SEAM-03 (P11 answers only for E; another environment's set is empty); D-AE-08 (scope from the credential). **Access paths** (U3 has no persistence or messaging of its own): the Registration View port and the seam, both built for E and answering nothing for another environment; the Sealer, holding only E's sealing material | QA enrichment (another environment's seal, scope, and `grantedSet`) | Covered |
| I2 Perimeter enforcement | Addressed | Yes | A check that relies on the SDK having behaved (a draft without stamped fields, a forwarded envelope taken as checked); a surface skipping a step | Steps 5 to 10 run on every envelope-bearing request, from the raw body (BR-IN-04); a forwarded envelope is verified, never trusted (O10; BR-FX); one entry point, so no surface can skip or reorder a step (D-AE-04) | TC-AE-009; TC-AE-010; TC-AE-014; QA enrichment (no surface depends on P2) | Covered |
| I3 Portable credential | Addressed | Yes | Scope or identity derived from network location, host, or deployment | D-AE-08: scope, agent and instance from the verified credential only; the configured scope is a fail-closed comparison, never a source (D-AE-23) | TC-AE-001; QA enrichment | Covered |
| I4 Attribution recoverable | Addressed | Yes | The chain truncated or reordered; unknown fields dropped, destroying attribution downstream; a re-broadening record missing where it was load-bearing, or present where it was not; an envelope stamped that no later hop can forward | BR-CD-01 (never truncated); BR-ST-02, 03 (forwarded entries and unknown fields as received; A6); BR-ST-04 (a record exactly when load-bearing); BR-ST-06 (refuse rather than truncate); BR-ST-08 (the outcome returned for U7's record) | TC-AE-003; TC-AE-005; TC-AE-008; TC-AE-017; TC-AE-019 | Covered |
| I5 Monotonic authority | Addressed | **Yes: the centre** | Authority computed in a second place; a union where an intersection belongs; re-broadening that recovers what the delegating principal lacked, or passes to a later hop; escalation by omission (O12), **or by forwarding an autonomous envelope without a declaration (GAP-AE-001)**; a human-only permission reaching an agent; composition behind the seam | BR-AU-01 (one place); BR-AU-02, BR-SEAM-02 (composition in core); BR-AU-04 to 07 (the §8b rule); BR-OR-02, 04 (O12; D-AE-01); BR-AU-03 (human-only); D-AE-20 (records never grant); D-AE-04 (the order structural) | TC-AE-004; TC-AE-005; TC-AE-011; TC-AE-015; TC-AE-016; TC-AE-018; TC-AE-020; TC-AE-022; QA enrichment (GAP-AE-001; human-only; L1 to L5) | Covered |
| I6 Two faces | Addressed | Yes | A control-face operation or NFR configuration added to the data path | U3 adds no operation; P2 and P3's agent evaluation serve the data face's hot path (PF §9). U4's `evaluateHuman` is P3's control-face extension, with its own profile (Application Design, Q3 X) | Contract check: U3 adds no operation to any surface document | Covered |
| I7 Contract compatibility | Addressed | Yes | A contract change unclassified; an unknown field or value made fatal; a refusal changed after release | Every change classified (business-rules §13; `contract/CHANGELOG.md`); D-AE-07 (unknown value non-fatal); D-AE-14 (unknown fields preserved) | TC-AE-008; U1's compatibility test run over the changed conventions | Covered |
| I8 Packaging rule | Addressed | Yes | A richer policy model (Access Policy, commercial) built into core, enabled or stubbed; the seam made narrower than PF §12 states | Packaging table below; D-AE-02 (both halves of the seam, as PF §12 states, so no core API is narrowed) | Packaging table, re-checked at Code Generation and at Build and Test | Covered |
| I9 Mechanism, not instance | Addressed | Yes | A tenant's agents, permissions, or chains hard-coded | Only plane-declared identifiers appear in code: the required permissions (`event:publish`, `event:subscribe`) and the human-only class. Agents and sets come from ports | Code Generation review; QA enrichment | Covered |
| I10 Runtime-later | Addressed | Yes | The instance identifier treated as verified; the seal or the credential read as code identity; enforcement assuming a managed runtime | BR-ST-05 (instance recorded, not verified); the seal proves only that E stamped the envelope (D-WC-06); all checks at the perimeter, none in the agent's process | Code Generation review | Covered |
| I11 No technology selection | Addressed | N/A | — | — | — | N/A: Construction is where technology is selected |

## I8 Packaging Table

PF §12 assigns 52 items to core and 8 to commercial. Every U3 capability is a core item,
and lands in `soorma-core`.

| Capability U3 implements | PF §12 assignment | Repository |
|---|---|---|
| The envelope: field set, stamped/asserted partition, `maxChainDepth` (stamping and validation) | core: contract (the event envelope) | soorma-core |
| Authority intersection algebra | core: mechanism | soorma-core |
| Origin stamping, including O12 | core: mechanism | soorma-core |
| Chain append with `maxChainDepth`, and re-broadening evaluation | core: mechanism | soorma-core |
| O5 to O9 and O12 (their evaluation, for the entry points) | core: obligations | soorma-core |
| L1 to L5, satisfied by the minimal model | core: obligations | soorma-core |
| Policy-decision interface | core: seam | soorma-core (`seams/`, Apache 2.0, unpublished) |
| The minimal permission model's evaluation (P11's default) | core: the seam's built-in default (PF §12) | soorma-core |

**Not built, and absent from core in any form**: a richer permission grammar (hierarchy,
wildcards, conditions) and organization-scale policy (Access Policy; PF §12's anticipated
replacement). No flag, stub, or disabled path for either.

## Invariant Findings

**GAP-AE-001** bears on I5 (escalation by forwarding). It is raised (soorma-prd#30) and
worked around by the fail-closed reading, so I5 holds under the build whichever way the
PRD resolves it. No other finding.
