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
| **the bound** | The published revocation propagation bound (M1-FR-07). Its value is set at NFR Requirements. *(Construction pass)* **B = 60 seconds**; the credential's lifetime **L = 15 minutes**; a lineage's maximum age **M = 24 hours**: code constants (NFR-AC-01 to 03; NP-AC-01) |
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

**Expected outcome**: An agent credential is returned, bound to A, E and the instance, with an expiry. *(Construction pass)* `200` from `POST /agent-credentials` with the body `{ agent: A, secret: <A's soorma_rs_ value>, instance: i-1 }` and no credential header; the response body is `{ credential, agent: A, environment: E's three parts, instance: i-1, expiresAt }`, with `Cache-Control: no-store`. The `soorma_ac_` token's header is `typ` `soorma-ac+jwt`, `alg` `Ed25519`; its claims are `env`, `sub` A, `inst` i-1, `cid`, `jti`, `iat`, `exp`, with `exp` at most 15 minutes after `iat`. An `agent_credentials` row holds the `cid`, E, A, i-1, the secret's id, and `lineage_ends_at` = `issued_at` + 24 hours. The full *done when* 2 proof by raw calls is TC-AC-093.

**Scope**: happy-path · **Priority**: High  
**Source**: agent-credentials / M1-FR-05  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-credentials/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; construction pass: `construction/agent-credentials/functional-design/business-rules.md` (BR-BS-06; D-AC-13, 24); `construction/agent-credentials/nfr-requirements/nfr-requirements.md` (NFR-AC-02, 03); `construction/agent-credentials/nfr-design/nfr-design-patterns.md` (NP-AC-03, 09)

---

### TC-AC-002 — The instance identifier is recorded, not verified

**Context**: The instance identifier is asserted and recorded, not verified (M1-FR-05).

**Scenario**: Two instances of A bootstrap with different instance identifiers.

**Preconditions**:
- E's data-gateway is running. A is registered in E, with a secret issued

**Steps**:
1. Bootstrap with instance identifier `i-1`
2. Bootstrap with instance identifier `i-2`

**Expected outcome**: Both succeed. Each credential carries its asserted identifier. *(Construction pass)* Both `200`; the tokens' `inst` claims are `i-1` and `i-2`, and their rows have distinct `cid`s. Nothing checks or derives the identifier (D-AC-23). An identifier shared by two live credentials: TC-AC-024.

**Scope**: happy-path · **Priority**: Medium  
**Source**: agent-credentials / M1-FR-05  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-credentials/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; construction pass: `construction/agent-credentials/functional-design/business-rules.md` (D-AC-07, 23)

---

### TC-AC-003 — A valid credential is renewed

**Context**: *Done when* 2, part 2: credential renewal (M1-FR-06), by raw call.

**Scenario**: The instance renews before expiry.

**Preconditions**:
- E's data-gateway is running. A is registered in E, with a secret issued
- The instance holds a live agent credential

**Steps**:
1. Call `renewAgentCredential`, presenting it

**Expected outcome**: A replacement credential is returned, with the same binding and a later expiry. *(Construction pass)* `POST /agent-credentials/current/renewal` with `Authorization: Bearer soorma_ac_…` and no body: `200`; the new token has the same `cid`, `sub`, `inst`, and `env`, a new `jti`, and `exp` = min(now + 15 minutes, the lineage end); the row's `expires_at` moves to it.

**Scope**: happy-path · **Priority**: High  
**Source**: agent-credentials / M1-FR-06  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-credentials/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; construction pass: `construction/agent-credentials/functional-design/business-rules.md` (BR-RN-01 to 08; D-AC-14, 15)

---

### TC-AC-004 — Bootstrap and renewal carry no envelope

**Context**: Neither call carries an envelope: the GAP-INT-008 work-around, option 1, in U6's inherited gaps.

**Scenario**: Bootstrap and renewal are made with no envelope.

**Preconditions**:
- E's data-gateway is running. A is registered in E, with a secret issued

**Steps**:
1. Bootstrap with no envelope
2. Renew with no envelope

**Expected outcome**: Both succeed. *(Construction pass)* The bootstrap body is exactly `{ agent, secret, instance }` and renewal has no body; neither response carries an envelope or any envelope field. A draft envelope in the bootstrap body is refused: TC-AC-037.

**Scope**: happy-path · **Priority**: Medium  
**Source**: agent-credentials / M1-FR-05, M1-FR-06 (GAP-INT-008)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-credentials/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; construction pass: `construction/agent-credentials/functional-design/business-rules.md` (D-AC-28; BR-BQ-01; BR-RN-05)

---

### TC-AC-005 — Bootstrap and renewal are attributed

**Context**: Both are platform-resource operations, so each produces an attribution record (M1-FR-12, in U6).

**Scenario**: A reviewer inspects attribution after one bootstrap and one renewal.

**Preconditions**:
- E's data-gateway is running. A is registered in E, with a secret issued
- One bootstrap and one renewal have been performed

**Steps**:
1. Read the attribution records for both

**Expected outcome**: Each has a record with scope E, naming A's instance. *(Construction pass)* One `attribution_records` row per operation, written in the same transaction as the credential: operation `exchangeBootstrap`, then `renewAgentCredential`; `actor_kind` `agent`; `registration` A; `instance` i-1; `sponsor` H; `credential_id` empty at bootstrap and the presented `cid` at renewal; target the `cid`; scope E; `chain`, `origin`, and the re-broadening columns null. Reading them from the record alone: TC-AC-035.

**Scope**: happy-path · **Priority**: Medium  
**Source**: agent-credentials / M1-FR-12  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-credentials/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; construction pass: `construction/agent-credentials/functional-design/business-rules.md` (BR-AT-AC-01, 02; D-AC-21)

---

### TC-AC-006 — An unrevoked credential passes the revocation read

**Context**: Revocation state is read on every request (M1-FR-07).

**Scenario**: The instance renews with a credential that is not revoked.

**Preconditions**:
- E's data-gateway is running. A is registered in E, with a secret issued
- The instance holds a live, unrevoked credential

**Steps**:
1. Call `renewAgentCredential`

**Expected outcome**: Succeeds. *(Construction pass)* `200`. At S3 the revocation read is the **direct** source, one statement over both granularities inside renewal's transaction (D-AC-01); it answers `not_revoked`. The cache's behaviour is tested in P5 (TC-AC-054, 065) and wired at S4 by U7.

**Scope**: happy-path · **Priority**: High  
**Source**: agent-credentials / M1-FR-07  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-credentials/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; construction pass: `construction/agent-credentials/functional-design/business-rules.md` (D-AC-01; BR-RN-03); `construction/agent-credentials/nfr-design/nfr-design-patterns.md` (NP-AC-04)

---

### TC-AC-007 — A wrong secret is refused, and the failure recorded against the registration

**Context**: Bootstrap is an unauthenticated surface, and failed attempts are recorded against the registration (M1-FR-05).

**Scenario**: Someone bootstraps A with a wrong secret.

**Preconditions**:
- E's data-gateway is running. A is registered in E, with a secret issued

**Steps**:
1. Call `exchangeBootstrap` for A with a wrong secret
2. Inspect A's failed-attempt record

**Expected outcome**: Refused. One failure is recorded against A. *(Construction pass)* `authentication_failed` (403), with no detail and no `WWW-Authenticate`. A `failed_bootstrap_attempts` row for A (reason `secret_mismatch`, `refused_by_bound` false) is written off the response path; the bound is settled as a failure; the security log has `bootstrap.refused` with reason `secret_mismatch`, and no secret, secret id, or digest.

**Scope**: negative · **Priority**: High  
**Source**: agent-credentials / M1-FR-05  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-credentials/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; construction pass: `construction/agent-credentials/functional-design/business-rules.md` (BR-BS-03; D-AC-05, 22); `construction/agent-credentials/nfr-requirements/nfr-requirements.md` (NFR-AC-11, 22)

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

**Expected outcome**: Further attempts are handled as the bound's shape defines, refused while it applies. Each refusal is recorded. *(Construction pass)* With the injected clock and NFR-AC-06 to 08's values: from the 10th consecutive failure, each attempt waits 1, 2, 4 … seconds, capped at 60; at most 60 attempts are live in any 60 seconds. A refused attempt is `too_many_attempts` (429) with `Retry-After` = the later wait, and a row with `refused_by_bound` true. The correct secret presented while refused is refused the same way; after `Retry-After` it succeeds.

**Scope**: negative · **Priority**: High  
**Source**: agent-credentials / M1-FR-05  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-credentials/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; construction pass: `construction/agent-credentials/nfr-requirements/nfr-requirements.md` (NFR-AC-06 to 10); `construction/agent-credentials/nfr-design/nfr-design-patterns.md` (NP-AC-07)

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

**Expected outcome**: Refused. *(Construction pass)* **Adjusted for D-AC-01**: step 2 does not wait. At S3, renewal reads revocation state directly, so it is `credential_refused` (401) at once after a `cid` revocation is seeded, and also after an agent revocation. The bound's timeline is TC-AC-054 (P5) and U7's at S4.

**Scope**: negative · **Priority**: High  
**Source**: agent-credentials / M1-FR-07, M1-FR-06  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-credentials/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; construction pass: `construction/agent-credentials/functional-design/business-rules.md` (D-AC-01, 16; BR-RN-03)

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

**Expected outcome**: Refused. *(Construction pass)* **Adjusted for D-AC-01**: at S3, with E's store unreachable, renewal is `unavailable` (503, `Retry-After: 5`) and nothing is written: S3 needs the store to write. Denial past B with a cached answer is tested in P5 (TC-AC-054) and at S4 by U7.

