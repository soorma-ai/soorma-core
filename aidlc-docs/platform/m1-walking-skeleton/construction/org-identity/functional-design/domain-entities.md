# Domain Entities: U2 `org-identity`

**Unit**: U2 `org-identity` (soorma-core#5). Control face, organization level
**Built against**: ID @ `prd-identity-v1.0`, PF @ `prd-platform-foundations-v1.3`
**Companions**: [business-rules.md](business-rules.md) (rules BR-* and decisions D-OI-01 to
D-OI-27), [business-logic-model.md](business-logic-model.md),
[l1-coverage-matrix.md](l1-coverage-matrix.md),
[invariant-coverage-matrix.md](invariant-coverage-matrix.md)

U2 owns the **first records soorma-core stores**. All of them are **organization-scoped**
(ID §6) and live in the org store. No environment holds any of them. Field names are
camelCase, as in U1 (D-WC-01). Storage technology is NFR Requirements'.

---

## Entity Map

| Entity | Kind | Keyed on | Stored | Lifecycle | Source |
|---|---|---|---|---|---|
| Human Principal | record | organization | org store | `pending → active` in M1. **Never deleted or pruned** | ID FR-001, §7a |
| Human Authentication Material | record | organization (through the principal) | org store | `enrollment → active → retired` | ID FR-006, FR-007, §7a |
| Pending P Enrollment | transient | principal | org store | created → confirmed / replaced / expired | D-OI-25 |
| Organization Sign-In | record and credential | organization | org store; the token is held by the human | `live → ended`; expiry is a time | ID FR-009, §7a |
| Failed Attempt | record | principal | org store | — | ID FR-008; M1-FR-12 |
| Attempt Counter | transient | presented identifier | org store | recovers with time | ID FR-008; D-OI-16 |
| Organization Minting Material | key material | organization | organization level only | never leaves it | ID FR-009; PF §6 |
| Verify-Only Material | key material | organization | served to each environment's S2 | — | ID FR-009; PF §6 |
| Tenancy Configuration | configuration | the deployment | each deployable reads its own part | read at start-up | ID FR-004; D-OI-12 |
| Environment Caller Material | configuration | environment | organization level (verify-only) | read at start-up | D-OI-22 |
| Human Principal Reference | value | — | — | — | ID FR-001; D-OI-21 |

**Not U2's** (ID §7a records with no U2 part): Human Environment Credential (U4), Delegation
Credential (ID FR-019 out), Organization-Level Attribution (ID FR-018 out), Configured
Identity Source (ID FR-024 out), Grant Mapping (ID FR-025 out). Grants, the first grant
included, are environment records (U4).

---

## Human Principal Reference

How a human is named everywhere: **always composed with its organization** (ID FR-001;
D-OI-21). The same shape as U1's `DelegatingPrincipalReference`.

| Field | Request side (closed) | Response side (open) |
|---|---|---|
| `organization` | `ConfiguredIdentifier` (strict, 1 to 64) | plain string (BR-ID-11) |
| `principal` | `HumanPrincipalIdentifier` (the human pattern, 1 to 256, ASCII-only) | plain string |

Two references are equal only when both parts are equal, compared exactly (BR-ID-08). A
person in two organizations is two principals.

## Human Principal

| Attribute | Type | Required | Set by | Note |
|---|---|---|---|---|
| `organization` | configured identifier | Yes | Configuration | The organization this level serves |
| `principal` | human principal identifier | Yes | Configuration (first Admin) | Unique within the organization; **never allocated globally** |
| `state` | `pending` \| `active` | Yes | Platform | `suspended` and `deactivated` exist in ID FR-001 but no M1 path reaches them (ID FR-003 out) |
| `registeredAt` | time | Yes | Platform | RFC 3339 UTC |
| `registeredBy` | `{ kind: "configuration", environment }` | Yes | Platform | The environment whose configuration named the first Admin. When several do, the first in the configuration's order (BR-CFG-05) |
| `activatedAt` | time | When `active` | Platform | Set at first authentication |

**Never deleted, never pruned** (ID FR-001): it is a resolution target for sponsor
references (PF FR-013). No operation in any surface removes it.

## Human Authentication Material

One record per material value. The record holds **class, state, and who established it**
(ID §7a). Only the organization level holds or verifies it (ID FR-006, §6).

| Attribute | Type | Required | Note |
|---|---|---|---|
| `id` | platform reference | Yes | |
| `principal` | Human Principal Reference | Yes | |
| `class` | `K` \| `P` | Yes | `X` is absent in M1 (ID FR-027 external types out). An enrollment material is class `K` |
| `state` | `enrollment` \| `active` \| `retired` | Yes | |
| `authenticatorType` | string | When `class` is `P` | The P type (Q6 A: chosen at NFR Requirements) |
| `enrolledAt`, `enrolledBy` | time; `configuration` | Only for configured enrollment material | When and by whom the enrollment material was set |
| `establishedAt`, `establishedBy` | time; Human Principal Reference | When `active` or `retired` | When the human established their own material, and that it was them (TC-OI-021) |
| `retiredAt` | time | When `retired` | |
| `verifier` | opaque | While not `retired` | **K**: an adaptive one-way form of the NFKC-normalized K only (M1-NFR-09; D-OI-20). **P**: what the authenticator type needs to verify a proof. **Destroyed on retirement**; the record's other attributes stay |

**States** (ID §7a: `enrollment → active → retired`):

| Transition | When | Effect |
|---|---|---|
| (none) → `enrollment` | Start-up, for a configured first Admin who does not exist | Class K. `verifier` = the one-way form of the configured enrollment material. `enrolledBy` = configuration |
| `enrollment` → `active` | First authentication | The **same record**: its `verifier` becomes the one-way form of H's own K; `establishedAt` and `establishedBy` = now and H. The enrollment value can never verify again (single use, ID FR-007) |
| (none) → `active` | A confirmed P enrollment, or a new K | A new record, established by H |
| `active` → `retired` | The human replaces that material | `verifier` destroyed; `retiredAt` set |

**Invariant per principal**: at most one record of each class is in `enrollment` or `active`
state at a time.

## Pending P Enrollment

The first step of enrolling P (D-OI-14, D-OI-25). **Not a material record**: no material
exists until possession is proven.

| Attribute | Type | Note |
|---|---|---|
| `id` | platform reference | Returned to the human; confirms the right enrollment |
| `principal` | Human Principal Reference | |
| `authenticatorType` | string | |
| `setupState` | opaque | What the server needs to check the confirming proof |
| `expiresAt` | time | Short; the value is NFR Requirements' |

At most one per principal. A new begin replaces it. Confirmation, expiry, or a material
change removes it.

## Organization Sign-In

A record, and the credential that refers to it (ID FR-009, §7a).

| Attribute | Type | Required | Note |
|---|---|---|---|
| `id` | platform reference | Yes | |
| `subject` | Human Principal Reference | Yes | A configured source can be a subject in ID; absent in M1 |
| `organization` | configured identifier | Yes | From configuration (D-OI-09) |
| `authenticatedAt` | time | Yes | Kept unchanged by renewal (D-OI-17) |
| `classes` | list of `K`, `P` | Yes | The classes verified at authentication |
| `expiresAt` | time | Yes | The latest token's expiry. Never later than `authenticatedAt` + the absolute maximum |
| `state` | `live` \| `ended` | Yes | |
| `endedAt` | time | When `ended` | |
| `endedBy` | `self` \| `materialChange` | When `ended` | The logout, or a material change (D-OI-18) |

**The sign-in token** (`soorma_si_…`, U1 BR-CR-03) asserts, verifiably with verify-only
material: the sign-in `id`, `subject`, `organization`, `authenticatedAt`, `classes`, and its
own expiry. **It asserts no environment and no location** (ID §8b *What a credential
asserts*). Its format is NFR Design's, within U1's syntax (BR-CR-05). Several tokens can
refer to one sign-in, one per renewal. Each stays valid until its own expiry unless the
sign-in is ended.

## Failed Attempt

| Attribute | Type | Note |
|---|---|---|
| `principal` | Human Principal Reference | Written **only when the principal exists** (D-OI-16) |
| `surface` | `authenticate` \| `firstAuthenticate` \| `changeMaterial` | |
| `at` | time | |
| `refusedByBound` | boolean | True when the bound refused it before any material was checked |

What was presented is **never** recorded: no K, P proof, or enrollment material, nor any
fragment of them.

## Attempt Counter

The state behind the per-principal bound (D-OI-16). Keyed on the **presented** reference,
so an identifier that names no principal is bounded the same way (BR-ERR-04). It limits
rate and **recovers with time**. It never locks a principal permanently. Its shape, value,
and the store's size bound are NFR Requirements' (BR-AB-05).

## Key Material

| Entity | Holds | Never |
|---|---|---|
| Organization Minting Material | Signs sign-in tokens | Leaves the organization level |
| Verify-Only Material | Verifies sign-in tokens: a set of keys, each with an identifier the token names | Can mint |
| Environment Caller Material | Per configured environment: what verifies that environment's calls to the internal interface (verify-only) | Lets the organization level act as an environment |

Algorithms, formats, and rotation are NFR Design's.

## Tenancy Configuration

One configuration describes the tenancy tree (D-OI-12). Each deployable reads its own part.

| Part | Read by | Holds |
|---|---|---|
| Organization | Organization level | Organization identity; projects and environments, and their membership; **whether P is required** (ID FR-005 by configuration); per first Admin identifier, a **reference to its enrollment material**; each environment's caller material (verify-only) |
| Environment | That environment's deployables | Its own identity, its project and organization, and its **first Admin's identifier only** (U4 applies the first grant) |

**Enrollment material is never in an environment's part** (ID §6). How the material reaches
the organization level is Infrastructure Design's (M1-TECH-06); it is never in source or IaC
(M1-NFR-09).

---

## Wire Shapes: `contract/org-gateway.openapi.yaml`

**One organization per org-gateway**, so paths carry no organization. JSON bodies, closed
on the request side (U1 *Adding an Operation*). **No operation carries an envelope**: they
are direct human operations (PF FR-001 v1.3; ID FR-022). Every request sends
`Soorma-Contract-Version` (BR-VER-02). Paths are proposed here and finalized at Code
Generation.

| Operation | Method and path | Security scheme | Request body | Success |
|---|---|---|---|---|
| `firstAuthenticate` | `POST /first-authentication` | none | `principal` (reference); `enrollmentMaterial` (`soorma_em_…`, at most 256); `newSecret` (K) | 200: `principal`, `state: active`, and either `signIn` or `secondFactorEnrollmentRequired: true` (D-OI-23) |
| `authenticate` | `POST /sign-ins` | none | `principal`; `secret` (K); `secondFactor` (P proof), where enrolled | 200: `signIn` |
| `renewSignIn` | `POST /sign-ins/current/renewal` | `signIn` | none | 200: `signIn` |
| `endSignIn` | `POST /sign-ins/current/end` | `signIn` | none | 204 |
| `changeMaterial` | `POST /material-changes` | none | `principal`; `current` (`secret`, and `secondFactor` once P is enrolled); `change` (below) | 200: by change type (below) |

**`signIn`** in a response: `{ token, expiresAt, subject, authenticatedAt, classes }`. The
token is opaque to clients; the other fields repeat what it asserts, for convenience.

**`change`**, discriminated by `type` (an open set on the response side; closed on the
request side):

| `type` | Fields | Success body |
|---|---|---|
| `replaceSecret` | `newSecret` | `{ type, retired: [classes], signInsEnded: n }` |
| `beginSecondFactor` | `authenticatorType` | `{ type, enrollment: { id, expiresAt, setup } }`. `setup` is type-specific |
| `confirmSecondFactor` | `enrollment` (id); `proof` | `{ type, retired: [classes], signInsEnded: n }` |

**P proof** (`secondFactor`, `proof`): `{ type, … }`, with the fields the authenticator type
defines (Q6 A). The M1 type and its fields are set at NFR Requirements. A later type is an
additive change (ID §7b).

**K** (`secret`, `newSecret`): a JSON string, 8 to 256 code points **after NFKC
normalization** (D-OI-20). The schema bounds the raw string at 1024 code points, so that
oversized input fails early. That is wider than 256 because NFKC can shorten a string, as
when combining sequences compose. The policy itself is checked after normalization
(BR-K-02).

New shared definitions in `components.openapi.yaml`: `HumanPrincipalReferenceInput` (request,
closed, patterned) and `HumanPrincipalReference` (received, open, plain strings). U4 reuses
both.

## Internal Interface (organization level → environments; not published)

Served on a **separate internal listener**, never through S1's edge (D-OI-22; PF §11). Every
call presents the calling environment's configured credential; the mechanism is NFR Design's.

| Operation | Input | Output | Used by |
|---|---|---|---|
| `verifyOnlyMaterial` | — | The current set of verify-only keys, with identifiers | U4 S2, cached; never per request |
| `principalExists` | Human Principal Reference | yes or no | U4 `grantToHuman` |
| `signInStatus` | sign-in id | `live`, `ended`, or `unknown` | U4: O3 for the sign-in at E's issuance |
