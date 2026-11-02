# Requirements: soorma-core M1 Walking Skeleton

**Built against**: `platform-foundations` (**PF**) @ `prd-platform-foundations-v1.3` and `identity` (**ID**) @ `prd-identity-v1.0`, both kind `plane`
**Delivery scope**: soorma-prd/backlog/m1-walking-skeleton.md @ `0aad84a`, `soorma-core` column
**Depth**: Comprehensive
**Revision**: run 2, after re-intake run 2 (2026-11-02). Run 1 was approved 2026-10-06 against PF @ `prd-platform-foundations-v1.1`
**Companions**:
- [prd-coverage-map.md](../prd-intake/prd-coverage-map.md): inherited decisions, items handed to AI-DLC, open risks, and intake classifications
- [specification-gaps.md](../prd-intake/specification-gaps.md): the full gap entries

Both are cited here, not repeated.

**Precedence**: each PRD at its tag wins over the brief, and the brief wins over this
document. A requirement that reads "as stated" is built exactly as the cited PRD section
states it. Nothing here narrows, widens, or reinterprets a PRD. Where M1 does less than a
PRD, the reason is a recorded routing or delivery decision, and the requirement says so.

**IDs**: every PRD-scoped ID is qualified by its key (`PF FR-016`, `ID FR-015`).
Obligations (`OB-n`) and invariants (`I1` to `I11`) are global. M1 requirement IDs from
run 1 are kept; M1-FR-14 to M1-FR-21 are new in run 2.

---

## 0. What Run 2 Changed

The re-run is scoped to the coverage map's *Stages Re-opened*.

| Area | Change | Where |
|---|---|---|
| (a) PF sections changed v1.1 → v1.3 | No envelope on a direct human operation; the re-broadening record is load-bearing only and travels with the chain; the registration secret's issuer; grantable = held, plus the human-only class; the origin table's delegated first hop; human credentials at the perimeter; verify-only material; attribution of human actors and configuration grants; the widened identity-resolution seam | M1-FR-01, 03, 04, 05, 08, 09, 10, 12, 13 |
| (b) Blocks lifted, work-around removed | GAP-INT-001, 002, and 005 resolved, so registration is no longer blocked. **The GAP-INT-004 work-around comes out**: re-broadening is built as PF FR-017 states | §2; M1-FR-03, 08; §6 |
| (c) New scope | The human side (ID FR-001, 004, 006 to 010, 013, 015, 022, 023); *decide at intake* ID FR-006 (**K + P**, RA run-2 Q1) and ID FR-011 (**all self-service**, Q2); PF FR-026 re-confirmed (Q3) | M1-FR-09, 14 to 21; M1-NFR-08, 09; M1-TECH-06, 07 |
| (d) GAP-INT-006 | Raised as soorma-prd#24 and worked around: only plane-declared permission identifiers are accepted | M1-FR-15; M1-FR-03; M1-FR-02 |
| (e) Extension compliance | SECURITY-12 no longer partly blocked; invariant scope inherited from both PRDs' §15 | §7 |

Carried forward unchanged except for ID qualification: M1-FR-06, M1-NFR-02 to 07, and
M1-TECH-01 to 05. M1-FR-02, 07, and 11 gain only the additions marked below.

---

## 1. Intent Analysis

| | |
|---|---|
| **User request** | Build soorma-core's part of M1 from the slice brief. That is the server side of an event travelling between two agents in one environment with identity context intact, **including the human side that registers them** |
| **Request type** | New project (greenfield) |
| **Scope** | System-wide within soorma-core. Also the **owner of the wire contract** that soorma-sdk consumes |
| **Complexity** | Complex: two security perimeters (agent and human), three unauthenticated surfaces, irreversible core assignments, and a contract consumed by another repository |

**What soorma-core proves** (brief, *done when*): items 1, 4, 6, and 7, plus 2 and 3
**with raw calls and no SDK**. Item 5, trace emission, belongs to soorma-sdk.

---

## 2. Status of the Outcome

**No *done when* item this repository proves is blocked.** soorma-prd#12 is resolved by
ID @ `prd-identity-v1.0`. ID §1 traces item 1 with no exception. Two gaps remain, each
worked around, and neither blocks a *done when* item:
- GAP-INT-003, event delivery: `Awaiting PRD: Event`
- GAP-INT-006, which permissions are valid in E: `Open`, soorma-prd#24

