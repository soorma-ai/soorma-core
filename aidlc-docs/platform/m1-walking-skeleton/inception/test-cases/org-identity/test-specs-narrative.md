# Test Specifications (Narrative): org-identity

**Unit**: `org-identity` (U2: human principals, sign-in, and self-service at the organization level, control face)  
**Unit abbreviation**: OI = org-identity  
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

### TC-OI-001 — A configured first Admin is registered as pending, with enrollment material

**Context**: M1-FR-14 has configuration name an environment's first Admin, and register the principal `pending` with single-use enrollment material if it does not exist. This is the trust root for every later step.

**Scenario**: The deployer starts the stack with configuration naming H as E's first Admin.

**Preconditions**:
- Configuration naming O, E, and H as E's first Admin with enrollment material
- No principal H exists yet

**Steps**:
1. Start the organization level
2. Inspect O's principals

**Expected outcome**: H exists in O as `pending`, with one single-use enrollment material record. No other principal was created.

**Scope**: happy-path · **Priority**: High  
**Source**: org-identity / M1-FR-14, M1-FR-16  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/org-identity/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

---

### TC-OI-002 — First authentication sets H's own K and activates H

**Context**: Enrollment material is replaced by the human's own material on first authentication (M1-FR-17), after which the principal is `active`.

**Scenario**: H authenticates for the first time with the enrollment material and a new K.

**Preconditions**:
- The organization level (org-gateway) is running with O configured
- H is `pending` with enrollment material

**Steps**:
1. Call `firstAuthenticate` with H's identifier, the enrollment material, and a new K meeting the K policy
2. Inspect H's state and material

**Expected outcome**: A sign-in is returned. H is `active`, the enrollment material is retired, and K is active.

**Scope**: happy-path · **Priority**: High  
**Source**: org-identity / M1-FR-17, M1-FR-16  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/org-identity/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

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

**Expected outcome**: A sign-in is returned asserting H, O, the authentication time, the class K, and an expiry.

**Scope**: happy-path · **Priority**: High  
**Source**: org-identity / M1-FR-19  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/org-identity/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

---

### TC-OI-004 — Once P is enrolled, sign-in needs K and P

**Context**: Core accepts K, or K + P; once a human enrolls P, sign-in needs both (M1-FR-17). This is the MFA support SECURITY-12 requires for the administrative first Admin.

**Scenario**: H, with P enrolled, signs in with K and P.

**Preconditions**:
- The organization level (org-gateway) is running with O configured
- H is `active` with K and P enrolled

**Steps**:
1. Call `authenticate` with H's identifier, K, and a valid P response

**Expected outcome**: A sign-in is returned asserting classes K and P.

**Scope**: happy-path · **Priority**: High  
**Source**: org-identity / M1-FR-17  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/org-identity/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

---

### TC-OI-005 — H renews their own sign-in

**Context**: Self-service includes renewing one's own sign-in (M1-FR-21).

**Scenario**: H renews a live sign-in.

**Preconditions**:
- The organization level (org-gateway) is running with O configured
- H holds a live sign-in

**Steps**:
1. Call `renewSignIn`, presenting the sign-in

**Expected outcome**: A renewed sign-in is returned for H, with a later expiry.

**Scope**: happy-path · **Priority**: Medium  
**Source**: org-identity / M1-FR-21  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/org-identity/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

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

**Expected outcome**: The end succeeds. The renewal is refused, because the sign-in is ended.

**Scope**: happy-path · **Priority**: High  
**Source**: org-identity / M1-FR-21  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/org-identity/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

---

### TC-OI-007 — H changes their own K by presenting the current K

**Context**: A human changes their own material by presenting the current material (M1-FR-21).

**Scenario**: H replaces K with K2.

**Preconditions**:
- The organization level (org-gateway) is running with O configured
- H is `active` with K

**Steps**:
1. Call `changeMaterial` with the current K and a new K2 meeting the policy
2. Authenticate with K
3. Authenticate with K2

**Expected outcome**: The change succeeds. Authentication with K is refused, and authentication with K2 succeeds.

**Scope**: happy-path · **Priority**: Medium  
**Source**: org-identity / M1-FR-21  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/org-identity/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

---

### TC-OI-008 — Where P is required, H enrolls P without a sign-in by presenting K

