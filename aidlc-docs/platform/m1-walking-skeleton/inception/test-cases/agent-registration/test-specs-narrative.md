# Test Specifications (Narrative): agent-registration

**Unit**: `agent-registration` (U5: logical agent registration and registration secrets, control face)  
**Unit abbreviation**: AR = agent-registration  
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

### TC-AR-001 — A logical agent is registered with all eight attributes, sponsored by H

**Context**: A registration carries all eight PF §7a attributes, and its sponsor reference names the registering human (M1-FR-03).

**Scenario**: H registers agent A with standing set {`event:publish`} and autonomy declared.

**Preconditions**:
- E's control-gateway is running. H holds a live credential for E and has self-granted `agent:register`, `event:publish` and `event:subscribe`

**Steps**:
1. Call `registerAgent` with standing set {`event:publish`}, an empty re-broadening declaration, and autonomy declared
2. Read the registration back

**Expected outcome**: The registration has: an identifier unique in E; environment E; sponsor H; a ceiling snapshot; standing set {`event:publish`}; an empty re-broadening declaration; autonomy declared; and a registration timestamp. Its state is `registered`.

**Scope**: happy-path · **Priority**: High  
**Source**: agent-registration / M1-FR-03  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-registration/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

---

### TC-AR-002 — The ceiling snapshot records the sponsor's held set

**Context**: The snapshot records what the sponsor held at the moment of granting (M1-FR-03).

**Scenario**: A reviewer inspects A's snapshot.

**Preconditions**:
- E's control-gateway is running. H holds a live credential for E and has self-granted `agent:register`, `event:publish` and `event:subscribe`
- A registered by H

**Steps**:
1. Read A's ceiling snapshot
2. Read H's grants in E at the registration time

**Expected outcome**: The snapshot equals H's held set at that moment, human-only permissions included.

**Scope**: happy-path · **Priority**: High  
**Source**: agent-registration / M1-FR-03  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-registration/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

---

### TC-AR-003 — Autonomy declared defaults to no

**Context**: The *autonomy declared* attribute is a boolean, default no (M1-FR-03).

**Scenario**: H registers an agent without stating autonomy.

**Preconditions**:
- E's control-gateway is running. H holds a live credential for E and has self-granted `agent:register`, `event:publish` and `event:subscribe`

**Steps**:
1. Call `registerAgent` with a standing set and no autonomy value
2. Read the registration

**Expected outcome**: Autonomy declared is no.

**Scope**: happy-path · **Priority**: Medium  
**Source**: agent-registration / M1-FR-03  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-registration/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

---

### TC-AR-004 — A re-broadening declaration within the standing set is accepted

**Context**: A declaration is a permission set within the standing set (M1-FR-03).

**Scenario**: H registers B with standing set {`event:subscribe`, `event:publish`}, declaring {`event:subscribe`}.

**Preconditions**:
- E's control-gateway is running. H holds a live credential for E and has self-granted `agent:register`, `event:publish` and `event:subscribe`

**Steps**:
1. Call `registerAgent` with that standing set and declaration

**Expected outcome**: Accepted. The registration records the declaration.

**Scope**: happy-path · **Priority**: High  
**Source**: agent-registration / M1-FR-03  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-registration/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

---

### TC-AR-005 — An empty re-broadening declaration is accepted

**Context**: The declaration may be empty (M1-FR-03).

**Scenario**: H registers an agent with an empty declaration.

**Preconditions**:
- E's control-gateway is running. H holds a live credential for E and has self-granted `agent:register`, `event:publish` and `event:subscribe`

**Steps**:
1. Call `registerAgent` with an empty declaration

**Expected outcome**: Accepted.

**Scope**: happy-path · **Priority**: Medium  
**Source**: agent-registration / M1-FR-03  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-registration/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

---

### TC-AR-006 — A registration secret is issued, with its issuer recorded

**Context**: Issuance records the issuer: the human who issued it (M1-FR-04).

**Scenario**: H issues a secret for A.

**Preconditions**:
- E's control-gateway is running. H holds a live credential for E and has self-granted `agent:register`, `event:publish` and `event:subscribe`
- A registered by H

**Steps**:
1. Call `issueRegistrationSecret` for A
2. Inspect the secret's record

**Expected outcome**: A secret is returned once. Its record names A and issuer H, and holds only verification material, never the secret itself.

**Scope**: happy-path · **Priority**: High  
**Source**: agent-registration / M1-FR-04  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-registration/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

---

### TC-AR-007 — Registration and issuance are attributed to H

**Context**: Every platform-resource operation is attributed. A direct human operation is attributed to the human, with no origin mode (M1-FR-12).

**Scenario**: A reviewer inspects attribution after registration and issuance.

**Preconditions**:
- E's control-gateway is running. H holds a live credential for E and has self-granted `agent:register`, `event:publish` and `event:subscribe`
- A registered, and a secret issued

**Steps**:
1. Read the attribution records for both operations

**Expected outcome**: Both name H and the credential presented, with scope E and no origin mode or chain.

**Scope**: happy-path · **Priority**: Medium  
**Source**: agent-registration / M1-FR-12  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-registration/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

