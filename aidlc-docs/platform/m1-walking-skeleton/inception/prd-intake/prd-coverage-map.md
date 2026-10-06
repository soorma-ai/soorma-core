# PRD Coverage Map

**PRD**: soorma-prd/aiprd-docs/platform-foundations/requirements/prd.md
**Version**: 1.1
**Approved version built against**: tag `prd-platform-foundations-v1.1` (commit `cef399f451e4a3cb0be5bed92586383cbf148afc`)
**Kind**: `plane` (inferred because the header declares no `Kind`; confirmed by the user at initiative start)
**Delivery scope**: soorma-prd/backlog/m1-walking-skeleton.md, *Repositories and sessions*, `soorma-core` column only
**Intake date**: 2026-10-05T02:26:06Z

> The PRD states the **target**. The slice brief decides only **delivery scope**: which
> FRs land in M1. Where the two appear to conflict, the PRD wins.

**Drift since the tag**: HEAD of `soorma-prd` differs from the tag only by a licence
identifier rename (`FSL-1.1-Apache-2.0` to `FSL-1.1-ALv2`, recorded in the PRD sign-off
as a naming correction). That has no build impact. All reads here are at the tag.

---

## M1 Scope for This Repository

From the brief's `soorma-core` column. Everything else in the brief is context.

| In scope (soorma-core) | Out of scope for M1 (absent, not simplified) |
|---|---|
| FR-001, FR-002, FR-003, FR-005, FR-006 (envelope) | FR-004 transition machinery (the version field itself is in) |
| FR-007, FR-016 (registration, sponsorship ceiling) | FR-008 rotation and retirement |
| FR-008 issuance only | FR-013 retention and pruning |
| FR-009, FR-027 (bootstrap and its abuse resistance) | FR-019 (obligations on Access Policy) |
| FR-010 (renewal) | FR-023 harness surface: owned by `soorma-sdk` |
| FR-012 (revocation read on every request) | FR-024 portal |
| FR-014, FR-015, FR-017, FR-018 (algebra, minimal model) | FR-025 read surface (recording is in) |
| FR-020 (O1 to O12 at every M1 entry point) | Everything commercial (§12) |
| FR-021, FR-022 (environment keying, configured identity) | |
| FR-025 attribution **recording** | |
| **Decide at intake**: FR-011 (revocation initiation), FR-026 (seams) | |

**Proves** (*done when*, from the brief): items 1, 4, 6, 7, plus 2 and 3 **with raw
calls and no SDK**. Item 5, trace emission, belongs to `soorma-sdk`.

**Owns**: the wire contract between an agent and the platform. The PRD fixes behaviour,
not wire format, so the format is a technology decision made once, here.

---

## Stage Coverage

| Inception Stage | Coverage | Source | Still Needed |
|---|---|---|---|
| Requirements Analysis | **Partial** | PRD §5 FRs, §6 to §11 for the in-scope FRs; brief for delivery scope | Routing of the specification gaps below; FR-011 and FR-026 decisions; extension opt-ins; confirming the technology classifications |
| User Stories | **Partial** | PRD §3 principals and grants (personas); brief *Done when* items (acceptance) | Assessed at the User Stories gate. Personas are settled and must not be re-derived |
| Application Design | **Partial** | PRD §2 seams; §11 *Gateway Exposure* (edge versus internal); §12 seam containment; §8b O10 | Components, the wire contract, and internal structure are AI-DLC's (I11). The PRD's placement constraints bind |
| Units Generation | **Partial** | PRD §9 and §10 split the owned operations by face; kind `plane` makes plane-face units available | Unit boundaries. A capability spanning both faces (for example revocation) becomes two units |

---

## L1 Domain Sources

Registered for the per-unit L1 Domain Coverage Gate. These are the most authoritative
L1 sources available and outrank anything re-derived.

