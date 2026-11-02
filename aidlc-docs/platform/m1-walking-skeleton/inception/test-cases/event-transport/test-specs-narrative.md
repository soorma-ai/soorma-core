# Test Specifications (Narrative): event-transport

**Unit**: `event-transport` (U7: event publish, subscribe and live delivery within an environment, data face)  
**Unit abbreviation**: ET = event-transport  
**Scope**: comprehensive (happy path, negative, edge and boundary), as recorded in `aidlc-state.md`  
**Derived from**: `aidlc-docs/platform/m1-walking-skeleton/inception/application-design/unit-of-work.md` and `aidlc-docs/platform/m1-walking-skeleton/inception/requirements/requirements.md` only  
**Generated**: inception pass, 2026-11-02. IDs are permanent

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

**Expected outcome**: B's stream yields one `Delivery`, carrying A's payload unchanged.

**Scope**: happy-path · **Priority**: High  
**Source**: event-transport / M1-FR-11  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/event-transport/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

---

### TC-ET-002 — The delivered envelope carries scope, origin and a stamped chain

**Context**: *Done when* 4: the envelope B receives carries scope, origin, and an actor chain appended by the perimeter, not by A (M1-FR-01).

**Scenario**: B inspects the delivered envelope.

**Preconditions**:
- E's event-ingest is running. A (`event:publish`) and B (`event:subscribe`) are registered in E with autonomy declared, and each instance holds a live agent credential for E
- One Delivery received by B, from A

**Steps**:
1. Read the envelope in the Delivery

**Expected outcome**: Scope E, origin `autonomous`, and actor chain `[A's instance]`. A's draft carried none of these.

**Scope**: happy-path · **Priority**: High  
**Source**: event-transport / M1-FR-01, M1-FR-08  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/event-transport/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

---

### TC-ET-003 — Trace context is carried as asserted

**Context**: Trace context is agent-asserted and carried, validated for well-formedness only (M1-FR-01). soorma-core emits no spans.

**Scenario**: A publishes with a known `traceparent`.

**Preconditions**:
- E's event-ingest is running. A (`event:publish`) and B (`event:subscribe`) are registered in E with autonomy declared, and each instance holds a live agent credential for E

**Steps**:
1. A publishes with `traceparent` T
2. B reads the Delivery

**Expected outcome**: The delivered envelope's trace context is T.

**Scope**: happy-path · **Priority**: Medium  
**Source**: event-transport / M1-FR-01  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/event-transport/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

---

### TC-ET-004 — A publish is attributed

**Context**: Publishing is a platform-resource operation, and is attributed (M1-FR-12, in U7).

**Scenario**: A reviewer inspects attribution after a publish.

**Preconditions**:
- E's event-ingest is running. A (`event:publish`) and B (`event:subscribe`) are registered in E with autonomy declared, and each instance holds a live agent credential for E
- A has published once

**Steps**:
1. Read the attribution record for the publish

**Expected outcome**: The record carries scope E, A's instance as actor, chain `[A]`, and origin `autonomous`.

**Scope**: happy-path · **Priority**: Medium  
**Source**: event-transport / M1-FR-12  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/event-transport/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

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

**Expected outcome**: Allowed. The resulting envelope has chain `[A, B]`, origin `autonomous` unchanged, and a re-broadening record naming B's hop.

**Scope**: happy-path · **Priority**: High  
**Source**: event-transport / M1-FR-08  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/event-transport/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

---

### TC-ET-006 — A publish with a credential from another environment is denied

**Context**: *Done when* 6: the same publish, attempted with a credential from another environment, is denied (O4; M1-FR-09).

**Scenario**: An instance holding an agent credential from E2 publishes to E.

**Preconditions**:
- E's event-ingest is running. A (`event:publish`) and B (`event:subscribe`) are registered in E with autonomy declared, and each instance holds a live agent credential for E
- E2 running, with an agent registered there holding `event:publish` and a live credential from E2

**Steps**:
1. Publish to E's ingest, presenting the E2 credential

**Expected outcome**: Denied. B receives nothing.

**Scope**: negative · **Priority**: High  
**Source**: event-transport / M1-FR-09, M1-FR-10  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/event-transport/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

---

### TC-ET-007 — A draft setting a platform-stamped field is rejected at ingest

**Context**: *Done when* 7: a draft in which the agent sets a platform-stamped field is rejected (M1-FR-01). Ingest checks it itself (O10).

**Scenario**: A publishes six drafts, each setting one platform-stamped field.

**Preconditions**:
- E's event-ingest is running. A (`event:publish`) and B (`event:subscribe`) are registered in E with autonomy declared, and each instance holds a live agent credential for E

**Steps**:
1. For each of envelope version, scope, origin mode, delegating principal, actor chain, and re-broadening record, publish a draft that sets it

**Expected outcome**: All six are rejected, and B receives nothing.

**Scope**: negative · **Priority**: High  
**Source**: event-transport / M1-FR-01, M1-FR-09  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/event-transport/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

---

### TC-ET-008 — A draft asserting `autonomous` is rejected at ingest

