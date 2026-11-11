# Components: soorma-core M1

**Built against**: PF @ `prd-platform-foundations-v1.3`, ID @ `prd-identity-v1.0`
**Design decisions** (Application Design plan, 2026-11-02):

| Decision | Choice |
|---|---|
| Q1 Topology | One deployment **per environment**, plus one **organization-level** deployment |
| Q2 Process split | **Separate deployables** per surface |
| Q3 Gateway | HTTP with JSON, **OpenAPI 3.1**, with JSON Schema 2020-12; a shared envelope schema |
| Q4 Event ingest | soorma-core's own ingest: publish over HTTP; subscribe over **Server-Sent Events**. The event surface is also defined in OpenAPI 3.1 (technology decision, recorded in the plan) |
| Q5 Layout | `contract/` and `seams/` under Apache 2.0; `packages/` and `services/` under FSL |

Business rules are not defined here; they belong to Functional Design, per unit.
Datastores, the internal broker, and libraries are chosen at NFR Requirements.

---

## Deployment Shape

```text
+---------------------------------------------------------------+
| Organization level (one per organization)                     |
|   org-gateway   (edge, control face, stateless)               |
|   org store     (principals, material, sign-ins, attempts)    |
|   org minting material for sign-ins (never leaves this level) |
+---------------------------------------------------------------+
        | verify-only material, principal lookup: to S2 only
        | (internal, cached, never per request)
        v
+---------------------------------------------------------------+
| Environment E (one deployment per environment; E2 the same)   |
|   control-gateway  (edge, control face, stateless)            |
|   data-gateway     (edge, data face, stateless)               |
|   event-ingest     (edge, data face, stateless)               |
|   env store        (registrations, grants, secrets,           |
|                     credentials, revocation, attribution)     |
|   env minting material (agent and human credentials)          |
|   env fan-out channel (internal; live delivery)               |
+---------------------------------------------------------------+
```

The local stack (M1-NFR-05) runs one organization level, plus environments **E** and
**E2**. *Done when* 6 needs both.

---

## Deployables (`services/`, FSL)

### S1 `org-gateway`: the organization level's edge

| | |
|---|---|
| **Level and face** | Organization; control |
| **Purpose** | The organization-level surface: authenticate, first authentication, sign-in, and self-service on one's own sign-in and material (ID FR-006 to FR-009, FR-011) |
| **Responsibilities** | Validates presented material by class (K, P), enrollment single use, and the sign-in abuse bound; issues, renews, and ends sign-ins; changes one's own K and P, including enrolling P by presenting K (M1-TECH-07); serves verify-only sign-in material to each environment's S2 (internal interface; S3 and S4 never call it) |
| **Holds** | Nothing in memory beyond request scope (M1-TECH-03). State lives in the org store |
| **Never** | Mints environment credentials. Reachable from any environment's per-request path |
| **M1-FRs** | 16, 17, 18, 19, 21 (sign-in half) |

### S2 `control-gateway`: environment E's control face

| | |
|---|---|
| **Level and face** | Environment; control |
| **Purpose** | Human operations in E: environment credential issuance, renewal, and end; grant to a human; registration of a logical agent; registration secret issuance |
| **Responsibilities** | Validates human credentials against O1 to O4 and O8 to O11 by kind. Refuses the organization sign-in everywhere except E's issuance (ID FR-009). Refuses agent credentials; no agent control operation exists in M1 (*Absent from M1*). Runs no envelope obligations, because direct human operations carry none |
| **M1-FRs** | 03, 04, 09, 12, 15, 20, 21 (credential half) |

### S3 `data-gateway`: environment E's synchronous data face