**Scope**: negative · **Priority**: High  
**Source**: agent-credentials / M1-FR-07  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-credentials/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; construction pass: `construction/agent-credentials/functional-design/business-rules.md` (D-AC-01; BR-RC-03); `construction/agent-credentials/nfr-requirements/nfr-requirements.md` (NFR-AC-14)

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

**Expected outcome**: Renewal is refused, and bootstrap succeeds. *(Construction pass)* Renewal with the expired token is `credential_expired` (401), decided only after its signature verifies; bootstrap with the secret then succeeds, with a new `cid`.

**Scope**: negative · **Priority**: High  
**Source**: agent-credentials / M1-FR-06  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-credentials/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; construction pass: `construction/agent-credentials/functional-design/business-rules.md` (BR-RN-09; BR-CR-AC-03); `construction/agent-credentials/nfr-requirements/nfr-requirements.md` (NFR-AC-18)

---

### TC-AC-012 — A human credential is refused by kind

**Context**: The data gateway accepts no human credential, and refuses one by kind without verifying it (M1-FR-09, in U6).

**Scenario**: H presents an environment credential to the data gateway.

**Preconditions**:
- E's data-gateway is running. A is registered in E, with a secret issued
- H holds a credential for E

**Steps**:
1. Call `renewAgentCredential`, presenting H's environment credential

**Expected outcome**: Refused. *(Construction pass)* At renewal, a `soorma_ec_` or `soorma_si_` credential is `credential_refused` (401) **without verifying**: S3 holds no human or organization material. At bootstrap, any `Authorization` header is `malformed_request` naming it (TC-AC-029). Every presenter row: TC-AC-039.

**Scope**: negative · **Priority**: High  
**Source**: agent-credentials / M1-FR-09  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-credentials/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; construction pass: `construction/agent-credentials/functional-design/business-rules.md` (D-AC-10; BR-PR-AC-02 to 04)

---

### TC-AC-013 — A credential from E2 is refused at E's data gateway

**Context**: Minting material is per environment, and nothing E2 mints is accepted by E (M1-FR-10).

**Scenario**: An instance with an agent credential from E2 renews at E.

**Preconditions**:
- E and E2 running
- An agent registered in E2 with a live credential from E2

**Steps**:
1. Call `renewAgentCredential` at E with the E2 credential

**Expected outcome**: Refused. *(Construction pass)* E2's agent credential at E's renewal is `credential_refused` (unknown `kid` or signature), so no expiry is disclosed; E2's secret at E's bootstrap is `authentication_failed`.

**Scope**: negative · **Priority**: High  
**Source**: agent-credentials / M1-FR-10, M1-FR-09  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-credentials/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; construction pass: `construction/agent-credentials/functional-design/business-rules.md` (BR-CR-AC-02; D-AC-32)

---

### TC-AC-014 — Bootstrap for an unknown registration is refused

**Context**: The secret must be bound to a registered logical agent in E (M1-FR-05).

**Scenario**: Bootstrap names a registration that does not exist in E.

**Preconditions**:
- E's data-gateway is running. A is registered in E, with a secret issued

**Steps**:
1. Call `exchangeBootstrap` with an unknown reference and any secret

**Expected outcome**: Refused, without disclosing whether the reference exists. *(Construction pass)* `authentication_failed`, identical to a wrong secret (TC-AC-048); no `failed_bootstrap_attempts` row (there is no registration to record it against); the bound still counts it.

**Scope**: negative · **Priority**: Medium  
**Source**: agent-credentials / M1-FR-05  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-credentials/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; construction pass: `construction/agent-credentials/functional-design/business-rules.md` (BR-BS-03, 07; BR-FA-01)

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

**Expected outcome**: Renewal is refused no later than the bound after seeding. *(Construction pass)* **Adjusted for D-AC-01**: measured in P5 with the injected clock (business-logic-model §5): with a `not_revoked` entry cached, a seeded revocation is answered `revoked` once the entry's age reaches B = 60 seconds, and never later. At S3 the next renewal is refused at once (TC-AC-009). At S4: U7.

**Scope**: edge-boundary · **Priority**: High  
**Source**: agent-credentials / M1-FR-07  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-credentials/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; construction pass: `construction/agent-credentials/functional-design/business-rules.md` (D-AC-01, 18); `construction/agent-credentials/nfr-requirements/nfr-requirements.md` (NFR-AC-01); `construction/agent-credentials/functional-design/business-logic-model.md` §5

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

**Expected outcome**: The binding is identical (registration, E, instance), with no widened claim. *(Construction pass)* The replacement's `sub`, `inst`, `env`, and `cid` equal the original's; only `jti`, `iat`, and `exp` differ; `exp` is never past the lineage end; no claim carries a permission.

**Scope**: edge-boundary · **Priority**: High  
**Source**: agent-credentials / M1-FR-06  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-credentials/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; construction pass: `construction/agent-credentials/functional-design/business-rules.md` (BR-RN-08; BR-CR-AC-01)

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

**Expected outcome**: Both succeed. *(Construction pass)* Run as Case 3 of `pnpm stack:outage`: with `org-gateway` stopped, (a) the running `e-data-gateway` serves a bootstrap and a renewal; (b) `e-data-gateway`, restarted while S1 is stopped, becomes healthy and serves both. U4's two cases are unchanged.

**Scope**: edge-boundary · **Priority**: High  
**Source**: agent-credentials / M1-FR-05, M1-FR-06 (M1-NFR-08)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-credentials/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; construction pass: `construction/agent-credentials/infrastructure-design/infrastructure-design.md` (§9; D-ID-AC-15); `construction/agent-credentials/functional-design/business-rules.md` (D-AC-11)

---

### TC-AC-018 — No edge operation exposes revocation state

**Context**: Revocation state is readable by no principal (M1-FR-07).

**Scenario**: A reviewer inspects every edge document for an operation reading revocation state.

**Preconditions**:
- All OpenAPI documents in `contract/` present at U6

**Steps**:
1. List every operation
2. Look for any that returns revocation state

**Expected outcome**: None does. *(Construction pass)* `contract/data-gateway.openapi.yaml` defines two operations only; no route reads, lists, or reveals revocation state; a revoked credential is plain `credential_refused` and a revoked agent at bootstrap is the one refusal.

**Scope**: edge-boundary · **Priority**: High  
**Source**: agent-credentials / M1-FR-07  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-credentials/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; construction pass: `construction/agent-credentials/functional-design/business-rules.md` (BR-RV-04; D-AC-16)

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

**Expected outcome**: Exactly one new record, for the renewal. None for the revocation read. *(Construction pass)* Exactly one new `attribution_records` row (operation `renewAgentCredential`); the direct revocation read writes none (rows counted before and after).

**Scope**: edge-boundary · **Priority**: Medium  
**Source**: agent-credentials / M1-FR-12 (GAP-INT-009)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-credentials/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; construction pass: `construction/agent-credentials/functional-design/business-rules.md` (D-AC-17; BR-RV-06)

---

### TC-AC-020 — E's credentials are verified only with E's own material

**Context**: Minting material is per environment and never shared (M1-FR-10).

**Scenario**: A reviewer inspects E's and E2's minting material.

**Preconditions**:
- E and E2 deployed

**Steps**:
1. Read the material identifier in each environment's configuration and store

**Expected outcome**: The two differ, and neither environment holds the other's. *(Construction pass)* E's and E2's agent signing keys are distinct files with distinct `kid`s; each S3 mounts only its own environment's (`data-gateway/`); a token minted by E fails at E2's S3.

**Scope**: edge-boundary · **Priority**: High  
**Source**: agent-credentials / M1-FR-10  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-credentials/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; construction pass: `construction/agent-credentials/functional-design/business-rules.md` (D-AC-03); `construction/agent-credentials/infrastructure-design/infrastructure-design.md` (D-ID-AC-05, 09)

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

**Expected outcome**: Every one of the unit's operations is present and references the conventions. The violating request is rejected with the contract's error model before any processing. *(Construction pass)* `contract/data-gateway.openapi.yaml`: `exchangeBootstrap` (no security scheme; a closed body) and `renewAgentCredential` (`agentCredential`; no body), referencing the shared components and conventions; a body failing the schema is `malformed_request` before any processing; S3's tests run the shared assertion on every Problem.

**Scope**: happy-path · **Priority**: High  
**Source**: agent-credentials / M1-FR-02  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-credentials/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; construction pass: `construction/agent-credentials/functional-design/business-rules.md` (§13; D-AC-24, 25)

---

### TC-AC-022 — Bootstrap material of an unsupported type is rejected

**Context**: The identity-resolution boundary's agent half accepts the locally verified registration secret only in M1 (M1-FR-13).

**Scenario**: A caller presents a different material type for A at bootstrap.

**Preconditions**:
- E's data-gateway is running. A is registered in E, with a secret issued

**Steps**:
1. Call `exchangeBootstrap` for A, declaring a material type other than a registration secret

**Expected outcome**: Rejected as unsupported. No credential is issued, and the failure is recorded against A. *(Construction pass)* A `secret` with another prefix (for example `soorma_em_`) is `authentication_failed`, after the bound; a `failed_bootstrap_attempts` row for A has reason `unsupported_material`.

**Scope**: negative · **Priority**: Medium  
**Source**: agent-credentials / M1-FR-13  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-credentials/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; construction pass: `construction/agent-credentials/functional-design/business-rules.md` (D-AC-04; BR-BS-01)

---

### TC-AC-023 — A lineage ends at M; renewal never extends past it

