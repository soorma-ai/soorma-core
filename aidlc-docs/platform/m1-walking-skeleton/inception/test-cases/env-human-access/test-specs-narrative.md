# Test Specifications (Narrative): env-human-access

**Unit**: `env-human-access` (U4: environment credentials and grants for humans, control face)  
**Unit abbreviation**: EHA = env-human-access  
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

### TC-EHA-001 — Configuration grants the first Admin `grant:human` and `human:manage` in E

**Context**: The environment's configuration grants its first Admin `grant:human` and `human:manage`, with *granted-by* = configuration (M1-FR-14, M1-FR-12).

**Scenario**: E starts with configuration naming H as first Admin.

**Preconditions**:
- E's control-gateway is running, alongside the organization level
- Configuration naming H as E's first Admin

**Steps**:
1. Start E
2. Inspect H's grants in E

**Expected outcome**: H holds `grant:human` and `human:manage` in E, recorded with *granted-by* = configuration.

**Scope**: happy-path · **Priority**: High  
**Source**: env-human-access / M1-FR-14, M1-FR-12  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/env-human-access/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

---

### TC-EHA-002 — An environment credential is issued from a live sign-in

**Context**: E issues a credential against a live sign-in to an `active` principal holding at least one grant in E (M1-FR-20).

**Scenario**: H, holding a sign-in, requests a credential for E.

**Preconditions**:
- E's control-gateway is running, alongside the organization level
- H is `active`, holds a live sign-in, and holds a grant in E

**Steps**:
1. Call `issueEnvironmentCredential` at E, presenting the sign-in

**Expected outcome**: An environment credential bound to E is returned, with an expiry no later than the sign-in's.

**Scope**: happy-path · **Priority**: High  
**Source**: env-human-access / M1-FR-20  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/env-human-access/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

---

### TC-EHA-003 — H renews their environment credential

**Context**: The environment credential is renewable (M1-FR-20).

**Scenario**: H renews a live environment credential.

**Preconditions**:
- E's control-gateway is running, alongside the organization level
- H holds a live environment credential for E, and its sign-in is live

**Steps**:
1. Call `renewEnvironmentCredential`, presenting it

**Expected outcome**: A renewed credential for E is returned. Its authority is unchanged.

**Scope**: happy-path · **Priority**: Medium  
**Source**: env-human-access / M1-FR-20  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/env-human-access/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

---

### TC-EHA-004 — H ends their own environment credential

**Context**: Ending one's own environment credential is part of the logout (M1-FR-21).

**Scenario**: H ends a live environment credential.

**Preconditions**:
- E's control-gateway is running, alongside the organization level
- H holds a live environment credential for E

**Steps**:
1. Call `endEnvironmentCredential`, presenting it

**Expected outcome**: The end succeeds.

**Scope**: happy-path · **Priority**: High  
**Source**: env-human-access / M1-FR-21  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/env-human-access/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

---

### TC-EHA-005 — H self-grants Developer permissions, recorded as self-grants

**Context**: A holder of `grant:human` may grant themselves any accepted permission, and every self-grant is recorded (M1-FR-15).

**Scenario**: H grants themselves `agent:register`, `event:publish`, and `event:subscribe`.

**Preconditions**:
- E's control-gateway is running, alongside the organization level
- H holds `grant:human` in E and a live environment credential

**Steps**:
1. Call `grantToHuman` with target H and {`agent:register`, `event:publish`, `event:subscribe`}
2. Inspect H's grants and the attribution records

**Expected outcome**: H holds the three permissions. The grant is attributed to H with the credential presented, no origin mode, and marked as a self-grant.

**Scope**: happy-path · **Priority**: High  
**Source**: env-human-access / M1-FR-15, M1-FR-12  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/env-human-access/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

---

### TC-EHA-006 — A grant to another human succeeds

**Context**: The ceiling allows granting to any human (M1-FR-15).

**Scenario**: H grants `event:subscribe` to H2, another principal of O.

