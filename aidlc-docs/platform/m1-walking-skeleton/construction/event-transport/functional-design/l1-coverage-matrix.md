# L1 Coverage Matrix: U7 `event-transport`

**Sources** (registered in `aidlc-state.md` `## PRD Intake`, each read at its tag):
- PF: soorma-prd/aiprd-docs/platform-foundations/requirements/prd.md @ `prd-platform-foundations-v1.3`,
  the main source for this unit
- ID: soorma-prd/aiprd-docs/identity/requirements/prd.md @ `prd-identity-v1.0`

**Status values**: `Covered` (design traced; implementation and verification targets set) ·
`N/A` (with a reason) · `Missing` (blocking). Code Generation moves rows to `Implemented`;
Build and Test moves them to `Verified`.

**Verification targets**: `TC-ET-001` to `024` are the inception specs
(`inception/test-cases/event-transport/`). *QA enrichment* marks a verification the QA
construction enrichment adds as a test case before the Construction Design PR gate; it replaces
each marker with a test-case ID. TC-AC ids are U6's, whose timelines U6 handed to S4.

**Result**: 36 applicable rows, all `Covered`. **0 `Missing`.** One rests on GAP-ET-001's
work-around (L1-26, Open, soorma-prd#31, raised here); L1-30 on GAP-INT-003's (Awaiting PRD:
Event); L1-08 on GAP-INT-007's; L1-10 on GAP-AE-001's.

---

## Applicable to U7