**Context**: A credential's lineage has a maximum age of 24 hours, after which the instance presents its secret again (D-AC-02).

**Scenario**: An instance renews up to and past its lineage end, with the injected clock.

**Preconditions**:
- E's data-gateway is running on the local stack. A is registered in E by H, with a secret issued
- The instance bootstrapped at T0

**Steps**:
1. Renew at T0 + 23:50
2. Renew at T0 + 23:58
3. Renew at T0 + 24:00
4. Bootstrap again

**Expected outcome**: Step 1: `exp` = T0 + 24:00 (capped). Step 2: `exp` still T0 + 24:00. Step 3: `credential_expired`. Step 4: `200`, a new `cid` and a new lineage end.

**Scope**: edge-boundary · **Priority**: High  
**Source**: agent-credentials / M1-FR-06 (D-AC-02)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-credentials/code/`  
**Technical references**: `construction/agent-credentials/functional-design/business-rules.md` (D-AC-02); `construction/agent-credentials/nfr-requirements/nfr-requirements.md` (NFR-AC-03)

---

### TC-AC-024 — Two live credentials may assert the same instance identifier

**Context**: The instance identifier is asserted, recorded, and never enforced unique (D-AC-07; I10).

**Scenario**: Two bootstraps of A both assert `i-1`.

**Preconditions**:
- E's data-gateway is running on the local stack. A is registered in E by H, with a secret issued

**Steps**:
1. Bootstrap A with `i-1`
2. Bootstrap A again with `i-1`
3. Renew both

**Expected outcome**: Both bootstraps `200`, with distinct `cid`s and `inst` `i-1`; both renewals `200`.

**Scope**: edge-boundary · **Priority**: Medium  
**Source**: agent-credentials / M1-FR-05 (D-AC-07)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-credentials/code/`  
**Technical references**: `construction/agent-credentials/functional-design/business-rules.md` (D-AC-07, 23)

---

### TC-AC-025 — A revoked agent cannot bootstrap, and its credentials cannot renew

**Context**: Revocation at the logical-agent granularity refuses every instance, present and future (BR-RV-01).

**Scenario**: An agent revocation for A is seeded through the test-only path.

**Preconditions**:
- E's data-gateway is running on the local stack. A is registered in E by H, with a secret issued
- An instance of A holds a live credential
- Test-only revocation seeding

**Steps**:
1. Seed an agent revocation for A
2. Renew the live credential
3. Bootstrap A with its secret

**Expected outcome**: Step 2: `credential_refused`. Step 3: `authentication_failed`, identical to any other cause; a failed-attempt row with reason `agent_revoked`.

**Scope**: negative · **Priority**: High  
**Source**: agent-credentials / M1-FR-07 (BR-RV-01)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-credentials/code/`  
**Technical references**: `construction/agent-credentials/functional-design/business-rules.md` (BR-BS-05; BR-RV-01)

---

### TC-AC-026 — The seam's agent half decides identity only

**Context**: The identity-resolution seam returns which registration the material is bound to; state, revocation, and what the credential asserts stay in core (D-AC-20).

**Scenario**: `packages/agent-identity` is called directly with valid and invalid material.

**Preconditions**:
- `packages/agent-identity`'s tests, against a test store

**Steps**:
1. Resolve a valid secret for A
2. Resolve it for a registration whose agent is revoked and for one not `registered` (seeded)
3. Resolve a wrong secret, an unknown id, and another registration's secret

**Expected outcome**: Step 1: `{ resolved: true, registration: { E, A }, secretId }`. Step 2: still `resolved: true` (the seam decides no state or revocation). Step 3: `{ resolved: false }` each time, the reason only through `onRejected`.

**Scope**: happy-path · **Priority**: High  
**Source**: agent-credentials / M1-FR-13 (D-AC-20)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-credentials/code/`  
**Technical references**: `construction/agent-credentials/functional-design/business-rules.md` (D-AC-20); `construction/agent-credentials/nfr-design/nfr-design-patterns.md` (NP-AC-08)

---

### TC-AC-027 — Renewal never consults the registration secret

**Context**: A secret's lifecycle is independent of any credential's (PF FR-008; D-AC-15).

**Scenario**: A credential is renewed while the store's statement log is captured.

**Preconditions**:
- The environment store's database tests (`pnpm db:test`), connected as the role the case names: `soorma_env_data`, with statement logging

**Steps**:
1. Bootstrap, then renew

**Expected outcome**: Renewal's statements touch `agent_credentials`, the revocation tables, `registrations`, and `attribution_records`, and never `registration_secrets`.

**Scope**: edge-boundary · **Priority**: Medium  
**Source**: agent-credentials / M1-FR-06 (D-AC-15)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-credentials/code/`  
**Technical references**: `construction/agent-credentials/functional-design/business-rules.md` (D-AC-15)

---

### TC-AC-028 — Revocation is terminal; reinstatement is a new issuance

**Context**: A revoked credential stays refused; a new bootstrap is a new `cid` (PF FR-011; D-AC-14).

**Scenario**: The instance's `cid` is revoked, then the instance bootstraps again.

**Preconditions**:
- E's data-gateway is running on the local stack. A is registered in E by H, with a secret issued
- Test-only revocation seeding

**Steps**:
1. Seed a revocation for the instance's `cid`
2. Renew with any token of that lineage
3. Bootstrap again
4. Renew the new credential

**Expected outcome**: Step 2: `credential_refused`. Step 3: `200`, a new `cid`. Step 4: `200`. The old lineage stays refused.

**Scope**: edge-boundary · **Priority**: High  
**Source**: agent-credentials / M1-FR-07 (BR-RV-02)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-credentials/code/`  
**Technical references**: `construction/agent-credentials/functional-design/business-rules.md` (BR-RV-02; D-AC-14)

---

### TC-AC-029 — Bootstrap refuses a credential header with `malformed_request`

**Context**: Bootstrap names no security scheme, so a credential header is malformed, never a 401 (BR-PR-AC-02).

**Scenario**: Bootstrap is called with credential headers.

**Preconditions**:
- E's data-gateway is running on the local stack. A is registered in E by H, with a secret issued

**Steps**:
1. Bootstrap with `Authorization: Bearer soorma_ac_x`
2. Bootstrap with a `Soorma-Delegation` header

**Expected outcome**: Each: `malformed_request` (400), `errors[]` naming the header, never `WWW-Authenticate`; nothing counted by the bound.

**Scope**: negative · **Priority**: Medium  
**Source**: agent-credentials / M1-FR-05 (BR-PR-AC-02)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-credentials/code/`  
**Technical references**: `construction/agent-credentials/functional-design/business-rules.md` (BR-PR-AC-02)

---

### TC-AC-030 — Any other path or method on S3 is a bare 404

**Context**: Deny by default (O9): only the contract's operations exist.

**Scenario**: Undefined routes are called.

**Preconditions**:
- E's data-gateway is running on the local stack. A is registered in E by H, with a secret issued

**Steps**:
1. `GET /agent-credentials`
2. `POST /revocations`
3. `DELETE /agent-credentials/current`

**Expected outcome**: Each: `404` with no body, with `Soorma-Contract-Version` and `Soorma-Request-Id`.

**Scope**: negative · **Priority**: Low  
**Source**: agent-credentials / M1-FR-09 (O9)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-credentials/code/`  
**Technical references**: `construction/agent-credentials/functional-design/business-rules.md` §10

---

### TC-AC-031 — The credential's environment is E's configured identity, whatever serves it

**Context**: Environment identity is configured, never inferred (O11; D-AC-09).

**Scenario**: S3 is reached through another hostname alias.

**Preconditions**:
- E's data-gateway is running on the local stack. A is registered in E by H, with a secret issued

**Steps**:
1. Bootstrap through `data-gateway.e.soorma.internal`
2. Bootstrap through the loopback edge

**Expected outcome**: Both tokens' `env` equal E's configured `{ organization, project, environment }`; nothing in the token or record names a host.

**Scope**: edge-boundary · **Priority**: Medium  
**Source**: agent-credentials / M1-FR-10 (O11)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-credentials/code/`  
**Technical references**: `construction/agent-credentials/functional-design/business-rules.md` (D-AC-09)

---

### TC-AC-032 — An agent without autonomy declared bootstraps and renews

**Context**: O12 does not apply to bootstrap or renewal (PF §8b; D-AC-28).

**Scenario**: C is registered without autonomy declared.

**Preconditions**:
- E's data-gateway is running on the local stack. A is registered in E by H, with a secret issued
- C registered in E without autonomy declared, with a secret

**Steps**:
1. Bootstrap C
2. Renew

**Expected outcome**: Both `200`.

**Scope**: edge-boundary · **Priority**: High  
**Source**: agent-credentials / M1-FR-05, 06 (O12 N/A)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-credentials/code/`  
**Technical references**: `construction/agent-credentials/functional-design/business-rules.md` (D-AC-28)

---

### TC-AC-033 — E's reads and writes never reach E2's rows, on every access path

**Context**: Isolation per access path (I1): every U6 table carries the environment, and every statement constrains on it.

**Scenario**: A test store holds E's and E2's rows with the same agent and ids.

**Preconditions**:
- The environment store's database tests (`pnpm db:test`), connected as the role the case names: `soorma_env_data`

**Steps**:
1. Read a credential record, a revocation, a slot, and the failed-attempt insert for E, with E2's rows present
2. Seed a revocation for E2's agent A

**Expected outcome**: Each read returns only E's row; E's renewal is unaffected by E2's revocation; the failed-attempt insert writes for E only.

