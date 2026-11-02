# Test Specifications (Narrative): authority-evaluation

**Unit**: `authority-evaluation` (U3: authority evaluation and the envelope, data face)  
**Unit abbreviation**: AE = authority-evaluation  
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

### TC-AE-001 — A valid draft is stamped with all six platform fields

**Context**: The perimeter writes the six platform-stamped fields (M1-FR-01). It is the core of what the envelope proves.

**Scenario**: A valid draft from an instance of A in E is stamped.

**Preconditions**:
- The authority and envelope modules are exercised directly, at the evaluation level, with constructed inputs (unit-of-work.md: U3 has no edge surface)
- A draft with a client contract version and a well-formed trace context
- A registered with autonomy declared, in E

**Steps**:
1. Validate the draft
2. Stamp it with A's checked context

**Expected outcome**: The envelope carries envelope version, scope E, origin `autonomous`, actor chain `[A's instance]`, and the trace context as asserted. There is no delegating principal and no re-broadening record.

**Scope**: happy-path · **Priority**: High  
**Source**: authority-evaluation / M1-FR-01  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/authority-evaluation/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

---

### TC-AE-002 — Autonomous origin is stamped for a declaring agent with no inbound context

**Context**: With no inbound context, an agent that declared autonomy acts `autonomous` (M1-FR-08). Every M1 chain starts this way.

**Scenario**: A, autonomy declared, acts with no forwarded context.

**Preconditions**:
- The authority and envelope modules are exercised directly, at the evaluation level, with constructed inputs (unit-of-work.md: U3 has no edge surface)
- A registered with autonomy declared

**Steps**:
1. Resolve origin for A with no inbound envelope

**Expected outcome**: Origin is `autonomous`, derived from A's registration.

**Scope**: happy-path · **Priority**: High  
**Source**: authority-evaluation / M1-FR-08  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/authority-evaluation/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

---

### TC-AE-003 — Origin propagates unchanged from an inbound envelope, and the chain grows

**Context**: An event-triggered hop propagates origin unchanged, and the chain grows (M1-FR-08).

**Scenario**: B, triggered by A's envelope, acts while forwarding it.

**Preconditions**:
- The authority and envelope modules are exercised directly, at the evaluation level, with constructed inputs (unit-of-work.md: U3 has no edge surface)
- An envelope stamped for A: `autonomous`, chain `[A]`

**Steps**:
1. Resolve origin for B with A's envelope forwarded
2. Stamp B's draft

**Expected outcome**: Origin is `autonomous`, unchanged, and the chain is `[A, B]`.

**Scope**: happy-path · **Priority**: High  
**Source**: authority-evaluation / M1-FR-08, M1-FR-01  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/authority-evaluation/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

---

### TC-AE-004 — Authority is allowed when every term holds the permission

**Context**: Effective authority is the intersection across the chain (M1-FR-08).

**Scenario**: B, forwarding A's context, needs `event:publish`, and both hold it.

**Preconditions**:
- The authority and envelope modules are exercised directly, at the evaluation level, with constructed inputs (unit-of-work.md: U3 has no edge surface)
- A's and B's standing sets both include `event:publish`

**Steps**:
1. Evaluate B's request for `event:publish` with chain terms [A]

**Expected outcome**: Allowed, without re-broadening.

**Scope**: happy-path · **Priority**: High  
**Source**: authority-evaluation / M1-FR-08  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/authority-evaluation/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

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

**Expected outcome**: Allowed, by re-broadening. The envelope carries a re-broadening record naming B's hop.

**Scope**: happy-path · **Priority**: High  
**Source**: authority-evaluation / M1-FR-08, M1-FR-01  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/authority-evaluation/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

---

### TC-AE-006 — The policy-decision boundary answers containment only

**Context**: The policy-decision seam decides containment, never composition (M1-FR-13).

**Scenario**: The policy-decision boundary is asked whether a permission is contained in a set.

**Preconditions**:
- The authority and envelope modules are exercised directly, at the evaluation level, with constructed inputs (unit-of-work.md: U3 has no edge surface)

**Steps**:
1. Ask whether `event:publish` is contained in {`event:publish`}
2. Ask whether `event:publish` is contained in {}

**Expected outcome**: Contained, and not contained, respectively. The interface offers no operation that returns an effective set.

**Scope**: happy-path · **Priority**: Medium  
**Source**: authority-evaluation / M1-FR-13  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/authority-evaluation/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

---

### TC-AE-007 — A well-formed trace context is accepted and carried as asserted

**Context**: Trace context is required, and is validated for well-formedness only, against W3C Trace Context (M1-FR-01).

**Scenario**: A draft carries a valid `traceparent` and `tracestate`.