Run 1's construction plan under the block no longer applies. Test-only fixtures that are
not compiled into the product remain in one place only: seeding **agent** revocation
state, because agent revocation initiation is deferred (PF FR-011, RA run-1 Q7).

| Done when | Requirements | Status |
|---|---|---|
| 1. Two agents registered, each with a sponsor reference and ceiling snapshot | M1-FR-03, 04, 14 to 20 | Buildable. The ID §1 trace, steps 1 to 9 |
| 2. Each instance bootstraps and receives a short-lived credential (raw calls) | M1-FR-04, 05, 06 | Buildable |
| 3. A publishes; B, subscribed in the same environment, receives it (raw calls) | M1-FR-11 | Buildable. Delivery semantics worked around (GAP-INT-003); both agents declare autonomy (A-5) |
| 4. B's envelope carries scope, origin, and a perimeter-appended chain | M1-FR-01, 08, 09 | Buildable |
| 6. A publish using another environment's credential is denied | M1-FR-09, 10, 20 | Buildable |
| 7. A draft that sets a platform-stamped field is rejected | M1-FR-01, 09 | Buildable |

---

## 3. Functional Requirements

### Envelope and wire contract

**M1-FR-01: Envelope**, per PF FR-001, FR-002, FR-003, FR-005, FR-006, and PF §7b, as stated
- Every event and every **agent-originated** synchronous platform call carries the
  envelope. **A direct human operation carries none** (PF FR-001 v1.3; ID FR-022)
- The seven fields. The perimeter writes the six platform-stamped fields and **rejects**
  a draft that sets any of them; it never overwrites
- **Origin mode is stamped by the perimeter on every hop, including an autonomous first
  hop**, where it is derived from the registration's autonomy declaration. A draft
  setting origin mode is rejected. This is the **GAP-INT-007 work-around** (PF §8b
  "agent-asserted, accepted" contradicts PF §11, FR-015, and §7b). Accepting an asserted
  value later is additive
- The re-broadening record is stamped only when re-broadening was **load-bearing**. It
  names the hop and travels with the chain (PF §7b, §8b)
- Trace context is required and is validated for well-formedness only, against **W3C
  Trace Context** (M1-TECH-05). soorma-core emits no spans
- A draft declares its **client contract version**, distinct from the envelope version
- Unknown fields are preserved and forwarded. Unknown enumerated values are non-fatal
- The full actor chain is appended per hop, with `maxChainDepth` enforced. The value is
  decided at Functional Design and published with the contract
- The *delegating principal* field is never stamped in M1, because no delegated chain
  can start (A-5)
- *Verifies*: done-when 4 and 7

**M1-FR-02: Wire contract** (brief *Order and the shared contract*; PF §7, §14; PF FR-023; ID §7b, §17)
- One versioned contract covers both entry points **and the human operations M1
  builds**: sign-in, first authentication, self-service, environment credential
  issuance and renewal, grant to a human, and registration and secret issuance by a
  human. soorma-sdk pins a version of it
- Human operations are called from the human's own client, which is not a registered
  agent. There is no client library for the human side (ID §11)