| PRD Section | Content | Applies To |
|---|---|---|
| §7a *Platform-Owned Records* | Logical Agent Registration (8 required attributes; states `registered`, `suspended`, `retired`; retirement never deletes), Agent Credential, Revocation State (readable by no principal), Permission Grant (minimal model), Registration Secret | Registration, credential, revocation, grant, and secret handling |
| §7b *Envelope Fields*, *Compatibility Policy*, *Recoverability* | The seven fields with their requiredness and setter; the stamped/asserted partition; the client contract version on the draft; the two consumer obligations; I4 recoverability hops | Envelope stamping, validation, and transport |
| §6 *Tenancy and Isolation Specification* | 18 items keyed on environment (organization for human identity, platform for the envelope); four isolation assertions; five rejected cross-environment mechanisms | Every record, identifier, cache, and namespace |
| §8a *Platform-Resource Operations* | Required authority per operation (`agent:register`, `credential:revoke`, `agent:retire`, `grant:human`, `event:publish`, `event:subscribe`, `attribution:read`) | Authority evaluation at both entry points |
| §8b *Evaluation Mechanism* | Intersection formula; origin stamping table; declared autonomy against forwarded context; O1 to O12; L1 to L5 | The perimeter |
| §9, §10 | Data-plane and control-plane operations, failure modes, NFR profiles | Per-face units |
| §11 | Harness surface "perimeter validates independently" column; *What the SDK may not populate*; *Gateway Exposure* | The wire contract and the edge |
| §17 | Tenant-facing contract appendix | The wire contract's published form |
| FR-025 | Attribution record content: scope, actor, chain, origin, resolved sponsor | Attribution recording |

---

## Decisions Inherited (DO NOT re-derive)

| Decision | PRD § | Why it must not be re-derived |
|---|---|---|
| Seven envelope fields; six platform-stamped, trace context agent-asserted | §7b, FR-001 | Settled contract; one-way once tenants build against it |
| A draft setting a platform-stamped field is **rejected, not overwritten** | FR-002, §11 | Overwriting would leave a tenant believing their value took effect |
| The envelope is a **platform** contract, not environment-scoped | FR-003 | The one platform-scoped contract in the system |
| Unknown fields preserved and forwarded; unknown enum values non-fatal | FR-005 | Load-bearing for attribution in choreography |
| Full actor chain travels, most recent last, minimum length 1, perimeter-appended; `maxChainDepth` rejects | FR-006 | Predecessor-plus-reference was rejected (hot-path lookup) |
| Origin is platform-stamped where derivable; asserted `autonomous` with inbound context is rejected; no context and no declared autonomy is denied (O12) | FR-015, §8b | Closes escalation by omission |
| `effective = standing ∩ hop1 ∩ ... ∩ hopN`; an agent never acquires its delegator's authority | FR-014 | I5 |
| Sponsorship is a grant-time ceiling checked once at registration, with the snapshot recorded; the sponsor's live permissions are never consulted per request | FR-016 | A second principal on the hot path was rejected |
| Re-broadening is **declared at registration** and **recorded** on the envelope, never requested | FR-017 | A wire-requested re-broadening is authority by assertion |
| Minimal model: flat, opaque permission identifiers with set semantics, deny by default | FR-018 | Minimality is load-bearing for scope and packaging |
| Everything keys on environment; no global identifiers, no global revocation list, no shared verification material | FR-021, §6 | I1 |
| Environment identity is configured, never inferred (O11) | FR-022 | The one-instance-per-environment trap |
| A credential asserts registration, not code identity; the instance identifier is asserted, not verified | FR-009, §8b | I10 |
| Core bootstrap material is a **locally-verified registration secret** | §8b, OQ-11 | Clause 1: no external dependency |
| Revocation state is cached for at most a platform-set bound, then the perimeter **fails closed** | FR-012, OQ-12 | Fail-open and tenant-configurable bounds were rejected |
| The bootstrap exchange is the only unauthenticated surface; failed attempts are recorded per registration; attempt volume per registration is bounded | FR-027 | R-6 mitigation |
| **No entry point treats another's traffic as pre-validated** (O10) | §8b, FR-020 | The perimeter hole most likely to open in good faith |
| Seam containment: intersection, origin stamping, chain append and `maxChainDepth`, the ceiling check, and what a credential asserts stay in core behind no seam. The policy seam decides containment, never composition | §12 | A seam implementation must not be able to widen authority |
| What is edge-reachable (bootstrap, renewal, credentialed data-plane calls, control plane) versus internal (revocation read and store, snapshot resolution, verification material, effective-authority evaluation) | §11 | Placement decision, not technology |
| Licence split: the substrate is FSL; **the envelope's machine-readable definition and the seam interfaces are Apache 2.0** | §22 | Bears on how the wire contract is laid out in this repository |

