# Test Specifications (Narrative): org-identity

**Unit**: `org-identity` (U2: human principals, sign-in, and self-service at the organization level, control face)  
**Unit abbreviation**: OI = org-identity  
**Scope**: comprehensive (happy path, negative, edge and boundary), as recorded in `aidlc-state.md`  
**Derived from**: `aidlc-docs/platform/m1-walking-skeleton/inception/application-design/unit-of-work.md` and `aidlc-docs/platform/m1-walking-skeleton/inception/requirements/requirements.md` only  
**Generated**: inception pass, 2026-11-02. IDs are permanent  
**Enriched**: construction pass, 2026-11-08 (TC-OI-001 to 025 updated in place; TC-OI-026 to 062 added). Sources: U2's `functional-design/`, `nfr-requirements/`, `nfr-design/`, `infrastructure-design/`

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

### Construction pass (2026-11-08): fixed values

Set by U2's Functional Design, NFR Requirements, NFR Design, and Infrastructure Design. Every
time-based case runs with the **injected clock** (NFR Design P-14), never by waiting.

| Name | Value |
|---|---|
| **O** | `o1`, from `deploy/local/config/tenancy.yaml` |
| **H** | `h@example.com`; referenced as `{ organization: o1, principal: h@example.com }` |
| **Paths** (S1 edge, `https://127.0.0.1:8441`, `--cacert` the stack CA) | `POST /first-authentication`, `POST /sign-ins`, `POST /sign-ins/current/renewal`, `POST /sign-ins/current/end`, `POST /material-changes` |
| **sign-in** | `soorma_si_` + JWS (`typ` `soorma-si+jwt`, `alg` `Ed25519`); lives **15 minutes**; renewal never past `auth_time` + **12 hours** |
| **the bound** (sign-in abuse) | **10 failures per sliding 15 minutes** per principal reference, and **backoff** from the 5th consecutive failure (1 s doubling, capped at 15 min); shared by `authenticate`, `firstAuthenticate`, `changeMaterial` |
| **K policy** | 8 to 256 code points after NFKC; no control characters; not on the pinned breached list; no context word; not the material it replaces |
| **P** | TOTP (RFC 6238): HMAC-SHA-1, 6 digits, 30 s, ±1 step; each code once; a pending enrollment lives 10 minutes |
| **Refusal codes** (U2) | `authentication_failed` 403; `second_factor_enrollment_required` 403; `second_factor_not_confirmed` 403; `secret_rejected` 400 (with `reason`); `too_many_attempts` 429; `malformed_request` 400; `credential_refused` and `credential_expired` 401 (sign-in operations only) |
| **internal interface** | S1's internal listener (port 9443), reachable only on `org-internal-{env}` networks; every call a signed request (NFR Design P-06) |
| **log pseudonym** | `hp_` + 128 bits of HMAC-SHA-256 under the organization's log-pseudonym key. No log carries a human identifier |

The bound in the table above is the **sign-in abuse bound**. The *bound* defined earlier in
this file (the revocation propagation bound) does not apply to U2.

---

### TC-OI-001 — A configured first Admin is registered as pending, with enrollment material

**Context**: M1-FR-14 has configuration name an environment's first Admin, and register the principal `pending` with single-use enrollment material if it does not exist. This is the trust root for every later step.

**Scenario**: The deployer starts the stack with configuration naming H as E's first Admin.

**Preconditions**:
- Configuration naming O, E, and H as E's first Admin with enrollment material
- No principal H exists yet

**Steps**:
1. Run `pnpm stack:init`, then start the stack (`org-db`, `org-migrate`, `org-gateway`) with `tenancy.yaml` naming H as E's first Admin
2. Inspect O's principal and material records in the org store
3. Search the logs and the store for the enrollment material

**Expected outcome**: H exists in O as `pending`, `registeredBy` naming configuration and environment E, with exactly **one** material record: class `K`, state `enrollment`, `enrolledBy` configuration, holding only a one-way verifier of the enrollment material. No other principal was created. The enrollment material appears in no log and in no record in plain form.

**Scope**: happy-path · **Priority**: High  
**Source**: org-identity / M1-FR-14, M1-FR-16  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/org-identity/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; construction pass: `construction/org-identity/functional-design/business-rules.md` (BR-CFG-03, 05, 09), `construction/org-identity/functional-design/domain-entities.md` (Human Authentication Material), `construction/org-identity/infrastructure-design/infrastructure-design.md` (§3)

---

### TC-OI-002 — First authentication sets H's own K and activates H

**Context**: Enrollment material is replaced by the human's own material on first authentication (M1-FR-17), after which the principal is `active`.

**Scenario**: H authenticates for the first time with the enrollment material and a new K.

**Preconditions**:
- The organization level (org-gateway) is running with O configured
- H is `pending` with enrollment material

**Steps**:
1. `POST /first-authentication` with `principal` H, the enrollment material, and a `newSecret` K meeting the K policy (O does not require P)
2. Inspect H's state, H's material records, and the sign-in records

**Expected outcome**: 200 with `state: active` and a `signIn`. H is `active`, with `activatedAt` set. **The same material record** moved from `enrollment` to `active`: its verifier now verifies K and no longer the enrollment material, and `establishedBy` is H. One sign-in record exists, with classes `[K]`.

**Scope**: happy-path · **Priority**: High  
**Source**: org-identity / M1-FR-17, M1-FR-16  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/org-identity/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; construction pass: `construction/org-identity/functional-design/business-rules.md` (BR-FA-01 to 05), `construction/org-identity/functional-design/business-logic-model.md` (§2.2)

---

### TC-OI-003 — Signing in with K yields an organization sign-in

**Context**: Authenticating at the organization level yields a short-lived sign-in asserting subject, organization, time, and classes used (M1-FR-19).

**Scenario**: H signs in with K.

**Preconditions**:
- The organization level (org-gateway) is running with O configured
- H is `active` with K, and no P enrolled

**Steps**:
1. Call `authenticate` with H's identifier and K
2. Inspect the returned sign-in's assertions

**Expected outcome**: 200 with a `signIn` whose token is `soorma_si_` followed by a JWS. Header: `alg` `Ed25519`, `typ` `soorma-si+jwt`, a `kid`. Claims: `iss` `urn:soorma:org:o1`, `sub` H, `sid`, `jti`, `iat`, `auth_time`, `amr` `["pwd"]`, and `exp` 15 minutes after `iat`. The response's `classes` is `[K]`, and `expiresAt` equals `exp`.

**Scope**: happy-path · **Priority**: High  
**Source**: org-identity / M1-FR-19  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/org-identity/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; construction pass: `construction/org-identity/nfr-design/nfr-design-patterns.md` (P-01), `construction/org-identity/nfr-requirements/nfr-requirements.md` (NFR-OI-01)

---

### TC-OI-004 — Once P is enrolled, sign-in needs K and P

**Context**: Core accepts K, or K + P; once a human enrolls P, sign-in needs both (M1-FR-17). This is the MFA support SECURITY-12 requires for the administrative first Admin.

**Scenario**: H, with P enrolled, signs in with K and P.

**Preconditions**:
- The organization level (org-gateway) is running with O configured
- H is `active` with K and P enrolled

**Steps**:
1. `POST /sign-ins` with H, K, and `secondFactor` `{ type: "totp", code }` for the current step

**Expected outcome**: 200. The token's `amr` is `["pwd","otp"]`, and the response's `classes` is `[K, P]`.

**Scope**: happy-path · **Priority**: High  
**Source**: org-identity / M1-FR-17  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/org-identity/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; construction pass: `construction/org-identity/nfr-design/nfr-design-patterns.md` (P-01), `construction/org-identity/nfr-requirements/nfr-requirements.md` (NFR-OI-07)

---

### TC-OI-005 — H renews their own sign-in

**Context**: Self-service includes renewing one's own sign-in (M1-FR-21).

**Scenario**: H renews a live sign-in.

**Preconditions**:
- The organization level (org-gateway) is running with O configured
- H holds a live sign-in

**Steps**:
1. Call `renewSignIn`, presenting the sign-in

**Expected outcome**: 200 with a new token: the same `sid` and `auth_time`, a new `jti`, and `exp` equal to the earlier of now + 15 minutes and `auth_time` + 12 hours. The sign-in record's `expiresAt` is updated. The earlier token stays valid until its own expiry.