---

### TC-AR-008 — Two agents are registered, each with its own sponsor and snapshot

**Context**: *Done when* 1: two logical agents in one environment, each with its own sponsor reference and ceiling snapshot (M1-FR-03).

**Scenario**: H registers A and B in E with raw calls.

**Preconditions**:
- E's control-gateway is running. H holds a live credential for E and has self-granted `agent:register`, `event:publish` and `event:subscribe`

**Steps**:
1. Register A with {`event:publish`}, autonomy declared
2. Register B with {`event:subscribe`}, autonomy declared
3. Read both registrations

**Expected outcome**: Two distinct registrations in E, each sponsored by H, each with its own snapshot.

**Scope**: happy-path · **Priority**: High  
**Source**: agent-registration / M1-FR-03  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-registration/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

---

### TC-AR-009 — A standing set exceeding what the sponsor holds is rejected

**Context**: The standing set must lie within the sponsor's held set (M1-FR-03).

**Scenario**: H registers an agent with `attribution:read`, which H does not hold.

**Preconditions**:
- E's control-gateway is running. H holds a live credential for E and has self-granted `agent:register`, `event:publish` and `event:subscribe`
- H does not hold `attribution:read`

**Steps**:
1. Call `registerAgent` with standing set {`attribution:read`}

**Expected outcome**: Rejected, citing the ceiling. No registration is created.

**Scope**: negative · **Priority**: High  
**Source**: agent-registration / M1-FR-03  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-registration/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

---

### TC-AR-010 — A standing set containing `grant:human` is rejected, although H holds it

**Context**: A standing set containing a human-only permission is rejected, whatever the sponsor holds (M1-FR-03).

**Scenario**: H, holding `grant:human`, puts it in an agent's standing set.

**Preconditions**:
- E's control-gateway is running. H holds a live credential for E and has self-granted `agent:register`, `event:publish` and `event:subscribe`

**Steps**:
1. Call `registerAgent` with standing set {`grant:human`}

**Expected outcome**: Rejected.

**Scope**: negative · **Priority**: High  
**Source**: agent-registration / M1-FR-03  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-registration/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

---

### TC-AR-011 — Standing sets containing `human:manage` or `agent:delegate` are rejected

**Context**: `human:manage` and `agent:delegate` are human-only too (M1-FR-03).

**Scenario**: H tries two registrations, each with one human-only permission.

**Preconditions**:
- E's control-gateway is running. H holds a live credential for E and has self-granted `agent:register`, `event:publish` and `event:subscribe`
- H holds `human:manage`, and has also self-granted `agent:delegate`

**Steps**:
1. Register with {`human:manage`}
2. Register with {`agent:delegate`}

**Expected outcome**: Both are rejected.

**Scope**: negative · **Priority**: High  
**Source**: agent-registration / M1-FR-03  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-registration/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

---

### TC-AR-012 — A declaration exceeding the standing set is rejected

**Context**: A registration declaring re-broadening beyond its standing set is rejected (M1-FR-03).

**Scenario**: H declares `event:subscribe` on an agent whose standing set is {`event:publish`}.

**Preconditions**:
- E's control-gateway is running. H holds a live credential for E and has self-granted `agent:register`, `event:publish` and `event:subscribe`

**Steps**:
1. Call `registerAgent` with standing set {`event:publish`} and declaration {`event:subscribe`}

**Expected outcome**: Rejected.

**Scope**: negative · **Priority**: High  
**Source**: agent-registration / M1-FR-03  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-registration/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

---

### TC-AR-013 — A standing set with a non-plane-declared identifier is rejected

**Context**: Accepted identifiers are limited to the plane-declared set (GAP-INT-006 work-around), in standing sets as in grants (M1-FR-15).

**Scenario**: H registers an agent with an unknown identifier.

**Preconditions**:
- E's control-gateway is running. H holds a live credential for E and has self-granted `agent:register`, `event:publish` and `event:subscribe`

**Steps**:
1. Call `registerAgent` with standing set {`invoice:approve`}

**Expected outcome**: Rejected, naming the identifier.

**Scope**: negative · **Priority**: High  
**Source**: agent-registration / M1-FR-15, M1-FR-03  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-registration/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

---

### TC-AR-014 — Registration without `agent:register` is denied

**Context**: Registering requires `agent:register` in E (M1-FR-08).

**Scenario**: H2, holding a credential for E but not `agent:register`, tries to register.

**Preconditions**:
- H2 holds a credential for E and no `agent:register`

**Steps**:
1. Call `registerAgent` as H2

**Expected outcome**: Denied.

**Scope**: negative · **Priority**: High  
**Source**: agent-registration / M1-FR-08  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-registration/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

---

### TC-AR-015 — Secret issuance without `agent:register` is denied

**Context**: Issuance requires `agent:register` (M1-FR-04).

**Scenario**: H2, without `agent:register`, tries to issue a secret for A.

**Preconditions**:
- A registered by H
- H2 holds a credential for E and no `agent:register`

**Steps**:
1. Call `issueRegistrationSecret` for A as H2

**Expected outcome**: Denied.

