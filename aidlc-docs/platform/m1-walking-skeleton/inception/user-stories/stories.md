# User Stories: soorma-core M1 Walking Skeleton

**Depth**: minimal
**Organised as**: one user journey, in the order of the brief's *done when* items and ID §1's trace
**Built against**: PF @ `prd-platform-foundations-v1.3`, ID @ `prd-identity-v1.0`
**Requirements**: [requirements.md](../requirements/requirements.md) (run 2)
**Personas**: [personas.md](personas.md)

**The requirements govern.** A story organises what the requirements already specify. It
never widens or narrows them. Each acceptance criterion cites the M1-FR (or M1-NFR) it
exercises, and if wording differs, the requirement wins.

**Scope**: this repository's *Proves* column: *done when* 1, 4, 6, and 7, plus 2 and 3
**with raw calls and no SDK**. Item 5, trace emission, belongs to soorma-sdk and has no
story here.

**Boundary coverage** (plan Q4 A): items 6 and 7 are stories of their own. Every other
refusal is a **negative criterion**, marked ✗, in the story whose surface it guards.
O12 is one of them.

---

## Journey

The stories run in this order:

| Step | Story | Done when |
|---|---|---|
| 1 | US-01 Deployer configures the organization, environments, and first Admin | 1 |
| 2 | US-02 First Admin activates and signs in | 1 |
| 3 | US-03 First Admin obtains an environment credential | 1 |
| 4 | US-04 First Admin self-grants Developer permissions | 1 |
| 5 | US-05 Developer registers agents A and B | **1** |
| 6 | US-06 Developer issues a registration secret per agent | 1, 2 |
| 7 | US-07 Agent instances bootstrap and renew | **2** |
| 8 | US-08 A publishes, B receives | **3** |
| 9 | US-09 B's envelope carries identity context | **4** |
| 10 | US-10 A cross-environment publish is denied | **6** |
| 11 | US-11 A draft setting a platform-stamped field is rejected | **7** |
| — | US-12 A human ends a sign-in and changes their own material | — (SECURITY-12) |

---

## US-01: Deployer configures the organization, environments, and first Admin

**As the** deployer, **I want** to configure an organization, a project, and its
environments, and name an environment's first Admin, **so that** the platform has a trust
root without anyone holding a working credential.

**Done when**: 1 (ID §1 trace, steps 1 and 2) · **Personas**: Deployer; First Admin

**Acceptance criteria**
- [ ] Organization, project, and environment identity and membership come from
      configuration. Two environments, E and E2, are configured, because item 6 needs a
      second one (M1-FR-14, M1-FR-10)
- [ ] E's configuration names first Admin H. H is registered `pending` with single-use
      enrollment material, and granted `grant:human` and `human:manage` in E, with
      *granted-by* = configuration (M1-FR-14, M1-FR-12, M1-FR-16)
- [ ] H's identifier is unique within the organization and composed with it (M1-FR-16)
- [ ] ✗ Identity is never inferred from host, instance, cluster, or deployment (M1-FR-10)
- [ ] ✗ The deployer never holds a working credential. No credential or enrollment
      material sits in source or IaC templates (M1-FR-14, M1-NFR-09, M1-TECH-06)
- [ ] ✗ Re-applying configuration does not re-register a principal that already exists,
      so lost material is not recovered this way (M1-FR-14; *Absent from M1*)

---

## US-02: First Admin activates and signs in

**As the** first Admin, **I want** to authenticate with my enrollment material, set my own
K and P, and sign in at the organization level, **so that** I hold material only I know.

**Done when**: 1 (ID §1 trace, step 3) · **Persona**: First Admin

**Acceptance criteria**
- [ ] First authentication with the enrollment material replaces it with H's own K, and
      P where enrolled. H becomes `active` (M1-FR-17, M1-FR-16)
- [ ] Signing in with K, or with K + P once P is enrolled, yields a short-lived sign-in
      asserting subject, organization, time, and the classes used (M1-FR-19)
