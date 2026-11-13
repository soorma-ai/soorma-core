# Test Specifications (Narrative): event-transport

**Unit**: `event-transport` (U7: event publish, subscribe and live delivery within an environment, data face)  
**Unit abbreviation**: ET = event-transport  
**Scope**: comprehensive (happy path, negative, edge and boundary), as recorded in `aidlc-state.md`  
**Derived from**: `aidlc-docs/platform/m1-walking-skeleton/inception/application-design/unit-of-work.md` and `aidlc-docs/platform/m1-walking-skeleton/inception/requirements/requirements.md` only  
**Generated**: inception pass, 2026-11-02. IDs are permanent. **Construction pass, 2026-11-13**: TC-ET-001 to 024 enriched in place; TC-ET-025 to 092 added (sources: functional-design/, nfr-requirements/, nfr-design/, infrastructure-design/)

## Common Fixtures

Every test case below runs against the **local stack** (M1-NFR-05) unless it says
otherwise. The fixture names are used throughout this file:

| Name | Meaning |
|---|---|
| **O** | The organization configured in the deployment's configuration |
| **E**, **E2** | Two environments of O, each its own deployment with its own store and minting material (`unit-of-work.md`, Code Organization) |
| **H** | The human principal named as E's first Admin in configuration |
| **K**, **P** | H's memorized secret, and possession-based authenticator, respectively |
| **sign-in** | An organization sign-in issued to H by the organization level |
| **env credential (E)** | A human environment credential issued by E |
| **A**, **B** | Two logical agents registered in E by H, each with autonomy declared unless a case says otherwise |
| **agent credential (E)** | A short-lived credential issued by E's bootstrap exchange to an instance of A or B |
| **the bound** | The published revocation propagation bound (M1-FR-07). Its value is set at NFR Requirements |
| **raw call** | An HTTP request made without the SDK, conforming to the wire contract |
| **test-only revocation seeding** | The path, not compiled into the product, that writes agent revocation state (M1-FR-07) |

Values not yet fixed (bounds, lifetimes, `maxChainDepth`) are referred to by name. Their
numbers come from the unit's NFR Requirements and Functional Design, and the construction
pass of this extension records them.

---

### TC-ET-001 — A publishes, and B, subscribed, receives a Delivery

**Context**: *Done when* 3: A publishes, and B, subscribed in the same environment, receives it, by raw calls (M1-FR-11).

**Scenario**: B subscribes, then A publishes.

**Preconditions**:
- E's event-ingest is running. A (`event:publish`) and B (`event:subscribe`) are registered in E with autonomy declared, and each instance holds a live agent credential for E

**Steps**:
1. B opens a subscribe stream with a draft envelope
2. A publishes a payload with a draft envelope
3. Read B's stream

**Expected outcome**: B's stream yields one `Delivery`, carrying A's payload unchanged. *(Construction pass)* By raw calls in `e2e/agent-registration.test.ts`, after TC-AC-093, reusing A, B and their agent credentials (D-ET-34): B `POST /subscriptions` `{ draft }` at `127.0.0.1:8446`, `200` `text/event-stream`; A `POST /events` `{ draft, payload }`, `202` with no body; B's stream yields one `delivery` event whose data is `{ envelope, seal, payload }`, the payload equal to A's.

**Scope**: happy-path · **Priority**: High  
**Source**: event-transport / M1-FR-11  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/event-transport/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; construction pass: `construction/event-transport/functional-design/business-rules.md` (D-ET-01, 02, 34)

---

### TC-ET-002 — The delivered envelope carries scope, origin and a stamped chain

**Context**: *Done when* 4: the envelope B receives carries scope, origin, and an actor chain appended by the perimeter, not by A (M1-FR-01).

**Scenario**: B inspects the delivered envelope.

**Preconditions**:
- E's event-ingest is running. A (`event:publish`) and B (`event:subscribe`) are registered in E with autonomy declared, and each instance holds a live agent credential for E
- One Delivery received by B, from A

**Steps**:
1. Read the envelope in the Delivery

**Expected outcome**: Scope E, origin `autonomous`, and actor chain `[A's instance]`. A's draft carried none of these. *(Construction pass)* `envelope.scope` `{ organization: o1, project: p1, environment: e }`, `originMode` `autonomous`, `actorChain` `[{ agent: A, instance: a-1 }]`, no `reBroadening`, no `delegatingPrincipal`; `seal` non-empty. A's draft carried only `clientContractVersion` and `traceContext`.

**Scope**: happy-path · **Priority**: High  
**Source**: event-transport / M1-FR-01, M1-FR-08  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/event-transport/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; construction pass: `construction/event-transport/functional-design/business-rules.md` (D-ET-19; BR-SM-02)

---

### TC-ET-003 — Trace context is carried as asserted

**Context**: Trace context is agent-asserted and carried, validated for well-formedness only (M1-FR-01). soorma-core emits no spans.

**Scenario**: A publishes with a known `traceparent`.

**Preconditions**:
- E's event-ingest is running. A (`event:publish`) and B (`event:subscribe`) are registered in E with autonomy declared, and each instance holds a live agent credential for E

**Steps**:
1. A publishes with `traceparent` T
2. B reads the Delivery

**Expected outcome**: The delivered envelope's trace context is T. *(Construction pass)* The delivered `traceContext.traceparent` equals T, and `tracestate` is present exactly when A sent one.

**Scope**: happy-path · **Priority**: Medium  
**Source**: event-transport / M1-FR-01  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/event-transport/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; construction pass: `construction/event-transport/functional-design/business-rules.md` (D-ET-35)

---

### TC-ET-004 — A publish is attributed

**Context**: Publishing is a platform-resource operation, and is attributed (M1-FR-12, in U7).

**Scenario**: A reviewer inspects attribution after a publish.

**Preconditions**:
- E's event-ingest is running. A (`event:publish`) and B (`event:subscribe`) are registered in E with autonomy declared, and each instance holds a live agent credential for E
- A has published once

**Steps**:
1. Read the attribution record for the publish

**Expected outcome**: The record carries scope E, A's instance as actor, chain `[A]`, and origin `autonomous`. *(Construction pass)* The `publish` row: `actor_kind` agent, `registration` A, `instance` a-1, `sponsor` H, `credential_kind` `agentCredential` with A's `cid`, `chain` `[A]`, `origin` `{ originMode: autonomous }`, `rebroadening_load_bearing` false, `rebroadening_hop` null, written before the Delivery (D-ET-16).

**Scope**: happy-path · **Priority**: Medium  
**Source**: event-transport / M1-FR-12  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/event-transport/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; construction pass: `construction/event-transport/functional-design/business-rules.md` (D-ET-16, 18; BR-AT-ET-01 to 04)

---

### TC-ET-005 — A triggered subscribe re-broadens at B's hop

**Context**: The M1 scenario where re-broadening is load-bearing: B, triggered by A's event, calls `event:subscribe` while forwarding A's context. A lacks `event:subscribe`, and B declared it (M1-FR-08).

**Scenario**: B, declaring `event:subscribe`, subscribes forwarding the envelope it received from A.

**Preconditions**:
- E's event-ingest is running. A (`event:publish`) and B (`event:subscribe`) are registered in E with autonomy declared, and each instance holds a live agent credential for E
- B's declaration includes `event:subscribe`
- A's standing set excludes `event:subscribe`
- B has received a Delivery from A

**Steps**:
1. B opens a subscribe stream whose draft forwards A's envelope

**Expected outcome**: Allowed. The resulting envelope has chain `[A, B]`, origin `autonomous` unchanged, and a re-broadening record naming B's hop. *(Construction pass)* In U7's own e2e file (B registered with the declaration). The subscribe's record: chain `[A, B]`, origin `autonomous`, `rebroadening_load_bearing` true, **`rebroadening_hop` 1** (the chain's last index). B is not given that envelope (D-ET-02).

**Scope**: happy-path · **Priority**: High  
**Source**: event-transport / M1-FR-08  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/event-transport/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; construction pass: `construction/event-transport/functional-design/business-rules.md` (BR-AT-ET-03; D-ET-02)

---

### TC-ET-006 — A publish with a credential from another environment is denied

**Context**: *Done when* 6: the same publish, attempted with a credential from another environment, is denied (O4; M1-FR-09).

**Scenario**: An instance holding an agent credential from E2 publishes to E.

**Preconditions**:
- E's event-ingest is running. A (`event:publish`) and B (`event:subscribe`) are registered in E with autonomy declared, and each instance holds a live agent credential for E
- E2 running, with an agent registered there holding `event:publish` and a live credential from E2

**Steps**:
1. Publish to E's ingest, presenting the E2 credential

**Expected outcome**: Denied. B receives nothing. *(Construction pass)* **D-ET-08**: chained in the journey: H obtains an E2 environment credential, self-grants `agent:register` in E2, registers A there, issues a secret, and an instance bootstraps at E2's S3; A's publish to E with that credential is `401` `credential_refused` (O4) and B's stream receives nothing. The same test presents A's E credential to E2's S4 (`8447`): `401` `credential_refused`.

**Scope**: negative · **Priority**: High  
**Source**: event-transport / M1-FR-09, M1-FR-10  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/event-transport/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; construction pass: `construction/event-transport/functional-design/business-rules.md` (D-ET-08; BR-CK-02)

---

### TC-ET-007 — A draft setting a platform-stamped field is rejected at ingest

**Context**: *Done when* 7: a draft in which the agent sets a platform-stamped field is rejected (M1-FR-01). Ingest checks it itself (O10).

**Scenario**: A publishes six drafts, each setting one platform-stamped field.

**Preconditions**:
- E's event-ingest is running. A (`event:publish`) and B (`event:subscribe`) are registered in E with autonomy declared, and each instance holds a live agent credential for E

**Steps**:
1. For each of envelope version, scope, origin mode, delegating principal, actor chain, and re-broadening record, publish a draft that sets it

**Expected outcome**: All six are rejected, and B receives nothing. *(Construction pass)* Each is `400` `stamped_field_set` with `errors[0].pointer` `/draft/<field>`; B's stream receives nothing.

**Scope**: negative · **Priority**: High  
**Source**: event-transport / M1-FR-01, M1-FR-09  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/event-transport/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; construction pass: `construction/event-transport/functional-design/business-rules.md` (BR-BF-04)

---

### TC-ET-008 — A draft asserting `autonomous` is rejected at ingest