**Preconditions**:
- The authority and envelope modules are exercised directly, at the evaluation level, with constructed inputs (unit-of-work.md: U3 has no edge surface)

**Steps**:
1. Validate a draft with a well-formed `traceparent` and `tracestate`
2. Stamp it

**Expected outcome**: Accepted. Both values appear in the envelope unchanged.

**Scope**: happy-path · **Priority**: Medium  
**Source**: authority-evaluation / M1-FR-01  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/authority-evaluation/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

---

### TC-AE-008 — Unknown fields are preserved, and unknown enumerated values are non-fatal

**Context**: Unknown fields are preserved and forwarded, and unknown enumerated values are non-fatal (M1-FR-01).

**Scenario**: A forwarded inbound envelope carries an unknown field and an unknown enumerated value in an extension field.

**Preconditions**:
- The authority and envelope modules are exercised directly, at the evaluation level, with constructed inputs (unit-of-work.md: U3 has no edge surface)
- An inbound envelope with an extra field `x-future`

**Steps**:
1. Validate and stamp a draft forwarding that envelope

**Expected outcome**: Processing succeeds, and `x-future` is present in the resulting envelope.

**Scope**: happy-path · **Priority**: Medium  
**Source**: authority-evaluation / M1-FR-01  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/authority-evaluation/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

---

### TC-AE-009 — A draft setting any platform-stamped field is rejected

**Context**: A draft that sets a platform-stamped field is rejected, never overwritten (M1-FR-01). It is *done when* 7's mechanism.

**Scenario**: Six drafts each set one platform-stamped field.

**Preconditions**:
- The authority and envelope modules are exercised directly, at the evaluation level, with constructed inputs (unit-of-work.md: U3 has no edge surface)

**Steps**:
1. For each of envelope version, scope, origin mode, delegating principal, actor chain, and re-broadening record, validate a draft that sets it

**Expected outcome**: All six are rejected, each naming the field. None is stamped.

**Scope**: negative · **Priority**: High  
**Source**: authority-evaluation / M1-FR-01  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/authority-evaluation/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

---

### TC-AE-010 — A draft asserting origin `autonomous` is rejected

**Context**: Origin is stamped by the perimeter on every hop, and a draft setting origin mode is rejected (M1-FR-01, the GAP-INT-007 work-around). This holds even at an autonomous first hop.

**Scenario**: A, autonomy declared, sends a draft asserting `autonomous`.

**Preconditions**:
- The authority and envelope modules are exercised directly, at the evaluation level, with constructed inputs (unit-of-work.md: U3 has no edge surface)
- A registered with autonomy declared

**Steps**:
1. Validate A's draft containing origin mode `autonomous`

**Expected outcome**: Rejected, although the asserted value matches what the perimeter would stamp.

**Scope**: negative · **Priority**: High  
**Source**: authority-evaluation / M1-FR-01 (GAP-INT-007)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/authority-evaluation/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

---

### TC-AE-011 — With no inbound context and no declared autonomy, the agent is denied

**Context**: With no inbound context, an agent that did not declare autonomy is denied (O12, M1-FR-08). Otherwise silence would widen authority.

**Scenario**: An agent C without declared autonomy acts with no forwarded context.

**Preconditions**:
- The authority and envelope modules are exercised directly, at the evaluation level, with constructed inputs (unit-of-work.md: U3 has no edge surface)
- C registered with autonomy not declared

**Steps**:
1. Resolve origin for C with no inbound envelope

**Expected outcome**: Denied (O12). No envelope is stamped.

**Scope**: negative · **Priority**: High  
**Source**: authority-evaluation / M1-FR-08  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/authority-evaluation/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

---

### TC-AE-012 — A malformed trace context is rejected

**Context**: Trace context must be well-formed against W3C Trace Context (M1-FR-01).

**Scenario**: A draft carries an invalid `traceparent`.

**Preconditions**:
- The authority and envelope modules are exercised directly, at the evaluation level, with constructed inputs (unit-of-work.md: U3 has no edge surface)

**Steps**:
1. Validate a draft whose `traceparent` has the wrong length or version

**Expected outcome**: Rejected, naming trace context.

**Scope**: negative · **Priority**: Medium  
**Source**: authority-evaluation / M1-FR-01  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/authority-evaluation/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

---

### TC-AE-013 — A draft without a client contract version is rejected

**Context**: A draft declares its client contract version (M1-FR-01).

**Scenario**: A draft omits the client contract version.

**Preconditions**:
- The authority and envelope modules are exercised directly, at the evaluation level, with constructed inputs (unit-of-work.md: U3 has no edge surface)

**Steps**:
1. Validate a draft with no client contract version

**Expected outcome**: Rejected.

