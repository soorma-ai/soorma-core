# Requirements: soorma-core M1 Walking Skeleton

**Built against**: `platform-foundations` @ `prd-platform-foundations-v1.1` (kind `plane`)
**Delivery scope**: soorma-prd/backlog/m1-walking-skeleton.md, `soorma-core` column
**Depth**: Comprehensive
**Companion**: [prd-coverage-map.md](../prd-intake/prd-coverage-map.md) holds the
inherited decisions, the items handed to AI-DLC, the open risks, and the full gap
entries. They are cited here, not repeated.

**Precedence**: the PRD at the tag wins over the brief, and the brief wins over this
document. A requirement below that reads "as stated" is built exactly as the cited PRD
section states it. Nothing here narrows, widens, or reinterprets the PRD. Where M1 does
less than the PRD, the reason is a recorded routing decision, and the requirement says so.

---

## 1. Intent Analysis

| | |
|---|---|
| **User request** | Build soorma-core's part of M1 from the slice brief: the server side of an event travelling between two agents in one environment, with identity context intact |
| **Request type** | New project (greenfield) |
| **Scope** | System-wide within soorma-core. Also the **owner of the wire contract** that soorma-sdk consumes |
| **Complexity** | Complex: the security perimeter, irreversible core assignments, and a contract consumed by another repository |

**What soorma-core proves** (brief, *done when*): items 1, 4, 6, and 7, plus 2 and 3,
**with raw calls and no SDK**. Item 5, trace emission, belongs to soorma-sdk.

---

## 2. Status of the Outcome

**M1 cannot complete in this repository until soorma-prd#12 is resolved.** Every *done
when* item needs a registered agent. Registration needs an authenticated human holding
`agent:register`, and both of those are open specification gaps (GAP-INT-001 and 002),
routed to block.

**Construction plan under the block** (an interpretation, to be confirmed at Workflow
Planning):
- Units that do not depend on the human control-plane path are designed and built
- Their tests may seed registrations, secrets, and revocation state through
  **test-only fixtures that are not compiled into the product**, on the same principle
  as the FR-011 decision (RA Q7)
- End-to-end proof of the *done when* items, using raw calls against a running stack,
  waits for #12. **No product stand-in for registration is built** (RA Q2 chose A, not D)

