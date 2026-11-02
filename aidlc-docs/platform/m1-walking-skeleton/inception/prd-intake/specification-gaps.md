# Specification Gaps Found at Intake

**Initiative**: soorma-core M1 walking skeleton
**Register**: `## PRD Specification Gaps` in [aidlc-state.md](../../aidlc-state.md)
**Classification and routing rules**: soorma-aidlc `inception/prd-gap-classification.md`

GAP-INT-001 to GAP-INT-005 were raised at intake run 1, against `platform-foundations`
(PF) @ `prd-platform-foundations-v1.1`. Run 1 recorded them in the coverage map. They
were **moved here verbatim** at re-intake run 2 (`prd-intake.md` Step 9.5). Each entry is
followed by its run-2 re-assessment, which records its current status and
`Resolved by`. The run-1 `**Status**:` line inside each entry is historical and is kept
unchanged.

**ID note**: entries dated before run 2 use unqualified PRD IDs. Each of them refers to
**PF** (`platform-foundations`). Run-2 text qualifies every PRD-scoped ID by its key: PF, or
ID for `identity`.

| ID | Status (run 2) | Raised against | Resolved by | Issue |
|---|---|---|---|---|
| [GAP-INT-001](#gap-int-001-human-principal-identity-and-control-plane-authentication) | Resolved — answered elsewhere | PF @ `prd-platform-foundations-v1.1` | ID @ `prd-identity-v1.0` FR-001, FR-006, FR-009, FR-010, FR-022 | soorma-prd#12 (closed) |
| [GAP-INT-002](#gap-int-002-the-first-human-grant-and-how-a-sponsor-obtains-agentregister) | Resolved — answered elsewhere | PF @ `prd-platform-foundations-v1.1` | ID @ `prd-identity-v1.0` FR-004, FR-007, FR-015 | soorma-prd#12 (closed) |
| [GAP-INT-003](#gap-int-003-event-delivery-guarantees) | **Awaiting PRD: Event**; worked around in M1 | PF @ `prd-platform-foundations-v1.1` | — | soorma-prd#13 (open) |
| [GAP-INT-004](#gap-int-004-re-broadening-evaluation-not-on-the-briefs-watch-list) | Resolved — PRD amended | PF @ `prd-platform-foundations-v1.1` | PF @ `prd-platform-foundations-v1.3` FR-017, §7a, §7b, §8b *Re-broadening* (introduced at v1.2, §23) | soorma-prd#14 (closed) |
| [GAP-INT-005](#gap-int-005-meaning-of-the-sponsors-grantable-set-reclassified-from-t-1) | Resolved — PRD amended | PF @ `prd-platform-foundations-v1.1` | PF @ `prd-platform-foundations-v1.3` FR-016, §8b *Sponsorship* (v1.2, §23); the `grant:human` half by ID @ `prd-identity-v1.0` FR-015 | soorma-prd#14 (closed); re-routed half on #12 |
| [GAP-INT-006](#gap-int-006-which-permissions-are-valid-in-an-environment) | **Open**; worked around in M1 (plane-declared identifiers only) | ID @ `prd-identity-v1.0` | — | soorma-prd#24 (open) |
| [GAP-INT-007](#gap-int-007-origin-at-an-autonomous-first-hop-agent-asserted-or-platform-stamped) | **Open** (found at User Stories); worked around (reject and stamp) | PF @ `prd-platform-foundations-v1.3` | — | soorma-prd#25 (open) |

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

#### Re-intake run 2 (2026-11-01)

**Raised against**: PF, soorma-prd/aiprd-docs/platform-foundations/requirements/prd.md @ `prd-platform-foundations-v1.1` (unchanged)
**Owner**: Identity plane PRD (OB-4)
**Issue**: [soorma-prd#12](https://github.com/soorma-ai/soorma-prd/issues/12), closed 2026-10-26 by soorma-prd PR #21
**Resolved by**: ID @ `prd-identity-v1.0`. FR-001 (the human principal), FR-006 (material: K, or K + P), FR-009 (organization sign-in), FR-010 (environment credential), FR-022 (human credentials at the perimeter). PF @ `prd-platform-foundations-v1.3` FR-001 (a direct human operation carries no envelope)

**Confirmed against *What the build needs***: *what a human principal is in core*. ID
FR-001 makes it organization-scoped, with states `pending`, `active`, `suspended`, and
`deactivated`, and never pruned. *What credential a human presents to the control-plane
face*. ID FR-010 says it is an environment credential issued by E and accepted only in E,
obtained from an organization sign-in (ID FR-009). ID FR-022 says the Gateway validates
it against O1 to O4 and O8 to O11. The section answers what the build needs, so this is
not a closed issue taken on trust.

**Effect on M1**: the block on registration (PF FR-007) and secret issuance (PF FR-008)
is lifted. The human side becomes new scope from the brief (ID FR-001, FR-004,
FR-006 to FR-010, FR-013, FR-015, FR-022, FR-023).

**Status**: `Resolved — answered elsewhere`

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

#### Re-intake run 2 (2026-11-01)

**Raised against**: PF @ `prd-platform-foundations-v1.1` (unchanged)
**Owner**: Identity plane PRD (OB-3, PF R-2)
**Issue**: [soorma-prd#12](https://github.com/soorma-ai/soorma-prd/issues/12), closed 2026-10-26 by soorma-prd PR #21
**Resolved by**: ID @ `prd-identity-v1.0` FR-004 (an environment's configuration names its first Admin and grants `grant:human` and `human:manage`), FR-007 (single-use enrollment material for the configured first Admin), FR-015 (the `grant:human` ceiling, through which the first Admin self-grants `agent:register`). PF @ `prd-platform-foundations-v1.3` §19 R-2 `Discharged`; §12 *Sufficiency Bar* step 1, discharged

**Confirmed against *What the build needs***: *how the first grant in an environment is
established*. It is established by configuration, which ID FR-004 names as the trust
root. How the sponsor then holds `agent:register` is answered by ID FR-015 (self-grant,
recorded). ID §1 *Success-Claim Traces* walks M1 *done when* 1 through both steps with no
exception.

**Effect on M1**: the block on registration is lifted. Option 2 of this entry was a
configuration-based first grant, which run 1 declined to adopt as a stand-in. It is now
what ID FR-004 specifies, so building it is not a stand-in.

**Status**: `Resolved — answered elsewhere`

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

#### Re-intake run 2 (2026-11-01)

**Raised against**: PF @ `prd-platform-foundations-v1.1` (unchanged)
**Owner**: Event plane PRD (OB-6), which has no approved PRD
**Issue**: [soorma-prd#13](https://github.com/soorma-ai/soorma-prd/issues/13), **open**
**Resolved by**: —

**Status correction (Step 9.1)**: run 1 recorded this gap as `Open`. The plane that owns
the answer has no approved PRD, so the correct status is `Awaiting PRD: Event`. This is a
status correction, not a resolution.

**Re-assessed at the new tags (Step 9.4)**: **not answered**. PF @ v1.3 still assigns
delivery semantics to Event (§2 *What This Is Not*; §19 *Success-Claim Trace* step 8).
ID @ v1.0 lists it as Event's (§2 *What This Is Not*: "Event delivery semantics, Event,
#13"). The work-around chosen at run 1 (RA Q4, routing E) still holds. Delivery reaches
live subscribers only, the contract states that delivery semantics are unspecified, and
the M1 wire contract is published as pre-release.

**Still missing**: everything listed under *What the build needs*. That is, at-most-once
or at-least-once delivery, whether an offline subscriber ever receives an event,
ordering, and acknowledgement.

**Status**: `Awaiting PRD: Event`. Worked around in M1, as above

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

#### Re-intake run 2 (2026-11-01)

**Raised against**: PF @ `prd-platform-foundations-v1.1` (unchanged)
**Owner**: platform-foundations
**Issue**: [soorma-prd#14](https://github.com/soorma-ai/soorma-prd/issues/14), closed 2026-10-07 by soorma-prd PR #19
**Resolved by**: PF @ `prd-platform-foundations-v1.3` FR-017; §7a *Re-broadening declaration*; §7b *Re-broadening record*; §8b *Re-broadening*, with its case table; §20 Decision 16. Introduced at v1.2 (§23) and unchanged at v1.3

**Confirmed against *What the build needs***:
- *When* re-broadening is exercised: only when it is **load-bearing**, meaning the
  request would be denied without it and allowed with it
- *How* it composes: at the declaring hop,
  `standing ∩ authority(delegating principal) ∩ (authority(upstream agent hops) ∪ declared)`.
  The declared set lies within the standing set, and a registration declaring more is
  rejected. The rule is **local** to the declaring hop. The record is stamped only when
  re-broadening is load-bearing, and it travels with the chain
- In autonomous origin the delegating-principal term reads *yes* (§8b, note under the
  case table)

**Effect on M1: the work-around comes out** (Step 9.4.5). Run 1 accepted only a
declaration of *none* (RA Q5, routing E). M1 now builds PF FR-017 as stated:
- a declaration is any set within the standing set
- the perimeter evaluates the composition and stamps the record when re-broadening is
  load-bearing
- an agent-set record is still rejected

In M1 every chain starts autonomous (see coverage map, A-5), so re-broadening is
exercised at an event-triggered hop whose upstream agent lacks a permission the
declaring agent declared. This re-opens M1-FR-03 and M1-FR-08 at Requirements Analysis.

**Status**: `Resolved — PRD amended`

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

#### Re-intake run 2 (2026-11-01)

**Raised against**: PF @ `prd-platform-foundations-v1.1` (unchanged)
**Owner**: platform-foundations for sponsorship. The `grant:human` ceiling was
**re-routed** by PF v1.2 (§23) to the Identity plane PRD (OB-13, soorma-prd#12)
**Issue**: [soorma-prd#14](https://github.com/soorma-ai/soorma-prd/issues/14), closed 2026-10-07 by PR #19. The re-routed half is on [soorma-prd#12](https://github.com/soorma-ai/soorma-prd/issues/12), closed 2026-10-26 by PR #21
**Resolved by**: PF @ `prd-platform-foundations-v1.3` FR-016 and §8b *Sponsorship*: grantable = held, plus the human-only class (introduced at v1.2). ID @ `prd-identity-v1.0` FR-015: the `grant:human` ceiling is any permission valid in E, self-grants recorded, and it never requires the Admin to hold what they grant. ID FR-013 adds `human:manage` and `agent:delegate` to the human-only class

**Confirmed against *What the build needs***: *what a principal's grantable set is*, for
the registration ceiling check. It is the sponsor's **held** set in the environment at
the moment of granting, which is option 1 of this entry plus a human-only exclusion.
That combination comes close to option 3. The snapshot records that held set. The same
term bounding `grant:human` is answered by ID FR-015. **One residue is not resolved by
these sections.** ID FR-015's own term *valid in E* is undefined. It is raised separately
as GAP-INT-006 below, and it does not re-open this gap.

**Effect on M1**: the ceiling check is unblocked and built as stated. A standing set
holding any permission in the human-only class (`grant:human`, `human:manage`,
`agent:delegate`) is rejected whatever the sponsor holds.

**Status**: `Resolved — PRD amended`

---

### GAP-INT-006: Which permissions are valid in an environment

**Raised**: 2026-11-01T21:12:26Z
**Stage**: PRD Intake, re-intake run 2 (Step 5.6, full intake of ID)
**Raised against**: ID, soorma-prd/aiprd-docs/identity/requirements/prd.md @ `prd-identity-v1.0`
**PRD section**: ID FR-015; ID §8a *Grant to a human in E*; ID §17 *Policy Grammar and Authority Evaluation*; ID §18 *Grantable set*. It bears on PF FR-016 and FR-018, PF §8a's preamble, and PF P4 *Supplied by the tenant*
**Owner**: Identity, for the term in FR-015. PF FR-018 bears on it, through the minimal model. Access Policy, which may extend the model (OB-2), has no PRD
**Unit**: (pre-unit), until Units Generation assigns it
**Issue**: [soorma-prd#24](https://github.com/soorma-ai/soorma-prd/issues/24), opened 2026-11-01 with this entry verbatim, pinned to `4693138`
**Resolved by**: —

#### What the build needs
Granting to a human (ID FR-015; M1 *done when* 1, step 5 of ID §1's trace) must decide
which permission identifiers a grant request may carry, and must reject the others. The
same set bounds every human's held set. Because grantable = held (PF FR-016), it also
bounds every agent's standing set. The answer is published in the wire contract, which
M1 owns and which is one-way once tenants build against it. The build needs to know
which identifiers are *valid in E*.

#### What the PRD says
- ID FR-015: "A holder of `grant:human` in E may grant **any permission valid in E**".
  ID §18 defines the `grant:human` grantable set as "every permission valid in the
  environment", which is circular. **The PRD body does not define *valid in E*.**
- ID plane-analysis P4-OQ-1, in its *Description* (context, not the answer): "The
  permissions valid in an environment are those plane PRDs declare, plus whatever Access
  Policy's model adds (OB-2)."
- PF FR-018: core's baseline is "flat, **opaque** permission identifiers with set
  semantics". PF §8a: "Tenant business operations never appear here. **Each tenant
  defines its own**, expressed through the machinery in 8b." PF P4 *Supplied by the
  tenant*: "which of their own business operations their agents may perform … expressed
  through this machinery, never enumerated here".

#### Why this is specification, not technology
FR-015 uses the term *valid in E* without defining it. Giving meaning to a term the PRD
uses but does not define is specification, even where one reading looks constructible.
The two available texts point in different directions. The plane-analysis description
reads as a closed set: what plane PRDs declare, plus Access Policy. PF's minimal model
and §8a read as open: tenants define their own identifiers through core's machinery,
with no Access Policy in core. It is also an authority rule. It decides what can ever
enter a human's or an agent's authority, which is I5. Two competent engineers would
choose differently, and the choice binds tenants.

#### Options considered
1. **Plane-declared only.** At these tags the set is PF's `agent:register`,
   `credential:revoke`, `agent:retire`, `grant:human`, `event:publish`,
   `event:subscribe`, and `attribution:read`, plus ID's `human:manage` and
   `agent:delegate`. Tenant-defined permissions arrive only with Access Policy. This
   matches the P4-OQ-1 description. The cost is that core alone can express no tenant
   business permission through the minimal model, which sits uneasily with PF §8a and P4
2. **Any well-formed opaque identifier.** Validity is syntactic, and tenants name their
   own permissions. This matches PF FR-018 and §8a. The cost is that a typo is a valid
   grant. It also needs a naming rule, so that a tenant identifier cannot collide with a
   permission a later plane PRD declares. The human-only class is matched explicitly
   either way (OB-16)
3. **Plane-declared, plus tenant permissions declared per environment**, through
   environment configuration or an operation. This reads *valid in E* literally as
   per-environment. The cost is a new configuration item or record, which is a core
   packaging question (I8)

**M1 work-around, if routed to D**: accept only the plane-declared identifiers, which
is option 1, and record it as a delivery limit, not a decision. Every option accepts
those identifiers, so widening the accepted set later is additive, while narrowing it
would be breaking. **This is narrower than options 2 and 3.** Under the slice's rule
("absent, not simplified") it must be recorded as unbuilt scope of ID FR-015 and
PF FR-018, never presented as the specified behaviour.

#### Blocked
**No *done when* item.** Step 5 of the item 1 trace grants only `agent:register`,
`event:publish`, and `event:subscribe`, which every option accepts. What is blocked is
the general input rule of grant-to-human (ID FR-015) and of the standing set
(PF FR-016, FR-018): the accepted set of identifiers in M1's wire contract.

#### Routing
**Chosen**: E, which combines A and D (re-intake Q2, 2026-11-01). Raise it against
soorma-prd, and build the work-around in M1. In the user's words: "accepting only the
identifiers the PRDs declare is the narrowest reading. Widening the accepted set later is
additive, while narrowing a published set would break tenants."

#### M1 work-around (what is left unbuilt)
- Grant to a human (ID FR-015) and the standing set at registration (PF FR-016,
  FR-018) accept **only plane-declared permission identifiers**. At these tags they are
  PF's `agent:register`, `credential:revoke`, `agent:retire`, `grant:human`,
  `event:publish`, `event:subscribe`, and `attribution:read`, and ID's `human:manage`
  and `agent:delegate`. Any other identifier is rejected
- The human-only class is still enforced against standing sets, whatever the sponsor
  holds (PF FR-016)
- **Unbuilt**: any tenant-defined identifier (option 2), and any per-environment
  declaration of one (option 3). This is a delivery limit of M1, recorded under the
  slice rule "absent, not simplified". It is not the specified behaviour, and the
  wire contract must not present it as the specified behaviour
- The wire contract states that the accepted set may widen in a compatible version.
  Widening is additive, so whichever option the PRD side picks lands without breaking
  M1's contract
- Carried into requirements as M1-FR-15 and into the Build and Test summary

**Status**: `Open`. Raised as [soorma-prd#24](https://github.com/soorma-ai/soorma-prd/issues/24) against ID @ `prd-identity-v1.0`, and worked around in M1 (see above)

---

### GAP-INT-007: Origin at an autonomous first hop: agent-asserted, or platform-stamped?

**Raised**: 2026-11-02T05:56:46Z
**Stage**: User Stories (classified with prd-gap-classification.md before any unit exists, hence `GAP-INT`)
**Raised against**: PF, soorma-prd/aiprd-docs/platform-foundations/requirements/prd.md @ `prd-platform-foundations-v1.3`
**PRD section**: PF §8b *Origin stamping*; PF §11 *What the SDK may not populate*; PF FR-015; PF §7b *Envelope Fields* (origin mode setter). Present verbatim since `prd-platform-foundations-v1.0`
**Owner**: platform-foundations
**Unit**: (pre-unit), until Units Generation assigns it
**Issue**: [soorma-prd#25](https://github.com/soorma-ai/soorma-prd/issues/25), opened 2026-11-02 with this entry verbatim, pinned to `14e7096`
**Resolved by**: —

#### What the build needs
The build needs to know who sets origin mode at a first hop with no inbound context,
where the agent has declared autonomy. Under A-5 that is **every M1 first hop**: A's
publish and B's subscribe. It also needs to know what happens to a draft that carries an
origin mode. *Done when* 7 rejects a draft that sets a platform-stamped field, so whether
origin mode is platform-stamped in this case decides what item 7 must reject.

#### What the PRD says
- PF §8b *Origin stamping*, row *No inbound context, autonomy declared*: origin
  `autonomous`, set by "**Agent-asserted, accepted** because the agent's own set is the
  ceiling regardless"
- PF §11 *What the SDK may not populate*: "Scope, **origin mode**, delegating principal,
  actor chain, re-broadening record | **Rejected** — never silently overwritten". It has
  no carve-out for an autonomous first hop
- PF FR-015: "Origin is stamped by the platform **wherever it is derivable**", and "An
  agent-asserted `autonomous` where inbound context exists is rejected". The second
  clause implies an asserted `autonomous` is acceptable where no context exists
- PF §7b: origin mode is set by "**Platform** where derivable". With autonomy declared on
  the registration, `autonomous` is derivable without any assertion

#### Why this is specification, not technology
These are two PRD sections that cannot both be satisfied, which is a listed
specification case. If the agent asserts `autonomous` and the platform accepts it
(§8b), the draft sets origin mode, and §11 rejects that draft. If the platform rejects
the draft and stamps origin (§11, §7b), the §8b row's "agent-asserted, accepted" is
false. The choice is part of the wire contract: what a draft may carry, and what a raw
caller must send. That makes it one-way once tenants build against it, and two competent
engineers would choose differently.

#### Options considered
1. **Reject and stamp.** Origin is platform-stamped at every hop. At an autonomous first
   hop the perimeter derives `autonomous` from the registration's autonomy declaration;
   any draft setting origin mode is rejected. Read this way, §8b's "agent-asserted" means
   *declared at registration*, not *asserted on the wire*. §11, §7b, and FR-015's first
   sentence hold as written; §8b's setter cell, and FR-015's "agent-asserted `autonomous`"
   phrasing, need correcting
2. **Assert and accept.** At an autonomous first hop the agent asserts `autonomous` on the
   draft, and the perimeter accepts it if the registration declares autonomy. §8b and
   FR-015's second sentence hold; §11's origin-mode row needs a carve-out. It leaves open
   what happens to a draft with no context that omits origin: stamped, or denied?
3. **Accept a matching assertion.** The perimeter stamps origin when the draft omits it,
   accepts an asserted `autonomous` that equals what it derives, and rejects any other
   value. §11 needs amending, and the contract carries an optional field

#### Routing
**Chosen**: E, combining A and D (2026-11-02). Raise it against soorma-prd, and keep the reject-and-stamp work-around in M1. Accepting an asserted value later is additive.

#### M1 work-around
M1-FR-01 already takes **option 1**: the perimeter stamps origin on every first hop, and
a draft setting origin mode is rejected (M1-FR-01, M1-FR-08). Moving to option 2 or 3
later means **accepting** an asserted value the perimeter now rejects, which is additive.
Moving from option 2 or 3 to option 1 would be breaking. So option 1 is the safe
interim, and it is recorded as a work-around, not as the specified behaviour.

#### Blocked
**No *done when* item**, given the work-around. It governs every M1 first hop (A-5;
US-08) and the origin-mode case of *done when* 7 (US-11).

**Status**: `Open`. Raised as [soorma-prd#25](https://github.com/soorma-ai/soorma-prd/issues/25) against PF @ `prd-platform-foundations-v1.3`, and worked around in M1 (reject and stamp)
