# Invariant Coverage Matrix: U7 `event-transport`

**Invariants source**: soorma-prd `references/platform/invariants.md` @
`prd-platform-foundations-v1.3` and @ `prd-identity-v1.0`. The text is identical at both tags
(re-checked 2026-11-12T22:03:40Z, at this unit's resumption).
**PRD compliance tables**: PF §15 @ `prd-platform-foundations-v1.3` (the main one for this unit)
and ID §15 @ `prd-identity-v1.0`: **I1 to I11 Addressed in both, none N/A, none Gap**.

**Status values**: `Covered` · `N/A` (with a reason) · `Missing` (blocking). Code Generation
moves rows to `Implemented`; Build and Test to `Verified`. *QA enrichment* marks a test case the
QA construction enrichment adds before the Construction Design PR gate.

**Result**: I1 to I10 `Covered`; I11 `N/A`. **0 `Missing`.** I1, I2, I4, and I5 are this unit's
centre: one channel per environment and every cache keyed on E; every obligation checked at
ingest from the raw request; envelope-bearing records, now structural both ways; the chain and
origin carried through hops by the one evaluator. I4's record availability rests on
**GAP-ET-001** (Open, soorma-prd#31), worked around.

| Code | PRD Status | Applies to Unit | Code-Level Risk in This Unit | Implementation Target | Verification Target | Status |
|---|---|---|---|---|---|---|
| I1 Isolation | Addressed | **Yes** | A Delivery reaching a stream in another environment; a channel shared by two environments; a cache key without E; a credential of E2 accepted at E; a `supersede` from E2 ending a stream in E | **Access and messaging paths**, each constrained on E: the revocation read (P5 cache key with E's three parts, BR-CK-02); the agent-facts read (U3's key with E); the record and the sponsor read (E's columns, U4 D-EHA-29); **E's fan-out channel**, one per environment deployment, for both `delivery` and `supersede` messages (BR-FO-01); credentials verified with E's agent verify halves only, O4 against E (D-ET-12) | TC-ET-006; TC-ET-015; *QA enrichment*: one test per path that nothing of E2 is read, written, delivered, or superseded at E (cache entries, records, deliveries, supersede messages) | Covered |
| I2 Perimeter enforcement | Addressed | **Yes** | S4 trusting a request because S2 or S3 saw it, or because the SDK built the draft; a stamped field overwritten instead of refused; the stream's checks skipped for "our" clients | Every check at S4 from the raw request: P1's presenter and `checkAgentRequest`, then `admit` (business-rules §11); a header claiming prior validation ignored (BR-CK-06); the stream's checks before each delivery (BR-SM-04) | TC-ET-007; TC-ET-021; TC-ET-024; *done when* 3, 4, 6, 7 by raw calls (D-ET-34); *QA enrichment*: every refusal in business-logic-model §8 sent as a raw call to the stack | Covered |
| I3 Portable credential | Addressed | Yes | Identity from a source address, host, or the stack's network; a subscriber trusted because it is "inside" | The agent and instance come from the verified credential only (BR-CK-02); nothing reads an address, host, or deployment label | *QA enrichment*: the same credential from another source address gives the same identity; a request with no credential from inside network `e` is refused | Covered |
| I4 Attribution recoverable | Addressed | **Yes** | A publish or subscribe with no record; a delivered event whose record was lost; an agent record without origin for an envelope-bearing operation; `hop` misplaced; the sponsor not resolvable | One record per accepted operation, written **before** it takes effect (BR-AT-ET-01; D-ET-16, 17); agent actor with resolved sponsor, chain, origin, re-broadening with `hop` the presenter's index (BR-AT-ET-02, 03); **P7 closed both ways**, writer and CHECK (BR-AT-ET-06). Record availability: GAP-ET-001, a synchronous write, fail closed (D-ET-09) | TC-ET-004; TC-ET-005; *QA enrichment*: reconstruct scope, actor, chain, origin, sponsor from the row alone at zero and one hop; an agent record outside the envelope-free list without envelope facts is refused by P7 and by the store; a failed write delivers nothing | Covered (GAP-ET-001 work-around) |
| I5 Monotonic authority | Addressed | **Yes** | S4 computing authority itself; a forwarded envelope granting the forwarder anything; origin rewritten or defaulted across a hop; a stream's authority widened later | **One evaluator**: `admit` (P3), and S4 imports nothing else of P2 or P3 (BR-EP-03); the forwarded envelope verified by seal and intersected, never trusted (U3); origin propagated unchanged (U3); a stream's authority fixed at open (D-ET-21) | TC-ET-005; TC-ET-020; TC-ET-010; TC-ET-011; *QA enrichment*: the import test (BR-EP-03); a low-authority publisher's event forwarded by a higher-authority agent is limited to the intersection | Covered |
| I6 Two faces | Addressed | **Yes** | A control-face operation on S4; a human credential accepted at S4; S4 sharing an NFR configuration with a control-face service | S4 is data-face only, its own contract document and NFR profile (BR-PK-01); human credentials refused by kind (D-ET-11) | TC-ET-012; TC-ET-024; *QA enrichment*: `event-ingest.openapi.yaml` holds no control-face operation | Covered |
| I7 Contract compatibility | Addressed | Yes | A new surface or widened code unclassified; the stream's events untyped; a change after the tag unversioned | business-rules §14: a new surface document, the Delivery payload bound published, `payload_too_large` widened, the stream's `end` codes open, all compatible and in `CHANGELOG.md`; the tag `contract-v0.1.0` after U7 (D-ET-33) | TC-ET-024; *QA enrichment*: U1's compatibility check over the completed contract | Covered |
| I8 Packaging rule | Addressed | **Yes** | Topic administration, durability, redelivery, or anything unassigned built partly or flagged; the test-only seeding fixture in S4's image | Packaging table below; live only, no topics (BR-PK-03) | *QA enrichment*: the packaging table re-checked at Code Generation and Build and Test; S4's image holds no seeding path (installed-packages check, D-ET-32) | Covered |
| I9 Mechanism, not instance | Addressed | **Yes** | The platform reading, validating, or classifying a payload; a tenant's event names hard-coded | `payload` is any JSON value, never read for meaning (BR-BF-06); no topic or event-type names exist. *Consistency fix from NFR Design (2026-11-13)*: the payload is **never inspected beyond its bound and its JSON well-formedness**; its numbers are never converted or compared (NP-ET-05) | *QA enrichment* (Code Generation review, with a check that S4 never inspects `payload` beyond its bound) | Covered |
| I10 Runtime-later | Addressed | Yes | A subscriber identified by its connection's origin; streams keyed on deployment topology; superseding keyed on host rather than lineage | Streams keyed on the credential's lineage (`cid`, D-ET-05); the instance asserted in the credential, never verified; environment from configuration. **Places tempted**: identifying a subscriber by its connection or host; keying superseding on the instance identifier (it may repeat, U6 D-AC-07) | *QA enrichment*: two instances of A asserting one name each hold their own stream | Covered |
| I11 No technology selection | Addressed | N/A | — | — | — | N/A: Construction is where technology is selected |

## I8 Packaging Table

PF §12 assigns 52 items to core and 8 to commercial; ID §12, 49 and 7. Every U7 capability is a
core item, and lands in `soorma-core`.

| Capability U7 implements | Assignment | Repository |
|---|---|---|
| Publish to an event namespace | PF §12 core: operation (§8a *Publish*); sufficiency bar item 6 | soorma-core |
| Subscribe to an event namespace, with live delivery | PF §12 core: operation (§8a *Subscribe*); item 6 | soorma-core |
| The perimeter's obligations at event ingest (O1 to O12) | PF §12 core; FR-020 | soorma-core |
| Envelope stamping and validation at ingest (through U3) | PF §12 core; FR-001 to FR-006 | soorma-core |
| Attribution of publish and subscribe | PF §12 core (record); FR-025 | soorma-core |
| The revocation read at ingest with the published bound (through U6's cache) | PF §12 core; FR-012 | soorma-core |
| The bounds (step-1 limits, the Delivery payload bound, the open-stream cap, the throttle) | **Security bounds, not tenant quotas**: platform constants governing no tenant's capacity (SECURITY-05, 11) | soorma-core |

**Not built, and absent from core in any form**: topics and topic administration (A-2); delivery
durability, ordering, redelivery, acknowledgement (GAP-INT-003, the Event plane's); revocation
initiation (deferred; test-only seeding outside the product's build); anything commercial. No
flag, stub, or disabled path for any.

## Invariant Findings

None.