- It is defined in a language-neutral schema (M1-TECH-02)
- The envelope's machine-readable definition is licensed Apache 2.0 (PF §22)
- It is **published as pre-release for M1**, because delivery semantics are unspecified
  (GAP-INT-003, soorma-prd#13)
- **The accepted permission identifiers may widen in a compatible version** (GAP-INT-006,
  soorma-prd#24)
- **Delegation-credential presentation can be added without a breaking change** (A-4;
  ID §14, "additive only")
- A raw caller that never links the SDK reaches identical enforcement

### Identity and credentials: agents

**M1-FR-03: Logical agent registration**, per PF FR-007, FR-016, FR-017, and PF §7a, as stated
- All eight attributes of PF §7a. The record carries its state. The suspend, resume, and
  retire **operations** are not in M1 scope (brief)
- Invoked by a **human** who presents an environment credential for E at the Gateway
  and holds `agent:register` in E (ID FR-022; ID §1 trace, step 6). The sponsor
  reference names that human (ID FR-001)
- **Sponsorship ceiling**: the standing set must lie within the sponsor's **held** set
  in E at the moment of granting. The snapshot records that held set. A standing set
  containing a **human-only** permission is rejected whatever the sponsor holds. At
  these tags the human-only permissions are `grant:human`, `human:manage`, and
  `agent:delegate` (PF FR-016, §8b; ID FR-013)
- **Re-broadening declaration**: a permission set, possibly empty, **within the
  standing set**. A registration declaring more is rejected (PF FR-017, §7a). Run 1
  accepted only a declaration of *none*; that work-around is removed (GAP-INT-004
  resolved)
- **Autonomy declared**: boolean, default no (PF §7a)
- Standing-set identifiers are limited as in M1-FR-15 (GAP-INT-006 work-around)
- Rejections, per PF §10: standing set exceeds what the sponsor holds; standing set
  includes a human-only permission; declaration exceeds the standing set; sponsor's
  held set unresolvable
- *Verifies*: done-when 1

**M1-FR-04: Registration secret issuance**, per PF FR-008 (issuance only), as stated
- Required authority `agent:register`, held by an Admin or the sponsoring Developer (PF §8a)
- The secret records its **issuer**: the human who issued it, a lower bound on who knows
  it (PF §7a v1.3)
- Rotation and retirement are absent
- *Verifies*: precondition for done-when 2

**M1-FR-05: Bootstrap exchange and its abuse resistance**, per PF FR-009, FR-027, and PF §8b, as stated
- Uses a locally-verified registration secret. The instance identifier is asserted and
  recorded, not verified
- Failed attempts are recorded against the registration. Attempt volume per
  registration is bounded; the shape and value are decided at NFR Requirements
- It is the only unauthenticated surface **in PF's capability**. **In M1 it is one of
  three**, with sign-in and first authentication (M1-FR-17, M1-FR-18; A-6). *Corrects
  run 1, which called it the only one*
- Accepted material types sit behind the internal identity-resolution boundary (M1-FR-13)
- *Verifies*: done-when 2

**M1-FR-06: Credential renewal**, per PF FR-010, as stated
- Renewal is never a weaker check than issuance. A lapsed instance re-bootstraps
- *Verifies*: done-when 2

**M1-FR-07: Revocation read**, per PF FR-012 and O3, as stated
- Revocation state is read on every request at both entry points
- It is cached for at most the published propagation bound, after which the perimeter
  **denies**
- Revocation state is readable by no principal
- For human environment credentials, O3 also refuses a credential the human has ended
  (M1-FR-21). It refuses once the principal is not `active`; only `pending` and `active`
  exist in M1 (ID §8b)
- **No initiation surface for agent credentials** (PF FR-011 deferred, RA run-1 Q7).
  Tests prove agent-side O3 by seeding revocation state through a test-only path that is
  not compiled into the product

### Authority

**M1-FR-08: Authority evaluation**, per PF FR-014, FR-015, FR-017, FR-018, and PF §8b, as stated
- The intersection across the chain is computed **in exactly one place** (I5 evidence)
- **Origin**, per the PF §8b table at v1.3. A delegated chain's first hop is stamped
  from a delegation credential, which is **absent in M1** (ID FR-019 to FR-021 out).
  So **every M1 chain starts autonomous** (A-5):
  - no inbound context with autonomy declared: `autonomous`
  - no inbound context without it: **denied** (O12)
  - an event-triggered hop propagates origin unchanged, and the chain grows
- **Re-broadening**, per the PF §8b rule:
  - at the declaring hop, `standing ∩ delegating principal ∩ (upstream agents ∪ declared)`,
    where the delegating-principal term reads *yes* in autonomous origin
  - exercised and recorded only when **load-bearing**
  - **local** to its hop
  - an agent-set re-broadening record is rejected
- The minimal model: flat, opaque identifiers with set semantics, and deny by default
- **Direct human operations**: effective authority is the human's grants in E (ID §8b,
  O8). A human has no origin mode (ID §8a)
- *Verifies*: done-when 4

### Perimeter and tenancy

**M1-FR-09: Perimeter obligations**, per PF FR-020 and O1 to O12; ID FR-022, FR-023, and ID §8b, as stated
- **Agent traffic**: O1 to O12 are discharged independently at the Gateway
  (synchronous) and at Event ingest (asynchronous). Neither entry point trusts the
  other (O10)
- **Human credentials**: the Gateway validates them by kind against O1 to O4 and O8 to
  O11. O5 to O7 do not apply, because there is no envelope. The organization sign-in is
  refused in every environment except at that environment's credential issuance
- **Every presenter × entry point in ID §8b's matrix is reached or refused**:
  - Event ingest refuses every human credential
  - an agent credential presented beside a human's credential is refused
  - a delegation credential presented alone, or beside another agent's credential, is
    refused
  - an agent credential with a delegation credential bound to it is refused by
    ID FR-020's own checks, since no delegation credential can be live in M1 (A-4)
- *Verifies*: done-when 6 and 7

**M1-FR-10: Tenancy**, per PF FR-021, FR-022, O11, and PF §6; ID FR-004 and ID §6, as stated
- Every agent-side record, identifier, cache, and namespace is keyed on environment.
  Human principals, their material, and sign-ins are keyed on **organization** (ID §6)
- Organization, project, and environment identity are configured, never inferred
- **No material that can mint** credentials is shared across environments. Environments
  hold **verify-only** material for the organization sign-in (PF §6 v1.3; ID FR-009)
- *Verifies*: done-when 6

### Event

**M1-FR-11: Publish and subscribe on the environment namespace**, per PF §8a, PF §6, and OB-6
- `event:publish` and `event:subscribe` apply in the environment's namespace. There are
  no topics and no topic administration (A-2)
- **Delivery reaches live subscribers only**: no durability, ordering, or redelivery. The
  contract states that delivery semantics are unspecified (GAP-INT-003 work-around,
  soorma-prd#13)
- Delivery to a subscriber stops within the propagation bound once its credential
  expires or is revoked (T-2)
- O4 is checked at both publish and subscribe. Event ingest refuses human credentials
- **Both demo agents are registered with autonomy declared**: A to publish, B to
  subscribe. PF R-4 is accepted (A-5)
- *Verifies*: done-when 3

### Attribution

**M1-FR-12: Attribution recording**, per PF FR-025 (recording only)
- Every platform-resource operation M1 performs writes a record carrying scope, actor,
  chain, and origin. Sponsorship is resolvable through the registration (I4)
- **A direct human operation** is attributed to the human principal and the credential
  presented, with no origin mode (ID §7b *Recoverability*; ID FR-022)
- A grant made by configuration records *granted-by* = the environment's configuration
  (PF FR-018, §7a v1.3). **Every self-grant is recorded** (ID FR-015)
- Sign-in and first authentication are recorded through their own records:
  - Organization Sign-In
  - Human Authentication Material, with established-at and established-by
  - failed attempts, per ID FR-008

  There is no organization-level attribution record (ID FR-018 out; M1 performs no
  organization-wide operation)
- First-hop delegation naming (PF FR-025 v1.3) is absent, because there is no
  delegation in M1
- There is no read surface

### Seams

**M1-FR-13: Internal seam boundaries**, per PF FR-026, decision B (RA run-1 Q8), **extended at run 2** (RA run-2 Q3)
- The code is shaped at the policy-decision and identity-resolution seam lines
- The identity-resolution boundary accepts **authentication** material types (PF §12
  v1.3):
  - the agent registration secret, returning an agent registration reference
  - core's human material (K, and P), returning a human principal reference

  External subjects and the class-X binding are absent (ID FR-027 external types out)
- Seam containment (PF §12; ID §12) is honoured. The policy boundary decides
  containment, never composition. The identity boundary decides identity, never
  authority. The human record, grant creation, enrollment single use, and the
  human-only class stay in core, behind no boundary
- No interface is published and no configuration selection is offered

### Human side (new at run 2)

**M1-FR-14: Configured tenancy and the first Admin**, per ID FR-004 and ID FR-007 (first-Admin material), as stated
- Organization, project, and environment identity and membership are **configured,
  never inferred** (PF FR-022 extended)
- An environment's configuration names its **first Admin**. If the principal does not
  exist, configuration registers it `pending` with single-use **enrollment material**,
  and grants it `grant:human` and `human:manage` in that environment, with *granted-by*
  = configuration
- The trust root is the deployment's configuration. An environment where no one holds
  `grant:human` is recovered only by configuration
- The deployer never holds a working credential. How the material is delivered is
  M1-TECH-06
- *Verifies*: done-when 1 (ID §1 trace, steps 1 and 2)

**M1-FR-15: Grant to a human, and the accepted permission set**, per ID FR-015, ID FR-013, and PF §8a; **GAP-INT-006 work-around**
- A holder of `grant:human` in E may grant any permission valid in E to any human,
  **themselves included**. It never requires the Admin to hold what they grant. Every
  self-grant is recorded
- `human:manage` and `agent:delegate` are declared human-only, joining `grant:human`
  (ID FR-013; PF §8b)
- **Accepted identifiers** (GAP-INT-006, soorma-prd#24, re-intake Q2 routing E):
  - only the plane-declared identifiers are accepted: PF's `agent:register`,
    `credential:revoke`, `agent:retire`, `grant:human`, `event:publish`,
    `event:subscribe`, and `attribution:read`, and ID's `human:manage` and
    `agent:delegate`
  - any other identifier is rejected, in grants and in standing sets (M1-FR-03)
  - this is **a recorded delivery limit, not the specified behaviour**. Tenant-defined
    identifiers are unbuilt, and widening later is additive
- Revoking a human's grant (ID FR-016) is absent
- *Verifies*: done-when 1 (ID §1 trace, step 5)

**M1-FR-16: The human principal**, per ID FR-001, as stated
- Organization-scoped. Its identifier is unique within the organization, composed with
  it, and never allocated globally. A person in two organizations is two principals
- Never deleted, never pruned (a resolution target)
- Attributes include registered-at and registered-by (configuration, for the first Admin)
- States reached in M1: `pending`, `active`. Suspension and deactivation operations are
  absent (ID FR-003 out); further human registration is absent (ID FR-002 out)

**M1-FR-17: Authentication material and first authentication**, per ID FR-006 and ID FR-007; **K + P** (RA run-2 Q1 A)
- Material classes **K** (memorized secret) and **P** (possession-based authenticator).
  Core accepts K, or K + P. Once a human enrolls P, sign-in needs both
- **The organization's configuration may require P for every human.** It is set by
  configuration only; no API is offered (ID FR-005 out). Where it is required and P is
  not enrolled, sign-in is refused until P is enrolled (ID §10). That human can still
  enroll P without a sign-in, by presenting their current K (M1-TECH-07, constraint 2)
- Material is held and verified **at the organization level only**, and K only in a
  form that can verify (M1-NFR-09)
- Enrollment material is single-use and is replaced by the human on first
  authentication. Reuse is refused (ID §10)
- Class X (external subjects) is absent
- *Verifies*: done-when 1 (ID §1 trace, step 3)

**M1-FR-18: Sign-in abuse resistance**, per ID FR-008, as stated
- Sign-in and first authentication are **unauthenticated surfaces**
- Failed attempts are recorded against the principal. Attempt volume per principal is
  bounded; the bound's value and shape are decided at NFR Requirements (control face)

**M1-FR-19: The organization sign-in**, per ID FR-009, as stated
- Authenticating at the organization level yields a short-lived sign-in asserting the
  subject, organization, time, and material classes used
- It is **refused at every environment's perimeter except that environment's credential
  issuance**. Otherwise it serves organization-scoped operations only; in M1 those are
  self-service (M1-FR-21)
- Environments hold verify-only material for it
- The organization level sits outside every environment and on no per-request path
- Its lifetime is decided at NFR Requirements
- *Verifies*: done-when 1 (ID §1 trace, step 3)

**M1-FR-20: The human environment credential**, per ID FR-010, as stated
- **Issued by environment E** against a live sign-in, to an `active` principal holding
  at least one grant in E
- **Accepted only in E** (O4)
- Short-lived and renewable. Renewal never widens authority and never outlives
  revocation, its sign-in, or the principal's `active` state. Its lifetime is decided at
  NFR Requirements
- *Verifies*: done-when 1 (step 4); done-when 6 (a credential from another environment
  is refused)

**M1-FR-21: Self-service**, per ID FR-011; **all of it** (RA run-2 Q2 A)
- Without a grant, a human may:
  - renew and **end** their own sign-in
  - end their own environment credential
  - change their own K and P, by presenting the current material. That includes
    enrolling P with no sign-in when the organization requires P (M1-TECH-07)
- Ending a sign-in or a credential is the **logout** (SECURITY-12). An ended credential
  is refused thereafter (O3; M1-FR-07)
- Acting on another human's credentials or material (ID FR-012) is absent

### Absent from M1

These are absent, not simplified:
- **PF**: FR-004 transition machinery; FR-008 rotation and retirement; FR-011
  initiation (agent credentials); FR-013; FR-019; FR-023 (owned by soorma-sdk); FR-024;
  the FR-025 read surface; FR-026 publication
- **ID**: FR-002, FR-003, FR-005, FR-012, FR-014, FR-016 to FR-021, FR-024 to FR-026,
  FR-027 external types and binding, FR-028, FR-029; class X
- **Behaviour**: delegated origin paths; topics and topic administration;
  tenant-defined permission identifiers (GAP-INT-006 work-around); everything
  commercial

**Consequence of ID FR-012 (reset) being absent**: **lost K or P is unrecoverable in
M1.** Enrollment material is issued only at registration, at a reset, and for a configured
first Admin (ID FR-007). Configuration creates the first Admin only if that principal does
not already exist (ID FR-004). With further registration (ID FR-002) and reset both
absent, nothing can issue new material to an existing principal. A human who loses K or P
is locked out, and the remedy is to re-create the local stack. That is acceptable for a
walking skeleton run locally. It is a delivery limit, not specified behaviour, and reset
lands additively with ID FR-012.

See the coverage map, *Slice Scope*.

---

## 4. Non-Functional Requirements

| ID | Requirement | Source |
|---|---|---|
| M1-NFR-01 | **Data face**: the revocation read must not dominate request latency. Exchange and renewal have a slower budget. Availability is bounded by the cache, not by the store. Throughput scales with request volume. The propagation bound and credential lifetime are set at NFR Requirements. The propagation bound is **one number**: it also bounds human lifecycle freshness (ID FR-021), which M1 does not exercise | PF §9 NFR profile; PF FR-012; ID §9 |
| M1-NFR-02 | **Control face**: registrations have the highest durability in the initiative. Consistency is read-your-writes for the acting principal. Throughput is low. Every operation is attributed | PF §10 NFR profile |
| M1-NFR-03 | Data-face and control-face operations are reachable through **separate surfaces**, each with its own NFR configuration | I6; PF §10 *Single-Face Statement* |
| M1-NFR-04 | Every published contract is versioned under the PF §7 compatibility policy, and compatibility is tested. For M1 the contract is pre-release | I7; PF §7, §14; ID §7b |
| M1-NFR-05 | **The whole stack runs locally** for a developer, organization level included | Brief, *Developer-visible outcome* |
| M1-NFR-06 | Security baseline SECURITY-01 to 15 are blocking constraints (Section 7) | RA run-1 Q10 |
| M1-NFR-07 | Platform invariants I1 to I10 are blocking constraints in Construction; I11 is N/A in Construction by design (Section 7) | RA run-1 Q11; PF §15; ID §15 |
| **M1-NFR-08** | **Organization level and the human control face**: highest durability for the human principal record. **Interactive** latency for sign-in and environment credential issuance. Read-your-writes for the actor. The organization level is on no per-request path. Its outage stops new sign-ins and organization operations; agent data-plane traffic is unaffected, because M1 has no delegation | ID §10 NFR profile; ID FR-009 |
| **M1-NFR-09** | **Human authentication**, per SECURITY-12, within ID FR-006: K of at least 8 characters, checked against breached-secret lists. K stored only under an adaptive one-way algorithm. P supported (MFA for the administrative first Admin). Sign-ins and environment credentials expire server-side and are invalidated when ended. If cookies carry them, `Secure`, `HttpOnly`, and `SameSite`. Brute-force protection is M1-FR-18. **No credential in source or IaC templates**, including the first Admin's enrollment material | SECURITY-12; ID FR-006, FR-007 |

---

## 5. Technology Decisions

| ID | Decision | Rationale and constraint |
|---|---|---|
| **M1-TECH-01** | **TypeScript with NestJS** | User's choice (run-1 clarification Q2): one language end to end. NestJS guards and interceptors map to O1 to O12 per entry point, and DI suits M1-FR-13. **TECH-02 to TECH-04 are conditions of this choice, not recommendations**, and each is verified at Code Generation and at Build and Test |
| **M1-TECH-02** | **Condition 1: the wire contract is defined in a language-neutral schema** (JSON Schema or OpenAPI, chosen at Application Design). TypeScript types are **generated** from it. No hand-written TypeScript type is shared with soorma-sdk | Keeps the SDK from becoming the contract (I2, I7), lets the SDK use other languages, gives the Apache 2.0 envelope definition a clean home (PF §22), and keeps the server language replaceable |
| **M1-TECH-03** | **Condition 2: perimeter and ingest components are stateless and horizontally scalable.** State lives in external stores. A hot component can be replaced behind the contract without tenants noticing | Contains Node's per-instance throughput and memory cost against Go |
| **M1-TECH-04** | **Condition 3: dependency discipline from the first commit.** A committed lockfile; a minimal dependency set, each dependency justified; vulnerability scanning in CI; an SBOM; pinned toolchain and base images | Contains the npm supply-chain surface on a security perimeter. Matches SECURITY-10 |
| M1-TECH-05 | W3C Trace Context (`traceparent` required, `tracestate` optional), validated for well-formedness only | T-3; PF Decision 8 left the standard to AI-DLC (I11) |
| **M1-TECH-06** | The first Admin's enrollment material is delivered through the **configuration mechanism**, decided at Infrastructure Design | T-4, confirmed at RA run-2 Q4. Constraints: single-use; never a working credential in the deployer's hands; configured, never inferred; held only at the organization level once consumed; never in source or IaC (M1-NFR-09) |
| **M1-TECH-07** | **Where P is enrolled**: at first authentication, or by self-service presenting the current material. Decided at Functional Design | Classified at this re-run as technology: both readings satisfy ID FR-006, FR-007, and FR-011, and neither engineer would be wrong. Constraints: (1) where the organization requires P, sign-in is refused until P is enrolled (ID §10). (2) **Whichever enrollment point is chosen, a human for whom P is required but not enrolled must be able to enroll P without a sign-in, by presenting their current K** (ID FR-011, "by presenting the current material"). Reset (ID FR-012) is absent in M1, so without this, turning the requirement on locks out every human, including the only Admin. **The authenticator that implements class P** is chosen at NFR Requirements (ID names material by class only) |

Every other handed-over item stays with the stage named in the coverage map's *Handed to
AI-DLC*. That includes: the propagation bound, the agent credential lifetime,
`maxChainDepth`, the bootstrap and sign-in attempt bounds, the sign-in and environment
credential lifetimes, credential formats, verify-only material, K storage, secret
storage, organization-level placement, the configuration mechanism, and the repository
layout.

---

## 6. Specification Gaps

The full entries are in [specification-gaps.md](../prd-intake/specification-gaps.md). The
register is in `aidlc-state.md`.

| ID | Summary | Status | Effect on M1 |
|---|---|---|---|
| GAP-INT-001 | Human principal and control-plane authentication | Resolved — answered elsewhere (ID @ v1.0) | Built: M1-FR-16, 17, 19, 20, 09 |
| GAP-INT-002 | First human grant (PF R-2) | Resolved — answered elsewhere (ID @ v1.0 FR-004) | Built: M1-FR-14, 15 |
| GAP-INT-003 | Event delivery guarantees | **Awaiting PRD: Event** (soorma-prd#13) | Worked around: M1-FR-11, M1-FR-02 (pre-release) |
| GAP-INT-004 | Re-broadening evaluation rule | Resolved — PRD amended (PF @ v1.3 §8b) | Built as stated: M1-FR-03, 08. Work-around removed |
| GAP-INT-005 | Meaning of "grantable set" | Resolved — PRD amended (PF @ v1.3 FR-016; ID FR-015) | Built as stated: M1-FR-03, 15 |
| GAP-INT-006 | Which permissions are valid in E | **Open** (soorma-prd#24) | Worked around: M1-FR-15, M1-FR-03, M1-FR-02 |
| GAP-INT-007 | Origin at an autonomous first hop: agent-asserted or platform-stamped (found at User Stories) | Classified; **routing pending** | Worked around (reject and stamp): M1-FR-01, M1-FR-08 |

**Counts**: Open 1 · Awaiting PRD 1 · Resolved 4 · Routing pending 1 (GAP-INT-007). All three unresolved gaps record
precisely what is left unbuilt, and all three are carried into the Build and Test summary.

---

## 7. Extensions and Compliance at Requirements Analysis

**Enabled**: security baseline; platform invariants; PR checkpoint; QA test cases
(comprehensive); tickets as **GitHub issues on soorma-core** instead of JIRA.

**Tickets** (run-1 clarification Q3): at the end of Inception, before the PR checkpoint,
create one tracking issue for the initiative with one sub-issue per unit of work. No
markdown ticket file is written. The created issue numbers are recorded in
`aidlc-state.md`.

**PR checkpoint, QA test cases, tickets**: N/A at Requirements Analysis. They trigger at
the end of Inception and in Construction.

### Security baseline at this stage

| Rule | Status | Note |
|---|---|---|
| SECURITY-01, 02, 07 | N/A at RA | Infrastructure Design |
| SECURITY-03, 14 | Compliant | Required of every component (M1-NFR-06). Designed at NFR Design |
| SECURITY-04 | N/A | M1 serves no HTML (the portal is out of scope) |
| SECURITY-05 | Compliant | Input validation on every parameter, including the accepted permission identifiers (M1-FR-15) and the stamped/asserted partition (M1-FR-01) |
| SECURITY-06 | N/A at RA | No cloud IAM yet |
| SECURITY-08 | Compliant | Deny by default; authority evaluated at the perimeter for agents and humans (M1-FR-08, 09) |
| SECURITY-09, 13, 15 | Compliant | Fail closed is PF FR-012 (M1-FR-07). The rest are designed at NFR Design |
| SECURITY-10 | Compliant | M1-TECH-04 |
| SECURITY-11 | Compliant | Three unauthenticated surfaces, each bounded (M1-FR-05, 18); perimeter isolated in dedicated components (M1-TECH-03) |
| SECURITY-12 | **Compliant**, no longer partly blocked | The following requirements cover it. MFA for administrative accounts: P supported (M1-FR-17, RA run-2 Q1 A). Logout: ending one's own sign-in and credential (M1-FR-21, Q2 A). Brute force: M1-FR-18. Password policy, adaptive storage, session expiry and cookie attributes, and no hardcoded credentials: M1-NFR-09 |

**Security findings**: none blocking.

### Platform invariants at this stage

Scope is inherited from PF §15 @ `prd-platform-foundations-v1.3` and ID §15 @
`prd-identity-v1.0`. All eleven invariants are `Addressed` in both, and none is N/A. The
invariant text is identical at both tags. At Requirements Analysis the obligation is to
record scope, which is done.

| Code | Where it lands in these requirements |
|---|---|
| I1 Isolation | M1-FR-10, 11, 19, 20 (organization sign-in refused outside issuance; environment credential only in E) |
| I2 Perimeter enforcement | M1-FR-02 (raw calls), M1-FR-09 (every presenter × entry point) |
| I3 Portable credential | M1-FR-05, 10, 14 (configured, never inferred), 17 (enrollment single use), 20 |
| I4 Attribution recoverable | M1-FR-12, 16 (never pruned) |
| I5 Monotonic authority | M1-FR-08, 03 (ceiling, human-only class), 15 |
| I6 Two faces | M1-NFR-03, M1-NFR-08 |
| I7 Contract compatibility | M1-FR-02, M1-NFR-04, M1-TECH-02 |
| I8 Packaging rule | The *Absent from M1* list; the first grant and K + P in core (M1-FR-14, 17); no commercial capability is built |
| I9 Mechanism, not instance | No tenant schema or payload is inspected (M1-FR-01); tenant end users are not principals (ID §17) |
| I10 Runtime-later | M1-FR-05 (instance identifier asserted, not verified); M1-FR-14 (tenancy from configuration, not deployment) |
| I11 No technology selection | N/A in Construction by design. Section 5 is where technology is selected |

**Invariant findings**: none blocking.