---

## Handed to AI-DLC

Decisions the PRD leaves to technical design, each with the constraints it still imposes.

| Item | PRD § | Constraint the answer must satisfy | Decided in |
|---|---|---|---|
| Technology selection (language, datastore, transport, libraries) | I11 | Excluded from PRDs by design | NFR Requirements, per unit |
| **Wire contract**: protocol and encoding for both entry points | Brief; §7, §14 | One contract decided here and consumed by `soorma-sdk` at a pinned version. Raw callers reach identical enforcement (FR-023). Carries the client contract version. Evolves under the §7 policy | Application Design |
| Revocation propagation bound (value) | FR-012, §9 | Finite, published, platform-set, not tenant-configurable. It **is** the revocation-state cache TTL; past it, deny | NFR Requirements (data face) |
| Credential lifetime ("short-lived") | FR-009, FR-010 | Renewable; renewal never widens authority or outlives revocation. Choose it alongside the propagation bound | NFR Requirements (data face) |
| `maxChainDepth` value | FR-006, §7b | **Handed over implicitly**: the PRD names the bound as a contract obligation but gives no value. Published as part of envelope v1; lowering it later is breaking | Functional Design (envelope) |
| Bootstrap attempt bound: value and shape (rate limit versus cap) | FR-027 | Per registration; failures recorded against the registration. A hard cap lets an attacker who knows a registration lock out the real agent, so the shape is a real trade-off | NFR Requirements (data face) |
| Trace-context standard | FR-001, §7b, Decision 8 | An open standard; the perimeter validates well-formedness only | Functional Design |
| Credential format and per-environment verification material | §6 | No verification material shared across environments | NFR Design |
| Registration secret storage and verification | §7a, FR-008 | Locally verified; verification material internal to the substrate | NFR Design |
| Environment configuration mechanism | FR-022, O11 | Configured; never derived from host, instance, cluster, or deployment | Infrastructure Design |
| Repository layout of the Apache 2.0 parts | §22 | Envelope definition and seam interfaces are separately licensed Apache 2.0 | Application Design |
| Client contract deprecation window | §14 | Published, longer than zero, announced before it starts. **Not exercised in M1** (one contract version) | Recorded only |

---

## Deferred Questions Imported

**None.** All fourteen PRD open questions (OQ-1 to OQ-14) are `Answered` at the tag.
None is `Deferred` to engineering, and none is `Awaiting Answer`.

---

## Open Risks (owned elsewhere: context, not AI-DLC's to resolve)

| ID | Risk | Class | Owner | If the build touches it |
|---|---|---|---|---|
| R-1 | Access Policy's model may break L1 for hierarchical or wildcard permissions | Substantive | Access Policy PRD (OB-1) | **Not touched.** M1 builds the flat minimal model only |
| **R-2** | The first human Admin grant must be obtainable in core | Execution | Identity plane PRD (OB-3) | **Touched. M1 depends on it.** See GAP-INT-002 |
| R-3 | Registry & Schema may not express the envelope compatibility policy | Substantive | Registry & Schema PRD (OB-5) | **Not touched.** M1 ships envelope v1 only and builds no registry |
| R-4 | An agent that declares autonomy and serves requests keeps the widening path | Accepted | — | Context. M1's demo agent A declares autonomy, which is exactly this, and it is accepted |
| R-5 | Orphaned sponsorships are undetectable | Accepted | — | Context |
| R-6 | Bootstrap is the only unauthenticated surface | Mitigated here | — | Mitigated by FR-027, which is in M1 scope |
| R-7 | Seam implementations become sellable after licence conversion | Accepted | — | Context for the FR-026 decision |