**Scope**: happy-path · **Priority**: Medium  
**Source**: org-identity / M1-FR-21  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/org-identity/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; construction pass: `construction/org-identity/functional-design/business-rules.md` (BR-SI-04), `construction/org-identity/nfr-requirements/nfr-requirements.md` (NFR-OI-01)

---

### TC-OI-006 — H ends their own sign-in, the logout

**Context**: Ending one's own sign-in is the logout SECURITY-12 requires (M1-FR-21).

**Scenario**: H ends a live sign-in, then tries to use it.

**Preconditions**:
- The organization level (org-gateway) is running with O configured
- H holds a live sign-in

**Steps**:
1. Call `endSignIn`, presenting the sign-in
2. Call `renewSignIn` with the same sign-in

**Expected outcome**: `endSignIn` returns 204, and the record is `ended` with `endedBy: self`. The renewal is refused with `credential_refused` (401, `WWW-Authenticate: Bearer`), as is every other token of the same sign-in.

**Scope**: happy-path · **Priority**: High  
**Source**: org-identity / M1-FR-21  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/org-identity/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; construction pass: `construction/org-identity/functional-design/business-rules.md` (BR-SI-06)

---

### TC-OI-007 — H changes their own K by presenting the current K

**Context**: A human changes their own material by presenting the current material (M1-FR-21).

**Scenario**: H replaces K with K2.

**Preconditions**:
- The organization level (org-gateway) is running with O configured
- H is `active` with K

**Steps**:
1. Sign H in, giving a live sign-in S
2. `POST /material-changes` with `current: { secret: K }` and `change: { type: "replaceSecret", newSecret: K2 }`
3. Authenticate with K
4. Authenticate with K2
5. Renew S

**Expected outcome**: Step 2: 200 with `retired: [K]` and `signInsEnded: 1`. Step 3: `authentication_failed` (403). Step 4: a sign-in. Step 5: `credential_refused`, because the change ended S. The old K record is `retired`, and its verifier is destroyed.

**Scope**: happy-path · **Priority**: Medium  
**Source**: org-identity / M1-FR-21  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/org-identity/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; construction pass: `construction/org-identity/functional-design/business-rules.md` (BR-MC-01 to 04), `construction/org-identity/functional-design/business-logic-model.md` (§2.5)

---

### TC-OI-008 — Where P is required, H enrolls P without a sign-in by presenting K

**Context**: M1-FR-17 says a human for whom P is required but not enrolled can enroll it without a sign-in, by presenting their current K. Without this, turning the requirement on locks out every human, the only Admin included.

**Scenario**: O's configuration requires P, and H has only K.

**Preconditions**:
- The organization level (org-gateway) is running with O configured
- O's configuration requires P
- H is `active` with K, and no P

**Steps**:
1. `POST /material-changes` with `current: { secret: K }` and `change: { type: "beginSecondFactor", authenticatorType: "totp" }`
2. Compute a TOTP code from the returned seed
3. `POST /material-changes` with `current: { secret: K }` and `change: { type: "confirmSecondFactor", enrollment: <id>, proof: { type: "totp", code } }`
4. Call `authenticate` with K and a fresh code

**Expected outcome**: Step 1: 200 with an enrollment `id`, `expiresAt` 10 minutes later, and `setup` holding a Base32 seed and an `otpauth://` URI. No sign-in is needed or issued. Step 3: 200 with `retired: []`. Step 4: a sign-in with `amr` `["pwd","otp"]`. The stored seed is not the plaintext seed.

**Scope**: happy-path · **Priority**: High  
**Source**: org-identity / M1-FR-17  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/org-identity/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; construction pass: `construction/org-identity/functional-design/business-rules.md` (BR-P-03 to 05), `construction/org-identity/functional-design/business-logic-model.md` (§2.6), `construction/org-identity/nfr-requirements/nfr-requirements.md` (NFR-OI-07 to 10)

---

### TC-OI-009 — Reused enrollment material is refused

**Context**: Enrollment material is single-use (M1-FR-17). Reuse would let whoever knew it, the deployer included, take over the principal.

**Scenario**: Someone presents H's enrollment material after H has activated.

**Preconditions**:
- The organization level (org-gateway) is running with O configured
- H has completed first authentication

**Steps**:
1. Call `firstAuthenticate` with H's identifier and the original enrollment material

**Expected outcome**: `authentication_failed` (403), with no `WWW-Authenticate` header. H's material and state are unchanged. The attempt counts against H's bound, and a Failed Attempt is recorded.

**Scope**: negative · **Priority**: High  
**Source**: org-identity / M1-FR-17  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/org-identity/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; construction pass: `construction/org-identity/functional-design/business-rules.md` (BR-FA-03, BR-RF-01, D-OI-13)

---

### TC-OI-010 — A wrong K is refused, and the failure recorded against H

**Context**: Sign-in is an unauthenticated surface. Failed attempts are recorded against the principal (M1-FR-18).

**Scenario**: An attacker tries a wrong K for H.

**Preconditions**:
- The organization level (org-gateway) is running with O configured
- H is `active`

**Steps**:
1. Call `authenticate` with H's identifier and a wrong K
2. Inspect H's failed-attempt record

**Expected outcome**: `authentication_failed` (403), with exactly the body an unknown principal gets (apart from `instance`). A Failed Attempt record (surface `authenticate`) is written against H, after the response is sent. The log line names H only by H's log pseudonym, never by identifier.

**Scope**: negative · **Priority**: High  
**Source**: org-identity / M1-FR-18  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/org-identity/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; construction pass: `construction/org-identity/functional-design/business-rules.md` (BR-RF-01, 03; BR-REC-03), `construction/org-identity/nfr-requirements/nfr-requirements.md` (NFR-OI-21, 22)

---

### TC-OI-011 — Attempts beyond the bound are refused

**Context**: Attempt volume per principal is bounded (M1-FR-18). The bound's value and shape are set at NFR Requirements.

**Scenario**: Repeated wrong attempts against H exceed the bound.

**Preconditions**:
- The organization level (org-gateway) is running with O configured
- H is `active`
- The sign-in attempt bound is known from U2's NFR Requirements

**Steps**:
1. With the injected clock, make 10 wrong-K attempts for H within 15 minutes, honouring each `Retry-After`
2. Attempt with the correct K
3. Advance the clock until the oldest failure has left the window and any backoff has passed, then attempt with the correct K

**Expected outcome**: From the 5th failure, backoff applies: the waits are 1, 2, 4… seconds. Step 2 is `too_many_attempts` (429) with `Retry-After`, even with the correct K, and K is not checked. Step 3 succeeds: H is never locked permanently. Refusals by the bound are recorded with `refusedByBound` true.

**Scope**: negative · **Priority**: High  
**Source**: org-identity / M1-FR-18  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/org-identity/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; construction pass: `construction/org-identity/nfr-requirements/nfr-requirements.md` (NFR-OI-02 to 04), `construction/org-identity/nfr-design/nfr-design-patterns.md` (P-04, P-05)

---

### TC-OI-012 — A K shorter than 8 characters is refused

**Context**: K must be at least 8 characters (M1-NFR-09, SECURITY-12).

**Scenario**: H tries to set a 7-character K at first authentication.

**Preconditions**:
- The organization level (org-gateway) is running with O configured
- H is `pending`

**Steps**:
1. Call `firstAuthenticate` with the enrollment material and a 7-character K

**Expected outcome**: `secret_rejected` (400), pointer `/newSecret`, reason `too_short`. H stays `pending`. The enrollment material is not consumed and still verifies. The attempt is not counted against the bound.

**Scope**: negative · **Priority**: Medium  
**Source**: org-identity / M1-FR-17 (M1-NFR-09)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/org-identity/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; construction pass: `construction/org-identity/functional-design/business-rules.md` (BR-K-02, 07; BR-FA-04)

---

### TC-OI-013 — A K on a breached-secret list is refused

**Context**: K is checked against breached-secret lists (M1-NFR-09, SECURITY-12).

**Scenario**: H tries to set a K known to be breached.

**Preconditions**:
- The organization level (org-gateway) is running with O configured
- H is `active`

**Steps**:
1. Call `changeMaterial` with the current K and `replaceSecret`, giving a new K taken from the pinned breached list

**Expected outcome**: `secret_rejected` (400), reason `breached`. K is unchanged, live sign-ins are unaffected, and the attempt is not counted.

**Scope**: negative · **Priority**: Medium  
**Source**: org-identity / M1-FR-17 (M1-NFR-09)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/org-identity/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; construction pass: `construction/org-identity/functional-design/business-rules.md` (BR-K-05), `construction/org-identity/nfr-requirements/nfr-requirements.md` (NFR-OI-13)

