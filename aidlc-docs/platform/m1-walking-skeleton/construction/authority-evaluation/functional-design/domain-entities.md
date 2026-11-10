# Domain Entities: U3 `authority-evaluation`

**Unit**: U3 `authority-evaluation` (soorma-core#6). Data face, environment level. Modules
only
**Built against**: PF @ `prd-platform-foundations-v1.3`, ID @ `prd-identity-v1.0`
**Companions**: [business-rules.md](business-rules.md) (rules BR-* and decisions D-AE-01 to
D-AE-26), [business-logic-model.md](business-logic-model.md),
[l1-coverage-matrix.md](l1-coverage-matrix.md),
[invariant-coverage-matrix.md](invariant-coverage-matrix.md)

**U3 stores nothing.** Every entity here is a value computed per request, or a view of a
record another unit owns (registrations and grants: U5 and U4, in P4). The wire shapes
(envelope, draft, `inbound`, Delivery) are U1's, in `contract/envelope.schema.json`; this
document names what U3 builds from them. Field names are camelCase (D-WC-01).

---

## Entity Map

| Entity | Kind | Built by | Lifetime | Source |
|---|---|---|---|---|
| Envelope Request | value (input) | the surface (U7) | one request | D-AE-04; BR-IN-02 |
| Checked Agent Context | value (input) | P1, from the verified agent credential (U6) | one request | D-AE-08 |
| Required Authority | value (input) | the surface, per operation | one request | D-AE-10; PF §8a |
| Agent Facts | view of P4's registrations | the entry point, through the agent-facts port U5 fills, behind one cache | one request | PF §7a; *Consistency fix from NFR Design (2026-11-10)* |
| Registration View | part of Agent Facts | the agent-facts read | one request | PF §7a |
| Permission Set | value | P3; the seam | one request | PF FR-018 |
| Principal Reference | value | P3 | one request | PF §7a *Permission Grant* |
| Validated Draft | value | P2 (steps 5 and 6) | one request | BR-DR; BR-DV |
| Verified Forwarded Context | value | P2 (step 7) | one request | BR-FC; BR-FX |
| Origin Resolution | value | P3 (step 9) | one request | BR-OR |
| Evaluation Outcome | value | P3 (step 9) | one request | BR-AU |
| Stamped Envelope and Seal | value (output) | P2 (step 10) | delivered by U7 | BR-ST |
| Admitted | value (output) | the entry point | one request | D-AE-04 |
| Refusal | value (output) | P2, P3, the entry point | one request | D-AE-11 |
| Human-Only Class | constant | P3 | the build | D-AE-03 |
| Problem Table | constant | P1 | the build | D-AE-06 |

---

## Envelope Request

The entry point's request input (D-AE-04).

| Field | Type | Notes |
|---|---|---|
| `body` | any JSON value | Untrusted. Only `clientContractVersion` is read before step 6 (BR-VR-05) |
| `contractVersionHeader` | list of strings, possibly empty | Every `Soorma-Contract-Version` value the request carried (BR-VR-04) |
| `agent` | Checked Agent Context | From P1 after steps 1 to 4 |
| `required` | Required Authority | From the surface |
| `requestId` | string | The response's `Soorma-Request-Id`; for the security log |

## Checked Agent Context

What P1 hands U3 after steps 1 to 4. **Every field comes from the verified credential's
claims**, never from deployment or the request body (D-AE-08; PF FR-022).

| Field | Type | Notes |
|---|---|---|
| `scope` | `{ organization, project, environment }` | Becomes the stamped `scope` with no `inbound`. Checked equal to the configured scope (D-AE-23) |
| `agent` | Logical Agent Identifier | The registration the credential is bound to |
| `instance` | Instance Identifier | **Asserted at bootstrap, recorded, not verified** (PF §7a; I10) |

## Required Authority

A **non-empty** Permission Set: every member must be contained (D-AE-10).

| Operation | Required |
|---|---|
| Publish (S4) | `{ event:publish }` |
| Subscribe (S4) | `{ event:subscribe }` |

## Registration View

What P3 reads from the presenter's registration, besides its standing set (which it reads
through the seam, D-AE-02). A view, not a copy. Both come from the request's **Agent Facts**
read (below).

