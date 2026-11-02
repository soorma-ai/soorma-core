# Test Specifications (Narrative): agent-credentials

**Unit**: `agent-credentials` (U6: agent credentials and the revocation read, data face)  
**Unit abbreviation**: AC = agent-credentials  
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

### TC-AC-001 — Bootstrap returns a short-lived credential bound to the registration and E

**Context**: *Done when* 2, part 1: an instance exchanges a locally verified secret for a short-lived credential (M1-FR-05), by raw call.

**Scenario**: An instance of A bootstraps with a raw HTTP call.

**Preconditions**:
- E's data-gateway is running. A is registered in E, with a secret issued

**Steps**:
1. Call `exchangeBootstrap` with A's registration reference, the secret, and an instance identifier

**Expected outcome**: An agent credential is returned, bound to A, E and the instance, with an expiry.

**Scope**: happy-path · **Priority**: High  
**Source**: agent-credentials / M1-FR-05  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-credentials/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

---

### TC-AC-002 — The instance identifier is recorded, not verified

**Context**: The instance identifier is asserted and recorded, not verified (M1-FR-05).

**Scenario**: Two instances of A bootstrap with different instance identifiers.

**Preconditions**:
- E's data-gateway is running. A is registered in E, with a secret issued

**Steps**:
1. Bootstrap with instance identifier `i-1`
2. Bootstrap with instance identifier `i-2`

**Expected outcome**: Both succeed. Each credential carries its asserted identifier.

**Scope**: happy-path · **Priority**: Medium  
**Source**: agent-credentials / M1-FR-05  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-credentials/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

---

### TC-AC-003 — A valid credential is renewed

**Context**: *Done when* 2, part 2: credential renewal (M1-FR-06), by raw call.

**Scenario**: The instance renews before expiry.

**Preconditions**:
- E's data-gateway is running. A is registered in E, with a secret issued
- The instance holds a live agent credential

**Steps**:
1. Call `renewAgentCredential`, presenting it

**Expected outcome**: A replacement credential is returned, with the same binding and a later expiry.

**Scope**: happy-path · **Priority**: High  
**Source**: agent-credentials / M1-FR-06  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-credentials/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

---

### TC-AC-004 — Bootstrap and renewal carry no envelope

**Context**: Neither call carries an envelope: the GAP-INT-008 work-around, option 1, in U6's inherited gaps.

**Scenario**: Bootstrap and renewal are made with no envelope.

**Preconditions**:
- E's data-gateway is running. A is registered in E, with a secret issued

**Steps**:
1. Bootstrap with no envelope
2. Renew with no envelope

**Expected outcome**: Both succeed.

**Scope**: happy-path · **Priority**: Medium  
**Source**: agent-credentials / M1-FR-05, M1-FR-06 (GAP-INT-008)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-credentials/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

---

### TC-AC-005 — Bootstrap and renewal are attributed

**Context**: Both are platform-resource operations, so each produces an attribution record (M1-FR-12, in U6).

**Scenario**: A reviewer inspects attribution after one bootstrap and one renewal.

**Preconditions**:
- E's data-gateway is running. A is registered in E, with a secret issued
- One bootstrap and one renewal have been performed

**Steps**:
1. Read the attribution records for both

**Expected outcome**: Each has a record with scope E, naming A's instance.

**Scope**: happy-path · **Priority**: Medium  
**Source**: agent-credentials / M1-FR-12  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-credentials/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

---

### TC-AC-006 — An unrevoked credential passes the revocation read

**Context**: Revocation state is read on every request (M1-FR-07).

**Scenario**: The instance renews with a credential that is not revoked.

**Preconditions**:
- E's data-gateway is running. A is registered in E, with a secret issued
- The instance holds a live, unrevoked credential

**Steps**:
1. Call `renewAgentCredential`

**Expected outcome**: Succeeds.

**Scope**: happy-path · **Priority**: High  
**Source**: agent-credentials / M1-FR-07  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-credentials/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

---

### TC-AC-007 — A wrong secret is refused, and the failure recorded against the registration

**Context**: Bootstrap is an unauthenticated surface, and failed attempts are recorded against the registration (M1-FR-05).

**Scenario**: Someone bootstraps A with a wrong secret.

**Preconditions**:
- E's data-gateway is running. A is registered in E, with a secret issued

**Steps**:
1. Call `exchangeBootstrap` for A with a wrong secret
2. Inspect A's failed-attempt record

**Expected outcome**: Refused. One failure is recorded against A.

**Scope**: negative · **Priority**: High  
**Source**: agent-credentials / M1-FR-05  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-credentials/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

---

### TC-AC-008 — Bootstrap attempts beyond the bound are refused

**Context**: Attempt volume per registration is bounded (M1-FR-05). Its value and shape come from U6's NFR Requirements.