| | |
|---|---|
| **Level and face** | Environment; data |
| **Purpose** | The bootstrap exchange and agent credential renewal |
| **Responsibilities** | Bootstrap: verifies the registration secret through identity resolution, enforces the per-registration attempt bound, and mints a short-lived agent credential bound to the registration and E. Renewal: O1 to O3 on the presented credential, never weaker than issuance. **Neither call carries an envelope** (GAP-INT-008 work-around, option 1; soorma-prd#27). Refuses human credentials **by kind**, without verifying them |
| **No organization-level dependency** | S3 never calls the organization level, so an organization-level outage leaves bootstrap and renewal unaffected (M1-NFR-08) |
| **M1-FRs** | 05, 06, 07, 09 |

### S4 `event-ingest`: environment E's asynchronous data face

| | |
|---|---|
| **Level and face** | Environment; data |
| **Purpose** | Publish to and subscribe on E's namespace, and deliver to live subscribers |
| **Responsibilities** | Discharges O1 to O12 itself (O10) on every publish and subscribe: credential, revocation, environment match, envelope validation and stamping, origin, chain, and authority. Refuses every human credential **by kind**, without verifying it. Fans out within E only, to live SSE streams. Ends a subscriber's stream within the propagation bound once its credential expires or is revoked (T-2). No durability, ordering, or redelivery (GAP-INT-003) |
| **Holds** | Open SSE connections are per instance. Fan-out across instances uses the internal environment channel |
| **No organization-level dependency** | S4 never calls the organization level, so an organization-level outage leaves publish, subscribe, and delivery unaffected (M1-NFR-08) |
| **M1-FRs** | 01, 08, 09, 11 |

**One process per deployable, each stateless and independently scaled** (Q2 A;
M1-TECH-03). The deployables share code from `packages/`, but none treats another's
traffic as pre-validated. Each runs its own perimeter checks (O10).

---

## Internal Modules (`packages/`, FSL)

Linked into the deployables as libraries. **Not edge-reachable**, which places them as
internal per PF §11.

| # | Module | Used by | Responsibility | M1-FRs |
|---|---|---|---|---|
| P1 | `perimeter` | S1 to S4 | Obligation checks as guards, applied **per deployable**: O1 to O12 for agent traffic, and the human-credential table (ID §8b), together with the presenter × entry-point matrix (ID FR-023). Each deployable selects the checks for its surface | 09 |
| P2 | `envelope` | S4 | Validates drafts (client contract version; trace context well-formed, W3C); **rejects** any platform-stamped field, origin mode included (GAP-INT-007); stamps scope, origin, chain, and the re-broadening record; enforces `maxChainDepth`; preserves unknown fields. S3 carries no envelope (GAP-INT-008 work-around, option 1) | 01 |
| P3 | `authority` | S2, S4 | **Effective authority, computed in exactly one place**: the intersection; origin stamping (autonomous from the registration, propagated from inbound, O12); re-broadening (the PF §8b composition; load-bearing only; local to its hop); direct human operations evaluated against the human's grants in E. It calls the policy-decision boundary for **containment only** | 03, 08 |
| P4 | `registry` | S2, S3, S4 | Logical agent registrations (all eight attributes), standing sets, ceiling snapshots (the held set), grants (*granted-by*: principal or configuration), registration secrets (issuer), and the **accepted-identifier set** (GAP-INT-006) | 03, 04, 15 |
| P5 | `credentials` | S2, S3, S4 | Mints and verifies agent credentials and human environment credentials **with E's own material** (never shared); reads revocation state on every request through a cache bounded by the propagation bound, **failing closed** past it; records ends (self-service) | 05, 06, 07, 20, 21 |
| P6 | `identity-resolution` | S1, S3 | Implements the identity-resolution seam: the registration secret, returning an agent registration reference; K and P at the organization level, returning a human principal reference. It decides identity, never authority | 05, 13, 17 |
| P7 | `attribution` | S2, S4 | Writes attribution records: scope, actor, chain, and origin, with a human actor named directly and no origin mode; self-grants and configuration grants marked | 12 |
| P8 | `abuse-bound` | S1, S3 | Records failed attempts against the registration (bootstrap) or the principal (sign-in, first authentication) and enforces the bound. Its value and shape are set at NFR Requirements | 05, 18 |
| P9 | `config` | S1 to S4 | Loads the configured organization, project, and environment identity and membership, and each environment's first Admin with enrollment material (M1-TECH-06). Never infers identity from the host | 10, 14 |
| P10 | `org-identity` | S1 | Human principals (`pending`, `active`; never pruned), material (K and P; enrollment; X absent), sign-ins, verify-only material publication, and the principal lookup environments use | 16, 17, 19 |
| P11 | `policy-decision` | P3 | Implements the policy-decision seam over the minimal model: flat opaque identifiers, set semantics, deny by default. **It answers containment, never composition** | 13, 08 |

*Corrected at U4 NFR Design (2026-11-11, plan Q2 A and Q4 A).* Two internal packages are added
beside P1 to P11. **`service-kit`** holds the organization-neutral runtime that S1 and S2 share:
- secret types;
- sign-in verification (minting stays in P10);
- the internal-call signer and verifier;
- key thumbprints;
- the log pseudonym;
- the clock;
- the semaphore;
- the migration runner and pool settings;
- problem documents;
- the HTTP plumbing.

It is moved out of P10 and S1, so **S2 never links P10**. **`env-store`** owns the environment
store: its one migration sequence, its pool, and the transaction handle P4, P5, and P7 write
through, so one operation's writes share one transaction. U5 and U6 add their tables to it. The
env store is PostgreSQL 18, one instance per environment. See
`construction/env-human-access/nfr-design/logical-components.md` (§2, §3) and
`nfr-design-patterns.md` (NP-EHA-06, 15).

---

## Seam Interfaces (`seams/`, Apache 2.0, unpublished in M1)

Type definitions only (Q5 X; PF §22). **Not published, and no configuration selection
offered** (M1-FR-13). The implementations are P6 and P11.

| Seam | Interface | M1 returns | Absent |
|---|---|---|---|
| **Policy decision** (PF §12) | Is a required permission contained in this set? | Contained, or not | Any richer model (Access Policy) |
| **Identity resolution** (PF §12 v1.3) | Verify authentication material of a declared type | An agent registration reference, a human principal reference, or a rejection | Verified external subjects and the class-X binding (ID FR-027 external types) |

**Containment, which no seam decides** (PF §12; ID §12):
- the intersection
- origin stamping
- chain append and `maxChainDepth`
- the sponsorship ceiling check
- what a credential asserts
- the human record and lifecycle
- grant creation
- enrollment single use
- per-environment issuance and verify-only material
- the human-only class

All of these stay in P2 to P5, P10, and P4, outside both seams.

*Corrected at U3 Functional Design (2026-11-10, plan Q2 and Q3): the policy-decision seam has
**both** halves PF §12 states, `grantedSet(principal, environment)` and `contains(effectiveSet,
requiredSet)`; composition stays in P3. The human-only class is **defined in P3**
(`packages/authority`) and used by P4's registration check. See
`construction/authority-evaluation/functional-design/business-rules.md` (D-AE-02, D-AE-03).*

*Corrected at U5 Functional Design (2026-11-11): the human-only check and the sponsor ceiling
are **P3's**, over the seam, not P4's: P4's registration write compares no permission sets. The
registration is also the agent's grant (PF §7a, agent-principal form); P4's grants stay
human-only. See `construction/agent-registration/functional-design/business-rules.md` (D-AR-06,
D-AR-07, D-AR-10).*

---

## Contract (`contract/`, Apache 2.0)

| Artifact | Content |
|---|---|
| `envelope.schema.json` | JSON Schema 2020-12 for the envelope and the draft: seven fields, the stamped/asserted partition, client contract version, and unknown-field preservation (PF §7b) |
| `delivery.schema.json` | **`Delivery`**: the stamped envelope (referencing `envelope.schema.json`) and the opaque payload. It is the named schema of each event on the subscribe stream. OpenAPI 3.1 types an SSE response only as `text/event-stream`, so the subscribe operation **references `Delivery` by name**, and soorma-sdk generates a type for each delivered event |
| `org-gateway.openapi.yaml` | Organization-level operations (S1) |
| `control-gateway.openapi.yaml` | Environment control operations (S2) |
| `data-gateway.openapi.yaml` | Bootstrap and renewal (S3). No envelope on either (GAP-INT-008 work-around) |
| `event-ingest.openapi.yaml` | Publish (HTTP) and subscribe (S4). The SSE response is `text/event-stream`, and each event's data is a `Delivery` (referenced by name) |
| Generated TypeScript types | Generated from the above; never hand-written, and never shared by hand with soorma-sdk (M1-TECH-02) |

**Status**: **pre-release** (GAP-INT-003). It states that delivery semantics are
unspecified, that the accepted permission set may widen (GAP-INT-006), and that
delegation-credential presentation can be added without a breaking change (A-4).
**Publication runs in two steps** (execution plan): the design when soorma-core#2
merges, and the schema at a tag on `main` after Code Generation.

---

## Stores (logical; technology at NFR Requirements)

| Store | Level | Holds | Never |
|---|---|---|---|
| Org store | Organization | Principals, authentication material (K in a verify-only form), sign-ins, failed sign-in attempts | Any environment's grants or credentials |
| Org minting material | Organization | Signs sign-ins | Leaves the organization level. Environments get verify-only material |
| Env store | Environment | Registrations, grants, secret verification material, credential records, revocation state, attribution records, failed bootstrap attempts | Any other environment's records (I1, structurally: one store per deployment, Q1 A) |
| Env minting material | Environment | Signs agent and human environment credentials for this environment only | Shared with any other environment (PF §6 v1.3) |
| Env fan-out channel | Environment | Live events in transit between ingest instances | Durability, or crossing environments |