| Field | Type | Notes |
|---|---|---|
| `autonomyDeclared` | boolean | PF §7a, **default no**. Decides BR-OR-01 to 04 |
| `reBroadeningDeclaration` | Permission Set, possibly empty | PF §7a; within the standing set (U5 enforces it; BR-AU-04 intersects with `S` anyway) |

Result: the view, or **not found** (BR-OR-06, `forbidden`). A failed read refuses the request
before origin is decided (`unavailable`).

## Agent Facts

*Consistency fix from NFR Design (2026-11-10)*. One port returns, **for a list of agents in one call**, each agent's Registration
View and standing set together, or **not found**. Read **once, at the start of step 9**, for
the presenter and every distinct upstream agent. **All or nothing**: a failure is
`unavailable`, and nothing from it is used.

| Field (per agent) | Type | Serves |
|---|---|---|
| `registrationView` | Registration View | Origin (BR-OR), and `D` (BR-AU) |
| `standingSet` | Permission Set | P11's agent `GrantSource` (`S`, `U1 … Un`) |

Behind one caching decorator (NFR-AE-09 to 15). Human principals never pass through it.

## Permission Set

A finite set of **Permission Identifiers**: flat, opaque strings, compared exactly (BR-ID-06,
BR-ID-08). Set semantics: no order, no duplicates. The **empty set** is the bottom element
(L3). There is no universal set value: a term that "imposes nothing" (`P` in autonomous
origin, `U` with no upstream hop) is represented by **its absence** from the composition,
never by a wildcard.

The five laws, which this model satisfies and P3's tests check (D-AE-16):

| Law | For permission sets |
|---|---|
| L1 Closure | `A ∩ B` is a Permission Set |
| L2 Associativity, commutativity | `(A ∩ B) ∩ C = A ∩ (B ∩ C)`; `A ∩ B = B ∩ A` |
| L3 Bottom | `∅` is representable, and `contains(∅, R)` is false for any non-empty `R` |
| L4 Monotonicity | `A ∩ B ⊆ A` |
| L5 Decidable containment | `R ⊆ A` is decided by exact membership |

## Principal Reference

The seam's way of naming whose granted set is wanted (BR-SEAM-01).