**Context**: Origin is stamped on every first hop, and an asserted origin is rejected (the GAP-INT-007 work-around, in U7's inherited gaps).

**Scenario**: A, autonomy declared, publishes a draft asserting `autonomous`.

**Preconditions**:
- E's event-ingest is running. A (`event:publish`) and B (`event:subscribe`) are registered in E with autonomy declared, and each instance holds a live agent credential for E

**Steps**:
1. Publish a draft containing origin mode `autonomous`

**Expected outcome**: Rejected.

**Scope**: negative · **Priority**: High  
**Source**: event-transport / M1-FR-01 (GAP-INT-007)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/event-transport/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

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

**Expected outcome**: Both are denied.

**Scope**: negative · **Priority**: High  
**Source**: event-transport / M1-FR-08  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/event-transport/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

---

### TC-ET-010 — A publish without `event:publish` is denied

**Context**: `event:publish` applies in the environment's namespace (M1-FR-11).

**Scenario**: B, without `event:publish`, publishes.

**Preconditions**:
- E's event-ingest is running. A (`event:publish`) and B (`event:subscribe`) are registered in E with autonomy declared, and each instance holds a live agent credential for E

**Steps**:
1. B publishes with no forwarded context

**Expected outcome**: Denied.

**Scope**: negative · **Priority**: High  
**Source**: event-transport / M1-FR-11  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/event-transport/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

---

### TC-ET-011 — A subscribe without `event:subscribe` is denied

**Context**: `event:subscribe` applies in the environment's namespace (M1-FR-11).

**Scenario**: A, without `event:subscribe`, subscribes.

**Preconditions**:
- E's event-ingest is running. A (`event:publish`) and B (`event:subscribe`) are registered in E with autonomy declared, and each instance holds a live agent credential for E

**Steps**:
1. A opens a subscribe stream with no forwarded context

**Expected outcome**: Denied. No stream opens.

**Scope**: negative · **Priority**: High  
**Source**: event-transport / M1-FR-11  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/event-transport/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

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

**Expected outcome**: Both are refused.

**Scope**: negative · **Priority**: High  
**Source**: event-transport / M1-FR-09, M1-FR-11  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/event-transport/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

---

### TC-ET-013 — A delegation credential is refused

**Context**: In M1 no delegation credential can be live, so a delegation credential, alone or beside an agent's, is refused by its own checks (M1-FR-09).

**Scenario**: A request presents a credential shaped as a delegation credential beside A's credential.

**Preconditions**:
- E's event-ingest is running. A (`event:publish`) and B (`event:subscribe`) are registered in E with autonomy declared, and each instance holds a live agent credential for E

**Steps**:
1. Publish, presenting A's credential and a delegation-credential-shaped token

**Expected outcome**: Refused.

**Scope**: negative · **Priority**: High  
**Source**: event-transport / M1-FR-09  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/event-transport/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

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

**Expected outcome**: Denied.

**Scope**: negative · **Priority**: High  
**Source**: event-transport / M1-FR-07  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/event-transport/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

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

**Expected outcome**: The E2 subscriber receives nothing.

**Scope**: negative · **Priority**: High  
**Source**: event-transport / M1-FR-10, M1-FR-11  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/event-transport/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

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

**Expected outcome**: B's stream has ended by expiry plus the bound, and the later event is not delivered to B.

**Scope**: edge-boundary · **Priority**: High  
**Source**: event-transport / M1-FR-11  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/event-transport/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

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

**Expected outcome**: B's stream has ended within the bound of the revocation, and the later event is not delivered.

**Scope**: edge-boundary · **Priority**: High  
**Source**: event-transport / M1-FR-11, M1-FR-07  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/event-transport/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

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

**Expected outcome**: B does not receive the earlier event.

**Scope**: edge-boundary · **Priority**: Medium  
**Source**: event-transport / M1-FR-11 (GAP-INT-003)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/event-transport/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

---

### TC-ET-019 — A forwarded chain at maxChainDepth cannot grow

**Context**: `maxChainDepth` is enforced at every hop (M1-FR-01).

**Scenario**: An agent publishes forwarding an envelope whose chain is already at `maxChainDepth`.

**Preconditions**:
- E's event-ingest is running. A (`event:publish`) and B (`event:subscribe`) are registered in E with autonomy declared, and each instance holds a live agent credential for E
- An inbound envelope with a chain of length `maxChainDepth`

**Steps**:
1. Publish a draft forwarding that envelope

**Expected outcome**: Rejected.

**Scope**: edge-boundary · **Priority**: Medium  
**Source**: event-transport / M1-FR-01  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/event-transport/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

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

**Expected outcome**: Origin is `autonomous`, as stamped for A, and the chain is `[A, B]`.

**Scope**: edge-boundary · **Priority**: Medium  
**Source**: event-transport / M1-FR-08  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/event-transport/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

---

### TC-ET-021 — Ingest checks independently of the gateways

**Context**: Neither entry point treats the other's traffic as pre-validated (O10; M1-FR-09).

**Scenario**: A request that would pass a gateway check reaches ingest with an invalid credential.

**Preconditions**:
- E's event-ingest is running. A (`event:publish`) and B (`event:subscribe`) are registered in E with autonomy declared, and each instance holds a live agent credential for E

**Steps**:
1. Publish to ingest with a malformed agent credential, adding any header that claims prior validation

**Expected outcome**: Refused. Ingest performs its own checks regardless.

**Scope**: edge-boundary · **Priority**: High  
**Source**: event-transport / M1-FR-09  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/event-transport/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

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

**Expected outcome**: B receives the Delivery.

**Scope**: edge-boundary · **Priority**: High  
**Source**: event-transport / M1-FR-11 (M1-NFR-08)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/event-transport/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

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

**Expected outcome**: `x-future` is present in the delivered envelope.

**Scope**: edge-boundary · **Priority**: Medium  
**Source**: event-transport / M1-FR-01  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/event-transport/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

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

**Expected outcome**: Every one of the unit's operations is present and references the conventions. The violating request is rejected with the contract's error model before any processing.

**Scope**: happy-path · **Priority**: High  
**Source**: event-transport / M1-FR-02  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/event-transport/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

---