**Scope**: negative · **Priority**: High  
**Source**: agent-registration / M1-FR-04  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-registration/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

---

### TC-AR-016 — Registration by an agent is refused

**Context**: Registration and secret issuance by an agent are absent from M1, a delivery decision (M1-FR-03).

**Scenario**: An instance of A, holding `agent:register` in its standing set, tries to register an agent.

**Preconditions**:
- E's control-gateway is running. H holds a live credential for E and has self-granted `agent:register`, `event:publish` and `event:subscribe`
- A is registered with `agent:register` in its standing set and holds an agent credential

**Steps**:
1. Call `registerAgent`, presenting A's agent credential

**Expected outcome**: Refused. No registration is created.

**Scope**: negative · **Priority**: High  
**Source**: agent-registration / M1-FR-03  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-registration/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

---

### TC-AR-017 — A secret for an unknown registration is rejected

**Context**: A secret is bound to one registration in E (M1-FR-04).

**Scenario**: H issues a secret for a registration reference that does not exist in E.

**Preconditions**:
- E's control-gateway is running. H holds a live credential for E and has self-granted `agent:register`, `event:publish` and `event:subscribe`

**Steps**:
1. Call `issueRegistrationSecret` with an unknown reference

**Expected outcome**: Rejected.

**Scope**: negative · **Priority**: Medium  
**Source**: agent-registration / M1-FR-04  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-registration/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

---

### TC-AR-018 — A standing set equal to the held set is accepted

**Context**: Boundary of the ceiling: subset includes equality (M1-FR-03).

**Scenario**: H registers an agent with exactly H's non-human-only held permissions.

**Preconditions**:
- E's control-gateway is running. H holds a live credential for E and has self-granted `agent:register`, `event:publish` and `event:subscribe`

**Steps**:
1. Call `registerAgent` with {`agent:register`, `event:publish`, `event:subscribe`}

**Expected outcome**: Accepted.

**Scope**: edge-boundary · **Priority**: Medium  
**Source**: agent-registration / M1-FR-03  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-registration/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

---

### TC-AR-019 — The snapshot is unaffected by later grants to the sponsor

**Context**: The ceiling is checked once at registration, and the snapshot records that moment. The sponsor's live permissions are never consulted again (M1-FR-03).

**Scenario**: H gains a permission after registering A.

**Preconditions**:
- E's control-gateway is running. H holds a live credential for E and has self-granted `agent:register`, `event:publish` and `event:subscribe`
- A registered by H

**Steps**:
1. Read A's snapshot
2. Grant H `attribution:read`
3. Read A's snapshot again

**Expected outcome**: The snapshot is unchanged.

**Scope**: edge-boundary · **Priority**: High  
**Source**: agent-registration / M1-FR-03  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-registration/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

---

### TC-AR-020 — A secret is returned only once

**Context**: Secret verification material is internal (M1-FR-04). The secret itself is never retrievable after issuance.

**Scenario**: A reviewer looks for a way to read A's secret back.

**Preconditions**:
- E's control-gateway is running. H holds a live credential for E and has self-granted `agent:register`, `event:publish` and `event:subscribe`
- A secret issued for A

**Steps**:
1. Inspect every operation in `control-gateway.openapi.yaml` for one that returns an existing secret

**Expected outcome**: None exists. The secret appeared only in the issuance response.

**Scope**: edge-boundary · **Priority**: High  
**Source**: agent-registration / M1-FR-04  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-registration/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

---

### TC-AR-021 — An unresolvable sponsor held set rejects the registration

**Context**: If the sponsor's held set cannot be resolved, registration is rejected; refusing is the only truthful answer (M1-FR-03).

**Scenario**: The grant store is unreachable while H registers an agent.

**Preconditions**:
- E's control-gateway is running. H holds a live credential for E and has self-granted `agent:register`, `event:publish` and `event:subscribe`
- E's grant records are made unavailable

**Steps**:
1. Call `registerAgent`

**Expected outcome**: Rejected. No registration is created.

**Scope**: edge-boundary · **Priority**: Medium  
**Source**: agent-registration / M1-FR-03  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-registration/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

---

### TC-AR-022 — This unit's operations are defined in the contract and validated against it

**Context**: Each surface unit adds its own operations to the wire contract (unit-of-work.md, Q1 B). A raw caller that never links the SDK reaches identical enforcement (M1-FR-02).

**Scenario**: A reviewer checks the unit's operations in `contract/control-gateway.openapi.yaml`, then sends a request that violates the schema.

**Preconditions**:
- `contract/control-gateway.openapi.yaml` after this unit's Code Generation

**Steps**:
1. List the operations in `contract/control-gateway.openapi.yaml` and compare them with this unit's operations: `registerAgent`, `issueRegistrationSecret`
2. Check that each references the shared conventions (versioning, error model, security schemes)
3. Send one request with a body that violates its operation's schema

**Expected outcome**: Every one of the unit's operations is present and references the conventions. The violating request is rejected with the contract's error model before any processing.

**Scope**: happy-path · **Priority**: High  
**Source**: agent-registration / M1-FR-02  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-registration/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

---