---

## From PR Review (not in the PRD body)

| Point | Source | Effect |
|---|---|---|
| Single review, state `COMMENTED`, body "looks good". No inline threads | soorma-prd PR #4 (merge `b5527a8`) | None. The PRD body is the complete record |

---

## Build-Time Questions Classified at Intake

The brief requires anything M1 needs that no PRD specifies to be classified at intake,
as **technology** (decide, record, continue) or **specification** (raise, block). The
test used throughout comes from `prd-gap-classification.md`:

> *Would two competent engineers, given this PRD, be free to answer differently without
> either being wrong?* Yes means technology. No, because one answer is required but the
> PRD does not say which, means specification. Unsure means specification.

Some questions turned out to be **answered by the PRD** once read closely. These are
not gaps and need no classification. They are recorded so the reasoning is visible.

### Summary

| Ref | Question | Brief's watch item | Outcome | Owner | Blocks (done-when) | Routing |
|---|---|---|---|---|---|---|
| A-1 | Who is the human sponsor? | Q1 (Identity) | **Answered by PRD**: the registering Developer (§12 core single-actor form) | — | — | — |
| GAP-INT-005 (was T-1) | What is the sponsor's "grantable set"? | Q1 (Identity) | **Specification**: reclassified by the user at RA from technology (interpretation) | platform-foundations (FR-016) | Registration's ceiling check (already blocked by 001 and 002) | Raised: soorma-prd#14 (with 004). Blocking |
| GAP-INT-001 | How does a human principal exist and authenticate to the control plane? | Q1 (Identity) | **Specification** | Identity plane PRD (OB-4) | 1, then 2 to 7 transitively | Raised: soorma-prd#12. Blocking |
| GAP-INT-002 | How does the sponsor come to hold `agent:register`? (the first Admin grant) | Q1 (Identity) | **Specification** | Identity plane PRD (OB-3, R-2) | 1, then 2 to 7 transitively | Raised: soorma-prd#12 (with 001). Blocking |
| A-2 | Who creates topics? | Q2 (Event) | **Answered by PRD for M1**: publish and subscribe target *the environment's* namespace, which exists with the environment. No topics and no topic administration in M1 | — | — | Confirmed at RA |
| T-2 | How does a subscription respect credential expiry and revocation? | Q2 (Event) | **Technology, constrained**: delivery to a subscriber must stop within the propagation bound once its credential expires or is revoked (O2, O3, FR-012) | AI-DLC | — | Confirmed at RA |
| GAP-INT-003 | What delivery guarantees does a subscriber get? | Q2 (Event) | **Specification** | Event plane PRD (OB-6 context; §2 *What This Is Not*) | 3 | Raised: soorma-prd#13, **and worked around in M1** |
| T-3 | What does a trace span mean beyond the envelope field? | Q3 (Observability) | **Technology for soorma-core**: validate well-formedness against an open standard (proposed: W3C Trace Context), carry the value as asserted, emit no spans. Span semantics stay Observability's (OB-8) and are not needed by any item this repository proves | AI-DLC | — | Confirmed at RA |
| A-3 | Does B need discovery, or only a subscription? | Q4 (Registry & Schema) | **Answered by PRD**: only a subscription. §8a has no discovery operation; what B listens for is the tenant's design (I9). OB-5 concerns the envelope's compatibility policy, which M1 does not engage | — | — | Confirmed at RA |
| GAP-INT-004 | When is re-broadening exercised, and how does it compose with the intersection? | **Not on the brief's list** | **Specification** | platform-foundations itself (FR-017, I5) | None directly; FR-017 is in scope | Raised: soorma-prd#14, **and worked around in M1** |
| E-1 | §17 says "Five are platform-stamped" but lists six; §4 says "Thirteen" operations where §8a and §12 count sixteen | Not on the brief's list | **Erratum, no build impact**: the normative tables (§7b, §8a) are unambiguous | soorma-prd | — | Raised: soorma-prd#15 (non-blocking) |