**Scenario**: Repeated wrong attempts for A exceed the bound.

**Preconditions**:
- E's data-gateway is running. A is registered in E, with a secret issued
- The bootstrap attempt bound from U6's NFR Requirements

**Steps**:
1. Make wrong-secret attempts for A up to the bound
2. Attempt once more with the correct secret

**Expected outcome**: Further attempts are handled as the bound's shape defines, refused while it applies. Each refusal is recorded.

**Scope**: negative · **Priority**: High  
**Source**: agent-credentials / M1-FR-05  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-credentials/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

---

### TC-AC-009 — A revoked credential is refused at renewal

**Context**: O3 refuses a revoked credential. Agent revocation is seeded through the test-only path, since initiation is absent (M1-FR-07).

**Scenario**: The instance's credential is revoked, then renewal is attempted.

**Preconditions**:
- E's data-gateway is running. A is registered in E, with a secret issued
- The instance holds a live credential
- Test-only revocation seeding is available

**Steps**:
1. Seed revocation for the credential
2. Wait for the bound to elapse
3. Call `renewAgentCredential`

**Expected outcome**: Refused.

**Scope**: negative · **Priority**: High  
**Source**: agent-credentials / M1-FR-07, M1-FR-06  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-credentials/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

---

### TC-AC-010 — Unconfirmable revocation state fails closed

**Context**: Past the propagation bound, the perimeter denies (M1-FR-07).

**Scenario**: E's revocation state is unreachable for longer than the bound.

**Preconditions**:
- E's data-gateway is running. A is registered in E, with a secret issued
- The instance holds a live credential
- E's revocation state is unreachable for longer than the bound

**Steps**:
1. Call `renewAgentCredential`

**Expected outcome**: Refused.

**Scope**: negative · **Priority**: High  
**Source**: agent-credentials / M1-FR-07  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-credentials/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

---

### TC-AC-011 — An expired credential cannot be renewed; the instance re-bootstraps

**Context**: A lapsed instance re-bootstraps (M1-FR-06).

**Scenario**: The instance tries to renew after expiry.

**Preconditions**:
- E's data-gateway is running. A is registered in E, with a secret issued
- The instance's credential has expired

**Steps**:
1. Call `renewAgentCredential` with it
2. Call `exchangeBootstrap` with the secret

**Expected outcome**: Renewal is refused, and bootstrap succeeds.

**Scope**: negative · **Priority**: High  
**Source**: agent-credentials / M1-FR-06  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-credentials/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

---

### TC-AC-012 — A human credential is refused by kind

**Context**: The data gateway accepts no human credential, and refuses one by kind without verifying it (M1-FR-09, in U6).

**Scenario**: H presents an environment credential to the data gateway.

**Preconditions**:
- E's data-gateway is running. A is registered in E, with a secret issued
- H holds a credential for E

**Steps**:
1. Call `renewAgentCredential`, presenting H's environment credential

**Expected outcome**: Refused.

**Scope**: negative · **Priority**: High  
**Source**: agent-credentials / M1-FR-09  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-credentials/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

---

### TC-AC-013 — A credential from E2 is refused at E's data gateway

**Context**: Minting material is per environment, and nothing E2 mints is accepted by E (M1-FR-10).

**Scenario**: An instance with an agent credential from E2 renews at E.

**Preconditions**:
- E and E2 running
- An agent registered in E2 with a live credential from E2

**Steps**:
1. Call `renewAgentCredential` at E with the E2 credential

**Expected outcome**: Refused.

**Scope**: negative · **Priority**: High  
**Source**: agent-credentials / M1-FR-10, M1-FR-09  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-credentials/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

---

### TC-AC-014 — Bootstrap for an unknown registration is refused

**Context**: The secret must be bound to a registered logical agent in E (M1-FR-05).

**Scenario**: Bootstrap names a registration that does not exist in E.

**Preconditions**:
- E's data-gateway is running. A is registered in E, with a secret issued

**Steps**:
1. Call `exchangeBootstrap` with an unknown reference and any secret

**Expected outcome**: Refused, without disclosing whether the reference exists.

**Scope**: negative · **Priority**: Medium  
**Source**: agent-credentials / M1-FR-05  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-credentials/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

---

### TC-AC-015 — A change of revocation state takes effect within the bound

**Context**: Revocation state is cached for at most the published bound (M1-FR-07).

**Scenario**: A credential is revoked while the perimeter holds a cached not-revoked answer.

**Preconditions**:
- E's data-gateway is running. A is registered in E, with a secret issued
- The instance holds a live credential and has just renewed, so the cache is warm

**Steps**:
1. Seed revocation for the credential
2. Renew repeatedly until refused, recording the elapsed time

**Expected outcome**: Renewal is refused no later than the bound after seeding.

