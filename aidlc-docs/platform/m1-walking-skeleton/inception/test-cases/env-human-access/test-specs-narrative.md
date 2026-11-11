# Test Specifications (Narrative): env-human-access

**Unit**: `env-human-access` (U4: environment credentials and grants for humans, control face)  
**Unit abbreviation**: EHA = env-human-access  
**Scope**: comprehensive (happy path, negative, edge and boundary), as recorded in `aidlc-state.md`  
**Derived from**: `aidlc-docs/platform/m1-walking-skeleton/inception/application-design/unit-of-work.md` and `aidlc-docs/platform/m1-walking-skeleton/inception/requirements/requirements.md` only  
**Generated**: inception pass, 2026-11-02. IDs are permanent  
**Enriched**: construction pass, 2026-11-11 (TC-EHA-001 to 024 updated in place; TC-EHA-025 to 091 added). Sources: U4's `functional-design/`, `nfr-requirements/`, `nfr-design/`, `infrastructure-design/`

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


**Values fixed by the construction pass** (2026-11-11):

| Name | Value | Source |
|---|---|---|
| Credential lifetime | 15 minutes, capped at the sign-in's current expiry | NFR-EHA-01 |
| Leeway | None on E's `exp`; E's `iat` up to 30 s ahead; sign-ins 30 s on `exp` and `iat` at the token check, A7 on S1's clock | NFR-EHA-03 |
| Throttles | 64 requests and 8 S1 calls per instance; 1 s wait; then 503, `Retry-After: 5` | NFR-EHA-04, 05 |
| S1 calls | One attempt, 2 s deadline, 64 KiB cap | NFR-EHA-07 |
| Verify keys | Refresh every 5 minutes; on demand at most once per 30 s | NFR-EHA-08 |
| Ports | S1 `127.0.0.1:8441`; E's S2 `8442`; E2's S2 `8443` | Infrastructure Design §7 |
| **stub S1** | A test double of S1's internal listener over TLS under a test CA, with scripted answers and delays, counting calls | NFR Design logical-components §6 |

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

**Expected outcome**: H holds `grant:human` and `human:manage` in E, recorded with *granted-by* = configuration. *(Construction pass)* At S2's start-up, E's store holds one `grants` row for H: `granted_by_kind` `configuration`, `permissions` `[grant:human, human:manage]`, `self_grant` false. Beside it is one attribution record: actor `configuration`, operation `configureFirstGrant`, no request id. `first_grant.applied` is logged. A restart writes nothing more (TC-EHA-035).

**Scope**: happy-path · **Priority**: High  
**Source**: env-human-access / M1-FR-14, M1-FR-12  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/env-human-access/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; construction pass: `construction/env-human-access/functional-design/business-rules.md` (BR-FG-01 to 03); `construction/env-human-access/nfr-design/nfr-design-patterns.md` (NP-EHA-08)

---

### TC-EHA-002 — An environment credential is issued from a live sign-in

**Context**: E issues a credential against a live sign-in to an `active` principal holding at least one grant in E (M1-FR-20).

**Scenario**: H, holding a sign-in, requests a credential for E.

**Preconditions**:
- E's control-gateway is running, alongside the organization level
- H is `active`, holds a live sign-in, and holds a grant in E

**Steps**:
1. Call `issueEnvironmentCredential` at E, presenting the sign-in