**Scope**: negative · **Priority**: High  
**Source**: agent-credentials / M1-FR-10 (I1)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-credentials/code/`  
**Technical references**: `construction/agent-credentials/functional-design/invariant-coverage-matrix.md` (I1); `construction/agent-credentials/nfr-design/nfr-design-patterns.md` (NP-AC-03, 04, 07)

---

### TC-AC-034 — The cache key includes the environment

**Context**: Caches are keyed on environment (PF §6; BR-RC-04).

**Scenario**: One cache instance is asked about the same `cid` and agent in E and E2.

**Preconditions**:
- P5's cache tests, injected clock and source

**Steps**:
1. Answer `revoked` for (E2, c, A)
2. Ask for (E, c, A)

**Expected outcome**: Step 2 reads through to the source and answers E's state, never E2's cached answer.

**Scope**: edge-boundary · **Priority**: Medium  
**Source**: agent-credentials / M1-FR-10 (BR-RC-04)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-credentials/code/`  
**Technical references**: `construction/agent-credentials/functional-design/business-rules.md` (BR-RC-04); `construction/agent-credentials/nfr-design/nfr-design-patterns.md` (NP-AC-05)

---

### TC-AC-035 — A bootstrap's and a renewal's records say everything from the record alone

**Context**: I4: scope, actor, instance, sponsor, and why there is no chain or origin are recoverable from each record (BR-AT-AC-02).

**Scenario**: The attribution rows of TC-AC-005 are read alone.

**Preconditions**:
- The environment store's database tests (`pnpm db:test`), connected as the role the case names (owner, for reading)

**Steps**:
1. Read each row with nothing else
2. Force the attribution insert to fail inside bootstrap's transaction

**Expected outcome**: Step 1: scope, agent actor, registration, instance, and sponsor are present; `operation` is in P7's envelope-free list, so the empty envelope columns are by definition. Step 2: no `agent_credentials` row is left.

**Scope**: happy-path · **Priority**: High  
**Source**: agent-credentials / M1-FR-12 (I4)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-credentials/code/`  
**Technical references**: `construction/agent-credentials/functional-design/business-rules.md` (BR-AT-AC-01 to 03; D-AC-21)

---

### TC-AC-036 — An envelope-free operation's record cannot carry envelope facts

**Context**: D-AC-33: P7's writer and the store's `0004` CHECK refuse envelope facts on `exchangeBootstrap` and `renewAgentCredential`.

**Scenario**: Inconsistent records are written directly.

**Preconditions**:
- The environment store's database tests (`pnpm db:test`), connected as the role the case names: owner, after `0004`

**Steps**:
1. Write an `exchangeBootstrap` agent record with a chain through P7
2. Insert the same row directly
3. Insert a human-actor `renewAgentCredential` row

**Expected outcome**: Step 1: refused before any SQL. Steps 2, 3: refused by `attribution_envelope_free_operations`. U4's and U5's record tests pass unchanged.

**Scope**: negative · **Priority**: High  
**Source**: agent-credentials / M1-FR-12 (D-AC-33)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-credentials/code/`  
**Technical references**: `construction/agent-credentials/functional-design/business-rules.md` (D-AC-33); `construction/agent-credentials/nfr-design/nfr-design-patterns.md` (NP-AC-02)

---

### TC-AC-037 — A draft envelope in the bootstrap body is refused

**Context**: Neither operation carries an envelope (GAP-INT-008; D-AC-28).

**Scenario**: A bootstrap body adds envelope fields.

**Preconditions**:
- E's data-gateway is running on the local stack. A is registered in E by H, with a secret issued

**Steps**:
1. Bootstrap with an added `traceContext`
2. Bootstrap with an added `actorChain`

**Expected outcome**: Each: `malformed_request` with a pointer to the field; nothing counted.

**Scope**: negative · **Priority**: Medium  
**Source**: agent-credentials / M1-FR-01 (GAP-INT-008)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-credentials/code/`  
**Technical references**: `construction/agent-credentials/functional-design/business-rules.md` (BR-BQ-01; D-AC-28)

---

### TC-AC-038 — The contract publishes B, L, and M from the code's constants

**Context**: B is the platform's published bound; L and M are upper bounds with the client rules (NFR-AC-05; NP-AC-01).

**Scenario**: The docs test reads `credentials.md` and the constants.

**Preconditions**:
- The repository

**Steps**:
1. Read the *Revocation and Lifetimes* section
2. Compare with `PROPAGATION_BOUND_MS`, `AGENT_CREDENTIAL_LIFETIME_MS`, `LINEAGE_MAX_AGE_MS`

**Expected outcome**: It states 60 seconds as the bound, 15 minutes and 24 hours as upper bounds, and the three client rules (schedule from `expiresAt`; re-bootstrap on `credential_expired`; never hard-code L or M); the values equal the constants.

**Scope**: happy-path · **Priority**: High  
**Source**: agent-credentials / M1-FR-07 (NFR-AC-05)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-credentials/code/`  
**Technical references**: `construction/agent-credentials/nfr-requirements/nfr-requirements.md` (NFR-AC-05); `construction/agent-credentials/nfr-design/nfr-design-patterns.md` (NP-AC-01)

---

### TC-AC-039 — Every presenter row of ID §8b is refused or reached at S3

**Context**: Every principal × entry point is reached or refused (ID FR-023).

**Scenario**: Renewal is called with each presenter.

**Preconditions**:
- E's data-gateway is running on the local stack. A is registered in E by H, with a secret issued
- A human environment credential and a sign-in

**Steps**:
1. Agent credential alone
2. Agent credential with `Soorma-Delegation`
3. A human credential
4. Two `Authorization` headers
5. A `soorma_dc_` value
6. An unknown prefix

**Expected outcome**: Step 1: `200`. Every other step: `credential_refused`, without verifying.

**Scope**: negative · **Priority**: High  
**Source**: agent-credentials / M1-FR-09 (ID FR-023)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-credentials/code/`  
**Technical references**: `construction/agent-credentials/functional-design/business-rules.md` (D-AC-10; BR-PR-AC-04)

---

### TC-AC-040 — S3's production closure holds no organization-level code

**Context**: S3 must not link `org-identity` or `identity-resolution`, and imports no evaluator (D-AC-11; I5).

**Scenario**: The workspace manifests are walked from S3.

**Preconditions**:
- The repository

**Steps**:
1. Walk `@soorma/data-gateway`'s production dependencies
2. Scan S3's sources for `@soorma/authority`

**Expected outcome**: The closure contains `service-kit`, `credentials`, `agent-identity`, `abuse-bound`, and neither `org-identity` nor `identity-resolution`; no `@soorma/authority` import. S2's TC-EHA-078 unchanged.

**Scope**: negative · **Priority**: High  
**Source**: agent-credentials / M1-NFR-08 (D-AC-11)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-credentials/code/`  
**Technical references**: `construction/agent-credentials/nfr-design/nfr-design-patterns.md` (NP-AC-10)

---

### TC-AC-041 — Nothing reads code identity or deployment topology

**Context**: A credential asserts registration, not code identity (PF §8b; I10).

**Scenario**: Code review with a check over S3, P5, P6's agent half, P8.

**Preconditions**:
- The repository

**Steps**:
1. Search for host, container, cluster, or pod identity reads, and source-address use in identity decisions

**Expected outcome**: None; the instance is the asserted field, the environment from configuration.

**Scope**: edge-boundary · **Priority**: Medium  
**Source**: agent-credentials / M1-FR-05 (I10)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-credentials/code/`  
**Technical references**: `construction/agent-credentials/functional-design/invariant-coverage-matrix.md` (I10)

---

### TC-AC-042 — Every S3 refusal holds for a raw call

**Context**: Every check runs at S3 from the raw request (I2).

**Scenario**: Each refusal of business-logic-model §7 is sent without the SDK.

**Preconditions**:
- E's data-gateway is running on the local stack. A is registered in E by H, with a secret issued

**Steps**:
1. Send each refusal case as a raw HTTP request

**Expected outcome**: Each gets its specified code, independent of any client.

**Scope**: negative · **Priority**: High  
**Source**: agent-credentials / M1-FR-09 (I2)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-credentials/code/`  
**Technical references**: `construction/agent-credentials/functional-design/invariant-coverage-matrix.md` (I2); `construction/agent-credentials/functional-design/business-logic-model.md` §7

---

### TC-AC-043 — The same credential from another address resolves the same; no credential is refused anywhere

**Context**: Identity comes only from presented material (I3).

**Scenario**: The same secret and credential are presented from two source addresses.

**Preconditions**:
- E's data-gateway is running on the local stack. A is registered in E by H, with a secret issued

**Steps**:
1. Bootstrap from the host loopback and from a container on `e`
2. Renew from both
3. Renew with no credential from inside `e`

**Expected outcome**: Steps 1, 2: the same agent and instance. Step 3: `credential_refused`.

**Scope**: negative · **Priority**: High  
**Source**: agent-credentials / M1-FR-05 (I3)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-credentials/code/`  
**Technical references**: `construction/agent-credentials/functional-design/invariant-coverage-matrix.md` (I3)

---

### TC-AC-044 — Each surface document holds one face only

**Context**: Data-face and control-face operations are reachable through separate surfaces (I6).

**Scenario**: The contract documents are read.

**Preconditions**:
- The repository

**Steps**:
1. Read `data-gateway.openapi.yaml` and `control-gateway.openapi.yaml`

**Expected outcome**: S3's holds no control-face operation; S2's holds no data-face operation.

**Scope**: edge-boundary · **Priority**: Medium  
**Source**: agent-credentials / M1-NFR-03 (I6)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-credentials/code/`  
**Technical references**: `construction/agent-credentials/functional-design/invariant-coverage-matrix.md` (I6)

