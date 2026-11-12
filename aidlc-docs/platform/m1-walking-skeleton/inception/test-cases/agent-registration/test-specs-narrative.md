# Test Specifications (Narrative): agent-registration

**Unit**: `agent-registration` (U5: logical agent registration and registration secrets, control face)  
**Unit abbreviation**: AR = agent-registration  
**Scope**: comprehensive (happy path, negative, edge and boundary), as recorded in `aidlc-state.md`  
**Derived from**: `aidlc-docs/platform/m1-walking-skeleton/inception/application-design/unit-of-work.md` and `aidlc-docs/platform/m1-walking-skeleton/inception/requirements/requirements.md` only  
**Generated**: inception pass, 2026-11-02. IDs are permanent  
**Enriched**: construction pass, 2026-11-11 (TC-AR-001 to 022 updated in place; TC-AR-023 to 072 added). Sources: U5's `functional-design/`, `nfr-requirements/` (by the user's instruction), `nfr-design/`. No `infrastructure-design/` (skipped)

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

**Expected outcome**: The registration has: an identifier unique in E; environment E; sponsor H; a ceiling snapshot; standing set {`event:publish`}; an empty re-broadening declaration; autonomy declared; and a registration timestamp. Its state is `registered`. *(Construction pass)* `200` from `POST /registrations` with every attribute in the body: `agent` (the client's identifier), `environment` E, `sponsor` H as `HumanPrincipalReference`, `ceilingSnapshot`, `standingPermissions` [`event:publish`], `reBroadeningDeclaration` [], `autonomyDeclared` true, `registeredAt`, `state` `registered`. There is no read surface (D-AR-20): step 2 reads the response and, in the test, the `registrations` row, which matches it.

**Scope**: happy-path · **Priority**: High  
**Source**: agent-registration / M1-FR-03  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-registration/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; construction pass: `construction/agent-registration/functional-design/business-rules.md` (BR-RG-01; D-AR-02, 20, 22); `construction/agent-registration/nfr-design/nfr-design-patterns.md` (NP-AR-01)

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

**Expected outcome**: The snapshot equals H's held set at that moment, human-only permissions included. *(Construction pass)* `ceilingSnapshot` equals H's whole held set as read once by P3 (`readHumanAuthority().snapshot()`): {`agent:register`, `event:publish`, `event:subscribe`, `grant:human`, `human:manage`}, sorted, human-only permissions included; the `registrations` row holds the same set.

**Scope**: happy-path · **Priority**: High  
**Source**: agent-registration / M1-FR-03  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-registration/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; construction pass: `construction/agent-registration/functional-design/business-rules.md` (D-AR-07, 11; BR-SP-05)

---

### TC-AR-003 — Autonomy declared defaults to no

**Context**: The *autonomy declared* attribute is a boolean, default no (M1-FR-03).

**Scenario**: H registers an agent without stating autonomy.

**Preconditions**:
- E's control-gateway is running. H holds a live credential for E and has self-granted `agent:register`, `event:publish` and `event:subscribe`

**Steps**:
1. Call `registerAgent` with a standing set and no autonomy value
2. Read the registration

**Expected outcome**: Autonomy declared is no. *(Construction pass)* `autonomyDeclared` is `false` in the response and the row (BR-RQ-05).

**Scope**: happy-path · **Priority**: Medium  
**Source**: agent-registration / M1-FR-03  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-registration/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; construction pass: `construction/agent-registration/functional-design/business-rules.md` (BR-RQ-05; D-AR-14)

---

### TC-AR-004 — A re-broadening declaration within the standing set is accepted

**Context**: A declaration is a permission set within the standing set (M1-FR-03).

**Scenario**: H registers B with standing set {`event:subscribe`, `event:publish`}, declaring {`event:subscribe`}.

**Preconditions**:
- E's control-gateway is running. H holds a live credential for E and has self-granted `agent:register`, `event:publish` and `event:subscribe`

**Steps**:
1. Call `registerAgent` with that standing set and declaration

**Expected outcome**: Accepted. The registration records the declaration. *(Construction pass)* `200`; `reBroadeningDeclaration` [`event:subscribe`]; the store's `<@ standing_permissions` constraint holds.

**Scope**: happy-path · **Priority**: High  
**Source**: agent-registration / M1-FR-03  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-registration/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; construction pass: `construction/agent-registration/functional-design/business-rules.md` (BR-RQ-04); `construction/agent-registration/nfr-design/nfr-design-patterns.md` (NP-AR-01)

---

### TC-AR-005 — An empty re-broadening declaration is accepted

**Context**: The declaration may be empty (M1-FR-03).

**Scenario**: H registers an agent with an empty declaration.

**Preconditions**:
- E's control-gateway is running. H holds a live credential for E and has self-granted `agent:register`, `event:publish` and `event:subscribe`

**Steps**:
1. Call `registerAgent` with an empty declaration

**Expected outcome**: Accepted. *(Construction pass)* `200` with the declaration explicitly `[]`, and also with the field omitted (both store `{}`).

**Scope**: happy-path · **Priority**: Medium  
**Source**: agent-registration / M1-FR-03  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-registration/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; construction pass: `construction/agent-registration/functional-design/business-rules.md` (BR-RQ-05; D-AR-14)

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

**Expected outcome**: A secret is returned once. Its record names A and issuer H, and holds only verification material, never the secret itself. *(Construction pass)* `200` from `POST /registration-secrets` with `{ id, registration, secret, issuedAt }`; `secret` matches `soorma_rs_{id}.{secret}` (NFR-AR-01) and carries `Cache-Control: no-store`. The `registration_secrets` row has `registration` = A's `agent`, `issuer` = H, `state` `active`, and a 32-byte `digest` equal to the domain-separated SHA-256 of the secret part; no column holds the value.

**Scope**: happy-path · **Priority**: High  
**Source**: agent-registration / M1-FR-04  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-registration/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; construction pass: `construction/agent-registration/functional-design/business-rules.md` (BR-SE-05); `construction/agent-registration/nfr-requirements/nfr-requirements.md` (NFR-AR-01, 02, 04); `construction/agent-registration/nfr-design/nfr-design-patterns.md` (NP-AR-02)

---

### TC-AR-007 — Registration and issuance are attributed to H

**Context**: Every platform-resource operation is attributed. A direct human operation is attributed to the human, with no origin mode (M1-FR-12).

**Scenario**: A reviewer inspects attribution after registration and issuance.

**Preconditions**:
- E's control-gateway is running. H holds a live credential for E and has self-granted `agent:register`, `event:publish` and `event:subscribe`
- A registered, and a secret issued

**Steps**:
1. Read the attribution records for both operations

**Expected outcome**: Both name H and the credential presented, with scope E and no origin mode or chain. *(Construction pass)* Two `attribution_records` rows: operations `registerAgent` and `issueRegistrationSecret`; actor kind `human`, principal H, credential kind `environmentCredential` with its id; target kind `registration`, target id A's `agent`; scope E; chain, origin, and re-broadening all null. Each committed in its operation's transaction.

**Scope**: happy-path · **Priority**: Medium  
**Source**: agent-registration / M1-FR-12  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-registration/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; construction pass: `construction/agent-registration/functional-design/business-rules.md` (D-AR-17, 18; BR-AT-AR-01, 03)

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

**Expected outcome**: Two distinct registrations in E, each sponsored by H, each with its own snapshot. *(Construction pass)* By raw calls in `e2e/` against the stack (*done when* 1): two `200`s with distinct `agent`s, each response with `sponsor` H and its own `ceilingSnapshot`; two `registrations` rows and two attribution records attributed to H. Then a secret issued for each.

**Scope**: happy-path · **Priority**: High  
**Source**: agent-registration / M1-FR-03  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-registration/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; construction pass: `construction/agent-registration/functional-design/business-rules.md` (business-logic-model §5.1); `construction/agent-registration/functional-design/business-logic-model.md`

---

### TC-AR-009 — A standing set exceeding what the sponsor holds is rejected

**Context**: The standing set must lie within the sponsor's held set (M1-FR-03).

**Scenario**: H registers an agent with `attribution:read`, which H does not hold.

**Preconditions**:
- E's control-gateway is running. H holds a live credential for E and has self-granted `agent:register`, `event:publish` and `event:subscribe`
- H does not hold `attribution:read`

**Steps**:
1. Call `registerAgent` with standing set {`attribution:read`}

**Expected outcome**: Rejected, citing the ceiling. No registration is created. *(Construction pass)* `exceeds_sponsor_ceiling` (403) with `errors[]` pointing at `/standingPermissions/0`, decided at step 9 after `agent:register` passes; no row and no attribution record; security event `registration.refused`, reason `ceiling_exceeded`.

**Scope**: negative · **Priority**: High  
**Source**: agent-registration / M1-FR-03  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-registration/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; construction pass: `construction/agent-registration/functional-design/business-rules.md` (BR-SP-03; D-AR-03)

---

### TC-AR-010 — A standing set containing `grant:human` is rejected, although H holds it

**Context**: A standing set containing a human-only permission is rejected, whatever the sponsor holds (M1-FR-03).

**Scenario**: H, holding `grant:human`, puts it in an agent's standing set.

**Preconditions**:
- E's control-gateway is running. H holds a live credential for E and has self-granted `agent:register`, `event:publish` and `event:subscribe`

**Steps**:
1. Call `registerAgent` with standing set {`grant:human`}

**Expected outcome**: Rejected. *(Construction pass)* `human_only_permission` (400), pointer `/standingPermissions/0`, at step 6 before any state is read; no row.

**Scope**: negative · **Priority**: High  
**Source**: agent-registration / M1-FR-03  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-registration/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; construction pass: `construction/agent-registration/functional-design/business-rules.md` (BR-RQ-03; D-AR-03, 10)

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

**Expected outcome**: Both are rejected. *(Construction pass)* Each is `human_only_permission` (400) with its pointer; no row.

**Scope**: negative · **Priority**: High  
**Source**: agent-registration / M1-FR-03  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-registration/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; construction pass: `construction/agent-registration/functional-design/business-rules.md` (BR-RQ-03)

---

### TC-AR-012 — A declaration exceeding the standing set is rejected

**Context**: A registration declaring re-broadening beyond its standing set is rejected (M1-FR-03).

**Scenario**: H declares `event:subscribe` on an agent whose standing set is {`event:publish`}.

**Preconditions**:
- E's control-gateway is running. H holds a live credential for E and has self-granted `agent:register`, `event:publish` and `event:subscribe`

**Steps**:
1. Call `registerAgent` with standing set {`event:publish`} and declaration {`event:subscribe`}

**Expected outcome**: Rejected. *(Construction pass)* `declaration_outside_standing` (400), pointer `/reBroadeningDeclaration/0`, at step 6; no row.

**Scope**: negative · **Priority**: High  
**Source**: agent-registration / M1-FR-03  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-registration/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; construction pass: `construction/agent-registration/functional-design/business-rules.md` (BR-RQ-04; D-AR-03)

---

### TC-AR-013 — A standing set with a non-plane-declared identifier is rejected

**Context**: Accepted identifiers are limited to the plane-declared set (GAP-INT-006 work-around), in standing sets as in grants (M1-FR-15).

**Scenario**: H registers an agent with an unknown identifier.

**Preconditions**:
- E's control-gateway is running. H holds a live credential for E and has self-granted `agent:register`, `event:publish` and `event:subscribe`

**Steps**:
1. Call `registerAgent` with standing set {`invoice:approve`}

**Expected outcome**: Rejected, naming the identifier. *(Construction pass)* `unknown_permission` (400), pointer `/standingPermissions/0`, at step 6, before the human-only check and authority; no row (GAP-INT-006 work-around).

**Scope**: negative · **Priority**: High  
**Source**: agent-registration / M1-FR-15, M1-FR-03  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-registration/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; construction pass: `construction/agent-registration/functional-design/business-rules.md` (BR-RQ-02; D-AR-14)

---

### TC-AR-014 — Registration without `agent:register` is denied

**Context**: Registering requires `agent:register` in E (M1-FR-08).

**Scenario**: H2, holding a credential for E but not `agent:register`, tries to register.

**Preconditions**:
- H2 holds a credential for E and no `agent:register`

**Steps**:
1. Call `registerAgent` as H2

**Expected outcome**: Denied. *(Construction pass)* `forbidden` (403), no detail, at step 9 (BR-SP-02); no row; reason `authority_denied` in the security log.

**Scope**: negative · **Priority**: High  
**Source**: agent-registration / M1-FR-08  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-registration/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; construction pass: `construction/agent-registration/functional-design/business-rules.md` (BR-SP-02)

---

### TC-AR-015 — Secret issuance without `agent:register` is denied

**Context**: Issuance requires `agent:register` (M1-FR-04).

**Scenario**: H2, without `agent:register`, tries to issue a secret for A.

**Preconditions**:
- A registered by H
- H2 holds a credential for E and no `agent:register`

**Steps**:
1. Call `issueRegistrationSecret` for A as H2

**Expected outcome**: Denied. *(Construction pass)* `forbidden` (403) at step 9 (BR-SE-02), before the registration lookup; no secret row.

**Scope**: negative · **Priority**: High  
**Source**: agent-registration / M1-FR-04  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-registration/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; construction pass: `construction/agent-registration/functional-design/business-rules.md` (BR-SE-02)

---

### TC-AR-016 — Registration by an agent is refused

**Context**: Registration and secret issuance by an agent are absent from M1, a delivery decision (M1-FR-03).

**Scenario**: An instance of A, holding `agent:register` in its standing set, tries to register an agent.

**Preconditions**:
- E's control-gateway is running. H holds a live credential for E and has self-granted `agent:register`, `event:publish` and `event:subscribe`
- A is registered with `agent:register` in its standing set and holds an agent credential

**Steps**:
1. Call `registerAgent`, presenting A's agent credential

**Expected outcome**: Refused. No registration is created. *(Construction pass)* Presenting a `soorma_ac_` value on `POST /registrations` (and on `POST /registration-secrets`) is `credential_refused` (401, `WWW-Authenticate: Bearer`) **by kind, without verifying** (BR-PR-AR-03), so the case needs no agent credential from U6: any `soorma_ac_`-prefixed value serves. No row.

**Scope**: negative · **Priority**: High  
**Source**: agent-registration / M1-FR-03  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-registration/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; construction pass: `construction/agent-registration/functional-design/business-rules.md` (BR-PR-AR-03; D-AR-08)

---

### TC-AR-017 — A secret for an unknown registration is rejected

**Context**: A secret is bound to one registration in E (M1-FR-04).

**Scenario**: H issues a secret for a registration reference that does not exist in E.

**Preconditions**:
- E's control-gateway is running. H holds a live credential for E and has self-granted `agent:register`, `event:publish` and `event:subscribe`

**Steps**:
1. Call `issueRegistrationSecret` with an unknown reference

**Expected outcome**: Rejected. *(Construction pass)* `unknown_registration` (400), pointer `/registration`, after `agent:register` passes (BR-SE-03); no secret row.

**Scope**: negative · **Priority**: Medium  
**Source**: agent-registration / M1-FR-04  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-registration/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; construction pass: `construction/agent-registration/functional-design/business-rules.md` (BR-SE-03; D-AR-05)

---

### TC-AR-018 — A standing set equal to the held set is accepted

**Context**: Boundary of the ceiling: subset includes equality (M1-FR-03).

**Scenario**: H registers an agent with exactly H's non-human-only held permissions.

**Preconditions**:
- E's control-gateway is running. H holds a live credential for E and has self-granted `agent:register`, `event:publish` and `event:subscribe`

**Steps**:
1. Call `registerAgent` with {`agent:register`, `event:publish`, `event:subscribe`}

**Expected outcome**: Accepted. *(Construction pass)* `200`; `standingPermissions` equals the three; the snapshot also holds `grant:human` and `human:manage`; the `<@ ceiling_snapshot` constraint holds. Also: an **empty** standing set is accepted (BR-SP-03).

**Scope**: edge-boundary · **Priority**: Medium  
**Source**: agent-registration / M1-FR-03  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-registration/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; construction pass: `construction/agent-registration/functional-design/business-rules.md` (BR-SP-03; D-AR-14)

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

**Expected outcome**: The snapshot is unchanged. *(Construction pass)* The `registrations` row's `ceiling_snapshot` is unchanged after H's new grant; a registration made after it has the larger snapshot (business-logic-model §5.4).

**Scope**: edge-boundary · **Priority**: High  
**Source**: agent-registration / M1-FR-03  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-registration/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; construction pass: `construction/agent-registration/functional-design/business-rules.md` (D-AR-11; BR-SP-04)

---

### TC-AR-020 — A secret is returned only once

**Context**: Secret verification material is internal (M1-FR-04). The secret itself is never retrievable after issuance.

**Scenario**: A reviewer looks for a way to read A's secret back.

**Preconditions**:
- E's control-gateway is running. H holds a live credential for E and has self-granted `agent:register`, `event:publish` and `event:subscribe`
- A secret issued for A

**Steps**:
1. Inspect every operation in `control-gateway.openapi.yaml` for one that returns an existing secret

**Expected outcome**: None exists. The secret appeared only in the issuance response. *(Construction pass)* `control-gateway.openapi.yaml` has exactly U4's four and U5's two operations, none returning a secret; the store holds only the digest (NP-AR-01); no log line carries the value (TC-AR-036).

**Scope**: edge-boundary · **Priority**: High  
**Source**: agent-registration / M1-FR-04  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-registration/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; construction pass: `construction/agent-registration/functional-design/business-rules.md` (D-AR-16, 20); `construction/agent-registration/nfr-requirements/nfr-requirements.md` (NFR-AR-04)

---

### TC-AR-021 — An unresolvable sponsor held set rejects the registration

**Context**: If the sponsor's held set cannot be resolved, registration is rejected; refusing is the only truthful answer (M1-FR-03).

**Scenario**: The grant store is unreachable while H registers an agent.

**Preconditions**:
- E's control-gateway is running. H holds a live credential for E and has self-granted `agent:register`, `event:publish` and `event:subscribe`
- E's grant records are made unavailable

**Steps**:
1. Call `registerAgent`

**Expected outcome**: Rejected. No registration is created. *(Construction pass)* With the held-set read failing (a fault-injecting `GrantSource`, or the store stopped), `unavailable` (503, `Retry-After`), nothing written; reason `held_set_unreadable`.

**Scope**: edge-boundary · **Priority**: Medium  
**Source**: agent-registration / M1-FR-03  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-registration/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; construction pass: `construction/agent-registration/functional-design/business-rules.md` (D-AR-13; BR-SP-01)

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

**Expected outcome**: Every one of the unit's operations is present and references the conventions. The violating request is rejected with the contract's error model before any processing. *(Construction pass)* Both operations in `contract/control-gateway.openapi.yaml`, each naming `environmentCredential` only and the shared components; the six new codes in `ProblemCode` and `errors.md`; a body failing the schema is `malformed_request` with pointers, before authority. S2's tests run `assertProblem` on every Problem.

**Scope**: happy-path · **Priority**: High  
**Source**: agent-registration / M1-FR-02  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-registration/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; construction pass: `construction/agent-registration/functional-design/business-rules.md` (§13; D-AR-22, 23)

---

### TC-AR-023 — A taken identifier is `registration_exists`, decided only after authority and the ceiling

**Context**: The client chooses the identifier, unique within E; a second registration with it is refused, and only a caller whose request is otherwise valid learns it is taken (D-AR-02).

**Scenario**: H registers `a`, then registers `a` again; H2 without `agent:register` also tries `a`.

**Preconditions**:
- E's control-gateway is running on the local stack. H holds a live credential for E and holds `agent:register`, `event:publish`, `event:subscribe` (self-granted), with `grant:human` and `human:manage` (configuration)
- H2 holds a live credential for E and no `agent:register`

**Steps**:
1. Register `a` with {`event:publish`}
2. Register `a` again with {`event:publish`}
3. As H2, register `a`
4. As H, register `a` with {`attribution:read`} (not held)

**Expected outcome**: Step 1: `200`. Step 2: `registration_exists` (409, `errors[]` with one pointer `/agent`), no new row, no attribution record. Step 3: `forbidden`, never `registration_exists`. Step 4: `exceeds_sponsor_ceiling`, never `registration_exists`.

**Scope**: negative · **Priority**: High  
**Source**: agent-registration / M1-FR-03 (D-AR-02)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-registration/code/`  
**Technical references**: `construction/agent-registration/functional-design/business-rules.md` (D-AR-02; BR-RG-02)

---

### TC-AR-024 — Two concurrent registrations of one identifier write one row and one attribution record

**Context**: The store's primary key decides a race; the loser writes nothing, its attribution record included (D-AR-26).

**Scenario**: Two requests register `x` at the same moment.

**Preconditions**:
- A test environment store from `pnpm db:test` (PostgreSQL 18), migrated through `0002_registrations.sql` by the shared runner, with the app and migrator roles

**Steps**:
1. Run two `registerAgent` transactions for `x` concurrently, both past authority

**Expected outcome**: Exactly one succeeds; the other is `registration_exists`. One `registrations` row and one `registerAgent` attribution record for `x`.

**Scope**: edge-boundary · **Priority**: High  
**Source**: agent-registration / M1-FR-03 (D-AR-26)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-registration/code/`  
**Technical references**: `construction/agent-registration/functional-design/business-rules.md` (D-AR-26); `construction/agent-registration/nfr-design/nfr-design-patterns.md` (NP-AR-06)

---

### TC-AR-025 — The same identifier in E and E2 is two independent registrations

**Context**: Uniqueness is per environment: an agent belongs to exactly one environment (PF §6, §7a).

**Scenario**: H registers `a` in E and in E2.

**Preconditions**:
- E's control-gateway is running on the local stack. H holds a live credential for E and holds `agent:register`, `event:publish`, `event:subscribe` (self-granted), with `grant:human` and `human:manage` (configuration)
- H also holds a credential for E2 and `agent:register`, `event:publish` there

**Steps**:
1. Register `a` in E
2. Register `a` in E2
3. Issue a secret for `a` in E

**Expected outcome**: Both `200`. Two rows in two stores. E2's `a` is never returned for E by any P4 read, and the secret in E names E's `a` only.

**Scope**: edge-boundary · **Priority**: High  
**Source**: agent-registration / M1-FR-03 (I1)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-registration/code/`  
**Technical references**: `construction/agent-registration/functional-design/business-rules.md` (BR-RG-02)

---

### TC-AR-026 — A body naming a sponsor is `malformed_request`

**Context**: The sponsor is always the presenting human; the closed schema refuses a `sponsor` field (D-AR-09).

**Scenario**: H registers with `sponsor` set to another principal.

**Preconditions**:
- E's control-gateway is running on the local stack. H holds a live credential for E and holds `agent:register`, `event:publish`, `event:subscribe` (self-granted), with `grant:human` and `human:manage` (configuration)

**Steps**:
1. Call `registerAgent` with `sponsor: { organization: O, principal: "h2" }`

**Expected outcome**: `malformed_request` (400) with a pointer at `/sponsor`; no row.

**Scope**: negative · **Priority**: High  
**Source**: agent-registration / M1-FR-03 (D-AR-09)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-registration/code/`  
**Technical references**: `construction/agent-registration/functional-design/business-rules.md` (D-AR-09; BR-RQ-01)

---

### TC-AR-027 — The app role holds only `SELECT` and `INSERT` on registrations and secrets

**Context**: Registrations and secrets are never modified or deleted in M1 (D-AR-15; NFR-AR-23).

**Scenario**: Connected as `soorma_env_app`.

**Preconditions**:
- A test environment store from `pnpm db:test` (PostgreSQL 18), migrated through `0002_registrations.sql` by the shared runner, with the app and migrator roles

**Steps**:
1. Attempt `UPDATE` and `DELETE` on `registrations` and on `registration_secrets`
2. Attempt `SELECT` and `INSERT` on both

**Expected outcome**: Every step 1 statement fails with `insufficient_privilege`; step 2 succeeds.

**Scope**: negative · **Priority**: High  
**Source**: agent-registration / NFR-AR-23 (D-AR-15)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-registration/code/`  
**Technical references**: `construction/agent-registration/nfr-requirements/nfr-requirements.md` (NFR-AR-23); `construction/agent-registration/nfr-design/nfr-design-patterns.md` (NP-AR-01)

---

### TC-AR-028 — No code path updates or deletes a registration or a secret

**Context**: A resolution target is never removed (PF FR-013); the privilege test is backed by a code check.

**Scenario**: A code check over `packages/registry/src/sql.ts` and every U5 statement.

**Preconditions**:
- U5's code

**Steps**:
1. Scan every SQL statement in P4 and S2 for `UPDATE` or `DELETE` naming `registrations` or `registration_secrets`

**Expected outcome**: None found.

**Scope**: negative · **Priority**: Medium  
**Source**: agent-registration / M1-FR-03 (PF FR-013)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-registration/code/`  
**Technical references**: `construction/agent-registration/functional-design/business-rules.md` (D-AR-15)

---

### TC-AR-029 — `exceeds_sponsor_ceiling` points at each standing entry not held

**Context**: The ceiling rejection cites the ceiling (TC-AR-009) and names only the caller's own requested entries (D-AR-03).

**Scenario**: H registers {`event:publish`, `agent:retire`, `credential:revoke`}, holding only the first.

**Preconditions**:
- E's control-gateway is running on the local stack. H holds a live credential for E and holds `agent:register`, `event:publish`, `event:subscribe` (self-granted), with `grant:human` and `human:manage` (configuration)

**Steps**:
1. Call `registerAgent` with that standing set

**Expected outcome**: `exceeds_sponsor_ceiling` (403) with pointers `/standingPermissions/1` and `/standingPermissions/2`, ordered, at most 10; no row.

**Scope**: negative · **Priority**: High  
**Source**: agent-registration / M1-FR-03 (D-AR-03)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-registration/code/`  
**Technical references**: `construction/agent-registration/functional-design/business-rules.md` (BR-SP-03)

---

### TC-AR-030 — `human_only_permission` points at each human-only entry, after `unknown_permission`

**Context**: Step 6's order: accepted identifiers first, then the human-only class (BR-RQ-02, 03).

**Scenario**: Two registrations: one with {`grant:human`, `event:publish`, `agent:delegate`}; one adding an unaccepted identifier.

**Preconditions**:
- E's control-gateway is running on the local stack. H holds a live credential for E and holds `agent:register`, `event:publish`, `event:subscribe` (self-granted), with `grant:human` and `human:manage` (configuration)

**Steps**:
1. Register with {`grant:human`, `event:publish`, `agent:delegate`}
2. Register with {`grant:human`, `billing:approve`}

**Expected outcome**: Step 1: `human_only_permission` with pointers `/standingPermissions/0` and `/standingPermissions/2`. Step 2: `unknown_permission` pointing at `/standingPermissions/1`. No row either time.

**Scope**: negative · **Priority**: High  
**Source**: agent-registration / M1-FR-03  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-registration/code/`  
**Technical references**: `construction/agent-registration/functional-design/business-rules.md` (BR-RQ-02, 03)

---

### TC-AR-031 — S2 and P4 import no evaluator or human-only class but P3's

**Context**: One place tests a human's set, and the human-only class has one definition (I5; D-AE-03; BR-SP-07).

**Scenario**: A dependency test over `services/control-gateway` and `packages/registry`.

**Preconditions**:
- U5's code

**Steps**:
1. List every import of `services/control-gateway` and `packages/registry`
2. Search both for a permission-set comparison or a copy of the human-only identifiers

**Expected outcome**: Authority comes only from `@soorma/authority` (`readHumanAuthority`, `checkRegistrationRequest`, `evaluateHuman`, `holdsAnyGrant`); no other evaluator, and no copy of the class, outside labelled test fixtures.

**Scope**: negative · **Priority**: High  
**Source**: agent-registration / M1-FR-08 (I5)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-registration/code/`  
**Technical references**: `construction/agent-registration/functional-design/business-rules.md` (BR-SP-07; D-AR-07, 10); `construction/agent-registration/nfr-design/nfr-design-patterns.md` (NP-AR-05)

---

### TC-AR-032 — The agent-facts source reads one statement, in E only, without snapshot or sponsor

**Context**: U3's port is filled with one query; the sponsor's set is never consulted per request (D-AR-19; PF §8b).

**Scenario**: P4's `AgentFactsSource.load` over a list of agents.

**Preconditions**:
- A test environment store from `pnpm db:test` (PostgreSQL 18), migrated through `0002_registrations.sql` by the shared runner, with the app and migrator roles
- Registrations `a1` to `a32` in E, and `a1` also under E2's identity

**Steps**:
1. With a counting pool, load E with 33 agents (`a1` to `a32` and `missing`)
2. Inspect the result's fields

**Expected outcome**: One statement executed. 32 entries, each with `registrationView` (autonomy, declaration) and `standingSet` from E's rows; `missing` absent; E2's `a1` never used. No snapshot or sponsor in the result.

**Scope**: happy-path · **Priority**: High  
**Source**: agent-registration / M1-FR-08 (D-AR-19)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-registration/code/`  
**Technical references**: `construction/agent-registration/nfr-requirements/nfr-requirements.md` (NFR-AR-16); `construction/agent-registration/nfr-design/nfr-design-patterns.md` (NP-AR-04)

---

### TC-AR-033 — Who may issue a secret: the sponsor, or an Admin holding `agent:register`

**Context**: Issuance needs `agent:register` and the sponsor or an Admin (`grant:human` and `human:manage`) (D-AR-01, specified by ID §3 with PF §8a).

**Scenario**: D registers `d1`. Four presenters issue for it, and D issues for H's `a`.

**Preconditions**:
- E's control-gateway is running on the local stack. H holds a live credential for E and holds `agent:register`, `event:publish`, `event:subscribe` (self-granted), with `grant:human` and `human:manage` (configuration)
- D holds `agent:register`, `event:publish`; A2 holds `agent:register`, `grant:human`, `human:manage`; M holds `grant:human`, `human:manage` only; `a` registered by H

**Steps**:
1. As D, issue for `d1`
2. As D, issue for `a`
3. As A2, issue for `d1`
4. As M, issue for `d1`
5. As H, issue for `d1`

**Expected outcome**: Steps 1, 3, 5: `200`, issuer the presenter. Step 2: `forbidden`. Step 4: `forbidden` (no `agent:register`, decided before the lookup).

**Scope**: negative · **Priority**: High  
**Source**: agent-registration / M1-FR-04 (D-AR-01)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-registration/code/`  
**Technical references**: `construction/agent-registration/functional-design/business-rules.md` (D-AR-01; BR-SE-02, 04); `construction/agent-registration/functional-design/business-logic-model.md` (§5.3)

---

### TC-AR-034 — A registration holds several active secrets

**Context**: Each issuance creates an independent active secret with its own issuer (D-AR-04).

**Scenario**: H and A2 each issue a secret for `a`.

**Preconditions**:
- E's control-gateway is running on the local stack. H holds a live credential for E and holds `agent:register`, `event:publish`, `event:subscribe` (self-granted), with `grant:human` and `human:manage` (configuration)
- A2 as in TC-AR-033

**Steps**:
1. As H, issue for `a`
2. As A2, issue for `a`

**Expected outcome**: Two `200`s with different ids and values; two `active` rows for `a`, issuers H and A2.

**Scope**: happy-path · **Priority**: Medium  
**Source**: agent-registration / M1-FR-04 (D-AR-04)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-registration/code/`  
**Technical references**: `construction/agent-registration/functional-design/business-rules.md` (BR-SE-06)

---

### TC-AR-035 — An unaccepted identifier in the declaration is `unknown_permission`

**Context**: Both sets are checked against the accepted identifiers (D-AR-14; GAP-INT-006).

**Scenario**: H declares an identifier no plane declares.

**Preconditions**:
- E's control-gateway is running on the local stack. H holds a live credential for E and holds `agent:register`, `event:publish`, `event:subscribe` (self-granted), with `grant:human` and `human:manage` (configuration)

**Steps**:
1. Register with standing {`event:publish`} and declaration {`invoice:approve`}

**Expected outcome**: `unknown_permission` (400), pointer `/reBroadeningDeclaration/0`; no row.

**Scope**: negative · **Priority**: Medium  
**Source**: agent-registration / M1-FR-15  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-registration/code/`  
**Technical references**: `construction/agent-registration/functional-design/business-rules.md` (BR-RQ-02)

---

### TC-AR-036 — No secret value or digest reaches a log, a record, or a Problem; issuance is not cacheable

**Context**: The value appears only in the issuance response (NFR-AR-04; D-AR-16).

**Scenario**: H issues a secret, then issues one that is refused.

**Preconditions**:
- E's control-gateway is running on the local stack. H holds a live credential for E and holds `agent:register`, `event:publish`, `event:subscribe` (self-granted), with `grant:human` and `human:manage` (configuration)

**Steps**:
1. Capture every log line and the attribution row while issuing a secret for `a`
2. Capture the same while issuing for an unknown registration

**Expected outcome**: Neither the value, its secret part, nor its digest (hex or base64) appears in any captured line, row, or Problem. The `200` carries `Cache-Control: no-store`.

**Scope**: negative · **Priority**: High  
**Source**: agent-registration / M1-FR-04 (SECURITY-03, 12)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-registration/code/`  
**Technical references**: `construction/agent-registration/nfr-requirements/nfr-requirements.md` (NFR-AR-04); `construction/agent-registration/nfr-design/nfr-design-patterns.md` (NP-AR-02, 07)

---

### TC-AR-037 — A self-grant of `agent:register` is usable on the next registration

**Context**: Read-your-writes for the acting principal: the held set is read uncached (BR-SP-06; PF §10).

**Scenario**: H2, holding `grant:human` but not `agent:register`, grants it to themselves and registers.

**Preconditions**:
- E's control-gateway is running on the local stack. H holds a live credential for E and holds `agent:register`, `event:publish`, `event:subscribe` (self-granted), with `grant:human` and `human:manage` (configuration)
- H2 holds `grant:human` and `event:publish` in E

**Steps**:
1. As H2, register (expect `forbidden`)
2. As H2, `grantToHuman` self with {`agent:register`}
3. As H2, register again at once

**Expected outcome**: Step 1 `forbidden`; step 3 `200`, its snapshot including `agent:register`.

**Scope**: happy-path · **Priority**: High  
**Source**: agent-registration / M1-FR-03 (PF §10)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-registration/code/`  
**Technical references**: `construction/agent-registration/functional-design/business-rules.md` (BR-SP-06)

---

### TC-AR-038 — Each operation reads the held set once; U4's evaluator tests are unchanged

**Context**: One read, one evaluator (D-AR-07): the snapshot is the set the check judged.

**Scenario**: S2 with a counting `GrantSource`.

**Preconditions**:
- U5's code; U4's `evaluateHuman` and `holdsAnyGrant` tests at their U4 text

**Steps**:
1. Register once; issue once; count `GrantSource` reads
2. Run U4's `evaluateHuman` and `holdsAnyGrant` tests

**Expected outcome**: Exactly one read per operation. U4's tests pass with no assertion changed.

**Scope**: happy-path · **Priority**: High  
**Source**: agent-registration / M1-FR-08 (D-AR-07)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-registration/code/`  
**Technical references**: `construction/agent-registration/functional-design/business-rules.md` (BR-HA-01 to 04); `construction/agent-registration/nfr-requirements/nfr-requirements.md` (NFR-AR-21); `construction/agent-registration/nfr-design/nfr-design-patterns.md` (NP-AR-05)

---

### TC-AR-039 — A principal of E reaches nothing of E2's, on every U5 access path

**Context**: Isolation per access path (I1).

**Scenario**: Rows seeded under E2's identity in E's store, and E2's own stack.

**Preconditions**:
- A test environment store from `pnpm db:test` (PostgreSQL 18), migrated through `0002_registrations.sql` by the shared runner, with the app and migrator roles
- A registration `z` and a secret for it seeded under E2's identity in E's store

**Steps**:
1. Issue a secret for `z` in E
2. Load agent facts for `z` in E
3. Register `z` in E
4. Issue a secret for `z` in E, then count active secrets for `z` in E

**Expected outcome**: Step 1: `unknown_registration` (E has no `z`). Step 2: `z` absent. Step 3: `200`, E's own `z`. Step 4: `200`, and the count is 1: E2's seeded secret is never counted or matched.

**Scope**: negative · **Priority**: High  
**Source**: agent-registration / M1-FR-03 (I1)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-registration/code/`  
**Technical references**: `construction/agent-registration/nfr-design/nfr-design-patterns.md` (NP-AR-01, 04)

---

### TC-AR-040 — Scope, actor, and sponsor are recoverable from the records alone

**Context**: Sponsorship resolves through the registration, which is never deleted (BR-AT-AR-02; PF §7b).

**Scenario**: A reviewer reconstructs, from rows only, who registered A and who sponsors an agent record naming A.

**Preconditions**:
- A test environment store from `pnpm db:test` (PostgreSQL 18), migrated through `0002_registrations.sql` by the shared runner, with the app and migrator roles
- A registered by H; a constructed agent attribution record naming `a`

**Steps**:
1. From the `registerAgent` record: scope, actor, target
2. From the agent record: the agent, then the registration's `sponsor`

**Expected outcome**: Scope E, actor H with the credential, target `a`; the agent record's sponsor resolves to H in two hops, equal to its own `sponsor` column.

**Scope**: happy-path · **Priority**: High  
**Source**: agent-registration / M1-FR-12 (I4)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-registration/code/`  
**Technical references**: `construction/agent-registration/functional-design/business-rules.md` (BR-AT-AR-02)

---

### TC-AR-041 — A failed attribution write leaves no registration and no secret

**Context**: Each write and its record are one transaction (D-AR-18).

**Scenario**: A fault-injecting `Tx` fails the attribution insert.

**Preconditions**:
- A test environment store from `pnpm db:test` (PostgreSQL 18), migrated through `0002_registrations.sql` by the shared runner, with the app and migrator roles

**Steps**:
1. Register with the fault
2. Issue a secret with the fault

**Expected outcome**: Both `unavailable`; no `registrations` row and no `registration_secrets` row.

**Scope**: negative · **Priority**: High  
**Source**: agent-registration / M1-FR-12 (D-AR-18)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-registration/code/`  
**Technical references**: `construction/agent-registration/nfr-requirements/nfr-requirements.md` (NFR-AR-17); `construction/agent-registration/nfr-design/nfr-design-patterns.md` (NP-AR-06)

---

### TC-AR-042 — Wrong presenters are refused on both operations

**Context**: Only E's environment credential is accepted (BR-PR-AR).

**Scenario**: Four presentations on each operation.

**Preconditions**:
- E's control-gateway is running on the local stack. H holds a live credential for E and holds `agent:register`, `event:publish`, `event:subscribe` (self-granted), with `grant:human` and `human:manage` (configuration)
- H holds a credential for E2

**Steps**:
1. Present E2's credential at E
2. Present H's sign-in
3. Present two `Authorization` headers
4. Send a `Soorma-Delegation` header

**Expected outcome**: Each is `credential_refused` (401); E2's credential's expiry is never disclosed.

**Scope**: negative · **Priority**: High  
**Source**: agent-registration / M1-FR-03 (ID §8b)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-registration/code/`  
**Technical references**: `construction/agent-registration/functional-design/business-rules.md` (BR-PR-AR-01 to 03)

---

### TC-AR-043 — Every rejection holds for a raw call

**Context**: Every check is at S2, from the raw request (I2).

**Scenario**: TC-AR-009 to 017's rejections sent as raw HTTP, plus a forged `soorma_ec_` value.

**Preconditions**:
- E's control-gateway is running on the local stack. H holds a live credential for E and holds `agent:register`, `event:publish`, `event:subscribe` (self-granted), with `grant:human` and `human:manage` (configuration)

**Steps**:
1. Send each as a raw call
2. Send a `soorma_ec_` value signed with a key E does not hold

**Expected outcome**: Each gets its code; the forged credential is `credential_refused`.

**Scope**: negative · **Priority**: High  
**Source**: agent-registration / M1-FR-02 (I2)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-registration/code/`  
**Technical references**: `construction/agent-registration/functional-design/business-rules.md` (§10)

---

### TC-AR-044 — The same credential from another source address registers with the same sponsor

**Context**: Identity comes only from the presented credential (I3).

**Scenario**: H registers from two source addresses; a request with no credential comes from inside E's network.

**Preconditions**:
- E's control-gateway is running on the local stack. H holds a live credential for E and holds `agent:register`, `event:publish`, `event:subscribe` (self-granted), with `grant:human` and `human:manage` (configuration)

**Steps**:
1. Register `p1` from the host
2. Register `p2` from a container on E's network with the same credential
3. From that container, register with no credential

**Expected outcome**: Steps 1 and 2: `200`, both sponsored by H. Step 3: `credential_refused`.

**Scope**: negative · **Priority**: Medium  
**Source**: agent-registration / M1-FR-03 (I3)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-registration/code/`  
**Technical references**: `construction/agent-registration/functional-design/business-rules.md` (D-AR-09)

---

### TC-AR-045 — The contract changes are compatible and recorded

**Context**: Two operations and six codes, all compatible (I7).

**Scenario**: U1's compatibility check over the changed contract.

**Preconditions**:
- `contract/` after U5's Code Generation

**Steps**:
1. Run the contract checks and the compatibility check
2. Read `contract/CHANGELOG.md`

**Expected outcome**: Both pass; the six codes are in `ProblemCode` and `errors.md` (codes, check order steps 6 and 9, disclosure); the change log names both operations and all six codes as compatible.

**Scope**: happy-path · **Priority**: High  
**Source**: agent-registration / M1-FR-02 (I7)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-registration/code/`  
**Technical references**: `construction/agent-registration/functional-design/business-rules.md` (§13)

---

### TC-AR-046 — Nothing unassigned or commercial lands in core; the cap is a security bound

**Context**: The I8 packaging table, re-checked as a set (I8; NFR-AR-24).

**Scenario**: A reviewer re-checks the table against the code.

**Preconditions**:
- U5's code; the I8 table

**Steps**:
1. Check every U5 capability against PF §12
2. Search for a registration read surface, sponsorship policy, rotation, retirement, a registration quota

**Expected outcome**: Every capability core-assigned; none of the searched items exists in any form; the cap of 10 is a platform constant, not configuration.

**Scope**: negative · **Priority**: High  
**Source**: agent-registration / I8 (NFR-AR-24)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-registration/code/`  
**Technical references**: `construction/agent-registration/functional-design/invariant-coverage-matrix.md` (I8 Packaging Table)

---

### TC-AR-047 — No tenant identifiers or deployment topology in U5's code

**Context**: Mechanism, not instance; runtime-later (I9, I10).

**Scenario**: A code review with a check.

**Preconditions**:
- U5's code

**Steps**:
1. Search for permission identifiers outside P4's accepted set and test fixtures
2. Search for reads of hostnames, source addresses, or deployment labels

**Expected outcome**: None found outside labelled fixtures.

**Scope**: negative · **Priority**: Medium  
**Source**: agent-registration / I9, I10  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-registration/code/`  
**Technical references**: `construction/agent-registration/functional-design/business-rules.md` (D-AR-02)

---

### TC-AR-048 — A secret's value has the specified format, and values are distinct

**Context**: `soorma_rs_{id}.{secret}`: 128-bit id, 256-bit secret, base64url, no checksum (NFR-AR-01).

**Scenario**: `generateRegistrationSecret` called 10,000 times.

**Preconditions**:
- `packages/registry`

**Steps**:
1. Generate 10,000 values

**Expected outcome**: Each: prefix `soorma_rs_`; one `.`; a 22-character and a 43-character base64url part; at most 256 characters. All distinct.

**Scope**: happy-path · **Priority**: High  
**Source**: agent-registration / NFR-AR-01  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-registration/code/`  
**Technical references**: `construction/agent-registration/nfr-requirements/nfr-requirements.md` (NFR-AR-01); `construction/agent-registration/nfr-design/nfr-design-patterns.md` (NP-AR-02)

---

### TC-AR-049 — The digest matches its test vector, and the store holds only it

**Context**: An unkeyed, domain-separated SHA-256 (NFR-AR-02).

**Scenario**: A fixed secret part and its literal expected digest.

**Preconditions**:
- `packages/registry`; a test store

**Steps**:
1. Digest the fixed 32 bytes
2. Issue a secret and read its row

**Expected outcome**: Step 1 equals the literal vector. Step 2: a 32-byte digest; no column contains the value or its secret part.

**Scope**: happy-path · **Priority**: High  
**Source**: agent-registration / NFR-AR-02  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-registration/code/`  
**Technical references**: `construction/agent-registration/nfr-requirements/nfr-requirements.md` (NFR-AR-02); `construction/agent-registration/nfr-design/nfr-design-patterns.md` (NP-AR-02)

---

### TC-AR-050 — Each malformed value is refused by the parser

**Context**: One encoding per value, refused before hashing (NFR-AR-03), the rule U6's bootstrap applies.

**Scenario**: `parseRegistrationSecret` over malformations.

**Preconditions**:
- `packages/registry`

**Steps**:
1. Parse: no prefix; another prefix; no `.`; two `.`s; a 21- or 23-character id; a 42- or 44-character secret; a secret with a non-canonical final character; padding `=`; a non-base64url character

**Expected outcome**: Each returns `invalid` without throwing; `registrationSecretMatches` returns `false` for a stored digest of any length but 32.

**Scope**: negative · **Priority**: High  
**Source**: agent-registration / NFR-AR-03  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-registration/code/`  
**Technical references**: `construction/agent-registration/nfr-requirements/nfr-requirements.md` (NFR-AR-03); `construction/agent-registration/nfr-design/nfr-design-patterns.md` (NP-AR-02)

---

### TC-AR-051 — The 10th secret is issued; an 11th is `secret_limit_reached`, shown only to a permitted caller

**Context**: At most 10 active secrets per registration, a lifetime total in M1 (NFR-AR-06).

**Scenario**: Ten secrets issued for `a`, then more.

**Preconditions**:
- E's control-gateway is running on the local stack. H holds a live credential for E and holds `agent:register`, `event:publish`, `event:subscribe` (self-granted), with `grant:human` and `human:manage` (configuration)
- D as in TC-AR-033

**Steps**:
1. Issue 10 secrets for `a` as H
2. Issue an 11th as H
3. As D (neither sponsor nor Admin), issue for `a`

**Expected outcome**: Step 1: ten `200`s. Step 2: `secret_limit_reached` (409, no `errors[]`), no row. Step 3: `forbidden`, never `secret_limit_reached`.

**Scope**: edge-boundary · **Priority**: High  
**Source**: agent-registration / NFR-AR-06  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-registration/code/`  
**Technical references**: `construction/agent-registration/nfr-requirements/nfr-requirements.md` (NFR-AR-06); `construction/agent-registration/functional-design/business-rules.md` (BR-SE-06)

---

### TC-AR-052 — The cap holds under concurrent issuances

**Context**: Serialised per registration without `UPDATE` privilege (NFR-AR-07).

**Scenario**: Five concurrent issuances at 9 active secrets.

**Preconditions**:
- A test environment store from `pnpm db:test` (PostgreSQL 18), migrated through `0002_registrations.sql` by the shared runner, with the app and migrator roles
- `a` with 9 active secrets

**Steps**:
1. Run 5 issuances for `a` concurrently

**Expected outcome**: Exactly 1 succeeds; 4 are `secret_limit_reached`; `a` has 10 secrets and 1 new `issueRegistrationSecret` attribution record.

**Scope**: edge-boundary · **Priority**: High  
**Source**: agent-registration / NFR-AR-07  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-registration/code/`  
**Technical references**: `construction/agent-registration/nfr-requirements/nfr-requirements.md` (NFR-AR-07); `construction/agent-registration/nfr-design/nfr-design-patterns.md` (NP-AR-03)

---

### TC-AR-053 — Issuances for different registrations do not wait on each other; the lock key is derived as specified

**Context**: The lock is keyed per registration (NP-AR-03).

**Scenario**: Two registrations, one transaction holding `a`'s lock.

**Preconditions**:
- A test environment store from `pnpm db:test` (PostgreSQL 18), migrated through `0002_registrations.sql` by the shared runner, with the app and migrator roles

**Steps**:
1. Hold `a`'s lock in an open transaction
2. Issue for `b` concurrently
3. Compute the key for a fixed tuple

**Expected outcome**: Step 2 completes while step 1's transaction is open. Step 3 equals the literal 63-bit vector.

**Scope**: edge-boundary · **Priority**: Medium  
**Source**: agent-registration / NFR-AR-07  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-registration/code/`  
**Technical references**: `construction/agent-registration/nfr-design/nfr-design-patterns.md` (NP-AR-03)

---

### TC-AR-054 — Success is reported only after commit

**Context**: U4's durability guarantees apply to registrations (NFR-AR-08).

**Scenario**: A fault injected before commit.

**Preconditions**:
- A test environment store from `pnpm db:test` (PostgreSQL 18), migrated through `0002_registrations.sql` by the shared runner, with the app and migrator roles

**Steps**:
1. Register with a fault injected after the inserts and before commit

**Expected outcome**: `unavailable`; no row; no `200` was sent.

**Scope**: negative · **Priority**: High  
**Source**: agent-registration / NFR-AR-08 (PF §10)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-registration/code/`  
**Technical references**: `construction/agent-registration/nfr-requirements/nfr-requirements.md` (NFR-AR-08)

---

### TC-AR-055 — S2's README documents backup and restore

**Context**: The procedure, and that the dump holds human identifiers (NFR-AR-09).

**Scenario**: A docs test over `services/control-gateway/README.md`.

**Preconditions**:
- The README

**Steps**:
1. Read its *Operations* section

**Expected outcome**: It names `pnpm stack:backup` and `pnpm stack:restore`, the path `deploy/local/.backups/`, mode `0600`, says the dump contains human identifiers, and that it never goes into the repository.

**Scope**: happy-path · **Priority**: Medium  
**Source**: agent-registration / NFR-AR-09  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-registration/code/`  
**Technical references**: `construction/agent-registration/nfr-requirements/nfr-requirements.md` (NFR-AR-09); `construction/agent-registration/nfr-design/nfr-design-patterns.md` (NP-AR-08)

---

### TC-AR-056 — The backup path is git-ignored, and the dump and its directory have restrictive modes

**Context**: The dump holds human identifiers (NFR-AR-09).

**Scenario**: A backup taken on the stack.

**Preconditions**:
- E's control-gateway is running on the local stack. H holds a live credential for E and holds `agent:register`, `event:publish`, `event:subscribe` (self-granted), with `grant:human` and `human:manage` (configuration)

**Steps**:
1. Run `pnpm stack:backup e`
2. Check the file and directory modes
3. Run `git check-ignore` on the file

**Expected outcome**: File `0600`, directory `0700`; `git check-ignore` succeeds; `.dockerignore` also excludes the path.

**Scope**: negative · **Priority**: High  
**Source**: agent-registration / NFR-AR-09  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-registration/code/`  
**Technical references**: `construction/agent-registration/nfr-requirements/nfr-requirements.md` (NFR-AR-09); `construction/agent-registration/nfr-design/nfr-design-patterns.md` (NP-AR-08)

---

### TC-AR-057 — The backup and restore services mount only `backup/`, and hold no password

**Context**: The Compose-model test over the four services (NFR-AR-09, 10; the user's additions).

**Scenario**: `docker compose config` read by U4's Compose-model test.

**Preconditions**:
- `deploy/local/compose.yaml`; `env.sh`

**Steps**:
1. For `e-backup`, `e-restore`, `e2-backup`, `e2-restore`: read profile, networks, volumes, environment, command, entrypoint
2. Read `env.sh`'s copies

**Expected outcome**: Each is under profile `backup`, on its own environment's network only, mounts only `backup/` of its own environment's secrets volume (plus a `tmpfs`), has `PGPASSFILE` as its only variable, and no value from `.secrets/` anywhere. `env.sh` copies `backup` as uid 999 with the migrator password and the CA only.

**Scope**: negative · **Priority**: High  
**Source**: agent-registration / NFR-AR-09, 10  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-registration/code/`  
**Technical references**: `construction/agent-registration/nfr-design/nfr-design-patterns.md` (NP-AR-08); `construction/agent-registration/nfr-design/logical-components.md` (§5)

---

### TC-AR-058 — A restore round trip preserves everything, applies no migration, and keeps the grants

**Context**: The data round trip in the `db:test` harness, with the user's additions (NFR-AR-10; NP-AR-09 (1)).

**Scenario**: Seeded store A dumped and restored into empty store B.

**Preconditions**:
- A test environment store from `pnpm db:test` (PostgreSQL 18), migrated through `0002_registrations.sql` by the shared runner, with the app and migrator roles

**Steps**:
1. Seed A; dump to a temporary path; restore into empty B
2. Compare B with A
3. Run the migration runner against B
4. Run TC-EHA-080 and TC-AR-027 against B
5. Clean up

**Expected outcome**: Every registration attribute, secret digest, and attribution record equal; the runner applies nothing; both privilege tests pass; A, B, and the temporary path are removed, and the path no longer exists, pass or fail.

**Scope**: happy-path · **Priority**: High  
**Source**: agent-registration / NFR-AR-10  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-registration/code/`  
**Technical references**: `construction/agent-registration/nfr-requirements/nfr-requirements.md` (NFR-AR-10); `construction/agent-registration/nfr-design/nfr-design-patterns.md` (NP-AR-09)

---

### TC-AR-059 — Backup and restore on the stack

**Context**: The stack step in CI's stack job (NP-AR-09 (2)).

**Scenario**: E backed up, its store emptied, restored.

**Preconditions**:
- E's control-gateway is running on the local stack. H holds a live credential for E and holds `agent:register`, `event:publish`, `event:subscribe` (self-granted), with `grant:human` and `human:manage` (configuration)

**Steps**:
1. `stack:backup e`; check mode and git-ignore
2. Remove `e`'s store volume; start `env-db-e` alone
3. `stack:restore e {file}`
4. Run `e-migrate`
5. Run the privilege test; start the rest of `e`; re-run the smoke test's registration part; delete the file

**Expected outcome**: Restore succeeds into the empty store; `e-migrate` applies nothing; the privilege test passes; registrations from before the backup are present.

**Scope**: happy-path · **Priority**: High  
**Source**: agent-registration / NFR-AR-10  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-registration/code/`  
**Technical references**: `construction/agent-registration/nfr-design/nfr-design-patterns.md` (NP-AR-09)

---

### TC-AR-060 — Every backup passes the archive validity check; damaged archives fail it

**Context**: A dump damaged in transit is caught (the user's replacement for a checksum test; NP-AR-09 (3)).

**Scenario**: `stack:backup`'s check, and two damaged files.

**Preconditions**:
- E's control-gateway is running on the local stack. H holds a live credential for E and holds `agent:register`, `event:publish`, `event:subscribe` (self-granted), with `grant:human` and `human:manage` (configuration)

**Steps**:
1. Take a backup
2. Prepend a line to a copy and run the check
3. Truncate a copy by one byte at the end and run the check

**Expected outcome**: Step 1: the file begins `PGDMP` and `pg_restore --list` exits 0. Step 2 fails the magic check; step 3 fails `pg_restore --list`; each failing backup deletes its file.

**Scope**: negative · **Priority**: High  
**Source**: agent-registration / NFR-AR-09  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-registration/code/`  
**Technical references**: `construction/agent-registration/nfr-design/nfr-design-patterns.md` (NP-AR-08, 09)

---

### TC-AR-061 — The Build and Test summary states U5's residuals

**Context**: Residuals are stated, not hidden (NFR-AR-11, 13; business-rules §16).

**Scenario**: A reviewer reads the Build and Test summary.

**Preconditions**:
- Build and Test

**Steps**:
1. Read the summary

**Expected outcome**: It lists: no registration bound in M1; the volume loss without a backup; identifier existence learnable within E; a registration made by mistake not removable; each active secret a separate way in.

**Scope**: happy-path · **Priority**: Medium  
**Source**: agent-registration / NFR-AR-11, 13  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-registration/code/`  
**Technical references**: `construction/agent-registration/nfr-requirements/nfr-requirements.md` (NFR-AR-11, 13); `construction/agent-registration/functional-design/business-rules.md` (§16)

---

### TC-AR-062 — S2's throttle covers both operations

**Context**: 64 in flight per instance, then 503 (NFR-AR-12; U4 NFR-EHA-04).

**Scenario**: U4's throttle test with registrations among the requests.

**Preconditions**:
- E's control-gateway is running on the local stack. H holds a live credential for E and holds `agent:register`, `event:publish`, `event:subscribe` (self-granted), with `grant:human` and `human:manage` (configuration)

**Steps**:
1. Hold 64 slots; send a registration and an issuance

**Expected outcome**: Both `unavailable` (503, `Retry-After`) after the 1-second wait; nothing written.

**Scope**: negative · **Priority**: Medium  
**Source**: agent-registration / NFR-AR-12  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-registration/code/`  
**Technical references**: `construction/agent-registration/nfr-requirements/nfr-requirements.md` (NFR-AR-12)

---

### TC-AR-063 — The body bound admits a maximal registration and refuses one byte more than 16 KiB

**Context**: 16 KiB on every route (NFR-AR-14).

**Scenario**: Two bodies.

**Preconditions**:
- E's control-gateway is running on the local stack. H holds a live credential for E and holds `agent:register`, `event:publish`, `event:subscribe` (self-granted), with `grant:human` and `human:manage` (configuration)

**Steps**:
1. Send a valid body with a 64-character `agent` and 32 identifiers in each set
2. Send a 16 KiB + 1 byte body

**Expected outcome**: Step 1 is decided by the rules, not the size; step 2 is `payload_too_large`.

**Scope**: edge-boundary · **Priority**: Medium  
**Source**: agent-registration / NFR-AR-14  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-registration/code/`  
**Technical references**: `construction/agent-registration/nfr-requirements/nfr-requirements.md` (NFR-AR-14)

---

### TC-AR-064 — The p95 of both operations is reported

**Context**: No latency target; reported beside U4's (NFR-AR-15).

**Scenario**: Measured on the running stack.

**Preconditions**:
- E's control-gateway is running on the local stack. H holds a live credential for E and holds `agent:register`, `event:publish`, `event:subscribe` (self-granted), with `grant:human` and `human:manage` (configuration)

**Steps**:
1. Run the latency measurement for both operations

**Expected outcome**: The p95 values appear in the Build and Test report, not gated.

**Scope**: happy-path · **Priority**: Low  
**Source**: agent-registration / NFR-AR-15  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-registration/code/`  
**Technical references**: `construction/agent-registration/nfr-requirements/nfr-requirements.md` (NFR-AR-15)

---

### TC-AR-065 — U3's admission benchmark is re-run with P4's agent-facts source

**Context**: The query's share of U3's budget (NFR-AR-16; TC-AE-040).

**Scenario**: `pnpm bench:admit` with P4's source.

**Preconditions**:
- U3's benchmark; a test store with registrations

**Steps**:
1. Run the benchmark

**Expected outcome**: The p99 is reported against NFR-AE-07, not gated.

**Scope**: happy-path · **Priority**: Low  
**Source**: agent-registration / NFR-AR-16  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-registration/code/`  
**Technical references**: `construction/agent-registration/nfr-requirements/nfr-requirements.md` (NFR-AR-16)

---

### TC-AR-066 — Each flow emits its security event, with no identifier or secret

**Context**: Named events (NFR-AR-18).

**Scenario**: Every operation and refusal.

**Preconditions**:
- E's control-gateway is running on the local stack. H holds a live credential for E and holds `agent:register`, `event:publish`, `event:subscribe` (self-granted), with `grant:human` and `human:manage` (configuration)

**Steps**:
1. Register; issue; trigger each refusal reason; capture events

**Expected outcome**: `registration.created`, `registration.refused`, `secret.issued`, `secret.refused`, each refusal with its reason; a human only as E's pseudonym; no secret or digest.

**Scope**: happy-path · **Priority**: Medium  
**Source**: agent-registration / NFR-AR-18  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-registration/code/`  
**Technical references**: `construction/agent-registration/nfr-requirements/nfr-requirements.md` (NFR-AR-18); `construction/agent-registration/nfr-design/nfr-design-patterns.md` (NP-AR-07)

---

### TC-AR-067 — The new alert rules validate and name only defined events

**Context**: Alert rules as files (NFR-AR-19).

**Scenario**: U2's alert-file format test.

**Preconditions**:
- `deploy/monitoring/alerts.yaml`

**Steps**:
1. Run the format test

**Expected outcome**: It passes; the three U5 rules name only events and reasons that exist.

**Scope**: happy-path · **Priority**: Low  
**Source**: agent-registration / NFR-AR-19  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-registration/code/`  
**Technical references**: `construction/agent-registration/nfr-requirements/nfr-requirements.md` (NFR-AR-19); `construction/agent-registration/nfr-design/nfr-design-patterns.md` (NP-AR-07)

---

### TC-AR-068 — U5 adds no dependency

**Context**: NFR-AR-20.

**Scenario**: The dependency checks.

**Preconditions**:
- The repository after U5

**Steps**:
1. Run `check:deps` and `pnpm audit`; diff the register

**Expected outcome**: Both pass; the register gains no row.

**Scope**: happy-path · **Priority**: Medium  
**Source**: agent-registration / NFR-AR-20  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-registration/code/`  
**Technical references**: `construction/agent-registration/nfr-requirements/nfr-requirements.md` (NFR-AR-20)

---

### TC-AR-069 — Timestamps come from the injected clock

**Context**: NFR-AR-22.

**Scenario**: A fixed clock.

**Preconditions**:
- A test environment store from `pnpm db:test` (PostgreSQL 18), migrated through `0002_registrations.sql` by the shared runner, with the app and migrator roles

**Steps**:
1. Register and issue with the clock at a fixed time

**Expected outcome**: `registeredAt` and `issuedAt` equal it.

**Scope**: happy-path · **Priority**: Low  
**Source**: agent-registration / NFR-AR-22  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-registration/code/`  
**Technical references**: `construction/agent-registration/nfr-requirements/nfr-requirements.md` (NFR-AR-22)

---

### TC-AR-070 — The store refuses rows breaking its constraints

**Context**: The tables' `CHECK`s and foreign key (NP-AR-01; Q5 A).

**Scenario**: Direct inserts as the migrator role.

**Preconditions**:
- A test environment store from `pnpm db:test` (PostgreSQL 18), migrated through `0002_registrations.sql` by the shared runner, with the app and migrator roles

**Steps**:
1. Insert a registration with standing not within its snapshot
2. One with a declaration not within standing
3. One with 33 standing entries
4. One with state `retired`
5. A secret with a 31-byte digest
6. A secret naming no registration
7. A secret naming E's `a` under E2's identity

**Expected outcome**: Each fails with its constraint.

**Scope**: negative · **Priority**: High  
**Source**: agent-registration / NFR Design (NP-AR-01)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-registration/code/`  
**Technical references**: `construction/agent-registration/nfr-design/nfr-design-patterns.md` (NP-AR-01)

---

### TC-AR-071 — U2's code checks pass over U5's code

**Context**: The `sql`, `compare`, and CSPRNG rules (NFR-AR-05; NP-AR-01, 02).

**Scenario**: The checks over the changed packages.

**Preconditions**:
- U5's code

**Steps**:
1. Run the `sql` and `compare` checks
2. Search for randomness not from `crypto.randomBytes`

**Expected outcome**: Both checks pass; every digest comparison is `timingSafeEqual`; no other randomness.

**Scope**: negative · **Priority**: High  
**Source**: agent-registration / NFR-AR-05  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-registration/code/`  
**Technical references**: `construction/agent-registration/nfr-requirements/nfr-requirements.md` (NFR-AR-05); `construction/agent-registration/nfr-design/nfr-design-patterns.md` (NP-AR-02)

---

### TC-AR-072 — Only the registrations primary-key violation maps to `registration_exists`

**Context**: Any other error is `unavailable` (NP-AR-06).

**Scenario**: A fault raising another unique violation.

**Preconditions**:
- A test environment store from `pnpm db:test` (PostgreSQL 18), migrated through `0002_registrations.sql` by the shared runner, with the app and migrator roles

**Steps**:
1. Register with a fault raising SQLSTATE `23505` on another constraint

**Expected outcome**: `unavailable`, not `registration_exists`; nothing written.

**Scope**: negative · **Priority**: Medium  
**Source**: agent-registration / NFR Design (NP-AR-06)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-registration/code/`  
**Technical references**: `construction/agent-registration/nfr-design/nfr-design-patterns.md` (NP-AR-06)

---