- [ ] Material is held and verified at the organization level only, and K only under an
      adaptive one-way algorithm (M1-FR-17, M1-NFR-09)
- [ ] Where the organization's configuration requires P, a human with no enrolled P can
      enroll it **without a sign-in, by presenting their current K** (M1-TECH-07,
      constraint 2)
- [ ] ✗ Reusing enrollment material is refused (M1-FR-17)
- [ ] ✗ A K shorter than 8 characters, or one on a breached-secret list, is refused
      (M1-NFR-09)
- [ ] ✗ Where P is required and not enrolled, sign-in is refused until it is (M1-FR-17)
- [ ] ✗ Sign-in and first authentication are unauthenticated surfaces. Failed attempts
      are recorded against the principal, and attempt volume per principal is bounded
      (M1-FR-18)

---

## US-03: First Admin obtains an environment credential

**As the** first Admin, **I want** to exchange my sign-in for a credential for environment
E, **so that** I can act in E and nowhere else.

**Done when**: 1 (ID §1 trace, step 4) · **Personas**: First Admin; Developer

**Acceptance criteria**
- [ ] E's credential issuance exchanges a live sign-in for a credential bound to E, for
      an `active` principal holding at least one grant in E (M1-FR-20)
- [ ] The credential is short-lived and renewable. It never outlives its sign-in, its
      revocation, or H's `active` state (M1-FR-20)
- [ ] ✗ The sign-in itself is refused at E's perimeter everywhere except at E's
      credential issuance (M1-FR-19, M1-FR-09)
- [ ] ✗ A `pending` principal, or one holding no grant in E, gets no credential
      (M1-FR-20)
- [ ] ✗ E's credential is refused in E2 (O4; M1-FR-20)
- [ ] ✗ Every human credential is refused at Event ingest (M1-FR-09)

---

## US-04: First Admin self-grants Developer permissions

**As the** first Admin, **I want** to grant myself `agent:register`, `event:publish`, and
`event:subscribe` in E, **so that** I can register and sponsor agents.

**Done when**: 1 (ID §1 trace, step 5) · **Personas**: First Admin → Developer

**Acceptance criteria**
- [ ] A holder of `grant:human` in E grants any accepted permission to any human,
      themselves included. Holding the permission is not required (M1-FR-15)
- [ ] Every self-grant is recorded, attributed to H and the credential presented, with no
      origin mode (M1-FR-15, M1-FR-12)
