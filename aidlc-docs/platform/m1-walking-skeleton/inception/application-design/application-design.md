# Application Design: soorma-core M1 Walking Skeleton

**Built against**: PF @ `prd-platform-foundations-v1.3`, ID @ `prd-identity-v1.0`
**Depth**: comprehensive
**Consolidates**:
- [components.md](components.md)
- [component-methods.md](component-methods.md)
- [services.md](services.md)
- [component-dependency.md](component-dependency.md)

Those four documents hold the detail. This one is the single read.

---

## 1. Decisions

| # | Decision | Choice | Why |
|---|---|---|---|
| Q1 | Environment topology | **One deployment per environment** plus one organization-level deployment | Isolation is structural (I1); matches PF §6 *Deployment Note*; the local stack runs the organization level, E, and E2 |
| Q2 | Process split | **Separate stateless deployables**: `org-gateway`, and per environment `control-gateway`, `data-gateway`, and `event-ingest` | M1-NFR-03 and O10 hold by construction; M1-TECH-03 |
| Q3 | Gateway protocol | **HTTP with JSON, OpenAPI 3.1** (JSON Schema 2020-12), with a shared envelope schema | Raw calls with only an HTTP client (PF FR-023); M1-TECH-02 |
| Q4 | Event ingest | **Own ingest**: publish over HTTP, subscribe over **SSE** | A smaller one-way surface. In-band renewal can be added later; reconnect overlap is Functional Design's (user's note). Exposing a broker directly was rejected because it cannot discharge O5 to O12 (I2) |
| — | Event surface schema | **OpenAPI 3.1** (not AsyncAPI) | Follows from Q4 B: SSE is plain HTTP, so one schema language serves every surface. A technology decision (I11), open to override |
| Q5 | Layout and licence | `contract/` under Apache 2.0, published; `seams/` under Apache 2.0, interface types only, **unpublished in M1**; `packages/` and `services/` under FSL | PF §22; M1-FR-13 (user's Q5 X) |

**Publication, in two steps** (execution plan): the **design** when soorma-core#2 merges,
which lets soorma-sdk run its Inception; the **schema** at a tag on `main` after Code
Generation, which soorma-sdk's Construction pins.

---

## 2. Components

| | Component | Kind | Responsibility (summary) |
|---|---|---|---|
| S1 | `org-gateway` | Deployable, organization, control | Authenticate, first authentication, sign-in, self-service on one's own sign-in and material; serves verify-only material |
| S2 | `control-gateway` | Deployable, environment, control | Environment credential issuance, renewal, and end; grant to a human; register an agent; issue a secret. Human credentials only |
| S3 | `data-gateway` | Deployable, environment, data | Bootstrap and renewal. The envelope question is pending GAP-INT-008 |
| S4 | `event-ingest` | Deployable, environment, data | Publish, and subscribe over SSE; O1 to O12; live fan-out within E |
| P1 to P11 | Internal modules | Libraries, FSL | perimeter, envelope, authority, registry, credentials, identity-resolution, attribution, abuse-bound, config, org-identity, policy-decision |
| — | `seams/` | Apache 2.0, unpublished | Policy-decision and identity-resolution interface types |
| — | `contract/` | Apache 2.0, published | `envelope.schema.json` and four OpenAPI documents; generated types |
| — | Stores | Logical | Org store and minting material; per environment: env store, minting material, fan-out channel |

---

## 3. Interfaces

**Edge**: 15 operations across the four deployables ([component-methods.md §1](component-methods.md)):
- S1: `firstAuthenticate`, `authenticate`, `renewSignIn`, `endSignIn`, `changeMaterial`
- S2: `issueEnvironmentCredential`, `renewEnvironmentCredential`,
  `endEnvironmentCredential`, `grantToHuman`, `registerAgent`, `issueRegistrationSecret`
- S3: `exchangeBootstrap`, `renewAgentCredential`
- S4: `publish`, `subscribe`

**Internal**: [component-methods.md §2](component-methods.md). The interfaces that carry
invariants:
- `authority.evaluateAgent` and `evaluateHuman`: **the only place** effective authority
  is computed (I5)
- `authority.resolveOrigin`: O12
- `envelope.validateDraft`: rejects stamped fields, origin mode included (GAP-INT-007)
- `credentials.isRevoked`: fails closed past the bound
- `registry.createRegistration`: the ceiling, the human-only class, declaration ⊆
  standing, accepted identifiers

---

## 4. Orchestration and Dependencies

Each journey step US-01 to US-12 is traced through services and modules in
[services.md](services.md). The dependency matrix and the data flow are in
[component-dependency.md](component-dependency.md). In summary:
- each deployable runs its own perimeter checks; shared code, no shared trust (O10)
- environments reach the organization level only for cached verify-only material and,
  from S2, a principal lookup; neither is on a per-request path (ID FR-009)
- **nothing flows between environments**

---

## 5. Requirement → Component Traceability

| M1-FR | Home | Also |
|---|---|---|
| 01 Envelope | P2 | S4, S3 (GAP-INT-008), `contract/` |
| 02 Wire contract | `contract/` | S1 to S4 |
| 03 Registration | P4, P3 | S2 |
| 04 Secret issuance | P4 | S2 |
| 05 Bootstrap | S3 | P6, P8, P5 |
| 06 Renewal | S3 | P5 |
| 07 Revocation read | P5 | S2, S3, S4 |
| 08 Authority | P3 | P11, S2, S4 |
| 09 Perimeter | P1 | S1 to S4 |
| 10 Tenancy | Topology (Q1); P9 | P5 (per-environment material) |
| 11 Publish and subscribe | S4 | Fan-out channel |
| 12 Attribution | P7 | S2, S4 |
| 13 Seams | `seams/`; P6, P11 | — |
| 14 Configured tenancy and first Admin | P9 | P10 (`ensureFirstAdmin`), P4 |
| 15 Grant to a human; accepted set | P4 | S2, P3 |
| 16 Human principal | P10 | S1 |
| 17 Material and first authentication | P10, P6 | S1 |
| 18 Sign-in abuse resistance | P8 | S1 |
| 19 Organization sign-in | P10 | S1; verify-only material to S2 |
| 20 Environment credential | P5 | S2 |
| 21 Self-service | S1, S2 | P5, P10 |

Every M1-FR has a home.

---

## 6. Open Items

| Item | Effect on this design | Where it is resolved |
|---|---|---|
| **GAP-INT-008**: do bootstrap and renewal carry an envelope? | S3's two signatures, and P2's use in S3, are marked pending | Routing: `inception/working/gap-int-008-questions.md` |
| GAP-INT-003, 006, 007 | Worked around in S4, P4, and P2 respectively | soorma-prd#13, #24, #25 |
| Where the schema is produced | `contract/` must exist before any unit generates types | Units Generation (execution plan) |
| Datastores, internal broker, minting algorithm, P authenticator, bounds | Logical here | NFR Requirements and NFR Design, per unit |
| Paths, field encodings, error shapes, `maxChainDepth`, SSE reconnect overlap, where P is enrolled | Not designed here | Functional Design, per unit |

---

## 7. Extension Compliance at Application Design

### Security baseline

| Rule | Status | Note |
|---|---|---|
| SECURITY-01 | N/A at AD | Encryption at rest and in transit is set at Infrastructure Design and NFR Design. Every edge surface is HTTP, so TLS is required there |
| SECURITY-02, 07 | N/A at AD | Infrastructure Design |
| SECURITY-03, 14 | Compliant | Every deployable logs through a shared module; designed at NFR Design |
| SECURITY-04 | N/A | No HTML is served |
| SECURITY-05 | Compliant | Input validation is schema-driven at every edge operation (OpenAPI and JSON Schema), plus P2 and `isAcceptedIdentifier` |
| SECURITY-06 | N/A at AD | No cloud IAM yet |
| SECURITY-08 | Compliant | Deny by default in P3 and P11; every edge operation goes through P1 |
| SECURITY-09, 15 | Compliant | Fail closed (P5 `isRevoked`: unknown means deny) |
| SECURITY-10 | Compliant | M1-TECH-04 carried; the monorepo has one lockfile |
| SECURITY-11 | Compliant | Perimeters isolated in dedicated deployables (Q2 A); three unauthenticated surfaces, each through P8 |
| SECURITY-12 | Compliant | P authenticator, logout (`endSignIn`, `endEnvironmentCredential`), and brute-force protection (P8) have homes. Storage and session mechanics are at NFR Design |
| SECURITY-13 | Compliant | Deserialization safety: every edge input is validated against the contract schema before use (P1, P2). Data integrity: P7 records actor and time for registrations, grants, and secrets. Artifact integrity and CI/CD controls are set at Infrastructure Design and Code Generation (M1-TECH-04) |

**Security findings**: none blocking.

### Platform invariants

| Code | Where the design addresses it |
|---|---|
| I1 Isolation | One deployment, store, minting material, and channel per environment (Q1 A); only verify-only material leaves the organization level |
| I2 Perimeter enforcement | S2 to S4 each enforce at their own edge; raw calls reach identical checks; no broker exposed (Q4) |
| I3 Portable credential | Credentials minted by P5 assert registration and environment, never location; configuration via P9 |
| I4 Attribution recoverable | P7 is called on every platform-resource operation; P10 never prunes principals |
| I5 Monotonic authority | P3 is the single evaluation point; P11 answers containment only; the human-only class is in P4 |
| I6 Two faces | Separate deployables per face, each with its own NFR profile |
| I7 Contract compatibility | One schema source in `contract/`, versioned; pre-release in M1 |
| I8 Packaging rule | Only core capabilities are designed; the seams are unpublished; the licence layout follows PF §22 |
| I9 Mechanism, not instance | Payloads are opaque to S4 |
| I10 Runtime-later | The instance identifier is asserted; tenancy is configured |
| I11 No technology selection | N/A in Construction by design. This stage's technology choices (Q3 to Q5) are AI-DLC's, by I11 |

**Invariant findings**: none blocking.