**Preconditions**:
- E's control-gateway is running, alongside the organization level
- A second principal H2 of O exists (for example, configured as E2's first Admin)
- H holds `grant:human` in E

**Steps**:
1. Call `grantToHuman` with target H2 and {`event:subscribe`}

**Expected outcome**: H2 holds `event:subscribe` in E. The grant is attributed to H and not marked as a self-grant.

**Scope**: happy-path · **Priority**: Medium  
**Source**: env-human-access / M1-FR-15  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/env-human-access/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

---

### TC-EHA-007 — Granting does not require holding the permission

**Context**: The `grant:human` ceiling never requires the Admin to hold what they grant (M1-FR-15).

**Scenario**: H, holding only the configured grants, grants `event:publish` to H2.

**Preconditions**:
- E's control-gateway is running, alongside the organization level
- H holds only `grant:human` and `human:manage` in E
- H2 exists

**Steps**:
1. Call `grantToHuman` with target H2 and {`event:publish`}

**Expected outcome**: Succeeds.

**Scope**: happy-path · **Priority**: High  
**Source**: env-human-access / M1-FR-15  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/env-human-access/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

---

### TC-EHA-008 — Human-only permissions can be granted to a human

**Context**: Any permission valid in E may be granted to a human, administrative ones included (M1-FR-15).

**Scenario**: H grants `human:manage` to H2.

**Preconditions**:
- E's control-gateway is running, alongside the organization level
- H holds `grant:human` in E
- H2 exists

**Steps**:
1. Call `grantToHuman` with target H2 and {`human:manage`}

**Expected outcome**: Succeeds.

**Scope**: edge-boundary · **Priority**: Medium  
**Source**: env-human-access / M1-FR-15  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/env-human-access/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

---

### TC-EHA-009 — The organization sign-in is refused everywhere in E except issuance

**Context**: The sign-in is refused at every environment's perimeter except that environment's credential issuance (M1-FR-19, M1-FR-09).

**Scenario**: H presents the sign-in itself to a control operation.

**Preconditions**:
- E's control-gateway is running, alongside the organization level
- H holds a live sign-in and the needed grants

**Steps**:
1. Call `grantToHuman`, presenting the sign-in instead of an environment credential

**Expected outcome**: Refused. No grant is made.

**Scope**: negative · **Priority**: High  
**Source**: env-human-access / M1-FR-09, M1-FR-19  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/env-human-access/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

---

### TC-EHA-010 — E's credential is refused in E2

**Context**: An environment credential is accepted only in the environment that issued it (O4, M1-FR-20).

**Scenario**: H presents E's credential to E2's control-gateway.

**Preconditions**:
- E and E2 running
- H holds a live environment credential for E

**Steps**:
1. Call `grantToHuman` at E2, presenting E's credential

**Expected outcome**: Refused, without disclosing anything about E2.

**Scope**: negative · **Priority**: High  
**Source**: env-human-access / M1-FR-20, M1-FR-10  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/env-human-access/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

---

### TC-EHA-011 — A principal holding no grant in E gets no credential

**Context**: Issuance requires at least one grant in E (M1-FR-20).

**Scenario**: H2, active with no grant in E, requests a credential for E.

**Preconditions**:
- E's control-gateway is running, alongside the organization level
- H2 is `active`, holds a live sign-in, and holds no grant in E

**Steps**:
1. Call `issueEnvironmentCredential` at E, presenting H2's sign-in

**Expected outcome**: Refused.

**Scope**: negative · **Priority**: High  
**Source**: env-human-access / M1-FR-20  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/env-human-access/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

---

### TC-EHA-012 — Granting without `grant:human` is denied

**Context**: Granting to a human needs `grant:human` in E (M1-FR-15).

**Scenario**: H2, holding an environment credential for E but not `grant:human`, tries to grant.

**Preconditions**:
- E's control-gateway is running, alongside the organization level
- H2 holds a credential for E and only `event:subscribe`

**Steps**:
1. Call `grantToHuman` with target H2 and {`agent:register`}

**Expected outcome**: Denied.

**Scope**: negative · **Priority**: High  
**Source**: env-human-access / M1-FR-15, M1-FR-08  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/env-human-access/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

---

### TC-EHA-013 — A permission identifier that is not plane-declared is rejected

**Context**: Only plane-declared identifiers are accepted. This is a recorded delivery limit (M1-FR-15, the GAP-INT-006 work-around).

**Scenario**: H grants an identifier no plane PRD declares.

**Preconditions**:
- E's control-gateway is running, alongside the organization level
- H holds `grant:human` in E

**Steps**:
1. Call `grantToHuman` with target H and {`invoice:approve`}

**Expected outcome**: Rejected, naming the identifier. No grant is made.

**Scope**: negative · **Priority**: High  
**Source**: env-human-access / M1-FR-15 (GAP-INT-006)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/env-human-access/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

---

### TC-EHA-014 — An ended environment credential is refused on the next request

**Context**: An ended credential is refused thereafter (O3; M1-FR-21).

**Scenario**: H ends a credential and then uses it.

**Preconditions**:
- E's control-gateway is running, alongside the organization level
- H holds a live environment credential for E

**Steps**:
1. Call `endEnvironmentCredential`
2. Call `grantToHuman`, presenting the same credential

**Expected outcome**: The second call is refused.

**Scope**: negative · **Priority**: High  
**Source**: env-human-access / M1-FR-21, M1-FR-07  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/env-human-access/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

---

### TC-EHA-015 — An agent credential is refused at the control gateway

**Context**: No control operation accepts an agent credential in M1 (M1-FR-09). Agent-initiated control operations are absent.

**Scenario**: An instance of A presents its agent credential to a control operation.

**Preconditions**:
- E's control-gateway is running, alongside the organization level
- A holds an agent credential for E

**Steps**:
1. Call `grantToHuman`, presenting A's agent credential

**Expected outcome**: Refused.

**Scope**: negative · **Priority**: High  
**Source**: env-human-access / M1-FR-09  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/env-human-access/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

---

### TC-EHA-016 — An agent credential presented beside a human credential is refused

**Context**: An agent credential presented beside a human's credential is refused (M1-FR-09).

**Scenario**: A request carries both H's environment credential and A's agent credential.

**Preconditions**:
- E's control-gateway is running, alongside the organization level

**Steps**:
1. Call `grantToHuman`, presenting both credentials

**Expected outcome**: Refused.

**Scope**: negative · **Priority**: High  
**Source**: env-human-access / M1-FR-09  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/env-human-access/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

---

### TC-EHA-017 — An expired environment credential is refused, and cannot be renewed

**Context**: The credential is short-lived (M1-FR-20).

**Scenario**: H uses and renews a credential after its expiry.

**Preconditions**:
- E's control-gateway is running, alongside the organization level
- H's environment credential has expired

**Steps**:
1. Call `grantToHuman` with it
2. Call `renewEnvironmentCredential` with it

**Expected outcome**: Both are refused.

**Scope**: negative · **Priority**: Medium  
**Source**: env-human-access / M1-FR-20  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/env-human-access/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

---

### TC-EHA-018 — A grant to a non-existent principal is rejected

**Context**: A grant names a human principal of the organization (M1-FR-15).

**Scenario**: H grants to an identifier that is not a principal of O.

**Preconditions**:
- E's control-gateway is running, alongside the organization level
- H holds `grant:human`

**Steps**:
1. Call `grantToHuman` with an unknown target and {`event:publish`}

**Expected outcome**: Rejected, and no grant is recorded.

**Scope**: negative · **Priority**: Medium  
**Source**: env-human-access / M1-FR-15  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/env-human-access/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

---

### TC-EHA-019 — An environment credential never outlives its sign-in

**Context**: Renewal never outlives the sign-in (M1-FR-20).

**Scenario**: H holds a credential issued from a sign-in that is about to expire.

**Preconditions**:
- E's control-gateway is running, alongside the organization level
- H holds a credential for E whose sign-in expires before the credential's natural lifetime would

**Steps**:
1. Read the credential's expiry
2. After the sign-in expires, try `renewEnvironmentCredential`

**Expected outcome**: The expiry is no later than the sign-in's, and renewal after the sign-in expires is refused.

**Scope**: edge-boundary · **Priority**: High  
**Source**: env-human-access / M1-FR-20  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/env-human-access/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

---

### TC-EHA-020 — Renewal after the sign-in has ended is refused

**Context**: Renewal never outlives the sign-in it came from (M1-FR-20). Ending the sign-in is the logout.

**Scenario**: H ends their sign-in, then tries to renew an environment credential issued from it.

**Preconditions**:
- E's control-gateway is running, alongside the organization level
- H holds a live credential for E, issued from a live sign-in

**Steps**:
1. End the sign-in at the organization level
2. Call `renewEnvironmentCredential` at E

**Expected outcome**: Refused.

**Scope**: edge-boundary · **Priority**: High  
**Source**: env-human-access / M1-FR-20, M1-FR-21  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/env-human-access/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

---

### TC-EHA-021 — A direct human operation carries no envelope, and is attributed to the human

**Context**: A direct human operation carries no envelope, and its attribution names the human and the credential presented, with no origin mode (M1-FR-12).

**Scenario**: H makes a grant, sending no envelope.

**Preconditions**:
- E's control-gateway is running, alongside the organization level
- H holds `grant:human` and a credential for E

**Steps**:
1. Call `grantToHuman` with no envelope
2. Inspect the attribution record

**Expected outcome**: The grant succeeds. The record names H and the credential, with scope E and no origin mode or chain.

**Scope**: edge-boundary · **Priority**: Medium  
**Source**: env-human-access / M1-FR-12, M1-FR-09  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/env-human-access/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

---

### TC-EHA-022 — E holds only verify-only material for the organization sign-in

**Context**: Environments hold verify-only material for the organization sign-in, never material that can mint (M1-FR-10).

**Scenario**: A reviewer inspects E's sign-in material, and tries to have E mint a sign-in.

**Preconditions**:
- E's control-gateway is running, alongside the organization level

**Steps**:
1. Inspect the sign-in material in E's store and configuration
2. Look for any E operation that issues a sign-in

**Expected outcome**: E holds only verification material, and no E operation issues a sign-in.

**Scope**: edge-boundary · **Priority**: High  
**Source**: env-human-access / M1-FR-10  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/env-human-access/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

---

### TC-EHA-023 — If revocation state cannot be read, a control request is refused

**Context**: The revocation read fails closed past the bound (M1-FR-07). That applies to human credentials at the control face too.

**Scenario**: E's revocation state is unreachable for longer than the bound.

**Preconditions**:
- E's control-gateway is running, alongside the organization level
- H holds a live credential for E
- E's revocation state is made unreachable for longer than the bound

**Steps**:
1. Call `grantToHuman`, presenting the credential

**Expected outcome**: Refused.

**Scope**: edge-boundary · **Priority**: High  
**Source**: env-human-access / M1-FR-07  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/env-human-access/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

---

### TC-EHA-024 — This unit's operations are defined in the contract and validated against it

**Context**: Each surface unit adds its own operations to the wire contract (unit-of-work.md, Q1 B). A raw caller that never links the SDK reaches identical enforcement (M1-FR-02).

**Scenario**: A reviewer checks the unit's operations in `contract/control-gateway.openapi.yaml`, then sends a request that violates the schema.

**Preconditions**:
- `contract/control-gateway.openapi.yaml` after this unit's Code Generation

**Steps**:
1. List the operations in `contract/control-gateway.openapi.yaml` and compare them with this unit's operations: `issueEnvironmentCredential`, `renewEnvironmentCredential`, `endEnvironmentCredential`, `grantToHuman`
2. Check that each references the shared conventions (versioning, error model, security schemes)
3. Send one request with a body that violates its operation's schema

**Expected outcome**: Every one of the unit's operations is present and references the conventions. The violating request is rejected with the contract's error model before any processing.

**Scope**: happy-path · **Priority**: High  
**Source**: env-human-access / M1-FR-02  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/env-human-access/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

---