**Context**: Origin is stamped on every first hop, and an asserted origin is rejected (the GAP-INT-007 work-around, in U7's inherited gaps).

**Scenario**: A, autonomy declared, publishes a draft asserting `autonomous`.

**Preconditions**:
- E's event-ingest is running. A (`event:publish`) and B (`event:subscribe`) are registered in E with autonomy declared, and each instance holds a live agent credential for E

**Steps**:
1. Publish a draft containing origin mode `autonomous`

**Expected outcome**: Rejected. *(Construction pass)* `400` `stamped_field_set`, pointer `/draft/originMode` (GAP-INT-007 work-around, in U3).

**Scope**: negative · **Priority**: High  
**Source**: event-transport / M1-FR-01 (GAP-INT-007)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/event-transport/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; construction pass: `construction/event-transport/functional-design/business-rules.md` (BR-BF-04; §19)

---

### TC-ET-009 — An agent without declared autonomy is denied at publish and subscribe

**Context**: With no inbound context, an agent that did not declare autonomy is denied (O12; M1-FR-08).

**Scenario**: Agent C, registered without declared autonomy and holding both event permissions, publishes and subscribes with no forwarded context.

**Preconditions**:
- E's event-ingest is running. A (`event:publish`) and B (`event:subscribe`) are registered in E with autonomy declared, and each instance holds a live agent credential for E
- C registered with autonomy not declared, holding `event:publish` and `event:subscribe`, with a live credential

**Steps**:
1. C publishes with no forwarded context
2. C subscribes with no forwarded context

**Expected outcome**: Both are denied. *(Construction pass)* Both `403` `forbidden` (O12); the subscribe opens no stream and writes no record. In U7's own e2e file, C seeded as the store's owner.

**Scope**: negative · **Priority**: High  
**Source**: event-transport / M1-FR-08  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/event-transport/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; construction pass: `construction/event-transport/functional-design/business-rules.md` (BR-RF-ET (step 9))

---

### TC-ET-010 — A publish without `event:publish` is denied

**Context**: `event:publish` applies in the environment's namespace (M1-FR-11).

**Scenario**: B, without `event:publish`, publishes.

**Preconditions**:
- E's event-ingest is running. A (`event:publish`) and B (`event:subscribe`) are registered in E with autonomy declared, and each instance holds a live agent credential for E

**Steps**:
1. B publishes with no forwarded context

**Expected outcome**: Denied. *(Construction pass)* `403` `forbidden`; no record.

**Scope**: negative · **Priority**: High  
**Source**: event-transport / M1-FR-11  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/event-transport/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; construction pass: `construction/event-transport/functional-design/business-rules.md` (BR-PB-01)

---

### TC-ET-011 — A subscribe without `event:subscribe` is denied

**Context**: `event:subscribe` applies in the environment's namespace (M1-FR-11).

**Scenario**: A, without `event:subscribe`, subscribes.

**Preconditions**:
- E's event-ingest is running. A (`event:publish`) and B (`event:subscribe`) are registered in E with autonomy declared, and each instance holds a live agent credential for E

**Steps**:
1. A opens a subscribe stream with no forwarded context

**Expected outcome**: Denied. No stream opens. *(Construction pass)* `403` `forbidden`, a Problem; no stream opens; no record.

**Scope**: negative · **Priority**: High  
**Source**: event-transport / M1-FR-11  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/event-transport/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; construction pass: `construction/event-transport/functional-design/business-rules.md` (BR-SB-01)

---

### TC-ET-012 — Every human credential is refused at ingest

**Context**: Event ingest refuses every human credential (M1-FR-09), and refuses it by kind.

**Scenario**: H presents an environment credential, then a sign-in, to ingest.

**Preconditions**:
- E's event-ingest is running. A (`event:publish`) and B (`event:subscribe`) are registered in E with autonomy declared, and each instance holds a live agent credential for E
- H holds a sign-in and a credential for E

**Steps**:
1. Publish, presenting H's environment credential
2. Publish, presenting H's sign-in

**Expected outcome**: Both are refused. *(Construction pass)* Both `401` `credential_refused` with `WWW-Authenticate: Bearer`, by kind, never verified; `ingest.refused` logged with the presenter reason.

**Scope**: negative · **Priority**: High  
**Source**: event-transport / M1-FR-09, M1-FR-11  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/event-transport/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; construction pass: `construction/event-transport/functional-design/business-rules.md` (BR-PR-ET-01, 02)

---

### TC-ET-013 — A delegation credential is refused

**Context**: In M1 no delegation credential can be live, so a delegation credential, alone or beside an agent's, is refused by its own checks (M1-FR-09).

**Scenario**: A request presents a credential shaped as a delegation credential beside A's credential.

**Preconditions**:
- E's event-ingest is running. A (`event:publish`) and B (`event:subscribe`) are registered in E with autonomy declared, and each instance holds a live agent credential for E

**Steps**:
1. Publish, presenting A's credential and a delegation-credential-shaped token

**Expected outcome**: Refused. *(Construction pass)* `401` `credential_refused` at step 2 (a credential beside `Soorma-Delegation`).

**Scope**: negative · **Priority**: High  
**Source**: event-transport / M1-FR-09  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/event-transport/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; construction pass: `construction/event-transport/functional-design/business-rules.md` (BR-PR-ET-01)

---

### TC-ET-014 — A revoked credential cannot publish

**Context**: Revocation state is read on every request at ingest (M1-FR-07).

**Scenario**: A's credential is revoked through the test-only path, then A publishes.

**Preconditions**:
- E's event-ingest is running. A (`event:publish`) and B (`event:subscribe`) are registered in E with autonomy declared, and each instance holds a live agent credential for E
- Test-only revocation seeding is available

**Steps**:
1. Seed revocation for A's credential
2. Wait for the bound to elapse
3. A publishes

**Expected outcome**: Denied. *(Construction pass)* Through P5's cache: the publish may pass while the cached `not_revoked` is younger than B (60 s); after it, `401` `credential_refused`. The timeline is TC-ET-028.

**Scope**: negative · **Priority**: High  
**Source**: event-transport / M1-FR-07  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/event-transport/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; construction pass: `construction/event-transport/functional-design/business-rules.md` (D-ET-12; BR-CK-02, 03)

---

### TC-ET-015 — Nothing crosses environments

**Context**: Events never cross the environment boundary (M1-FR-10).

**Scenario**: An agent subscribed in E2 waits while A publishes in E.

**Preconditions**:
- E's event-ingest is running. A (`event:publish`) and B (`event:subscribe`) are registered in E with autonomy declared, and each instance holds a live agent credential for E
- An agent in E2 holding `event:subscribe`, subscribed there

**Steps**:
1. A publishes in E
2. Read the E2 subscriber's stream for a period

**Expected outcome**: The E2 subscriber receives nothing. *(Construction pass)* The E2 subscriber at `127.0.0.1:8447` receives no `delivery` within 5 s; E's and E2's channels are separate processes (BR-FO-01).

**Scope**: negative · **Priority**: High  
**Source**: event-transport / M1-FR-10, M1-FR-11  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/event-transport/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; construction pass: `construction/event-transport/functional-design/business-rules.md` (BR-FO-01)

---

### TC-ET-016 — A stream ends within the bound after the subscriber's credential expires

**Context**: Delivery stops within the propagation bound once the subscriber's credential expires (M1-FR-11).

**Scenario**: B's credential expires while the stream is open.

**Preconditions**:
- E's event-ingest is running. A (`event:publish`) and B (`event:subscribe`) are registered in E with autonomy declared, and each instance holds a live agent credential for E
- B subscribed with a credential near expiry

**Steps**:
1. Let B's credential expire without renewal
2. A publishes after the expiry plus the bound
3. Observe B's stream

**Expected outcome**: B's stream has ended by expiry plus the bound, and the later event is not delivered to B. *(Construction pass)* In process with an injected clock (L is 15 minutes): the stream ends at the credential's `exp` exactly with `end` `{ code: "credential_expired" }`; a publish after `exp` is not delivered to it.

**Scope**: edge-boundary · **Priority**: High  
**Source**: event-transport / M1-FR-11  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/event-transport/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; construction pass: `construction/event-transport/functional-design/business-rules.md` (D-ET-22; BR-SR-01)

---

### TC-ET-017 — A stream ends within the bound after revocation

**Context**: Delivery stops within the bound once the subscriber's credential is revoked (M1-FR-11).

**Scenario**: B's credential is revoked while the stream is open.

**Preconditions**:
- E's event-ingest is running. A (`event:publish`) and B (`event:subscribe`) are registered in E with autonomy declared, and each instance holds a live agent credential for E
- B subscribed
- Test-only revocation seeding is available

**Steps**:
1. Seed revocation for B's credential
2. A publishes after the bound has elapsed
3. Observe B's stream

**Expected outcome**: B's stream has ended within the bound of the revocation, and the later event is not delivered. *(Construction pass)* In process with an injected clock: no Delivery is written to B's stream after revocation + B (60 s); the stream ends with `end` `{ code: "credential_refused" }` within R (1 s) after that; `stream.revoked` logged. On the stack, seeded revocation; the end observed within 61 s plus a request.

**Scope**: edge-boundary · **Priority**: High  
**Source**: event-transport / M1-FR-11, M1-FR-07  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/event-transport/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; construction pass: `construction/event-transport/functional-design/business-rules.md` (D-ET-04; BR-SR-02 to 04; NFR-ET-07)

---

### TC-ET-018 — A subscriber offline at publish time never receives the event

**Context**: Delivery reaches live subscribers only: no durability or redelivery (M1-FR-11, the GAP-INT-003 work-around).

**Scenario**: A publishes while B is not subscribed; B subscribes afterwards.

**Preconditions**:
- E's event-ingest is running. A (`event:publish`) and B (`event:subscribe`) are registered in E with autonomy declared, and each instance holds a live agent credential for E

**Steps**:
1. A publishes with no subscriber connected
2. B subscribes
3. Read B's stream for a period

**Expected outcome**: B does not receive the earlier event. *(Construction pass)* Live only: B never receives the earlier event; a `Last-Event-ID` header on B's subscribe changes nothing (D-ET-20).

**Scope**: edge-boundary · **Priority**: Medium  
**Source**: event-transport / M1-FR-11 (GAP-INT-003)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/event-transport/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; construction pass: `construction/event-transport/functional-design/business-rules.md` (D-ET-20; BR-SM-01, 02)

---

### TC-ET-019 — A forwarded chain at maxChainDepth cannot grow

**Context**: `maxChainDepth` is enforced at every hop (M1-FR-01).

**Scenario**: An agent publishes forwarding an envelope whose chain is already at `maxChainDepth`.

**Preconditions**:
- E's event-ingest is running. A (`event:publish`) and B (`event:subscribe`) are registered in E with autonomy declared, and each instance holds a live agent credential for E
- An inbound envelope with a chain of length `maxChainDepth`

**Steps**:
1. Publish a draft forwarding that envelope

**Expected outcome**: Rejected. *(Construction pass)* In process, with a 32-entry chain sealed by E's ring through U3's test helpers: `400` `chain_too_deep`; nothing delivered.

**Scope**: edge-boundary · **Priority**: Medium  
**Source**: event-transport / M1-FR-01  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/event-transport/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; construction pass: `construction/event-transport/functional-design/business-rules.md` (BR-RF-ET (step 8))

---

### TC-ET-020 — A forwarded origin propagates unchanged

**Context**: An event-triggered hop propagates origin unchanged (M1-FR-08).

**Scenario**: B, triggered by A's event, publishes forwarding it.

**Preconditions**:
- E's event-ingest is running. A (`event:publish`) and B (`event:subscribe`) are registered in E with autonomy declared, and each instance holds a live agent credential for E
- B also holds `event:publish`

**Steps**:
1. B publishes, forwarding A's envelope
2. A subscriber reads the Delivery

**Expected outcome**: Origin is `autonomous`, as stamped for A, and the chain is `[A, B]`. *(Construction pass)* In U7's own e2e file, B holding `event:publish` too: the delivered envelope has chain `[A, B]` and origin `autonomous`.

**Scope**: edge-boundary · **Priority**: Medium  
**Source**: event-transport / M1-FR-08  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/event-transport/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; construction pass: `construction/event-transport/functional-design/business-rules.md` (D-ET-13)

---

### TC-ET-021 — Ingest checks independently of the gateways

**Context**: Neither entry point treats the other's traffic as pre-validated (O10; M1-FR-09).

**Scenario**: A request that would pass a gateway check reaches ingest with an invalid credential.

**Preconditions**:
- E's event-ingest is running. A (`event:publish`) and B (`event:subscribe`) are registered in E with autonomy declared, and each instance holds a live agent credential for E

**Steps**:
1. Publish to ingest with a malformed agent credential, adding any header that claims prior validation

**Expected outcome**: Refused. Ingest performs its own checks regardless. *(Construction pass)* A malformed `soorma_ac_` token with a header such as `X-Soorma-Validated: true`: `401` `credential_refused`; the header is ignored (BR-CK-06).

**Scope**: edge-boundary · **Priority**: High  
**Source**: event-transport / M1-FR-09  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/event-transport/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; construction pass: `construction/event-transport/functional-design/business-rules.md` (BR-CK-06)

---

### TC-ET-022 — Publish, subscribe and delivery work while the organization level is down

**Context**: Event ingest has no organization-level dependency, so agent data-plane traffic is unaffected by its outage (U7 in unit-of-work.md; M1-NFR-08).

**Scenario**: The organization level is stopped while A and B exchange an event.

**Preconditions**:
- E's event-ingest is running. A (`event:publish`) and B (`event:subscribe`) are registered in E with autonomy declared, and each instance holds a live agent credential for E
- The organization level is stopped

**Steps**:
1. B subscribes
2. A publishes

**Expected outcome**: B receives the Delivery. *(Construction pass)* `pnpm stack:outage` **Case 4** (D-ID-ET-11): with `org-gateway` stopped, B subscribes, A publishes, B receives; then `e-event-ingest` restarted with S1 still stopped becomes healthy and the round trip works again. Agents from the store-owner seeding helpers.

**Scope**: edge-boundary · **Priority**: High  
**Source**: event-transport / M1-FR-11 (M1-NFR-08)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/event-transport/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; construction pass: `construction/event-transport/functional-design/business-rules.md` (D-ID-ET-11; NFR-ET-14)

---

### TC-ET-023 — Unknown fields survive to delivery

**Context**: Unknown fields are preserved and forwarded (M1-FR-01).

**Scenario**: A forwards an inbound envelope that carries an unknown field.

**Preconditions**:
- E's event-ingest is running. A (`event:publish`) and B (`event:subscribe`) are registered in E with autonomy declared, and each instance holds a live agent credential for E
- An inbound envelope with `x-future`

**Steps**:
1. A publishes, forwarding it
2. B reads the Delivery

**Expected outcome**: `x-future` is present in the delivered envelope. *(Construction pass)* `x-future` (and any unknown field at any level of the forwarded envelope) is present in the Delivery's envelope, carried by U3's stamp.

**Scope**: edge-boundary · **Priority**: Medium  
**Source**: event-transport / M1-FR-01  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/event-transport/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; construction pass: `construction/event-transport/functional-design/business-rules.md` (D-ET-19)

---

### TC-ET-024 — This unit's operations are defined in the contract and validated against it

**Context**: Each surface unit adds its own operations to the wire contract (unit-of-work.md, Q1 B). A raw caller that never links the SDK reaches identical enforcement (M1-FR-02).

**Scenario**: A reviewer checks the unit's operations in `contract/event-ingest.openapi.yaml`, then sends a request that violates the schema.

**Preconditions**:
- `contract/event-ingest.openapi.yaml` after this unit's Code Generation

**Steps**:
1. List the operations in `contract/event-ingest.openapi.yaml` and compare them with this unit's operations: `publish`, `subscribe` (whose SSE events reference the named `Delivery` schema)
2. Check that each references the shared conventions (versioning, error model, security schemes)
3. Send one request with a body that violates its operation's schema

**Expected outcome**: Every one of the unit's operations is present and references the conventions. The violating request is rejected with the contract's error model before any processing. *(Construction pass)* `contract/event-ingest.openapi.yaml` (new) holds `publish` (`POST /events`, `202`) and `subscribe` (`POST /subscriptions`, `200` `text/event-stream`, events `delivery` with data `Delivery` by name and `end` with `{ code }`), each `agentCredential`. A violating body is refused at step 5 or 6 with the contract's Problem (TC-ET-025, 077).

**Scope**: happy-path · **Priority**: High  
**Source**: event-transport / M1-FR-02  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/event-transport/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; construction pass: `construction/event-transport/functional-design/business-rules.md` (D-ET-10, 33; §14)

---


### TC-ET-025 — The draft's contract version is checked at both operations

**Context**: A draft declares its client contract version (PF §7b); with the Body Form it is read at `/draft/clientContractVersion` (BR-BF-03; L1-06).

**Scenario**: A publish and a subscribe each send a missing version, an unsupported version, and a `Soorma-Contract-Version` header that differs from the draft's.

**Preconditions**:
- E's event-ingest is running. A (`event:publish`) and B (`event:subscribe`) are registered in E with autonomy declared, and each instance holds a live agent credential for E

**Steps**:
1. For each operation, send a body whose draft has no `clientContractVersion`
2. Send one whose draft declares `9.9.9`
3. Send one declaring `0.1.0` with the header `Soorma-Contract-Version: 0.2.0`
4. Send one whose body is not an object, and one whose `draft` is not an object

**Expected outcome**: The first two are `400` `unsupported_contract_version` with `supportedVersions`; the third `400` `malformed_request` naming the header; the fourth `malformed_request` with pointer `""`, the fifth with pointer `/draft`. Nothing is delivered and no stream opens.

**Scope**: negative · **Priority**: High  
**Source**: event-transport / M1-FR-01, M1-FR-02  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/event-transport/code/`  
**Technical references**: `construction/event-transport/functional-design/business-rules.md` (BR-BF-03); `construction/event-transport/functional-design/l1-coverage-matrix.md` (L1-06)

---

### TC-ET-026 — A forward that is not load-bearing records no hop

**Context**: Re-broadening is recorded only when load-bearing (PF §8b; L1-11).

**Scenario**: B, whose own standing set already holds `event:subscribe`, subscribes forwarding A's envelope.

**Preconditions**:
- E's event-ingest is running. A (`event:publish`) and B (`event:subscribe`) are registered in E with autonomy declared, and each instance holds a live agent credential for E
- B has received a Delivery from A

**Steps**:
1. B subscribes with a draft whose `inbound` is A's envelope and seal
2. Read the subscribe's attribution record

**Expected outcome**: Allowed. The record has chain `[A, B]`, origin `autonomous`, `rebroadening_load_bearing` false, and `rebroadening_hop` null.

**Scope**: edge-boundary · **Priority**: Medium  
**Source**: event-transport / M1-FR-08, M1-FR-12  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/event-transport/code/`  
**Technical references**: `construction/event-transport/functional-design/business-rules.md` (BR-AT-ET-03)

---

### TC-ET-027 — A forwarded envelope is never a credential

**Context**: The envelope is never usable to act; acting needs the presenter's own credential (PF §17; L1-15).

**Scenario**: A request carries A's sealed envelope as `inbound` and no credential.

**Preconditions**:
- E's event-ingest is running. A (`event:publish`) and B (`event:subscribe`) are registered in E with autonomy declared, and each instance holds a live agent credential for E
- A Delivery from A is held

**Steps**:
1. Publish with no `Authorization` header and a draft forwarding A's envelope and seal

**Expected outcome**: `401` `credential_refused` with `WWW-Authenticate: Bearer`, decided at step 2 before the body is read. Nothing is delivered.

**Scope**: negative · **Priority**: High  
**Source**: event-transport / M1-FR-09  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/event-transport/code/`  
**Technical references**: `construction/event-transport/functional-design/business-rules.md` (BR-PR-ET-01)

---

### TC-ET-028 — Revocation reaches a publish within the bound, at either granularity

**Context**: U6 handed its revocation timelines to S4 (TC-AC-009, TC-AC-015; D-AC-01): O3 is read through P5's cache, `not_revoked` for at most B (L1-17).

**Scenario**: In process with an injected clock: A publishes (warming the cache), its lineage is revoked, and A publishes again across the bound; then the same with the logical agent revoked.

**Preconditions**:
- E's event-ingest is running. A (`event:publish`) and B (`event:subscribe`) are registered in E with autonomy declared, and each instance holds a live agent credential for E
- Test-only revocation seeding; an injected clock

**Steps**:
1. A publishes at t = 0 (accepted)
2. Seed a `cid` revocation at t = 1 s
3. A publishes at t = 30 s and at t = 60 s
4. Repeat with a fresh lineage and an agent revocation
5. On the stack, seed a `cid` revocation and publish until refused, recording the elapsed time

**Expected outcome**: At 30 s the cached `not_revoked` (read at 0) may still be served; **from 60 s after the read the publish is `401` `credential_refused`**, for both granularities, with no difference in the response. On the stack, refused no later than 60 s (plus one request) after seeding. The security log names the granularity.

**Scope**: edge-boundary · **Priority**: High  
**Source**: event-transport / M1-FR-07  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/event-transport/code/`  
**Technical references**: `construction/event-transport/functional-design/business-rules.md` (BR-CK-02, 03); `construction/event-transport/nfr-requirements/nfr-requirements.md` (NFR-ET-01)

---

### TC-ET-029 — Unreadable revocation state: served within the bound, then denied

**Context**: PF §9: "served from cache until the bound expires, then denied" (TC-AC-010 at S4; L1-28; BR-SR-05).

**Scenario**: In process with an injected clock, the store becomes unreachable after a warm read; a publish and an open stream are observed across the bound.

**Preconditions**:
- E's event-ingest is running. A (`event:publish`) and B (`event:subscribe`) are registered in E with autonomy declared, and each instance holds a live agent credential for E
- B's stream is open; an injected clock

**Steps**:
1. A publishes at t = 0 (accepted; cache warm for A and B)
2. Make the store unreachable
3. A publishes at t = 30 s
4. Advance past 60 s and publish again
5. Observe B's stream

**Expected outcome**: At 30 s, steps 1 to 4 pass from the cache, and the publish is `503` `unavailable` at the record's write (GAP-ET-001). Past 60 s, the publish is `503` `unavailable` at step 4. B's stream stays open until its revocation answer is older than B, then ends with `end` `{ code: "unavailable" }` within R (1 s).

**Scope**: edge-boundary · **Priority**: High  
**Source**: event-transport / M1-FR-07  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/event-transport/code/`  
**Technical references**: `construction/event-transport/functional-design/business-rules.md` (BR-CK-04, BR-SR-05; D-ET-09)

---

### TC-ET-030 — One bound, one constant, no configuration key

**Context**: PF FR-012: the bound is platform-set, not tenant-configurable, and is the cache TTL (D-ET-15; L1-18; NFR-ET-01).

**Scenario**: S4's composition is built with recording cache factories; the configuration schema and S4's settings are scanned.

**Preconditions**:
- S4's `assembleRuntime` with injectable factories (NP-ET-02)

**Steps**:
1. Build S4's composition with recording factories
2. Read the `ttl` each factory received
3. With the injected clock, read revocation at t = 0 and t = 60 s
4. Scan `tenancy.schema.json` and `loadEventIngest`'s settings for a key matching `/bound|ttl|propagation/i`

**Expected outcome**: Both factories received `ttl === PROPAGATION_BOUND_MS` (imported from `@soorma/credentials`). The answer is re-read at exactly 60 s. No key matches.

**Scope**: happy-path · **Priority**: High  
**Source**: event-transport / M1-FR-07, M1-NFR-01  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/event-transport/code/`  
**Technical references**: `construction/event-transport/nfr-design/nfr-design-patterns.md` (NP-ET-02)

---

### TC-ET-031 — Neither granularity of revocation is told apart

**Context**: Revocation state is readable by no principal (PF §7a; L1-19).

**Scenario**: One credential is revoked by `cid`, another by its logical agent; each is used to publish, and each to hold a stream.

**Preconditions**:
- E's event-ingest is running. A (`event:publish`) and B (`event:subscribe`) are registered in E with autonomy declared, and each instance holds a live agent credential for E
- Test-only revocation seeding

**Steps**:
1. Seed a `cid` revocation for one lineage, an agent revocation for another agent
2. Publish with each past the bound
3. Hold a stream with each past the bound

**Expected outcome**: Both publishes are byte-identical `401` `credential_refused` Problems apart from the request id; both streams end with `end` `{ code: "credential_refused" }`. Only the security log names the granularity.

**Scope**: negative · **Priority**: High  
**Source**: event-transport / M1-FR-07  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/event-transport/code/`  
**Technical references**: `construction/event-transport/functional-design/business-rules.md` (BR-CK-03, BR-SR-03)

---

### TC-ET-032 — S4's caches never answer across environments

**Context**: PF §6: the credential-validation, revocation, and permission caches key on environment (L1-23).

**Scenario**: Cache entries for an agent of E exist; the same agent identifier, registered in E2, is checked at E2's S4.

**Preconditions**:
- E's event-ingest is running. A (`event:publish`) and B (`event:subscribe`) are registered in E with autonomy declared, and each instance holds a live agent credential for E
- An agent with A's identifier registered in E2

**Steps**:
1. In process: warm E's caches for A
2. Ask the cache of a runtime configured for E2 about A
3. On the stack: revoke A in E2 only, and publish with A's E credential at E's S4

**Expected outcome**: E's entries never answer E2's request (keys carry organization, project, environment). A's publish at E is unaffected by E2's revocation.

**Scope**: edge-boundary · **Priority**: High  
**Source**: event-transport / M1-FR-10  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/event-transport/code/`  
**Technical references**: `construction/event-transport/functional-design/business-rules.md` (BR-CK-02); `construction/event-transport/nfr-design/nfr-design-patterns.md` (NP-ET-02)

---

### TC-ET-033 — S4 learns its environment from configuration only

**Context**: Environment identity is configured, never inferred (PF O11; L1-25; I10).

**Scenario**: S4 is started with a configuration naming E and a host name, labels, and variables that suggest E2.

**Preconditions**:
- S4's configuration for E

**Steps**:
1. Start S4 with `SOORMA_ENVIRONMENT=e` and the container's host name set to look like `e2`
2. Publish with an E credential
3. Search S4's source for reads of the host name, network position, or deployment labels

**Expected outcome**: S4 serves E (O4 compares against E); the publish is accepted. The source search finds none.

**Scope**: edge-boundary · **Priority**: Medium  
**Source**: event-transport / M1-FR-10  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/event-transport/code/`  
**Technical references**: `construction/event-transport/functional-design/business-rules.md` (D-ET-13)

---

### TC-ET-034 — A record alone recovers scope, actor, chain, origin, and sponsor

**Context**: PF FR-025, §7b *Recoverability*; I4: at zero hops and across a chain (L1-26).

**Scenario**: A publishes with no forwarded context (one entry); B subscribes forwarding A's envelope (two entries, load-bearing).

**Preconditions**:
- E's event-ingest is running. A (`event:publish`) and B (`event:subscribe`) are registered in E with autonomy declared, and each instance holds a live agent credential for E
- B declares `event:subscribe` for re-broadening (TC-ET-005's set-up)

**Steps**:
1. A publishes
2. B subscribes forwarding A's envelope
3. Read each record, and with only its columns reconstruct scope, actor, chain, origin, and, through the registration, the sponsor

**Expected outcome**: The publish: scope E, actor A's instance, chain `[A]`, origin `autonomous`, not load-bearing, sponsor H. The subscribe: chain `[A, B]`, origin `autonomous`, load-bearing at hop 1, sponsor H. Nothing outside the row (and the registration it names) is needed.

**Scope**: happy-path · **Priority**: High  
**Source**: event-transport / M1-FR-12  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/event-transport/code/`  
**Technical references**: `construction/event-transport/functional-design/business-rules.md` (BR-AT-ET-01 to 04)

---

### TC-ET-035 — A record that cannot be written: nothing delivered, no stream

**Context**: GAP-ET-001's work-around: the record is synchronous and fail closed (D-ET-09; BR-PB-03; BR-SB-03).

**Scenario**: The store refuses the record's write; A publishes while B is subscribed, and C subscribes.

**Preconditions**:
- E's event-ingest is running. A (`event:publish`) and B (`event:subscribe`) are registered in E with autonomy declared, and each instance holds a live agent credential for E
- B's stream open; the record's write made to fail (in process: a failing transaction)

**Steps**:
1. A publishes
2. C subscribes
3. Read B's stream

**Expected outcome**: The publish is `503` `unavailable` with `Retry-After: 5`; B receives nothing. C's subscribe is `503` `unavailable`, a Problem; no stream opens. `store.unavailable` is logged.

**Scope**: negative · **Priority**: High  
**Source**: event-transport / M1-FR-12 (GAP-ET-001)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/event-transport/code/`  
**Technical references**: `construction/event-transport/functional-design/business-rules.md` (D-ET-09)

---

### TC-ET-036 — S4's latency on the running stack, reported

**Context**: NFR-ET-15: reported, not gated (L1-29). A Build and Test measurement.

**Scenario**: On the local stack, publishes, stream openings, and publish-to-delivery times are measured.

**Preconditions**:
- E's event-ingest is running. A (`event:publish`) and B (`event:subscribe`) are registered in E with autonomy declared, and each instance holds a live agent credential for E
- The local stack running

**Steps**:
1. Open a stream and publish 200 times, measuring each publish, each opening, and each time from a publish's request to its `delivery` read

**Expected outcome**: Reported: p95 of publish (target at most 200 ms), of opening (at most 200 ms), of publish to delivery (at most 250 ms). Not a gate.

**Scope**: edge-boundary · **Priority**: Low  
**Source**: event-transport / M1-NFR-01  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/event-transport/code/`  
**Technical references**: `construction/event-transport/nfr-requirements/nfr-requirements.md` (NFR-ET-15)

---

### TC-ET-037 — A publish leaves its record and nothing of the event

**Context**: PF §6 *Envelope (in flight)*: not stored here; live only (L1-31; GAP-INT-003).

**Scenario**: A publishes a payload with a distinctive marker.

**Preconditions**:
- E's event-ingest is running. A (`event:publish`) and B (`event:subscribe`) are registered in E with autonomy declared, and each instance holds a live agent credential for E

**Steps**:
1. A publishes a payload containing `marker-7f3c`
2. Search every table of E's store for the marker and for the seal

**Expected outcome**: One new `attribution_records` row (operation `publish`); the marker and the seal appear nowhere in the store.

**Scope**: edge-boundary · **Priority**: Medium  
**Source**: event-transport / M1-FR-11 (GAP-INT-003)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/event-transport/code/`  
**Technical references**: `construction/event-transport/functional-design/business-rules.md` (BR-PB-06)

---

### TC-ET-038 — S4's contract document holds data-face operations only

**Context**: I6: separate surfaces per face (L1-35).

**Scenario**: A reviewer checks `contract/event-ingest.openapi.yaml`.

**Preconditions**:
- The completed contract

**Steps**:
1. List its operations and security schemes

**Expected outcome**: Exactly `publish` and `subscribe`, each `agentCredential` only; no control-face operation, no human scheme. No data-face operation appears in S1's or S2's documents.

**Scope**: happy-path · **Priority**: Medium  
**Source**: event-transport / M1-FR-02, M1-NFR-03  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/event-transport/code/`  
**Technical references**: `construction/event-transport/functional-design/business-rules.md` (BR-PK-01)

---

### TC-ET-039 — Nothing of E2 is read, written, delivered, or superseded at E

**Context**: I1: one test per access and messaging path.

**Scenario**: E and E2 each run their S4; an agent of each subscribes in its own environment.

**Preconditions**:
- E's and E2's S4 running; one subscriber in each
- In process: two runtimes for E and E2, each with its own channel

**Steps**:
1. A publishes in E; an E2 agent publishes in E2
2. Each environment's subscriber reads its stream
3. In process: a `supersede` for a `cid` sent on E2's channel
4. Check each environment's store for the other's records

**Expected outcome**: Each subscriber receives only its own environment's Delivery; E's stream of the same `cid` value is untouched by E2's `supersede`; each store holds only its own records; cache entries never cross (TC-ET-032).

**Scope**: negative · **Priority**: High  
**Source**: event-transport / M1-FR-10, M1-FR-11  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/event-transport/code/`  
**Technical references**: `construction/event-transport/functional-design/business-rules.md` (BR-FO-01)

---

### TC-ET-040 — Every refusal holds for a raw call to the stack

**Context**: I2: the perimeter enforces independently of the SDK.

**Scenario**: Every refusal in business-logic-model §8 is sent to E's S4 with a raw HTTPS client.

**Preconditions**:
- E's event-ingest is running. A (`event:publish`) and B (`event:subscribe`) are registered in E with autonomy declared, and each instance holds a live agent credential for E
- The local stack running

**Steps**:
1. Send each refusal case of business-logic-model §8 as a raw call

**Expected outcome**: Each answers exactly its code, status, and headers, with a Problem passing the shared assertion.

**Scope**: negative · **Priority**: High  
**Source**: event-transport / M1-FR-09, M1-FR-02  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/event-transport/code/`  
**Technical references**: `construction/event-transport/functional-design/business-logic-model.md` (§8)

---

### TC-ET-041 — The same credential from another address is the same agent

**Context**: I3: identity from the presented credential only.

**Scenario**: A's credential is presented from the host and from inside network `e`; and no credential from inside network `e`.

**Preconditions**:
- E's event-ingest is running. A (`event:publish`) and B (`event:subscribe`) are registered in E with autonomy declared, and each instance holds a live agent credential for E
- The local stack running

**Steps**:
1. Publish with A's credential from the host
2. Publish with it from a container on network `e`
3. Publish with no credential from that container

**Expected outcome**: The first two are accepted and their records name the same actor; the third is `401` `credential_refused`.

**Scope**: edge-boundary · **Priority**: Medium  
**Source**: event-transport / M1-FR-09  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/event-transport/code/`  
**Technical references**: `construction/event-transport/functional-design/business-rules.md` (BR-CK-06)

---

### TC-ET-042 — P7 is closed both ways

**Context**: D-ET-07: an agent record outside the envelope-free list must carry envelope facts; the store repeats it. Includes the user's approved class-3 change to U5's test.

**Scenario**: Records are written through P7 and directly into the store.

**Preconditions**:
- `packages/attribution`; E's store migrated through `0005`

**Steps**:
1. Write an agent record for `publish` without envelope facts through P7
2. Insert the same row directly as the store's owner
3. Write an agent record for `exchangeBootstrap` with no envelope facts
4. Run U5's test with `operation: 'exchangeBootstrap'`

**Expected outcome**: The first is refused by P7 before any SQL; the second by the CHECK; the third is accepted (no target, no credential required). U5's test passes with its one approved change and nothing else.

**Scope**: negative · **Priority**: High  
**Source**: event-transport / M1-FR-12  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/event-transport/code/`  
**Technical references**: `construction/event-transport/functional-design/business-rules.md` (D-ET-07; BR-AT-ET-06); `construction/event-transport/nfr-design/nfr-design-patterns.md` (NP-ET-14)

---

### TC-ET-043 — S4 imports only the allowlisted names of P2 and P3

**Context**: I5: one evaluator; S4 imports only the entry point and its two construction helpers (NP-ET-03).

**Scenario**: A test scans S4's import declarations and built output.

**Preconditions**:
- S4 built

**Steps**:
1. List every name S4 imports from `@soorma/authority` and `@soorma/envelope`, in source and in the bundle

**Expected outcome**: Exactly `createEnvelopeAdmission`, `createCachingAgentFacts`, `loadSealKeyRing`, and types.

**Scope**: negative · **Priority**: High  
**Source**: event-transport / M1-FR-08  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/event-transport/code/`  
**Technical references**: `construction/event-transport/nfr-design/nfr-design-patterns.md` (NP-ET-03)

---

### TC-ET-044 — A forwarding hop never gains authority beyond the intersection

**Context**: I5: a low-authority agent's event forwarded by a higher-authority agent stays limited.

**Scenario**: D, holding `event:publish` and `event:subscribe`, forwards an envelope from C, which holds only `event:subscribe`, in a publish; D declares no re-broadening.

**Preconditions**:
- E's event-ingest is running. A (`event:publish`) and B (`event:subscribe`) are registered in E with autonomy declared, and each instance holds a live agent credential for E
- C and D registered with those standing sets, autonomy declared

**Steps**:
1. D publishes forwarding C's envelope

**Expected outcome**: `403` `forbidden`: `standing(D) ∩ standing(C)` lacks `event:publish`, and nothing re-broadens it.

**Scope**: negative · **Priority**: High  
**Source**: event-transport / M1-FR-08  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/event-transport/code/`  
**Technical references**: `construction/event-transport/functional-design/business-rules.md` (BR-PB-01)

---

### TC-ET-045 — The completed contract passes U1's compatibility check

**Context**: I7: every change to a published contract is classified and checked.

**Scenario**: U1's checks run over the contract with `event-ingest.openapi.yaml` and the convention changes.

**Preconditions**:
- The completed contract

**Steps**:
1. Run `pnpm check:contract` and U1's compatibility test against the `0.1.0` fixtures

**Expected outcome**: Both pass; every change is in `CHANGELOG.md` and classified compatible.

**Scope**: happy-path · **Priority**: High  
**Source**: event-transport / M1-FR-02, M1-NFR-04  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/event-transport/code/`  
**Technical references**: `construction/event-transport/functional-design/business-rules.md` (§14)

---

### TC-ET-046 — No topic administration, durability, or seeding path in core

**Context**: I8: the packaging table re-checked.

**Scenario**: A reviewer re-checks the I8 table and S4's image.

**Preconditions**:
- S4's image built

**Steps**:
1. Re-check every capability against the table
2. List S4's image contents for a seeding path or test fixture

**Expected outcome**: Every capability core-assigned; no topic, durable queue, or redelivery code; no seeding path or fixture in the image.

**Scope**: edge-boundary · **Priority**: Medium  
**Source**: event-transport / M1-FR-11  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/event-transport/code/`  
**Technical references**: `construction/event-transport/functional-design/invariant-coverage-matrix.md` (I8)

---

### TC-ET-047 — S4 never reads a payload beyond its bound and well-formedness

**Context**: I9: the payload is never inspected beyond its bound and its JSON well-formedness (NP-ET-05).

**Scenario**: A Code Generation review, with a check.

**Preconditions**:
- S4's source

**Steps**:
1. Search S4's source for any read of the payload other than parse, measure, and serialize

**Expected outcome**: None: the payload is parsed, measured by `jcs`, and serialized; no member is read, compared, or converted.

**Scope**: edge-boundary · **Priority**: Medium  
**Source**: event-transport / M1-FR-01  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/event-transport/code/`  
**Technical references**: `construction/event-transport/nfr-design/nfr-design-patterns.md` (NP-ET-05)

---

### TC-ET-048 — Two instances asserting one name each hold their own stream

**Context**: I10: streams key on the credential's lineage, not the asserted instance (D-ET-05).

**Scenario**: Two instances of A bootstrap asserting `a-1` (two lineages) and both subscribe.

**Preconditions**:
- E's event-ingest is running. A (`event:publish`) and B (`event:subscribe`) are registered in E with autonomy declared, and each instance holds a live agent credential for E

**Steps**:
1. Bootstrap A twice with instance `a-1`
2. Subscribe with each credential
3. Publish once

**Expected outcome**: Both streams stay open and each receives the Delivery; neither supersedes the other.

**Scope**: edge-boundary · **Priority**: Medium  
**Source**: event-transport / M1-FR-11  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/event-transport/code/`  
**Technical references**: `construction/event-transport/functional-design/business-rules.md` (D-ET-05)

---

### TC-ET-049 — The payload bound at its edge, with a large number

**Context**: NFR-ET-02; NP-ET-05 test 4: P measured on the payload's canonical form with numbers counted by their source text.

**Scenario**: Payloads at exactly 65 536 and 65 537 bytes of that form, made mostly of one long number.

**Preconditions**:
- E's event-ingest is running. A (`event:publish`) and B (`event:subscribe`) are registered in E with autonomy declared, and each instance holds a live agent credential for E

**Steps**:
1. Publish a payload `{"n": <digits>}` whose source-text canonical form is exactly 65 536 bytes
2. Publish one 1 byte longer

**Expected outcome**: The first is accepted and delivered with the number unchanged; the second is `413` `payload_too_large`.

**Scope**: edge-boundary · **Priority**: High  
**Source**: event-transport / M1-FR-11  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/event-transport/code/`  
**Technical references**: `construction/event-transport/nfr-design/nfr-design-patterns.md` (NP-ET-05)

---

### TC-ET-050 — Step-1 limits at both edges of both operations

**Context**: NFR-ET-03: subscribe 65 536 bytes, publish 262 144 bytes, refused before any credential is read.

**Scenario**: Bodies at and over each limit, with no credential.

**Preconditions**:
- S4 running

**Steps**:
1. Send each operation a body of exactly its limit, then its limit plus one byte, without a credential

**Expected outcome**: At the limit: `401` `credential_refused` (step 2). Over it: `413` `payload_too_large` (step 1). Any other path keeps 16 KiB.

**Scope**: edge-boundary · **Priority**: High  
**Source**: event-transport / M1-FR-09  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/event-transport/code/`  
**Technical references**: `construction/event-transport/nfr-requirements/nfr-requirements.md` (NFR-ET-03); `construction/event-transport/nfr-design/nfr-design-patterns.md` (NP-ET-04)

---

### TC-ET-051 — The guaranteed maximum-size forwarding draft passes step 1

**Context**: NFR-ET-04, the user's guarantee: a 32-entry chain, the defined fields, a flat unknown field padding the envelope to 16 384 JCS bytes, every non-ASCII character escaped as `\uXXXX`, indented with 2 spaces; for publish, a maximum payload serialized the same way.

**Scenario**: Exactly that body is sent to each operation.

**Preconditions**:
- E's event-ingest is running. A (`event:publish`) and B (`event:subscribe`) are registered in E with autonomy declared, and each instance holds a live agent credential for E

**Steps**:
1. Build the draft at its maximum with non-ASCII padding; serialize it escaped and indented
2. Subscribe with it; publish with it and a maximum payload serialized the same way
3. Grow each body to its limit plus one byte

**Expected outcome**: Both pass step 1 (refused, if at all, only later); each grown body is `413` `payload_too_large`.

**Scope**: edge-boundary · **Priority**: High  
**Source**: event-transport / M1-FR-01  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/event-transport/code/`  
**Technical references**: `construction/event-transport/nfr-requirements/nfr-requirements.md` (NFR-ET-04)

---

### TC-ET-052 — Maximum nesting at each operation's limit

**Context**: NFR-ET-05: U3's nesting test at S4's actual limits.

**Scenario**: Bodies of exactly each limit, as deeply nested as fits.

**Preconditions**:
- S4 running

**Steps**:
1. Send each operation a body of its limit consisting of nested arrays in `inbound.envelope`

**Expected outcome**: No crash or stack overflow; a deterministic Problem from the check order.

**Scope**: edge-boundary · **Priority**: Medium  
**Source**: event-transport / M1-FR-09  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/event-transport/code/`  
**Technical references**: `construction/event-transport/nfr-requirements/nfr-requirements.md` (NFR-ET-05)

---

### TC-ET-053 — The contract's statements on payloads and streams

**Context**: NFR-ET-06 and business-rules §14: compact JSON recommended; numbers delivered as written; I-JSON numbers not required; well-formed strings; duplicates keep the last value; the stream's events and codes; no resumption.

**Scenario**: A docs check over `envelope.md`, `errors.md`, `pre-release.md`.

**Preconditions**:
- The completed contract

**Steps**:
1. Check each statement is present, and P's value equals the code's constant

**Expected outcome**: All present, including "compact, without HTML-safe or other ASCII escaping (for example Go's `json.Encoder.SetEscapeHTML(false)`)".

**Scope**: happy-path · **Priority**: Medium  
**Source**: event-transport / M1-FR-02  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/event-transport/code/`  
**Technical references**: `construction/event-transport/nfr-requirements/nfr-requirements.md` (NFR-ET-06)

---

### TC-ET-054 — A heartbeat after 15 seconds of silence

**Context**: NFR-ET-07.

**Scenario**: In process with an injected scheduler, a stream receives nothing for 15 seconds.

**Preconditions**:
- E's event-ingest is running. A (`event:publish`) and B (`event:subscribe`) are registered in E with autonomy declared, and each instance holds a live agent credential for E
- An injected clock and scheduler

**Steps**:
1. B subscribes
2. Advance 14.9 s, then to 15 s
3. A publishes; advance 15 s more

**Expected outcome**: No comment line before 15 s; one at 15 s; the delivery re-arms it, so the next is 15 s after the delivery.

**Scope**: edge-boundary · **Priority**: Low  
**Source**: event-transport / M1-FR-11  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/event-transport/code/`  
**Technical references**: `construction/event-transport/nfr-requirements/nfr-requirements.md` (NFR-ET-07)

---

### TC-ET-055 — The open-stream cap

**Context**: NFR-ET-08, D-ET-25: 256 streams per instance; a same-lineage supersede on the instance does not count.

**Scenario**: In process, 256 lineages subscribe, then a 257th, then one of the 256 re-subscribes.

**Preconditions**:
- An S4 runtime; 257 agent credentials

**Steps**:
1. Open 256 streams
2. Subscribe with a 257th lineage
3. Re-subscribe with one of the 256's renewed credential

**Expected outcome**: The 257th is `503` `unavailable` (`Retry-After: 5`), `throttle.refused` with code `streams`, and writes no record. The re-subscribe succeeds and supersedes.

**Scope**: edge-boundary · **Priority**: High  
**Source**: event-transport / M1-FR-11  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/event-transport/code/`  
**Technical references**: `construction/event-transport/nfr-design/nfr-design-patterns.md` (NP-ET-09)

---

### TC-ET-056 — A full send buffer ends the stream with overflow

**Context**: NFR-ET-08, D-ET-06: 1 MiB per stream.

**Scenario**: A subscriber stops reading while events are published.

**Preconditions**:
- E's event-ingest is running. A (`event:publish`) and B (`event:subscribe`) are registered in E with autonomy declared, and each instance holds a live agent credential for E

**Steps**:
1. B subscribes and stops reading
2. A publishes maximum-size Deliveries until B's queued bytes pass 1 MiB

**Expected outcome**: B's stream ends: queued deliveries discarded, `end` `{ code: "overflow" }` written if possible, `stream.overflow` logged. Other streams are unaffected.

**Scope**: edge-boundary · **Priority**: High  
**Source**: event-transport / M1-FR-11  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/event-transport/code/`  
**Technical references**: `construction/event-transport/functional-design/business-rules.md` (BR-SM-06)

---

### TC-ET-057 — A stream that cannot take its end is closed after the grace

**Context**: NFR-ET-08: a 5-second grace.

**Scenario**: In process, an overflowed stream's socket accepts nothing.

**Preconditions**:
- An injected scheduler; a stalled socket

**Steps**:
1. Overflow a stream whose socket is not draining
2. Advance 4.9 s, then 5 s

**Expected outcome**: The socket is still open at 4.9 s and destroyed at 5 s.

**Scope**: edge-boundary · **Priority**: Medium  
**Source**: event-transport / M1-FR-11  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/event-transport/code/`  
**Technical references**: `construction/event-transport/nfr-design/nfr-design-patterns.md` (NP-ET-10)

---

### TC-ET-058 — The stream's encoding

**Context**: NFR-ET-10, P-05: UTF-8; `event: delivery` or `event: end`; one `data:` line; no `id:` or `retry:`; comment heartbeats.

**Scenario**: A stream's raw bytes are read.

**Preconditions**:
- E's event-ingest is running. A (`event:publish`) and B (`event:subscribe`) are registered in E with autonomy declared, and each instance holds a live agent credential for E

**Steps**:
1. B subscribes with a `Last-Event-ID` header
2. A publishes a payload with a line break inside a string
3. Read B's raw stream until the end event

**Expected outcome**: Each event is `event: delivery\ndata: <one line>\n\n`; the line break is escaped in the JSON; no `id:` or `retry:` field; the `Last-Event-ID` header changed nothing; the last event is `event: end`.

**Scope**: happy-path · **Priority**: Medium  
**Source**: event-transport / M1-FR-02  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/event-transport/code/`  
**Technical references**: `construction/event-transport/nfr-requirements/nfr-requirements.md` (NFR-ET-10)

---

### TC-ET-059 — The stream route outlives the server's ordinary timeouts

**Context**: NFR-ET-10: no server-side request or idle timeout on the stream route; other routes keep theirs.

**Scenario**: In process, a stream stays open longer than the server's ordinary timeouts.

**Preconditions**:
- An S4 runtime with its server timeouts

**Steps**:
1. Hold a stream open past the server's request and idle timeouts (heartbeats flowing)
2. Hold a slow publish request past the request timeout

**Expected outcome**: The stream stays open; the slow publish is closed by the server's timeout.

**Scope**: edge-boundary · **Priority**: Medium  
**Source**: event-transport / M1-FR-11  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/event-transport/code/`  
**Technical references**: `construction/event-transport/nfr-requirements/nfr-requirements.md` (NFR-ET-10)

---

### TC-ET-060 — Shutdown ends every stream within 5 seconds

**Context**: NFR-ET-11, NP-ET-17.

**Scenario**: S4 is stopped with streams open.

**Preconditions**:
- E's event-ingest is running. A (`event:publish`) and B (`event:subscribe`) are registered in E with autonomy declared, and each instance holds a live agent credential for E
- Three open streams

**Steps**:
1. Stop S4
2. Read each stream; send a new request during the shutdown

**Expected outcome**: Each stream ends with `end` `{ code: "unavailable" }`; the new request is not accepted; S4 exits within 5 s.

**Scope**: edge-boundary · **Priority**: Medium  
**Source**: event-transport / M1-FR-11  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/event-transport/code/`  
**Technical references**: `construction/event-transport/nfr-design/nfr-design-patterns.md` (NP-ET-17)

---

### TC-ET-061 — The throttle at S4, and a stream holds no permit

**Context**: NFR-ET-12, NP-ET-13: 64 permits, a 1-second wait, released once; a stream releases its permit when it opens.

**Scenario**: In process: 64 requests held, a 65th; then 64 streams opened and a publish.

**Preconditions**:
- An S4 runtime

**Steps**:
1. Hold 64 publishes in flight; send a 65th; advance 1 s
2. Abort 64 requests in flight (U4's 64-abort shape)
3. Open 64 streams, then publish

**Expected outcome**: The 65th is `503` `unavailable`, `Retry-After: 5`, `throttle.refused` code `requests`; after the aborts every permit is free exactly once; with 64 streams open the publish takes a permit at once.

**Scope**: edge-boundary · **Priority**: High  
**Source**: event-transport / M1-FR-11  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/event-transport/code/`  
**Technical references**: `construction/event-transport/nfr-design/nfr-design-patterns.md` (NP-ET-13)

---

### TC-ET-062 — Superseding across two instances on one channel

**Context**: NFR-ET-13, BR-FO-05: in process, two S4 runtimes share one channel object.

**Scenario**: B's lineage has a stream on instance X; B subscribes again through instance Y.

**Preconditions**:
- Two S4 runtimes over one in-process channel

**Steps**:
1. Open B's stream on X
2. Subscribe again with B's renewed credential on Y
3. Publish once

**Expected outcome**: X's stream ends with `end` `{ code: "superseded" }`; Y's stream receives the Delivery. A dropped `supersede` (the channel made to lose it) leaves both open until the earlier credential's `exp`.

**Scope**: edge-boundary · **Priority**: High  
**Source**: event-transport / M1-FR-11  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/event-transport/code/`  
**Technical references**: `construction/event-transport/functional-design/business-rules.md` (BR-FO-05, 06)

---

### TC-ET-063 — Superseding on one instance

**Context**: BR-FO-04: a later stream of the same lineage ends the earlier one, registered first so nothing is missed.

**Scenario**: B renews and subscribes again on the same instance.

**Preconditions**:
- E's event-ingest is running. A (`event:publish`) and B (`event:subscribe`) are registered in E with autonomy declared, and each instance holds a live agent credential for E

**Steps**:
1. B subscribes
2. B renews (same `cid`) and subscribes again
3. A publishes

**Expected outcome**: The first stream ends `superseded`; the second receives the Delivery; a publish accepted between the two steps reaches at least the second.

**Scope**: edge-boundary · **Priority**: High  
**Source**: event-transport / M1-FR-11  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/event-transport/code/`  
**Technical references**: `construction/event-transport/functional-design/business-rules.md` (BR-FO-04)

---

### TC-ET-064 — Two racing subscribes leave exactly one stream

**Context**: BR-FO-05, 07: the order key `(openedAt, id)` is total.

**Scenario**: Two subscribes of one lineage are registered at once on two instances sharing a channel, with the same clock reading.

**Preconditions**:
- Two S4 runtimes over one channel; an injected clock

**Steps**:
1. Register both streams at the same `openedAt`
2. Deliver both `supersede` messages

**Expected outcome**: Exactly one stream survives: the one with the larger id.

**Scope**: edge-boundary · **Priority**: Medium  
**Source**: event-transport / M1-FR-11  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/event-transport/code/`  
**Technical references**: `construction/event-transport/functional-design/business-rules.md` (BR-FO-05, 07)

---

### TC-ET-065 — The Compose model: one S4 per environment, no replicas

**Context**: D-ID-ET-14, the user's item 1; with every profile.

**Scenario**: `deploy/test/event-ingest.test.ts` renders the model.

**Preconditions**:
- `deploy/local/compose.yaml`

**Steps**:
1. Render with every profile
2. Check S4's services, limits, secrets, networks, variables

**Expected outcome**: Exactly one `event-ingest` service per environment, no `deploy.replicas`, no `scale` above 1; `mem_limit` 512m; seal keys and verify halves only in their environment's `event-ingest/`; no signing key, human ring, caller key, log-pseudonym key, or other role's password there; network `{env}` only; its variables only from the allowlist.

**Scope**: happy-path · **Priority**: High  
**Source**: event-transport / M1-NFR-05  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/event-transport/code/`  
**Technical references**: `construction/event-transport/infrastructure-design/infrastructure-design.md` (§14)

---

### TC-ET-066 — With the store down, steps 1 to 3 answer exactly

**Context**: BR-CK-05: U6's pattern; a bad credential is never `unavailable`.

**Scenario**: E's store is stopped.

**Preconditions**:
- E's event-ingest is running. A (`event:publish`) and B (`event:subscribe`) are registered in E with autonomy declared, and each instance holds a live agent credential for E
- E's store unreachable

**Steps**:
1. Publish with no credential, an `soorma_ec_` credential, a forged token, an expired token, and an E2 token

**Expected outcome**: Each is `401` `credential_refused` or `credential_expired` exactly as with the store up; none is `unavailable`.

**Scope**: negative · **Priority**: High  
**Source**: event-transport / M1-FR-09  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/event-transport/code/`  
**Technical references**: `construction/event-transport/functional-design/business-rules.md` (BR-CK-05)

---

### TC-ET-067 — TLS 1.3 at S4's edge and to its store

**Context**: NFR-ET-17.

**Scenario**: TLS versions are probed.

**Preconditions**:
- The local stack running

**Steps**:
1. Connect to 8446 and 8447 with TLS 1.2 only, then 1.3
2. Read S4's store session's TLS version

**Expected outcome**: TLS 1.2 is refused; 1.3 accepted, streams included; the session is TLS 1.3 with `verify-full`.

**Scope**: negative · **Priority**: Medium  
**Source**: event-transport / M1-NFR-06  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/event-transport/code/`  
**Technical references**: `construction/event-transport/nfr-requirements/nfr-requirements.md` (NFR-ET-17)

---

### TC-ET-068 — S4's logs carry no secret, token, seal, envelope, payload, trace value, or human

**Context**: NFR-ET-18; SECURITY-03.

**Scenario**: Every S4 test run and the stack's run are scanned.

**Preconditions**:
- S4's tests and the smoke test

**Steps**:
1. Collect every credential, seal, payload marker, `traceparent`, and human identifier the tests used
2. Scan S4's log output

**Expected outcome**: None appears; every S4 line is JSON with a named event; no line has a human-principal field.

**Scope**: negative · **Priority**: High  
**Source**: event-transport / M1-NFR-06  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/event-transport/code/`  
**Technical references**: `construction/event-transport/nfr-requirements/nfr-requirements.md` (NFR-ET-18)

---

### TC-ET-069 — S4's events and alert rules, the overlap pinned

**Context**: NFR-ET-18, 19; NP-ET-16.

**Scenario**: The monitoring files are validated.

**Preconditions**:
- `deploy/monitoring/`

**Steps**:
1. Run the monitoring tests with S4's events

**Expected outcome**: `alerts.yaml` lists every event once; S4's overlap with S1 to S3 is exactly `store.unavailable` and `throttle.refused`; S4's four rules carry their thresholds, grouped by environment or code; none by agent.

**Scope**: happy-path · **Priority**: Medium  
**Source**: event-transport / M1-NFR-06  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/event-transport/code/`  
**Technical references**: `construction/event-transport/nfr-design/nfr-design-patterns.md` (NP-ET-16)

---

### TC-ET-070 — service-kit's route body limits are additive

**Context**: NP-ET-04: without the option nothing changes.

**Scenario**: service-kit's adapter with and without route limits.

**Preconditions**:
- `packages/service-kit`

**Steps**:
1. Run service-kit's existing tests unchanged
2. Build an adapter with `{ '/x': 32768 }` and send 32 768 and 32 769 bytes to `/x` and 16 385 to `/y`

**Expected outcome**: The existing tests pass unchanged; `/x` accepts 32 768 and refuses 32 769; `/y` refuses 16 385.

**Scope**: happy-path · **Priority**: Medium  
**Source**: event-transport / M1-NFR-06  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/event-transport/code/`  
**Technical references**: `construction/event-transport/nfr-design/nfr-design-patterns.md` (NP-ET-04)

---

### TC-ET-071 — An integer above 2^53 is delivered unchanged

**Context**: NP-ET-05 test 1, the user's design.

**Scenario**: A publishes `{"id": 12345678901234567890}`.

**Preconditions**:
- E's event-ingest is running. A (`event:publish`) and B (`event:subscribe`) are registered in E with autonomy declared, and each instance holds a live agent credential for E
- B subscribed

**Steps**:
1. A publishes the payload
2. Read B's Delivery's payload text

**Expected outcome**: Accepted; delivered as `{"id":12345678901234567890}`, in process and on the stack.

**Scope**: happy-path · **Priority**: High  
**Source**: event-transport / M1-FR-11  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/event-transport/code/`  
**Technical references**: `construction/event-transport/nfr-design/nfr-design-patterns.md` (NP-ET-05)

---

### TC-ET-072 — A long decimal and an exponent form are delivered exactly

**Context**: NP-ET-05 test 2.

**Scenario**: A publishes `[0.10000000000000000555, 6.02214076e23, 1E+400, -0]`.

**Preconditions**:
- E's event-ingest is running. A (`event:publish`) and B (`event:subscribe`) are registered in E with autonomy declared, and each instance holds a live agent credential for E
- B subscribed

**Steps**:
1. A publishes the payload
2. Read B's Delivery's payload text

**Expected outcome**: Delivered as `[0.10000000000000000555,6.02214076e23,1E+400,-0]`: every number as written.

**Scope**: happy-path · **Priority**: High  
**Source**: event-transport / M1-FR-11  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/event-transport/code/`  
**Technical references**: `construction/event-transport/nfr-design/nfr-design-patterns.md` (NP-ET-05)

---

### TC-ET-073 — A lone surrogate in a payload is refused with a pointer

**Context**: NP-ET-05 test 3: no JCS form.

**Scenario**: A publishes `{"a": "\ud800"}`.

**Preconditions**:
- E's event-ingest is running. A (`event:publish`) and B (`event:subscribe`) are registered in E with autonomy declared, and each instance holds a live agent credential for E

**Steps**:
1. A publishes the payload

**Expected outcome**: `400` `malformed_request`, `errors[0].pointer` `/payload/a`; nothing delivered.

**Scope**: negative · **Priority**: High  
**Source**: event-transport / M1-FR-01  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/event-transport/code/`  
**Technical references**: `construction/event-transport/nfr-design/nfr-design-patterns.md` (NP-ET-05)

---

### TC-ET-074 — `packages/jcs`'s source mode, and its default unchanged

**Context**: NP-ET-05 test 5.

**Scenario**: `canonicalize` in both modes.

**Preconditions**:
- `packages/jcs`

**Steps**:
1. Run U3's `jcs` tests unchanged
2. Canonicalize a raw number, a raw non-number, a plain number, and a lone surrogate with `{ numbers: 'source' }`
3. Canonicalize a raw number in the default mode

**Expected outcome**: U3's tests pass unchanged. Source mode: the raw number's text exactly; the raw non-number, the plain number, and the lone surrogate refused, each with its pointer. Default mode: the raw value refused, as before.

**Scope**: happy-path · **Priority**: High  
**Source**: event-transport / M1-FR-01  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/event-transport/code/`  
**Technical references**: `construction/event-transport/nfr-design/nfr-design-patterns.md` (NP-ET-05)

---

### TC-ET-075 — S4 refuses to start without `JSON.rawJSON`

**Context**: NP-ET-05 test 6: the start-up check; no fallback.

**Scenario**: S4's start is run with `JSON.rawJSON` removed.

**Preconditions**:
- S4's `main`

**Steps**:
1. Stub `JSON.rawJSON` away and start S4
2. Start S4 normally

**Expected outcome**: The first refuses to start with a `ConfigurationError` logged; the second starts.

**Scope**: negative · **Priority**: High  
**Source**: event-transport / M1-NFR-06  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/event-transport/code/`  
**Technical references**: `construction/event-transport/nfr-design/nfr-design-patterns.md` (NP-ET-05)

---

### TC-ET-076 — Duplicate payload member names keep the last value

**Context**: NP-ET-05; stated in the contract.

**Scenario**: A publishes `{"k": 1, "k": 2}`.

**Preconditions**:
- E's event-ingest is running. A (`event:publish`) and B (`event:subscribe`) are registered in E with autonomy declared, and each instance holds a live agent credential for E
- B subscribed

**Steps**:
1. A publishes the payload
2. Read B's Delivery

**Expected outcome**: Delivered as `{"k":2}`.

**Scope**: edge-boundary · **Priority**: Low  
**Source**: event-transport / M1-FR-11  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/event-transport/code/`  
**Technical references**: `construction/event-transport/nfr-design/nfr-design-patterns.md` (NP-ET-05)

---

### TC-ET-077 — The Body Form on `admit`

**Context**: NP-ET-06; BR-BF-03 to 05, 07: additive; U3's suite unchanged; new tests.

**Scenario**: U3's entry point with and without the Body Form.

**Preconditions**:
- `packages/authority`

**Steps**:
1. Run U3's suite unchanged
2. With the publish form: a non-object body; no `draft`; a non-object `draft`; an extra member; no `payload`; a stamped field with an extra member; a payload over its bound
3. With the subscribe form: an extra `payload` member

**Expected outcome**: U3's suite passes unchanged. `malformed_request` `""`; `malformed_request` `/draft` (twice); `unknown_field` `/extra`; `malformed_request` `/payload`; `stamped_field_set` (precedence); `payload_too_large`; `unknown_field` `/payload`.

**Scope**: happy-path · **Priority**: High  
**Source**: event-transport / M1-FR-01  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/event-transport/code/`  
**Technical references**: `construction/event-transport/nfr-design/nfr-design-patterns.md` (NP-ET-06)

---

### TC-ET-078 — The verify-only key ring

**Context**: NP-ET-07: additive in P5; U4's and U6's tests unchanged.

**Scenario**: `loadVerifyKeyRing` and `verifyAgentCredential` over it.

**Preconditions**:
- `packages/credentials`

**Steps**:
1. Run U4's and U6's P5 tests unchanged
2. Load SPKI halves: one valid, a repeated key, none, a non-Ed25519 key, a private key
3. Verify an S3-minted token with the verify-only ring

**Expected outcome**: Existing tests unchanged. The valid half loads; each other case is refused, naming it. The token verifies; its `exp` is returned.

**Scope**: happy-path · **Priority**: High  
**Source**: event-transport / M1-FR-07  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/event-transport/code/`  
**Technical references**: `construction/event-transport/nfr-design/nfr-design-patterns.md` (NP-ET-07)

---

### TC-ET-079 — A stream's headers, and its deliveries in order

**Context**: NP-ET-10.

**Scenario**: A stream is opened and several events published.

**Preconditions**:
- E's event-ingest is running. A (`event:publish`) and B (`event:subscribe`) are registered in E with autonomy declared, and each instance holds a live agent credential for E

**Steps**:
1. B subscribes; read the response head
2. A publishes three events in sequence

**Expected outcome**: `200`, `text/event-stream; charset=utf-8`, `Cache-Control: no-store`, `Soorma-Contract-Version`, `Soorma-Request-Id`; B receives the three in the order accepted (observed, not promised).

**Scope**: happy-path · **Priority**: Medium  
**Source**: event-transport / M1-FR-11  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/event-transport/code/`  
**Technical references**: `construction/event-transport/nfr-design/nfr-design-patterns.md` (NP-ET-10)

---

### TC-ET-080 — One frame per publish, the same for every stream

**Context**: NP-ET-11.

**Scenario**: In process, three streams receive one publish.

**Preconditions**:
- An S4 runtime with three streams

**Steps**:
1. Publish once; capture the frame each stream writes

**Expected outcome**: The three frames are the same string, serialized once.

**Scope**: edge-boundary · **Priority**: Low  
**Source**: event-transport / M1-FR-11  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/event-transport/code/`  
**Technical references**: `construction/event-transport/nfr-design/nfr-design-patterns.md` (NP-ET-11)

---

### TC-ET-081 — Migrations `0005` and `0006`

**Context**: NP-ET-14: the reverse rule's CHECK alone, then S4's grants.

**Scenario**: E's store migrated from empty.

**Preconditions**:
- `packages/env-store`

**Steps**:
1. Migrate an empty store
2. Run TC-EHA-068's migration-list test

**Expected outcome**: `0001` to `0006` applied in order; TC-EHA-068's list gains exactly the two names (class 1).

**Scope**: happy-path · **Priority**: Medium  
**Source**: event-transport / M1-FR-12  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/event-transport/code/`  
**Technical references**: `construction/event-transport/nfr-design/nfr-design-patterns.md` (NP-ET-14)

---

### TC-ET-082 — `soorma_env_ingest`'s privileges, with the real statements

**Context**: NP-ET-15, D-ID-ET-04.

**Scenario**: The role's attributes and privileges are tested.

**Preconditions**:
- A store migrated through `0006`

**Steps**:
1. Check the role's attributes
2. As the role, run U5's agent-facts statement, the sponsor statement, P5's revocation statement, and P7's insert
3. As the role, select `ceiling_snapshot`, update or delete any row, read `grants`, `credentials`, `agent_credentials`, `registration_secrets`

**Expected outcome**: U4's attributes; the four statements succeed; every other attempt is refused. U4's, U5's, and U6's store tests pass with the harness's new export (class 1).

**Scope**: negative · **Priority**: High  
**Source**: event-transport / M1-NFR-06  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/event-transport/code/`  
**Technical references**: `construction/event-transport/nfr-design/nfr-design-patterns.md` (NP-ET-15)

---

### TC-ET-083 — S4's dependency closure and image packages

**Context**: NP-ET-18, D-ID-ET-08.

**Scenario**: S4's manifests and image are checked.

**Preconditions**:
- S4's image built

**Steps**:
1. Walk S4's production dependency closure
2. Run `image-packages --forbid @soorma/org-identity,@soorma/identity-resolution,@soorma/agent-identity,@soorma/abuse-bound`
3. Run the image secret scan

**Expected outcome**: None of the four packages; no secret pattern.

**Scope**: negative · **Priority**: High  
**Source**: event-transport / M1-NFR-08  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/event-transport/code/`  
**Technical references**: `construction/event-transport/infrastructure-design/infrastructure-design.md` (§3)

---

### TC-ET-084 — `stack:init` writes each environment's seal key, never overwriting it

**Context**: D-ID-ET-05, the user's item 3.

**Scenario**: `stack:init` runs on an empty and on a populated directory.

**Preconditions**:
- An empty `.secrets/`

**Steps**:
1. Run `stack:init`
2. Record `e-seal-key-1` and `e2-seal-key-1`
3. Run it again

**Expected outcome**: Each is base64url text of 256 bits, the two differ, and the second run leaves both byte-identical; `{env}-db-ingest-password` likewise.

**Scope**: happy-path · **Priority**: High  
**Source**: event-transport / M1-NFR-05  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/event-transport/code/`  
**Technical references**: `construction/event-transport/infrastructure-design/infrastructure-design.md` (§4)

---

### TC-ET-085 — The smoke test at S3's depth

**Context**: D-ID-ET-10, as changed at the user's review.

**Scenario**: `stack:smoke` on a fresh stack.

**Preconditions**:
- The local stack running

**Steps**:
1. Run `pnpm stack:smoke`

**Expected outcome**: Per environment: health, port, hardening; exactly five secrets, 65532, 0400; TLS 1.3; the 401 Problem; an agent registered through that S2 (with the event permissions and autonomy, through `registeredAgent`'s new optional parameter), bootstrapped at that S3, subscribing and publishing at that S4, receiving its own Delivery with that environment's scope and a seal; `soorma_env_ingest` with U4's attributes and S4's session as it over TLS 1.3, right after the round trip; then E's credential refused at E2's S4; the log scan. U6's smoke checks pass unchanged.

**Scope**: happy-path · **Priority**: High  
**Source**: event-transport / M1-NFR-05  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/event-transport/code/`  
**Technical references**: `construction/event-transport/infrastructure-design/infrastructure-design.md` (§9)

---

### TC-ET-086 — U5's backup round trip with S4

**Context**: D-ID-ET-12, the user's item 7: class 1.

**Scenario**: TC-AR-059, 056, 060 run with `e-event-ingest` in their lists.

**Preconditions**:
- The local stack running

**Steps**:
1. Run U5's backup round trip

**Expected outcome**: It passes with every assertion unchanged; `e-event-ingest` is stopped, removed, and back healthy with the others.

**Scope**: edge-boundary · **Priority**: Medium  
**Source**: event-transport / M1-NFR-05  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/event-transport/code/`  
**Technical references**: `construction/event-transport/infrastructure-design/infrastructure-design.md` (§11)

---

### TC-ET-087 — S4's README Operations match the code

**Context**: D-ID-ET-13, 18.

**Scenario**: A docs test over S4's README.

**Preconditions**:
- `services/event-ingest/README.md`

**Steps**:
1. Check the seal rotation's three steps, "at least 24 hours", the consequence sentence, the verify-key step, and the constants against the code

**Expected outcome**: All present and equal to the code's values.

**Scope**: happy-path · **Priority**: Low  
**Source**: event-transport / M1-NFR-05  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/event-transport/code/`  
**Technical references**: `construction/event-transport/infrastructure-design/infrastructure-design.md` (§12)

---

### TC-ET-088 — S4's memory, measured against its limit

**Context**: D-ID-ET-17, the user's Q1: measured at Code Generation, the peak recorded; above 460 MiB, a stop.

**Scenario**: S4 on the stack, idle and under the worst case.

**Preconditions**:
- The local stack running

**Steps**:
1. Read S4's memory idle
2. Open 256 streams that stop reading until each buffer holds 1 MiB, with 64 concurrent maximum-size publishes
3. Read the peak

**Expected outcome**: Both numbers recorded beside `mem_limit: 512m`. A peak above 460 MiB stops Code Generation for the user; the limit is never raised.

**Scope**: edge-boundary · **Priority**: High  
**Source**: event-transport / M1-NFR-05  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/event-transport/code/`  
**Technical references**: `construction/event-transport/infrastructure-design/infrastructure-design.md` (§8)

---

### TC-ET-089 — `loadEventIngest` refuses a shared secret or another role

**Context**: D-ID-ET-19, the user's correction: a config test for each case.

**Scenario**: `tenancy.yaml` variants are loaded.

**Preconditions**:
- `packages/config`

**Steps**:
1. For each of a seal key, an agent verify key, and the database password, name it also in E2's part, in S2's part, in S3's part, and at the organization level (twelve variants)
2. Set `database.user` to S2's, S3's, and the migrator's role
3. Load the committed local `tenancy.yaml`

**Expected outcome**: Each of the fifteen variants is refused, naming the secret or the role; the committed file loads. `stack-ca-cert` is the one name allowed in several parts.

**Scope**: negative · **Priority**: High  
**Source**: event-transport / M1-FR-10  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/event-transport/code/`  
**Technical references**: `construction/event-transport/infrastructure-design/infrastructure-design.md` (§6)

---

### TC-ET-090 — An envelope sealed in E2 is refused when forwarded in E

**Context**: I1 and the seal: one ring per environment.

**Scenario**: An E2 agent's Delivery is forwarded to E's S4 by an E agent.

**Preconditions**:
- E's event-ingest is running. A (`event:publish`) and B (`event:subscribe`) are registered in E with autonomy declared, and each instance holds a live agent credential for E
- A Delivery received in E2

**Steps**:
1. A, in E, publishes forwarding the E2 envelope and seal

**Expected outcome**: `400` `invalid_inbound_context`; nothing delivered.

**Scope**: negative · **Priority**: High  
**Source**: event-transport / M1-FR-10  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/event-transport/code/`  
**Technical references**: `construction/event-transport/functional-design/business-rules.md` (BR-FO-01)

---

### TC-ET-091 — `humanGrants` grants nothing at S4

**Context**: D-ET-14: no human enters an agent's chain in M1.

**Scenario**: S4's composition is inspected.

**Preconditions**:
- S4's runtime

**Steps**:
1. Ask S4's `humanGrants` for any principal

**Expected outcome**: The empty set, always; S4's role has no privilege on `grants` (TC-ET-082).

**Scope**: edge-boundary · **Priority**: Low  
**Source**: event-transport / M1-FR-08  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/event-transport/code/`  
**Technical references**: `construction/event-transport/functional-design/business-rules.md` (D-ET-14)

---

### TC-ET-092 — Neither operation returns its own hop's envelope

**Context**: D-ET-02.

**Scenario**: A publishes; B subscribes forwarding A's envelope.

**Preconditions**:
- E's event-ingest is running. A (`event:publish`) and B (`event:subscribe`) are registered in E with autonomy declared, and each instance holds a live agent credential for E

**Steps**:
1. A publishes; read the response
2. B subscribes forwarding; read the stream's first events

**Expected outcome**: Publish is `202` with no body; B's stream carries only `delivery` (and later `end`) events, never its own stamped envelope.

**Scope**: happy-path · **Priority**: Medium  
**Source**: event-transport / M1-FR-11  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/event-transport/code/`  
**Technical references**: `construction/event-transport/functional-design/business-rules.md` (D-ET-02)

---