- [ ] The operation carries no envelope (M1-FR-01, M1-FR-09)
- [ ] ✗ **GAP-INT-006 work-around**: any identifier that is not plane-declared is rejected.
      This is a recorded delivery limit, not specified behaviour (M1-FR-15; soorma-prd#24)
- [ ] ✗ Without `grant:human` in E, the grant is denied (M1-FR-15, M1-FR-08)

---

## US-05: Developer registers agents A and B

**As a** Developer, **I want** to register two logical agents in E, each sponsored by me
with a standing set I hold, **so that** each has a durable identity with a recorded
ceiling.

**Done when**: **1** (ID §1 trace, steps 6 to 9) · **Persona**: Developer

**Acceptance criteria**
- [ ] H, presenting E's credential at the Gateway and holding `agent:register`, registers
      A and B with all eight PF §7a attributes. The sponsor reference names H (M1-FR-03,
      M1-FR-09)
- [ ] Each standing set lies within H's held set. The ceiling snapshot records that held
      set (M1-FR-03)
- [ ] A holds `event:publish` and B holds `event:subscribe`. **Both are registered with
      autonomy declared** (M1-FR-03, M1-FR-11; A-5)
- [ ] A re-broadening declaration within the standing set is accepted, possibly empty
      (M1-FR-03)
- [ ] Both registrations are attributed to H, with no origin mode and no envelope
      (M1-FR-12, M1-FR-01)
- [ ] ✗ A standing set exceeding what H holds is rejected (M1-FR-03)
- [ ] ✗ A standing set containing `grant:human`, `human:manage`, or `agent:delegate` is
      rejected whatever H holds (M1-FR-03)
- [ ] ✗ A re-broadening declaration exceeding the standing set is rejected (M1-FR-03)
- [ ] ✗ An identifier that is not plane-declared is rejected (M1-FR-15, M1-FR-03)
- [ ] ✗ Without `agent:register` in E, registration is denied (M1-FR-08)

---

## US-06: Developer issues a registration secret per agent

**As a** Developer, **I want** to issue a registration secret for each agent I sponsor,
**so that** I can provision it into my own compute.

**Done when**: 1, precondition for 2 · **Persona**: Developer

**Acceptance criteria**
- [ ] A holder of `agent:register` (Admin or the sponsoring Developer) issues one secret
      per registration (M1-FR-04)
- [ ] The secret records its issuer, H (M1-FR-04)
- [ ] Issuance is attributed to H (M1-FR-12)
- [ ] ✗ Without `agent:register` in E, issuance is denied (M1-FR-04, M1-FR-08)
- [ ] Rotation and retirement are absent (M1-FR-04)

---

## US-07: Agent instances bootstrap and renew

**As an** agent instance, **I want** to exchange my registration secret for a short-lived
credential, and renew it, with raw calls, **so that** I can act without holding durable
material beyond what I was provisioned.

**Done when**: **2**, by raw calls · **Persona**: Agent (instance)

**Acceptance criteria**
- [ ] A raw call, with no SDK, exchanges a locally-verified secret for a short-lived
      credential bound to the registration and E. The instance identifier is asserted and
      recorded, not verified (M1-FR-05, M1-FR-02)
- [ ] Renewal is never a weaker check than issuance. A lapsed instance re-bootstraps
      (M1-FR-06)
- [ ] The revocation state is read on every request. Past the propagation bound, the
      perimeter denies (M1-FR-07)
- [ ] ✗ Bootstrap is an unauthenticated surface. Failed attempts are recorded against the
      registration, and attempt volume per registration is bounded (M1-FR-05)
- [ ] ✗ A revoked agent credential is denied. In M1, revocation state is seeded through a
      test-only path not compiled into the product, because agent revocation initiation
      is absent (M1-FR-07)
- [ ] ✗ An agent credential presented beside a human's own credential is refused, at the
      Gateway and at Event ingest (M1-FR-09)

---

## US-08: A publishes, B receives

**As** agent A, **I want** to publish an event in E that agent B, subscribed in E,
receives, with raw calls, **so that** two agents communicate within one environment.

**Done when**: **3**, by raw calls · **Persona**: Agent (A, B)

**Acceptance criteria**
- [ ] B subscribes to E's namespace, and A publishes to it. B, a live subscriber, receives
      the event (M1-FR-11)
- [ ] A's publish and B's subscribe each carry an envelope stamped `autonomous` **by the
      perimeter**, derived from each registration's autonomy declaration. Effective
      authority is each agent's standing set (M1-FR-08, M1-FR-01)
- [ ] ✗ **GAP-INT-007 work-around**: a draft that asserts an origin mode is rejected,
      `autonomous` included. Accepting an asserted value later is additive (M1-FR-01)
- [ ] O1 to O12 are discharged independently at Event ingest. Neither entry point trusts
      the other (M1-FR-09)
- [ ] **GAP-INT-003 work-around**: delivery reaches live subscribers only, with no
      durability, ordering, or redelivery. The contract states that delivery semantics are
      unspecified, and it is pre-release (M1-FR-11, M1-FR-02)
- [ ] ✗ **O12**: an agent registered **without** declared autonomy, publishing or
      subscribing with no inbound context, is **denied** (M1-FR-08)
- [ ] ✗ Without `event:publish` (or `event:subscribe`) in E, the operation is denied
      (M1-FR-11, M1-FR-08)
- [ ] ✗ Delivery to B stops within the propagation bound once B's credential expires or
      is revoked (M1-FR-11)
- [ ] ✗ Every human credential is refused at Event ingest (M1-FR-09, M1-FR-11)
- [ ] ✗ A delegation credential, alone, beside another agent's credential, or beside the
      agent's own, is refused. In M1 none can be live (M1-FR-09; A-4)

---

## US-09: B's envelope carries identity context

**As** agent B, **I want** the envelope I receive to carry scope, origin, and an actor
chain the perimeter appended, **so that** I know who acted, in which environment, and
under what authority, without trusting A's claims.

**Done when**: **4** · **Persona**: Agent (B)

**Acceptance criteria**
- [ ] The envelope carries scope = E, origin `autonomous`, and the actor chain
      `[A's instance]`, appended by the perimeter, not by A (M1-FR-01, M1-FR-08)
- [ ] The trace context is carried as A asserted it, validated only as well-formed W3C
      Trace Context. soorma-core emits no spans (M1-FR-01, M1-TECH-05)
- [ ] There is no delegating-principal field, because no delegated chain exists in M1
      (M1-FR-01)
- [ ] Unknown fields are preserved and forwarded. Unknown enum values are non-fatal
      (M1-FR-01)
- [ ] **Re-broadening, the scenario M1's journey exercises**: B, triggered by A's event,
      calls `event:subscribe` **forwarding A's context**. A lacks `event:subscribe`, and B
      declared it. The request is allowed by re-broadening; the perimeter stamps the record
      naming B's hop; the record travels with the chain; a later hop does not inherit it
      (M1-FR-08, M1-FR-01)
- [ ] This is the **only** M1 scenario that makes re-broadening load-bearing. A triggered
      publish cannot, because every upstream publisher holds `event:publish`. Registration
      and secret issuance by an agent are absent (requirements, *Absent from M1*). The full
      PF §8b case table is verified at the authority-evaluation level, with constructed
      chains (M1-FR-08)
- [ ] ✗ A chain exceeding `maxChainDepth` is rejected (M1-FR-01)
- [ ] ✗ Without re-broadening load-bearing, no re-broadening record is stamped (M1-FR-01,
      M1-FR-08)

---

## US-10: A cross-environment publish is denied

**As the** platform, **I want** a publish made with a credential from another environment
denied, **so that** environments stay isolated.

**Done when**: **6** · **Persona**: Agent; also Developer for the human-credential case

**Acceptance criteria**
- [ ] ✗ A publish to E using an agent credential issued in E2 is denied at Event ingest
      (O4; M1-FR-09, M1-FR-10)
- [ ] ✗ A synchronous call to E through the Gateway using an agent credential issued in E2
      is denied there, independently (O4, O10; M1-FR-09)
- [ ] ✗ A control operation in E using a human environment credential issued by E2 is
      refused (O4; M1-FR-20)
- [ ] ✗ No verification material that can mint is shared between E and E2. Each holds
      verify-only material for the organization sign-in (M1-FR-10)
- [ ] ✗ Nothing is delivered across environments (M1-FR-11, M1-FR-10)

---

## US-11: A draft setting a platform-stamped field is rejected

**As the** platform, **I want** a draft envelope that sets any platform-stamped field
rejected, never overwritten, **so that** no tenant believes an asserted value took effect.

**Done when**: **7** · **Persona**: Agent

**Acceptance criteria**
- [ ] ✗ A draft setting any one of envelope version, scope, origin mode, delegating
      principal, actor chain, or re-broadening record is **rejected**, at the Gateway and
      at Event ingest, each independently (M1-FR-01, M1-FR-09)
- [ ] ✗ **Origin mode included at an autonomous first hop**: a draft asserting
      `autonomous` is rejected even though the registration declares autonomy. This is the
      GAP-INT-007 work-around, which takes PF §11 over the PF §8b row (M1-FR-01)
- [ ] ✗ The rejected value is never overwritten and forwarded (M1-FR-01)
- [ ] ✗ A malformed trace context is rejected (M1-FR-01)
- [ ] A draft declaring its client contract version and setting only trace context is
      accepted (M1-FR-01)

---

## US-12: A human ends a sign-in and changes their own material

**As a** human principal, **I want** to end my own sign-in and environment credential,
renew my sign-in, and change my own K and P, **so that** I can log out and keep my
material current without an Admin.

**Done when**: none. Required by SECURITY-12 (RA run-2 Q2 A) · **Personas**: First Admin
(any human)

**Acceptance criteria**
- [ ] Without any grant, a human renews and ends their own sign-in, and ends their own
      environment credential (M1-FR-21)
- [ ] Ending is the logout. The ended sign-in or credential is refused thereafter (O3;
      M1-FR-21, M1-FR-07, M1-NFR-09)
- [ ] A human changes their own K or P by presenting the current material (M1-FR-21)
- [ ] ✗ A change without the current material is refused (M1-FR-21)
- [ ] Acting on another human's credentials or material is absent (ID FR-012; M1-FR-21)

---

## Persona → Story Map

| Persona | Stories |
|---|---|
| Deployer (not a principal) | US-01 |
| First Admin of an environment | US-01, US-02, US-03, US-04, US-12 |
| Admin | US-04 (granting to humans) |
| Developer (H, by self-grant) | US-03, US-05, US-06, US-10 |
| Agent, logical and instance | US-07, US-08, US-09, US-10, US-11 |
| Operator, SME | None: no M1 grants, and no further humans are registered |
| Configured identity source | None: absent (ID FR-024) |

---

## Story → Requirement Traceability

| Story | Requirements exercised |
|---|---|
| US-01 | M1-FR-10, 12, 14, 16; M1-NFR-09; M1-TECH-06 |
| US-02 | M1-FR-16, 17, 18, 19; M1-NFR-09; M1-TECH-07 |
| US-03 | M1-FR-09, 19, 20 |
| US-04 | M1-FR-01, 08, 09, 12, 15 |
| US-05 | M1-FR-01, 03, 08, 09, 11, 12, 15 |
| US-06 | M1-FR-04, 08, 12 |
| US-07 | M1-FR-02, 05, 06, 07, 09 |
| US-08 | M1-FR-01, 02, 08, 09, 11 |
| US-09 | M1-FR-01, 08; M1-TECH-05 |
| US-10 | M1-FR-09, 10, 11, 20 |
| US-11 | M1-FR-01, 09 |
| US-12 | M1-FR-07, 21; M1-NFR-09 |

**Coverage check**: every M1-FR from 01 to 21 is exercised by at least one story, except
**M1-FR-13** (internal seam boundaries). M1-FR-13 shapes internal code and has no
behaviour a user observes. It is verified at Code Generation, and by the platform
invariants extension's seam-containment checks (I5, I8).

**Work-arounds and delivery limits, where they show**:

| Limit | Shows in |
|---|---|
| GAP-INT-003 (live subscribers only; pre-release contract) | US-08 |
| GAP-INT-006 (plane-declared identifiers only) | US-04, US-05 |
| GAP-INT-007 (origin stamped, never asserted, at every first hop) | US-08, US-11 |
| No recovery of a lost K or P (ID FR-012 absent) | US-01 |
| No delegation (ID FR-019 to FR-021 absent) | US-08 (refusal), US-09 (no delegating principal) |
| No agent revocation initiation (PF FR-011 deferred) | US-07 |

---

## INVEST Check

| Criterion | Holds because |
|---|---|
| **Independent** | Each story has its own surface and its own refusals. Journey order is a dependency of *setup*, not of design. US-07 to US-11 need only the registrations and secrets US-05 and US-06 create through the product's own operations; no story relies on a test-only fixture except US-07's agent revocation state (requirements §2). US-12 needs any active human |
| **Negotiable** | Stories state outcomes and cite requirements. How each is met is left to design (I11) |
| **Valuable** | Each story is a *done when* proof, a step in ID §1's trace, or a SECURITY-12 obligation |
| **Estimable** | Each is bounded by the M1-FRs it cites |
| **Small** | One surface or one proof each, 12 in all |
| **Testable** | Every criterion is an observable allow, deny, record, or field value |
