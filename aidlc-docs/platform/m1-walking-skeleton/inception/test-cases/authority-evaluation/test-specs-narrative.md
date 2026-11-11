# Test Specifications (Narrative): authority-evaluation

**Unit**: `authority-evaluation` (U3: authority evaluation and the envelope, data face)  
**Unit abbreviation**: AE = authority-evaluation  
**Scope**: comprehensive (happy path, negative, edge and boundary), as recorded in `aidlc-state.md`  
**Derived from**: `aidlc-docs/platform/m1-walking-skeleton/inception/application-design/unit-of-work.md` and `aidlc-docs/platform/m1-walking-skeleton/inception/requirements/requirements.md` only  
**Generated**: inception pass, 2026-11-02. IDs are permanent  
**Enriched**: construction pass, 2026-11-10 (TC-AE-001 to 022 updated in place; TC-AE-023 to 040 added). Sources: U3's `functional-design/`, `nfr-requirements/` (by the user's instruction, as for U1 and U2: F38), and `nfr-design/` (`infrastructure-design/` does not exist: skipped for U3)

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

### Construction pass: U3's fixtures and fixed values (2026-11-10)

**U3 has no edge surface.** Every case runs **in-process**, against U3's packages, not the
local stack. Unless a case says otherwise, it calls the entry point, `admit`, built by
`createEnvelopeAdmission` (`nfr-design/nfr-design-patterns.md` NP-05), after a constructed
Checked Agent Context stands in for steps 1 to 4.

| Name | Meaning |
|---|---|
| **admission(E)** | `createEnvelopeAdmission` for E: accepted versions `{0.1.0}`; E's configured scope; E's test key ring; the caching agent-facts decorator over the in-memory source; P11's default as the policy factory; a collecting security log; an injected clock |
| **context(X)** | A Checked Agent Context for agent X in E: scope E (organization, project, environment), agent X, an instance id |
| **draft** | `{ clientContractVersion: "0.1.0", traceContext: { traceparent: <valid, version 00> } }` unless a case adds to it |
| **facts** | The in-memory agent-facts source: per agent, a Registration View (autonomy declared, re-broadening declaration) and a standing set; with a **call counter** and an injectable failure or delay |
| **humans** | An in-memory human `GrantSource` |
| **ring(E)**, **ring(E2)** | Test seal key rings, `{ current: k1, keys: [k1] }`, different keys per environment (fixed test keys, never production secrets) |
| **sealed(env, X)** | An envelope stamped and sealed by admission(E) for agent X's request (or constructed and sealed with ring(E) when a case needs a shape the platform would not stamp) |
| **C** | An agent registered in E with **autonomy not declared** |
| **`maxChainDepth`** | **32** (D-WC-05) |
| **the envelope bound** | **16384 bytes** of the RFC 8785 (JCS) serialization, UTF-8 (BR-DR-09, D-AE-22) |
| **the bound** | The propagation bound: the agent-facts cache's TTL (NP-04). Its value is U6's; U3's tests inject one |
| **the security log** | Each refusal writes exactly one `envelope_refused` event: code, internal reason, request id, environment, agent, instance (NP-08) |

A refusal is checked by its **contract code** and, where the case names one, its
**internal reason in the security log**. A response never carries the reason.

---

### TC-AE-001 — A valid draft is stamped with all six platform fields

**Context**: The perimeter writes the six platform-stamped fields (M1-FR-01). It is the core of what the envelope proves.

**Scenario**: A valid draft from an instance of A in E is stamped.

**Preconditions**:
- The authority and envelope modules are exercised directly, at the evaluation level, with constructed inputs (unit-of-work.md: U3 has no edge surface)
- A draft with a client contract version and a well-formed trace context
- A registered with autonomy declared, in E
- *(Construction pass)* admission(E); facts holds A with `{event:publish}`; context(A); required `{event:publish}`; no `inbound`

**Steps**:
1. Validate the draft
2. Stamp it with A's checked context
3. *(Construction pass)* Run both as one `admit` call, and verify the returned seal with ring(E)

**Expected outcome**: The envelope carries envelope version, scope E, origin `autonomous`, actor chain `[A's instance]`, and the trace context as asserted. There is no delegating principal and no re-broadening record. *(Construction pass)* Exactly: `envelopeVersion` `1`; `scope` equal to context(A)'s scope, **from the credential, not from configuration** (D-AE-08); `originMode` `autonomous`; `actorChain` `[{ agent: A, instance }]`; `traceContext` the draft's; no `delegatingPrincipal`, no `reBroadening`, no other field. The seal is `v1.k1.{43 base64url characters}` and verifies over the envelope's JCS bytes (NP-01). The envelope's JCS form is at most 16384 bytes.

**Scope**: happy-path · **Priority**: High  
**Source**: authority-evaluation / M1-FR-01  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/authority-evaluation/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; `construction/authority-evaluation/functional-design/business-rules.md` (BR-ST-01, 05 to 07; D-AE-08); `construction/authority-evaluation/nfr-design/nfr-design-patterns.md` (NP-01)

---

### TC-AE-002 — Autonomous origin is stamped for a declaring agent with no inbound context

**Context**: With no inbound context, an agent that declared autonomy acts `autonomous` (M1-FR-08). Every M1 chain starts this way.

**Scenario**: A, autonomy declared, acts with no forwarded context.

**Preconditions**:
- The authority and envelope modules are exercised directly, at the evaluation level, with constructed inputs (unit-of-work.md: U3 has no edge surface)
- A registered with autonomy declared
- *(Construction pass)* facts holds A with autonomy declared

**Steps**:
1. Resolve origin for A with no inbound envelope
2. *(Construction pass)* Also run `admit` for A with no `inbound`, and a draft that carries no origin

**Expected outcome**: Origin is `autonomous`, derived from A's registration. *(Construction pass)* It is read from the presenter's Registration View in the request's single agent-facts read (BR-OR-01; NP-04), never from the draft.

**Scope**: happy-path · **Priority**: High  
**Source**: authority-evaluation / M1-FR-08  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/authority-evaluation/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; `construction/authority-evaluation/functional-design/business-rules.md` (BR-OR-01)

---

### TC-AE-003 — Origin propagates unchanged from an inbound envelope, and the chain grows

**Context**: An event-triggered hop propagates origin unchanged, and the chain grows (M1-FR-08).

**Scenario**: B, triggered by A's envelope, acts while forwarding it.

**Preconditions**:
- The authority and envelope modules are exercised directly, at the evaluation level, with constructed inputs (unit-of-work.md: U3 has no edge surface)
- An envelope stamped for A: `autonomous`, chain `[A]`
- *(Construction pass)* The envelope and seal are sealed(E, A), as admission(E) returned them; facts holds A and B, both declaring autonomy, both holding `{event:publish}`