---

### TC-AC-045 — The changed contract passes U1's compatibility check

**Context**: Every change is compatible under the pre-release policy (I7).

**Scenario**: U1's check runs over the changed contract.

**Preconditions**:
- The repository

**Steps**:
1. Run U1's compatibility check

**Expected outcome**: A new surface, `authentication_failed` widened, the instance sentence, the published bound: all classified compatible.

**Scope**: happy-path · **Priority**: Medium  
**Source**: agent-credentials / M1-NFR-04 (I7)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-credentials/code/`  
**Technical references**: `construction/agent-credentials/functional-design/business-rules.md` §13

---

### TC-AC-046 — No commercial or unassigned capability, and no seeding path, ships

**Context**: The packaging table (I8); the seeding fixture never in an image.

**Scenario**: The packaging table is re-checked; each built image's files are listed.

**Preconditions**:
- The repository; built images

**Steps**:
1. Check the I8 table against the code
2. Search each image for the seeding fixture and helper

**Expected outcome**: Every capability core-assigned; no revocation initiation or rotation in any form; no seeding code in any image.

**Scope**: negative · **Priority**: High  
**Source**: agent-credentials / M1-FR-07 (I8)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-credentials/code/`  
**Technical references**: `construction/agent-credentials/functional-design/invariant-coverage-matrix.md` (I8); `construction/agent-credentials/nfr-design/nfr-design-patterns.md` (NP-AC-06)

---

### TC-AC-047 — No tenant constant in the platform's code

**Context**: Mechanism, not instance (I9).

**Scenario**: Code review with a check.

**Preconditions**:
- The repository

**Steps**:
1. Search U6's source for agent or instance names outside labelled test fixtures

**Expected outcome**: None.

**Scope**: edge-boundary · **Priority**: Low  
**Source**: agent-credentials / M1-FR-05 (I9)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-credentials/code/`  
**Technical references**: `construction/agent-credentials/functional-design/invariant-coverage-matrix.md` (I9)

---

### TC-AC-048 — Every bootstrap failure is the same response

**Context**: One uniform refusal, so no cause can be told apart (BR-BS-07).

**Scenario**: Each cause of BR-BS-01 to 05 is produced.

**Preconditions**:
- E's data-gateway is running on the local stack. A is registered in E by H, with a secret issued
- Test-only revocation seeding

**Steps**:
1. Unknown agent; another prefix; malformed secret; unknown secret id; another registration's secret; wrong secret; revoked agent

**Expected outcome**: Each: the same status (403), code, body shape, and headers; only the security log's reason differs.

**Scope**: negative · **Priority**: High  
**Source**: agent-credentials / M1-FR-05 (BR-BS-07)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-credentials/code/`  
**Technical references**: `construction/agent-credentials/functional-design/business-rules.md` (BR-BS-07)

---

### TC-AC-049 — Failed attempts are recorded only for an existing registration, off the response path

**Context**: The writer decides existence itself (BR-FA-01, 02; NP-AC-07).

**Scenario**: Failures are produced for A and for an unknown agent.

**Preconditions**:
- The environment store's database tests (`pnpm db:test`), connected as the role the case names: `soorma_env_data`

**Steps**:
1. Queue failures for A and for `nobody`
2. Flush the writer

**Expected outcome**: One row for A, none for `nobody`; the batch insert joined to `registrations` decided it; no row holds a secret, id, or digest.

**Scope**: edge-boundary · **Priority**: High  
**Source**: agent-credentials / M1-FR-05 (BR-FA-01, 02)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-credentials/code/`  
**Technical references**: `construction/agent-credentials/functional-design/business-rules.md` (BR-FA-01 to 03); `construction/agent-credentials/nfr-design/nfr-design-patterns.md` (NP-AC-07)

---

### TC-AC-050 — A token whose record is missing or names another instance is refused

**Context**: The record governs the binding (BR-RN-02).

**Scenario**: Tokens are minted with E's key for a missing `cid` and a mismatched instance.

**Preconditions**:
- S3's tests, with E's agent key ring

**Steps**:
1. Renew with a token for an unknown `cid`
2. Renew with a token whose `inst` differs from its record

**Expected outcome**: Each: `credential_refused`; nothing written.

**Scope**: negative · **Priority**: Medium  
**Source**: agent-credentials / M1-FR-06 (BR-RN-02)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-credentials/code/`  
**Technical references**: `construction/agent-credentials/functional-design/business-rules.md` (BR-RN-02); `construction/agent-credentials/nfr-design/nfr-design-patterns.md` (NP-AC-03)

---

### TC-AC-051 — Concurrent renewals of one lineage all succeed

**Context**: The record keeps the latest expiry (D-AC-15).

**Scenario**: Two renewals of one token run at once.

**Preconditions**:
- The environment store's database tests (`pnpm db:test`), connected as the role the case names: `soorma_env_data`

**Steps**:
1. Renew twice concurrently

**Expected outcome**: Both `200`; `expires_at` is the later of the two; two attribution records.

**Scope**: edge-boundary · **Priority**: Medium  
**Source**: agent-credentials / M1-FR-06 (D-AC-15)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-credentials/code/`  
**Technical references**: `construction/agent-credentials/functional-design/business-rules.md` (D-AC-15)

---

### TC-AC-052 — With the store down, both operations fail closed and write nothing

**Context**: S3's availability is the store's (NFR-AC-14).

**Scenario**: E's store is stopped.

**Preconditions**:
- E's data-gateway is running on the local stack. A is registered in E by H, with a secret issued

**Steps**:
1. Stop `e-db`
2. Bootstrap
3. Renew

**Expected outcome**: Each: `unavailable` (503, `Retry-After: 5`); nothing written; the bound settles bootstrap as a failure.

**Scope**: negative · **Priority**: High  
**Source**: agent-credentials / M1-FR-07 (NFR-AC-14)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-credentials/code/`  
**Technical references**: `construction/agent-credentials/nfr-requirements/nfr-requirements.md` (NFR-AC-14)

---

### TC-AC-053 — An earlier token of a lineage stays valid until its own expiry

**Context**: Liveness is the record's expiry and revocation, not the latest `jti` (BR-CR-AC-06).

**Scenario**: An instance renews, then presents its earlier token.

**Preconditions**:
- E's data-gateway is running on the local stack. A is registered in E by H, with a secret issued

**Steps**:
1. Renew
2. Renew again with the first token

**Expected outcome**: Step 2: `200` while the first token is unexpired.

**Scope**: edge-boundary · **Priority**: Low  
**Source**: agent-credentials / M1-FR-06 (BR-CR-AC-06)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-credentials/code/`  
**Technical references**: `construction/agent-credentials/functional-design/business-rules.md` (BR-CR-AC-06)

---

### TC-AC-054 — B is 60 seconds, from the one constant, with no configuration key

**Context**: The bound is one defined value in code (NFR-AC-01; NP-AC-01).

**Scenario**: P5's cache runs on the injected clock.

**Preconditions**:
- P5's cache tests

**Steps**:
1. Cache `not_revoked` at 0 s; ask at 59.999 s and at 60 s
2. With the source failing, ask at 59.999 s and at 60 s
3. Search the configuration schemas for a bound or TTL key

**Expected outcome**: Step 1: served, then re-read. Step 2: served, then denied (`unavailable`). Step 3: none; the cache is built with `PROPAGATION_BOUND_MS`.

**Scope**: edge-boundary · **Priority**: High  
**Source**: agent-credentials / M1-FR-07 (NFR-AC-01)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-credentials/code/`  
**Technical references**: `construction/agent-credentials/nfr-requirements/nfr-requirements.md` (NFR-AC-01); `construction/agent-credentials/nfr-design/nfr-design-patterns.md` (NP-AC-01, 05)

---

### TC-AC-055 — L is 15 minutes at bootstrap and renewal

**Context**: Every token expires at most 15 minutes after issue (NFR-AC-02).

**Scenario**: Tokens are minted on the injected clock.

**Preconditions**:
- S3's tests

**Steps**:
1. Bootstrap
2. Renew 10 minutes later

**Expected outcome**: Each `exp` = `iat` + 15 minutes (or the lineage end, if sooner); every response's `expiresAt` equals its token's `exp`.

**Scope**: edge-boundary · **Priority**: Medium  
**Source**: agent-credentials / M1-FR-06 (NFR-AC-02)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-credentials/code/`  
**Technical references**: `construction/agent-credentials/nfr-requirements/nfr-requirements.md` (NFR-AC-02, 05)

---

### TC-AC-056 — B < L ≤ M holds over the constants

**Context**: The relations are checked by a unit test (NFR-AC-04, as fixed at NFR Design).

**Scenario**: A unit test over the three constants.

**Preconditions**:
- P5's tests

**Steps**:
1. Compare the constants

**Expected outcome**: 60 s < 15 min ≤ 24 h.

**Scope**: edge-boundary · **Priority**: Low  
**Source**: agent-credentials / M1-FR-07 (NFR-AC-04)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-credentials/code/`  
**Technical references**: `construction/agent-credentials/nfr-requirements/nfr-requirements.md` (NFR-AC-04)

---

### TC-AC-057 — The bound's window admits 60 live attempts per agent in 60 seconds

**Context**: In-flight attempts count; successes remove their own (NFR-AC-06).

**Scenario**: Attempts against one agent, injected clock.

**Preconditions**:
- P8's tests with the agent limits