**Context**: M1-FR-17 says a human for whom P is required but not enrolled can enroll it without a sign-in, by presenting their current K. Without this, turning the requirement on locks out every human, the only Admin included.

**Scenario**: O's configuration requires P, and H has only K.

**Preconditions**:
- The organization level (org-gateway) is running with O configured
- O's configuration requires P
- H is `active` with K, and no P

**Steps**:
1. Call `changeMaterial` presenting K, with a new P enrollment
2. Call `authenticate` with K and P

**Expected outcome**: P is enrolled without any sign-in, and authentication with K and P then succeeds.

**Scope**: happy-path · **Priority**: High  
**Source**: org-identity / M1-FR-17  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/org-identity/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

---

### TC-OI-009 — Reused enrollment material is refused

**Context**: Enrollment material is single-use (M1-FR-17). Reuse would let whoever knew it, the deployer included, take over the principal.

**Scenario**: Someone presents H's enrollment material after H has activated.

**Preconditions**:
- The organization level (org-gateway) is running with O configured
- H has completed first authentication

**Steps**:
1. Call `firstAuthenticate` with H's identifier and the original enrollment material

**Expected outcome**: Refused. H's material and state are unchanged.

**Scope**: negative · **Priority**: High  
**Source**: org-identity / M1-FR-17  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/org-identity/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

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

**Expected outcome**: Refused, without revealing whether H exists or which factor failed. One failed attempt is recorded against H.

**Scope**: negative · **Priority**: High  
**Source**: org-identity / M1-FR-18  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/org-identity/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

---

### TC-OI-011 — Attempts beyond the bound are refused

**Context**: Attempt volume per principal is bounded (M1-FR-18). The bound's value and shape are set at NFR Requirements.

**Scenario**: Repeated wrong attempts against H exceed the bound.

**Preconditions**:
- The organization level (org-gateway) is running with O configured
- H is `active`
- The sign-in attempt bound is known from U2's NFR Requirements

**Steps**:
1. Make wrong-K attempts for H up to the bound
2. Make one more attempt with the correct K

**Expected outcome**: Once the bound is reached, further attempts are refused, as the bound's shape defines, even with the correct K. Each refusal is recorded.

**Scope**: negative · **Priority**: High  
**Source**: org-identity / M1-FR-18  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/org-identity/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

---

### TC-OI-012 — A K shorter than 8 characters is refused

**Context**: K must be at least 8 characters (M1-NFR-09, SECURITY-12).

**Scenario**: H tries to set a 7-character K at first authentication.

**Preconditions**:
- The organization level (org-gateway) is running with O configured
- H is `pending`

**Steps**:
1. Call `firstAuthenticate` with the enrollment material and a 7-character K

**Expected outcome**: Refused. H stays `pending`, and the enrollment material is not consumed.

**Scope**: negative · **Priority**: Medium  
**Source**: org-identity / M1-FR-17 (M1-NFR-09)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/org-identity/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

---

### TC-OI-013 — A K on a breached-secret list is refused

**Context**: K is checked against breached-secret lists (M1-NFR-09, SECURITY-12).

**Scenario**: H tries to set a K known to be breached.

**Preconditions**:
- The organization level (org-gateway) is running with O configured
- H is `active`

**Steps**:
1. Call `changeMaterial` with the current K and a new K taken from the breached list in use

**Expected outcome**: Refused. K is unchanged.

**Scope**: negative · **Priority**: Medium  
**Source**: org-identity / M1-FR-17 (M1-NFR-09)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/org-identity/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

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

**Expected outcome**: Refused, with an indication that a second factor must be enrolled. No sign-in is issued.

**Scope**: negative · **Priority**: High  
**Source**: org-identity / M1-FR-17  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/org-identity/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

---

### TC-OI-015 — Changing material without the current material is refused

**Context**: A change requires the current material (M1-FR-21). Otherwise anyone could replace a human's material.

**Scenario**: A caller tries to replace H's K without presenting it.

**Preconditions**:
- The organization level (org-gateway) is running with O configured
- H is `active`

**Steps**:
1. Call `changeMaterial` for H with a wrong current K and a new K

**Expected outcome**: Refused. K is unchanged, and the failure is recorded against H.

**Scope**: negative · **Priority**: High  
**Source**: org-identity / M1-FR-21  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/org-identity/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

---