---

### TC-OI-014 — Where P is required and not enrolled, sign-in is refused

**Context**: Where the organization requires P and it is not enrolled, sign-in is refused until it is (M1-FR-17).

**Scenario**: O requires P, and H tries to sign in with K alone.

**Preconditions**:
- The organization level (org-gateway) is running with O configured
- O's configuration requires P
- H is `active` with K, and no P

**Steps**:
1. Call `authenticate` with H's identifier and K
2. Repeat with a wrong K

**Expected outcome**: Step 1: `second_factor_enrollment_required` (403); no sign-in is issued. Step 2: `authentication_failed` (403). The specific code is reached only with the right K.

**Scope**: negative · **Priority**: High  
**Source**: org-identity / M1-FR-17  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/org-identity/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; construction pass: `construction/org-identity/functional-design/business-rules.md` (BR-P-02, BR-RF-02)

---

### TC-OI-015 — Changing material without the current material is refused

**Context**: A change requires the current material (M1-FR-21). Otherwise anyone could replace a human's material.

**Scenario**: A caller tries to replace H's K without presenting it.

**Preconditions**:
- The organization level (org-gateway) is running with O configured
- H is `active`

**Steps**:
1. Call `changeMaterial` for H with a wrong current K and a new K

**Expected outcome**: `authentication_failed` (403). K is unchanged, live sign-ins are unaffected, the attempt counts against the bound, and a Failed Attempt (surface `changeMaterial`) is recorded.

**Scope**: negative · **Priority**: High  
**Source**: org-identity / M1-FR-21  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/org-identity/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; construction pass: `construction/org-identity/functional-design/business-rules.md` (BR-MC-02)

---

### TC-OI-016 — K alone is refused once P is enrolled

**Context**: Once a human enrolls P, sign-in needs both K and P (M1-FR-17).

**Scenario**: H, with P enrolled, tries K alone.

**Preconditions**:
- The organization level (org-gateway) is running with O configured
- H has K and P enrolled

**Steps**:
1. Call `authenticate` with H's identifier and K only

**Expected outcome**: `authentication_failed` (403). No sign-in is issued. The attempt is counted.

**Scope**: negative · **Priority**: High  
**Source**: org-identity / M1-FR-17  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/org-identity/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; construction pass: `construction/org-identity/functional-design/business-rules.md` (BR-P-01)

---

### TC-OI-017 — Re-applying configuration does not re-register an existing first Admin

**Context**: Configuration registers the first Admin only if the principal does not exist (M1-FR-14). Reset is absent, so lost material is not recoverable by re-applying configuration (requirements, Absent from M1).

**Scenario**: The organization level restarts with the same configuration after H has activated.

**Preconditions**:
- H is `active` with K
- Configuration still names H as E's first Admin

**Steps**:
1. Add new enrollment material for H to the organization's secrets
2. Restart the organization level
3. Inspect H's state and material records
4. Call `firstAuthenticate` with the original material, then with the new material
5. Inspect the start-up logs

**Expected outcome**: H is still `active` with K; no record was created or changed. Both first authentications are `authentication_failed`. A `config.enrollment_ignored` event names H only by log pseudonym, never by identifier, and never contains the material.

**Scope**: edge-boundary · **Priority**: High  
**Source**: org-identity / M1-FR-14  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/org-identity/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; construction pass: `construction/org-identity/functional-design/business-rules.md` (BR-CFG-04), `construction/org-identity/nfr-requirements/nfr-requirements.md` (NFR-OI-22)

---

### TC-OI-018 — A principal's identifier is composed with its organization

**Context**: A human principal's identifier is unique within its organization and composed with it, never allocated globally (M1-FR-16).

**Scenario**: A reviewer inspects H's identifier.

**Preconditions**:
- The organization level (org-gateway) is running with O configured
- H exists

**Steps**:
1. Read H's identifier as returned in a sign-in's subject

**Expected outcome**: The token's `iss` is `urn:soorma:org:o1` and its `sub` is H's identifier. The response's `subject` is `{ organization: o1, principal: h@example.com }`. A request naming another organization with H's identifier and K is `authentication_failed`.

**Scope**: edge-boundary · **Priority**: Medium  
**Source**: org-identity / M1-FR-16  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/org-identity/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; construction pass: `construction/org-identity/functional-design/business-rules.md` (D-OI-21), `construction/org-identity/nfr-design/nfr-design-patterns.md` (P-01)

---

### TC-OI-019 — Organization identity comes from configuration only

**Context**: Organization identity is configured, never inferred from host, instance, or deployment (M1-FR-10).

**Scenario**: The organization level starts on a host whose name resembles another organization, with configuration naming O.

**Preconditions**:
- Configuration naming O
- A host name that differs from O's identifier

**Steps**:
1. Start the organization level
2. Sign H in and read the organization in the sign-in

**Expected outcome**: The sign-in asserts `iss` `urn:soorma:org:o1`, as configured in `tenancy.yaml`. Nothing derives from the host name, the container name, or the Compose project name.

**Scope**: edge-boundary · **Priority**: High  
**Source**: org-identity / M1-FR-10, M1-FR-14  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/org-identity/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; construction pass: `construction/org-identity/functional-design/business-rules.md` (D-OI-09, BR-CFG-01), `construction/org-identity/infrastructure-design/infrastructure-design.md` (§3)

---

### TC-OI-020 — An expired sign-in cannot be renewed

**Context**: The sign-in is short-lived (M1-FR-19), and renewal applies only to a live sign-in.

**Scenario**: H tries to renew a sign-in after its expiry.