**Steps**:
1. Admit 60 at once
2. Admit a 61st
3. Fail one at 0 s; admit at 60 s
4. Run 60 parallel successes

**Expected outcome**: Step 2 refused; step 3's place frees at 60 s; step 4 all admitted.

**Scope**: edge-boundary · **Priority**: High  
**Source**: agent-credentials / M1-FR-05 (NFR-AC-06)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-credentials/code/`  
**Technical references**: `construction/agent-credentials/nfr-requirements/nfr-requirements.md` (NFR-AC-06)

---

### TC-AC-058 — The bound's backoff doubles from 1 second to a 60-second cap

**Context**: Backoff from the 10th consecutive failure (NFR-AC-07).

**Scenario**: Consecutive failures, injected clock.

**Preconditions**:
- P8's tests with the agent limits

**Steps**:
1. Fail 9 times
2. Fail on, reading each wait
3. Succeed once

**Expected outcome**: No wait after 9; then 1, 2, 4, 8, 16, 32, 60, 60 seconds; a success resets the backoff only.

**Scope**: edge-boundary · **Priority**: High  
**Source**: agent-credentials / M1-FR-05 (NFR-AC-07)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-credentials/code/`  
**Technical references**: `construction/agent-credentials/nfr-requirements/nfr-requirements.md` (NFR-AC-07)

---

### TC-AC-059 — `Retry-After` is the later of the two waits

**Context**: U2's rule for the agent bound (NFR-AC-08).

**Scenario**: The window and the backoff both apply.

**Preconditions**:
- P8's tests

**Steps**:
1. Produce a window wait and a backoff wait

**Expected outcome**: `Retry-After` is the later, in whole seconds, rounded up.

**Scope**: edge-boundary · **Priority**: Low  
**Source**: agent-credentials / M1-FR-05 (NFR-AC-08)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-credentials/code/`  
**Technical references**: `construction/agent-credentials/nfr-requirements/nfr-requirements.md` (NFR-AC-08)

---

### TC-AC-060 — Admission is atomic per slot, and each environment has its own table

**Context**: Concurrent attempts cannot exceed the window (NFR-AC-09).

**Scenario**: Parallel failing attempts; the same agent in E2.

**Preconditions**:
- The environment store's database tests (`pnpm db:test`), connected as the role the case names: `soorma_env_data`

**Steps**:
1. Run 80 parallel failing attempts for A
2. Attempt A in E2

**Expected outcome**: At most 60 admitted; E2's attempt uses E2's table and secret, unaffected.

**Scope**: edge-boundary · **Priority**: High  
**Source**: agent-credentials / M1-FR-05 (NFR-AC-09)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-credentials/code/`  
**Technical references**: `construction/agent-credentials/nfr-requirements/nfr-requirements.md` (NFR-AC-09); `construction/agent-credentials/nfr-design/nfr-design-patterns.md` (NP-AC-07)

---

### TC-AC-061 — The lockout lasts at most 60 seconds after an attack stops