### TC-OI-016 — K alone is refused once P is enrolled

**Context**: Once a human enrolls P, sign-in needs both K and P (M1-FR-17).

**Scenario**: H, with P enrolled, tries K alone.

**Preconditions**:
- The organization level (org-gateway) is running with O configured
- H has K and P enrolled

**Steps**:
1. Call `authenticate` with H's identifier and K only

**Expected outcome**: Refused. No sign-in is issued.

**Scope**: negative · **Priority**: High  
**Source**: org-identity / M1-FR-17  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/org-identity/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

---

### TC-OI-017 — Re-applying configuration does not re-register an existing first Admin

**Context**: Configuration registers the first Admin only if the principal does not exist (M1-FR-14). Reset is absent, so lost material is not recoverable by re-applying configuration (requirements, Absent from M1).

**Scenario**: The organization level restarts with the same configuration after H has activated.

**Preconditions**:
- H is `active` with K
- Configuration still names H as E's first Admin

**Steps**:
1. Restart the organization level
2. Inspect H's state and material
3. Try `firstAuthenticate` with the original enrollment material

**Expected outcome**: H is still `active` with K, no new enrollment material was issued, and the first-authentication attempt is refused.

**Scope**: edge-boundary · **Priority**: High  
**Source**: org-identity / M1-FR-14  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/org-identity/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

---

### TC-OI-018 — A principal's identifier is composed with its organization

**Context**: A human principal's identifier is unique within its organization and composed with it, never allocated globally (M1-FR-16).

**Scenario**: A reviewer inspects H's identifier.

**Preconditions**:
- The organization level (org-gateway) is running with O configured
- H exists

**Steps**:
1. Read H's identifier as returned in a sign-in's subject

**Expected outcome**: The identifier is composed with O, and is not a bare global identifier.

**Scope**: edge-boundary · **Priority**: Medium  
**Source**: org-identity / M1-FR-16  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/org-identity/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

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

**Expected outcome**: The sign-in asserts O, as configured. Nothing derives from the host name.

**Scope**: edge-boundary · **Priority**: High  
**Source**: org-identity / M1-FR-10, M1-FR-14  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/org-identity/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

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

**Expected outcome**: Refused. H must authenticate again.

**Scope**: edge-boundary · **Priority**: Medium  
**Source**: org-identity / M1-FR-19, M1-FR-21  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/org-identity/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

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

**Expected outcome**: A sign-in record shows H, the time, and the classes used. The material record shows K established at activation, by H.

**Scope**: edge-boundary · **Priority**: Medium  
**Source**: org-identity / M1-FR-12  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/org-identity/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

---

### TC-OI-022 — No operation deletes a human principal

**Context**: A human principal is never deleted or pruned (M1-FR-16). It is a resolution target for sponsor references.

**Scenario**: A reviewer inspects the organization-level contract.

**Preconditions**:
- `contract/org-gateway.openapi.yaml` after U2

**Steps**:
1. List every operation in the document

**Expected outcome**: No operation deletes or prunes a principal.

**Scope**: edge-boundary · **Priority**: Low  
**Source**: org-identity / M1-FR-16  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/org-identity/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

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

**Expected outcome**: Every one of the unit's operations is present and references the conventions. The violating request is rejected with the contract's error model before any processing.

**Scope**: happy-path · **Priority**: High  
**Source**: org-identity / M1-FR-02  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/org-identity/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

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

**Expected outcome**: Refused. No sign-in is issued.

**Scope**: negative · **Priority**: High  
**Source**: org-identity / M1-FR-09  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/org-identity/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

---

### TC-OI-025 — Material of a class core does not accept is rejected

**Context**: The identity-resolution boundary's human half accepts K and P only; class X (external subjects) is absent in M1 (M1-FR-13, M1-FR-17).

**Scenario**: A caller presents an external-subject assertion in place of K.

**Preconditions**:
- The organization level (org-gateway) is running with O configured
- H is `active`

**Steps**:
1. Call `authenticate` for H, presenting an external identity-provider assertion as the material

**Expected outcome**: Rejected as an unsupported material class. No sign-in is issued.

**Scope**: negative · **Priority**: Medium  
**Source**: org-identity / M1-FR-13  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/org-identity/`  
**Technical references**: `inception/application-design/component-methods.md`, `inception/application-design/unit-of-work.md`

---