**Steps**:
1. Resolve origin for B with A's envelope forwarded
2. Stamp B's draft
3. *(Construction pass)* Run as one `admit` for context(B), with `inbound: { envelope, seal }`, required `{event:publish}`

**Expected outcome**: Origin is `autonomous`, unchanged, and the chain is `[A, B]`. *(Construction pass)* A's chain entry is carried **exactly as received**, then `{ agent: B, instance }`. `scope` is the forwarded one, equal to E's. The new seal verifies. facts' call counter shows **one** call, for `[B, A]` (NP-04).

**Scope**: happy-path · **Priority**: High  
**Source**: authority-evaluation / M1-FR-08, M1-FR-01  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/authority-evaluation/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; `construction/authority-evaluation/functional-design/business-rules.md` (BR-ST-02; BR-OR-03); `construction/authority-evaluation/nfr-design/nfr-design-patterns.md` (NP-04)

---

### TC-AE-004 — Authority is allowed when every term holds the permission

**Context**: Effective authority is the intersection across the chain (M1-FR-08).

**Scenario**: B, forwarding A's context, needs `event:publish`, and both hold it.

**Preconditions**:
- The authority and envelope modules are exercised directly, at the evaluation level, with constructed inputs (unit-of-work.md: U3 has no edge surface)
- A's and B's standing sets both include `event:publish`

**Steps**:
1. Evaluate B's request for `event:publish` with chain terms [A]

**Expected outcome**: Allowed, without re-broadening. *(Construction pass)* `evaluateAgent` returns `allowed: true`, `loadBearing: false`; through `admit`, the envelope has no `reBroadening`.

**Scope**: happy-path · **Priority**: High  
**Source**: authority-evaluation / M1-FR-08  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/authority-evaluation/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; `construction/authority-evaluation/functional-design/business-logic-model.md` (§3)

---

### TC-AE-005 — Load-bearing re-broadening allows, and is recorded at the declaring hop

**Context**: Re-broadening recovers what upstream agents narrowed away. It is exercised and recorded only when load-bearing (M1-FR-08).

**Scenario**: B, forwarding A's context, needs `event:subscribe`. A lacks it, and B holds and declared it.

**Preconditions**:
- The authority and envelope modules are exercised directly, at the evaluation level, with constructed inputs (unit-of-work.md: U3 has no edge surface)
- B's standing set and declaration include `event:subscribe`
- A's standing set excludes `event:subscribe`

**Steps**:
1. Evaluate B's request for `event:subscribe` with chain terms [A]
2. Stamp B's envelope

**Expected outcome**: Allowed, by re-broadening. The envelope carries a re-broadening record naming B's hop. *(Construction pass)* The record is `{ hop: 1 }`: B's zero-based index in the new chain `[A, B]` (BR-ST-04).

**Scope**: happy-path · **Priority**: High  
**Source**: authority-evaluation / M1-FR-08, M1-FR-01  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/authority-evaluation/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; `construction/authority-evaluation/functional-design/business-rules.md` (BR-AU-04, 05; BR-ST-04)

---

### TC-AE-006 — The policy-decision boundary decides containment, never composition

**Context**: The policy-decision seam decides containment, never composition (M1-FR-13).

**Scenario**: The policy-decision boundary is asked whether a permission is contained in a set.

**Preconditions**:
- The authority and envelope modules are exercised directly, at the evaluation level, with constructed inputs (unit-of-work.md: U3 has no edge surface)
- *(Construction pass)* P11's default built for E over a `GrantSource` holding agent A with `{event:publish}`

**Steps**:
1. Ask whether `event:publish` is contained in {`event:publish`}
2. Ask whether `event:publish` is contained in {}
3. *(Construction pass)* Ask `contains({event:publish}, {event:publish, event:subscribe})`
4. *(Construction pass)* Ask `contains({event:*}, {event:publish})`
5. *(Construction pass)* Ask `grantedSet(A, E)` and `grantedSet(A, E2)`
6. *(Construction pass)* Inspect the seam's type declarations