**Scope**: negative · **Priority**: Medium  
**Source**: authority-evaluation / M1-FR-01  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/authority-evaluation/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

---

### TC-AE-014 — An agent-set re-broadening record is rejected

**Context**: Re-broadening is declared at registration and recorded by the perimeter, never requested (M1-FR-08).

**Scenario**: B's draft includes a re-broadening record.

**Preconditions**:
- The authority and envelope modules are exercised directly, at the evaluation level, with constructed inputs (unit-of-work.md: U3 has no edge surface)

**Steps**:
1. Validate B's draft that sets a re-broadening record

**Expected outcome**: Rejected.

**Scope**: negative · **Priority**: High  
**Source**: authority-evaluation / M1-FR-08  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/authority-evaluation/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

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

**Expected outcome**: Denied. No re-broadening record.

**Scope**: negative · **Priority**: High  
**Source**: authority-evaluation / M1-FR-08  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/authority-evaluation/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

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

**Expected outcome**: Denied, and no re-broadening record.

**Scope**: edge-boundary · **Priority**: High  
**Source**: authority-evaluation / M1-FR-08  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/authority-evaluation/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

---

### TC-AE-017 — The chain at maxChainDepth is accepted; one more hop is rejected

**Context**: `maxChainDepth` is enforced (M1-FR-01). Its value is fixed at U3's Functional Design.

**Scenario**: Forwarded envelopes with chains of length `maxChainDepth − 1` and `maxChainDepth`.

**Preconditions**:
- The authority and envelope modules are exercised directly, at the evaluation level, with constructed inputs (unit-of-work.md: U3 has no edge surface)
- `maxChainDepth` from U3's Functional Design

**Steps**:
1. Stamp a draft forwarding a chain of length `maxChainDepth − 1`
2. Stamp a draft forwarding a chain of length `maxChainDepth`

**Expected outcome**: The first produces a chain of length `maxChainDepth`. The second is rejected.

**Scope**: edge-boundary · **Priority**: High  
**Source**: authority-evaluation / M1-FR-01  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/authority-evaluation/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

---

### TC-AE-018 — Re-broadening is local to its hop

**Context**: Later hops intersect against the chain as though the declaring hop had not re-broadened (M1-FR-08).

**Scenario**: After B re-broadens for `event:subscribe`, agent D, triggered by B, needs `event:subscribe`. D holds it but did not declare it.

**Preconditions**:
- The authority and envelope modules are exercised directly, at the evaluation level, with constructed inputs (unit-of-work.md: U3 has no edge surface)
- A chain [A, B] with B's re-broadening record
- D holds `event:subscribe`, with an empty declaration

**Steps**:
1. Evaluate D's request for `event:subscribe` with chain terms [A, B]

**Expected outcome**: Denied, because A's term still lacks it. B's re-broadening is not inherited.

**Scope**: edge-boundary · **Priority**: High  
**Source**: authority-evaluation / M1-FR-08  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/authority-evaluation/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

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

**Expected outcome**: Allowed, and the envelope has no re-broadening record.

**Scope**: edge-boundary · **Priority**: Medium  
**Source**: authority-evaluation / M1-FR-01, M1-FR-08  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/authority-evaluation/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

---

### TC-AE-020 — A permission outside the standing set is always denied

**Context**: Outside the declaring agent's standing set, every row of the case table denies (M1-FR-08).

**Scenario**: B requests a permission it does not hold.

**Preconditions**:
- The authority and envelope modules are exercised directly, at the evaluation level, with constructed inputs (unit-of-work.md: U3 has no edge surface)
- B's standing set excludes `attribution:read`

**Steps**:
1. Evaluate B's request for `attribution:read` with no chain

**Expected outcome**: Denied.

**Scope**: edge-boundary · **Priority**: High  
**Source**: authority-evaluation / M1-FR-08  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/authority-evaluation/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

---

### TC-AE-021 — Evaluation is deny-by-default for an empty or unknown set

**Context**: The minimal model denies by default (M1-FR-08).

**Scenario**: An agent with an empty standing set requests anything.

**Preconditions**:
- The authority and envelope modules are exercised directly, at the evaluation level, with constructed inputs (unit-of-work.md: U3 has no edge surface)
- An agent with an empty standing set

**Steps**:
1. Evaluate a request for `event:publish`

**Expected outcome**: Denied.

**Scope**: edge-boundary · **Priority**: Medium  
**Source**: authority-evaluation / M1-FR-08  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/authority-evaluation/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

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

**Expected outcome**: The outcomes, in order, are: allow with no record; allow with a record; deny; deny.

**Scope**: edge-boundary · **Priority**: High  
**Source**: authority-evaluation / M1-FR-08  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/authority-evaluation/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

---