**Preconditions**:
- The organization level (org-gateway) is running with O configured
- H holds a sign-in
- Its expiry has passed (the lifetime from U2's NFR Requirements)

**Steps**:
1. Call `renewSignIn`, presenting the expired sign-in

**Expected outcome**: `credential_expired` (401, `WWW-Authenticate: Bearer`), returned only because the token verified. Separately, a sign-in renewed repeatedly never gets an expiry past `auth_time` + 12 hours.

**Scope**: edge-boundary · **Priority**: Medium  
**Source**: org-identity / M1-FR-19, M1-FR-21  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/org-identity/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; construction pass: `construction/org-identity/functional-design/business-rules.md` (BR-SI-07), `construction/org-identity/nfr-requirements/nfr-requirements.md` (NFR-OI-01)

---

### TC-OI-021 — Sign-ins and material changes are recorded

**Context**: Sign-in and first authentication are recorded through their own records: Organization Sign-In, and Human Authentication Material with established-at and established-by (M1-FR-12).

**Scenario**: A reviewer inspects the records after H activates and signs in.

**Preconditions**:
- The organization level (org-gateway) is running with O configured
- H has completed first authentication and one sign-in

**Steps**:
1. Inspect O's sign-in records for H
2. Inspect H's material records

**Expected outcome**: The sign-in record shows H, O, `authenticatedAt`, classes `[K]`, `expiresAt`, and state `live`. The material record shows class K, `enrolledAt` and `enrolledBy` configuration, and `establishedAt` at activation with `establishedBy` H.

**Scope**: edge-boundary · **Priority**: Medium  
**Source**: org-identity / M1-FR-12  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/org-identity/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; construction pass: `construction/org-identity/functional-design/domain-entities.md`, `construction/org-identity/functional-design/business-rules.md` (BR-REC-01, 02)

---

### TC-OI-022 — No operation deletes a human principal

**Context**: A human principal is never deleted or pruned (M1-FR-16). It is a resolution target for sponsor references.

**Scenario**: A reviewer inspects the organization-level contract.

**Preconditions**:
- `contract/org-gateway.openapi.yaml` after U2

**Steps**:
1. List every operation in `contract/org-gateway.openapi.yaml`
2. Connected as the app database role (`soorma_org_app`), try `DELETE` on `principals` and on `materials`

**Expected outcome**: No operation deletes or prunes a principal. The app role is denied `DELETE` on `principals` and `materials`: the database enforces "never pruned" too.

**Scope**: edge-boundary · **Priority**: Low  
**Source**: org-identity / M1-FR-16  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/org-identity/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; construction pass: `construction/org-identity/functional-design/business-rules.md` (BR-HP-03), `construction/org-identity/infrastructure-design/infrastructure-design.md` (§5)

---

### TC-OI-023 — This unit's operations are defined in the contract and validated against it

**Context**: Each surface unit adds its own operations to the wire contract (unit-of-work.md, Q1 B). A raw caller that never links the SDK reaches identical enforcement (M1-FR-02).

**Scenario**: A reviewer checks the unit's operations in `contract/org-gateway.openapi.yaml`, then sends a request that violates the schema.

**Preconditions**:
- `contract/org-gateway.openapi.yaml` after this unit's Code Generation

**Steps**:
1. List the operations in `contract/org-gateway.openapi.yaml` and compare them with this unit's operations: `firstAuthenticate`, `authenticate`, `renewSignIn`, `endSignIn`, `changeMaterial`
2. Check that each references the shared conventions (versioning, error model, security schemes)
3. Send one request with a body that violates its operation's schema

**Expected outcome**: All five operations are present, at `POST /first-authentication`, `/sign-ins`, `/sign-ins/current/renewal`, `/sign-ins/current/end`, and `/material-changes`. Each references `Soorma-Contract-Version` and `Problem`. `firstAuthenticate`, `authenticate`, and `changeMaterial` name no security scheme; `renewSignIn` and `endSignIn` name `signIn`. Request bodies are closed. The violating request is `malformed_request` (400) with a pointer, before the abuse bound is touched.

**Scope**: happy-path · **Priority**: High  
**Source**: org-identity / M1-FR-02  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/org-identity/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; construction pass: `construction/org-identity/functional-design/domain-entities.md` (Wire Shapes), `construction/org-identity/functional-design/business-rules.md` (§10)

---

### TC-OI-024 — A sign-in that fails verification is refused at the organization level

**Context**: The Gateway validates human credentials against O1 to O4 and O8 to O11 by kind (M1-FR-09). The organization level's self-service operations check the presented sign-in themselves.

**Scenario**: A caller presents a sign-in whose signature has been altered.

**Preconditions**:
- The organization level (org-gateway) is running with O configured
- H holds a live sign-in

**Steps**:
1. Alter one character of the sign-in's signature
2. Call `renewSignIn`, presenting the altered sign-in

**Expected outcome**: `credential_refused` (401, `WWW-Authenticate: Bearer`). No sign-in is issued.

**Scope**: negative · **Priority**: High  
**Source**: org-identity / M1-FR-09  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/org-identity/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; construction pass: `construction/org-identity/nfr-design/nfr-design-patterns.md` (P-01)

---

### TC-OI-025 — Material of a class core does not accept is rejected

**Context**: The identity-resolution boundary's human half accepts K and P only; class X (external subjects) is absent in M1 (M1-FR-13, M1-FR-17).

**Scenario**: A caller presents an external-subject assertion in place of K.

**Preconditions**:
- The organization level (org-gateway) is running with O configured
- H is `active`

**Steps**:
1. Call `authenticate` for H, presenting an external identity-provider assertion as the material

**Expected outcome**: `malformed_request` (400): the closed body has no field for an external assertion. The attempt is not counted against the bound.

**Scope**: negative · **Priority**: Medium  
**Source**: org-identity / M1-FR-13  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/org-identity/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`; construction pass: `construction/org-identity/functional-design/business-rules.md` (D-OI-10)

---

### TC-OI-026 — A credential header sent to an unauthenticated operation is a malformed request

**Context**: The three unauthenticated operations accept no credential. A presented `Authorization` or `Soorma-Delegation` header is a client error, refused as `malformed_request` (400), not as a 401 whose `Bearer` challenge would be false (D-OI-26; U1 amendment A4).

**Scenario**: A caller sends a credential header to each unauthenticated operation.

**Preconditions**:
- The local stack is running with O configured
- H is `active`

**Steps**:
1. Call `authenticate` with a valid body and `Authorization: Bearer soorma_si_x`
2. Call `firstAuthenticate` and `changeMaterial` the same way
3. Call `authenticate` with a valid body and a `Soorma-Delegation` header

**Expected outcome**: Each is `malformed_request` (400) with an `errors[]` entry whose `header` names the header and which never echoes its value. No `WWW-Authenticate` header. The attempts are not counted against the bound.

**Scope**: negative · **Priority**: High  
**Source**: org-identity / M1-FR-09 (D-OI-26; BR-RF-06)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/org-identity/code/`  
**Technical references**: `construction/org-identity/functional-design/business-rules.md` (D-OI-26, BR-RF-06), `construction/org-identity/functional-design/business-logic-model.md` (§1)

---

### TC-OI-027 — A credential of the wrong kind is refused on the sign-in operations

**Context**: At S1 only the organization sign-in is accepted, and only on `renewSignIn` and `endSignIn`. Every other presenter is refused (ID §8b matrix; D-OI-05).

**Scenario**: A caller presents other credential kinds to the sign-in operations.

**Preconditions**:
- The local stack is running with O configured
- H holds a live sign-in

**Steps**:
1. Call `renewSignIn` with `Authorization: Bearer soorma_ec_…`, then `soorma_ac_…`, then `soorma_dc_…`
2. Call `renewSignIn` with H's sign-in plus a `Soorma-Delegation` header
3. Call `renewSignIn` with two `Authorization` headers

**Expected outcome**: Every call is `credential_refused` (401, `WWW-Authenticate: Bearer`), with no detail. The sign-in is unchanged.

**Scope**: negative · **Priority**: High  
**Source**: org-identity / M1-FR-09 (D-OI-05)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/org-identity/code/`  
**Technical references**: `construction/org-identity/functional-design/business-rules.md` (D-OI-05)

---

### TC-OI-028 — An unknown principal, or another organization, is refused exactly like a known one

**Context**: Sign-in must not reveal whether a principal exists (BR-ERR-04; BR-RF-01; BR-AB-06).

**Scenario**: An attacker tries identifiers that name no principal, and H's identifier under another organization.

**Preconditions**:
- The local stack is running with O configured

**Steps**:
1. Call `authenticate` for `nobody@example.com` with any K
2. Call `authenticate` for `{ organization: o2, principal: H }` with H's K
3. Repeat step 1 eleven times within 15 minutes
4. Inspect the Failed Attempt records

**Expected outcome**: Steps 1 and 2: `authentication_failed` (403), with the same body as a wrong K for H. Step 3: the 11th is `too_many_attempts`, as for a known principal. No Failed Attempt record exists for the unknown references.

**Scope**: negative · **Priority**: High  
**Source**: org-identity / M1-FR-18 (BR-AB-06; BR-RF-01)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/org-identity/code/`  
**Technical references**: `construction/org-identity/functional-design/business-rules.md` (BR-AB-06, BR-RF-01)

---

### TC-OI-029 — Refusal timing does not reveal whether a principal exists

**Context**: A decoy verification with the real Argon2id parameters, and a Failed Attempt write kept off the response path, keep timing independent of existence (BR-RF-03; D-OI-27). *Split at the enrichment review (the user's change)*: this case checks the **structure** that makes timing independent, deterministically, and runs in CI. The statistical timing comparison is **TC-OI-062**, a reported measurement at Build and Test, not a gate, because a p < 0.01 test fails about 1 run in 100 by chance.

**Scenario**: A test replaces the hashing primitive and the Failed Attempt queue with test doubles that record their calls, and drives `authenticate` for a known and an unknown principal.

**Preconditions**:
- S1's modules, with a recording test double for the Argon2id primitive and for the Failed Attempt queue
- H is `active`

**Steps**:
1. Call `authenticate` for H with a wrong K
2. Call `authenticate` for an unknown identifier with any K
3. Call `firstAuthenticate` for an unknown identifier
4. Inspect the recorded calls

**Expected outcome**: Each call performs **exactly one** Argon2id verification, with the **real parameters** (64 MiB, 3 passes, parallelism 1); the unknown-principal calls verify against the decoy. In step 1, the Failed Attempt record is **enqueued, and the request completes without awaiting** the queue's write (the double's write never resolves, and the response still returns). Steps 2 and 3 enqueue nothing, and their responses equal step 1's apart from `instance`.

**Scope**: edge-boundary · **Priority**: High  
**Source**: org-identity / M1-FR-18 (BR-RF-03)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/org-identity/code/`  
**Technical references**: `construction/org-identity/functional-design/business-rules.md` (BR-RF-03, D-OI-27), `construction/org-identity/nfr-design/nfr-design-patterns.md` (P-10, P-11)

---

### TC-OI-030 — A success does not restore the window's allowance

**Context**: Window counts only decay; a success resets the backoff only (NFR-OI-02, 03).

**Scenario**: H fails, succeeds, and fails again within one window.

**Preconditions**:
- The local stack is running with O configured
- H is `active`; injected clock

**Steps**:
1. Make 4 wrong-K attempts for H
2. Authenticate with the correct K
3. Make 6 more wrong-K attempts, honouring any `Retry-After`
4. Attempt once more with the correct K, within 15 minutes of the first failure

**Expected outcome**: Step 2 succeeds, and the backoff restarts (the next failures wait no backoff until the 5th consecutive). Step 4 is `too_many_attempts`: the 10 failures in the window still count.

**Scope**: edge-boundary · **Priority**: High  
**Source**: org-identity / M1-FR-18 (NFR-OI-02, 03)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/org-identity/code/`  
**Technical references**: `construction/org-identity/nfr-requirements/nfr-requirements.md` (NFR-OI-02, 03), `construction/org-identity/nfr-design/nfr-design-patterns.md` (P-04)

---

### TC-OI-031 — Backoff doubles from the 5th failure, to a 15-minute cap, and Retry-After reports the later wait

**Context**: The backoff wait for the n-th consecutive failure is 2^(n−5) seconds, capped at 900; `Retry-After` is the later of the window and backoff waits (NFR-OI-03, 04).

**Scenario**: Consecutive failures for one reference under the injected clock.

**Preconditions**:
- The local stack is running with O configured
- Injected clock

**Steps**:
1. Make consecutive wrong-K attempts for an identifier, advancing the clock past each wait, while watching `Retry-After`
2. Attempt before a wait has passed

**Expected outcome**: Waits after the 5th, 6th, 7th… failure are 1, 2, 4… seconds, never more than 900. An attempt before the wait has passed is `too_many_attempts` without checking K, and `Retry-After` is the remaining wait (rounded up, at least 1), or the window's wait when that is later.

**Scope**: edge-boundary · **Priority**: Medium  
**Source**: org-identity / M1-FR-18 (NFR-OI-03, 04)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/org-identity/code/`  
**Technical references**: `construction/org-identity/nfr-requirements/nfr-requirements.md` (NFR-OI-03, 04), `construction/org-identity/nfr-design/nfr-design-patterns.md` (P-05)

---

### TC-OI-032 — The three surfaces share one counter

**Context**: An attacker must not get three budgets of guesses at one K (D-OI-16; BR-AB-01).

**Scenario**: Wrong attempts are spread across the three surfaces for H.

**Preconditions**:
- The local stack is running with O configured
- H is `active`; injected clock

**Steps**:
1. Make 4 wrong attempts at `authenticate`, 3 at `changeMaterial`, and 3 at `firstAuthenticate` for H, honouring `Retry-After`
2. Make one more attempt at any of them

**Expected outcome**: Step 2 is `too_many_attempts`: 10 failures across the three surfaces exhaust one window.

**Scope**: negative · **Priority**: High  
**Source**: org-identity / M1-FR-18 (BR-AB-01)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/org-identity/code/`  
**Technical references**: `construction/org-identity/functional-design/business-rules.md` (BR-AB-01)

---

### TC-OI-033 — Concurrent attempts cannot exceed the bound, and a success removes only its own reservation

**Context**: Admission reserves a failure before verifying and settles after (NFR Design P-04), so concurrency cannot exceed the bound (NFR-OI-06).

**Scenario**: Many attempts arrive at once for one reference.

**Preconditions**:
- The local stack is running with O configured
- H is `active`; a fresh window

**Steps**:
1. Send 20 wrong-K `authenticate` requests for H in parallel
2. In a fresh window, send 9 wrong-K requests and 1 correct request for H in parallel
3. Inspect H's slot

**Expected outcome**: Step 1: at most 10 are admitted to verification; the rest are `too_many_attempts`. Step 2: the correct request signs in, and the slot then holds exactly 9 entries: the success removed only its own reservation.

**Scope**: edge-boundary · **Priority**: High  
**Source**: org-identity / M1-FR-18 (NFR-OI-05, 06)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/org-identity/code/`  
**Technical references**: `construction/org-identity/nfr-design/nfr-design-patterns.md` (P-04), `construction/org-identity/nfr-requirements/nfr-requirements.md` (NFR-OI-06)

---

### TC-OI-034 — Two concurrent first authentications with the same enrollment material succeed at most once

**Context**: Single use is atomic (D-OI-04; NFR-OI-15).

**Scenario**: Two clients race to activate H with the same material.

**Preconditions**:
- The local stack is running with O configured
- H is `pending`

**Steps**:
1. Send two `firstAuthenticate` requests for H with the same enrollment material and different K, in parallel

**Expected outcome**: Exactly one returns 200; the other is `authentication_failed`. H has one active K, the winner's.

**Scope**: edge-boundary · **Priority**: High  
**Source**: org-identity / M1-FR-17 (D-OI-04)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/org-identity/code/`  
**Technical references**: `construction/org-identity/functional-design/business-rules.md` (D-OI-04), `construction/org-identity/nfr-design/nfr-design-patterns.md` (P-13)

---

### TC-OI-035 — Where P is required, first authentication activates H and issues no sign-in

**Context**: `firstAuthenticate` reports the P requirement in a 200, because K was set and H is `active` (D-OI-23).

**Scenario**: O requires P, and H activates.

**Preconditions**:
- The local stack is running with O configured with `secondFactorRequired: true`
- H is `pending`

**Steps**:
1. Call `firstAuthenticate` with valid enrollment material and K
2. Call `authenticate` with K

**Expected outcome**: Step 1: 200 with `state: active`, `secondFactorEnrollmentRequired: true`, and no `signIn`. Step 2: `second_factor_enrollment_required`. H can then enroll P as in TC-OI-008.

**Scope**: happy-path · **Priority**: High  
**Source**: org-identity / M1-FR-17 (D-OI-23)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/org-identity/code/`  
**Technical references**: `construction/org-identity/functional-design/business-rules.md` (D-OI-23, BR-FA-05)

---

### TC-OI-036 — A material change ends every live sign-in

**Context**: A change of K or P ends every live sign-in of that human (D-OI-18; BR-MC-04).

**Scenario**: H holds two sign-ins, then enrolls P.

**Preconditions**:
- The local stack is running with O configured
- H is `active` with K, and holds two live sign-ins S1 and S2

**Steps**:
1. Enroll P (begin and confirm) presenting K
2. Renew S1, then S2
3. Inspect the sign-in records

**Expected outcome**: The confirmation reports `signInsEnded: 2`. Both renewals are `credential_refused`. Both records are `ended` with `endedBy: materialChange`.

**Scope**: happy-path · **Priority**: High  
**Source**: org-identity / M1-FR-21 (BR-MC-04)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/org-identity/code/`  
**Technical references**: `construction/org-identity/functional-design/business-rules.md` (BR-MC-04, D-OI-18)

---

### TC-OI-037 — Replacing P retires the old one

**Context**: P can be replaced, not removed, in M1 (D-OI-24; BR-P-05).

**Scenario**: H, with P enrolled, enrolls a new authenticator.

**Preconditions**:
- The local stack is running with O configured
- H is `active` with K and P1

**Steps**:
1. Begin and confirm a new TOTP enrollment P2, presenting K and a P1 code
2. Authenticate with K and a P1 code
3. Authenticate with K and a P2 code

**Expected outcome**: The confirmation reports `retired: [P]`. Step 2 is `authentication_failed`. Step 3 signs in. The P1 record is `retired` with its seed destroyed. No operation removes P without replacing it.

**Scope**: happy-path · **Priority**: Medium  
**Source**: org-identity / M1-FR-21 (BR-P-05; D-OI-24)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/org-identity/code/`  
**Technical references**: `construction/org-identity/functional-design/business-rules.md` (BR-P-05, D-OI-24)

---

### TC-OI-038 — A failed P confirmation is refused without counting, and a pending enrollment expires

**Context**: After the current material verifies, a confirmation failure is `second_factor_not_confirmed`, not counted (BR-P-06); a pending enrollment lives 10 minutes (NFR-OI-10).

**Scenario**: H confirms with a wrong code, a wrong id, and too late.

**Preconditions**:
- The local stack is running with O configured
- H is `active` with K; injected clock

**Steps**:
1. Begin a P enrollment
2. Confirm with a wrong code
3. Confirm with another enrollment id
4. Advance the clock 10 minutes and 1 second, and confirm with a correct code

**Expected outcome**: Steps 2 to 4 are each `second_factor_not_confirmed` (403), with no detail. None counts against the bound. After step 4 no pending enrollment remains; H has no P.

**Scope**: negative · **Priority**: Medium  
**Source**: org-identity / M1-FR-17 (BR-P-06; NFR-OI-10)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/org-identity/code/`  
**Technical references**: `construction/org-identity/functional-design/business-rules.md` (BR-P-06), `construction/org-identity/nfr-requirements/nfr-requirements.md` (NFR-OI-10)

---

### TC-OI-039 — TOTP codes follow RFC 6238, with one step of drift, each accepted once

**Context**: The M1 P type is TOTP; each code is accepted at most once (NFR-OI-07, 08; P-12).

**Scenario**: Unit and service checks of the TOTP implementation.

**Preconditions**:
- TOTP module; the local stack for steps 3 and 4
- H has P enrolled; injected clock

**Steps**:
1. Check the implementation against RFC 6238 Appendix B's SHA-1 vectors
2. Check codes one step early and late (accepted) and two steps away (refused)
3. Authenticate twice with the same code
4. After a later step's code is accepted, authenticate with an earlier step's code

**Expected outcome**: Step 1 matches every vector. Step 2 as stated. Step 3: the second is `authentication_failed`. Step 4: `authentication_failed`. Two concurrent uses of one code cannot both succeed.

**Scope**: edge-boundary · **Priority**: High  
**Source**: org-identity / M1-FR-17 (NFR-OI-07, 08)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/org-identity/code/`  
**Technical references**: `construction/org-identity/nfr-requirements/nfr-requirements.md` (NFR-OI-07, 08), `construction/org-identity/nfr-design/nfr-design-patterns.md` (P-12)

---

### TC-OI-040 — Renewal is refused when P is required and the sign-in lacks it

**Context**: A sign-in whose classes no longer satisfy the organization's P requirement cannot be renewed (BR-SI-05).

**Scenario**: O's requirement is turned on while H holds a K-only sign-in.

**Preconditions**:
- H holds a live sign-in with classes `[K]`
- O's configuration is changed to require P, and the organization level restarted

**Steps**:
1. Call `renewSignIn` with H's sign-in

**Expected outcome**: `second_factor_enrollment_required` (403). The sign-in is not extended, and expires at its own time.

**Scope**: edge-boundary · **Priority**: Medium  
**Source**: org-identity / M1-FR-17 (BR-SI-05)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/org-identity/code/`  
**Technical references**: `construction/org-identity/functional-design/business-rules.md` (BR-SI-05, BR-P-10)

---

### TC-OI-041 — Renewal never passes the 12-hour absolute maximum

**Context**: NFR-OI-01: a token's expiry is never later than `auth_time` + 12 hours.

**Scenario**: H renews near the absolute maximum.

**Preconditions**:
- The local stack is running with O configured
- H holds a sign-in; injected clock

**Steps**:
1. Renew every 10 minutes until 11 hours 50 minutes after `auth_time`
2. Renew at 11 hours 50 minutes
3. Advance to 12 hours and renew

**Expected outcome**: Step 2's token expires at exactly `auth_time` + 12 hours. Step 3 is `credential_expired`.

**Scope**: edge-boundary · **Priority**: High  
**Source**: org-identity / M1-FR-19 (NFR-OI-01)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/org-identity/code/`  
**Technical references**: `construction/org-identity/nfr-requirements/nfr-requirements.md` (NFR-OI-01)

---

### TC-OI-042 — The K policy normalizes, measures, and rejects as specified

**Context**: K is NFKC-normalized before every check; 8 to 256 code points; no control characters; no context word; not the material it replaces (BR-K).

**Scenario**: A series of new Ks through `replaceSecret`.

**Preconditions**:
- The local stack is running with O configured
- H is `active` with K

**Steps**:
1. Try a K of 256 code points after NFKC, and one of 257
2. Try a K that is only 7 code points after NFKC but longer before it
3. Try a K containing a control character
4. Try a K that contains H's identifier in another case (`xH@EXAMPLE.COMx`), one that contains `SOORMA`, and one that contains only the 2-character organization identifier `o1` (`o1-garden-lantern`)
5. Try the current K as the new K

**Expected outcome**: Step 1: 256 accepted; 257 is `secret_rejected` `too_long`. Step 2: `too_short`. Step 3: `disallowed_character`. Step 4: the identifier and `soorma` Ks are `secret_rejected`, with reason **`context_word`** (BR-K-07, amendment A5); the K containing only `o1` is accepted, because identifiers shorter than 4 characters are not matched. Step 5: `reused`.

**Scope**: edge-boundary · **Priority**: Medium  
**Source**: org-identity / M1-FR-17 (BR-K-01 to 07; NFR-OI-14)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/org-identity/code/`  
**Technical references**: `construction/org-identity/functional-design/business-rules.md` (BR-K), `construction/org-identity/nfr-requirements/nfr-requirements.md` (NFR-OI-14)

---

### TC-OI-043 — K is stored only as Argon2id over the full normalized input

**Context**: K is held only in a one-way form, with no truncation (BR-K-08; NFR-OI-11).

**Scenario**: A reviewer inspects stored verifiers and verification.

**Preconditions**:
- The local stack is running with O configured

**Steps**:
1. Set K to a 100-byte string, then try to authenticate with a K equal in its first 72 bytes and different after
2. Inspect the stored verifier

**Expected outcome**: Authentication with the second K fails. The verifier records `argon2id`, memory 64 MiB, 3 passes, parallelism 1, and a salt, and holds no recoverable K. No environment configuration or store holds any human material.

**Scope**: edge-boundary · **Priority**: High  
**Source**: org-identity / M1-FR-17 (BR-K-08; NFR-OI-11)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/org-identity/code/`  
**Technical references**: `construction/org-identity/nfr-requirements/nfr-requirements.md` (NFR-OI-11, 12), `construction/org-identity/functional-design/l1-coverage-matrix.md` (L1-11)

---

### TC-OI-044 — Sign-in verification is strict, and the token asserts no environment

**Context**: Verifiers require every claim, the exact `typ`, and `Ed25519` only (P-01). The token names no environment or location (BR-SI-02).

**Scenario**: A tester alters tokens.

**Preconditions**:
- The local stack is running with O configured
- H holds a sign-in

**Steps**:
1. Decode the token and list its claims
2. Present tokens re-signed with the organization's key but with, in turn, a claim removed, `typ` changed, `iss` changed
3. Present a token with `alg` `EdDSA`, and one signed by another key

**Expected outcome**: Step 1: no claim names an environment, address, or host, and there is no `aud`. Steps 2 and 3: each is `credential_refused`.

**Scope**: negative · **Priority**: High  
**Source**: org-identity / M1-FR-19 (BR-SI-02; P-01)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/org-identity/code/`  
**Technical references**: `construction/org-identity/nfr-design/nfr-design-patterns.md` (P-01), `construction/org-identity/functional-design/l1-coverage-matrix.md` (L1-21)

---

### TC-OI-045 — The internal interface accepts only signed requests bound to their content

**Context**: Every internal call carries a JWS from a configured environment's key, bound to method, full target, and body hash; network location is never the check (P-06; I3).

**Scenario**: Callers on the internal network try unsigned and altered requests.

**Preconditions**:
- The local stack is running; a test container on `org-internal-e` holds E's caller key

**Steps**:
1. Call `principalExists` with no token
2. Call with a token signed by an unconfigured key, and with E's key but `iss` E2
3. Call with an expired token, and with another `aud`
4. Reuse a valid token with a different query string, and `signInStatus`'s token on another sign-in id
5. Call from a different container address with a valid token for that exact request

**Expected outcome**: Steps 1 to 4: each refused, with no detail, and logged as `internal.call_refused`. Step 5: answered: the address played no part.

**Scope**: negative · **Priority**: High  
**Source**: org-identity / M1-FR-10 (BR-INT-02; P-06; I3)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/org-identity/code/`  
**Technical references**: `construction/org-identity/nfr-design/nfr-design-patterns.md` (P-06), `construction/org-identity/functional-design/invariant-coverage-matrix.md` (I3)

---

### TC-OI-046 — The internal interface discloses only what each operation states

**Context**: `verifyOnlyMaterial` returns only public verify keys; `principalExists` only yes or no; `signInStatus` only `live`, `ended`, or `unknown` (BR-INT-03 to 05).

**Scenario**: A signed caller reads each operation.

**Preconditions**:
- The local stack is running; a signed test caller on `org-internal-e`
- H exists and holds one live and one ended sign-in

**Steps**:
1. Call `verifyOnlyMaterial`
2. Verify H's sign-in with the returned keys, and try to sign a token with them
3. Call `principalExists` for H and for an unknown identifier
4. Call `signInStatus` for the live, the ended, and an unknown sign-in id

**Expected outcome**: Step 1: a JWKS of Ed25519 public keys only. Step 2: verification succeeds; signing is impossible. Step 3: `{ exists: true }` and `{ exists: false }`, nothing else. Step 4: `live`, `ended`, `unknown`, nothing else.

**Scope**: happy-path · **Priority**: High  
**Source**: org-identity / M1-FR-10 (BR-INT-03 to 05)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/org-identity/code/`  
**Technical references**: `construction/org-identity/functional-design/business-rules.md` (BR-INT), `construction/org-identity/nfr-design/logical-components.md` (§5)

---

### TC-OI-047 — The listeners are separate

**Context**: The edge serves only the contract's operations, the internal listener only the internal ones, and health is loopback-only (P-07; I6).

**Scenario**: A tester probes each port.

**Preconditions**:
- The local stack is running

**Steps**:
1. Call each internal path on the edge port
2. Call each edge path on the internal port (signed)
3. From another container, connect to the health port; inside the S1 container, call it

**Expected outcome**: Steps 1 and 2: 404. Step 3: unreachable from outside; inside, 204 with an empty body.

**Scope**: edge-boundary · **Priority**: Medium  
**Source**: org-identity / M1-FR-10 (P-07; I6)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/org-identity/code/`  
**Technical references**: `construction/org-identity/nfr-design/nfr-design-patterns.md` (P-07)

---

### TC-OI-048 — Configuration errors stop start-up, and no environment part carries material

**Context**: Enrollment material is referenced only in the organization's part; any configuration or key error stops start-up (BR-CFG-02, 03, 08; ID §6).

**Scenario**: The organization level starts with faulty configurations.

**Preconditions**:
- An absent principal named as a first Admin

**Steps**:
1. Start with an environment part carrying an `enrollmentMaterial` field
2. Start with a first Admin who does not exist and no material configured
3. Start with a malformed signing key
4. Start with the counter secret missing

**Expected outcome**: Each start-up fails with a logged configuration error and no listener opens. No partial configuration is used.

**Scope**: negative · **Priority**: High  
**Source**: org-identity / M1-FR-14 (BR-CFG-02, 03, 08)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/org-identity/code/`  
**Technical references**: `construction/org-identity/functional-design/business-rules.md` (BR-CFG), `construction/org-identity/functional-design/l1-coverage-matrix.md` (L1-27)

---

### TC-OI-049 — Logs carry no secret and no human identifier

**Context**: No K, P proof or seed, enrollment material, token, key, or human identifier appears in any log; humans are named by log pseudonym, with a separate key per level (NFR-OI-22, 23).

**Scenario**: Every S1 flow runs with known values, and the logs are searched.

**Preconditions**:
- The local stack with known secrets, and known identifiers (H and an unknown one)

**Steps**:
1. Run every flow in TC-OI-001 to 048, capturing all logs
2. Search the captured logs for every secret, token, and identifier
3. Check each security event that names a human
4. Compute H's pseudonym under the organization's key, and under a different key

**Expected outcome**: Step 2: no match. Step 3: each carries `hp_…`, the event name, and the request id. Step 4: the pseudonym in the logs matches the organization key's and differs from the other key's.

**Scope**: negative · **Priority**: High  
**Source**: org-identity / M1-FR-12 (NFR-OI-22, 23; SECURITY-03)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/org-identity/code/`  
**Technical references**: `construction/org-identity/nfr-requirements/nfr-requirements.md` (NFR-OI-22, 23), `construction/org-identity/nfr-design/nfr-design-patterns.md` (P-17)

---

### TC-OI-050 — The Failed Attempt writer stays off the response path

**Context**: The record is written after the response, in batches; a full queue drops and logs; shutdown flushes (NFR-OI-21; P-11).

**Scenario**: The writer under delay and pressure.

**Preconditions**:
- S1 with its store writes for `failed_attempts` delayed by a test hook

**Steps**:
1. Make a wrong-K attempt for H and time the response
2. Fill the queue past 10,000
3. Stop S1 gracefully with records queued

**Expected outcome**: Step 1: the response is not delayed by the write, and the record appears later. Step 2: excess records are dropped, and `failed_attempt.dropped` is logged without a secret. Step 3: queued records are written before exit.

**Scope**: edge-boundary · **Priority**: Medium  
**Source**: org-identity / M1-FR-18 (NFR-OI-21)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/org-identity/code/`  
**Technical references**: `construction/org-identity/nfr-requirements/nfr-requirements.md` (NFR-OI-21), `construction/org-identity/nfr-design/nfr-design-patterns.md` (P-11)

---

### TC-OI-051 — Migrations run once, in org-migrate, and S1 holds only the app role

**Context**: Migrations run in the one-shot `org-migrate` service under an advisory lock; S1 never holds the migrator credential (NFR-OI-18; D-ID-OI-02).

**Scenario**: The stack starts with migration edge cases.

**Preconditions**:
- A fresh org store

**Steps**:
1. Run `org-migrate` twice concurrently
2. Edit an applied migration and run `org-migrate`
3. Start the stack after step 2
4. Inspect `org-gateway`'s mounted secrets and its database role's privileges

**Expected outcome**: Step 1: each migration applied once. Step 2: `org-migrate` fails. Step 3: `org-gateway` does not start. Step 4: no migrator password is mounted; the app role has no DDL and no `DELETE` on `principals` or `materials`.

**Scope**: edge-boundary · **Priority**: High  
**Source**: org-identity / M1-FR-16 (NFR-OI-18; D-ID-OI-02)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/org-identity/code/`  
**Technical references**: `construction/org-identity/nfr-requirements/nfr-requirements.md` (NFR-OI-18), `construction/org-identity/infrastructure-design/infrastructure-design.md` (§5)

---

### TC-OI-052 — S1 fails closed when the store or the hashing budget is exhausted

**Context**: An unreachable store, or a saturated hashing semaphore, gives `unavailable` (503), never a partial success (NFR-OI-20; P-15).

**Scenario**: Dependencies fail under load.

**Preconditions**:
- The local stack is running with O configured
- Injected clock

**Steps**:
1. Stop `org-db`, then call `authenticate`
2. Restart it; hold every hashing permit with a test hook, then call `authenticate`
3. Check the default permit count with a stubbed CPU count of 16 and the default budget

**Expected outcome**: Step 1: `unavailable` (503, `Retry-After`); no sign-in. Step 2: `unavailable` after 2 seconds. Step 3: 8 permits.

**Scope**: negative · **Priority**: Medium  
**Source**: org-identity / M1-FR-18 (NFR-OI-20; P-09, P-15)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/org-identity/code/`  
**Technical references**: `construction/org-identity/nfr-requirements/nfr-requirements.md` (NFR-OI-20), `construction/org-identity/nfr-design/nfr-design-patterns.md` (P-09, P-15)

---

### TC-OI-053 — Retention prunes what it may, and never a principal or material

**Context**: Failed Attempt records, and ended or expired sign-ins, are pruned after 90 days; principals and material never (NFR-OI-25).

**Scenario**: The daily pruner runs.

**Preconditions**:
- Records 89 and 91 days old of each prunable kind; principals and retired material older than 91 days; injected clock

**Steps**:
1. Run the pruner in two instances at once

**Expected outcome**: Only the 91-day-old prunable records are deleted, once. Every principal and material record remains.

**Scope**: edge-boundary · **Priority**: Medium  
**Source**: org-identity / M1-FR-16 (NFR-OI-25)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/org-identity/code/`  
**Technical references**: `construction/org-identity/nfr-requirements/nfr-requirements.md` (NFR-OI-25), `construction/org-identity/nfr-design/nfr-design-patterns.md` (P-16)

---

### TC-OI-054 — TOTP seeds are encrypted and bound to their row

**Context**: Seeds are AES-256-GCM with associated data binding each ciphertext to its row (P-03; NFR-OI-09).

**Scenario**: A reviewer inspects stored seeds.

**Preconditions**:
- The local stack is running with O configured
- Two humans' P records (a test fixture)

**Steps**:
1. Read a stored seed column
2. Copy one row's ciphertext into the other row, and authenticate the second human
3. Remove the seed key's id from configuration and restart

**Expected outcome**: Step 1: not the plaintext seed; carries a key id and nonce. Step 2: `authentication_failed`. Step 3: start-up fails, or verification fails closed, never accepting a code.

**Scope**: negative · **Priority**: High  
**Source**: org-identity / M1-FR-17 (NFR-OI-09; P-03)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/org-identity/code/`  
**Technical references**: `construction/org-identity/nfr-design/nfr-design-patterns.md` (P-03)

---

### TC-OI-055 — Request bodies over 16 KiB are refused

**Context**: S1 bounds request bodies at 16 KiB (NFR-OI-27).

**Scenario**: A caller sends an oversized body.

**Preconditions**:
- The local stack is running with O configured

**Steps**:
1. Send `authenticate` with a body of exactly 16 KiB, then 16 KiB + 1 byte

**Expected outcome**: The first is processed (refused or accepted on its merits). The second is `payload_too_large` (413), not counted against the bound.

**Scope**: negative · **Priority**: Low  
**Source**: org-identity / M1-FR-02 (NFR-OI-27)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/org-identity/code/`  
**Technical references**: `construction/org-identity/nfr-requirements/nfr-requirements.md` (NFR-OI-27)

---

### TC-OI-056 — The local stack is TLS-only and minimally exposed

**Context**: TLS 1.3 everywhere with a name-constrained CA; only the edge is published, on loopback (Infrastructure Design §4, §6).

**Scenario**: A tester checks the stack from the host and inside it.

**Preconditions**:
- `pnpm stack:init` and `pnpm stack:up` completed

**Steps**:
1. List published host ports
2. Connect to the edge with `--cacert` the stack CA, and without it
3. Connect to `org-db` from `org-gateway` with `sslmode=verify-full`, and try a non-TLS connection
4. Inspect the CA certificate's name constraints, and try to issue a certificate for `example.com` with the CA key

**Expected outcome**: Step 1: only `127.0.0.1:8441`. Step 2: succeeds with the CA, fails without. Step 3: TLS succeeds; non-TLS refused. Step 4: constraints permit only `localhost`, `soorma.internal`, and loopback addresses, marked critical; a client honouring them rejects the `example.com` certificate.

**Scope**: edge-boundary · **Priority**: High  
**Source**: org-identity / M1-NFR-05 (Infrastructure Design §4, §6)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/org-identity/code/`  
**Technical references**: `construction/org-identity/infrastructure-design/infrastructure-design.md` (§4, §6)

---

### TC-OI-057 — Secrets are generated safely and never reach the repository or the image

**Context**: `stack:init` never overwrites; handover files hold the enrollment material; the secret check runs over the repository and the built image (Infrastructure Design §3, §8).

**Scenario**: Init and CI checks.

**Preconditions**:
- A clean checkout

**Steps**:
1. Run `pnpm stack:init` twice
2. Inspect file modes in `deploy/local/.secrets/`, and `git status`
3. Run the secret-pattern check over the repository and over the exported S1 image
4. Plant a `soorma_em_` value in a file under `deploy/` and rerun the check
5. Inspect the S1 container's environment variables

**Expected outcome**: Step 1: the second run refuses to overwrite. Step 2: mode 0600; nothing tracked. Step 3: no match. Step 4: the check fails. Step 5: no secret in any environment variable.

**Scope**: negative · **Priority**: High  
**Source**: org-identity / M1-NFR-09 (Infrastructure Design §3, §8)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/org-identity/code/`  
**Technical references**: `construction/org-identity/infrastructure-design/infrastructure-design.md` (§3, §8)

---

### TC-OI-058 — The breached-list artifact matches its manifest

**Context**: The derived list is a pinned artifact; the build checks its digest (NFR-OI-13).

**Scenario**: The build verifies the artifact.

**Preconditions**:
- The repository with the derived list and its manifest

**Steps**:
1. Run the build check
2. Change one byte of the derived file and rerun
3. Inspect `.gitattributes`

**Expected outcome**: Step 1 passes. Step 2 fails. Step 3: the derived file is marked `binary`. The manifest records source, commit, path, licence (MIT), and both digests.

**Scope**: edge-boundary · **Priority**: Medium  
**Source**: org-identity / M1-NFR-09 (NFR-OI-13)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/org-identity/code/`  
**Technical references**: `construction/org-identity/nfr-requirements/nfr-requirements.md` (NFR-OI-13)

---

### TC-OI-059 — Sign-in meets its latency targets

**Context**: p95 at most 500 ms for `authenticate` and `firstAuthenticate`, and 200 ms for other S1 operations, on the local stack (NFR-OI-19).

**Scenario**: A load test at Build and Test.

**Preconditions**:
- The local stack; H active; the bound not engaged (distinct principals, or the bound raised in a test configuration)

**Steps**:
1. Run 500 `authenticate`, 500 `renewSignIn`, and 500 `endSignIn` requests at a rate within the hashing budget
2. Compute p95 per operation

**Expected outcome**: `authenticate` p95 ≤ 500 ms; `renewSignIn` and `endSignIn` p95 ≤ 200 ms.

**Scope**: edge-boundary · **Priority**: Medium  
**Source**: org-identity / M1-FR-19 (NFR-OI-19)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/org-identity/code/`  
**Technical references**: `construction/org-identity/nfr-requirements/nfr-requirements.md` (NFR-OI-19)

---

### TC-OI-060 — The identity-resolution seam decides identity only

**Context**: The seam's human half returns a principal reference or a rejection and changes no state (BR-SEAM; PF §12).

**Scenario**: A unit test of the seam implementation.

**Preconditions**:
- The P6 implementation behind `seams/identity-resolution`

**Steps**:
1. Resolve K, a TOTP proof, and enrollment material for H, correct and wrong
2. Inspect the store and the principal's state after each

**Expected outcome**: Each returns H's reference or a rejection. No call changes any record: single use, state, and sign-ins are P10's.

**Scope**: edge-boundary · **Priority**: Medium  
**Source**: org-identity / M1-FR-13 (BR-SEAM-01, 02)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/org-identity/code/`  
**Technical references**: `construction/org-identity/functional-design/business-rules.md` (BR-SEAM), `construction/org-identity/functional-design/l1-coverage-matrix.md` (L1-32)

---

### TC-OI-061 — No tenant identifier is hard-coded in platform code

**Context**: Every principal and organization comes from configuration; tenant values appear only in labelled test fixtures and deployment configuration (I9).

**Scenario**: A code check at Code Generation and Build and Test.

**Preconditions**:
- U2's packages and services

**Steps**:
1. Search `packages/` and `services/` source, outside `test/`, for `o1`, `h@example.com`, and any `soorma_em_` value

**Expected outcome**: No match outside `test/` and `deploy/`.

**Scope**: edge-boundary · **Priority**: Low  
**Source**: org-identity / M1-FR-14 (I9)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/org-identity/code/`  
**Technical references**: `construction/org-identity/functional-design/invariant-coverage-matrix.md` (I9)

---

### TC-OI-062 — Refusal timing for known and unknown principals is measured and reported

**Context**: The statistical half of TC-OI-029, split from it at the enrichment review (the user's change). BR-RF-03's structure is checked deterministically by TC-OI-029. This case **measures** the result on the running stack and **reports** it. It is **not a pass/fail gate**: a test at p < 0.01 would fail about 1 run in 100 by chance alone.

**Scenario**: At Build and Test, a tester compares response times for a known and an unknown principal on the local stack.

**Preconditions**:
- The local stack is running with O configured
- H is `active`; the hashing semaphore is not saturated; the bound does not engage (fresh windows, or the bound raised in a test configuration)

**Steps**:
1. Send 200 wrong-K `authenticate` requests for H and 200 for an unknown identifier, interleaved
2. Compute each distribution's median and p95, and a two-sample test statistic and p-value

**Expected outcome**: **A reported measurement, recorded in the Build and Test summary**: both medians and p95s, their difference, and the test's p-value. It does not fail the build. A large, repeatable difference is investigated as a defect against BR-RF-03, and TC-OI-029 extended to catch its cause.

**Scope**: edge-boundary · **Priority**: Low  
**Source**: org-identity / M1-FR-18 (BR-RF-03)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/org-identity/code/`  
**Technical references**: `construction/org-identity/functional-design/business-rules.md` (BR-RF-03), `construction/org-identity/nfr-requirements/nfr-requirements.md` (NFR-OI-19)

---