**Scope**: edge-boundary · **Priority**: High  
**Source**: agent-credentials / M1-FR-07  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-credentials/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

---

### TC-AC-016 — Renewal is never a weaker check than issuance

**Context**: Renewal is never a weaker check than issuance (M1-FR-06).

**Scenario**: A credential is renewed, and its binding compared with the original.

**Preconditions**:
- E's data-gateway is running. A is registered in E, with a secret issued
- The instance holds a live credential

**Steps**:
1. Renew
2. Compare the binding and claims of the original and the replacement

**Expected outcome**: The binding is identical (registration, E, instance), with no widened claim.

**Scope**: edge-boundary · **Priority**: High  
**Source**: agent-credentials / M1-FR-06  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-credentials/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

---

### TC-AC-017 — Bootstrap and renewal keep working while the organization level is down

**Context**: The data gateway has no organization-level dependency, so agent data-plane traffic is unaffected by its outage (U6 in unit-of-work.md; M1-NFR-08).

**Scenario**: The organization level is stopped.

**Preconditions**:
- E's data-gateway is running. A is registered in E, with a secret issued
- The organization level is stopped

**Steps**:
1. Bootstrap an instance of A
2. Renew its credential

**Expected outcome**: Both succeed.

**Scope**: edge-boundary · **Priority**: High  
**Source**: agent-credentials / M1-FR-05, M1-FR-06 (M1-NFR-08)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-credentials/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

---

### TC-AC-018 — No edge operation exposes revocation state

**Context**: Revocation state is readable by no principal (M1-FR-07).

**Scenario**: A reviewer inspects every edge document for an operation reading revocation state.

**Preconditions**:
- All OpenAPI documents in `contract/` present at U6

**Steps**:
1. List every operation
2. Look for any that returns revocation state

**Expected outcome**: None does.

**Scope**: edge-boundary · **Priority**: High  
**Source**: agent-credentials / M1-FR-07  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-credentials/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

---

### TC-AC-019 — The internal revocation read writes no attribution record

**Context**: U6's internal revocation read writes no attribution record: the GAP-INT-009 work-around, in U6's inherited gaps.

**Scenario**: A reviewer counts attribution records across one renewal.

**Preconditions**:
- E's data-gateway is running. A is registered in E, with a secret issued
- The instance holds a live credential

**Steps**:
1. Note the attribution record count
2. Renew once, which also reads revocation state
3. Count again

**Expected outcome**: Exactly one new record, for the renewal. None for the revocation read.

**Scope**: edge-boundary · **Priority**: Medium  
**Source**: agent-credentials / M1-FR-12 (GAP-INT-009)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-credentials/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

---

### TC-AC-020 — E's credentials are verified only with E's own material

**Context**: Minting material is per environment and never shared (M1-FR-10).

**Scenario**: A reviewer inspects E's and E2's minting material.

**Preconditions**:
- E and E2 deployed

**Steps**:
1. Read the material identifier in each environment's configuration and store

**Expected outcome**: The two differ, and neither environment holds the other's.

**Scope**: edge-boundary · **Priority**: High  
**Source**: agent-credentials / M1-FR-10  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-credentials/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

---

### TC-AC-021 — This unit's operations are defined in the contract and validated against it

**Context**: Each surface unit adds its own operations to the wire contract (unit-of-work.md, Q1 B). A raw caller that never links the SDK reaches identical enforcement (M1-FR-02).

**Scenario**: A reviewer checks the unit's operations in `contract/data-gateway.openapi.yaml`, then sends a request that violates the schema.

**Preconditions**:
- `contract/data-gateway.openapi.yaml` after this unit's Code Generation

**Steps**:
1. List the operations in `contract/data-gateway.openapi.yaml` and compare them with this unit's operations: `exchangeBootstrap`, `renewAgentCredential` (neither with an envelope)
2. Check that each references the shared conventions (versioning, error model, security schemes)
3. Send one request with a body that violates its operation's schema

**Expected outcome**: Every one of the unit's operations is present and references the conventions. The violating request is rejected with the contract's error model before any processing.

**Scope**: happy-path · **Priority**: High  
**Source**: agent-credentials / M1-FR-02  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-credentials/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

---

### TC-AC-022 — Bootstrap material of an unsupported type is rejected

**Context**: The identity-resolution boundary's agent half accepts the locally verified registration secret only in M1 (M1-FR-13).

**Scenario**: A caller presents a different material type for A at bootstrap.

**Preconditions**:
- E's data-gateway is running. A is registered in E, with a secret issued

**Steps**:
1. Call `exchangeBootstrap` for A, declaring a material type other than a registration secret

**Expected outcome**: Rejected as unsupported. No credential is issued, and the failure is recorded against A.

**Scope**: negative · **Priority**: Medium  
**Source**: agent-credentials / M1-FR-13  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-credentials/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

---
