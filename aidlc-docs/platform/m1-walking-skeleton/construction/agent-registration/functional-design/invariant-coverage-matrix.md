# Invariant Coverage Matrix: U5 `agent-registration`

**Invariants source**: soorma-prd `references/platform/invariants.md` @
`prd-platform-foundations-v1.3` and @ `prd-identity-v1.0`. The text is identical at both tags
(re-checked 2026-11-11, at this unit's resumption).
**PRD compliance tables**: PF §15 @ `prd-platform-foundations-v1.3` (the main one for this unit)
and ID §15 @ `prd-identity-v1.0`: **I1 to I11 Addressed in both, none N/A, none Gap**.

**Status values**: `Covered` · `N/A` (with a reason) · `Missing` (blocking). Code Generation
moves rows to `Implemented`; Build and Test to `Verified`. *QA enrichment* marks a test case the
QA construction enrichment adds before the Construction Design PR gate.

**Result**: I1 to I10 `Covered`; I11 `N/A`. **0 `Missing`.** I1, I4, I5, and I8 are this unit's
centre.

| Code | PRD Status | Applies to Unit | Code-Level Risk in This Unit | Implementation Target | Verification Target | Status |
|---|---|---|---|---|---|---|
| I1 Isolation | Addressed | **Yes** | A registration, secret, or agent-facts read with no environment constraint; an identifier unique across environments rather than per environment; an E2 credential registering in E | **Access paths** (all in E's own store; every row carries the three columns and every statement constrains on them, U4 D-EHA-29): the registration write and uniqueness (BR-RG-02); the registration lookup at issuance (BR-SE-03); the secret write (BR-SE-05); the agent-facts query (BR-AF-02); the held-set read (U4's). Credentials: E's material only (BR-PR-AR-02) | *QA enrichment*: one test per access path showing a principal of E cannot register into, issue for, look up, or read the facts of E2's registrations; the same `agent` in E and E2 are independent; E2's credential refused at E | Covered |
| I2 Perimeter enforcement | Addressed | Yes | The ceiling, human-only, or declaration check relying on a client (there is no human client library); an operation reachable without its checks | Every check runs at S2 from the raw request (§10 of the business rules); P3 decides, S2 enforces | TC-AR-022; *QA enrichment*: each rejection sent as a raw call | Covered |
| I3 Portable credential | Addressed | Yes | The sponsor or issuer taken from anything but the verified credential; identity from the network | The sponsor and issuer are the Checked Human Context's subject only (D-AR-09; BR-SE-05); nothing reads a source address or host | *QA enrichment*: the same credential from another source address registers with the same sponsor | Covered |
| I4 Attribution recoverable | Addressed | **Yes** | A registration or secret without its attribution record; the sponsor not resolvable later (a deletable registration); the snapshot not recorded, so the ceiling cannot be audited | **Governed records**: the registration (scope = `environment`; sponsor; snapshot; `registeredAt`), the secret (`issuer`, `registration`), each attribution record (scope, human actor, no origin). One transaction each (D-AR-18). Never deleted (D-AR-15). Sponsorship two hops (BR-AT-AR-02) | TC-AR-002; TC-AR-007; *QA enrichment*: reconstruct scope, actor, and sponsor from the records alone; resolve an agent record's sponsor through the registration; a failed attribution write leaves nothing | Covered |
| I5 Monotonic authority | Addressed | **Yes** | A second evaluator of a human's set (the ceiling computed in S2 or P4); a standing set wider than the sponsor's held set; a human-only permission reaching an agent; a declaration that could widen beyond the standing set; autonomy by omission | **D-AR-07** (one read, one evaluator: `evaluateHeld`, shared by `evaluateHuman` and `readHumanAuthority`); BR-SP-03 (ceiling); BR-RQ-03 (human-only, P3's class); BR-RQ-04 (declaration ⊆ standing); BR-RQ-05 (autonomy default `false`). Origin and the chain: not applicable to a direct human operation (no envelope); U3 and U7 hold them | TC-AR-009 to 012; TC-AR-003; *QA enrichment*: S2 and P4 import no evaluator but P3's; one held-set read per operation; `evaluateHuman`'s U4 tests unchanged | Covered |
| I6 Two faces | Addressed | Yes | A data-face operation added to S2, or registration added to a data-face surface; an agent credential accepted at S2 | Both operations on S2 in `control-gateway.openapi.yaml` (business-rules §12); one NFR profile, PF §10; `soorma_ac_` refused (D-AR-08) | Contract check: `control-gateway.openapi.yaml` holds no data-face operation; TC-AR-016 | Covered |
| I7 Contract compatibility | Addressed | Yes | A new operation or code unclassified; a change to a published shape | §13 of the business rules: two operations, five codes, check-order and disclosure text, all compatible, recorded in `contract/CHANGELOG.md` | U1's compatibility check over the changed contract; TC-AR-022 | Covered |
| I8 Packaging rule | Addressed | **Yes** | A commercial capability (sponsorship policy: who may sponsor, registrant and role constraints) built into core, enabled or stubbed; an unassigned capability (a registration read surface) landing in core | Packaging table below; D-AR-09, 20 | The packaging table, re-checked at Code Generation and at Build and Test | Covered |
| I9 Mechanism, not instance | Addressed | Yes | A tenant's agent names or permissions hard-coded | Agent identifiers come from requests (D-AR-02); only plane-declared identifiers appear in code (BR-ACC); test fixtures labelled as such | Code Generation review | Covered |
| I10 Runtime-later | Addressed | Yes | A registration bound to code identity or deployment topology; the secret treated as attestation | A registration asserts identity and authority only; the secret is client-credentials material, locally verified (PF §8b); nothing reads a host, cluster, or deployment label | Code Generation review | Covered |
| I11 No technology selection | Addressed | N/A | — | — | — | N/A: Construction is where technology is selected |

## I8 Packaging Table

PF §12 assigns 52 items to core and 8 to commercial; ID §12, 49 and 7. Every U5 capability is a
core item, and lands in `soorma-core`.

| Capability U5 implements | Assignment | Repository |
|---|---|---|
| Logical agent registration (all eight attributes; never deleted) | PF §12 core: records (*Logical Agent Registration*, *Permission Grant*); operations (§8a *Register logical agent*, *Grant standing permissions at registration*) | soorma-core |
| Standing permissions granted at registration, the ceiling (grantable = held) and its snapshot, with the human-only refusal | PF §12 core: mechanism ("sponsorship grant-time ceiling check, against held authority with the human-only class"); ID §12 core (FR-013's declarations) | soorma-core |
| The re-broadening declaration and autonomy declared (recorded) | PF §12 core: records | soorma-core |
| Registration secret issuance, with its issuer | PF §12 core: record (*Registration Secret*); operation (§8a *Issue a registration secret*); ID §12 core (FR-026's issuer) | soorma-core |
| Attribution recording for both operations | PF §12 core (record) | soorma-core |

**Not built, and absent from core in any form**: sponsorship policy (who may sponsor, registrant
and role constraints; PF §12 commercial); a registration read surface (unassigned, D-AR-20); the snapshot's core read through FR-025 (core, absent from M1);
secret rotation and retirement, suspend, resume, retire, and revocation (core, but absent from
M1). No flag, stub, or disabled path for any.

## Invariant Findings

None.
