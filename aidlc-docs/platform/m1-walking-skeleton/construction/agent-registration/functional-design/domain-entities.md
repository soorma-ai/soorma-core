# Domain Entities: U5 `agent-registration`

**Unit**: U5 `agent-registration` (soorma-core#8). Control face, environment level. Adds two
operations to S2 `control-gateway`
**Built against**: PF @ `prd-platform-foundations-v1.3` (the main source), ID @ `prd-identity-v1.0`
**Companions**: [business-rules.md](business-rules.md) (rules BR-* and decisions D-AR-01 to
D-AR-27), [business-logic-model.md](business-logic-model.md),
[l1-coverage-matrix.md](l1-coverage-matrix.md),
[invariant-coverage-matrix.md](invariant-coverage-matrix.md)

Every record here lives in E's **environment store** (U4), carries E's three identity columns,
and is read and written only with a constraint on them (U4 D-EHA-29). Field names are camelCase
(D-WC-01). Wire shapes are added to `contract/control-gateway.openapi.yaml` at Code Generation
(business-rules §13). Physical design (tables, indexes, privileges) is NFR Design's.

---

## Entity Map

| Entity | Kind | Owner (module) | Lifetime | Source |
|---|---|---|---|---|
| Logical Agent Registration | record | P4 `registry` | written once; **never modified or deleted** in M1 | PF §7a; FR-007, FR-013 |
| Ceiling Snapshot | value, part of the registration | P4, from P3's read | as the registration | PF §7a, FR-016, §8b |
| Standing Set | value, part of the registration | P4 | as the registration | PF §7a, FR-016; **also the agent's grant** (D-AR-06) |
| Re-broadening Declaration | value, part of the registration | P4 | as the registration | PF §7a, FR-017 |
| Registration Secret | record | P4 `registry` | written once, `active`; never modified or deleted in M1 (rotation and retirement absent) | PF §7a v1.3, FR-008; ID FR-026 |
| Registration Secret Value | value (wire) | S2, returned once | the issuance response only | credentials.md (`soorma_rs_`) |
| Human Authority | value | P3 `authority`, from one read | one request | D-AR-07; U4 D-EHA-13, 14 |
| Registration Request Check | value | P3 | one request | D-AR-03, 10 |
| Agent Facts | value (the query's result) | P4, behind U3's port | one call (then U3's cache) | U3 NP-04 |
| Attribution Record | record (U4's) | P7 `attribution` | written once | PF FR-025; ID §7b |
| Problem Table additions | constant | P1 | the build | D-AR-02, 03, 05 |

---

## Logical Agent Registration (record)

All eight attributes of PF §7a, and the record's state.

| Attribute | Meaning | Source |
|---|---|---|
| `agent` | The logical agent's identifier, **chosen by the client**, unique within E, compared exactly. `LogicalAgentIdentifier`: the `strict` pattern, 1 to 64 characters (BR-ID-02). It is also the **registration's reference**: there is one identifier for the record. Once used in E it is never reusable, because the record is never deleted (D-AR-02) | PF §7a *Identifier*; FR-007; identifiers.md |
| `environment` | `{ organization, project, environment }`: E's **configured** identity. The one environment this agent belongs to | PF §7a *Environment scope*; PF §6; FR-022 |
| `sponsor` | `{ organization, principal }`: **the human who presented the environment credential** (D-AR-09), composed, never allocated | PF §7a *Sponsor reference*; ID FR-001; ID §1 trace step 6 |
| `ceilingSnapshot` | The sponsor's **whole held set** in E, read once at the check, human-only permissions included; a set (D-AR-11) | PF §7a *Sponsor ceiling snapshot*; FR-016; §8b *Sponsorship* |
| `standingPermissions` | The agent's own authority, the ceiling in autonomous origin; a set of 0 to 32 accepted identifiers, none human-only, within the snapshot | PF §7a *Standing permission set*; FR-016 |
| `reBroadeningDeclaration` | A set of 0 to 32 identifiers **within the standing set**; empty when the request omits it | PF §7a *Re-broadening declaration*; FR-017 |
| `autonomyDeclared` | Boolean, **default `false`** | PF §7a *Autonomy declared* |
| `registeredAt` | When S2 wrote the record (RFC 3339, UTC) | PF §7a *Registration timestamp* |
| `state` | `registered`. PF's `suspended` and `retired` are unreachable in M1: the operations are absent (M1-FR-03) | PF §7a *State transitions* |

**The registration is the agent's grant** (D-AR-06). Read as PF §7a's *Permission Grant* in its
agent-principal form: principal = `agent`; environment scope = `environment`; permission set =
`standingPermissions`; granted-at = `registeredAt`; granted-by = `sponsor` (with the credential
presented, on the attribution record). U4's Grant record stays human-only.

**Never modified, never deleted** (D-AR-15): a resolution target (PF FR-013), on which U3's
evaluation of a sealed chain relies (D-AE-09).

## Ceiling Snapshot (value)

The set P3 judged the ceiling against, written as it was read (D-AR-07, 11). It is not limited
to the standing set and not recomputed: a later grant to the sponsor leaves it unchanged
(TC-AR-019). It is **never consulted per request**: U3 reads the standing set, autonomy, and
declaration only (PF §8b *Sponsorship*).

## Registration Secret (record)

| Attribute | Meaning | Source |
|---|---|---|
| `id` | At least 128 random bits, unique within E (D-AR-25) | ID §6; U4 D-EHA-30 |
| `environment` | E's configured identity, equal to its registration's | PF §6 |
| `registration` | The `agent` it is bound to: exactly one registration | PF §7a *Registration Secret* |
| `issuer` | `{ organization, principal }`: **the human who issued it**, a lower bound on who knows it, never the set | PF §7a v1.3; ID FR-026 |
| `issuedAt` | When S2 wrote the record | PF FR-008 |
| `state` | `active`. Retirement is absent (M1-FR-04) | PF FR-008 |
| verification material | **Only material that can verify the secret, never the secret** (TC-AR-006). A fast hash of a value with at least 256 random bits, never a slow password hash (*added at approval*); its exact form, and whether it is keyed, is NFR Requirements' | PF §8b *Bootstrap* ("locally-verified"); SECURITY-12 |

A registration may hold **several active secrets**, each with its own record and issuer
(D-AR-04). The number is capped at NFR Requirements. The secret's lifecycle is **independent of
any credential's** (PF FR-008): issuing one changes no credential, and U6's credentials never
change a secret.

## Registration Secret Value (wire)

`soorma_rs_` followed by a body NFR Requirements chooses, which **carries the secret record's `id`** and at least 256 random bits (*added at approval, 2026-11-11*: bootstrap checks exactly one record; business-rules §17); at most 256 characters; material, not a
credential, so it goes in a request body, never in `Authorization` (credentials.md). **Returned
exactly once**, in the issuance response, and stored nowhere (TC-AR-020).

## Human Authority (value)

The presenter's held set in E, read **once** per operation through P11 over P4's human
`GrantSource` (uncached, U4 D-EHA-14), and wrapped by P3 so that **every test of it goes through
one evaluator** (D-AR-07):

| Member | Meaning |
|---|---|
| `allows(required)` | P3's evaluator over the held set: the seam's `contains(held, required)`, `required` non-empty. The same function `evaluateHuman` uses |
| `exceeding(candidate)` | The entries of `candidate` the held set does not contain, each decided by `allows({ p })`, in request order |
| `snapshot()` | The held set as read, for the Ceiling Snapshot |

No other module sees the held set except through these members (I5; U4 BR-EV-04).

## Registration Request Check (value)

P3's result over the request's two sets, before any state is read (D-AR-10):
- `humanOnly`: the standing entries in P3's `HUMAN_ONLY_PERMISSIONS` (D-AE-03)
- `outsideStanding`: the declared entries the standing set does not contain, by the seam's
  `contains`

## Agent Facts (value)

U3's port (NP-04), filled by P4 with **one query** for a list of agents in one environment
(D-AR-19). For each agent found:

| Field | From |
|---|---|
| `registrationView.autonomyDeclared` | the registration |
| `registrationView.reBroadeningDeclaration` | the registration |
| `standingSet` | the registration's `standingPermissions` (D-AR-06) |

An agent not returned is *not found*. Any failure rejects the whole call.

## Attribution Record (U4's, called)

| Operation | Actor | Target | Scope |
|---|---|---|---|
| `registerAgent` | human: the sponsor and the `environmentCredential` presented | the registration (`agent`) | E |
| `issueRegistrationSecret` | human: the issuer and the `environmentCredential` presented | the registration (`agent`) | E |

No chain, origin, or re-broadening (no envelope; ID FR-022). Which secret was issued, and by
whom, is on the secret record (`registration`, `issuer`, `issuedAt`).

## Relationships

Each registration belongs to one environment and names one human sponsor.
Each secret belongs to one registration and names one human issuer; a registration has zero or
more secrets. U3 reads a registration's facts; U6 bootstraps against its secrets; U6 and U7
resolve the sponsor through it for attribution records.

| Relationship | Cardinality | Constraint |
|---|---|---|
| Registration → environment | exactly 1 | `agent` unique within E (D-AR-02) |
| Registration → sponsor | exactly 1 | the presenter (D-AR-09); never changes in M1 |
| Secret → registration | exactly 1 | same environment; the registration exists (D-AR-05) |
| Registration → secrets | 0 to the cap | NFR Requirements (D-AR-04) |
| Secret → issuer | exactly 1 | the presenter; the sponsor or an Admin (D-AR-01) |
| Standing ⊆ snapshot | always | D-AR-07 |
| Declaration ⊆ standing | always | D-AR-10 |
| Standing ∩ human-only = ∅ | always | D-AR-10 |

## Problem Table additions (P1)

| Code | Status | Pointer |
|---|---|---|
| `human_only_permission` | 400 | each `/standingPermissions/{i}` in the class |
| `declaration_outside_standing` | 400 | each `/reBroadeningDeclaration/{i}` outside the standing set |
| `exceeds_sponsor_ceiling` | 403 | each `/standingPermissions/{i}` the presenter does not hold |
| `registration_exists` | 409 | `/agent` |
| `unknown_registration` | 400 | `/registration` |

Each list is ordered by pointer, at most 10 entries (U1 BR-ERR).