**Bottom line for the §19 claim** ("M1's builders need invent no architectural
decision"): it **does not hold**. Five specification gaps were found (four at intake,
plus T-1, which the user reclassified at RA). Two of them
(GAP-INT-001, GAP-INT-002) sit at the root of the outcome. Every *done when* item needs a
registered agent, registration needs an authenticated human holding `agent:register`,
and the PRD assigns both of those to a PRD that does not exist yet. The PRD declares
this dependency itself, in the §12 sufficiency bar (step 1) and as R-2. What the brief
did not anticipate is that it blocks M1, not just the sufficiency bar.

---

### A-1 and T-1 (now GAP-INT-005): the sponsor, and the sponsor's grantable set

> **Reclassified at Requirements Analysis.** The user reclassified T-1 as
> **specification** (RA Q6). It is now **GAP-INT-005**: owned by platform-foundations
> (FR-016), status `Open`, raised on soorma-prd#14. Its full entry follows this section. The intake reasoning is
> kept below so the change of classification is visible.

**A-1**: in core's single-actor form, "the registering Developer is the sponsor; the
ceiling snapshot is taken and the check passes trivially" (§12 *Core Single-Actor
Form*). The sponsor is therefore a human principal with the Developer role, and the
sponsor reference on the registration (§7a) points at an organization-scoped human
principal (§6).

**T-1**: FR-016 requires the granted standing set to be a subset of "the sponsor's
grantable set at the moment of granting", but no section defines *grantable* separately
from *held*. Under the minimal model (FR-018) a grant record carries only principal,
environment, permission set, granted-at, and granted-by. There is no grant-option
attribute to derive anything else from, and adding one would change a core record.
The only answer constructible from the specified records is **the sponsor's held
permission set in that environment**, so this is an interpretation rather than an
invention. It is classified as technology, but flagged: if the product team intends a
separate grantable set, it is specification.

---

### GAP-INT-005: Meaning of the sponsor's "grantable set" (reclassified from T-1)

**Raised**: 2026-10-06T23:06:23Z
**Stage**: Requirements Analysis (reclassified by the user at RA Q6, from technology to specification)
**PRD**: soorma-prd/aiprd-docs/platform-foundations/requirements/prd.md
**Built against**: `prd-platform-foundations-v1.1`
**PRD section**: FR-016; §8a (*Grant standing permissions at registration*; *Grant permissions to a human principal*); §10 *Failure Modes*; §12 *Core Single-Actor Form*; FR-018

#### What the build needs
The registration ceiling check: the granted standing set must be a subset of "the
sponsor's grantable set at the moment of granting", and that set is snapshotted on the
registration record. The build needs to know what a principal's *grantable* set is.
The same term bounds an Admin's `grant:human` (§8a).

#### What the PRD says
"Grantable set" is used in FR-016, §8a, §10, and §11, but never defined, and never
distinguished from the principal's *held* permission set. The minimal model's grant
record (FR-018, §7a) carries principal, environment, permission set, granted-at, and
granted-by, with no grant-option or delegable attribute. §12 says that under
self-sponsorship "the check passes trivially".

#### Why this is specification, not technology
At intake, AI-DLC read it as *grantable = held*, the only reading constructible from
the specified records. The user reclassified it, and the reading is open to question:
- "passes trivially" under self-sponsorship fits *grantable* being something broader
  than *held*
- A separate grantable set would add an attribute to a core record, which is a
  packaging decision (I8)

It is an authority rule with an unspecified case. It bounds escalation by sponsorship
(I5), and it decides what the ceiling snapshot contains, which I4 makes auditable.