**Context**: The lockout residual, quantified (NFR-AC-10; the user's Q6 wording).

**Scenario**: An outsider floods A's bootstrap with wrong secrets, then stops.

**Preconditions**:
- E's data-gateway is running on the local stack. A is registered in E by H, with a secret issued
- An instance of A holds a live credential

**Steps**:
1. Flood A with wrong secrets
2. During it, renew the live credential
3. Stop; bootstrap correctly within 60 seconds

**Expected outcome**: Step 2: `200` (renewal is outside the bound). Step 3: succeeds within 60 seconds.

**Scope**: edge-boundary · **Priority**: High  
**Source**: agent-credentials / M1-FR-05 (NFR-AC-10)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-credentials/code/`  
**Technical references**: `construction/agent-credentials/nfr-requirements/nfr-requirements.md` (NFR-AC-10); `construction/agent-credentials/functional-design/business-rules.md` §16

---

### TC-AC-062 — The Failed Bootstrap Attempt writer keeps U2's behaviour

**Context**: Queue 10,000, batches of 100 every 250 ms, drops counted (NFR-AC-11).

**Scenario**: U2's writer tests run over the agent writer.

**Preconditions**:
- P8's tests

**Steps**:
1. Fill the queue past 10,000
2. Fail a batch
3. Shut down

**Expected outcome**: Drops counted and logged without a secret; the batch dropped and counted; the queue flushed.

**Scope**: edge-boundary · **Priority**: Medium  
**Source**: agent-credentials / M1-FR-05 (NFR-AC-11)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-credentials/code/`  
**Technical references**: `construction/agent-credentials/nfr-requirements/nfr-requirements.md` (NFR-AC-11)

---

### TC-AC-063 — S3 holds at most 64 requests in flight

**Context**: U4's throttle at S3 (NFR-AC-12).

**Scenario**: 65 slow requests, and 64 aborted ones.

**Preconditions**:
- S3's tests

**Steps**:
1. Hold 64; send a 65th
2. Abort 64 in flight; send another

**Expected outcome**: Step 1: the 65th `unavailable` after 1 second, `Retry-After: 5`, `throttle.refused`. Step 2: every slot released once; admitted.

**Scope**: edge-boundary · **Priority**: Medium  
**Source**: agent-credentials / SECURITY-11 (NFR-AC-12)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-credentials/code/`  
**Technical references**: `construction/agent-credentials/nfr-requirements/nfr-requirements.md` (NFR-AC-12)

---

### TC-AC-064 — Body bounds at S3

**Context**: 16 KiB on both routes; renewal takes no body (NFR-AC-13).

**Scenario**: Oversized and unexpected bodies.

**Preconditions**:
- S3's tests

**Steps**:
1. Bootstrap with 16 KiB + 1 byte
2. Renew with a 1-byte body

**Expected outcome**: `payload_too_large`; `malformed_request` with pointer `''`.

**Scope**: negative · **Priority**: Low  
**Source**: agent-credentials / SECURITY-05 (NFR-AC-13)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-credentials/code/`  
**Technical references**: `construction/agent-credentials/nfr-requirements/nfr-requirements.md` (NFR-AC-13)

---

### TC-AC-065 — The cache is bounded, shares misses, and never admits by eviction

**Context**: NFR-AC-15; NP-AC-05.

**Scenario**: P5's cache at its bound, injected source.

**Preconditions**:
- P5's cache tests

**Steps**:
1. Fill past 16,384 entries
2. Evict a `revoked` entry, then ask again
3. Ask for one key from 10 callers at once
4. Fail a read, then ask again

**Expected outcome**: Oldest evicted; the revoked target re-reads `revoked`; one read for the 10; the failure not cached.

**Scope**: edge-boundary · **Priority**: High  
**Source**: agent-credentials / M1-FR-07 (NFR-AC-15)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-credentials/code/`  
**Technical references**: `construction/agent-credentials/nfr-requirements/nfr-requirements.md` (NFR-AC-15); `construction/agent-credentials/nfr-design/nfr-design-patterns.md` (NP-AC-05)

---

### TC-AC-066 — The revocation read's cost is reported

**Context**: A cache hit at most 0.1 ms p99 in process; a miss one statement (NFR-AC-16). Reported, not gated.

**Scenario**: `pnpm bench:revocation` at Build and Test.

**Preconditions**:
- The workspace built

**Steps**:
1. Run the benchmark

**Expected outcome**: The p99 is reported in the Build and Test summary; the miss is one statement by review.

**Scope**: edge-boundary · **Priority**: Low  
**Source**: agent-credentials / M1-NFR-01 (NFR-AC-16)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-credentials/code/`  
**Technical references**: `construction/agent-credentials/nfr-requirements/nfr-requirements.md` (NFR-AC-16)

---

### TC-AC-067 — Bootstrap and renewal latency is reported

**Context**: At most 200 ms p95 on the local stack (NFR-AC-17). Reported, not gated.

**Scenario**: A performance run at Build and Test.

**Preconditions**:
- The local stack

**Steps**:
1. Measure both operations

**Expected outcome**: The p95 is reported in the Build and Test summary.

**Scope**: edge-boundary · **Priority**: Low  
**Source**: agent-credentials / M1-NFR-01 (NFR-AC-17)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-credentials/code/`  
**Technical references**: `construction/agent-credentials/nfr-requirements/nfr-requirements.md` (NFR-AC-17)

---

### TC-AC-068 — Token time rules: no leeway on expiry, 30 seconds on issue

**Context**: U4's rules for agent tokens (NFR-AC-18).

**Scenario**: Tokens at the edges, injected clock.

**Preconditions**:
- P5's token tests

**Steps**:
1. Verify at `exp`
2. Verify an `iat` 30 s ahead
3. Verify an `iat` 31 s ahead

**Expected outcome**: `credential_expired`; accepted; `credential_refused`.

**Scope**: edge-boundary · **Priority**: Medium  
**Source**: agent-credentials / M1-FR-06 (NFR-AC-18)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-credentials/code/`  
**Technical references**: `construction/agent-credentials/nfr-requirements/nfr-requirements.md` (NFR-AC-18)

---

### TC-AC-069 — A key rotation keeps old tokens verifying, and the README says wait at least 15 minutes

**Context**: Rotation keeps a retired key's verify half for at least L (NFR-AC-19; D-ID-AC-17).

**Scenario**: The agent ring rotates; the README is read.

**Preconditions**:
- S3's tests; the repository

**Steps**:
1. Mint with key 1; rotate to key 2 (key 1 kept for verifying)
2. Verify the old token
3. Read S3's README Operations

**Expected outcome**: Step 2: valid until its `exp`. Step 3: the three steps, "wait at least 15 minutes", the counter secret, the lockout, the store outage, S1 stopped, the constants, and the upgrade note (docs test).

**Scope**: happy-path · **Priority**: Medium  
**Source**: agent-credentials / M1-FR-06 (NFR-AC-19)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-credentials/code/`  
**Technical references**: `construction/agent-credentials/nfr-requirements/nfr-requirements.md` (NFR-AC-19); `construction/agent-credentials/infrastructure-design/infrastructure-design.md` (§11)

---

### TC-AC-070 — Constant-time comparison covers U6's code

**Context**: NFR-AC-20.

**Scenario**: U2's `secret-compare` code check.

**Preconditions**:
- The repository

**Steps**:
1. Run the code checks

**Expected outcome**: No `===` on a secret-derived value in U6's code.

**Scope**: edge-boundary · **Priority**: Low  
**Source**: agent-credentials / SECURITY-12 (NFR-AC-20)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-credentials/code/`  
**Technical references**: `construction/agent-credentials/nfr-requirements/nfr-requirements.md` (NFR-AC-20)

---

### TC-AC-071 — TLS 1.3 at S3's edge and to its store

**Context**: NFR-AC-21.

**Scenario**: TLS handshakes at the edge and to the store.

**Preconditions**:
- E's data-gateway is running on the local stack. A is registered in E by H, with a secret issued

**Steps**:
1. Connect with TLS 1.2 to the edge
2. Inspect S3's store connection

**Expected outcome**: TLS 1.2 refused; the store connection is TLS 1.3, `verify-full`.

**Scope**: negative · **Priority**: Medium  
**Source**: agent-credentials / SECURITY-01 (NFR-AC-21)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-credentials/code/`  
**Technical references**: `construction/agent-credentials/nfr-requirements/nfr-requirements.md` (NFR-AC-21)

---

### TC-AC-072 — S3's logs name events, never a secret or a human

**Context**: NFR-AC-22; D-ID-AC-11.

**Scenario**: Every log line of each operation and refusal is captured.

**Preconditions**:
- S3's tests

**Steps**:
1. Bootstrap, renew, and produce each refusal

**Expected outcome**: The event names of NFR-AC-22; no secret, secret id, digest, or token; no human-principal field.

**Scope**: negative · **Priority**: High  
**Source**: agent-credentials / SECURITY-03 (NFR-AC-22)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-credentials/code/`  
**Technical references**: `construction/agent-credentials/nfr-requirements/nfr-requirements.md` (NFR-AC-22); `construction/agent-credentials/infrastructure-design/infrastructure-design.md` (D-ID-AC-11)

---

### TC-AC-073 — S3's alert rules validate

**Context**: NFR-AC-23.

**Scenario**: The alert file's schema test.

**Preconditions**:
- The repository

**Steps**:
1. Validate `deploy/monitoring/alerts.yaml`

**Expected outcome**: S3's three rules present and valid.

**Scope**: happy-path · **Priority**: Low  
**Source**: agent-credentials / SECURITY-14 (NFR-AC-23)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-credentials/code/`  
**Technical references**: `construction/agent-credentials/nfr-requirements/nfr-requirements.md` (NFR-AC-23)

---

### TC-AC-074 — Nothing is pruned, and the store keeps U4's guarantees

**Context**: NFR-AC-24.

**Scenario**: Review.

**Preconditions**:
- The repository

**Steps**:
1. Search for a pruning job; review the store settings

**Expected outcome**: No pruning; `synchronous_commit` on; one transaction per operation.

**Scope**: edge-boundary · **Priority**: Low  
**Source**: agent-credentials / M1-FR-12 (NFR-AC-24)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-credentials/code/`  
**Technical references**: `construction/agent-credentials/nfr-requirements/nfr-requirements.md` (NFR-AC-24)

---

### TC-AC-075 — No new dependency

**Context**: NFR-AC-25.

**Scenario**: The dependency register and audit.

**Preconditions**:
- The repository

**Steps**:
1. Compare the register; run `pnpm audit`

**Expected outcome**: No new external dependency; audit clean.

**Scope**: happy-path · **Priority**: Low  
**Source**: agent-credentials / SECURITY-10 (NFR-AC-25)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-credentials/code/`  
**Technical references**: `construction/agent-credentials/nfr-requirements/nfr-requirements.md` (NFR-AC-25)

---

### TC-AC-076 — The two new migrations apply, and 0001 and 0002 are unchanged

**Context**: NP-AC-02; TC-EHA-068's list gains two names (class 1).

**Scenario**: The migration test on a fresh database.

**Preconditions**:
- The environment store's database tests (`pnpm db:test`), connected as the role the case names: migrator

**Steps**:
1. Run two concurrent migrations
2. Compare 0001 and 0002 with `main`

**Expected outcome**: Applied once each: `0001` to `0004`; the earlier files byte-identical.

**Scope**: happy-path · **Priority**: High  
**Source**: agent-credentials / NP-AC-02  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-credentials/code/`  
**Technical references**: `construction/agent-credentials/nfr-design/nfr-design-patterns.md` (NP-AC-02)

---

### TC-AC-077 — `agent_credentials` refuses an expiry past the lineage end, and a row of another environment

**Context**: NP-AC-03's constraints.

**Scenario**: Rows are inserted directly as the owner.

**Preconditions**:
- The environment store's database tests (`pnpm db:test`), connected as the role the case names: owner

**Steps**:
1. Insert `expires_at` > `lineage_ends_at`
2. Insert a row naming E2's registration with E's columns
3. Insert a row naming an unknown secret

**Expected outcome**: Each refused by its constraint.

**Scope**: negative · **Priority**: Medium  
**Source**: agent-credentials / NP-AC-03  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-credentials/code/`  
**Technical references**: `construction/agent-credentials/nfr-design/nfr-design-patterns.md` (NP-AC-03)

---

### TC-AC-078 — A revocation can only name a target in its own environment

**Context**: NP-AC-04's foreign keys; the direct statement covers both granularities.

**Scenario**: Revocations are seeded as the owner.

**Preconditions**:
- The environment store's database tests (`pnpm db:test`), connected as the role the case names: owner

**Steps**:
1. Seed a credential revocation for an unknown `cid`
2. Seed an agent revocation for E2's agent with E's columns
3. Read with the direct statement for each granularity

**Expected outcome**: Steps 1, 2 refused; step 3 answers `revoked` for each granularity, `not_revoked` otherwise.

**Scope**: negative · **Priority**: High  
**Source**: agent-credentials / NP-AC-04  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-credentials/code/`  
**Technical references**: `construction/agent-credentials/nfr-design/nfr-design-patterns.md` (NP-AC-04)

---

### TC-AC-079 — S2's role has nothing on U6's tables

**Context**: NP-AC-06, as corrected at Infrastructure Design.

**Scenario**: Statements as `soorma_env_app`.

**Preconditions**:
- The environment store's database tests (`pnpm db:test`), connected as the role the case names: `soorma_env_app`

**Steps**:
1. `SELECT`, `INSERT`, `UPDATE`, `DELETE` on each U6 table

**Expected outcome**: Each fails with permission denied; U4's TC-EHA-080 cases unchanged.

**Scope**: negative · **Priority**: High  
**Source**: agent-credentials / SECURITY-06 (NP-AC-06)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-credentials/code/`  
**Technical references**: `construction/agent-credentials/nfr-design/nfr-design-patterns.md` (NP-AC-06)

---

### TC-AC-080 — S3's role can run exactly its statements, and nothing else

**Context**: D-ID-AC-07, with the user's addition: the grants fit the statements, not only refuse others.

**Scenario**: Statements as `soorma_env_data`, the real `statement()` objects.

**Preconditions**:
- The environment store's database tests (`pnpm db:test`), connected as the role the case names: `soorma_env_data`

**Steps**:
1. Run P8's admission, settle-success, settle-failure, and the backoff update (the objects from `packages/abuse-bound`)
2. Run bootstrap's writes, renewal's `UPDATE (expires_at)` with `RETURNING`, the agent half's read, and both revocation reads (the objects from `packages/credentials`, `agent-identity`, `attribution`)
3. Run each forbidden statement of NP-AC-06
4. Check the role's attributes

**Expected outcome**: Steps 1, 2 succeed; step 3 each fails with permission denied (`grants`, `credentials`, `schema_migrations`; writes to registrations, secrets, revocations; other `agent_credentials` columns; `attempt_slots.slot`; reads of `failed_bootstrap_attempts`, `attribution_records`; `DELETE`); step 4 `NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION NOBYPASSRLS`.

**Scope**: negative · **Priority**: High  
**Source**: agent-credentials / SECURITY-06 (D-ID-AC-07)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-credentials/code/`  
**Technical references**: `construction/agent-credentials/nfr-design/nfr-design-patterns.md` (NP-AC-06); `construction/agent-credentials/infrastructure-design/infrastructure-design.md` (§5)

---

### TC-AC-081 — P8's generic core keeps U2's API, and the agent slot has its own vectors

**Context**: Q4 A at NFR Design: U2's tests and canonical vectors unchanged (NP-AC-07).

**Scenario**: P8's and U2's tests run.

**Preconditions**:
- The repository

**Steps**:
1. Run U2's P8 tests and canonical vectors unchanged
2. Run the agent slot-key vectors
3. Build a `SlotBound` with the agent limits

**Expected outcome**: U2's pass unchanged; the agent vectors match; the agent limits apply.

**Scope**: happy-path · **Priority**: High  
**Source**: agent-credentials / NP-AC-07  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-credentials/code/`  
**Technical references**: `construction/agent-credentials/nfr-design/nfr-design-patterns.md` (NP-AC-07)

---

### TC-AC-082 — Each credential kind is refused by the other's verifier

**Context**: Kind separation (NP-AC-09; D-AC-03, 13).

**Scenario**: Tokens re-prefixed across kinds.

**Preconditions**:
- P5's token tests, both rings

**Steps**:
1. A `soorma_ec_` token's JWS behind `soorma_ac_` at `verifyAgentCredential`
2. A `soorma_ac_` token's JWS behind `soorma_ec_` at U4's `verifyEnvironmentCredential`

**Expected outcome**: Each refused (its `typ`; an unknown `kid`); U4's token tests unchanged.

**Scope**: negative · **Priority**: High  
**Source**: agent-credentials / D-AC-03 (NP-AC-09)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-credentials/code/`  
**Technical references**: `construction/agent-credentials/nfr-design/nfr-design-patterns.md` (NP-AC-09)

---

### TC-AC-083 — Built images hold none of the forbidden packages

**Context**: NP-AC-10 with the user's addition: S3's, S2's, and S1 as a positive control.

**Scenario**: `image-packages` on the built images, in CI.

**Preconditions**:
- The three images built

**Steps**:
1. Check S3's image (forbid `org-identity`, `identity-resolution`)
2. Check S2's image (forbid `org-identity`)
3. Check S1's image (expect `org-identity`)

**Expected outcome**: S3 and S2 pass; S1's check finds `org-identity`.

**Scope**: negative · **Priority**: High  
**Source**: agent-credentials / M1-NFR-08 (NP-AC-10)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-credentials/code/`  
**Technical references**: `construction/agent-credentials/nfr-design/nfr-design-patterns.md` (NP-AC-10)

---

### TC-AC-084 — The secret check finds agent credentials and registration secrets, never fake ones

**Context**: NP-AC-12, with the user's condition: fixtures use obviously fake values, no exception in the check.

**Scenario**: The secret-pattern check over samples, the repository, and each image.

**Preconditions**:
- The repository; built images

**Steps**:
1. Check a real-shaped agent token and secret value
2. Check the test fixtures' fake values
3. Inspect `FIXTURE_PATHS`

**Expected outcome**: Real shapes found; fakes not matched; no new `FIXTURE_PATHS` entry or allowlist; the existing patterns unchanged.

**Scope**: negative · **Priority**: High  
**Source**: agent-credentials / SECURITY-12 (NP-AC-12)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-credentials/code/`  
**Technical references**: `construction/agent-credentials/nfr-design/nfr-design-patterns.md` (NP-AC-12)

---

### TC-AC-085 — `checkAgentRequest` takes callbacks, and P1 gains no dependency

**Context**: NP-AC-11.

**Scenario**: P1's tests and manifest.

**Preconditions**:
- The repository

**Steps**:
1. Run `checkAgentRequest` with stub `verify` and `revocation` callbacks for each outcome
2. Read `@soorma/perimeter`'s dependencies

**Expected outcome**: Each outcome as specified; the dependencies are still `service-kit` only.

**Scope**: happy-path · **Priority**: Medium  
**Source**: agent-credentials / D-AC-27 (NP-AC-11)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-credentials/code/`  
**Technical references**: `construction/agent-credentials/nfr-design/nfr-design-patterns.md` (NP-AC-11)

---

### TC-AC-086 — U4's Compose-model rules hold for every service under every profile

**Context**: D-ID-AC-13: U4's test renders with every profile (class 2), its rules unchanged.

**Scenario**: The Compose-model test.

**Preconditions**:
- The repository; Docker

**Steps**:
1. Render with every listed profile
2. Apply U4's rules to every service

**Expected outcome**: Every rule holds, the backup, restore, and data-gateway services included; only lists gained items (class 1).

**Scope**: edge-boundary · **Priority**: High  
**Source**: agent-credentials / D-ID-AC-13  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-credentials/code/`  
**Technical references**: `construction/agent-credentials/infrastructure-design/infrastructure-design.md` (§13)

---

### TC-AC-087 — S3's secrets, roles, and networks are separated as designed

**Context**: U6's Compose assertions (D-ID-AC-09, 11, 12, the user's instruction).