**Expected outcome**: An environment credential bound to E is returned, with an expiry no later than the sign-in's. *(Construction pass)* 200 with `{ credential, expiresAt }`. `credential` is `soorma_ec_` followed by a JWS: header `alg` `Ed25519`, `typ` `soorma-ec+jwt`, `kid`; claims `env` `{ organization: o1, project: p1, environment: e }`, `sub` H, `cid`, `jti`, `iat`, `exp`. `expiresAt` equals `exp`, the earlier of `iat` + 15 minutes and the sign-in's current expiry. One `credentials` row (`live`, `issued_from` the sign-in's `sid`) and one attribution record (human actor, credential kind `signIn`) are committed together. `credential.issued` is logged, and **exactly one** `signInStatus` call is made.

**Scope**: happy-path · **Priority**: High  
**Source**: env-human-access / M1-FR-20  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/env-human-access/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; construction pass: `construction/env-human-access/functional-design/business-rules.md` (BR-IS-01 to 04, BR-EC-01, 04; D-EHA-22); `construction/env-human-access/nfr-design/nfr-design-patterns.md` (NP-EHA-01, 03); `construction/env-human-access/nfr-requirements/nfr-requirements.md` (NFR-EHA-01)

---

### TC-EHA-003 — H renews their environment credential

**Context**: The environment credential is renewable (M1-FR-20).

**Scenario**: H renews a live environment credential.

**Preconditions**:
- E's control-gateway is running, alongside the organization level
- H holds a live environment credential for E, and its sign-in is live

**Steps**:
1. Call `renewEnvironmentCredential`, presenting it

**Expected outcome**: A renewed credential for E is returned. Its authority is unchanged. *(Construction pass)* 200 with a new token: the same `cid`, a new `jti`, and `exp` the earlier of now + 15 minutes and the sign-in's current expiry. The record's `expires_at` is updated by a conditional update while `live`, with an attribution record (credential kind `environmentCredential`). One `signInStatus` call is made. No authority is added (TC-EHA-026).

**Scope**: happy-path · **Priority**: Medium  
**Source**: env-human-access / M1-FR-20  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/env-human-access/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; construction pass: `construction/env-human-access/functional-design/business-rules.md` (BR-EC-04, 05); `construction/env-human-access/nfr-design/nfr-design-patterns.md` (NP-EHA-09)

---

### TC-EHA-004 — H ends their own environment credential

**Context**: Ending one's own environment credential is part of the logout (M1-FR-21).

**Scenario**: H ends a live environment credential.

**Preconditions**:
- E's control-gateway is running, alongside the organization level
- H holds a live environment credential for E

**Steps**:
1. Call `endEnvironmentCredential`, presenting it

**Expected outcome**: The end succeeds. *(Construction pass)* 204, no body. The record becomes `ended`, with `ended_by` `self` and `ended_at` set, and an attribution record in the same transaction. **No call to S1 is made.** Every token of the credential is `credential_refused` from then on (TC-EHA-014). Ending is the logout in E (BR-EC-09; SECURITY-12).

**Scope**: happy-path · **Priority**: High  
**Source**: env-human-access / M1-FR-21  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/env-human-access/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; construction pass: `construction/env-human-access/functional-design/business-rules.md` (BR-EC-07, 09; D-EHA-25)

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

**Expected outcome**: H holds the three permissions. The grant is attributed to H with the credential presented, no origin mode, and marked as a self-grant. *(Construction pass)* 200 with the Grant (`id`, `target`, `permissions`, `grantedAt`, `selfGrant` true). The `grants` row has `granted_by_principal` H, `granted_by_credential` the presented credential's `cid`, and `self_grant` true. The attribution record also has `self_grant` true, and `grant.made` is logged. The permissions are usable on H's next request (TC-EHA-027).

**Scope**: happy-path · **Priority**: High  
**Source**: env-human-access / M1-FR-15, M1-FR-12  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/env-human-access/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; construction pass: `construction/env-human-access/functional-design/business-rules.md` (BR-GR-05, 08); `construction/env-human-access/nfr-design/nfr-design-patterns.md` (NP-EHA-07, 10)

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

**Expected outcome**: H2 holds `event:subscribe` in E. The grant is attributed to H and not marked as a self-grant. *(Construction pass)* 200, `selfGrant` false. Exactly one `principalExists` call is made, for the target, after the authority check (BR-GR-04).

**Scope**: happy-path · **Priority**: Medium  
**Source**: env-human-access / M1-FR-15  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/env-human-access/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; construction pass: `construction/env-human-access/functional-design/business-rules.md` (BR-GR-03 to 05)

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

**Expected outcome**: Succeeds. *(Construction pass)* 200. Nothing compares the granted set with H's own: only `grant:human` is evaluated (BR-GR-03).

**Scope**: happy-path · **Priority**: High  
**Source**: env-human-access / M1-FR-15  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/env-human-access/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; construction pass: `construction/env-human-access/functional-design/business-rules.md` (BR-GR-03)

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

**Expected outcome**: Succeeds. *(Construction pass)* 200 for `grant:human`, `human:manage`, and `agent:delegate`: P3's human-only refusal applies to agents only (BR-EV-03), and all three are among the nine accepted identifiers (BR-ACC-01).

**Scope**: edge-boundary · **Priority**: Medium  
**Source**: env-human-access / M1-FR-15  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/env-human-access/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; construction pass: `construction/env-human-access/functional-design/business-rules.md` (BR-EV-03, BR-ACC-01)

---

### TC-EHA-009 — The organization sign-in is refused everywhere in E except issuance

**Context**: The sign-in is refused at every environment's perimeter except that environment's credential issuance (M1-FR-19, M1-FR-09).

**Scenario**: H presents the sign-in itself to a control operation.

**Preconditions**:
- E's control-gateway is running, alongside the organization level
- H holds a live sign-in and the needed grants

**Steps**:
1. Call `grantToHuman`, presenting the sign-in instead of an environment credential

**Expected outcome**: Refused. No grant is made. *(Construction pass)* `credential_refused` (401, `WWW-Authenticate: Bearer`) on renewal, ending, and `grantToHuman`, and `credential.refused` logged. At issuance the same sign-in is accepted (BR-PR-02).

**Scope**: negative · **Priority**: High  
**Source**: env-human-access / M1-FR-09, M1-FR-19  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/env-human-access/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; construction pass: `construction/env-human-access/functional-design/business-rules.md` (BR-PR-02; BR-RF-04)

---

### TC-EHA-010 — E's credential is refused in E2

**Context**: An environment credential is accepted only in the environment that issued it (O4, M1-FR-20).

**Scenario**: H presents E's credential to E2's control-gateway.

**Preconditions**:
- E and E2 running
- H holds a live environment credential for E

**Steps**:
1. Call `grantToHuman` at E2, presenting E's credential

**Expected outcome**: Refused, without disclosing anything about E2. *(Construction pass)* `credential_refused` (401) at E2's renewal, ending, and `grantToHuman`. E2's key ring holds no key with E's `kid`, so verification stops before `exp` is read, and **no expiry is disclosed** (BR-EC-03; NP-EHA-01 step 3). E's and E2's rings come from distinct secrets.

**Scope**: negative · **Priority**: High  
**Source**: env-human-access / M1-FR-20, M1-FR-10  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/env-human-access/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; construction pass: `construction/env-human-access/functional-design/business-rules.md` (BR-EC-03); `construction/env-human-access/nfr-design/nfr-design-patterns.md` (NP-EHA-01, 02)

---

### TC-EHA-011 — A principal holding no grant in E gets no credential

**Context**: Issuance requires at least one grant in E (M1-FR-20).

**Scenario**: H2, active with no grant in E, requests a credential for E.

**Preconditions**:
- E's control-gateway is running, alongside the organization level
- H2 is `active`, holds a live sign-in, and holds no grant in E

**Steps**:
1. Call `issueEnvironmentCredential` at E, presenting H2's sign-in

**Expected outcome**: Refused. *(Construction pass)* `forbidden` (403). No credential row and no attribution record; `credential.refused` is logged with reason `no_grant_in_environment`.

**Scope**: negative · **Priority**: High  
**Source**: env-human-access / M1-FR-20  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/env-human-access/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; construction pass: `construction/env-human-access/functional-design/business-rules.md` (BR-EC-01, BR-EV-02, BR-RF-03)

---

### TC-EHA-012 — Granting without `grant:human` is denied

**Context**: Granting to a human needs `grant:human` in E (M1-FR-15).

**Scenario**: H2, holding an environment credential for E but not `grant:human`, tries to grant.

**Preconditions**:
- E's control-gateway is running, alongside the organization level
- H2 holds a credential for E and only `event:subscribe`

**Steps**:
1. Call `grantToHuman` with target H2 and {`agent:register`}

**Expected outcome**: Denied. *(Construction pass)* `forbidden` (403). No grant row, `grant.denied` logged, and **no `principalExists` call**: authority precedes the target check, so a non-Admin learns nothing about existence (BR-GR-04; BR-RF-02).

**Scope**: negative · **Priority**: High  
**Source**: env-human-access / M1-FR-15, M1-FR-08  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/env-human-access/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; construction pass: `construction/env-human-access/functional-design/business-rules.md` (BR-GR-03, 04; BR-RF-02)

---

### TC-EHA-013 — A permission identifier that is not plane-declared is rejected

**Context**: Only plane-declared identifiers are accepted. This is a recorded delivery limit (M1-FR-15, the GAP-INT-006 work-around).

**Scenario**: H grants an identifier no plane PRD declares.

**Preconditions**:
- E's control-gateway is running, alongside the organization level
- H holds `grant:human` in E

**Steps**:
1. Call `grantToHuman` with target H and {`invoice:approve`}

**Expected outcome**: Rejected, naming the identifier. No grant is made. *(Construction pass)* `unknown_permission` (400) with one `errors[]` pointer per unaccepted identifier (`/permissions/{i}`), checked at step 6, before authority. No grant is written. The accepted set is the nine plane-declared identifiers (BR-ACC-01).

**Scope**: negative · **Priority**: High  
**Source**: env-human-access / M1-FR-15 (GAP-INT-006)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/env-human-access/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; construction pass: `construction/env-human-access/functional-design/business-rules.md` (BR-GR-02, BR-ACC-01 to 03; D-EHA-06)

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

**Expected outcome**: The second call is refused. *(Construction pass)* `credential_refused` (401) at renewal, ending, and `grantToHuman`, read from the record uncached (O3; NP-EHA-01 step 9).

**Scope**: negative · **Priority**: High  
**Source**: env-human-access / M1-FR-21, M1-FR-07  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/env-human-access/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; construction pass: `construction/env-human-access/functional-design/business-rules.md` (BR-EC-02, 07); `construction/env-human-access/nfr-design/nfr-design-patterns.md` (NP-EHA-01)

---

### TC-EHA-015 — An agent credential is refused at the control gateway

**Context**: No control operation accepts an agent credential in M1 (M1-FR-09). Agent-initiated control operations are absent.

**Scenario**: An instance of A presents its agent credential to a control operation.

**Preconditions**:
- E's control-gateway is running, alongside the organization level
- A holds an agent credential for E

**Steps**:
1. Call `grantToHuman`, presenting A's agent credential

**Expected outcome**: Refused. *(Construction pass)* `credential_refused` (401) **by kind, without verifying**: no M1 operation at S2 takes `soorma_ac_` (BR-PR-04).

**Scope**: negative · **Priority**: High  
**Source**: env-human-access / M1-FR-09  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/env-human-access/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; construction pass: `construction/env-human-access/functional-design/business-rules.md` (BR-PR-04)

---

### TC-EHA-016 — An agent credential presented beside a human credential is refused

**Context**: An agent credential presented beside a human's credential is refused (M1-FR-09).

**Scenario**: A request carries both H's environment credential and A's agent credential.

**Preconditions**:
- E's control-gateway is running, alongside the organization level

**Steps**:
1. Call `grantToHuman`, presenting both credentials

**Expected outcome**: Refused. *(Construction pass)* `credential_refused` (401): two credentials on one request (BR-PR-01, 05).

**Scope**: negative · **Priority**: High  
**Source**: env-human-access / M1-FR-09  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/env-human-access/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; construction pass: `construction/env-human-access/functional-design/business-rules.md` (BR-PR-01, 05)

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

**Expected outcome**: Both are refused. *(Construction pass)* `credential_expired` (401) at renewal, ending, and `grantToHuman`, reported only after the signature verifies. A credential is expired **at** `exp`, with no leeway (NFR-EHA-03).

**Scope**: negative · **Priority**: Medium  
**Source**: env-human-access / M1-FR-20  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/env-human-access/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; construction pass: `construction/env-human-access/functional-design/business-rules.md` (BR-EC-02, 06); `construction/env-human-access/nfr-requirements/nfr-requirements.md` (NFR-EHA-03)

---

### TC-EHA-018 — A grant to a non-existent principal is rejected

**Context**: A grant names a human principal of the organization (M1-FR-15).

**Scenario**: H grants to an identifier that is not a principal of O.

**Preconditions**:
- E's control-gateway is running, alongside the organization level
- H holds `grant:human`

**Steps**:
1. Call `grantToHuman` with an unknown target and {`event:publish`}

**Expected outcome**: Rejected, and no grant is recorded. *(Construction pass)* `unknown_principal` (400) with an `errors[]` pointer `/target`, after authority. One `principalExists` call is made, and no grant is written.

**Scope**: negative · **Priority**: Medium  
**Source**: env-human-access / M1-FR-15  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/env-human-access/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; construction pass: `construction/env-human-access/functional-design/business-rules.md` (BR-GR-04; D-EHA-05)

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

**Expected outcome**: The expiry is no later than the sign-in's, and renewal after the sign-in expires is refused. *(Construction pass)* The expiry is the earlier of `iat` + 15 minutes and the sign-in's current expiry (NFR-EHA-01). After the sign-in expires, renewal is `credential_refused`, because `signInStatus` (A7) answers `ended` for an expired sign-in.

**Scope**: edge-boundary · **Priority**: High  
**Source**: env-human-access / M1-FR-20  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/env-human-access/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; construction pass: `construction/env-human-access/functional-design/business-rules.md` (BR-EC-04, 05; D-EHA-02); `construction/env-human-access/nfr-requirements/nfr-requirements.md` (NFR-EHA-01)

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

**Expected outcome**: Refused. *(Construction pass)* `credential_refused` (401), because A7 answers `ended`. The credential itself still passes O1 to O4 until its own expiry (D-EHA-01; TC-EHA-029).

**Scope**: edge-boundary · **Priority**: High  
**Source**: env-human-access / M1-FR-20, M1-FR-21  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/env-human-access/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; construction pass: `construction/env-human-access/functional-design/business-rules.md` (BR-EC-05, 08; D-EHA-01)

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

**Expected outcome**: The grant succeeds. The record names H and the credential, with scope E and no origin mode or chain. *(Construction pass)* The attribution record has `actor_kind` `human`, `principal` H, `credential_kind` and `credential_id`, and null `chain`, `origin`, and re-broadening columns. The store's CHECK constraints refuse any other combination (TC-EHA-047).

**Scope**: edge-boundary · **Priority**: Medium  
**Source**: env-human-access / M1-FR-12, M1-FR-09  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/env-human-access/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; construction pass: `construction/env-human-access/functional-design/business-rules.md` (BR-AT-02, 05); `construction/env-human-access/nfr-design/nfr-design-patterns.md` (NP-EHA-07)

---

### TC-EHA-022 — E holds only verify-only material for the organization sign-in

**Context**: Environments hold verify-only material for the organization sign-in, never material that can mint (M1-FR-10).

**Scenario**: A reviewer inspects E's sign-in material, and tries to have E mint a sign-in.

**Preconditions**:
- E's control-gateway is running, alongside the organization level

**Steps**:
1. Inspect the sign-in material in E's store and configuration
2. Look for any E operation that issues a sign-in

**Expected outcome**: E holds only verification material, and no E operation issues a sign-in. *(Construction pass)* No E container holds the organization's signing key: `org-signing-key` is mounted only into `org-gateway` (TC-EHA-079). S2 holds S1's **public** verify keys, fetched over `GET /verify-keys` (NP-EHA-03).

**Scope**: edge-boundary · **Priority**: High  
**Source**: env-human-access / M1-FR-10  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/env-human-access/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; construction pass: `construction/env-human-access/infrastructure-design/infrastructure-design.md` (§3); `construction/env-human-access/nfr-design/nfr-design-patterns.md` (NP-EHA-03)

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

**Expected outcome**: Refused. *(Construction pass)* `unavailable` (503) with `Retry-After: 5`, and `store.unavailable` logged. It is never a pass (BR-EC-02, BR-EV-06).

**Scope**: edge-boundary · **Priority**: High  
**Source**: env-human-access / M1-FR-07  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/env-human-access/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; construction pass: `construction/env-human-access/functional-design/business-rules.md` (BR-EC-02, BR-EV-06); `construction/env-human-access/nfr-requirements/nfr-requirements.md` (NFR-EHA-04 to 07)

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

**Expected outcome**: Every one of the unit's operations is present and references the conventions. The violating request is rejected with the contract's error model before any processing. *(Construction pass)* `contract/control-gateway.openapi.yaml` defines `POST /environment-credentials`, `/environment-credentials/current/renewal`, `/environment-credentials/current/end`, and `/grants`, with statuses 200, 200, 204, and 200, each naming exactly one security scheme. `ProblemCode` gains `unknown_principal` and `unknown_permission`. Every Problem S2 emits passes `assertProblem`.

**Scope**: happy-path · **Priority**: High  
**Source**: env-human-access / M1-FR-02  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/env-human-access/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; construction pass: `construction/env-human-access/functional-design/business-rules.md` (§12, §13; D-EHA-22, 25)

---

### TC-EHA-025 — Issuance from an ended sign-in is refused

**Context**: Issuance needs a live sign-in; `signInStatus` (A7) is called at issuance (BR-IS-03).

**Scenario**: H ends their sign-in at S1, then asks E for a credential with it.

**Preconditions**:
- The local stack is running (`pnpm stack:up`): S1 at `127.0.0.1:8441`, E's S2 at `127.0.0.1:8442`, E2's S2 at `127.0.0.1:8443`
- H is `active` and holds a live sign-in from S1, and the grants E's configuration gives the first Admin

**Steps**:
1. Call S1 `endSignIn` with the sign-in
2. Call E's `issueEnvironmentCredential` with the same sign-in

**Expected outcome**: Step 2 is `credential_refused` (401): A7 answers `ended`. No credential row and no attribution record; `credential.refused` logged with reason `sign_in_ended`.

**Scope**: negative · **Priority**: High  
**Source**: env-human-access / M1-FR-20 (BR-IS-03)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/env-human-access/code/`  
**Technical references**: `construction/env-human-access/functional-design/business-rules.md` (BR-IS-03)

---

### TC-EHA-026 — A grant made after issuance applies at once, and renewal adds nothing

**Context**: The credential carries no permissions (D-EHA-10). Authority is read uncached from grants on each request (D-EHA-14).

**Scenario**: H holds a credential; another human, J, is granted `grant:human` after J's credential was issued.

**Preconditions**:
- The local stack is running (`pnpm stack:up`): S1 at `127.0.0.1:8441`, E's S2 at `127.0.0.1:8442`, E2's S2 at `127.0.0.1:8443`
- H is `active` and holds a live sign-in from S1, and the grants E's configuration gives the first Admin
- J is `active`, holds one grant in E (any accepted permission, not `grant:human`), and holds a credential for E

**Steps**:
1. J calls `grantToHuman`: forbidden
2. H grants J `grant:human`
3. J calls `grantToHuman` again with the **same** credential
4. J renews; inspect the new token's claims

**Expected outcome**: Step 1 is `forbidden`; step 3 succeeds with no renewal; the renewed token in step 4 has exactly the claims `env`, `sub`, `cid`, `jti`, `iat`, `exp`, and no permission claim.

**Scope**: edge-boundary · **Priority**: High  
**Source**: env-human-access / M1-FR-20, M1-FR-15 (D-EHA-10, 14)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/env-human-access/code/`  
**Technical references**: `construction/env-human-access/functional-design/business-rules.md` (D-EHA-10, 14; BR-GR-08)

---

### TC-EHA-027 — A self-grant is usable on the next request

**Context**: Read-your-writes for the actor (ID §10; BR-GR-08).

**Scenario**: H self-grants `agent:register`.

**Preconditions**:
- S2's modules run in-process against a test environment store (PostgreSQL 18, migrated by the real runner), a stub S1 over TLS under a test CA, and an injected clock and scheduler
- H holds a credential for E, and `grant:human`

**Steps**:
1. H grants themselves `agent:register`
2. Immediately evaluate `evaluateHuman(H, agent:register)` through P3 over P4's `GrantSource`

**Expected outcome**: Allowed on the first evaluation after the grant's commit; nothing is cached between the two.

**Scope**: edge-boundary · **Priority**: High  
**Source**: env-human-access / M1-FR-15 (BR-GR-08; NFR-EHA-10)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/env-human-access/code/`  
**Technical references**: `construction/env-human-access/functional-design/business-rules.md` (BR-GR-08); `construction/env-human-access/nfr-design/nfr-design-patterns.md` (NP-EHA-10)

---

### TC-EHA-028 — A renewed sign-in extends renewal of the credential

**Context**: A7 reports the sign-in's current expiry; each renewal caps at it (D-EHA-02; BR-EC-04).

**Scenario**: H's sign-in has 6 minutes left; H renews the sign-in at S1, then renews the credential.

**Preconditions**:
- S2's modules run in-process against a test environment store (PostgreSQL 18, migrated by the real runner), a stub S1 over TLS under a test CA, and an injected clock and scheduler
- The stub S1 answers `signInStatus` with `{ status: 'live', expiresAt }`, scripted per step
- H holds a credential whose expiry was capped at the sign-in's expiry (6 minutes)

**Steps**:
1. Script `expiresAt` = now + 15 minutes (the sign-in was renewed)
2. Renew the credential

**Expected outcome**: The new token's `exp` is now + 15 minutes: the cap moved with the sign-in. It never moves earlier than the previous expiry.

**Scope**: happy-path · **Priority**: High  
**Source**: env-human-access / M1-FR-20 (D-EHA-02; A7)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/env-human-access/code/`  
**Technical references**: `construction/env-human-access/functional-design/business-rules.md` (BR-EC-04, 05); `construction/env-human-access/nfr-requirements/nfr-requirements.md` (NFR-EHA-01)

---

### TC-EHA-029 — A credential stays usable after its sign-in ends, until its own expiry

**Context**: The accepted residual (D-EHA-01; Functional Design §16): ending a sign-in bars renewal and issuance, not use. Bounded at 15 minutes (NFR-EHA-02).

**Scenario**: H logs out at S1 only.

**Preconditions**:
- The local stack is running (`pnpm stack:up`): S1 at `127.0.0.1:8441`, E's S2 at `127.0.0.1:8442`, E2's S2 at `127.0.0.1:8443`
- H is `active` and holds a live sign-in from S1, and the grants E's configuration gives the first Admin
- H holds a credential for E

**Steps**:
1. Call S1 `endSignIn`
2. Call `grantToHuman` with the credential
3. Call `renewEnvironmentCredential`
4. Call `endEnvironmentCredential`
5. Call `grantToHuman` again

**Expected outcome**: Step 2 succeeds; step 3 is `credential_refused` (A7 `ended`); step 4 is 204; step 5 is `credential_refused`. With an injected clock, the credential is `credential_expired` at its `exp` if not ended.

**Scope**: edge-boundary · **Priority**: High  
**Source**: env-human-access / M1-FR-21 (D-EHA-01; NFR-EHA-02)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/env-human-access/code/`  
**Technical references**: `construction/env-human-access/functional-design/business-rules.md` (§16; BR-EC-08, 09); `construction/env-human-access/nfr-requirements/nfr-requirements.md` (NFR-EHA-02)

---

### TC-EHA-030 — Renewal racing an end, and two concurrent ends, each commit exactly one outcome

**Context**: Renewal and ending are conditional updates on `state = 'live'` (D-EHA-26; NP-EHA-09).

**Scenario**: Two requests on one credential arrive together.

**Preconditions**:
- S2's modules run in-process against a test environment store (PostgreSQL 18, migrated by the real runner), a stub S1 over TLS under a test CA, and an injected clock and scheduler

**Steps**:
1. Run `renewEnvironmentCredential` and `endEnvironmentCredential` concurrently on one credential, 50 times
2. Run two `endEnvironmentCredential` concurrently on one credential, 50 times

**Expected outcome**: In step 1, either the end wins (renewal `credential_refused`, no renewal record) or the renewal wins and the end then succeeds: never a renewed, ended credential with two records. In step 2, exactly one 204 and one `credential_refused`; exactly one attribution record per success.

**Scope**: edge-boundary · **Priority**: High  
**Source**: env-human-access / M1-FR-21 (D-EHA-26)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/env-human-access/code/`  
**Technical references**: `construction/env-human-access/nfr-design/nfr-design-patterns.md` (NP-EHA-09)

---

### TC-EHA-031 — Ending, O3, and authority make no organization-level call

**Context**: The organization level is on no per-request path (ID FR-009; D-EHA-23; BR-OL-04).

**Scenario**: The stub S1 counts every call.

**Preconditions**:
- S2's modules run in-process against a test environment store (PostgreSQL 18, migrated by the real runner), a stub S1 over TLS under a test CA, and an injected clock and scheduler

**Steps**:
1. End a credential
2. Call `grantToHuman` as a non-Admin (denied at authority)
3. Present an ended credential

**Expected outcome**: The stub records zero calls for all three. Only issuance, renewal (`signInStatus`), a grant's target check (`principalExists`), and the key fetch ever call S1.

**Scope**: edge-boundary · **Priority**: High  
**Source**: env-human-access / M1-FR-09 (D-EHA-23; BR-OL-04)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/env-human-access/code/`  
**Technical references**: `construction/env-human-access/functional-design/business-rules.md` (BR-OL-01, 04)

---

### TC-EHA-032 — A delegation header, or a second Authorization header, is refused

**Context**: Exactly one `Authorization: Bearer` and no `Soorma-Delegation` (BR-PR-01), counted on the raw header list.

**Scenario**: Raw requests with extra credential headers.

**Preconditions**:
- The local stack is running (`pnpm stack:up`): S1 at `127.0.0.1:8441`, E's S2 at `127.0.0.1:8442`, E2's S2 at `127.0.0.1:8443`
- H is `active` and holds a live sign-in from S1, and the grants E's configuration gives the first Admin
- H holds a credential for E

**Steps**:
1. Send `grantToHuman` with the credential plus `Soorma-Delegation: anything`
2. Send it with two `Authorization` headers carrying the same credential
3. Send it with `authorization` in lower case once

**Expected outcome**: Steps 1 and 2 are `credential_refused` (401); step 3 succeeds (header names are case-insensitive).

**Scope**: negative · **Priority**: High  
**Source**: env-human-access / M1-FR-09 (BR-PR-01)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/env-human-access/code/`  
**Technical references**: `construction/env-human-access/functional-design/business-rules.md` (BR-PR-01)

---

### TC-EHA-033 — An environment credential is refused at issuance

**Context**: `soorma_ec_` is accepted only on renewal, ending, and `grantToHuman` (BR-PR-03).

**Scenario**: H presents an environment credential to the issuance operation.

**Preconditions**:
- The local stack is running (`pnpm stack:up`): S1 at `127.0.0.1:8441`, E's S2 at `127.0.0.1:8442`, E2's S2 at `127.0.0.1:8443`
- H is `active` and holds a live sign-in from S1, and the grants E's configuration gives the first Admin
- H holds a credential for E

**Steps**:
1. Call `issueEnvironmentCredential` with the environment credential

**Expected outcome**: `credential_refused` (401); nothing is issued.

**Scope**: negative · **Priority**: Medium  
**Source**: env-human-access / M1-FR-09 (BR-PR-03)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/env-human-access/code/`  
**Technical references**: `construction/env-human-access/functional-design/business-rules.md` (BR-PR-03)

---

### TC-EHA-034 — Malformed or unknown-kind credentials are refused by kind

**Context**: Syntax and prefix are checked before any verification (BR-PR-04, 06; BR-CR-05).

**Scenario**: Raw requests with bad credentials.

**Preconditions**:
- The local stack is running (`pnpm stack:up`): S1 at `127.0.0.1:8441`, E's S2 at `127.0.0.1:8442`, E2's S2 at `127.0.0.1:8443`

**Steps**:
1. Send `grantToHuman` with each: a 4097-character `soorma_ec_` token; a token with a space; `soorma_dc_x`; `soorma_xx_x`; `Bearer` with nothing after it

**Expected outcome**: Each is `credential_refused` (401); none reaches verification or the store (no store query is logged).

**Scope**: negative · **Priority**: High  
**Source**: env-human-access / M1-FR-09 (BR-PR-04, 06)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/env-human-access/code/`  
**Technical references**: `construction/env-human-access/functional-design/business-rules.md` (BR-PR-04, 06, 07)

---

### TC-EHA-035 — Two concurrent start-ups write one configuration grant and one record; a restart writes nothing

**Context**: At most one configuration grant per principal in E, by a partial unique index (BR-FG-02; NP-EHA-08). The user's concurrency test.

**Scenario**: Two S2 instances start together against one fresh store.

**Preconditions**:
- A test environment store (PostgreSQL 18), migrated by `env-store`'s migrations through the shared runner, fresh

**Steps**:
1. Start two S2 runtimes concurrently against the store, 20 times on fresh stores
2. Restart one of them

**Expected outcome**: Each time: exactly one `grants` row with `granted_by_kind` `configuration` for H, exactly one attribution record with operation `configureFirstGrant`, and both runtimes start. Step 2 writes nothing.

**Scope**: edge-boundary · **Priority**: High  
**Source**: env-human-access / M1-FR-14 (D-EHA-07; BR-FG-02)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/env-human-access/code/`  
**Technical references**: `construction/env-human-access/nfr-design/nfr-design-patterns.md` (NP-EHA-08); `construction/env-human-access/nfr-requirements/nfr-requirements.md` (NFR-EHA-12)

---

### TC-EHA-036 — S2 refuses to start on a bad key ring

**Context**: E's key ring comes from configuration; start-up fails closed (NP-EHA-02; D-EHA-28).

**Scenario**: S2's configuration is broken in one way at a time.

**Preconditions**:
- A test environment store (PostgreSQL 18), migrated by `env-store`'s migrations through the shared runner
- A valid `controlGateway` configuration for E

**Steps**:
1. Start S2 with each fault in turn: the signing key file missing; a P-256 key as the signing key; `signing` not listed in `verify`; two `verify` entries holding one key (one `kid`); the caller key missing; the log-pseudonym key missing

**Expected outcome**: Each start-up exits non-zero with a configuration error naming the item and no secret value; nothing is written to the store.

**Scope**: negative · **Priority**: High  
**Source**: env-human-access / M1-FR-10 (NP-EHA-02; D-EHA-28)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/env-human-access/code/`  
**Technical references**: `construction/env-human-access/nfr-design/nfr-design-patterns.md` (NP-EHA-02); `construction/env-human-access/infrastructure-design/infrastructure-design.md` (§3)

---

### TC-EHA-037 — S2 refuses to start if the first grant cannot be written

**Context**: A first grant that cannot be written stops S2 (BR-FG-05; D-EHA-28).

**Scenario**: The store refuses the write.

**Preconditions**:
- A test environment store (PostgreSQL 18), migrated by `env-store`'s migrations through the shared runner, with the app role's `INSERT` on `grants` revoked for the test

**Steps**:
1. Start S2

**Expected outcome**: Start-up exits non-zero; no listener opens; no attribution record is written.

**Scope**: negative · **Priority**: Medium  
**Source**: env-human-access / M1-FR-14 (BR-FG-05)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/env-human-access/code/`  
**Technical references**: `construction/env-human-access/functional-design/business-rules.md` (BR-FG-05)

---

### TC-EHA-038 — `unknown_permission` reports at most 10 pointers

**Context**: One pointer per unaccepted identifier, at most 10 (D-EHA-06).

**Scenario**: A grant names 12 unaccepted identifiers.

**Preconditions**:
- The local stack is running (`pnpm stack:up`): S1 at `127.0.0.1:8441`, E's S2 at `127.0.0.1:8442`, E2's S2 at `127.0.0.1:8443`
- H is `active` and holds a live sign-in from S1, and the grants E's configuration gives the first Admin
- H holds a credential for E

**Steps**:
1. Call `grantToHuman` with 12 well-formed, unaccepted identifiers and 2 accepted ones

**Expected outcome**: `unknown_permission` (400) with exactly 10 `errors[]` entries, pointing at the first 10 unaccepted identifiers in order; no grant written.

**Scope**: edge-boundary · **Priority**: Medium  
**Source**: env-human-access / M1-FR-15 (D-EHA-06)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/env-human-access/code/`  
**Technical references**: `construction/env-human-access/functional-design/business-rules.md` (D-EHA-06; BR-GR-02)

---

### TC-EHA-039 — A malformed grant body is rejected with pointers

**Context**: The body is closed: `target` and `permissions` (1 to 32, unique) (BR-GR-01).

**Scenario**: Raw grant bodies with schema faults.

**Preconditions**:
- The local stack is running (`pnpm stack:up`): S1 at `127.0.0.1:8441`, E's S2 at `127.0.0.1:8442`, E2's S2 at `127.0.0.1:8443`
- H is `active` and holds a live sign-in from S1, and the grants E's configuration gives the first Admin
- H holds a credential for E

**Steps**:
1. Send each: no `target`; an extra top-level field; 33 permissions; a duplicate permission; an empty `permissions`; a permission violating the identifier pattern

**Expected outcome**: Each is `malformed_request` (400) with a pointer to the offending field; none reaches authority (no `grant.denied`, no S1 call).

**Scope**: negative · **Priority**: High  
**Source**: env-human-access / M1-FR-15 (BR-GR-01)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/env-human-access/code/`  
**Technical references**: `construction/env-human-access/functional-design/business-rules.md` (BR-GR-01)

---

### TC-EHA-040 — Every environment-store access path constrains on the environment

**Context**: Every row carries its environment and every statement constrains on it (D-EHA-29; NP-EHA-06).

**Scenario**: Rows under E2's identity are planted in E's store.

**Preconditions**:
- S2's modules run in-process against a test environment store (PostgreSQL 18, migrated by the real runner), a stub S1 over TLS under a test CA, and an injected clock and scheduler

**Steps**:
1. Insert, as the migrator, a credential, a grant for H, and an attribution record carrying E2's identity into E's store
2. Present that credential's token, minted with E's key but naming the planted `cid`
3. Evaluate H's held set in E
4. Run every P4, P5, and P7 read

**Expected outcome**: The token is `credential_refused` (record not found for E); the planted grant is not in H's held set; no read returns a planted row. A review rule lists every statement with its environment predicate.

**Scope**: edge-boundary · **Priority**: High  
**Source**: env-human-access / M1-FR-10 (D-EHA-29; I1)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/env-human-access/code/`  
**Technical references**: `construction/env-human-access/nfr-design/nfr-design-patterns.md` (NP-EHA-06)

---

### TC-EHA-041 — A grant target in another organization is `unknown_principal`, with no organization-level call

**Context**: Another organization's principal does not exist for E (BR-GR-04; D-EHA-16).

**Scenario**: H grants to `{ organization: o2, principal: h@example.com }`.

**Preconditions**:
- S2's modules run in-process against a test environment store (PostgreSQL 18, migrated by the real runner), a stub S1 over TLS under a test CA, and an injected clock and scheduler
- H holds `grant:human` in E

**Steps**:
1. Call `grantToHuman` with the other-organization target

**Expected outcome**: `unknown_principal` (400), pointer `/target`; the stub S1 records no call.

**Scope**: negative · **Priority**: High  
**Source**: env-human-access / M1-FR-15 (BR-GR-04)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/env-human-access/code/`  
**Technical references**: `construction/env-human-access/functional-design/business-rules.md` (BR-GR-04)

---

### TC-EHA-042 — A non-Admin cannot probe whether a principal exists

**Context**: Only an Admin in E learns existence; authority precedes the target check (BR-GR-04; BR-RF-02).

**Scenario**: J, without `grant:human`, grants to an existing and a non-existent principal.

**Preconditions**:
- The local stack is running (`pnpm stack:up`): S1 at `127.0.0.1:8441`, E's S2 at `127.0.0.1:8442`, E2's S2 at `127.0.0.1:8443`
- J is `active`, holds a credential for E, and lacks `grant:human`

**Steps**:
1. J grants to H (exists)
2. J grants to `nobody@example.com` (absent)

**Expected outcome**: Both are `forbidden` (403) with identical bodies apart from the request id; S1 receives no `principalExists` call.

**Scope**: negative · **Priority**: High  
**Source**: env-human-access / M1-FR-15 (BR-RF-02)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/env-human-access/code/`  
**Technical references**: `construction/env-human-access/functional-design/business-rules.md` (BR-GR-04; BR-RF-02; §15)

---

### TC-EHA-043 — An unreachable or misbehaving S1 makes S2 answer `unavailable`, after one attempt

**Context**: The S1 caller fails closed with no retry, a 2-second deadline, a 64 KiB cap, a shape check, and the local CA as the only trust root (D-EHA-27; NP-EHA-04).

**Scenario**: The stub S1 misbehaves in one way at a time.

**Preconditions**:
- S2's modules run in-process against a test environment store (PostgreSQL 18, migrated by the real runner), a stub S1 over TLS under a test CA, and an injected clock and scheduler

**Steps**:
1. For issuance, renewal, and `grantToHuman`, script the stub to: refuse the connection; answer at 2.001 s (clock-controlled); answer 500; answer `{ status: 'live' }` without `expiresAt`; add an extra field; send 65 KiB; present a certificate from another CA; present a certificate for another name

**Expected outcome**: Each is `unavailable` (503) with `Retry-After: 5` and `orglevel.unavailable` logged; the stub records exactly one attempt per request; nothing is written.

**Scope**: negative · **Priority**: High  
**Source**: env-human-access / M1-FR-07 (D-EHA-27; NFR-EHA-07, 23)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/env-human-access/code/`  
**Technical references**: `construction/env-human-access/nfr-design/nfr-design-patterns.md` (NP-EHA-04); `construction/env-human-access/nfr-requirements/nfr-requirements.md` (NFR-EHA-07)

---

### TC-EHA-044 — S2 computes a human's authority only through P3

**Context**: One place computes authority (I5; BR-EV-04).

**Scenario**: A structural check over S2's code.

**Preconditions**:
- The repository at the commit under test

**Steps**:
1. Run the import check over `services/control-gateway`, `packages/registry`, `packages/credentials`, and `packages/attribution`

**Expected outcome**: S2 imports `evaluateHuman` and `holdsAnyGrant` from `@soorma/authority` and nothing else that computes authority; P4, P5, and P7 import no evaluator and call no `contains`.

**Scope**: edge-boundary · **Priority**: High  
**Source**: env-human-access / M1-FR-08 (BR-EV-04; I5)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/env-human-access/code/`  
**Technical references**: `construction/env-human-access/functional-design/business-rules.md` (BR-EV-04)

---

### TC-EHA-045 — A credential asserting another environment, signed with E's key, is refused

**Context**: `env` is compared field by field with E's identity (O4; D-EHA-12; NP-EHA-01 step 8).

**Scenario**: Tokens re-signed with E's key with one `env` field altered.

**Preconditions**:
- S2's modules run in-process against a test environment store (PostgreSQL 18, migrated by the real runner), a stub S1 over TLS under a test CA, and an injected clock and scheduler
- A live credential record for H in E

**Steps**:
1. Present tokens whose `env.organization`, `env.project`, or `env.environment` is altered, each signed with E's signing key and naming the live `cid`

**Expected outcome**: Each is `credential_refused` (401) with `credential.refused` reason `wrong_environment`; no store read is made for them.

**Scope**: negative · **Priority**: High  
**Source**: env-human-access / M1-FR-10 (D-EHA-12)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/env-human-access/code/`  
**Technical references**: `construction/env-human-access/nfr-design/nfr-design-patterns.md` (NP-EHA-01)

---

### TC-EHA-046 — Each actor kind is recoverable from its attribution record alone

**Context**: Scope, actor, chain, origin, and the resolved sponsor are recoverable from the record (BR-AT-07; I4). Agent records are constructed here; U6 and U7 write them.

**Scenario**: Records of each actor kind are written and read back.

**Preconditions**:
- A test environment store (PostgreSQL 18), migrated by `env-store`'s migrations through the shared runner

**Steps**:
1. Write through P7: a human record; a configuration record; an agent record with no envelope (registration, instance, sponsor); an agent record with chain `[A]`, origin `{ originMode: 'autonomous' }`, not load-bearing; an agent record with chain `[A, B]`, load-bearing at hop 1
2. Read each row back, with no other table

**Expected outcome**: Each row alone yields its scope (organization, project, environment), actor kind and identity, sponsor (agents), chain, origin, and re-broadening outcome exactly as written.

**Scope**: happy-path · **Priority**: High  
**Source**: env-human-access / M1-FR-12 (BR-AT-07; I4)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/env-human-access/code/`  
**Technical references**: `construction/env-human-access/functional-design/business-rules.md` (BR-AT-01 to 07); `construction/env-human-access/nfr-design/nfr-design-patterns.md` (NP-EHA-07)

---

### TC-EHA-047 — The store refuses an inconsistent attribution record

**Context**: CHECK constraints repeat BR-AT-05 (NP-EHA-07). The writer refuses first.

**Scenario**: Inconsistent rows inserted directly as the app role, and through P7.

**Preconditions**:
- A test environment store (PostgreSQL 18), migrated by `env-store`'s migrations through the shared runner

**Steps**:
1. Insert directly, one per constraint: a human actor with a chain; a configuration actor with a principal; an agent actor without a sponsor; chain present without origin; a hop without load-bearing; a hop equal to the chain's length; a non-array chain
2. Pass the same records to P7's writer

**Expected outcome**: Every direct insert fails with `check_violation`, naming its constraint; P7 refuses each before any SQL is sent.

**Scope**: negative · **Priority**: High  
**Source**: env-human-access / M1-FR-12 (BR-AT-05)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/env-human-access/code/`  
**Technical references**: `construction/env-human-access/nfr-design/nfr-design-patterns.md` (NP-EHA-07); `construction/env-human-access/nfr-design/logical-components.md` (§3)

---

### TC-EHA-048 — A failed attribution write rolls back its operation, and refusals write no record

**Context**: Each operation and its record commit in one transaction (D-EHA-17; NP-EHA-06); refusals go to the log only (BR-AT-09).

**Scenario**: The attribution insert is forced to fail.

**Preconditions**:
- S2's modules run in-process against a test environment store (PostgreSQL 18, migrated by the real runner), a stub S1 over TLS under a test CA, and an injected clock and scheduler

**Steps**:
1. Force P7's insert to fail during a `grantToHuman`, an issuance, a renewal, and an end
2. Make a refused `grantToHuman` (forbidden)

**Expected outcome**: Each step 1 operation is `unavailable` (503) and leaves no grant, no new credential, the old expiry, and `live` respectively; step 2 writes no attribution record.

**Scope**: edge-boundary · **Priority**: High  
**Source**: env-human-access / M1-FR-12 (D-EHA-17; BR-AT-09)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/env-human-access/code/`  
**Technical references**: `construction/env-human-access/nfr-design/nfr-design-patterns.md` (NP-EHA-06)

---

### TC-EHA-049 — A forged sign-in and a forged environment credential, sent raw, are refused

**Context**: S2 verifies everything from the raw request (I2; O10).

**Scenario**: Tokens signed with keys E does not hold.

**Preconditions**:
- The local stack is running (`pnpm stack:up`): S1 at `127.0.0.1:8441`, E's S2 at `127.0.0.1:8442`, E2's S2 at `127.0.0.1:8443`

**Steps**:
1. Mint a `soorma_si_` token with a fresh Ed25519 key and a `kid` S1 never published; call issuance
2. Mint a `soorma_ec_` token with a fresh key; call `grantToHuman`

**Expected outcome**: Both are `credential_refused` (401). Step 1 makes at most one on-demand key fetch (TC-EHA-064).

**Scope**: negative · **Priority**: High  
**Source**: env-human-access / M1-FR-09 (I2; O10)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/env-human-access/code/`  
**Technical references**: `construction/env-human-access/nfr-design/nfr-design-patterns.md` (NP-EHA-01, 03)

---

### TC-EHA-050 — Identity comes from the credential alone, never the network

**Context**: A credential asserts a binding, never a location (BR-EC-10; I3).

**Scenario**: The same credential from two places; no credential from inside.

**Preconditions**:
- The local stack is running (`pnpm stack:up`): S1 at `127.0.0.1:8441`, E's S2 at `127.0.0.1:8442`, E2's S2 at `127.0.0.1:8443`
- H is `active` and holds a live sign-in from S1, and the grants E's configuration gives the first Admin
- H holds a credential for E

**Steps**:
1. Call `grantToHuman` from the host
2. Call it with the same credential from a container on network `e`
3. From a container on `org-internal-e`, call E's S2 with no credential

**Expected outcome**: Steps 1 and 2 resolve the same actor and both succeed; step 3 is `credential_refused`.

**Scope**: negative · **Priority**: High  
**Source**: env-human-access / M1-FR-10 (BR-EC-10; I3)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/env-human-access/code/`  
**Technical references**: `construction/env-human-access/functional-design/business-rules.md` (BR-EC-10)

---

### TC-EHA-051 — Nothing of E2's is reachable from E

**Context**: One test per access path (I1).

**Scenario**: H holds grants and credentials in both environments.

**Preconditions**:
- The local stack is running (`pnpm stack:up`): S1 at `127.0.0.1:8441`, E's S2 at `127.0.0.1:8442`, E2's S2 at `127.0.0.1:8443`
- H is `active` and holds a live sign-in from S1, and the grants E's configuration gives the first Admin in both E and E2

**Steps**:
1. Present E2's credential at each of E's operations
2. Grant H `agent:register` in E2 only; evaluate it at E
3. Compare H's log pseudonym in E's and E2's logs

**Expected outcome**: Step 1 is `credential_refused` everywhere. Step 2: H's held set in E lacks `agent:register`, so `evaluateHuman(H, agent:register)` at E is denied. Step 3 shows two different pseudonyms for H (per-environment keys).

**Scope**: negative · **Priority**: High  
**Source**: env-human-access / M1-FR-10 (I1)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/env-human-access/code/`  
**Technical references**: `construction/env-human-access/functional-design/business-rules.md` (invariant-coverage-matrix I1); `construction/env-human-access/infrastructure-design/infrastructure-design.md` (§3)

---

### TC-EHA-052 — Body-less operations refuse a body, and the contract version is checked

**Context**: The three credential operations take no body (D-EHA-24); the contract version is step 5.

**Scenario**: Raw calls with a body or a bad version.

**Preconditions**:
- The local stack is running (`pnpm stack:up`): S1 at `127.0.0.1:8441`, E's S2 at `127.0.0.1:8442`, E2's S2 at `127.0.0.1:8443`
- H is `active` and holds a live sign-in from S1, and the grants E's configuration gives the first Admin
- H holds a credential for E

**Steps**:
1. Call issuance, renewal, and ending with a 1-byte body
2. Call each with no `Soorma-Contract-Version`, and with `9.9.9`

**Expected outcome**: Step 1: `malformed_request` (400), pointer `''`. Step 2: the contract's version error, as S1's. Neither changes any record.

**Scope**: negative · **Priority**: Medium  
**Source**: env-human-access / M1-FR-02 (D-EHA-24)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/env-human-access/code/`  
**Technical references**: `construction/env-human-access/functional-design/business-rules.md` (D-EHA-24; §11)

---

### TC-EHA-053 — Logs carry no token, key, or principal identifier

**Context**: Humans are named only by `hp_` under E's own key (NFR-EHA-18).

**Scenario**: Every S2 flow runs with known secret values.

**Preconditions**:
- S2's modules run in-process against a test environment store (PostgreSQL 18, migrated by the real runner), a stub S1 over TLS under a test CA, and an injected clock and scheduler, with logs captured

**Steps**:
1. Run issuance, renewal, ending, a grant, each refusal, and the first grant, with known tokens, keys, and identifiers (existing and unknown)

**Expected outcome**: No captured line contains any known token, key, password, or identifier, in whole or part; every event naming a human carries `hp_` computed with E's log-pseudonym key.

**Scope**: edge-boundary · **Priority**: High  
**Source**: env-human-access / NFR-EHA-18 (SECURITY-03)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/env-human-access/code/`  
**Technical references**: `construction/env-human-access/nfr-requirements/nfr-requirements.md` (NFR-EHA-18); `construction/env-human-access/nfr-design/nfr-design-patterns.md` (NP-EHA-12)

---

### TC-EHA-054 — Every S2 security event is emitted by its flow

**Context**: Ten named events (NFR-EHA-19).

**Scenario**: Each flow is run once.

**Preconditions**:
- S2's modules run in-process against a test environment store (PostgreSQL 18, migrated by the real runner), a stub S1 over TLS under a test CA, and an injected clock and scheduler, with logs captured

**Steps**:
1. Trigger each: issuance, renewal, ending, a refusal, a grant, a denial, the first grant, S1 down, the store down, a throttle refusal

**Expected outcome**: Each flow logs exactly its event: `credential.issued`, `credential.renewed`, `credential.ended`, `credential.refused`, `grant.made`, `grant.denied`, `first_grant.applied`, `orglevel.unavailable`, `store.unavailable`, `throttle.refused`.

**Scope**: happy-path · **Priority**: Medium  
**Source**: env-human-access / NFR-EHA-19 (SECURITY-14)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/env-human-access/code/`  
**Technical references**: `construction/env-human-access/nfr-requirements/nfr-requirements.md` (NFR-EHA-19)

---

### TC-EHA-055 — The credential lives 15 minutes, capped at the sign-in

**Context**: NFR-EHA-01, with an injected clock.

**Scenario**: Issuance and renewal against scripted sign-in expiries.

**Preconditions**:
- S2's modules run in-process against a test environment store (PostgreSQL 18, migrated by the real runner), a stub S1 over TLS under a test CA, and an injected clock and scheduler

**Steps**:
1. Issue with the sign-in's `expiresAt` 20 minutes ahead
2. Issue with it 6 minutes ahead
3. Renew after the stub's `expiresAt` moves to 15 minutes ahead

**Expected outcome**: Expiries: now + 15 minutes; now + 6 minutes; now + 15 minutes.

**Scope**: edge-boundary · **Priority**: High  
**Source**: env-human-access / NFR-EHA-01  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/env-human-access/code/`  
**Technical references**: `construction/env-human-access/nfr-requirements/nfr-requirements.md` (NFR-EHA-01)

---

### TC-EHA-056 — E's credentials have no `exp` leeway, and `iat` up to 30 seconds ahead

**Context**: NFR-EHA-03, E's own tokens.

**Scenario**: Tokens at the edges, with an injected clock.

**Preconditions**:
- S2's modules run in-process against a test environment store (PostgreSQL 18, migrated by the real runner), a stub S1 over TLS under a test CA, and an injected clock and scheduler

**Steps**:
1. Present a live credential 1 ms before `exp`, and at `exp`
2. Present tokens with `iat` 30 s and 31 s ahead

**Expected outcome**: 1 ms before: accepted; at `exp`: `credential_expired`. `iat` +30 s: accepted; +31 s: `credential_refused`.

**Scope**: edge-boundary · **Priority**: High  
**Source**: env-human-access / NFR-EHA-03  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/env-human-access/code/`  
**Technical references**: `construction/env-human-access/nfr-requirements/nfr-requirements.md` (NFR-EHA-03); `construction/env-human-access/nfr-design/nfr-design-patterns.md` (NP-EHA-01)

---

### TC-EHA-057 — Sign-in leeway at issuance: the token check allows 30 seconds, A7 judges expiry on S1's clock

**Context**: NFR-EHA-03 as corrected at review; NP-EHA-15's leeway parameter. S1's settings stay unchanged.

**Scenario**: Sign-ins just past their expiry, through P1 at S2's settings, and at S1's.

**Preconditions**:
- S2's modules run in-process against a test environment store (PostgreSQL 18, migrated by the real runner), a stub S1 over TLS under a test CA, and an injected clock and scheduler
- The stub S1 answers A7 from its own record of each sign-in

**Steps**:
1. (a) A never-renewed sign-in, 29 s past its expiry: issue
2. (b) An older token of a renewed sign-in, 29 s past its own expiry: issue
3. (c) Any sign-in token 31 s past its expiry: issue
4. A sign-in with `iat` 30 s ahead, then 31 s ahead: issue
5. Run the same tokens through S1's settings (`{ expSeconds: 0 }`, no `iat` check)

**Expected outcome**: (a) `credential_refused` (A7 `ended`); (b) accepted, credential capped at the renewed expiry; (c) `credential_expired`; `iat` +30 s accepted, +31 s `credential_refused`. Step 5 gives S1's existing answers, unchanged.

**Scope**: edge-boundary · **Priority**: High  
**Source**: env-human-access / NFR-EHA-03 (U2 F-2)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/env-human-access/code/`  
**Technical references**: `construction/env-human-access/nfr-requirements/nfr-requirements.md` (NFR-EHA-03); `construction/env-human-access/nfr-design/nfr-design-patterns.md` (NP-EHA-15)

---

### TC-EHA-058 — The request throttle refuses the 65th request after 1 second

**Context**: 64 requests in flight per instance (NFR-EHA-04).

**Scenario**: 64 requests are held open.

**Preconditions**:
- S2's modules run in-process against a test environment store (PostgreSQL 18, migrated by the real runner), a stub S1 over TLS under a test CA, and an injected clock and scheduler, with requests held open by a blocking stub

**Steps**:
1. Hold 64 requests
2. Send a 65th; advance the clock 1 s
3. Release one held request while a 66th waits

**Expected outcome**: The 65th is `unavailable` (503), `Retry-After: 5`, `throttle.refused` reason `requests`; the 66th proceeds when the permit is released.

**Scope**: edge-boundary · **Priority**: High  
**Source**: env-human-access / NFR-EHA-04 (SECURITY-11)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/env-human-access/code/`  
**Technical references**: `construction/env-human-access/nfr-design/nfr-design-patterns.md` (NP-EHA-05)

---

### TC-EHA-059 — Aborted requests release their slots exactly once

**Context**: The user's 64-abort test; the release-once guard in `onResponse` and `onRequestAbort` (NP-EHA-05).

**Scenario**: Requests are aborted mid-body.

**Preconditions**:
- S2's modules run in-process against a test environment store (PostgreSQL 18, migrated by the real runner), a stub S1 over TLS under a test CA, and an injected clock and scheduler (real Fastify listener)

**Steps**:
1. Open 64 requests that send half a body, then abort them
2. Send one more request
3. Answer one request, then abort its socket; abort another, then let it be answered
4. Abort a request while it waits for a permit

**Expected outcome**: Step 2 gets a permit at once; after step 3 the available count is exactly 64, never 65; step 4's request holds nothing and leaves the queue.

**Scope**: edge-boundary · **Priority**: High  
**Source**: env-human-access / NFR-EHA-04 (NP-EHA-05)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/env-human-access/code/`  
**Technical references**: `construction/env-human-access/nfr-design/nfr-design-patterns.md` (NP-EHA-05)

---

### TC-EHA-060 — The S1-call throttle refuses the 9th call after 1 second; key fetches are not throttled

**Context**: 8 S1 calls in flight (NFR-EHA-05); the key fetch has its own single socket (NP-EHA-04, the user's change).

**Scenario**: Eight S1 calls are held open.

**Preconditions**:
- S2's modules run in-process against a test environment store (PostgreSQL 18, migrated by the real runner), a stub S1 over TLS under a test CA, and an injected clock and scheduler

**Steps**:
1. Hold 8 issuance calls at the stub
2. Send a 9th issuance; advance 1 s
3. End a credential
4. Trigger a verify-key fetch

**Expected outcome**: The 9th is `unavailable` (503), `Retry-After: 5`, `throttle.refused` reason `s1_calls`; ending succeeds; the key fetch completes while the 8 are held.

**Scope**: edge-boundary · **Priority**: High  
**Source**: env-human-access / NFR-EHA-05 (NP-EHA-04)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/env-human-access/code/`  
**Technical references**: `construction/env-human-access/nfr-design/nfr-design-patterns.md` (NP-EHA-04, 05)

---

### TC-EHA-061 — Verify keys refresh every 5 minutes; on-demand fetches are limited to one per 30 seconds

**Context**: NFR-EHA-08; NP-EHA-03.

**Scenario**: The cache under an injected clock.

**Preconditions**:
- S2's modules run in-process against a test environment store (PostgreSQL 18, migrated by the real runner), a stub S1 over TLS under a test CA, and an injected clock and scheduler

**Steps**:
1. Advance 5 minutes
2. Present two unknown-`kid` sign-ins 10 s apart, then two 31 s apart
3. Make an on-demand fetch, advance 5 s to the scheduled refresh
4. Fail a fetch; answer a malformed JWKS
5. Start 5 concurrent callers needing a fetch

**Expected outcome**: One scheduled fetch at 5 minutes; one on-demand fetch for the 10 s pair and two for the 31 s pair; the scheduled refresh still runs; failed and malformed fetches keep the held keys and log `orglevel.unavailable`; the 5 callers share one fetch.

**Scope**: edge-boundary · **Priority**: High  
**Source**: env-human-access / NFR-EHA-08 (U2 F-1)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/env-human-access/code/`  
**Technical references**: `construction/env-human-access/nfr-design/nfr-design-patterns.md` (NP-EHA-03)

---

### TC-EHA-062 — Rotation at S1: after the 5-minute wait, issuance under the new key needs no on-demand fetch

**Context**: NFR-EHA-08a case 1; S1's rotation step 2 waits at least 5 minutes.

**Scenario**: S1 adds a key, then signs with it after 5 minutes.

**Preconditions**:
- S2's modules run in-process against a test environment store (PostgreSQL 18, migrated by the real runner), a stub S1 over TLS under a test CA, and an injected clock and scheduler

**Steps**:
1. The stub adds a new verify key
2. Advance 5 minutes
3. Sign a sign-in with the new key; issue
4. After 15 minutes, the stub removes the old key; advance to the next refresh
5. Issue with a sign-in under the old key

**Expected outcome**: Step 3 succeeds with no on-demand fetch; step 5 is `credential_refused`.

**Scope**: edge-boundary · **Priority**: High  
**Source**: env-human-access / NFR-EHA-08a (U2 R-1)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/env-human-access/code/`  
**Technical references**: `construction/env-human-access/nfr-requirements/nfr-requirements.md` (NFR-EHA-08a); `construction/env-human-access/nfr-design/nfr-design-patterns.md` (NP-EHA-03)

---

### TC-EHA-063 — Rotation at S1: a refresh that failed during step 1 is covered by one on-demand fetch

**Context**: NFR-EHA-08a case 2, added at review.

**Scenario**: The refresh fails while S1 restarts.

**Preconditions**:
- S2's modules run in-process against a test environment store (PostgreSQL 18, migrated by the real runner), a stub S1 over TLS under a test CA, and an injected clock and scheduler

**Steps**:
1. The stub adds a new key and fails the next scheduled refresh
2. Sign with the new key; issue

**Expected outcome**: Issuance succeeds after exactly one on-demand fetch.

**Scope**: edge-boundary · **Priority**: High  
**Source**: env-human-access / NFR-EHA-08a  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/env-human-access/code/`  
**Technical references**: `construction/env-human-access/nfr-requirements/nfr-requirements.md` (NFR-EHA-08a); `construction/env-human-access/nfr-design/nfr-design-patterns.md` (NP-EHA-03)

---

### TC-EHA-064 — The unknown-`kid` flow through P1: refetch, then verify exactly once more

**Context**: NP-EHA-03's flow; NP-EHA-15's `unknownKey` result and `refetch()` (the user's review).

**Scenario**: Sign-ins naming keys S2 lacks.

**Preconditions**:
- S2's modules run in-process against a test environment store (PostgreSQL 18, migrated by the real runner), a stub S1 over TLS under a test CA, and an injected clock and scheduler

**Steps**:
1. The refetch brings the key: issue
2. The refetch does not bring it: issue
3. Inside the 30 s limit: issue
4. No keys held and the fetch fails: issue
5. A token with no `kid`: issue

**Expected outcome**: 1: one fetch, two verifications, accepted. 2: one fetch, two verifications, `credential_refused`. 3: no fetch, two verifications, `credential_refused`. 4: `unavailable` (503, `Retry-After: 5`). 5: `credential_refused`, no fetch.

**Scope**: edge-boundary · **Priority**: High  
**Source**: env-human-access / NFR-EHA-08 (NP-EHA-03, 15)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/env-human-access/code/`  
**Technical references**: `construction/env-human-access/nfr-design/nfr-design-patterns.md` (NP-EHA-03, 15)

---

### TC-EHA-065 — The key source is read on every verification

**Context**: P1 holds no copy of the key set (NP-EHA-15, the user's review).

**Scenario**: A refresh lands between two sign-ins.

**Preconditions**:
- S2's modules run in-process against a test environment store (PostgreSQL 18, migrated by the real runner), a stub S1 over TLS under a test CA, and an injected clock and scheduler

**Steps**:
1. Make an on-demand fetch (the limit is now active)
2. Issue under a new key (refused inside the limit)
3. The scheduled refresh brings the key
4. Issue under the new key again

**Expected outcome**: Step 2 is `credential_refused`; step 4 is accepted with no on-demand fetch.

**Scope**: edge-boundary · **Priority**: High  
**Source**: env-human-access / NFR-EHA-08 (NP-EHA-15)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/env-human-access/code/`  
**Technical references**: `construction/env-human-access/nfr-design/nfr-design-patterns.md` (NP-EHA-03, 15)

---

### TC-EHA-066 — Issuance makes exactly one `signInStatus` call and caps at its answer

**Context**: P1 makes the call and returns `expiresAt`; the handler reuses it (NP-EHA-15; BR-EC-04).

**Scenario**: The stub counts calls.

**Preconditions**:
- S2's modules run in-process against a test environment store (PostgreSQL 18, migrated by the real runner), a stub S1 over TLS under a test CA, and an injected clock and scheduler

**Steps**:
1. Script `expiresAt` = now + 7 minutes; issue

**Expected outcome**: One `signInStatus` call; the credential's expiry is now + 7 minutes.

**Scope**: edge-boundary · **Priority**: High  
**Source**: env-human-access / M1-FR-20 (NP-EHA-15; BR-EC-04)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/env-human-access/code/`  
**Technical references**: `construction/env-human-access/nfr-design/nfr-design-patterns.md` (NP-EHA-03, 15)

---

### TC-EHA-067 — E's store credentials cannot reach E2's store

**Context**: One instance per environment, with its own credentials (NFR-EHA-09; I1).

**Scenario**: Cross-environment connection attempts.

**Preconditions**:
- The local stack is running (`pnpm stack:up`): S1 at `127.0.0.1:8441`, E's S2 at `127.0.0.1:8442`, E2's S2 at `127.0.0.1:8443`

**Steps**:
1. From `e-control-gateway`, try to resolve and connect to `env-db.e2.soorma.internal`
2. Connect to E's store with E2's app password

**Expected outcome**: Step 1 fails to resolve (no shared network); step 2 fails authentication.

**Scope**: negative · **Priority**: High  
**Source**: env-human-access / NFR-EHA-09 (I1)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/env-human-access/code/`  
**Technical references**: `construction/env-human-access/nfr-requirements/nfr-requirements.md` (NFR-EHA-09); `construction/env-human-access/infrastructure-design/infrastructure-design.md` (§6, §7)

---

### TC-EHA-068 — Environment migrations are locked, checksummed, and run only by `{env}-migrate`

**Context**: NFR-EHA-14.

**Scenario**: Concurrent and tampered migration runs.

**Preconditions**:
- A test environment store (PostgreSQL 18), migrated by `env-store`'s migrations through the shared runner

**Steps**:
1. Run two migrate runs concurrently
2. Edit an applied migration; run again
3. Inspect S2's mounted secrets

**Expected outcome**: Each migration applies once; the edited one fails the run (and S2 would not start); S2 has no migrator password.

**Scope**: edge-boundary · **Priority**: High  
**Source**: env-human-access / NFR-EHA-14  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/env-human-access/code/`  
**Technical references**: `construction/env-human-access/nfr-requirements/nfr-requirements.md` (NFR-EHA-14); `construction/env-human-access/infrastructure-design/infrastructure-design.md` (§6)

---

### TC-EHA-069 — Code checks pass over U4's packages, and `===` on a secret token fails them

**Context**: NFR-EHA-13, 25; NP-EHA-14 (the user's Q2 condition).

**Scenario**: The repository's `check:code`.

**Preconditions**:
- The repository at the commit under test

**Steps**:
1. Run `check:code` (sql, compare, inject)
2. Run its fixture with `===` on a `SecretText` token

**Expected outcome**: Step 1 is clean over `service-kit`, `env-store`, P4, P5, P7, and S2; step 2 reports a `compare` finding.

**Scope**: edge-boundary · **Priority**: High  
**Source**: env-human-access / NFR-EHA-13, 25 (NP-EHA-14)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/env-human-access/code/`  
**Technical references**: `construction/env-human-access/nfr-design/nfr-design-patterns.md` (NP-EHA-14, 15)

---

### TC-EHA-070 — S2 latency is measured and reported

**Context**: p95 at most 300 ms for issuance and renewal, 200 ms otherwise; **reported, not a gate** (NFR-EHA-15).

**Scenario**: A load run on the local stack.

**Preconditions**:
- The local stack is running (`pnpm stack:up`): S1 at `127.0.0.1:8441`, E's S2 at `127.0.0.1:8442`, E2's S2 at `127.0.0.1:8443`

**Steps**:
1. Run 500 of each operation sequentially after warm-up
2. Compute p95 per operation

**Expected outcome**: The four p95 figures are recorded in the Build and Test summary beside the targets. This case does not fail the build.

**Scope**: edge-boundary · **Priority**: Medium  
**Source**: env-human-access / NFR-EHA-15  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/env-human-access/code/`  
**Technical references**: `construction/env-human-access/nfr-requirements/nfr-requirements.md` (NFR-EHA-15)

---

### TC-EHA-071 — Request bodies are bounded at 16 KiB

**Context**: NFR-EHA-16; validators compiled once at start-up (NFR-EHA-17).

**Scenario**: Large bodies.

**Preconditions**:
- The local stack is running (`pnpm stack:up`): S1 at `127.0.0.1:8441`, E's S2 at `127.0.0.1:8442`, E2's S2 at `127.0.0.1:8443`
- H is `active` and holds a live sign-in from S1, and the grants E's configuration gives the first Admin
- H holds a credential for E

**Steps**:
1. Send `grantToHuman` with a 16 KiB + 1 byte body
2. Send exactly 16 KiB (valid JSON, padded)
3. Start S2 with a corrupted contract document

**Expected outcome**: 1: `payload_too_large`; 2: processed normally; 3: start-up fails.

**Scope**: edge-boundary · **Priority**: Medium  
**Source**: env-human-access / NFR-EHA-16, 17 (SECURITY-05)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/env-human-access/code/`  
**Technical references**: `construction/env-human-access/nfr-requirements/nfr-requirements.md` (NFR-EHA-16, 17)

---

### TC-EHA-072 — Identifiers are 128 random bits, base64url

**Context**: D-EHA-30; NP-EHA-11.

**Scenario**: Ids are inspected.

**Preconditions**:
- S2's modules run in-process against a test environment store (PostgreSQL 18, migrated by the real runner), a stub S1 over TLS under a test CA, and an injected clock and scheduler

**Steps**:
1. Issue, grant, and record 1,000 times; collect every id and `jti`

**Expected outcome**: Every id is 22 base64url characters with no padding; all are distinct.

**Scope**: edge-boundary · **Priority**: Low  
**Source**: env-human-access / M1-FR-20 (D-EHA-30)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/env-human-access/code/`  
**Technical references**: `construction/env-human-access/nfr-design/nfr-design-patterns.md` (NP-EHA-11)

---

### TC-EHA-073 — Each malformed or altered environment credential is refused at its verification step

**Context**: NP-EHA-01's nine steps.

**Scenario**: A table of bad tokens.

**Preconditions**:
- S2's modules run in-process against a test environment store (PostgreSQL 18, migrated by the real runner), a stub S1 over TLS under a test CA, and an injected clock and scheduler
- A live credential record for H in E

**Steps**:
1. Present each: wrong prefix; 4097 characters; `typ: JWT`; `alg: EdDSA`; unknown `kid`; minted by E2; a flipped signature byte; each claim missing in turn; an ended record; a record whose `sub` differs

**Expected outcome**: Each is `credential_refused` (401), with no expiry disclosed; the expired case is TC-EHA-056.

**Scope**: negative · **Priority**: High  
**Source**: env-human-access / M1-FR-20 (NP-EHA-01)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/env-human-access/code/`  
**Technical references**: `construction/env-human-access/nfr-design/nfr-design-patterns.md` (NP-EHA-01)

---

### TC-EHA-074 — A token minted before a renewal stays valid until its own expiry

**Context**: The record, not the token, governs liveness (NP-EHA-01).

**Scenario**: H renews, then uses the older token.

**Preconditions**:
- S2's modules run in-process against a test environment store (PostgreSQL 18, migrated by the real runner), a stub S1 over TLS under a test CA, and an injected clock and scheduler

**Steps**:
1. Renew H's credential
2. Call `grantToHuman` with the pre-renewal token before its `exp`
3. Advance past its `exp`; call again
4. End the credential with the new token; present the old one before its `exp`

**Expected outcome**: Step 2 succeeds; step 3 is `credential_expired`; step 4's old token is `credential_refused`.

**Scope**: edge-boundary · **Priority**: Medium  
**Source**: env-human-access / M1-FR-20 (NP-EHA-01)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/env-human-access/code/`  
**Technical references**: `construction/env-human-access/nfr-design/nfr-design-patterns.md` (NP-EHA-01)

---

### TC-EHA-075 — E's minting key rotates by configuration

**Context**: Three-step rotation (NP-EHA-02; the operations notes).

**Scenario**: A new key is added, made signing, then the old removed.

**Preconditions**:
- S2's modules run in-process against a test environment store (PostgreSQL 18, migrated by the real runner), a stub S1 over TLS under a test CA, and an injected clock and scheduler

**Steps**:
1. Issue under key 1
2. Add key 2 as a verify key; restart; present the key-1 token
3. Make key 2 signing; restart; issue
4. Remove key 1; restart; present the key-1 token

**Expected outcome**: Step 2 accepted; step 3's token has key 2's `kid`; step 4 is `credential_refused`.

**Scope**: happy-path · **Priority**: Medium  
**Source**: env-human-access / M1-FR-20 (NP-EHA-02)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/env-human-access/code/`  
**Technical references**: `construction/env-human-access/nfr-design/nfr-design-patterns.md` (NP-EHA-02); `construction/env-human-access/infrastructure-design/infrastructure-design.md` (§10)

---

### TC-EHA-076 — The held set is the union of a human's grants

**Context**: NP-EHA-10; BR-GR-06 (granting a held permission is allowed).

**Scenario**: Two overlapping grants.

**Preconditions**:
- S2's modules run in-process against a test environment store (PostgreSQL 18, migrated by the real runner), a stub S1 over TLS under a test CA, and an injected clock and scheduler

**Steps**:
1. Grant J `{ agent:register }`, then `{ agent:register, human:manage }`
2. Read J's held set through the `GrantSource`

**Expected outcome**: Both grants succeed and are recorded; the held set is `{ agent:register, human:manage }`.

**Scope**: happy-path · **Priority**: Medium  
**Source**: env-human-access / M1-FR-15 (BR-GR-06)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/env-human-access/code/`  
**Technical references**: `construction/env-human-access/functional-design/business-rules.md` (BR-GR-06); `construction/env-human-access/nfr-design/nfr-design-patterns.md` (NP-EHA-10)

---

### TC-EHA-077 — A client-sent request id is replaced

**Context**: A request id is generated for every request, never taken from the client (NP-EHA-12).

**Scenario**: A request carries its own `Soorma-Request-Id`.

**Preconditions**:
- The local stack is running (`pnpm stack:up`): S1 at `127.0.0.1:8441`, E's S2 at `127.0.0.1:8442`, E2's S2 at `127.0.0.1:8443`

**Steps**:
1. Send any S2 request with `Soorma-Request-Id: client-chosen`

**Expected outcome**: The response's `Soorma-Request-Id` is a server-generated id, not `client-chosen`; the response carries `Soorma-Contract-Version`.

**Scope**: edge-boundary · **Priority**: Low  
**Source**: env-human-access / M1-FR-02 (NP-EHA-12)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/env-human-access/code/`  
**Technical references**: `construction/env-human-access/nfr-design/nfr-design-patterns.md` (NP-EHA-12)

---

### TC-EHA-078 — The shared-code move keeps U2 green, and S2 never links `@soorma/org-identity`

**Context**: NP-EHA-15 (the user's Q2 conditions).

**Scenario**: Checks after the move commits.

**Preconditions**:
- The repository after commit 1 (pure move) and after commit 2 (generalisations)

**Steps**:
1. Run U2's full test suite after each commit
2. Build S1's image after each commit
3. List `services/control-gateway`'s production dependency closure

**Expected outcome**: U2's suite passes unchanged after both; S1's image builds; `@soorma/org-identity` is absent from S2's closure, transitive dependencies included.

**Scope**: edge-boundary · **Priority**: High  
**Source**: env-human-access / NFR-EHA-22 (NP-EHA-15)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/env-human-access/code/`  
**Technical references**: `construction/env-human-access/nfr-design/nfr-design-patterns.md` (NP-EHA-15); `construction/env-human-access/nfr-design/logical-components.md` (§2.1)

---

### TC-EHA-079 — Secrets are mounted files only, and never cross a level (Compose-model test)

**Context**: The user's O-4; Infrastructure Design §3.

**Scenario**: The rendered Compose model.

**Preconditions**:
- `docker compose config` over `deploy/local/compose.yaml`

**Steps**:
1. Assert each service's mounted volume and subpath
2. Assert each `*-secrets-init`'s secret list
3. Assert every service's environment variables

**Expected outcome**: Each service mounts only its own level's volume at its own subpath; `{env}-secrets-init` lists only `{env}-` secrets and `stack-ca-cert`; `org-secrets-init` lists only `org-` secrets, `stack-ca-cert`, and the `-caller-public-key` files; no environment variable holds a value matching the secret pattern or is named `*PASSWORD`, `*KEY`, `*SECRET`, `*TOKEN` other than `_FILE` paths; `{env}-control-gateway` has no migrator password; `org-signing-key` is on `org-gateway` only.

**Scope**: negative · **Priority**: High  
**Source**: env-human-access / Infrastructure Design §3 (O-4; ID §6)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/env-human-access/code/`  
**Technical references**: `construction/env-human-access/infrastructure-design/infrastructure-design.md` (§3)

---

### TC-EHA-080 — The app role holds only its granted table and column privileges

**Context**: Infrastructure Design §6 (O-2); NFR-EHA-21 (nothing pruned).

**Scenario**: Connected as `soorma_env_app`.

**Preconditions**:
- A test environment store (PostgreSQL 18), migrated by `env-store`'s migrations through the shared runner

**Steps**:
1. Attempt: `UPDATE credentials SET principal`; `SET issued_from`; `SET organization`; `DELETE FROM credentials`; `UPDATE` and `DELETE` on `grants` and `attribution_records`; `SELECT` on `schema_migrations`
2. Attempt `UPDATE credentials SET state = 'ended'` on a live row

**Expected outcome**: Every step 1 statement fails with `insufficient_privilege`; step 2 succeeds.

**Scope**: negative · **Priority**: High  
**Source**: env-human-access / Infrastructure Design §6 (O-2)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/env-human-access/code/`  
**Technical references**: `construction/env-human-access/infrastructure-design/infrastructure-design.md` (§6); `construction/env-human-access/nfr-design/logical-components.md` (§3)

---

### TC-EHA-081 — S1's README says "wait at least 5 minutes" in its rotation steps

**Context**: O-1 (the user's P-04 addition); the docs test.

**Scenario**: The operations notes.

**Preconditions**:
- The repository at the commit under test

**Steps**:
1. Read `services/org-gateway/README.md`'s *Rotating the signing key* section

**Expected outcome**: It contains "wait at least 5 minutes" at step 2, with the reason; the test fails if the phrase is removed.

**Scope**: edge-boundary · **Priority**: Medium  
**Source**: env-human-access / Infrastructure Design §10 (O-1)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/env-human-access/code/`  
**Technical references**: `construction/env-human-access/infrastructure-design/infrastructure-design.md` (§10)

---

### TC-EHA-082 — S1 refuses an ambiguous internal-caller configuration

**Context**: Q2 A with the user's addition (I1): no `kid` may name two environments' keys.

**Scenario**: S1 starts with one fault at a time.

**Preconditions**:
- S1's configuration with E and E2 as internal callers

**Steps**:
1. Start S1 with: E listed twice; one secret name in E's and E2's `publicKeys`; one key twice in E's `publicKeys` under two file names; one key in E's and E2's `publicKeys` under two file names

**Expected outcome**: Each start-up exits non-zero with its configuration error (environment twice; name listed more than once; `kid` twice for E; `kid` configured for E and E2).

**Scope**: negative · **Priority**: High  
**Source**: env-human-access / Infrastructure Design §4 (I1)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/env-human-access/code/`  
**Technical references**: `construction/env-human-access/infrastructure-design/infrastructure-design.md` (§4)

---

### TC-EHA-083 — A caller key rotates with no outage, and a call is attributed only to its own environment

**Context**: `publicKeys` lists (Q2 A).

**Scenario**: E has two listed keys during rotation.

**Preconditions**:
- The local stack is running (`pnpm stack:up`): S1 at `127.0.0.1:8441`, E's S2 at `127.0.0.1:8442`, E2's S2 at `127.0.0.1:8443`

**Steps**:
1. List E's old and new public keys; restart S1
2. Sign a call with each of E's keys
3. Sign a call with E2's key naming E as `iss`

**Expected outcome**: Both of E's keys are attributed to E; step 3 is refused (`internal.call_refused`). Issuance at E keeps working through the three rotation steps.

**Scope**: happy-path · **Priority**: Medium  
**Source**: env-human-access / Infrastructure Design §4  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/env-human-access/code/`  
**Technical references**: `construction/env-human-access/infrastructure-design/infrastructure-design.md` (§4)

---

### TC-EHA-084 — Outage case 1: S1 stops under a running S2

**Context**: Infrastructure Design §11; D-EHA-23 (Functional Design §16).

**Scenario**: `docker compose stop org-gateway` with E's S2 running and holding keys.

**Preconditions**:
- The local stack is running (`pnpm stack:up`): S1 at `127.0.0.1:8441`, E's S2 at `127.0.0.1:8442`, E2's S2 at `127.0.0.1:8443`
- H is `active` and holds a live sign-in from S1, and the grants E's configuration gives the first Admin
- H holds a live credential for E, an ended one, and a credential from E2

**Steps**:
1. Stop `org-gateway`
2. Issue; renew; grant
3. End the live credential (re-issue one beforehand for later steps)
4. Present the live, ended, and E2 credentials
5. Start `org-gateway`; issue

**Expected outcome**: Step 2: each 503 with `Retry-After: 5`, `orglevel.unavailable` logged. Step 3: 204. Step 4: live passes O1 to O4; ended and E2 are `credential_refused`. Step 5: issuance succeeds as soon as S1 answers (keys were kept).

**Scope**: edge-boundary · **Priority**: High  
**Source**: env-human-access / M1-FR-09 (D-EHA-23)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/env-human-access/code/`  
**Technical references**: `construction/env-human-access/infrastructure-design/infrastructure-design.md` (§11)

---

### TC-EHA-085 — Outage case 2: E's S2 starts while S1 is stopped

**Context**: Infrastructure Design §11, the user's second case.

**Scenario**: S2 restarts with no verify keys.

**Preconditions**:
- The local stack is running (`pnpm stack:up`): S1 at `127.0.0.1:8441`, E's S2 at `127.0.0.1:8442`, E2's S2 at `127.0.0.1:8443`
- H is `active` and holds a live sign-in from S1, and the grants E's configuration gives the first Admin
- H holds a credential for E issued before the restart

**Steps**:
1. Stop `org-gateway`; restart `e-control-gateway`
2. Issue
3. Present the pre-restart credential at `grantToHuman` (S1-free path stops at its target check) and end it
4. Start `org-gateway`; issue

**Expected outcome**: Step 2: 503, `Retry-After: 5` (no keys). Step 3: the credential passes O1 to O4 and is ended (204). Step 4: issuance succeeds on the next fetch.

**Scope**: edge-boundary · **Priority**: High  
**Source**: env-human-access / M1-FR-09 (D-EHA-23)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/env-human-access/code/`  
**Technical references**: `construction/env-human-access/infrastructure-design/infrastructure-design.md` (§11)

---

### TC-EHA-086 — Stack smoke test: sign in, issue, renew, grant, end, and cross-environment refusal

**Context**: Infrastructure Design §12 (CI).

**Scenario**: The full stack with throwaway secrets.

**Preconditions**:
- The local stack is running (`pnpm stack:up`): S1 at `127.0.0.1:8441`, E's S2 at `127.0.0.1:8442`, E2's S2 at `127.0.0.1:8443`

**Steps**:
1. Sign in at S1
2. Issue at E; renew; grant
3. Present E's credential at E2
4. End at E

**Expected outcome**: All succeed in order; step 3 is `credential_refused`.

**Scope**: happy-path · **Priority**: High  
**Source**: env-human-access / M1-FR-20, M1-FR-21  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/env-human-access/code/`  
**Technical references**: `construction/env-human-access/infrastructure-design/infrastructure-design.md` (§12)

---

### TC-EHA-087 — Alert rules and dashboard validate, and name only defined events

**Context**: Infrastructure Design §9 (O-3).

**Scenario**: The monitoring files.

**Preconditions**:
- `deploy/monitoring/alerts.yaml`, `dashboard.yaml`

**Steps**:
1. Validate both against their schemas
2. Check each rule's and panel's event is in `events`

**Expected outcome**: Both validate; the five U4 rules exist with the stated thresholds; every event they name is listed.

**Scope**: happy-path · **Priority**: Medium  
**Source**: env-human-access / NFR-EHA-19 (O-3)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/env-human-access/code/`  
**Technical references**: `construction/env-human-access/infrastructure-design/infrastructure-design.md` (§9)

---

### TC-EHA-088 — The S2 image holds no secret

**Context**: Infrastructure Design §2, §12.

**Scenario**: The built image.

**Preconditions**:
- `soorma/control-gateway:local` built

**Steps**:
1. Run the secret-pattern check over the image's file system

**Expected outcome**: No finding.

**Scope**: negative · **Priority**: High  
**Source**: env-human-access / Infrastructure Design §2  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/env-human-access/code/`  
**Technical references**: `construction/env-human-access/infrastructure-design/infrastructure-design.md` (§2, §12)

---

### TC-EHA-089 — No network spans two environments, and only edges are published, on loopback

**Context**: Infrastructure Design §7.

**Scenario**: The rendered Compose model.

**Preconditions**:
- `docker compose config`

**Steps**:
1. List each network's members
2. List every published port

**Expected outcome**: Network `e` holds only E's store, migrate, and S2; `org-internal-e` only `e-control-gateway` and `org-gateway`; the same for E2. Published: `127.0.0.1:8441`, `8442`, `8443` only; no store port.

**Scope**: negative · **Priority**: High  
**Source**: env-human-access / Infrastructure Design §7 (I1)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/env-human-access/code/`  
**Technical references**: `construction/env-human-access/infrastructure-design/infrastructure-design.md` (§7)

---

### TC-EHA-090 — S1's `signInStatus` answers A7's shape

**Context**: U2 amendment A7, applied by U4 (D-EHA-02).

**Scenario**: S1's internal interface, called with signed requests.

**Preconditions**:
- S1 running, with a signed internal caller

**Steps**:
1. Ask for a live sign-in
2. Ask for an ended one
3. Ask for an expired one
4. Ask for an absent id

**Expected outcome**: 1: `{ status: 'live', expiresAt }`, `expiresAt` the sign-in's current expiry. 2 and 3: `{ status: 'ended' }`. 4: `{ status: 'unknown' }`. No other field.

**Scope**: happy-path · **Priority**: High  
**Source**: env-human-access / M1-FR-20 (A7)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/env-human-access/code/`  
**Technical references**: `construction/env-human-access/functional-design/business-rules.md` (§14, A7)

---

### TC-EHA-091 — A `pending` principal may be a grant target

**Context**: Any principal of E's organization, `pending` included (BR-GR-07).

**Scenario**: H grants to a configured but not yet activated principal.

**Preconditions**:
- The local stack is running (`pnpm stack:up`): S1 at `127.0.0.1:8441`, E's S2 at `127.0.0.1:8442`, E2's S2 at `127.0.0.1:8443`
- H is `active` and holds a live sign-in from S1, and the grants E's configuration gives the first Admin
- P2 is configured at S1 and `pending`

**Steps**:
1. H grants P2 `agent:register`

**Expected outcome**: 200; one grant row; `principalExists` answered true.

**Scope**: edge-boundary · **Priority**: Medium  
**Source**: env-human-access / M1-FR-15 (BR-GR-07)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/env-human-access/code/`  
**Technical references**: `construction/env-human-access/functional-design/business-rules.md` (BR-GR-07)

---
