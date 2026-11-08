# Business Rules: U2 `org-identity`

**Unit**: U2 `org-identity` (soorma-core#5). Control face, organization level
**Built against**: ID @ `prd-identity-v1.0`, PF @ `prd-platform-foundations-v1.3`
**Amendment A5** (2026-11-08, at the QA construction enrichment, the user's): BR-K-07 gains the reason `context_word`; `reason` is an open enumeration (contract-change table, §10).
**Plan**: Q1 to Q12 answered 2026-11-08 (audit.md, *Functional Design: Answers Received*).
Every answer is classified technology (prd-gap-classification.md Step 1). **No
specification gap was found in U2.**
**Builds on**: U1's conventions (`contract/conventions/`; U1 business rules BR-CR, BR-ERR,
BR-ID, BR-VER), which apply unchanged unless a rule below says otherwise

---

## 1. Decisions

| # | Decision | Source |
|---|---|---|
| D-OI-01 | The principal identifier is the first Admin's configured value, under U1's human pattern (BR-ID-05). Compared exactly; ASCII-only in M1 | BR-ID-05, 08, 12 |
| D-OI-02 | `authenticate` on a `pending` principal, and `firstAuthenticate` on an `active` one, each fail with `authentication_failed` and count against the bound | ID FR-007; TC-OI-009 |
| D-OI-03 | Check order at S1: [business-logic-model.md §1](business-logic-model.md). The new K is checked **after** the presented material verifies. A refusal at any step leaves enrollment material unconsumed | BR-ERR-07; SECURITY-11 |
| D-OI-04 | Single use is atomic: two concurrent `firstAuthenticate` calls with the same enrollment material cannot both succeed | ID FR-007 |
| D-OI-05 | S1 accepts only the `signIn` scheme (`soorma_si_`), and only on `renewSignIn` and `endSignIn`. On those two, any other prefix, or the `Soorma-Delegation` header, is `credential_refused`. On the three operations naming no scheme, a presented header is `malformed_request` (D-OI-26) | BR-CR-01, 03, 06, 08; ID §8b |
| D-OI-06 | At S1 a sign-in passes O1, O2, and O3. O4 does not apply at the organization level; O11 is n/a (ID §8b) | ID §8b |
| D-OI-07 | No organization-level attribution record (ID FR-018 out). U2's attribution is its own records | M1-FR-12 |
| D-OI-08 | No operation deletes a principal, a material record, or a sign-in record | ID FR-001; TC-OI-022 |
| D-OI-09 | Organization identity comes only from configuration: never from the host, the request, or the deployment | ID FR-004; PF FR-022; I10 |
| D-OI-10 | Class X, and any material other than K, P, and enrollment material, has no field in the closed request bodies, so it is `malformed_request` | ID FR-006; FR-027 external types out |
| D-OI-11 | The identity-resolution seam's human half decides identity only (§12) | PF §12; ID §12 |
| **D-OI-12** | **Q1 A.** One configuration describes the tenancy tree, and each deployable reads its own part. **Enrollment material is supplied to the organization level only.** It applies **only when the principal does not exist**. For an existing principal, `pending` or `active`, it is ignored and never re-enrolls, so a redeploy cannot act as a reset. Start-up logs that it was ignored, without the material | ID FR-004, FR-007, §6 |
| **D-OI-13** | **Status codes for the new refusals: 403, not 401.** RFC 9110 §15.5.2 requires a 401 to carry a `WWW-Authenticate` challenge that applies to the target resource, and U1 (BR-ERR-06) makes that challenge `Bearer`. `firstAuthenticate`, `authenticate`, and `changeMaterial` accept **no** bearer credential (BR-CR-08 names none for them), so a `Bearer` challenge would tell the client to do something that cannot work. A 400 would say the request is malformed, which it is not. **403** fits: the request is understood, and refused. `authentication_failed`, `second_factor_enrollment_required`, and `second_factor_not_confirmed` are 403. They are told apart from `forbidden` (authority) by `code`. The sign-in-bearing operations keep U1's 401 codes, whose `Bearer` challenge is correct there | RFC 9110; BR-ERR-06; Q5 |
| **D-OI-14** | **Q2 A, Q6 A.** P is enrolled **only through `changeMaterial`**, in two steps (`beginSecondFactor`, `confirmSecondFactor`), presenting the current material. Never inside `firstAuthenticate`. The design is class-neutral: a P proof is an object discriminated by `type`; the one M1 type is chosen at NFR Requirements | M1-TECH-07; ID FR-006, FR-011 |
| **D-OI-15** | **Q3 A.** `changeMaterial` is authenticated by the **current material only**: K, plus a P proof once P is `active`. No sign-in | ID FR-011 |
| **D-OI-16** | **Q4 A.** **One attempt counter per presented principal reference, shared** by `authenticate`, `firstAuthenticate`, and `changeMaterial`. An unknown reference is counted and refused the same way, but no Failed Attempt record is written for it. **The bound limits rate and recovers with time. It never permanently locks a principal** | ID FR-008; BR-ERR-04 |
| **D-OI-17** | **Q7 A.** Renewal keeps the sign-in (id, `authenticatedAt`, `classes`) and issues a new token with a later expiry, **capped by an absolute maximum** from `authenticatedAt` | ID FR-009, FR-011; SECURITY-12 |
| **D-OI-18** | **Q8 A.** A change of K or P **ends every live sign-in** of that human | SECURITY-12 |
| **D-OI-19** | **Q9 A.** Enrollment material **does not expire** in M1. Single use is its only limit | ID FR-007 |
| **D-OI-20** | **Q10 A.** K is 8 to 256 Unicode code points **after NFKC normalization**; no control characters; no composition rules; checked against a breached-secret list. Normalized before the length check, hashing, and verification | M1-NFR-09; NIST SP 800-63B |
| **D-OI-21** | **Q11 A.** A human is always named as `{organization, principal}`, in requests and in the sign-in's subject | ID FR-001 |
| **D-OI-22** | **Q12 A.** The internal interface is on a separate listener. Every caller presents a configured per-environment credential, for every operation including verify-only material | I3; PF §11; ID FR-009 |
| D-OI-23 | Where P is required and not `active`, a successful `firstAuthenticate` returns **200** with `secondFactorEnrollmentRequired: true` and no `signIn`. It is a success, because K was set and H is `active`. A refusal code here would wrongly suggest nothing changed | D-OI-14; ID §10 |
| D-OI-24 | **No operation removes P in M1.** Replacing P (enrolling a new one while P is `active`) is supported. Removal is additive later | ID FR-011 ("change") |
| D-OI-25 | A begun P enrollment is a **Pending P Enrollment**, not a material record. Material exists only once possession is proven. At most one per principal; short-lived (value at NFR Requirements) | ID §7a |
| **D-OI-26** | *(Review round 1.)* **On an operation that names no security scheme, a presented `Authorization` or `Soorma-Delegation` header is `malformed_request` (400)**, with an `errors[]` entry naming the header. Not `credential_refused`: that is a 401, which must carry `WWW-Authenticate: Bearer` (BR-ERR-06), and no bearer credential can succeed on these operations (D-OI-13). The rule is stated for **every** operation naming no scheme, so U6's bootstrap inherits it. **It narrows U1's BR-CR-02 and BR-CR-06**, recorded as U1 amendment A4 | RFC 9110 §15.5.2; BR-CR-08 |
| **D-OI-27** | *(Review round 1.)* **Writing a Failed Attempt record is kept off the response path.** The counter update, which happens for every presented reference, stays on it. So whether the principal exists does not change response timing | BR-RF-03; SECURITY-11 |

---

## 2. Human Principal (BR-HP)

| ID | Rule | Source |
|---|---|---|
| BR-HP-01 | A principal is `{organization, principal}`. The identifier is unique within the organization and never allocated globally | ID FR-001; BR-ID-07 |
| BR-HP-02 | M1 states: `pending` and `active`. The only transition is `pending → active`, at first authentication. No M1 path reaches `suspended` or `deactivated` | ID FR-001, FR-003 out |
| BR-HP-03 | **Never deleted, never pruned.** No operation on any surface removes a principal | ID FR-001; I4 |
| BR-HP-04 | `registeredAt` and `registeredBy` (configuration, naming the environment) are set when the principal is registered, and never change | ID §7a |

## 3. Configuration and the First Admin (BR-CFG)

| ID | Rule | Source |
|---|---|---|
| BR-CFG-01 | Organization, project, and environment identity and membership come **only from configuration** | ID FR-004; PF FR-022; I10 |
| BR-CFG-02 | Each environment's part names its first Admin **by identifier only**. Enrollment material is referenced **only in the organization's part**, keyed by principal identifier. The environment part has no field for material, so it cannot carry any | ID FR-004, §6; D-OI-12 |
| BR-CFG-03 | At start-up, for each first Admin named by any environment: **if the principal does not exist**, its enrollment material must be configured, and the principal is registered `pending` with one class-K record in state `enrollment`. If no material is configured for it, the organization level refuses to start | ID FR-004, FR-007 |
| BR-CFG-04 | **If the principal exists, `pending` or `active`, any configured enrollment material for it is ignored**: nothing is re-registered or re-enrolled, and no state changes. Start-up logs that the material was ignored, naming the principal **by its log pseudonym** (NFR-OI-22, amended) and never the material | ID FR-004, FR-007; Q1 |
| BR-CFG-05 | Registration at start-up is idempotent and atomic: concurrent start-ups register a principal at most once. When several environments name the same principal, `registeredBy` names the first in the configuration's order | ID FR-004 |
| BR-CFG-06 | **Whether P is required** is a setting in the organization's part. No API sets it (ID FR-005 is out). It is read at start-up; a change takes effect at restart | ID FR-005, FR-006 |
| BR-CFG-07 | Configured enrollment material has U1's syntax (`soorma_em_`, at most 256 characters, BR-CR-07). Its generation and minimum entropy are Infrastructure Design's (M1-TECH-06) | BR-CR-07 |
| BR-CFG-08 | **Any configuration error stops start-up.** The organization level never runs on a partial or inferred configuration | SECURITY-15 |
| BR-CFG-09 | Enrollment material is held only in its one-way form once loaded. It is never written to a log, an error, or a record in any other form | M1-NFR-09; SECURITY-03 |

## 4. First Authentication (BR-FA)

| ID | Rule | Source |
|---|---|---|
| BR-FA-01 | `firstAuthenticate` succeeds only for a `pending` principal whose `enrollment` record verifies the presented enrollment material | ID FR-007 |
| BR-FA-02 | On success, **atomically**: the `enrollment` record becomes `active` with the human's own K (`establishedBy` = H); the principal becomes `active` with `activatedAt` | ID FR-007, §7a |
| BR-FA-03 | The enrollment material can never verify again (single use). Presenting it later is `authentication_failed` | ID FR-007; TC-OI-009, 017 |
| BR-FA-04 | The new K must meet BR-K. A policy refusal changes nothing, consumes nothing, and is not counted against the bound, because the presented material verified | M1-NFR-09; TC-OI-012 |
| BR-FA-05 | If P is not required: a sign-in is issued with `classes` `[K]`. If P is required: **no sign-in**, and the response says `secondFactorEnrollmentRequired: true` (D-OI-23) | ID §10; D-OI-14 |

## 5. K Policy (BR-K)

| ID | Rule | Source |
|---|---|---|
| BR-K-01 | K is a JSON string, normalized with **NFKC** before every check, hash, and verification | D-OI-20 |
| BR-K-02 | After normalization: **at least 8 and at most 256 code points**. The upper bound is checked on the normalized value. The schema's raw bound (1024) only stops oversized input early | M1-NFR-09; Q10 |
| BR-K-03 | No control characters (Unicode general category Cc) | D-OI-20 |
| BR-K-04 | **No composition rules.** No forced digits, symbols, or cases | NIST SP 800-63B |
| BR-K-05 | Every new K is checked against a **breached-secret list held locally**. Neither K nor any hash of it is sent outside the organization level | M1-NFR-09 |
| BR-K-06 | A new K may not equal the material it replaces: the enrollment material at first authentication, or the current K at `replaceSecret` | Defence in depth |
| BR-K-07 | A refused K is `secret_rejected` (400), with a pointer to the field and a `reason`: `too_short`, `too_long`, `disallowed_character`, `breached`, `reused`, or **`context_word`** (K contains the principal identifier, the organization identifier, or `soorma`; NFR-OI-14). *Amendment A5 (the user's, 2026-11-08, at the QA enrichment)*: `context_word` added. **`reason` is an open enumeration** in the contract (U1's shape, `anyOf: [{ enum: [...] }, { type: string }]`, NFR-WC-06): a client tolerates a reason it does not know. It is a validation error, returned only after the presented material verified | BR-ERR-01 |
| BR-K-08 | K is stored only in an adaptive one-way form that **takes the full normalized input**: no silent truncation, as bcrypt does at 72 bytes (carried to NFR Requirements) | M1-NFR-09; Q10 |

## 6. Second Factor (BR-P)

| ID | Rule | Source |
|---|---|---|
| BR-P-01 | Core accepts **K, or K + P**. Once P is `active`, every `authenticate` and every `changeMaterial` needs a valid P proof as well as K | ID FR-006 |
| BR-P-02 | Where the organization requires P and P is not `active`, `authenticate` with a verified K is refused with `second_factor_enrollment_required`. No sign-in is issued | ID FR-006, §10; Q5 |
| BR-P-03 | **A human with K and no P can always enroll P without a sign-in**, by presenting K to `changeMaterial` (`beginSecondFactor`, then `confirmSecondFactor`). So requiring P never locks a human out | M1-TECH-07 constraint 2 |
| BR-P-04 | `beginSecondFactor` creates a Pending P Enrollment and returns its `id`, `expiresAt`, and type-specific `setup`. It replaces any earlier pending enrollment. It changes no material and ends no sign-in | D-OI-25 |
| BR-P-05 | `confirmSecondFactor` succeeds only if the enrollment `id` names this principal's pending enrollment, it has not expired, and the `proof` verifies against it. Then, atomically: a new P record is `active` (`establishedBy` = H); any earlier `active` P is `retired`; the pending enrollment is removed; every live sign-in ends (BR-MC-04) | ID FR-011; D-OI-18 |
| BR-P-06 | A confirmation that fails after the current material verified is `second_factor_not_confirmed` (403). It names no cause, is not counted against the bound, and leaves the pending enrollment in place until it expires | D-OI-13 |
| BR-P-07 | A P proof presented where P is not `active` is `authentication_failed` | ID FR-006 |
| BR-P-08 | `authenticatorType` must be a type core accepts. In M1 that is the one type chosen at NFR Requirements. Anything else is `malformed_request` | Q6 A |
| BR-P-09 | Whether a P proof can be replayed within its validity is the authenticator type's rule, set at NFR Requirements, and enforced | SECURITY-12 |
| BR-P-10 | **`second_factor_enrollment_required` is returned only by `authenticate` and `renewSignIn`.** `firstAuthenticate` reports the requirement in its 200 (D-OI-23). `changeMaterial` never refuses because of the requirement, so it stays usable for enrolling P (BR-P-03) | ID §10; M1-TECH-07 |

## 7. Sign-In (BR-SI)

| ID | Rule | Source |
|---|---|---|
| BR-SI-01 | A sign-in is issued only to an `active` principal whose presented material verified **every class required** (BR-P-01, 02). Each successful `authenticate` creates one sign-in record. A human may hold several | ID FR-009 |
| BR-SI-02 | The token asserts the sign-in `id`, `subject`, `organization`, `authenticatedAt`, `classes`, and its expiry. **It asserts no environment, location, or code identity** | ID FR-009, §8b; I3 |
| BR-SI-03 | It is minted with the organization's minting material, which never leaves the organization level. Environments verify it with verify-only material | ID FR-009; PF §6 |
| BR-SI-04 | **Renewal** (D-OI-17): the sign-in must be `live` and its token unexpired. The new token's expiry is the earlier of *now + sign-in lifetime* and *`authenticatedAt` + absolute maximum*. `authenticatedAt` and `classes` are unchanged. Both values are NFR Requirements' | ID FR-009, FR-011 |
| BR-SI-05 | Renewal is refused with `second_factor_enrollment_required` if the organization requires P and the sign-in's `classes` lack P | ID FR-006 |
| BR-SI-06 | **Ending** sets `state` = `ended`, `endedAt`, and `endedBy` = `self`. It is the logout. Every token of that sign-in is refused afterwards (O3), at S1 and, through `signInStatus`, at E's issuance | ID FR-011; SECURITY-12 |
| BR-SI-07 | An expired token is `credential_expired`, returned only after it verifies (BR-ERR-02). An expired sign-in cannot be renewed; the human authenticates again | TC-OI-020 |
| BR-SI-08 | At the organization level the sign-in serves only `renewSignIn` and `endSignIn`. In environments it is accepted only at E's credential issuance (U4), and refused everywhere else by kind | ID FR-009; BR-CR-03 |

## 8. Material Change (BR-MC)

| ID | Rule | Source |
|---|---|---|
| BR-MC-01 | `changeMaterial` requires an `active` principal and the **current material**: K, plus a P proof once P is `active`. No sign-in (D-OI-15) | ID FR-011 |
| BR-MC-02 | A failed verification of the current material is `authentication_failed`, counted against the bound, and recorded as a Failed Attempt | ID FR-008; TC-OI-015 |
| BR-MC-03 | `replaceSecret`: the new K must meet BR-K. Then, atomically: the current K is `retired`, the new K is `active` (`establishedBy` = H), any pending P enrollment is removed, and every live sign-in ends | ID FR-011; D-OI-18 |
| BR-MC-04 | **A change of K or P ends every live sign-in** of the human: `endedBy` = `materialChange`. The response reports how many ended, and carries no sign-in | D-OI-18 |
| BR-MC-05 | Enrollment material is never accepted as current material | ID FR-007 |
| BR-MC-06 | No change acts on another human's material (ID FR-012 is out). The principal in the request is the one whose current material is verified | ID FR-011, FR-012 |

## 9. Abuse Bound (BR-AB)

| ID | Rule | Source |
|---|---|---|
| BR-AB-01 | **One counter per presented principal reference**, shared by `authenticate`, `firstAuthenticate`, and `changeMaterial` (D-OI-16) | ID FR-008 |
| BR-AB-02 | The bound is checked (`admit`) **before** any material is verified. A refusal is `too_many_attempts` (429, `Retry-After`), and the material is not checked | ID FR-008; BR-ERR-07 |
| BR-AB-03 | Every failed material verification counts. A K policy refusal, `second_factor_enrollment_required`, and `second_factor_not_confirmed` do not, because the presented material verified | ID FR-008 |
| BR-AB-04 | **The bound limits rate and recovers with time** (a window or a backoff). **It never locks a principal permanently**: M1 has one first Admin and no reset, so a lockout would let anyone who knows the identifier deny that Admin for good | Q4 |
| BR-AB-05 | Its shape and value, and **the counter store's size bound against unknown-identifier spraying**, are NFR Requirements' obligations | Q4 |
| BR-AB-06 | An unknown principal, or another organization, is bounded and refused **exactly like a known one** (BR-ERR-04), and is not recorded as a Failed Attempt | BR-ERR-04 |
| BR-AB-07 | Each refusal by the bound against an existing principal is recorded as a Failed Attempt with `refusedByBound` = true | TC-OI-011 |

## 10. Refusal and Disclosure (BR-RF)

| ID | Rule | Source |
|---|---|---|
| BR-RF-01 | **One code for every failure to authenticate**: `authentication_failed` (403). It covers an unknown principal, another organization, a wrong K, a wrong or missing P proof, a P proof where P is not `active`, a `pending` principal at `authenticate` or `changeMaterial`, an `active` principal at `firstAuthenticate`, and a used or wrong enrollment material. It never says which | ID FR-008; BR-ERR-01; TC-OI-010 |
| BR-RF-02 | `second_factor_enrollment_required` (403) is returned **only once K has verified** (BR-P-02, BR-SI-05). It is no oracle, because reaching it needs the right K | Q5 A |
| BR-RF-03 | **Timing does not disclose existence.** (a) For an unknown principal, the same one-way verification work is done against a decoy verifier, with the same algorithm and parameters. (b) The attempt counter is updated on the response path for **every** presented reference, known or not. (c) **The Failed Attempt record, written only for an existing principal, is written off the response path** (D-OI-27): the response never waits for it. The mechanism is NFR Design's | SECURITY-11 |
| BR-RF-04 | Validation errors (`malformed_request`, `secret_rejected`) name the field. `secret_rejected` is returned only after the presented material verified | BR-ERR-01 |
| BR-RF-05 | No response, log, or record carries K, a P proof or seed, enrollment material, or a token, in whole or in part. **No log carries a human principal identifier**: logs name a human by the log pseudonym (NFR-OI-22, amended at Infrastructure Design) | SECURITY-03, 09 |
| BR-RF-06 | On `firstAuthenticate`, `authenticate`, and `changeMaterial` (and any operation naming no security scheme), a presented `Authorization` or `Soorma-Delegation` header is `malformed_request` (400). Its `errors[]` entry carries `header` (the header's name) and a `detail`, and never the header's value. It is checked before the contract version and the abuse bound, and is not counted (D-OI-26) | D-OI-26; BR-ERR-01 |

### Contract changes U2 makes (Q5)

| Change | Where | Classification (BR-VER-05) |
|---|---|---|
| Add `authentication_failed`, 403: every failure to authenticate on `firstAuthenticate`, `authenticate`, `changeMaterial`. Disclosure: none | `conventions/errors.md`; `ProblemCode` | **Compatible**: the code set is open |
| Add `second_factor_enrollment_required`, 403: P required and not enrolled, after K verified (sign-in, renewal). Disclosure: that P must be enrolled | same | **Compatible** |
| Add `secret_rejected`, 400: a new K fails the policy, after the presented material verified. Disclosure: pointer and `reason` | same | **Compatible** |
| Add the optional Problem member **`reason`** (on `secret_rejected`), an **open enumeration**: `too_short`, `too_long`, `disallowed_character`, `breached`, `reused`, `context_word` (amendment A5). A later reason is compatible | `components.openapi.yaml` (`Problem`, a new `SecretRejectedReason`); `conventions/errors.md` | **Compatible**: an optional member of an open object; an open value set (BR-ENV-06's rule) |
| Add `second_factor_not_confirmed`, 403: a P confirmation fails after the current material verified. Disclosure: none | same | **Compatible** |
| `too_many_attempts`: *When* becomes "The abuse bound on bootstrap, sign-in, first authentication, or material change" | `conventions/errors.md` | **Compatible**: a wider *When* for an existing code |
| Disclosure section: the 403 refusals carry no `WWW-Authenticate` (D-OI-13) | `conventions/errors.md` | Compatible |
| **`malformed_request`**: *When* widens to "The body is not JSON, or fails the schema; **or the operation names no security scheme and an `Authorization` or `Soorma-Delegation` header is present**". Detail: `errors[]`, each with a JSON Pointer **or a header name** | `conventions/errors.md` | Compatible: a wider *When*, same status |
| **`ProblemFieldError`** gains an optional `header` (the request header's name). The `errors` description changes from "a JSON Pointer into the request body" to "a JSON Pointer into the body (`pointer`), or a request header (`header`)" | `components.openapi.yaml` | **Compatible**: an optional field on an open object |
| **U1 amendment A4**, `credential_refused`'s scope. *When* becomes "… on an operation that names a security scheme". `conventions/credentials.md` *Presentation* and *Reserved: delegation*: on an operation naming no scheme, an `Authorization` or `Soorma-Delegation` header is `malformed_request`. U1's BR-CR-02 and BR-CR-06 are narrowed to match | `conventions/errors.md`, `conventions/credentials.md`; U1 `business-rules.md` | **A change within unreleased 0.1.0**: `contract-v0.1.0` is not tagged, so no client depends on the earlier text. Released, moving a case between codes would be **breaking** (a changed meaning, BR-VER-05), which is why it is made now |
| New document `org-gateway.openapi.yaml`, with the five operations | `contract/` | **Compatible**: new operations |
| New shared definitions `HumanPrincipalReferenceInput`, `HumanPrincipalReference` | `components.openapi.yaml` | Compatible: additions |
| Each of the above | `contract/CHANGELOG.md`, under 0.1.0 (unreleased) | Recorded with its classification |

## 11. Internal Interface (BR-INT)

| ID | Rule | Source |
|---|---|---|
| BR-INT-01 | It runs on a **separate internal listener**. It is not part of the published contract and not reachable through S1's edge | PF §11; D-OI-22 |
| BR-INT-02 | **Every call presents the calling environment's configured credential**, verified with that environment's caller material. A call without one, or one that fails, is refused. **No caller is trusted because of its network location** | I3; D-OI-22 |
| BR-INT-03 | `verifyOnlyMaterial` returns only material that can verify sign-ins. Never minting material | ID FR-009; PF §6 |
| BR-INT-04 | `principalExists` answers yes or no, and nothing else: no state, no attributes | ID FR-017 is out; minimum disclosure |
| BR-INT-05 | `signInStatus` answers `live`, `ended`, or `unknown`, and nothing else | ID §8b O3 |
| BR-INT-06 | **No internal operation changes state** | Least privilege |
| BR-INT-07 | Each internal call is logged with the calling environment and the operation, never with a token | SECURITY-03 |
| BR-INT-08 | None of these is on a per-request path. U4 caches verify-only material, and calls `principalExists` and `signInStatus` from control operations only | ID FR-009; M1-NFR-08 |

## 12. Identity-Resolution Seam (BR-SEAM)

| ID | Rule | Source |
|---|---|---|
| BR-SEAM-01 | The human half of `seams/identity-resolution` takes a material type (K, P proof, enrollment material), a principal reference, and the material, and returns **a human principal reference, or a rejection** | PF §12 v1.3; ID FR-027 |
| BR-SEAM-02 | **It decides identity only.** The human record and its state, enrollment single use, the K policy, the P requirement, and sign-in issuance stay in P10, behind no seam | PF §12; ID §12 |
| BR-SEAM-03 | External types (class X) are absent. No interface is published and no configuration selection is offered | M1-FR-13 |

## 13. Records and Attribution (BR-REC)

| ID | Rule | Source |
|---|---|---|
| BR-REC-01 | Every authentication that issues a sign-in writes a sign-in record: subject, organization, `authenticatedAt`, classes, expiry, state | ID §7a; M1-FR-12 |
| BR-REC-02 | Every material established writes `establishedAt` and `establishedBy`; every retirement writes `retiredAt`. Configured enrollment material writes `enrolledAt` and `enrolledBy` = configuration | ID §7a; M1-FR-12 |
| BR-REC-03 | Every failed attempt against an existing principal writes a Failed Attempt record, off the response path (BR-RF-03) | ID FR-008 |
| BR-REC-04 | The actor of every U2 operation is recoverable as the human principal and the material or sign-in presented. A human has no origin mode | ID §7b *Recoverability* |
| BR-REC-05 | Writes are read-your-writes for the actor: a sign-in or change is visible to the human's next call | ID §10 |
| BR-REC-06 | The retention of Failed Attempt and expired sign-in records is NFR Requirements'. The principal record is never pruned | ID FR-001 |

---

## 14. Obligations Carried Forward

### To NFR Requirements (U2)

| Item | From |
|---|---|
| Sign-in lifetime, and the absolute maximum | BR-SI-04 |
| The abuse bound's shape and value, and the counter store's size bound against unknown-identifier spraying | BR-AB-04, 05 |
| The P authenticator type, its replay rule, and the Pending P Enrollment lifetime | BR-P-08, 09; D-OI-25 |
| The K hashing algorithm: adaptive, one-way, **taking the full normalized input** (no truncation) | BR-K-08 |
| The breached-secret list: its source, held locally | BR-K-05 |
| The org store, and retention of Failed Attempt and expired sign-in records | BR-REC-06 |
| The Failed Attempt write, off the response path: its durability (what a crash may lose) and the size bound of whatever holds it before writing | BR-RF-03; D-OI-27 |
| Highest durability for the principal record; interactive latency for sign-in | ID §10 |

### To Code Generation (U2): the contract changes, including U1 amendment A4

U2's Code Generation **applies amendment A4 to U1's published contract** (D-OI-26; U1
business-rules.md, *Amendment from U2*), alongside U2's own additions. The A4 part:

| Artifact | Change |
|---|---|
| `contract/conventions/errors.md` | The `credential_refused` row scoped to operations naming a security scheme; the `malformed_request` row's *When* and detail (a pointer **or a header name**); the check order (an unauthenticated surface runs step 1, refuses any `Authorization` or `Soorma-Delegation` header with `malformed_request`, then continues from step 5) |
| `contract/conventions/credentials.md` | *Presentation* and *Reserved: delegation*: on an operation naming no scheme, those headers are `malformed_request` |
| `contract/conventions/components.openapi.yaml` | `ProblemFieldError.header` (optional), and the `errors` description; then the regenerated types in `contract/generated/` (`pnpm run generate`; `check:generated` passes) |
| U1's tests | `contract/test/problem.test.ts` (TC-WC-024) and `contract/test/conventions.test.ts` (TC-WC-025), to the updated expected outcomes. Also the TC-WC-026 test in `conventions.test.ts`, if the `credentials.md` text it checks changes. TC-WC-026's expected outcome ("refused") is unchanged |
| `contract/CHANGELOG.md` | A4 recorded under 0.1.0 (unreleased), as a change within the unreleased version |

U2's own additions go with it: the four new codes (`authentication_failed`,
`second_factor_enrollment_required`, `secret_rejected`, `second_factor_not_confirmed`) and
the widened `too_many_attempts`; `org-gateway.openapi.yaml`; and
`HumanPrincipalReferenceInput` and `HumanPrincipalReference` (§10, *Contract changes U2
makes*).

### To NFR Design and Infrastructure Design (U2)

| Item | Stage |
|---|---|
| The sign-in token format; minting and verify-only material; rotation | NFR Design |
| The internal interface's caller credential (signed requests or mTLS) | NFR Design |
| How enrollment material reaches the organization level; its generation and entropy | Infrastructure Design (M1-TECH-06) |

### To later units (recorded on their issues when this stage is approved)

| To | Obligation |
|---|---|
| U4 `env-human-access` (#7) | ID FR-010: renewal "never outlives … its sign-in". **Whether ending a sign-in refuses the environment credentials issued from it** is U4's to classify through prd-gap-classification.md. `signInStatus` supports either reading |
| U4 (#7) | Build the internal-interface caller (BR-INT-02); apply the first grant; check O3 for the sign-in at E's issuance through `signInStatus`; call `principalExists` only after `grantToHuman`'s own authority check |
| U4 (#7) | **Fail closed** at E's issuance (and at any renewal that consults sign-in state): a `signInStatus` of **`unknown` refuses issuance**, as `ended` does; an **unreachable** internal interface refuses with **`unavailable`** (503, `Retry-After`). Never issue on a sign-in whose state could not be read (SECURITY-15; ID §8b O3) |
| U4 (#7) | Reuse `HumanPrincipalReferenceInput` and `HumanPrincipalReference` for grant targets |

---

## 15. Misuse Cases (SECURITY-11)

| Misuse | Rule that defeats it |
|---|---|
| The deployer keeps the enrollment material and activates H's principal first | Single use (BR-FA-03): H's own first authentication then fails, which is visible; the enrollment record shows when it became `active` |
| A redeploy with new enrollment material resets an existing principal | BR-CFG-04: ignored for any existing principal |
| An attacker guesses K for H at three surfaces to triple their budget | BR-AB-01: one shared counter |
| An attacker sprays wrong K at H to lock the only Admin out | BR-AB-04: the bound recovers with time and never locks permanently |
| An attacker probes which principals exist | BR-RF-01, 03; BR-AB-06: one code, equal timing, the same bound |
| An attacker sprays random identifiers to exhaust the counter store | BR-AB-05: a size bound, set at NFR Requirements |
| Someone with a stolen sign-in changes H's K | BR-MC-01: a change needs the current material, and a sign-in is not material |
| Someone who learned the old K keeps using sign-ins it produced | BR-MC-04: a change ends every live sign-in |
| A sign-in is replayed in an environment's data plane | BR-SI-02, 08: it asserts no environment and is refused by kind |
| A process inside the network calls `principalExists` to enumerate humans | BR-INT-02: a configured environment credential is required, never network location |
| Enrollment material leaks through an environment's configuration | BR-CFG-02: the environment part has no field for it |
| A secret or token leaks through logs or errors | BR-CFG-09; BR-RF-05 |
| An attacker learns whether a principal exists from how long a refusal takes, because a Failed Attempt is written only for an existing one | BR-RF-03: decoy verification, the counter for every reference, and the record written off the response path |
| **Someone who has H's K, or K + P, replaces K or enrolls their own P, and so takes the principal over** | **Not defeated in M1: accepted residual** (below) |

### Accepted Residual: compromise of K, or K + P, is unrecoverable in M1

**Whoever holds a human's current material is, to the platform, that human.** They can
replace K (BR-MC-03), or enroll their own P (BR-P-05), and every live sign-in of the real
human then ends (BR-MC-04). The real human can no longer authenticate.

**There is no recovery inside M1.** Recovery is a reset that issues new enrollment material
(ID FR-007, FR-012), and reset is out of M1. Configuration does not re-enroll an existing
principal (BR-CFG-04), deliberately, so that a redeploy cannot be used as a reset. **The
only remedy is re-creating the deployment.** This is the same delivery limit as a lost K or
P (requirements, *Absent from M1*).

**Accepted, not blocking**, because:
- it is a consequence of a recorded delivery decision (reset absent), not of a design
  choice in this unit, and it lands additively with ID FR-012
- the exposure is bounded by what protects the material: K's policy and breached-list check
  (BR-K), the abuse bound (BR-AB), P where enrolled (BR-P-01), and no material in logs or
  responses (BR-RF-05)
- requiring a live sign-in as well for a change would not close it: whoever has the
  material can authenticate first. And the P constraint (BR-P-03) requires a path with no
  sign-in

Carried into the Build and Test summary with the other delivery limits.