| Done when | Requirements | Status |
|---|---|---|
| 1. Two agents registered, each with a sponsor reference and ceiling snapshot | M1-FR-03 | **Blocked**: #12, GAP-INT-005 |
| 2. Each instance bootstraps and receives a short-lived credential (raw calls) | M1-FR-04, 05, 06 | Blocked transitively (needs 1) |
| 3. A publishes; B, subscribed in the same environment, receives it (raw calls) | M1-FR-11 | Blocked transitively. Delivery semantics worked around (#13) |
| 4. B's envelope carries scope, origin, and a perimeter-appended chain | M1-FR-01, 08, 09 | Blocked transitively |
| 6. A publish using another environment's credential is denied | M1-FR-09, 10 | Blocked transitively |
| 7. A draft that sets a platform-stamped field is rejected | M1-FR-01, 09 | Blocked transitively |

---

## 3. Functional Requirements

### Envelope and wire contract

**M1-FR-01: Envelope**, per FR-001, FR-002, FR-003, FR-005, FR-006, and §7b, as stated
- The seven fields. The perimeter writes the six platform-stamped fields and **rejects**
  a draft that sets any of them; it never overwrites
- Trace context is required, and is validated for well-formedness only, against **W3C
  Trace Context** (T-3). soorma-core emits no spans
- A draft declares its **client contract version**, which is distinct from the envelope
  version
- Unknown fields are preserved and forwarded. Unknown enumerated values are non-fatal
- The full actor chain is appended per hop, with `maxChainDepth` enforced. The value is
  decided at Functional Design and published with the contract
- *Verifies*: done-when 4 and 7

**M1-FR-02: Wire contract** (brief *Order and the shared contract*; §7; §14; FR-023)
- One versioned contract covers both entry points. It is decided here, and soorma-sdk
  pins a version of it
- It is defined in a language-neutral schema (see M1-TECH-02)
- The envelope's machine-readable definition is licensed Apache 2.0 (§22)
- It is **published as pre-release for M1**, because delivery semantics are unspecified
  (GAP-INT-003, #13)
- A raw caller that never links the SDK reaches identical enforcement

### Identity and credentials

**M1-FR-03: Logical agent registration**, per FR-007 and FR-016, as stated
- All eight attributes of §7a. The record carries its state. The suspend, resume, and
  retire **operations** are not in M1 scope (brief)
- The sponsorship ceiling is checked once at registration, and the snapshot is recorded.
  The meaning of "grantable set" waits on **GAP-INT-005**
- The re-broadening declaration accepts only **none**, and a registration declaring
  anything else is rejected (GAP-INT-004 work-around, #14)
- **Blocked** by GAP-INT-001 and 002 (#12) and GAP-INT-005

**M1-FR-04: Registration secret issuance**, per FR-008 (issuance only), as stated
- Rotation and retirement are absent
- **Blocked** by GAP-INT-001 and 002

**M1-FR-05: Bootstrap exchange and its abuse resistance**, per FR-009, FR-027, and §8b,
as stated
- Uses a locally-verified registration secret. The instance identifier is asserted and
  recorded, not verified
- Failed attempts are recorded against the registration. Attempt volume per
  registration is bounded; the shape and value are decided at NFR Requirements
- It is the only unauthenticated surface
- Accepted material types sit behind an internal identity-resolution boundary (M1-FR-13)
- *Verifies*: done-when 2

**M1-FR-06: Credential renewal**, per FR-010, as stated
- Renewal is never a weaker check than issuance. A lapsed instance re-bootstraps
- *Verifies*: done-when 2

**M1-FR-07: Revocation read**, per FR-012 and O3, as stated
- Revocation state is read on every request at both entry points
- It is cached for at most the published propagation bound, then the perimeter
  **denies**
- Revocation state is readable by no principal
- **No initiation surface** (FR-011 deferred, RA Q7). Tests prove O3 by seeding
  revocation state through a test-only path that is not compiled into the product

### Authority

**M1-FR-08: Authority evaluation**, per FR-014, FR-015, FR-017, FR-018, and §8b, as
stated
- Intersection across the chain, computed **in exactly one place** (I5 evidence)
- Origin stamping, including O6 and O12. Autonomy is honoured only when declared
- The minimal model: flat, opaque identifiers with set semantics, and deny by default
- An agent-set re-broadening record is rejected. Re-broadening is never evaluated in M1,
  because only *none* can be declared
- *Verifies*: done-when 4

### Perimeter and tenancy

**M1-FR-09: Perimeter obligations**, per FR-020 and O1 to O12, as stated
- The obligations are discharged independently at the Gateway (synchronous) and at Event
  ingest (asynchronous), and neither entry point trusts the other (O10)
- *Verifies*: done-when 6 and 7

**M1-FR-10: Environment**, per FR-021, FR-022, O11, and §6, as stated
- Every record, identifier, cache, and namespace is keyed on environment
- Environment identity is configured, never inferred
- Verification material is per environment and never shared
- *Verifies*: done-when 6

### Event

**M1-FR-11: Publish and subscribe on the environment namespace**, per §8a, §6, and OB-6
- `event:publish` and `event:subscribe` apply in the environment's namespace. There are
  no topics and no topic administration (A-2)
- **Delivery reaches live subscribers only**: no durability, ordering, or redelivery. The
  contract states that delivery semantics are unspecified (GAP-INT-003 work-around, #13)
- Delivery to a subscriber stops within the propagation bound once its credential
  expires or is revoked (T-2)
- O4 is checked at both publish and subscribe
- *Verifies*: done-when 3

### Attribution

**M1-FR-12: Attribution recording**, per FR-025 (recording only)
- Every platform-resource operation M1 performs writes a record carrying scope, actor,
  chain, and origin. Sponsorship is resolvable through the registration (I4)
- There is no read surface

### Seams

**M1-FR-13: Internal seam boundaries**, per FR-026, decision B (RA Q8)
- The code is shaped at the policy-decision and identity-resolution seam lines
- Seam containment (§12) is honoured: the policy boundary decides containment, never
  composition
- No interface is published and no configuration selection is offered

### Absent from M1

These are absent, not simplified: FR-004 transition machinery, FR-008 rotation and
retirement, FR-011 initiation, FR-013, FR-019, FR-023 (owned by soorma-sdk), FR-024,
the FR-025 read surface, FR-026 publication, topics and topic administration,
re-broadening evaluation, and everything commercial. Coverage map, *M1 Scope*.

---

## 4. Non-Functional Requirements

| ID | Requirement | Source |
|---|---|---|
| M1-NFR-01 | **Data face**: the revocation read must not dominate request latency. Exchange and renewal have a slower budget. Availability is bounded by the cache, not by the store. Throughput scales with request volume. The propagation bound and credential lifetime are set at NFR Requirements | §9 NFR profile; FR-012 |
| M1-NFR-02 | **Control face**: registrations have the highest durability in the initiative. Consistency is read-your-writes for the acting principal. Throughput is low. Every operation is attributed | §10 NFR profile |
| M1-NFR-03 | Data-face and control-face operations are reachable through **separate surfaces**, each with its own NFR configuration | I6; §10 *Single-Face Statement* |
| M1-NFR-04 | Every published contract is versioned under the §7 compatibility policy, and compatibility is tested. For M1 the contract is pre-release | I7; §7, §14 |
| M1-NFR-05 | **The whole stack runs locally** for a developer | Brief, *Developer-visible outcome* |
| M1-NFR-06 | Security baseline SECURITY-01 to 15 are blocking constraints (Section 7) | RA Q10 |
| M1-NFR-07 | Platform invariants I1 to I10 are blocking constraints in Construction; I11 is N/A in Construction by design (Section 7) | RA Q11; PRD §15 |

---

## 5. Technology Decisions

| ID | Decision | Rationale and constraint |
|---|---|---|
| **M1-TECH-01** | **TypeScript with NestJS** | User's choice (clarification Q2): one language end to end. NestJS guards and interceptors map to O1 to O12 per entry point, and DI suits M1-FR-13. **TECH-02 to TECH-04 are conditions of this choice, not recommendations**, and each is verified at Code Generation and at Build and Test |
| **M1-TECH-02** | **Condition 1: the wire contract is defined in a language-neutral schema** (JSON Schema or OpenAPI, chosen at Application Design). TypeScript types are **generated** from it. No hand-written TypeScript type is shared with soorma-sdk | Keeps the SDK from becoming the contract (I2, I7), lets the SDK use other languages, gives the Apache 2.0 envelope definition a clean home (§22), and keeps the server language replaceable |
| **M1-TECH-03** | **Condition 2: perimeter and ingest components are stateless and horizontally scalable.** State lives in external stores. A hot component can be replaced behind the contract without tenants noticing | Contains Node's per-instance throughput and memory cost against Go |
| **M1-TECH-04** | **Condition 3: dependency discipline from the first commit.** A committed lockfile; a minimal dependency set, each dependency justified; vulnerability scanning in CI; an SBOM; pinned toolchain and base images | Contains the npm supply-chain surface on a security perimeter. Matches SECURITY-10 |
| M1-TECH-05 | W3C Trace Context (`traceparent` required, `tracestate` optional), validated for well-formedness only | T-3; Decision 8 left the standard to AI-DLC (I11) |

Every other handed-over item (the propagation bound, credential lifetime,
`maxChainDepth`, the bootstrap attempt bound, credential format, secret storage, the
environment configuration mechanism, and repository layout) stays with the stage named
in the coverage map's *Handed to AI-DLC*.

---

## 6. Open Specification Gaps

The full entries are in the coverage map. The register is in `aidlc-state.md`.

| ID | Summary | Routing | Effect on M1 |
|---|---|---|---|
| GAP-INT-001 | Human principal and control-plane authentication | Raised, soorma-prd#12 | **Blocking** |
| GAP-INT-002 | First human grant (R-2) | Raised, soorma-prd#12 | **Blocking** |
| GAP-INT-003 | Event delivery guarantees | Raised, soorma-prd#13 | Worked around (M1-FR-11) |
| GAP-INT-004 | Re-broadening evaluation rule | Raised, soorma-prd#14 | Worked around (M1-FR-03, 08) |
| GAP-INT-005 | Meaning of "grantable set" (FR-016) | To be raised. **Issue placement awaiting confirmation** (#12 or #14) | Blocking the ceiling check, which is already blocked by #12 |

---

## 7. Extensions and Compliance at Requirements Analysis

**Enabled**: security baseline; platform invariants; PR checkpoint; QA test cases
(comprehensive); tickets as **GitHub issues on soorma-core** instead of JIRA.

**Tickets** (clarification Q3): at the end of Inception, before the PR checkpoint, create
one tracking issue for the initiative with one sub-issue per unit of work. No markdown
ticket file is written. The created issue numbers are recorded in `aidlc-state.md`.

### Security baseline at this stage

| Rule | Status | Note |
|---|---|---|
| SECURITY-01, 02, 07 | N/A at RA | Infrastructure Design |
| SECURITY-03, 14 | Compliant | Required of every component (M1-NFR-06). Designed at NFR Design |
| SECURITY-04 | N/A | M1 serves no HTML (the portal is out of scope) |
| SECURITY-05, 08 | Compliant | O1 to O12, the stamped/asserted partition, and deny by default are captured (M1-FR-01, 08, 09) |
| SECURITY-06 | N/A at RA | No cloud IAM yet |
| SECURITY-09, 13, 15 | Compliant | Fail closed is FR-012 (M1-FR-07). The rest are designed at NFR Design |
| SECURITY-10 | Compliant | M1-TECH-04 |
| SECURITY-11 | Compliant | Bootstrap abuse resistance (M1-FR-05); perimeter isolated in dedicated components (M1-TECH-03) |
| SECURITY-12 | Applicable, **partly blocked** | Human authentication (passwords, MFA, sessions) waits on GAP-INT-001. For agent secrets, how high-entropy registration secrets are stored is decided at NFR Design |

### Platform invariants at this stage

Scope inherited from PRD §15: all eleven are `Addressed` and none is N/A. The
invariants were read at `prd-platform-foundations-v1.1`. At Requirements Analysis the
obligation is to record scope, which is done.

| Code | Where it lands in these requirements |
|---|---|
| I1 Isolation | M1-FR-10, M1-FR-11 |
| I2 Perimeter enforcement | M1-FR-02 (raw calls), M1-FR-09 |
| I3 Portable credential | M1-FR-05, M1-FR-10 |
| I4 Attribution recoverable | M1-FR-12 |
| I5 Monotonic authority | M1-FR-08 |
| I6 Two faces | M1-NFR-03 |
| I7 Contract compatibility | M1-FR-02, M1-NFR-04, M1-TECH-02 |
| I8 Packaging rule | The *Absent from M1* list. No commercial capability is built |
| I9 Mechanism, not instance | No tenant schema or payload is inspected (M1-FR-01) |
| I10 Runtime-later | M1-FR-05 (instance identifier asserted, not verified) |
| I11 No technology selection | N/A in Construction by design. Section 5 is where technology is selected |