#### Options considered
1. **Grantable = held**: the sponsor's held permission set in the environment. No
   record change. A Developer must hold `event:publish` to grant it to an agent
2. **A separate grantable set**: grants carry a grant-option (or a distinct
   grantable permission set). This changes the FR-018 grant record and the §7a
   snapshot's meaning
3. **Grantable = held, minus administrative permissions** (for example, `grant:human`
   can never be granted onward to an agent). This is a narrower rule layered on
   option 1

#### Blocked
Registration's ceiling check (M1-FR-03), which is already blocked by GAP-INT-001 and 002
(soorma-prd#12). It raises nothing new for the *done when* items.

**Status**: `Open`. Raised on [soorma-prd#14](https://github.com/soorma-ai/soorma-prd/issues/14) alongside GAP-INT-004, the other platform-foundations authority-rule gap (routing confirmed by the user). **Blocking** the ceiling check.

---

### GAP-INT-001: Human principal identity and control-plane authentication

**Raised**: 2026-10-05T02:26:06Z
**Stage**: PRD Intake (classified for the brief's *Questions to watch*)
**PRD**: soorma-prd/aiprd-docs/platform-foundations/requirements/prd.md
**Built against**: `prd-platform-foundations-v1.1`
**PRD section**: §7a ("Not owned here: human principal identity records"), §2 *What This Is Not*, §13 (Identity row), O1

#### What the build needs
Registration (FR-007) and secret issuance (FR-008) are control-plane operations invoked
by a human, through the Gateway, under O1 to O12. O1 requires a credential that is
presented and well-formed. The build needs to know what a human principal is in core
and what credential a human presents to the control-plane face.

#### What the PRD says
Human principal identity records, principal registration, human lifecycle, and IdP
federation are assigned to the Identity plane PRD (CF-1, §13, OB-4). The PRD specifies
agent credentials only. Nothing specifies a human credential or how one is obtained.

#### Why this is specification, not technology
Whatever a human presents to the control plane is part of the wire contract that
tenants and the portal build against, so it is one-way. The brief forbids stand-ins on
any public surface. The answer also decides the Identity plane's core shape (for example
local accounts versus federation-first), which the PRD explicitly assigns elsewhere.
Two engineers would answer differently, and the difference is a product decision.

#### Options considered
1. **Raise against soorma-prd; an Identity plane PRD (or a narrow core slice of it)
   specifies human principals and control-plane authentication.** M1 registration waits
   for it. This is the clean route
2. **Resolve here**: the user decides a minimal human principal and credential for core.
   This pre-empts the Identity PRD, and the decision becomes the contract
3. **Work around**: build all agent-side behaviour, and create registrations and secrets
   through a non-public operator seeding path (deployment configuration, no API), with
   the sponsor reference naming a configured principal identifier. This proves *done
   when* 2, 3, 4, 6, and 7 with raw calls, but proves item 1 only partly (the record
   exists; the FR-007 operation and its perimeter path are not exercised). It must be
   recorded as a technology stand-in and kept off every public surface

#### Blocked
Done-when 1 directly; 2 to 7 transitively, because they all need a registered agent
with an issued secret. Units: control-face registration and secret issuance.

**Status**: `Open`. Raised as [soorma-prd#12](https://github.com/soorma-ai/soorma-prd/issues/12) (routing A, RA Q2). **Blocking.**

---

### GAP-INT-002: The first human grant, and how a sponsor obtains `agent:register`

**Raised**: 2026-10-05T02:26:06Z
**Stage**: PRD Intake
**PRD**: soorma-prd/aiprd-docs/platform-foundations/requirements/prd.md
**Built against**: `prd-platform-foundations-v1.1`
**PRD section**: §8a (`grant:human` is Admin only), §12 *Sufficiency Bar* step 1, §19 R-2, §13 (Identity row)

#### What the build needs
Registering an agent requires `agent:register` in the environment (§8a). Grants to
humans are made by an Admin (`grant:human`), so the first Admin's own grant must come
from somewhere. The build needs to know how the first grant in an environment is
established.

#### What the PRD says
"Establishing the first human Admin grant is human principal lifecycle, out of scope
at CF-1 and **owed by the Identity plane PRD**" (§12). It is risk R-2, class *Execution*,
status `Open`, and obligation OB-3.

#### Why this is specification, not technology
`prd-gap-classification.md` is explicit: if a unit's work depends on an open risk
resolving one way, that is a specification gap, and it must never be assumed to resolve
favourably. The PRD also states that the answer must land in core or the sufficiency
bar fails, which makes it a packaging decision (I8) as well as an identity one.

#### Options considered
1. **Raise with GAP-INT-001**. Both are the Identity plane's, and one PRD likely
   discharges both OB-3 and OB-4
2. **Resolve here**: for example, the first Admin grant is established by environment
   configuration at deployment time. That is plausible, but it is an irreversible core
   assignment the PRD reserves for the Identity PRD
3. **Work around**: the same seeding path as GAP-INT-001 option 3, which seeds the grant
   alongside the registrations

#### Blocked
Same as GAP-INT-001.

**Status**: `Open`. Raised with GAP-INT-001 as [soorma-prd#12](https://github.com/soorma-ai/soorma-prd/issues/12) (routing A, RA Q3). **Blocking.**

---

### A-2 and T-2: topics, and subscription lifetime

**A-2**: §8a specifies "Publish to an event namespace: `event:publish` in **that
environment's** namespace", and §6 keys the event namespace on environment. The
namespace exists by virtue of the environment, so nobody creates it. M1 builds
publish and subscribe on that namespace exactly as specified. Topics, sub-namespaces,
and topic administration are Event's (§2) and are **absent** in M1. Adding them later is
additive.

*Residual*: whole-namespace subscription becomes a behaviour the future Event PRD
inherits. If you read "event namespaces" (plural, §17) as several per environment,
this becomes specification.

**T-2**: a subscription outlives a single request. O2 and O3 apply to every request, and
FR-012 promises that revocation takes effect within the published bound. The constraint
is therefore that, whatever the subscription mechanism, **delivery to a subscriber must
stop within the propagation bound once its credential expires or is revoked**, and O4
applies at subscribe time. How that is achieved is technology.

---

### GAP-INT-003: Event delivery guarantees

**Raised**: 2026-10-05T02:26:06Z
**Stage**: PRD Intake
**PRD**: soorma-prd/aiprd-docs/platform-foundations/requirements/prd.md
**Built against**: `prd-platform-foundations-v1.1`
**PRD section**: §2 *What This Is Not* ("Event delivery semantics, subscription mechanics, topic administration" belong to Event), §13 (Event row), OB-6

#### What the build needs
A delivery semantic for B's subscription: at-most-once or at-least-once, whether a
subscriber that is offline at publish time ever receives the event, ordering, and
acknowledgement.

#### What the PRD says
Nothing, by design. It assigns these to the Event plane PRD.

#### Why this is specification, not technology
The guarantee changes what every consumer must build. Moving from at-most-once to
at-least-once later introduces duplicates, which forces idempotency on tenants who never
needed it, so it is a breaking change in consumer obligations. Whichever guarantee M1
ships becomes the contract, which the brief forbids on a public surface. Two engineers
would choose differently, and the choice binds tenants.

#### Options considered
1. **Raise against soorma-prd** for the Event plane PRD. Done-when 3 waits
2. **Resolve here**: the user picks the guarantee now, pre-empting the Event PRD
3. **Work around**: live subscribers only, with no durability, ordering, or redelivery,
   and the wire contract **states explicitly that delivery semantics are unspecified at
   this contract version**. This proves done-when 3. The cost is that observed behaviour
   becomes relied upon whatever the contract says, so it is only safe if the M1 wire
   contract is published as pre-release

#### Blocked
Done-when 3 (and the delivery half of 4). Units: event transport (data face).

**Status**: `Open`. Raised as [soorma-prd#13](https://github.com/soorma-ai/soorma-prd/issues/13), **and worked around in M1** with option 3 (routing E, RA Q4): live subscribers only, delivery semantics stated as unspecified, and the M1 wire contract published as pre-release.

---

### T-3: trace context in soorma-core

The PRD reserves the field and requires it (§7b). It is agent-asserted and validated by
the platform "for well-formedness against an open standard" only. Semantics, sampling,
and ingest are Observability's (OB-8, Decision 8, which deliberately left the standard
unnamed under I11). Choosing the standard is therefore technology. The proposal is
**W3C Trace Context** (`traceparent` required, `tracestate` optional), confirmed in
Functional Design.

soorma-core **emits no spans in M1**. A perimeter-emitted span would be a stand-in for
Observability's span semantics, and it would also require the platform to rewrite an
agent-asserted field. Done-when 5 ("a trace is emitted") belongs to `soorma-sdk`, and
that session must classify span semantics for itself.

---

### GAP-INT-004: Re-broadening evaluation (not on the brief's watch list)

**Raised**: 2026-10-05T02:26:06Z
**Stage**: PRD Intake
**PRD**: soorma-prd/aiprd-docs/platform-foundations/requirements/prd.md
**Built against**: `prd-platform-foundations-v1.1`
**PRD section**: FR-017, §7a (*Re-broadening declaration*), §7b (*Re-broadening record*), P4 *Chain narrowing and re-broadening*; brief *Identity Model*; invariant I5

#### What the build needs
FR-017 is in M1 scope. The perimeter must evaluate re-broadening against the
registration's declaration, and stamp the re-broadening record when it is exercised.
The build needs two rules: **when** a declaring agent's re-broadening is exercised, and
**how** it composes with `standing ∩ hop1 ∩ ... ∩ hopN`.

#### What the PRD says
Where re-broadening is declared (registration), that the envelope records it at a named
hop, that it is never requested over the wire, and that an agent-set re-broadening field
is rejected. The platform brief and invariant I5 say only "re-broadening must be
explicitly declared, never implicit". **No layer states the evaluation rule.**

#### Why this is specification, not technology
It is an authority rule with an unspecified case, which is listed as specification.
Plausible readings differ in effective authority. Two examples: at the declaring hop
effective authority becomes `standing ∩ declared` and drops upstream terms, or it
becomes `(chain intersection) ∪ (standing ∩ declared)`. Re-broadening could be exercised
automatically at every hop by a declaring agent, or only when the narrowed set is
insufficient for the operation. Each reading gives a different answer to "may this
request proceed?", which is I5's core question.

#### Options considered
1. **Raise against soorma-prd** for a platform-foundations amendment (v1.2)
2. **Resolve here**: the user supplies the rule
3. **Work around**: M1 accepts only a re-broadening declaration of *none*, so
   registrations declaring any re-broadening are rejected until the rule is specified.
   The perimeter never stamps the conditional record, and still rejects an agent-set
   one (FR-017, O5). Accepting more declaration values later is additive. This does not
   affect the *done when* items. **Recommended in combination with option 1**

#### Blocked
No *done when* item. FR-017's evaluation half is unbuildable as specified.

**Status**: `Open`. Raised as [soorma-prd#14](https://github.com/soorma-ai/soorma-prd/issues/14), **and worked around in M1** with option 3 (routing E, RA Q5): only a declaration of *none* is accepted.

---

### E-1: Errata (no build impact)

- §17 *Envelope*: "Five are **platform-stamped** ... envelope version, scope, origin
  mode, delegating principal, actor chain, and the re-broadening record" lists six. The
  §7b table is normative and unambiguous: six platform-stamped fields and one
  agent-asserted field
- §4, P4 row: "Thirteen platform-resource operations", whereas §8a lists sixteen and §12
  counts sixteen

Neither changes what is built. They are worth a non-blocking issue on soorma-prd.