| # | L1 requirement | Design coverage | Implementation target | Verification target | Status |
|---|---|---|---|---|---|
| L1-01 | PF §7b, FR-001: **every event carries the envelope**; publish and subscribe are envelope-bearing | D-ET-01; BR-BF-01 | S4; `contract/event-ingest.openapi.yaml` | TC-ET-001; TC-ET-024 | Covered |
| L1-02 | PF §7b, FR-002, O5: **six fields platform-stamped**; a draft setting one is **rejected, never overwritten** | BR-BF-04 (U3's precedence); D-ET-13 | U3's `admit` through S4 | TC-ET-007; TC-ET-002 | Covered |
| L1-03 | PF §7b: **scope stamped from the presenting credential** | D-ET-13 (U3 D-AE-08) | `admit` with the Checked Agent Context | TC-ET-002 | Covered |
| L1-04 | PF FR-005, §17 *Compatibility Rules*: **unknown fields preserved and forwarded**; unknown enumerated values non-fatal | D-ET-19; BR-SM-02 | `admit` (U3 stamp); the Delivery as returned | TC-ET-023 | Covered |
| L1-05 | PF §7b: **trace context agent-asserted**, validated for form only; the platform emits no spans | D-ET-35 | `admit` (U3) | TC-ET-003 | Covered |
| L1-06 | PF §7b, §17, FR-004: **the draft declares its client contract version** | BR-BF-03 | `admit` step 5 at `/draft/clientContractVersion` | TC-ET-024; *QA enrichment*: a missing or unsupported version, and a differing header, at both operations | Covered |
| L1-07 | PF §7b, FR-006, O7: **the actor chain appended per hop by the perimeter; `maxChainDepth` enforced** | D-ET-13; BR-RF-ET (step 8) | `admit` | TC-ET-002; TC-ET-019 | Covered |
| L1-08 | PF §8b *Origin*: an autonomous first hop stamped from the registration's declaration; **an asserted origin rejected** (GAP-INT-007 work-around, M1-FR-01) | D-ET-13; §19 | `admit` (U3 BR-OR, BR-DV-04) | TC-ET-002; TC-ET-008 | Covered |
| L1-09 | PF O6, §8b: **origin propagated unchanged** on an event-triggered hop | D-ET-13 | `admit` | TC-ET-020; TC-ET-005 | Covered |
| L1-10 | PF O12: **autonomous origin denied unless the registration declares autonomy**; the forwarded case denied (GAP-AE-001 work-around) | BR-RF-ET (step 9) | `admit` | TC-ET-009 | Covered |
| L1-11 | PF §7b, §8b, FR-017: **re-broadening recorded only when load-bearing, at the declaring hop, local to it** | D-ET-18; BR-AT-ET-03; business-logic-model §7 | `admit`; the record's `hop` | TC-ET-005; *QA enrichment*: a non-load-bearing forward records `loadBearing` false and no hop | Covered |
| L1-12 | PF §8a *Publish*: **`event:publish` in E's namespace**; the intersection with the invoking principal; the standing set the ceiling (FR-014, FR-015, FR-018) | BR-PB-01; D-ET-13 | `admit` step 9 (P3, P11) | TC-ET-001; TC-ET-010 | Covered |
| L1-13 | PF §8a *Subscribe*: **`event:subscribe` in E's namespace**, likewise | BR-SB-01 | `admit` step 9 | TC-ET-001; TC-ET-011 | Covered |
| L1-14 | PF O8, O9: **deny by default**; deny unless effective authority suffices | BR-RF-ET-03; D-ET-14 | `admit`; `humanGrants` grants nothing | TC-ET-010; TC-ET-011 | Covered |
| L1-15 | PF §17: **the envelope is never usable to act**; acting needs the presenter's own credential | BR-PR-ET-01; BR-CK-02 | P1 at S4; the seal gives no authority (U3) | TC-ET-021; *QA enrichment*: a forwarded sealed envelope with no credential is `credential_refused` | Covered |
| L1-16 | PF O1, O2: **a credential presented, well-formed, unexpired**, checked at ingest | BR-CK-02; D-ET-12 | P1 `checkAgentRequest`; P5 verifier over E's agent verify halves | TC-ET-021; TC-ET-016 | Covered |
| L1-17 | PF O3, FR-012, §7a *Revocation State*: **read on every request at both granularities**; cached **at most one bound**, then **deny** | D-ET-12; BR-CK-02 to 04 | P5's cache at S4 | TC-ET-014; TC-AC-009, TC-AC-010, TC-AC-015 at S4 (*QA enrichment* assigns S4 test ids) | Covered |
| L1-18 | PF FR-012, §9: the bound **finite, published, platform-set, not tenant-configurable**; **one number**, the cache TTL | D-ET-15; BR-BND-01 to 03 | `PROPAGATION_BOUND_MS` passed to both caches; no configuration key | *QA enrichment*: the composition and no-key test (BR-BND-03) | Covered |
| L1-19 | PF §7a: revocation state **readable by no principal** | BR-CK-03; BR-SR-03; Stream End | No route; one refusal code for both granularities, at request and stream end | *QA enrichment*: a credential revocation and an agent revocation give the same response and the same `end` code | Covered |
| L1-20 | PF M1-FR-11 (T-2), O2, O3 applied to subscription: **delivery stops within the bound** once the subscriber's credential expires or is revoked | D-ET-04, 22; BR-SR-01 to 05 | The stream's checks before each delivery and every R | TC-ET-016; TC-ET-017 | Covered |
| L1-21 | PF O4, FR-021, §6 *Credentials*: **the credential's environment matches; deny on mismatch** | BR-CK-02; D-ET-08 | P1 O4 against P9's configured identity | TC-ET-006 | Covered |
| L1-22 | PF §6 *Events*: **the namespace derives from environment scope**; scope validated against the credential's environment on **both publish and subscribe**; a subscriber in another environment cannot receive | BR-FO-01; BR-SM-01 | One channel per environment deployment; `admit`'s scope check | TC-ET-015; TC-ET-006 | Covered |
| L1-23 | PF §6: **credential validation, revocation, and permission caches keyed on environment** | D-ET-12, 13 | P5's cache key and U3's facts key carry E's three parts | *QA enrichment*: cache isolation at S4 (entries for E never answer E2's request; one instance per environment) | Covered |
| L1-24 | PF O10, FR-020: **obligations identical at every entry point; no entry point treats another's traffic as pre-validated** | BR-CK-06; BR-RF-ET | S4 runs P1 and `admit` itself | TC-ET-021 | Covered |
| L1-25 | PF O11, FR-022: **environment identity configured, never inferred** | D-ET-13 | P9's scope for E | *QA enrichment*: S4 reads E from configuration only; nothing reads a host or deployment label | Covered |
| L1-26 | PF FR-025, §7b *Recoverability*: **every platform-resource operation produces an attribution record** carrying scope, actor, chain, origin; sponsor resolvable. **Availability of the record against PF §9: GAP-ET-001** | D-ET-07, 09, 16 to 18; BR-AT-ET-01 to 08 | P7 over `env-store`'s `Tx`; the reverse rule; a new migration | TC-ET-004; TC-ET-005; *QA enrichment*: reconstruct scope, actor, chain, origin and sponsor from the row alone at zero and one hop; a failed write delivers nothing / opens nothing | Covered (GAP-ET-001 work-around) |
| L1-27 | PF §7a *Agent Credential*: asserts **logical agent, environment, instance**; the instance asserted, recorded, not verified | D-ET-12; BR-AT-ET-02 | The chain entry and the record's instance from the verified token | TC-ET-002; TC-ET-004 | Covered |
| L1-28 | PF §9 *Failure Modes*: **revocation state unavailable: served from cache until the bound expires, then denied** | BR-CK-04, 05; BR-SR-05 | P5's cache | TC-AC-010 at S4 (*QA enrichment*) | Covered |
| L1-29 | PF §9 *NFR Profile*: the revocation read on the hot path **must not dominate request latency**; throughput scales with request volume | D-ET-12, 25; *consistency fix from NFR Requirements (2026-11-13)*: per instance only; across instances not demonstrated in M1 (one S4 per environment, NFR-ET-13), a residual | The cache; the throttle (NFR-ET-12) | *QA enrichment* (NFR Requirements' budget, reported) | Covered |
| L1-30 | PF §2 *What This Is Not*, OB-6: **delivery semantics are the Event plane's**; M1 delivers to live subscribers only, semantics stated as unspecified (GAP-INT-003 work-around, M1-FR-11) | D-ET-20; BR-FO-03; BR-PB-05 | The channel; the contract's pre-release statement | TC-ET-018 | Covered (GAP-INT-003 work-around) |
| L1-31 | PF §6 *Envelope (in flight)*: carries scope; **not stored here** | BR-PB-06 | No event store; the record holds envelope facts only | *QA enrichment*: after a publish, E's store holds the record and nothing of the payload | Covered |
| L1-32 | PF §17 *Namespacing Rules*, §6: **identifiers unique within an environment**; global uniqueness composed with scope | D-ET-08; BR-AT-ET-02 | A registered in E and in E2 as separate registrations; every key with E | TC-ET-006 (done when 6's E2 registration of A) | Covered |
| L1-33 | ID §8b, FR-023: **event ingest refuses every human credential**, by kind | D-ET-11; BR-PR-ET-01, 02 | P1's presenter at S4 | TC-ET-012 | Covered |
| L1-34 | ID §8b, PF FR-020: **a delegation credential**, alone or beside an agent's, **refused** (no delegation credential can be live in M1) | BR-PR-ET-01 | P1's presenter | TC-ET-013 | Covered |
| L1-35 | PF §9 *NFR Profile*, I6: **the data face has its own surface and NFR profile** | BR-PK-01 | `contract/event-ingest.openapi.yaml`; S4 | TC-ET-024; *QA enrichment*: S4's document holds no control-face operation | Covered |
| L1-36 | ID §10 *NFR Profile*, ID FR-009 (M1-NFR-08): **agent data-plane traffic unaffected by an organization-level outage** | D-ET-23; BR-PK-02 | No S1 dependency; the closure test | TC-ET-022 | Covered |

## Not Applicable to U7

| L1 requirement | Reason |
|---|---|
| PF §7a *Logical Agent Registration* and *Registration Secret* writes | U5's. S4 reads registrations only (agent facts, the sponsor) |
| PF §7a *Permission Grant*; §8a grant rows | No grant is made or read at S4 (D-ET-14) |
| PF FR-008 to FR-011 (secrets, bootstrap, renewal, revocation initiation) | U5's and U6's; initiation deferred in M1 |
| PF FR-013 retention; FR-025's read; §8a *Read attribution records* | Absent from M1 |
| PF §8b delegated origin; ID FR-019 to FR-021 | No delegation credential can be live in M1 (A-4, A-5); `delegatingPrincipal` never stamped |
| ID §7a human records | Refused by kind at S4, never read (L1-33) |

## PRD-Sourced Gaps

| Gap | Rows | Status |
|---|---|---|
| **GAP-ET-001** (raised in U7) | L1-26 | Open, soorma-prd#31. Worked around: a synchronous record, fail closed (D-ET-09) |
| GAP-INT-003 (inherited) | L1-30 | Awaiting PRD: Event, soorma-prd#13. Worked around: live only |
| GAP-INT-007 (inherited) | L1-08 | Open, soorma-prd#25. Worked around in U3: reject and stamp |
| GAP-AE-001 (inherited) | L1-10 | Open, soorma-prd#30. Worked around in U3: deny |