| Variant | Fields | Granted set (P11's default) |
|---|---|---|
| Agent | `agent` (Logical Agent Identifier) | Its standing set (U5 fills `GrantSource`) |
| Human | `principal` (Human Principal Identifier) | The union of its grants in E (U4 fills `GrantSource`) |

## Validated Draft

The draft after steps 5 and 6 (U1's `Draft`, closed at its top level).

| Field | Notes |
|---|---|
| `clientContractVersion` | In the accepted set |
| `traceContext` | Closed: `traceparent`, and `tracestate` if sent. Well-formed (BR-TC) |
| `inbound` | Optional: `{ envelope, seal }`, the envelope open and as received |

## Verified Forwarded Context

`inbound` after step 7 (BR-FX): within the bound, seal verified with this environment's
material, `envelopeVersion` `1`, scope equal to this environment's, re-broadening indexes
valid. Carried **as received**, unknown fields included. **It grants nothing** (BR-FX-06).

| Derived | Use |
|---|---|
| The forwarded chain's length | Step 8 (BR-CD-01) |
| The forwarded origin and delegating principal | Step 9 (BR-OR-03 to 05); stamped unchanged |
| The distinct agents in the forwarded chain | The upstream terms (D-AE-21) |

## Origin Resolution

| Outcome | When |
|---|---|
| `autonomous`, stamped here | No `inbound`; autonomy declared (BR-OR-01) |
| `autonomous`, propagated | `inbound` autonomous; autonomy declared (BR-OR-03) |
| Refusal `forbidden` | Autonomy not declared, with or without `inbound` (BR-OR-02, 04: O12; GAP-AE-001 work-around); `inbound` origin `delegated` or unknown (BR-OR-05) |

## Evaluation Outcome

P3's `evaluateAgent` result (BR-AU).

| Field | Type | Notes |
|---|---|---|
| `allowed` | boolean | `R` contains no human-only permission, and `R ⊆ W` |
| `loadBearing` | boolean | `allowed`, and not `R ⊆ N`. Never true at a first hop |
| `reason` | internal reason, when not allowed | `human_only_permission`, `authority_denied`, `upstream_unresolved` |

`N` and `W` are computed and discarded inside P3. **No effective set leaves P3.**

## Stamped Envelope and Seal

U1's `Envelope` (seven fields, open), field by field (BR-ST):

| Field | Without `inbound` | With a verified `inbound` |
|---|---|---|
| `envelopeVersion` | `1` | `1` |
| `scope` | the Checked Agent Context's scope | `inbound`'s, kept with its unknown fields (equal to this environment's) |
| `originMode` | `autonomous` | `inbound`'s, unchanged |
| `delegatingPrincipal` | absent | `inbound`'s, unchanged (never present in M1) |
| `actorChain` | `[{ agent, instance }]` | `inbound`'s entries as received, then `{ agent, instance }` |
| `reBroadening` | absent | `inbound`'s records as received, then `{ hop: n }` if load-bearing here; absent if none |
| `traceContext` | the draft's | `inbound`'s unknown trace-context fields, the draft's `traceparent`, and the draft's `tracestate` only if sent (A6) |
| unknown fields | none | `inbound`'s, preserved |

**Seal**: an opaque string over the envelope's JCS form, with this environment's sealing
material (BR-ST-07). Delivered **beside** the envelope, never inside it. Its form is NFR
Design's; U1 bounds it at 1024 characters in `inbound.seal`.

## Admitted

The entry point's success result.

| Field | Notes |
|---|---|
| `envelope` | The Stamped Envelope |
| `seal` | Its seal |
| `origin` | `autonomous` in M1 |
| `reBroadeningLoadBearing` | Whether this hop re-broadened |

U7 publishes or subscribes with it, and writes the attribution record from it (BR-ST-08).

## Refusal

| Field | Notes |
|---|---|
| `code` | A contract code from P1's table (BR-RF-03) |
| `reason` | The internal reason (§10 of business-rules). **Security log only** |
| `errors` | For steps 5 and 6 only: `{ pointer }` or `{ header }` entries (BR-DV-03; BR-VR-04) |

## Human-Only Class

`{ grant:human, human:manage, agent:delegate }`: the union of the human-only permissions
the plane PRDs declare (PF §8b, `grant:human`; ID FR-013, `human:manage` and
`agent:delegate`). **One definition**, exported by `packages/authority` (D-AE-03). Matched
literally, never by pattern (ID OB-16). A later plane PRD declaring another adds it here.

## Problem Table

In P1 (`packages/perimeter`; D-AE-06): every contract error code, with its status and
generic title, plus the server contract version and the accepted set (D-AE-25). U3 adds six
codes (BR-PE-01).

---

## The Seam's Types (`seams/policy-decision`, Apache 2.0, unpublished)

| Type | Shape |
|---|---|
| `PermissionId` | string |
| `PermissionSet` | a read-only set of `PermissionId` |
| `PrincipalRef` | `{ kind: agent, agent }` or `{ kind: human, principal }` |
| `EnvironmentRef` | `{ organization, project, environment }` |
| `PolicyDecision` | `grantedSet(principal, environment)` → `PermissionSet`, asynchronously (it reads storage); `contains(effectiveSet, requiredSet)` → boolean |

P11's port, outside the seam: `GrantSource.grantsOf(principal, environment)` → a
`PermissionSet`, or a read failure.

## Relationships

| From | To | Cardinality | Constraint |
|---|---|---|---|
| Stamped Envelope | Actor Reference | 1 to 32 | This hop last; forwarded entries unchanged before it |
| Stamped Envelope | Re-broadening Record | 0, or 1 to 32 | `hop` < chain length; no duplicate `hop`; at most one new record, for this hop |
| Evaluation | upstream term | one per distinct forwarded agent | Each the agent's standing set in E; unresolved is `∅` |
| Evaluation | Principal Reference | 1 + distinct upstream agents | All in the same environment (E) |
| Stamped Envelope | Seal | exactly 1 | Over the JCS form; this environment's material |