**Expected outcome**: Contained, and not contained, respectively. The interface offers no operation that returns an effective set. *(Construction pass)* Step 3: not contained (every required member must be). Step 4: not contained (literal containment, no wildcard). Step 5: `{event:publish}`, then the empty set (one environment, deny by default). Step 6: exactly two operations, `grantedSet` (one principal's own granted set) and `contains`. None composes sets (D-AE-02; BR-SEAM-01 to 03).

**Scope**: happy-path · **Priority**: Medium  
**Source**: authority-evaluation / M1-FR-13  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/authority-evaluation/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; `construction/authority-evaluation/functional-design/business-rules.md` (D-AE-02; BR-SEAM-01 to 05)

---

### TC-AE-007 — A well-formed trace context is accepted and carried as asserted

**Context**: Trace context is required, and is validated for well-formedness only, against W3C Trace Context (M1-FR-01).

**Scenario**: A draft carries a valid `traceparent` and `tracestate`.

**Preconditions**:
- The authority and envelope modules are exercised directly, at the evaluation level, with constructed inputs (unit-of-work.md: U3 has no edge surface)

**Steps**:
1. Validate a draft with a well-formed `traceparent` and `tracestate`
2. Stamp it
3. *(Construction pass)* Repeat with a version-`01` `traceparent` carrying a further `-`-separated field, and a `tracestate` of exactly 32 list members

**Expected outcome**: Accepted. Both values appear in the envelope unchanged. *(Construction pass)* Step 3 is accepted too (BR-TC-02, 03). The values are never interpreted (D-AE-17).

**Scope**: happy-path · **Priority**: Medium  
**Source**: authority-evaluation / M1-FR-01  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/authority-evaluation/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; `construction/authority-evaluation/functional-design/business-rules.md` (D-AE-17)

---

### TC-AE-008 — Unknown fields are preserved, and unknown enumerated values are non-fatal

**Context**: Unknown fields are preserved and forwarded, and unknown enumerated values are non-fatal (M1-FR-01).

**Scenario**: A forwarded inbound envelope carries an unknown field and an unknown enumerated value in an extension field.

**Preconditions**:
- The authority and envelope modules are exercised directly, at the evaluation level, with constructed inputs (unit-of-work.md: U3 has no edge surface)
- An inbound envelope with an extra field `x-future`
- *(Construction pass)* The envelope is constructed and sealed with ring(E), with an unknown field at **every** level U3 does not replace: the envelope (`x-future`), `scope`, A's actor reference, and (in a second envelope) a re-broadening record

**Steps**:
1. Validate and stamp a draft forwarding that envelope

**Expected outcome**: Processing succeeds, and `x-future` is present in the resulting envelope. *(Construction pass)* Every unknown field, at every level, is present in the new envelope with its value unchanged (D-AE-14). The unknown `originMode` case is TC-AE-025.

**Scope**: happy-path · **Priority**: Medium  
**Source**: authority-evaluation / M1-FR-01  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/authority-evaluation/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; `construction/authority-evaluation/functional-design/business-rules.md` (D-AE-14; BR-ST-02)

---

### TC-AE-009 — A draft setting any platform-stamped field is rejected

**Context**: A draft that sets a platform-stamped field is rejected, never overwritten (M1-FR-01). It is *done when* 7's mechanism.

**Scenario**: Six drafts each set one platform-stamped field.

**Preconditions**:
- The authority and envelope modules are exercised directly, at the evaluation level, with constructed inputs (unit-of-work.md: U3 has no edge surface)

**Steps**:
1. For each of envelope version, scope, origin mode, delegating principal, actor chain, and re-broadening record, validate a draft that sets it

**Expected outcome**: All six are rejected, each naming the field. None is stamped. *(Construction pass)* Each is `stamped_field_set`, with one `errors[]` entry whose pointer is the field (`/envelopeVersion`, `/scope`, `/originMode`, `/delegatingPrincipal`, `/actorChain`, `/reBroadening`). facts is never called.

**Scope**: negative · **Priority**: High  
**Source**: authority-evaluation / M1-FR-01  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/authority-evaluation/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; `construction/authority-evaluation/functional-design/business-rules.md` (BR-DV-02 to 05)

---

### TC-AE-010 — A draft asserting origin `autonomous` is rejected

**Context**: Origin is stamped by the perimeter on every hop, and a draft setting origin mode is rejected (M1-FR-01, the GAP-INT-007 work-around). This holds even at an autonomous first hop.

**Scenario**: A, autonomy declared, sends a draft asserting `autonomous`.

**Preconditions**:
- The authority and envelope modules are exercised directly, at the evaluation level, with constructed inputs (unit-of-work.md: U3 has no edge surface)
- A registered with autonomy declared

**Steps**:
1. Validate A's draft containing origin mode `autonomous`

**Expected outcome**: Rejected, although the asserted value matches what the perimeter would stamp. *(Construction pass)* `stamped_field_set`, pointer `/originMode` (BR-DV-04).

**Scope**: negative · **Priority**: High  
**Source**: authority-evaluation / M1-FR-01 (GAP-INT-007)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/authority-evaluation/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; `construction/authority-evaluation/functional-design/business-rules.md` (BR-DV-04)

---

### TC-AE-011 — With no inbound context and no declared autonomy, the agent is denied

**Context**: With no inbound context, an agent that did not declare autonomy is denied (O12, M1-FR-08). Otherwise silence would widen authority.

**Scenario**: An agent C without declared autonomy acts with no forwarded context.

**Preconditions**:
- The authority and envelope modules are exercised directly, at the evaluation level, with constructed inputs (unit-of-work.md: U3 has no edge surface)
- C registered with autonomy not declared
- *(Construction pass)* facts holds C, autonomy not declared, with `{event:publish}` in its standing set

**Steps**:
1. Resolve origin for C with no inbound envelope

**Expected outcome**: Denied (O12). No envelope is stamped. *(Construction pass)* `forbidden`; the security log has reason `o12_undeclared` (BR-OR-02). Holding the permission does not change it.

**Scope**: negative · **Priority**: High  
**Source**: authority-evaluation / M1-FR-08  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/authority-evaluation/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; `construction/authority-evaluation/functional-design/business-rules.md` (BR-OR-02)

---

### TC-AE-012 — A malformed trace context is rejected

**Context**: Trace context must be well-formed against W3C Trace Context (M1-FR-01).

**Scenario**: A draft carries an invalid `traceparent`.

**Preconditions**:
- The authority and envelope modules are exercised directly, at the evaluation level, with constructed inputs (unit-of-work.md: U3 has no edge surface)

**Steps**:
1. Validate a draft whose `traceparent` has the wrong length or version
2. *(Construction pass)* Separately: version `ff`; an all-zero trace id; an all-zero parent id; uppercase hex; a `tracestate` of 33 list members; a `tracestate` with an invalid key; a `tracestate` over 512 characters

**Expected outcome**: Rejected, naming trace context. *(Construction pass)* Each is `malformed_request`, with a pointer to `/traceContext/traceparent` or `/traceContext/tracestate` (BR-DV-03; D-AE-17).

**Scope**: negative · **Priority**: Medium  
**Source**: authority-evaluation / M1-FR-01  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/authority-evaluation/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; `construction/authority-evaluation/functional-design/business-rules.md` (BR-DV-03; D-AE-17)

---

### TC-AE-013 — A draft without a client contract version is rejected

**Context**: A draft declares its client contract version (M1-FR-01).

**Scenario**: A draft omits the client contract version.

**Preconditions**:
- The authority and envelope modules are exercised directly, at the evaluation level, with constructed inputs (unit-of-work.md: U3 has no edge surface)

**Steps**:
1. Validate a draft with no client contract version
2. *(Construction pass)* Repeat with `clientContractVersion: 1` (not a string)

**Expected outcome**: Rejected. *(Construction pass)* Both are `unsupported_contract_version`, listing `supportedVersions: ["0.1.0"]`, at step 5: declaring no version is not declaring an accepted one (BR-VR-02). The other step 5 cases are TC-AE-030.

**Scope**: negative · **Priority**: Medium  
**Source**: authority-evaluation / M1-FR-01  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/authority-evaluation/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; `construction/authority-evaluation/functional-design/business-rules.md` (BR-VR-02)

---

### TC-AE-014 — An agent-set re-broadening record is rejected

**Context**: Re-broadening is declared at registration and recorded by the perimeter, never requested (M1-FR-08).

**Scenario**: B's draft includes a re-broadening record.

**Preconditions**:
- The authority and envelope modules are exercised directly, at the evaluation level, with constructed inputs (unit-of-work.md: U3 has no edge surface)

**Steps**:
1. Validate B's draft that sets a re-broadening record

**Expected outcome**: Rejected. *(Construction pass)* `stamped_field_set`, pointer `/reBroadening` (BR-DV-04).

**Scope**: negative · **Priority**: High  
**Source**: authority-evaluation / M1-FR-08  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/authority-evaluation/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; `construction/authority-evaluation/functional-design/business-rules.md` (BR-DV-04)

---

### TC-AE-015 — Without re-broadening, an upstream gap denies

**Context**: The intersection denies a permission any term lacks, unless re-broadening is declared and load-bearing (M1-FR-08).

**Scenario**: B, forwarding A's context, needs `event:subscribe`. A lacks it, and B holds it but did not declare it.

**Preconditions**:
- The authority and envelope modules are exercised directly, at the evaluation level, with constructed inputs (unit-of-work.md: U3 has no edge surface)
- B holds `event:subscribe`, and its declaration is empty
- A lacks `event:subscribe`

**Steps**:
1. Evaluate B's request for `event:subscribe` with chain terms [A]

**Expected outcome**: Denied. No re-broadening record. *(Construction pass)* Through `admit`: `forbidden`, reason `authority_denied` (BR-AU-10).

**Scope**: negative · **Priority**: High  
**Source**: authority-evaluation / M1-FR-08  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/authority-evaluation/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; `construction/authority-evaluation/functional-design/business-rules.md` (BR-AU-10)

---

### TC-AE-016 — Re-broadening never recovers what the delegating principal lacked

**Context**: At the declaring hop, effective authority is `standing ∩ delegating principal ∩ (upstream ∪ declared)`, so the delegating principal's limit always stands (M1-FR-08). M1 stamps no delegating principal, so this is verified with a constructed input.

**Scenario**: A constructed chain with a delegating-principal term lacking `p`, where B declared `p`.

**Preconditions**:
- The authority and envelope modules are exercised directly, at the evaluation level, with constructed inputs (unit-of-work.md: U3 has no edge surface)
- A constructed delegating-principal term without `p`
- B holds and declared `p`; the upstream agent lacks `p`

**Steps**:
1. Evaluate B's request for `p`
2. *(Construction, consistency fix, 2026-11-11)* With no `P` term: B holds and declared `p`, and forwards a sealed envelope whose chain names an agent X that facts reports **not found**. Evaluate B's request for `p`, through `admit` and on `evaluateAgent`

**Expected outcome**: Denied, and no re-broadening record. *(Construction pass)* Exercised on `evaluateAgent` directly, with a constructed `P` term. Through `admit` a delegated origin is refused earlier (TC-AE-025), so this row is reachable only at the evaluation level (business-logic-model §3, row 4). Step 2: **allowed**, re-broadening load-bearing, and the stamped envelope carries `reBroadening` `[{ hop: 1 }]`. X's term is the empty set and evaluation continues (D-AE-09), exactly as for a registered X with no grants; what an unresolved upstream agent lacked, the presenter's declaration recovers, while what the delegating principal lacked it never does.

**Scope**: edge-boundary · **Priority**: High  
**Source**: authority-evaluation / M1-FR-08  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/authority-evaluation/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; `construction/authority-evaluation/functional-design/business-logic-model.md` (§3)

---

### TC-AE-017 — The chain at maxChainDepth is accepted; one more hop is rejected

**Context**: `maxChainDepth` is enforced (M1-FR-01). Its value is fixed at U3's Functional Design.

**Scenario**: Forwarded envelopes with chains of length `maxChainDepth − 1` and `maxChainDepth`.

**Preconditions**:
- The authority and envelope modules are exercised directly, at the evaluation level, with constructed inputs (unit-of-work.md: U3 has no edge surface)
- `maxChainDepth` from U3's Functional Design
- *(Construction pass)* `maxChainDepth` = **32**. Both forwarded envelopes are constructed and sealed with ring(E)

**Steps**:
1. Stamp a draft forwarding a chain of length `maxChainDepth − 1`
2. Stamp a draft forwarding a chain of length `maxChainDepth`

**Expected outcome**: The first produces a chain of length `maxChainDepth`. The second is rejected. *(Construction pass)* The first: a chain of 32. The second: `chain_too_deep` at step 8, **with zero calls to facts** (BR-CD-02); nothing is truncated.

**Scope**: edge-boundary · **Priority**: High  
**Source**: authority-evaluation / M1-FR-01  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/authority-evaluation/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; `construction/authority-evaluation/functional-design/business-rules.md` (BR-CD-01, 02; D-AE-13)

---

### TC-AE-018 — Re-broadening is local to its hop

**Context**: Later hops intersect against the chain as though the declaring hop had not re-broadened (M1-FR-08).

**Scenario**: After B re-broadens for `event:subscribe`, agent D, triggered by B, needs `event:subscribe`. D holds it but did not declare it.

**Preconditions**:
- The authority and envelope modules are exercised directly, at the evaluation level, with constructed inputs (unit-of-work.md: U3 has no edge surface)
- A chain [A, B] with B's re-broadening record
- D holds `event:subscribe`, with an empty declaration
- *(Construction pass)* The chain is TC-AE-005's sealed result, `reBroadening [{hop: 1}]`

**Steps**:
1. Evaluate D's request for `event:subscribe` with chain terms [A, B]
2. *(Construction pass)* Repeat with D's declaration `{event:subscribe}`

**Expected outcome**: Denied, because A's term still lacks it. B's re-broadening is not inherited. *(Construction pass)* Step 1: `forbidden`; B's record grants D nothing (D-AE-20). Step 2: allowed, load-bearing at D's own hop: the new envelope's `reBroadening` is `[{hop: 1}, {hop: 2}]`, B's record carried unchanged.

**Scope**: edge-boundary · **Priority**: High  
**Source**: authority-evaluation / M1-FR-08  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/authority-evaluation/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; `construction/authority-evaluation/functional-design/business-rules.md` (BR-AU-06; D-AE-20; BR-ST-04)

---

### TC-AE-019 — Non-load-bearing re-broadening is not recorded

**Context**: The record is stamped only when re-broadening was load-bearing (M1-FR-01).

**Scenario**: B declared `event:publish`, but A also holds it.

**Preconditions**:
- The authority and envelope modules are exercised directly, at the evaluation level, with constructed inputs (unit-of-work.md: U3 has no edge surface)
- A and B both hold `event:publish`, and B declared it

**Steps**:
1. Evaluate B's `event:publish` request with chain terms [A]
2. Stamp the envelope
3. *(Construction pass)* Repeat at a first hop: B with no `inbound`, declaring `event:publish`

**Expected outcome**: Allowed, and the envelope has no re-broadening record. *(Construction pass)* Step 3: allowed, no record; at a first hop re-broadening is never load-bearing (BR-AU-07).

**Scope**: edge-boundary · **Priority**: Medium  
**Source**: authority-evaluation / M1-FR-01, M1-FR-08  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/authority-evaluation/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; `construction/authority-evaluation/functional-design/business-rules.md` (BR-AU-05, 07)

---

### TC-AE-020 — A permission outside the standing set is always denied

**Context**: Outside the declaring agent's standing set, every row of the case table denies (M1-FR-08).

**Scenario**: B requests a permission it does not hold.

**Preconditions**:
- The authority and envelope modules are exercised directly, at the evaluation level, with constructed inputs (unit-of-work.md: U3 has no edge surface)
- B's standing set excludes `attribution:read`

**Steps**:
1. Evaluate B's request for `attribution:read` with no chain
2. *(Construction pass)* Repeat with B's declaration containing `attribution:read` (a registration U5 would reject) and an upstream agent holding it

**Expected outcome**: Denied. *(Construction pass)* Both `forbidden`: `W` is intersected with B's standing set, so a declaration wider than it grants nothing (BR-AU-04).

**Scope**: edge-boundary · **Priority**: High  
**Source**: authority-evaluation / M1-FR-08  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/authority-evaluation/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; `construction/authority-evaluation/functional-design/business-rules.md` (BR-AU-04)

---

### TC-AE-021 — Evaluation is deny-by-default for an empty or unknown set

**Context**: The minimal model denies by default (M1-FR-08).

**Scenario**: An agent with an empty standing set requests anything.

**Preconditions**:
- The authority and envelope modules are exercised directly, at the evaluation level, with constructed inputs (unit-of-work.md: U3 has no edge surface)
- An agent with an empty standing set

**Steps**:
1. Evaluate a request for `event:publish`
2. *(Construction pass)* B forwards a sealed envelope whose chain names an agent X that facts reports **not found**; B holds `event:publish` and declares nothing
3. *(Construction pass)* The presenter itself is not found in facts

**Expected outcome**: Denied. *(Construction pass)* Step 2: `forbidden`, reason `upstream_unresolved`: X's term is the empty set, and B's declaration does not cover the request (D-AE-09; with a declaration that covers it, the request is allowed: TC-AE-016 step 2). Step 3: `forbidden`, reason `presenter_unresolved` (D-AE-24). Neither not-found is cached: a second request after X is added to facts reads it (TC-AE-034).

**Scope**: edge-boundary · **Priority**: Medium  
**Source**: authority-evaluation / M1-FR-08  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/authority-evaluation/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; `construction/authority-evaluation/functional-design/business-rules.md` (BR-AU-08, 10; D-AE-09, 24)

---

### TC-AE-022 — Evaluation matches every row of the re-broadening case table

**Context**: The PF §8b case table defines four outcomes for `p` in the declaring agent's standing set (M1-FR-08). Constructed chains cover all of them.

**Scenario**: Four constructed inputs, one per case-table row, using a constructed delegating-principal term where needed.

**Preconditions**:
- The authority and envelope modules are exercised directly, at the evaluation level, with constructed inputs (unit-of-work.md: U3 has no edge surface)

**Steps**:
1. Row 1: `p` in the principal's term, in every upstream term, declared either way
2. Row 2: `p` in the principal's term, missing upstream, declared
3. Row 3: `p` in the principal's term, missing upstream, not declared
4. Row 4: `p` not in the principal's term

**Expected outcome**: The outcomes, in order, are: allow with no record; allow with a record; deny; deny. *(Construction pass)* Rows 1 to 3 run through `admit` in autonomous origin (the principal's term imposes nothing), with the values of business-logic-model §3; row 4 runs on `evaluateAgent` with a constructed `P`. The test is table-driven.

**Scope**: edge-boundary · **Priority**: High  
**Source**: authority-evaluation / M1-FR-08  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/authority-evaluation/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; `construction/authority-evaluation/functional-design/business-logic-model.md` (§3)

---

### TC-AE-023 — An agent without declared autonomy forwarding an autonomous envelope is denied

**Context**: GAP-AE-001's work-around (D-AE-01; soorma-prd#30): an `autonomous` origin, stamped or propagated, requires the presenter's own declaration. M1 builds O12 as written until the PRD decides.

**Scenario**: C, autonomy not declared, forwards A's sealed autonomous envelope.

**Preconditions**:
- facts holds A (autonomy declared, `{event:publish}`) and C (autonomy **not** declared, `{event:publish}`)
- sealed(E, A)

**Steps**:
1. `admit` for context(C), forwarding A's envelope and seal, required `{event:publish}`

**Expected outcome**: `forbidden`; the security log has reason `o12_undeclared` (BR-OR-04). No envelope is stamped. It is refused although C and A both hold the permission.

**Scope**: negative · **Priority**: High  
**Source**: authority-evaluation / M1-FR-08 (GAP-AE-001)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/authority-evaluation/code/`  
**Technical references**: `construction/authority-evaluation/functional-design/business-rules.md` (D-AE-01; BR-OR-04); `construction/authority-evaluation/prd-gaps/specification-gaps.md` (GAP-AE-001)

---

### TC-AE-024 — Every forwarded-context failure is one code, with the cause only in the log

**Context**: A forwarded envelope is verified before use; every cause is `invalid_inbound_context`, and the response never says which (BR-FC-03; BR-FX-01 to 05, 07).

**Scenario**: B forwards a series of bad envelopes.

**Preconditions**:
- facts holds A and B; sealed(E, A) as the base

**Steps**:
1. Change one character of A's envelope, keep the seal
2. Forward an envelope sealed with ring(E2)
3. A seal naming a key id not in ring(E)
4. Malformed seals: `v2.k1.{mac}`; a MAC of 42 characters; a MAC with a character outside base64url; a MAC whose 43 characters do not re-encode identically
5. A constructed envelope with `envelopeVersion: 2`, sealed with ring(E)
6. A constructed envelope whose `scope` names E2, sealed with ring(E)
7. Constructed envelopes, sealed with ring(E), with `reBroadening [{hop: 5}]` on a chain of 2, and with `[{hop: 0}, {hop: 0}]`
8. An envelope whose JCS form is 16385 bytes
9. An envelope with a lone surrogate (`"\ud800"`) in an unknown field

**Expected outcome**: Every one is `invalid_inbound_context`, with **no detail** in the refusal. The security log reasons are, in order: `seal_failed` (1 to 4), `envelope_version`, `scope_mismatch`, `rebroadening_index`, `inbound_too_large`, `jcs_invalid`. In 3 and 4 no MAC is computed (NP-01). facts is never called.

**Scope**: negative · **Priority**: High  
**Source**: authority-evaluation / M1-FR-01, M1-FR-08  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/authority-evaluation/code/`  
**Technical references**: `construction/authority-evaluation/functional-design/business-rules.md` (BR-FX-01 to 07); `construction/authority-evaluation/nfr-design/nfr-design-patterns.md` (NP-01, NP-03)

---

### TC-AE-025 — A forwarded `delegated` or unknown origin is refused, not crashed

**Context**: M1 cannot evaluate a delegating principal, and an unknown enumerated value must not be fatal (D-AE-07; PF FR-005 b).

**Scenario**: Constructed envelopes sealed with ring(E), one with `originMode: "delegated"` and a `delegatingPrincipal`, one with `originMode: "x-future-mode"`.

**Preconditions**:
- facts holds B, declaring autonomy

**Steps**:
1. `admit` for context(B) forwarding each

**Expected outcome**: Both `forbidden`, reason `origin_unsupported` (BR-OR-05). No exception, no `malformed_request`, no `internal_error`.

**Scope**: edge-boundary · **Priority**: High  
**Source**: authority-evaluation / M1-FR-01, M1-FR-08  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/authority-evaluation/code/`  
**Technical references**: `construction/authority-evaluation/functional-design/business-rules.md` (D-AE-07; BR-OR-05)

---

### TC-AE-026 — A human-only permission is never an agent's

**Context**: The human-only class is refused at evaluation whatever the standing set holds (D-AE-03; defence in depth behind U5's check).

**Scenario**: A's standing set wrongly contains `grant:human`, `human:manage`, and `agent:delegate`.

**Preconditions**:
- facts holds A, declaring autonomy, with those three in its standing set

**Steps**:
1. `admit` for context(A) with required `{grant:human}`, then `{human:manage}`, then `{agent:delegate}`
2. Inspect `HUMAN_ONLY_PERMISSIONS` exported by `packages/authority`

**Expected outcome**: Each `forbidden`, reason `human_only_permission` (BR-AU-03). The export is exactly those three identifiers, the single definition U5's registration check imports.

**Scope**: negative · **Priority**: High  
**Source**: authority-evaluation / M1-FR-08  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/authority-evaluation/code/`  
**Technical references**: `construction/authority-evaluation/functional-design/business-rules.md` (D-AE-03; BR-AU-03)

---

### TC-AE-027 — The stamped trace context carries forwarded unknown fields, and only the draft's known ones

**Context**: U1 amendment A6 (D-AE-05): the new `traceContext` is the forwarded one's unknown fields plus the draft's `traceparent`, and the draft's `tracestate` only if sent.

**Scenario**: A constructed envelope sealed with ring(E) whose `traceContext` is `{ traceparent: T0, tracestate: "a=1", x-trace-future: "v" }`.

**Preconditions**:
- facts holds A and B

**Steps**:
1. B forwards it with a draft `traceContext: { traceparent: T1 }`
2. B forwards it with a draft `traceContext: { traceparent: T1, tracestate: "b=2" }`

**Expected outcome**: Step 1: `{ x-trace-future: "v", traceparent: T1 }`, **no `tracestate`**. Step 2: `{ x-trace-future: "v", traceparent: T1, tracestate: "b=2" }`. T0 and `a=1` never appear.

**Scope**: edge-boundary · **Priority**: High  
**Source**: authority-evaluation / M1-FR-01  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/authority-evaluation/code/`  
**Technical references**: `construction/authority-evaluation/functional-design/business-rules.md` (D-AE-05; BR-ST-03); `construction/wire-contract/functional-design/business-rules.md` (amendment A6)

---

### TC-AE-028 — An envelope over the bound is refused at stamping, never truncated

**Context**: The perimeter refuses to stamp an envelope over 16384 JCS bytes, so every stamped envelope can be forwarded (BR-ENV-10; BR-ST-06).

**Scenario**: Constructed forwarded envelopes, sealed with ring(E), padded with an unknown field.

**Preconditions**:
- facts holds A and B

**Steps**:
1. Forward one whose new envelope (with B's hop appended) would be exactly 16384 bytes
2. Forward one whose new envelope would be 16385 bytes
3. As 2, but where B's hop would also add a load-bearing re-broadening record that crosses the bound

**Expected outcome**: Step 1 is admitted, and the new envelope is exactly 16384 bytes. Steps 2 and 3: `envelope_too_large` at step 10, reason `envelope_bound`, after authority; nothing is dropped to fit.

**Scope**: edge-boundary · **Priority**: High  
**Source**: authority-evaluation / M1-FR-01  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/authority-evaluation/code/`  
**Technical references**: `construction/authority-evaluation/functional-design/business-rules.md` (BR-ST-06; D-AE-22)

---

### TC-AE-029 — Step 6 refuses with one code, in a fixed precedence

**Context**: Stamped fields, then unknown fields, then any other schema failure (D-AE-18; BR-DV-02, 03).

**Scenario**: Drafts with several faults.

**Preconditions**:
- None beyond admission(E)

**Steps**:
1. A draft with `scope`, an unknown top-level field `foo`, and a malformed `traceparent`
2. A draft with `foo`, `bar`, and a malformed `traceparent`
3. A draft with an unknown field inside `traceContext`
4. A draft with only a malformed `traceparent`
5. *(Construction, consistency fix, 2026-11-11)* A draft with 15 unknown fields and a malformed `traceparent`; one with 12 malformed fields; and one with 12 malformed fields and one unknown field whose pointer sorts after them all

**Expected outcome**: 1: `stamped_field_set`, `errors[]` = `[/scope]`. 2: `unknown_field`, `errors[]` = `[/bar, /foo]`, ordered by pointer. 3: `unknown_field`, pointer into `/traceContext`. 4: `malformed_request`. 5: `errors[]` holds **at most 10** entries, the first 10 by pointer (D-AE-18): `unknown_field` with 10; `malformed_request` with 10; and `unknown_field` with only the unknown field, because the code is picked from every failure before the list is cut. facts is never called.

**Scope**: negative · **Priority**: Medium  
**Source**: authority-evaluation / M1-FR-01  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/authority-evaluation/code/`  
**Technical references**: `construction/authority-evaluation/functional-design/business-rules.md` (D-AE-18; BR-DV-02, 03)

---

### TC-AE-030 — Step 5 on a draft call: the body, the version, and the header

**Context**: Version on a draft call (D-AE-12; BR-VR-01 to 05).

**Scenario**: Requests that fail step 5 in each way.

**Preconditions**:
- None beyond admission(E)

**Steps**:
1. Body `[]`, then `"x"`, then `null`
2. `clientContractVersion: "0.2.0"`
3. A valid draft with `Soorma-Contract-Version: 0.1.1`
4. A valid draft with the header sent twice, both `0.1.0`
5. A valid draft with the header `0.1.0`; and with no header
6. A body with `clientContractVersion: "0.2.0"` and a stamped field

**Expected outcome**: 1: `malformed_request`, pointer `""`. 2: `unsupported_contract_version`, `supportedVersions: ["0.1.0"]`. 3 and 4: `malformed_request`, one `errors[]` entry naming the header. 5: both admitted. 6: `unsupported_contract_version` (step 5 runs before step 6).

**Scope**: negative · **Priority**: Medium  
**Source**: authority-evaluation / M1-FR-01  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/authority-evaluation/code/`  
**Technical references**: `construction/authority-evaluation/functional-design/business-rules.md` (D-AE-12; BR-VR-01 to 05)

---

### TC-AE-031 — Every Problem soorma-core emits meets BR-ERR-08

**Context**: Problem emission moves into P1, with one shared assertion every edge runs (D-AE-06; BR-PE-01 to 06).

**Scenario**: P1's table and S1 after the move.

**Preconditions**:
- P1's `problemResponse` and its test-only `assertProblem`

**Steps**:
1. For every code in P1's table, build a Problem for request id `r-1` and run `assertProblem`
2. Check every contract code U3 can return is in P1's table
3. Run S1's existing edge tests, with `assertProblem` in place of S1's former local helper
4. Check `services/org-gateway/src/problems.ts` no longer exists

**Expected outcome**: 1: each has `type` `urn:soorma:problem:{code}`, `title`, `status`, `code`, `instance` `urn:soorma:request:r-1`; `Content-Type: application/problem+json; charset=utf-8`; `WWW-Authenticate: Bearer` on a 401 only; `Retry-After` on a 429 or 503; `unsupported_contract_version` lists `supportedVersions`; each conforms to the `Problem` schema. 2: all present. 3: every U2 test passes, no check dropped. 4: removed.

**Scope**: happy-path · **Priority**: High  
**Source**: authority-evaluation / M1-FR-01  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/authority-evaluation/code/`  
**Technical references**: `construction/authority-evaluation/functional-design/business-rules.md` (D-AE-06; BR-PE-01 to 06; BR-RF-03); `construction/authority-evaluation/nfr-design/nfr-design-patterns.md` (NP-08)

---

### TC-AE-032 — The seal: form, vector, and domain separation

**Context**: `v1.{kid}.{mac}`, HMAC-SHA-256 over a label, a zero byte, and the JCS bytes (NP-01).

**Scenario**: A fixed key and a fixed envelope.

**Preconditions**:
- A fixed 256-bit test key `k1`; a fixed envelope

**Steps**:
1. Seal the envelope
2. Compute HMAC-SHA-256 over the JCS bytes **without** the label
3. Verify the seal

**Expected outcome**: 1: equals the committed literal seal, matching `^v1\.k1\.[A-Za-z0-9_-]{43}$`. 2: differs from 1's MAC. 3: verifies; the comparison uses `timingSafeEqual` (review check).

**Scope**: happy-path · **Priority**: High  
**Source**: authority-evaluation / M1-FR-01  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/authority-evaluation/code/`  
**Technical references**: `construction/authority-evaluation/nfr-design/nfr-design-patterns.md` (NP-01)

---

### TC-AE-033 — The key ring: start-up checks and rotation

**Context**: The ring follows U2's seed-key shape, is checked at start-up, and rotates by configuration (NP-02).

**Scenario**: Ring configurations and a rotation.

**Preconditions**:
- Secrets written as base64url text of 256 random bits, loaded through P9's `SecretReader.key(secret, true)`

**Steps**:
1. Start with: a missing secret; a secret that is not base64url; a 128-bit key; a 512-bit key; `current` not among the keys; a duplicate id; an id `k.1`
2. Ring `{ current: k1, keys: [k1] }`: seal S1
3. Ring `{ current: k1, keys: [k1, k2] }`: verify S1; seal S2
4. Ring `{ current: k2, keys: [k1, k2] }`: verify S1; seal S3
5. Ring `{ current: k2, keys: [k2] }`: verify S1, S3

**Expected outcome**: 1: start-up refused in every case. 2 to 4: every verification succeeds; S2 names `k1`, S3 names `k2`. 5: S1 fails (`seal_failed`), S3 verifies.

**Scope**: edge-boundary · **Priority**: High  
**Source**: authority-evaluation / M1-FR-01  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/authority-evaluation/code/`  
**Technical references**: `construction/authority-evaluation/nfr-design/nfr-design-patterns.md` (NP-02); `construction/authority-evaluation/nfr-design/logical-components.md`

---

### TC-AE-034 — One read per request, and the cache's rules

**Context**: Agent facts are read once at the start of step 9, all or nothing, through one caching decorator (NP-04).

**Scenario**: Requests against facts, with its counter, injectable failure and delay, and the injected clock. The bound is set to 60 s for the test.

**Preconditions**:
- facts holds 31 distinct agents for a forwarded chain, and the presenter

**Steps**:
1. Refusals at steps 5, 6, 7 and 8
2. A request forwarding the 31-agent chain, cold cache
3. The same request again, 59 s later
4. Again at 60 s
5. With the clock at t, a cold read that completes at t + 10 s; then requests at t + 59 s and t + 60 s
6. A read that fails; then the same request with facts working
7. facts fails while every entry is within the bound; then after the bound
8. 20 concurrent requests for one cold agent; then 20 where that read fails
9. 4097 distinct agents read; then the least recently used again
10. A human principal's `grantedSet` during a request
11. During one request, count calls made by P11's agent `GrantSource`
12. Inspect a cache key
13. Inspect the configuration schema for any cache-lifetime setting

**Expected outcome**: 1: zero calls. 2: **one** call, for 32 agents. 3: zero calls. 4: one call. 5: at t + 59 s served; at t + 60 s re-read (the TTL runs from when the read was **issued**). 6: `unavailable` with `Retry-After: 1`, reason `agent_facts_read_failed`; then one call, admitted (nothing cached from the failure). 7: served within the bound; `unavailable` after it. 8: one call; then all 20 `unavailable`, nothing cached. 9: entry count never exceeds 4096; the evicted agent is read again. 10: goes to humans, never to facts or the cache. 11: zero (served from the request snapshot). 12: carries organization, project, environment, and agent. 13: there is none; the lifetime is the one propagation bound (NFR-AE-10).

**Scope**: edge-boundary · **Priority**: High  
**Source**: authority-evaluation / M1-FR-08  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/authority-evaluation/code/`  
**Technical references**: `construction/authority-evaluation/nfr-design/nfr-design-patterns.md` (NP-04); `construction/authority-evaluation/functional-design/business-rules.md` (BR-AU-09; BR-OR-06); `construction/authority-evaluation/nfr-requirements/nfr-requirements.md` (NFR-AE-08 to 15)

---

### TC-AE-035 — The permission model satisfies L1 to L5

**Context**: Any model must satisfy the five laws; core's flat sets do (D-AE-16; PF FR-019).

**Scenario**: Table-driven checks over a fixed collection of sets, the empty set included.

**Preconditions**:
- Sets over identifiers such as `event:publish`, `event:subscribe`, `agent:register`

**Steps**:
1. For every pair and triple: closure, associativity, commutativity, monotonicity (`A ∩ B ⊆ A`)
2. `contains(∅, R)` for non-empty `R`; `contains(A, R)` against exact membership

**Expected outcome**: Every law holds for every combination. No new dependency is used.

**Scope**: edge-boundary · **Priority**: Medium  
**Source**: authority-evaluation / M1-FR-08  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/authority-evaluation/code/`  
**Technical references**: `construction/authority-evaluation/functional-design/domain-entities.md` (*Permission Set*); `construction/authority-evaluation/functional-design/business-rules.md` (D-AE-16)

---

### TC-AE-036 — Canonical JSON, computed once, and the swap in U2

**Context**: `packages/jcs` is the one RFC 8785 implementation; U2's wrapper must stay byte-identical (NP-03).

**Scenario**: The canonicalizer alone, inside `admit`, and in U2.

**Preconditions**:
- **Committed before the swap**: literal-byte vectors for U2's log-pseudonym input (`referenceJson`, identifiers with `'`, `/`, `|`, `@`, `+`, `:`, `.`) and their pseudonyms under a fixed key; literal-byte vectors for the seed associated data; a fixture seed encrypted by U2's current code

**Steps**:
1. RFC 8785's examples, and the committed number and string vectors (including `-0`, exponents, and escapes)
2. A string with a lone surrogate
3. A spy on `canonicalize` during an `admit` that forwards an envelope
4. After the swap: U2's vectors, pseudonyms, and the fixture's decryption

**Expected outcome**: 1: byte-equal to the expected output. 2: `CanonicalizationError`. 3: exactly two calls: one for `inbound.envelope`, one for the stamped envelope. 4: every one passes **unchanged**; any difference stops Code Generation.

**Scope**: edge-boundary · **Priority**: High  
**Source**: authority-evaluation / M1-FR-01  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/authority-evaluation/code/`  
**Technical references**: `construction/authority-evaluation/nfr-design/nfr-design-patterns.md` (NP-03)

---

### TC-AE-037 — Maximum depth and `__proto__`: no crash, no prototype

**Context**: Deep nesting is handled without recursion; the copy defines own data properties (NP-07).

**Scenario**: A 1 MiB raw body, and a `__proto__` key.

**Preconditions**:
- A fixed **1 MiB raw body string** whose `inbound.envelope` holds an unknown field nested as deeply as fits

**Steps**:
1. `JSON.parse` the raw string and run `admit` with it
2. Copy an object parsed from `{"__proto__": {"polluted": true}, "a": 1}` with U3's copy
3. Compute the JCS bytes of original and copy

**Expected outcome**: 1: `invalid_inbound_context` (the bound), never a crash, `RangeError`, or stack overflow. 2: the copy's prototype is `Object.prototype`; `__proto__` is an own property; `({}).polluted` is `undefined`. 3: equal.

**Scope**: edge-boundary · **Priority**: High  
**Source**: authority-evaluation / M1-FR-01  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/authority-evaluation/code/`  
**Technical references**: `construction/authority-evaluation/nfr-design/nfr-design-patterns.md` (NP-07)

---

### TC-AE-038 — Every contract pattern finishes on its worst-case input

**Context**: Ajv runs on V8's default regex engine; every pattern is proven linear and timed against its worst case (NP-06).

**Scenario**: Every `pattern` in `contract/` (schemas and OpenAPI documents).

**Preconditions**:
- The patterns are found by walking the contract files, not listed by hand

**Steps**:
1. For each, build the worst-case input at its maximum length (its repeated unit, then a character that fails the match at the end) and match it

**Expected outcome**: Each match completes within **100 ms**. A new pattern added later is picked up automatically.

**Scope**: edge-boundary · **Priority**: Medium  
**Source**: authority-evaluation / M1-FR-01  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/authority-evaluation/code/`  
**Technical references**: `construction/authority-evaluation/nfr-design/nfr-design-patterns.md` (NP-06)

---

### TC-AE-039 — The entry point's structure: one import, no framework, refusals returned, and the log

**Context**: The entry point is the only surface import; packages are framework-free; refusals are returned and logged (D-AE-04; NP-05; NP-08).

**Scenario**: The packages and `admit`.

**Preconditions**:
- None beyond admission(E)

**Steps**:
1. Scan the imports of `packages/jcs`, `packages/envelope`, `packages/authority`, `packages/policy-decision`, `seams/policy-decision`, and every service
2. Cause one refusal at each of steps 5 to 10
3. A context(A) whose scope differs from E's configured scope; and an empty required set
4. Inspect the security log after step 2
5. Count how often the draft validator is compiled while one entry point serves 100 requests
6. Run the same 50 requests through two separately built entry points with the same inputs
7. Check `DEPENDENCIES.md` after U3's changes

**Expected outcome**: 1: none imports NestJS; no service imports `packages/envelope`; `packages/authority` imports neither P1 nor P11. 2: each refusal is **returned**, never thrown. 3: both are `internal_error` (reasons `credential_scope_mismatch`, `empty_required_set`), never an allow. 4: exactly one `envelope_refused` event per refusal, with exactly code, reason, request id, environment, agent, instance; never the body, the seal, the forwarded envelope, or trace values. 5: once, when the entry point is built (NFR-AE-03). 6: identical results, request by request: no state outside the cache behind its port (NFR-AE-22). 7: no new direct dependency; Ajv's row gains `packages/envelope` as a runtime workspace (NFR-AE-23).

**Scope**: edge-boundary · **Priority**: High  
**Source**: authority-evaluation / M1-FR-08, M1-FR-13  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/authority-evaluation/code/`  
**Technical references**: `construction/authority-evaluation/functional-design/business-rules.md` (D-AE-04, 10, 23, 26); `construction/authority-evaluation/nfr-design/nfr-design-patterns.md` (NP-05, NP-08); `construction/authority-evaluation/nfr-requirements/nfr-requirements.md` (NFR-AE-03, 22, 23)

---

### TC-AE-040 — The latency of steps 5 to 10 is measured and reported

**Context**: PF §9 places the evaluation on the per-request hot path and states no number. NFR-AE-07 sets a **target, reported, not gated**: timing gates flake in shared CI, as U2 found (TC-OI-062). The structural bounds that are gated are TC-AE-034's (one read, none before step 9) and TC-AE-039's (validator compiled once). This case **measures** and **reports**. It is **not a pass/fail gate**.

**Scenario**: At Build and Test, a tester benchmarks `admit` on the reference workstation.

**Preconditions**:
- admission(E) with a **warm** agent-facts cache, so no term read is timed (term reads are excluded by NFR-AE-07)
- A **maximum-size forwarding draft**: a sealed forwarded envelope with a **31-entry chain** (so the stamped chain has 32), padded with an unknown field so the stamped envelope is just under 16384 bytes, and a `traceContext` with a `tracestate` of 512 characters
- facts holds every agent in the chain and the presenter, all holding the required permission

**Steps**:
1. Run `admit` on that draft under `vitest bench` (P-NFR-05), long enough for a stable p99
2. Record p50, p99, and the number of samples

**Expected outcome**: **A reported measurement, recorded in the Build and Test summary**: p50 and p99 of steps 5 to 10, excluding term reads, against the **target of ≤ 2 ms p99**. It does not fail the build. A p99 over the target is investigated, and the cause recorded there.

**Scope**: edge-boundary · **Priority**: Low  
**Source**: authority-evaluation / M1-FR-01, M1-FR-08 (NFR-AE-07)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/authority-evaluation/code/`  
**Technical references**: `construction/authority-evaluation/nfr-requirements/nfr-requirements.md` (NFR-AE-06, 07; P-NFR-05)

---
