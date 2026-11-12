# Business Rules: U7 `event-transport`

**Unit**: U7 `event-transport` (soorma-core#10). Data face, environment level. Builds the
deployable S4 `event-ingest`, with `publish` and `subscribe`, and completes the wire contract
**Built against**: PF @ `prd-platform-foundations-v1.3` (the main source), ID @ `prd-identity-v1.0`
**Decisions from**: the Functional Design plan, Q1 to Q9 and proposals P-01 to P-27, answered
2026-11-12T23:11:09Z (recorded verbatim in `audit.md`). Q1 with the user's condition (the
additive option only; every U3 test unchanged; new tests for the option). Q5 with the user's
addition (superseding across instances, its failure mode, its test, §7). Q7 with the user's
approval of exactly one class-3 change (§15). **Q9 classified as specification by the user:
GAP-ET-001**, raised as soorma-prd#31 and worked around (D-ET-09)
**Entities**: [domain-entities.md](domain-entities.md). **Logic**:
[business-logic-model.md](business-logic-model.md)
**Inherited rules**: U1's envelope, draft, Delivery, error and check-order rules
(`construction/wire-contract/functional-design/business-rules.md`: BR-ENV, BR-DR, BR-FC, BR-DL,
BR-ERR, BR-PR); U3's entry point and every rule behind steps 5 to 10
(`construction/authority-evaluation/`: BR-IN, BR-VR, BR-DV, BR-FX, BR-CD, BR-OR, BR-AU, BR-ST,
D-AE-01, 04, 08, NP-02, 04, 05); U4's presenter matrix, attribution, throttle and environment
store (`construction/env-human-access/`: BR-PR, BR-AT, D-EHA-29, 31, NP-EHA-05, 07, 15); U5's
agent-facts source (`construction/agent-registration/`: D-AR-19, BR-AT-AR-02); U6's agent
checks, revocation cache and envelope-free list (`construction/agent-credentials/`: D-AC-03, 14,
18, 27, 33, NP-AC-01, 05). This document does not restate them except where U7 extends them
**Specification gaps**: **GAP-ET-001** (Open, soorma-prd#31; raised here). Inherited, work-arounds
kept: GAP-INT-003 (Awaiting PRD: Event, soorma-prd#13), GAP-INT-007 (Open, soorma-prd#25),
GAP-AE-001 (Open, soorma-prd#30). See §19

Module names are the Application Design's: P1 `perimeter`, P2 `envelope`, P3 `authority`, P4
`registry`, P5 `credentials`, P7 `attribution`, P9 `config`, P11 `policy-decision`. Symbols:
**B** the propagation bound, `PROPAGATION_BOUND_MS` (60 s, U6 NFR-AC-01); **L** the agent
credential's lifetime (15 min, U6 NFR-AC-02); **R** a stream's check interval and **P** the
Delivery payload bound, both set at NFR Requirements.

---

## 1. Decisions

| ID | Decision | Source | Class |
|---|---|---|---|
| **D-ET-01** | **The body form.** Publish's body is a closed `{ draft, payload }`; subscribe's a closed `{ draft }`. U3's `admit` gains **one additive option**, the Body Form: where the draft sits and which other members the body holds. Without it `admit` behaves exactly as today, and **every U3 test stays unchanged**; **new tests cover the option**. Step 5: a body that is not an object is `malformed_request` (`""`); a `draft` member that is missing or not an object is `malformed_request` (`/draft`); then the draft's version at `/draft/clientContractVersion`, and the header rule. Step 6: the body's and the draft's schema together, under the published precedence (stamped, then unknown, then any other), pointers from the body's root; then the payload bound (D-ET-27) | Q1 A, with the user's condition | Technology |
| **D-ET-02** | **S4 does not give the caller its own hop's envelope.** Publish answers `202` with no body; a subscribe's stream carries only `delivery` and `end`. Each hop's stamped envelope is in its attribution record. Returning it later is additive | Q2 A | Technology |
| **D-ET-03** | **A stream ends with one `end` event, then closes.** Data `{ code }`, an open string: `credential_expired`, `credential_refused`, `unavailable`, `superseded`, `overflow` (domain-entities *Stream End*). SSE comment lines are heartbeats (interval at NFR Requirements). The contract names both events | Q3 A | Technology |
| **D-ET-04** | **An open stream observes revocation through P5's cache**, before every delivery to it and on a sweep every R. **No Delivery is written to a stream after revocation + B**; the connection closes within R after that. With no revocation answer younger than B, the stream ends `unavailable`. One revocation path at S4 | Q4 A | Technology |
| **D-ET-05** | **At most one open stream per credential lineage in E.** A subscribe registers its stream, then supersedes any earlier stream of the same `cid`: on its own instance directly, and **on the other instances in E through a `supersede` message on E's fan-out channel** (§7). **Failure mode**: if a supersede message is lost, the earlier stream still ends at its own credential's `exp`, at most L later. **Tested on one instance**; the cross-instance case is a **stated residual** if the M1 stack cannot exercise it (§17) | Q5 A, with the user's addition | Technology |
| **D-ET-06** | **A subscriber that cannot keep up**: when its stream's send buffer is full, the stream ends with `end` `overflow`; nothing is dropped silently | Q6 A | Technology |
| **D-ET-07** | **P7's envelope rule is closed in both directions**: an agent record for an operation outside the envelope-free list (`exchangeBootstrap`, `renewAgentCredential`) must carry envelope facts. P7's writer refuses it, and a new migration adds the same CHECK (`0001` to `0004` untouched). **U5's constructed record changes exactly as approved** (class 3, §15). P7 requires nothing more of an `exchangeBootstrap` record than an agent actor (registration, instance, sponsor) and no envelope facts: checked 2026-11-12 against `checkRecord` and the store's CHECKs, so the user's stop condition does not fire | Q7 A, the user's approval | Technology |
| **D-ET-08** | ***Done when* 6 uses a real E2 credential**, chained in the journey: H obtains an E2 environment credential, self-grants `agent:register` there, registers A in E2 (the same identifier, a separate registration), issues a secret, and an instance bootstraps at E2's S3. A's publish to E with that credential is `credential_refused` (O4), and B, subscribed in E, receives nothing. The same test presents A's E credential to E2's S4 (refused) | Q8 A | Technology |
| **D-ET-09** | **GAP-ET-001 work-around**: the record is written **synchronously** in E's store, in the operation's own transaction, before the operation takes effect; when it cannot be written, the operation is `unavailable` (503, `Retry-After`). So in M1, E's store is S4's availability floor for new publishes and subscribes (§17), against the reading of PF §9 that the bound is "the outage window during which authorization continues". Raised as soorma-prd#31 with both readings; the PRD chooses | Q9 B (specification, the user's classification); routing A then D | Specification (worked around) |
| D-ET-10 | **Paths and ids**: `publish` `POST /events`, `subscribe` `POST /subscriptions`, each naming exactly one security scheme, `agentCredential`. The ids name the attribution records' operations | P-01 | Technology |
| D-ET-11 | **Presenter**: exactly one `Authorization: Bearer soorma_ac_`, no `Soorma-Delegation`; any human, delegation or unknown kind, two credentials, or a credential beside `Soorma-Delegation` is `credential_refused` **by kind, without verifying** | P-02; ID §8b, FR-023 | Inherited |
| D-ET-12 | **Steps 1 to 4** by P1's `checkAgentRequest(rawHeaders, { verify, revocation })`: `verify` is P5's verifier over **E's agent verify halves only**; `revocation` is `createRevocationCache(directRevocationSource(store), { ttl: PROPAGATION_BOUND_MS, clock })`, one per instance | P-03; D-AC-03, 18, 27 | Inherited |
| D-ET-13 | **The entry point**: built once per instance and provided through NestJS, with P9's scope, E's seal key ring, `createCachingAgentFacts(agentFactsFromStore(store), { ttl: PROPAGATION_BOUND_MS, clock })`, P11, `humanGrants` (D-ET-14), and the security log. `admit` runs **once** per publish and per subscribe. S4 imports nothing of P2 or P3 but the entry point | P-04; D-AE-04; NP-04, 05 | Inherited |
| D-ET-14 | **`humanGrants` grants nothing at S4 in M1**: no delegated origin starts (A-5), so no human enters an agent's chain. S4's role has no privilege on `grants` | P-05 (accepted by the user) | Technology |
| D-ET-15 | **One bound, one constant**: `PROPAGATION_BOUND_MS` is the TTL of both caches at S4; **no configuration key** exists for it, and a test proves both | P-06; the user's correction; PF FR-012 | Inherited |
| D-ET-16 | **Publish writes, then delivers**: the record (D-ET-09) commits, then the Delivery goes to E's channel, then `202`. A failed write: `unavailable`, nothing delivered. A failed hand-off after the commit: `unavailable`, the record stands | P-07 | Technology |
| D-ET-17 | **Subscribe writes, then opens**: the open-stream cap (D-ET-25), then the record, then the stream is registered and supersedes (D-ET-05), then `200` | P-08 | Technology |
| D-ET-18 | **The record**: domain-entities *Attribution Record*. The sponsor read from the registration in the record's transaction; `hop` the chain's last index exactly when load-bearing | P-09; D-EHA-31; BR-ST-08 | Technology |
| D-ET-19 | **The Delivery** is the publish's stamped envelope and seal, and its payload, the same for every stream | P-10; BR-DL-01 to 03 | Inherited |
| D-ET-20 | **Fan-out**: every open stream in E, on every instance in E, the publisher's own included; nothing leaves E; live only; no `id:`; `Last-Event-ID` ignored | P-11; GAP-INT-003 | Technology (work-around for GAP-INT-003) |
| D-ET-21 | **A stream's authority is evaluated once, at open** | P-12; NFR-AE-16 | Technology |
| D-ET-22 | **Expiry ends a stream at its credential's `exp` exactly**; S4's `verify` callback keeps the `exp` | P-13 | Technology |
| D-ET-23 | **No organization-level dependency**; S4's production closure excludes `@soorma/org-identity` | P-14; M1-NFR-08; NP-EHA-15 | Inherited |
| D-ET-24 | **Problems through P1**; the shared assertion on every Problem; after a stream's `200`, only `end` | P-15; BR-PE-06 | Inherited |
| D-ET-25 | **Throttle and the open-stream cap**: service-kit's per-instance semaphore around each publish and each subscribe's opening (an open stream holds no slot); a per-instance cap on open streams, checked after step 10, a subscribe that supersedes a stream of its own lineage on the same instance not counting against it. Over either: `unavailable` (503, `Retry-After`). Values at NFR Requirements | P-16; SECURITY-11 | Technology |
| D-ET-26 | **Step-1 limits**: subscribe's admits a maximum-size forwarding draft (U3's floor); publish's that plus P and the wrapper. A test sends a maximum-size forwarding draft through step 1 of both; the depth test runs at S4's actual limit | P-17; U3 obligations | Technology |
| D-ET-27 | **The Delivery payload bound P**, on the payload's JCS serialization; a publish over it is `payload_too_large` (413) at step 6, after the schema. Published in `envelope.md` | P-18; BR-DL-04 | Technology |
| D-ET-28 | **Security log and alerts** under the shared-name rule; S4's rules never group by `agent` | P-19 | Technology |
| D-ET-29 | **S4's own database role**: `SELECT` on `registrations`, `credential_revocations`, `agent_revocations`; `INSERT` on `attribution_records`; nothing else | P-20; D-ID-AC-07 | Technology |
| D-ET-30 | **What S4 holds**: TLS, its database password, E's agent verify halves, E's seal key ring. No signing key, no human or organization material, no log-pseudonym key | P-21 | Technology |
| D-ET-31 | **Ports** 8446 (E) and 8447 (E2), on the environment's network only | P-22 | Technology |
| D-ET-32 | **The image**: built, secret-scanned, and through U6's installed-packages check | P-23 | Technology |
| D-ET-33 | **The contract** completed (§14); tagged `contract-v0.1.0` on `main` after GitHub shows U7's code PR merged, with the user's go-ahead | P-24; D-WC-02 | Technology |
| D-ET-34 | ***Done when* 3, 4, 6, 7 by raw calls** after TC-AC-093; other stack cases in U7's own e2e file | P-25 | Technology |
| D-ET-35 | **Done when 5 is soorma-sdk's**; S4 carries trace context and emits no spans | P-26 | Inherited |
| D-ET-36 | **Misuse cases** as §16 | P-27 | Technology |

---

## 2. Presenter and Steps 1 to 4 (BR-PR-ET, BR-CK)

| ID | Rule | Source |
|---|---|---|
| BR-PR-ET-01 | Both operations take **exactly one** `Authorization: Bearer soorma_ac_…`, counted on the raw header list, and no `Soorma-Delegation` header. Anything else is `credential_refused` **by kind, without verifying**: `soorma_ec_` and `soorma_si_` (human), `soorma_dc_` (delegation, reserved), an unknown prefix, none, two credentials, a credential beside `Soorma-Delegation`, a credential elsewhere | D-ET-11; ID §8b, FR-023; M1-FR-09 |
| BR-PR-ET-02 | S4 holds **no human or organization verify material**, so it cannot verify a human credential even by mistake | D-ET-30 |
| BR-CK-01 | Step 1: a body over its operation's limit is `payload_too_large`, before any credential is looked at | D-ET-26 |
| BR-CK-02 | Steps 2 to 4 are P1's `checkAgentRequest`: presenter, O1, O2 (`credential_refused`, then `credential_expired` only after verifying), O4 field by field against P9's configured identity, then O3 through the cache at **both granularities** (the `cid` and the logical agent) | D-ET-12; D-AC-27 |
| BR-CK-03 | A revoked answer, at either granularity, is `credential_refused`; the granularity goes to the security log only | BR-RN-03 (U6); PF §7a |
| BR-CK-04 | No revocation answer younger than B: `unavailable` (503, `Retry-After`) | PF FR-012; BR-RC-03 (U6) |
| BR-CK-05 | **With the store down, steps 1 to 3 answer exactly**: a malformed, foreign-kind, unverifiable, wrong-environment, or expired credential is refused as it would be with the store up, never `unavailable`. Step 4 then serves any cached answer younger than B | U6's pattern; TC-AC-010 at S4 |
| BR-CK-06 | Nothing on S4's request path consults another entry point's result: a header claiming prior validation is ignored, and every check runs | PF O10; TC-ET-021 |

## 3. The Entry Point (BR-EP)

| ID | Rule | Source |
|---|---|---|
| BR-EP-01 | Built **once per S4 instance**, before the first request: `createEnvelopeAdmission` with P9's scope for E, E's seal key ring (P9's `loadSealKeys`), the agent-facts source wrapped by `createCachingAgentFacts` with `ttl` `PROPAGATION_BOUND_MS`, P11's policy decision, `humanGrants` (BR-EP-04), the accepted versions, and S4's security log. Provided to NestJS as one provider | D-ET-13; NP-05 |
| BR-EP-02 | `admit` is called **once** per publish and per subscribe, after steps 1 to 4 pass, with the parsed body, the Body Form (§4), every `Soorma-Contract-Version` value, the Checked Agent Context, the required permission (`{event:publish}` or `{event:subscribe}`), and the request id | D-ET-13; BR-IN-01, 02 (U3) |
| BR-EP-03 | **S4 imports nothing of P2 or P3 except the entry point**, and no other code path stamps, seals, verifies a seal, or evaluates authority (a test over S4's source and its built output) | D-AE-04; I5 |
| BR-EP-04 | `humanGrants` returns the empty set for any principal. In M1 no human enters an agent's chain (A-5), so it is never the deciding term; if one did, deny by default holds | D-ET-14; PF O9 |
| BR-EP-05 | A refusal from `admit` becomes a Problem through P1 (§12). An exception from `admit` is `internal_error` | BR-IN (U3) |

## 4. The Request Bodies (BR-BF)

| ID | Rule | Source |
|---|---|---|
| BR-BF-01 | Publish's body is `{ draft, payload }`, both required, nothing else. Subscribe's is `{ draft }`, nothing else | D-ET-01 |
| BR-BF-02 | `draft` is U1's draft exactly: closed top level (`clientContractVersion`, `traceContext`, `inbound`), and every rule U3 applies to it | BR-DR (U1); BR-DV (U3) |
| BR-BF-03 | **Step 5**, in order: the body is not a JSON object: `malformed_request`, pointer `""`; `draft` missing or not an object: `malformed_request`, pointer `/draft`; then U3's version rules, reading only `/draft/clientContractVersion`, then the header rule | D-ET-01; BR-VR (U3) |
| BR-BF-04 | **Step 6**: the body's members and the draft's schema are judged **together**, under the published precedence: a platform-stamped field at the draft's top level is `stamped_field_set`, whatever else fails; otherwise a member the body does not define, or a field the draft or its `traceContext` does not define, is `unknown_field`; otherwise any other failure (a missing `payload` included) is `malformed_request`. `errors[]` lists the fields failing with the winning code, pointers from the body's root (`/draft/traceContext/traceparent`, `/extra`), at most 10 | D-ET-01; BR-DV (U3); D-AE-18 |
| BR-BF-05 | Then, for publish only, the payload bound: `payload` over P on its JCS serialization is `payload_too_large` (413) | D-ET-27 |
| BR-BF-06 | `payload` is never read for meaning: any JSON value passes the schema (I9). Its value is carried as received | BR-DL-03 (U1) |
| BR-BF-07 | **U3's `admit` without the Body Form behaves exactly as before**: every U3 test passes unchanged, and new tests in `packages/authority` cover the option (both forms, every step-5 and step-6 case above, the pointers, the bound) | D-ET-01, the user's condition |

## 5. Publish (BR-PB)

| ID | Rule | Source |
|---|---|---|
| BR-PB-01 | Required authority `{event:publish}` in E's namespace: the intersection across the chain, the standing set the ceiling, re-broadening at the declaring hop only (all U3's) | PF §8a, FR-014, FR-017, FR-018 |
| BR-PB-02 | After `admit` admits, **one transaction writes the publish record** (§9). Only after it commits is the Delivery handed to E's channel | D-ET-16, D-ET-09 |
| BR-PB-03 | The record cannot be written: `unavailable`; nothing is delivered | D-ET-09 |
| BR-PB-04 | The hand-off fails after the commit: `unavailable`. The record stands: an authorized attempt, recorded, append-only | D-ET-16 |
| BR-PB-05 | Success is `202 Accepted` with no body, whether or not anyone is subscribed. `202` means accepted for live delivery to the streams open in E at that moment; it promises no delivery | D-ET-02; GAP-INT-003 |
| BR-PB-06 | Publish has no effect beyond the record and the Delivery: nothing about the event is stored | GAP-INT-003; PF §6 *Envelope (in flight)* |

## 6. Subscribe and the Stream (BR-SB, BR-SM)

| ID | Rule | Source |
|---|---|---|
| BR-SB-01 | Required authority `{event:subscribe}` in E's namespace, as BR-PB-01 | PF §8a |
| BR-SB-02 | After `admit` admits: the open-stream cap (D-ET-25); then one transaction writes the subscribe record (§9); then the stream is registered on the instance and supersedes (§7); then `200`, `text/event-stream`, `Cache-Control: no-store`, with `Soorma-Contract-Version` and `Soorma-Request-Id` | D-ET-17 |
| BR-SB-03 | The record cannot be written: `unavailable`, a Problem; no stream opens | D-ET-09 |
| BR-SB-04 | The subscribe's own stamped envelope is recorded and given to no one; it does not enter any Delivery | D-ET-02 |
| BR-SM-01 | A stream receives, as `delivery` events, every Delivery accepted in E **after it was registered**, from any S4 instance in E, the subscriber's own publishes included. Nothing earlier, nothing from another environment | D-ET-20; M1-FR-11 |
| BR-SM-02 | Each `delivery` event's data is the Delivery exactly (D-ET-19). No SSE `id:` field; a `Last-Event-ID` header is ignored | D-ET-20 |
| BR-SM-03 | Heartbeats are SSE comment lines, at an interval set at NFR Requirements | D-ET-03 |
| BR-SM-04 | **Before each delivery to a stream**, S4 checks: the stream's credential has not expired, and its revocation answer through P5's cache is `not_revoked`. Otherwise the stream ends (§8) and the Delivery is not written to it | D-ET-04, 22 |
| BR-SM-05 | A stream's authority is evaluated once, at open. A Delivery is not an operation of the subscriber's, and is neither re-authorized nor attributed | D-ET-21 |
| BR-SM-06 | **The send buffer** is bounded (NFR Requirements). A Delivery that would overflow it ends the stream: the queued deliveries are discarded, `end` `overflow` is written, the connection closes. If the connection cannot take even that, it is closed after a short grace (NFR Requirements) | D-ET-06 |
| BR-SM-07 | **Every stream ends with exactly one `end` event** (domain-entities *Stream End*), unless the connection is already gone; then it is closed. A stream never reopens: the subscriber subscribes again | D-ET-03 |
| BR-SM-08 | An S4 instance stopping ends its streams with `end` `unavailable` | D-ET-03 |
| BR-SM-09 | The client closing its connection ends the stream silently; it is removed from the instance's registry | — |

## 7. Fan-Out and Superseding (BR-FO)

| ID | Rule | Source |
|---|---|---|
| BR-FO-01 | **E's fan-out channel** carries Channel Messages between the S4 instances of E only. Each environment's deployment has its own channel; nothing on E's channel reaches E2, and an S4 of E2 is not on it | D-ET-20; PF §6 *Events*; I1 |
| BR-FO-02 | A `delivery` message is offered to every open stream on every instance in E, the instance that accepted the publish included | BR-SM-01 |
| BR-FO-03 | The channel stores, replays, orders and acknowledges nothing. A message an instance misses is lost for its streams (GAP-INT-003: semantics unspecified) | GAP-INT-003 |
| BR-FO-04 | **Superseding on one instance**: when a stream of lineage `cid` is registered and the same instance has an open stream of that `cid`, the earlier one ends with `end` `superseded`, after the new one is registered, so no Delivery accepted in between is missed by both | D-ET-05 |
| BR-FO-05 | **Superseding across instances**: the instance registering the new stream then sends a `supersede` message on E's channel with the `cid` and the new stream's order key (its opening time and id). Each instance in E that holds an open stream of that `cid` **ordered before** the new one ends it `superseded`. The order key is total, so two racing subscribes of one lineage leave exactly the later-ordered one open | D-ET-05, the user's addition |
| BR-FO-06 | **Failure mode**: if a `supersede` message is lost, the earlier stream stays open and still ends at its own credential's `exp`, **at most L later**. Until then the lineage has two streams, and each Delivery reaches both | D-ET-05, the user's addition |
| BR-FO-07 | Order keys come from each instance's clock: with skew between instances, the stream that survives a race may be the earlier one in real time; at most one survives either way | D-ET-05 |
| BR-FO-08 | **Verification**: superseding is tested on one instance (BR-FO-04), and in process on two instances sharing one channel if the channel's design allows it (NFR Design). If the M1 stack runs one S4 per environment, **the cross-instance case is not exercised on the stack, and is a stated residual** (§17) | D-ET-05, the user's addition |

## 8. Revocation and Expiry on an Open Stream (BR-SR)

| ID | Rule | Source |
|---|---|---|
| BR-SR-01 | **Expiry**: a stream ends at its presented credential's `exp` exactly, with `end` `credential_expired`, whether or not a Delivery is pending | D-ET-22; PF O2 |
| BR-SR-02 | **Revocation**: S4 asks P5's cache (the same cache as step 4) about the stream's `cid` and logical agent before each delivery (BR-SM-04) and on a **sweep every R** over all open streams of the instance | D-ET-04 |
| BR-SR-03 | A revoked answer, either granularity, ends the stream with `end` `credential_refused`; the granularity goes to the security log only | D-ET-04; PF §7a |
| BR-SR-04 | **The bound, as delivered**: the cache answers `not_revoked` only from a read issued less than B ago, so any check at or after revocation + B answers revoked. **No Delivery is written to a stream after revocation + B**, and the connection closes no later than revocation + B + R | D-ET-04; M1-FR-11 ("delivery stops within the propagation bound") |
| BR-SR-05 | **Revocation unreadable**: when the cache has no answer younger than B and cannot read one, the stream ends with `end` `unavailable`. Within B, a store outage is invisible to open streams | D-ET-04; PF §9 *Failure Modes* |
| BR-SR-06 | A stream's credential is never renewed in place: a subscriber renews (S3) and subscribes again before `exp`; the new stream supersedes the old one (§7) | D-ET-05 |

## 9. Attribution (BR-AT-ET) and P7's Reverse Rule

| ID | Rule | Source |
|---|---|---|
| BR-AT-ET-01 | **One record per accepted publish and per accepted subscribe**, written through P7 over `env-store`'s `Tx`, in its own transaction, **before** the operation takes effect (the hand-off, the stream). It is the transaction's only write: neither operation stores anything else | D-ET-16, 17; BR-AT (U4); D-EHA-17 |
| BR-AT-ET-02 | The record's fields are domain-entities *Attribution Record*. The **sponsor is read from the registration inside the same transaction**, as of the write (BR-AT-AR-02, D-EHA-31); the registration always exists (never deleted) | D-ET-18 |
| BR-AT-ET-03 | Envelope facts come from `admit`'s result: `chain` the stamped `actorChain`, `origin` the stamped origin, `loadBearing` from the outcome, and **`hop` = the chain's last index exactly when load-bearing**: re-broadening is local to the presenter's hop (PF §8b), and U3's outcome carries no hop. P7 and the store's CHECKs bound it | D-ET-18; BR-ST-08 (U3) |
| BR-AT-ET-04 | **Scope, actor, chain, origin, and sponsor are recoverable from the row alone** (FR-025's read, absent in M1, needs nothing else) | PF FR-025, §7b *Recoverability*; I4 |
| BR-AT-ET-05 | Refusals write no record. A refusal is a security-log event | BR-AT-09 (U4) |
| BR-AT-ET-06 | **P7 closes the rule both ways**: `ENVELOPE_BEARING` agent operations are `publish` and `subscribe`; an agent record for **any operation outside the envelope-free list must carry envelope facts**. P7's writer refuses it before any SQL; a new migration adds the same CHECK on `attribution_records` (`actor_kind <> 'agent' OR operation IN (envelope-free list) OR chain IS NOT NULL`), alone in its migration as U6's `0004` was | D-ET-07 |
| BR-AT-ET-07 | With U4's all-or-none CHECK, an agent record for `publish` or `subscribe` therefore has chain, origin, and the re-broadening outcome, and one for `exchangeBootstrap` or `renewAgentCredential` has none | D-ET-07; D-AC-33 |
| BR-AT-ET-08 | The record cannot be written: the operation is `unavailable` (GAP-ET-001 work-around, D-ET-09) | D-ET-09 |

## 10. The Bound (BR-BND)

| ID | Rule | Source |
|---|---|---|
| BR-BND-01 | **One number**: `PROPAGATION_BOUND_MS` from `packages/credentials`, passed as `ttl` to P5's revocation cache (D-ET-12) and to U3's agent-facts cache (D-ET-13). No second number exists for either | D-ET-15; PF FR-012, §9; NFR-AE-10 |
| BR-BND-02 | **No configuration key**: neither `tenancy.yaml`'s schema nor S4's settings defines one, so the bound is platform-set and not tenant-configurable | PF FR-012 |
| BR-BND-03 | **A test proves it**: S4's composition is built and both caches' `ttl` is `PROPAGATION_BOUND_MS`; neither the tenancy schema nor S4's settings names a key for a bound, TTL, or propagation interval. U6's TC-AC-038 already ties the constant to the published sentence in `credentials.md` | the user's correction |
| BR-BND-04 | R (the stream sweep) is not a second bound: it bounds only how late a connection closes after deliveries have stopped (BR-SR-04) | D-ET-04 |

## 11. Refusals and the Check Order (BR-RF-ET)

Both operations, in order. The first failing check decides the response. U1's `errors.md`
*Check order*, with S4's specifics.

| Step | Check | Code |
|---|---|---|
| — | Throttle, at request start | `unavailable` (503) |
| 1 | Body over the operation's limit | `payload_too_large` (413) |
| 2 | Presenter (BR-PR-ET-01) | `credential_refused` (401) |
| 3 | O1 verification with E's agent verify halves; O2 expiry | `credential_refused`; then `credential_expired` (401) |
| 4 | O4 environment; O3 revocation through the cache | `credential_refused`; `unavailable` (503) |
| 5 | Body form and contract version (BR-BF-03) | `malformed_request`; `unsupported_contract_version` (400) |
| 6 | Body and draft schema (BR-BF-04); then, for publish, the payload bound | `stamped_field_set`, `unknown_field`, `malformed_request` (400); `payload_too_large` (413) |
| 7 | Forwarded context: the bound, the seal, scope, version | `invalid_inbound_context` (400) |
| 8 | Chain depth | `chain_too_deep` (400) |
| 9 | Agent facts (unreadable: `unavailable`); origin, O12 (GAP-AE-001: forwarded autonomous with no declaration denied); then the required permission | `forbidden` (403) |
| 10 | The envelope to be stamped over 16 KiB | `envelope_too_large` (400) |
| — | Subscribe: the open-stream cap (D-ET-25) | `unavailable` (503) |
| write | The record (D-ET-09); for publish, the hand-off | `unavailable` (503) |

| ID | Rule | Source |
|---|---|---|
| BR-RF-ET-01 | Every refusal writes exactly one security-log event naming the code, the internal reason, the request id, E, and, once known, the agent and instance. Never a token, seal, envelope, payload, or trace value | SECURITY-03; NFR-AE-20 |
| BR-RF-ET-02 | Every `401` carries `WWW-Authenticate: Bearer`; every `503` carries `Retry-After`; every response carries `Soorma-Contract-Version` and `Soorma-Request-Id` | U1 `errors.md` |
| BR-RF-ET-03 | A refused publish delivers nothing; a refused subscribe opens no stream | O8, O9 |

## 12. Problem Emission and the Stream's End (BR-PE)

| ID | Rule | Source |
|---|---|---|
| BR-PE-ET-01 | Every refusal before a stream opens is a Problem through P1's `problemResponse` | D-ET-24; BR-PE-06 (U3) |
| BR-PE-ET-02 | S4's tests run the shared Problem assertion on every Problem S4 emits, every code above included | BR-PE-06 |
| BR-PE-ET-03 | After a stream's `200`, nothing is a Problem: the `end` event's `{ code }` is the only signal. Its codes reuse the request codes where they mean the same (`credential_expired`, `credential_refused`, `unavailable`), so a client handles both alike | D-ET-03 |

## 13. Two Faces, Packaging, and the Dependency Closure

| ID | Rule | Source |
|---|---|---|
| BR-PK-01 | S4 is **data-face only**: two agent operations in their own contract document, its own NFR profile (PF §9), its own throttle values; no control-face operation and no human credential accepted | I6; M1-NFR-03 |
| BR-PK-02 | **No organization-level dependency**: no S1 address, key, or call. S4's production dependency closure excludes `@soorma/org-identity` (a closure test, as S2's and S3's), and S4 serves with S1 stopped (TC-ET-022) | D-ET-23; M1-NFR-08 |
| BR-PK-03 | Every capability U7 builds is core-assigned (invariant-coverage-matrix, I8). No topic administration, durability, redelivery, or anything commercial, in any form | I8; A-2 |

## 14. Contract Changes

Made at U7's Code Generation, under contract `0.1.0` (unreleased until the tag), and recorded in
`contract/CHANGELOG.md`. All are compatible: a new surface document, clarifications, and an
open code widened.

| Change | Where | Classification |
|---|---|---|
| **New surface**: `publish` (`POST /events`, `202`) and `subscribe` (`POST /subscriptions`, `200` `text/event-stream`), `agentCredential`; the bodies (BR-BF-01); the stream's named events `delivery` (data: `delivery.schema.json`'s `Delivery`, by name) and `end` (data: `{ code }`, open) | `contract/event-ingest.openapi.yaml` (new) | Compatible: the contract is completed |
| **The draft's place on S4**: in the `draft` member of the body; step 5 and step 6 for the body form (BR-BF-03, 04) | `conventions/errors.md` (*Check order*, steps 5 and 6); `conventions/envelope.md` (*Envelope-bearing operations*: where the draft sits) | Compatible: a clarification |
| **`payload_too_large` widened**: "or a publish's `payload` exceeds the Delivery payload bound" | `conventions/errors.md` | Compatible: an open code's scope widened, its meaning kept |
| **The Delivery payload bound P** published (D-ET-27), measured on the JCS serialization | `conventions/envelope.md` (*The Delivery*); `pre-release.md` (the "not set in this version" line replaced) | Compatible: a value the conventions left to U7 |
| **The stream**: one `end` event, its open codes, heartbeats, no resumption (`Last-Event-ID` ignored), at most one stream per lineage (a later subscribe supersedes) | `conventions/envelope.md` (*The Delivery*) or a new section; `pre-release.md` statement 2 (no resumption) | Compatible: states behaviour of a new surface |
| The tag `contract-v0.1.0` on `main` | after U7's code PR merges (D-ET-33) | — |

## 15. Amendments and Corrections

| To | Change | Classification |
|---|---|---|
| **U3** `packages/authority` (`admit`) | **The Body Form option** (D-ET-01): additive; without it, behaviour is unchanged. **No U3 test or helper changes**; new tests for the option. Noted in U3 business-rules §2 (*Amendment from U7*) | Code change to an earlier unit's package, no test change |
| **U4/U6** `packages/attribution` and `env-store` | The envelope-bearing list and the reverse rule (D-ET-07, BR-AT-ET-06); a new migration; `0001` to `0004` untouched | Code change; the earlier units' attribution tests unchanged |
| **U5** `services/control-gateway/test/registration.test.ts` | **Class 3, approved by the user (2026-11-12, Q7 A), exactly**: in "an agent's record resolves its sponsor through the registration, in two hops", `operation: 'constructedAgentOperation'` becomes `operation: 'exchangeBootstrap'`. Nothing else in the file changes. **Condition**: if P7's writer requires anything more of an `exchangeBootstrap` record (a target or a credential), Code Generation stops. Checked at this stage: it does not (D-ET-07) | Class 3, approved |
| **U6** `e2e/agent-registration.test.ts`, TC-AC-093 | One line inside its loop keeps each instance's agent credential for U7's tests: captures a value, no assertion changes | Class 1 |
| **U5** the backup round trip (TC-AR-059, 056, 060) | `e-event-ingest` added to its stop, remove, and up lists, as U6 added `e-data-gateway` | Class 1 |
| **U4** Compose-model, privilege, and monitoring tests | S4's items added to their lists only; if the monitoring overlap assertion cannot take S4's shared names by adding items only, Code Generation stops | Class 1 (CI steps: class 2) |
| **Application Design** `component-methods.md` S4 | Correction note: the paths, the bodies, the stream's end, one stream per lineage | Note |

## 16. Misuse Cases (SECURITY-11)

| Misuse | Control | Residual |
|---|---|---|
| A human credential, a delegation credential, or a credential from E2 presented to E's ingest | Refused by kind (BR-PR-ET-01), or at O4 | None |
| A draft setting a stamped field, asserting origin, or forging a chain or re-broadening record | `stamped_field_set` (U3); a chain only from a sealed, verified envelope | None |
| A forged or foreign forwarded envelope | The seal with E's ring; scope E (U3) | A genuine sealed envelope can be replayed by anyone who saw it: the seal proves neither delivery nor recency (U1's accepted residual, carried) |
| Stream hoarding by one credential | One stream per lineage (D-ET-05); the per-instance cap | A holder of several lineages (several bootstraps) holds several streams, up to the cap. Per-agent stream limits: the first hosted deployment |
| Publish flood into E | The per-instance throttle; body and payload bounds | Every subscriber in E receives what one agent publishes, up to the throttle. Per-agent publish limits: the first hosted deployment |
| A slow or stalled reader holding memory | The bounded send buffer; `overflow` (D-ET-06); the grace close | None beyond the buffer |
| A revoked agent keeping its stream | Checks before each delivery and every R through the cache (D-ET-04) | The connection closes up to R after deliveries stop |
| Oversized or deeply nested bodies | The step-1 limits; the depth test at S4's limit (D-ET-26) | None |
| Probing which agents exist or are revoked | A revoked credential is plain `credential_refused`; the stream's end says `credential_refused`, never the granularity | None |

## 17. Accepted Residuals

- **GAP-ET-001 work-around (D-ET-09)**: in M1, **E's store is S4's availability floor** for new
  publishes and subscribes. During a store outage, the caches still answer for up to B, open
  streams stay open and keep checking, and a malformed or foreign credential is still refused
  exactly (BR-CK-05), but **no new publish or subscribe proceeds**. Carried to Build and Test;
  the PRD chooses at soorma-prd#31
- **Superseding across instances (D-ET-05)**: if the M1 stack runs one S4 per environment, the
  cross-instance path (BR-FO-05) is not exercised on the stack; it is tested in process only if
  the channel's design allows two instances on one channel. A lost `supersede` leaves two
  streams of one lineage for at most L
- **The connection's close after revocation lags deliveries by up to R** (BR-SR-04)
- **A stream's authority is fixed at open** (D-ET-21): sound in M1 (NFR-AE-16), and bounded by L
- **Live only (GAP-INT-003)**: a subscriber offline, superseded, overflowed, or on an instance
  that misses a channel message loses those events
- **Every subscriber in E receives everything published in E** (no topics, A-2)

## 18. Forward Obligations

| To | Obligation |
|---|---|
| **Build and Test** | GAP-ET-001's residual (§17), reported as an `Open` gap; the cross-instance supersede residual if it stands; TC-ET-016 and 017 and U6's TC-AC-009, 010, 015 timelines at S4; S4's p95 on the running stack (NFR Requirements' budget, reported); the contract tag after the merge |
| **soorma-sdk** (the brief's consumer; the brief is not edited) | The bodies `{ draft, payload }` and `{ draft }`; publish `202` with no body; the stream's `delivery` and `end` events and the open end codes; renew, then subscribe again before `exp` (the new stream supersedes the old); no resumption; live only |
| **The first hosted deployment** | Per-agent publish and stream limits; a multi-instance channel that exercises cross-instance superseding |
| **The unit that first changes a standing set, a declaration, or autonomy, or suspends or retires an agent** (NFR-AE-16, extended) | Account for open streams as well as U3's term cache: a stream's authority is fixed at open |
| **GAP-ET-001's answer** | If the PRD chooses decoupled attribution, S4's record path (D-ET-09) changes; the contract's codes do not |

## 19. Specification Gaps

| ID | Status | Rule affected | Issue |
|---|---|---|---|
| **GAP-ET-001** | **Open**; worked around (a synchronous record, fail closed) | D-ET-09; BR-PB-03; BR-SB-03; BR-AT-ET-08 | [soorma-prd#31](https://github.com/soorma-ai/soorma-prd/issues/31) |
| GAP-INT-003 (inherited) | Awaiting PRD: Event; worked around (live only) | D-ET-20; BR-FO-03; BR-PB-05, 06 | [soorma-prd#13](https://github.com/soorma-ai/soorma-prd/issues/13) |
| GAP-INT-007 (inherited) | Open; worked around (reject and stamp), in U3 | step 6 (U3 BR-DV-04) | [soorma-prd#25](https://github.com/soorma-ai/soorma-prd/issues/25) |
| GAP-AE-001 (inherited) | Open; worked around (deny), in U3 | step 9 (U3 BR-OR-04) | [soorma-prd#30](https://github.com/soorma-ai/soorma-prd/issues/30) |

Full entry: [../prd-gaps/specification-gaps.md](../prd-gaps/specification-gaps.md).