**Scenario**: U6's Compose test, every profile.

**Preconditions**:
- The repository; Docker

**Steps**:
1. Read each service's mounts, env.sh's copies, and the networks

**Expected outcome**: S3 never gets `{env}-db-app-password`; S2 never gets `{env}-db-data-password`; agent signing keys only in `data-gateway/`; agent verify keys listed and copied nowhere yet; no human ring, caller key, or log key in `data-gateway/`; S3 on no `org-internal-*` network; S3's variables within its allowlist.

**Scope**: negative · **Priority**: High  
**Source**: agent-credentials / D-ID-AC-09  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-credentials/code/`  
**Technical references**: `construction/agent-credentials/infrastructure-design/infrastructure-design.md` (§4, §13)

---

### TC-AC-088 — The restore services mount their own `restore/` subdirectory

**Context**: D-ID-AC-14: the one class-3 change, approved by the user.

**Scenario**: U5's backup test, as changed.

**Preconditions**:
- The repository; Docker

**Steps**:
1. Render with `--profile backup`; read the restore services' mounts
2. Read env.sh's copy lines

**Expected outcome**: `e-restore`, `e2-restore` mount `restore`; the backup services `backup`; `copy restore 999 "$env-db-migrator-password" stack-ca-cert` and the unchanged `copy backup …` line.

**Scope**: happy-path · **Priority**: Medium  
**Source**: agent-credentials / D-ID-AC-14  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-credentials/code/`  
**Technical references**: `construction/agent-credentials/infrastructure-design/infrastructure-design.md` (§14)

---

### TC-AC-089 — `stack:init` generates U6's secrets safely

**Context**: D-ID-AC-05, 06, 08.

**Scenario**: `stack:init` into a fresh directory.

**Preconditions**:
- The repository

**Steps**:
1. Run `stack:init` twice

**Expected outcome**: Each environment gets `{env}-agent-signing-key-1` (Ed25519), its matching `{env}-agent-verify-key-1`, `{env}-bootstrap-counter-secret` (32 bytes), `{env}-db-data-password`, `{env}-data-gateway-tls`, 0600, distinct per environment; a second run overwrites nothing; a mismatched verify half is refused.

**Scope**: happy-path · **Priority**: Medium  
**Source**: agent-credentials / D-ID-AC-05  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-credentials/code/`  
**Technical references**: `construction/agent-credentials/infrastructure-design/infrastructure-design.md` (§4)

---

### TC-AC-090 — The data role exists in a fresh store and S3 connects as it

**Context**: D-ID-AC-07, 08: env-roles.sql, the init script, `env-pg_hba.conf`.

**Scenario**: A fresh stack.

**Preconditions**:
- The local stack, fresh

**Steps**:
1. Read `pg_roles`
2. Read each gateway's session user

**Expected outcome**: `soorma_env_data` exists with U4's attributes; S3 connects as `soorma_env_data`, S2 as `soorma_env_app`; both over TLS, SCRAM.

**Scope**: happy-path · **Priority**: High  
**Source**: agent-credentials / D-ID-AC-07  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-credentials/code/`  
**Technical references**: `construction/agent-credentials/infrastructure-design/infrastructure-design.md` (§5)

---

### TC-AC-091 — U5's backup round trip still passes with S3 on the stack

**Context**: D-ID-AC-16: the e2e's lists gain `e-data-gateway` (class 1).

**Scenario**: U5's backup and restore e2e on a fresh stack.

**Preconditions**:
- The local stack, fresh

**Steps**:
1. Run `pnpm test:e2e`'s backup round trip

**Expected outcome**: It passes with `e-data-gateway` stopped, removed, and restarted beside `e-control-gateway`; every U5 assertion unchanged.

**Scope**: happy-path · **Priority**: Medium  
**Source**: agent-credentials / D-ID-AC-16  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-credentials/code/`  
**Technical references**: `construction/agent-credentials/infrastructure-design/infrastructure-design.md` (§10)

---

### TC-AC-092 — The stack smoke test covers S3 in both environments

**Context**: D-ID-AC-18.

**Scenario**: `pnpm stack:smoke`.

**Preconditions**:
- The local stack

**Steps**:
1. Bootstrap and renew in E and in E2
2. Present E's credential at E2's S3

**Expected outcome**: Steps 1: `200` each. Step 2: `credential_refused`. U4's and U5's smoke checks unchanged.

**Scope**: happy-path · **Priority**: High  
**Source**: agent-credentials / D-ID-AC-18  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-credentials/code/`  
**Technical references**: `construction/agent-credentials/infrastructure-design/infrastructure-design.md` (§17)

---

### TC-AC-093 — *Done when* 2, by raw calls

**Context**: Each instance bootstraps and receives a short-lived credential, with raw calls and no SDK (D-AC-31).

**Scenario**: After *done when* 1, an instance of A and one of B bootstrap and renew.

**Preconditions**:
- The local stack; *done when* 1's registrations and secrets

**Steps**:
1. Bootstrap `a-1` for A and `b-1` for B
2. Renew each

**Expected outcome**: Each `200` with the specified bodies; two credential records and four attribution records (two per operation), each with the agent actor and sponsor H, none with a chain or origin.

**Scope**: happy-path · **Priority**: High  
**Source**: agent-credentials / M1-FR-05, 06 (done when 2)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/agent-credentials/code/`  
**Technical references**: `construction/agent-credentials/functional-design/business-logic-model.md` §6; `construction/agent-credentials/functional-design/business-rules.md` (D-AC-31)

---
