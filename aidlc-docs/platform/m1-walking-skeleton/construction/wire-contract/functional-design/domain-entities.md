# Domain Entities: U1 `wire-contract`

**Unit**: U1 `wire-contract` (soorma-core#4). A contract unit with no face
**Built against**: PF @ `prd-platform-foundations-v1.3`, ID @ `prd-identity-v1.0`
**Companions**: [business-rules.md](business-rules.md) (the rules and decisions D-WC-01 to
D-WC-16), [business-logic-model.md](business-logic-model.md), [l1-coverage-matrix.md](l1-coverage-matrix.md),
[invariant-coverage-matrix.md](invariant-coverage-matrix.md)

**Amendments after approval** (2026-11-08; see business-rules.md): **A1**, the envelope's
`traceContext` is open and the draft's closed; **A2**, the Problem's `type` and `instance`
carry no pattern; **A3**, the received Problem schema requires no field.

These are the entities of the **wire contract**: what travels between a client and the
platform. They are not stored records. The platform's records (registrations, grants,
credentials) belong to the surface units. Field names are camelCase (D-WC-01).

---

## Entity Map

| Entity | Defined in | Open to unknown fields? | Produced by | Consumed by |
|---|---|---|---|---|
| Envelope | `envelope.schema.json` | **Yes**, at every level | The perimeter (stamping) | Subscribers; the perimeter, when forwarded |
| Draft | `envelope.schema.json` | **No**, at its top level | The client | The perimeter |
| Forwarded Context (`inbound`) | `envelope.schema.json` | The wrapper: no. Its envelope: **yes** | The client, copying a received `Delivery` | The perimeter |
| Seal | `envelope.schema.json` | — (an opaque string) | The perimeter | The perimeter only |
| Delivery | `delivery.schema.json` | **Yes** | The perimeter (S4) | Subscribers |
| Scope | `envelope.schema.json` | Yes | The perimeter, from the credential | Everyone |
| Actor Reference | `envelope.schema.json` | Yes | The perimeter, per hop | Everyone |
| Re-broadening Record | `envelope.schema.json` | Yes | The perimeter, when load-bearing | Everyone |
| Delegating Principal Reference | `envelope.schema.json` | Yes | The perimeter. **Never in M1** | Everyone |
| Trace Context, in a draft | `envelope.schema.json` (the draft's definition) | **No**: input strictness | The client (asserted) | The perimeter |
| Trace Context, in an envelope | `envelope.schema.json` (the envelope's definition) | **Yes** | The perimeter, from the draft | Observability; the trace |
| Contract Version | `conventions/` | — | soorma-core, at a tag | Clients (pinned) |
| Client Contract Version | Draft, or the `Soorma-Contract-Version` header | — | The client | The perimeter |
| Problem | `conventions/` | Yes | The perimeter | Clients |
| Credential Presentation | `conventions/` (security schemes) | — | The client | The perimeter |

---

## Envelope

The identity context of an event or an agent-originated call (PF FR-001, PF §7b). Six
fields are platform-stamped; one is agent-asserted (PF FR-002). It carries assertions the
platform stamped, **not proof**, and it is never usable to act (PF §17).

| Field | Type | Required | Set by | Source |
|---|---|---|---|---|
| `envelopeVersion` | integer ≥ 1. Always `1` in M1 | Yes | Platform | PF §7b; D-WC-03 |
| `scope` | Scope | Yes | Platform, from the presented credential | PF §7b; D-WC-04 |
| `originMode` | open string; known values `autonomous`, `delegated` | Yes | Platform | PF §7b, FR-015; GAP-INT-007 |
| `delegatingPrincipal` | Delegating Principal Reference | When `originMode` is `delegated` | Platform | PF §7b; ID §7b. Never stamped in M1 (A-5) |
| `actorChain` | list of Actor Reference, 1 to 32, most recent last | Yes | Platform, appended per hop | PF FR-006; D-WC-05 |
| `reBroadening` | list of Re-broadening Record, at least 1 | When re-broadening was load-bearing at some hop | Platform | PF §7b, §8b |
| `traceContext` | Trace Context, the envelope's definition (open) | Yes | Agent-asserted; validated for well-formedness only | PF §7b; M1-TECH-05 |

**Seven fields, exactly as PF states them.** No eighth field is added. The seal travels
**beside** the envelope, never inside it (D-WC-06).

## Scope

The environment the envelope belongs to: **its identity composed with its organization and
project** (D-WC-04).

| Field | Type | Required |
|---|---|---|
| `organization` | Configured Identifier | Yes |
| `project` | Configured Identifier | Yes |
| `environment` | Configured Identifier | Yes |

All three are configured, never inferred (PF FR-022, O11; ID FR-004). Two scopes are
equal only when all three parts are equal.

## Actor Reference

One hop of the actor chain (PF FR-006, PF §7b).

| Field | Type | Required | Note |
|---|---|---|---|
| `agent` | Logical Agent Identifier | Yes | The logical agent whose credential was presented at that hop. It resolves to the registration, and from there to the sponsor (PF §7b *Recoverability*) |
| `instance` | Instance Identifier | Yes | Asserted at bootstrap, recorded, not verified (PF FR-009; I10) |

Both are unique within the envelope's scope. Global uniqueness is composed with scope,
never allocated (PF §17). An entry may gain fields later, but the chain's order and
minimum length may not change within a major line (PF §14).

## Re-broadening Record

That re-broadening was **load-bearing** at a named hop (PF §7b, §8b).

| Field | Type | Required | Note |
|---|---|---|---|
| `hop` | integer ≥ 0 | Yes | The zero-based index of the `actorChain` entry that re-broadened |

The list travels with the chain. Indexes stay valid because the chain only grows by
appending. A later hop does not inherit re-broadening; the record only says where it
happened (PF §8b *Propagation*).

## Delegating Principal Reference

Present only when `originMode` is `delegated` (PF §7b). It is opaque, organization-scoped,
and **never proof** (ID §7b).

| Field | Type | Required |
|---|---|---|
| `organization` | Configured Identifier | Yes |
| `principal` | Human Principal Identifier | Yes |

Defined in envelope v1 so that delegation lands without a breaking change (A-4). **No M1
path stamps it**, because no delegated chain can start (A-5).

## Trace Context

Distributed trace correlation, conforming to W3C Trace Context (M1-TECH-05).

| Field | Type | Required |
|---|---|---|
| `traceparent` | string, W3C `traceparent` syntax | Yes |
| `tracestate` | string, W3C `tracestate` syntax, at most 512 characters | No |

It is carried in the request **body**, as part of the draft. soorma-core validates its form
only, and emits no spans (T-3).

**Two definitions** (amendment A1; BR-TC-05). W3C defines the two header strings, not this
object, so its openness is the contract's choice:
- **In a draft**, it is **closed**: exactly `traceparent` and `tracestate`. An unknown field
  is `unknown_field` (BR-DR-06)
- **In an envelope**, it is **open**, like every other envelope object (BR-ENV-05), so an
  optional field added later is compatible

## Draft

What a client sends on an envelope-bearing call: publish and subscribe (D-WC-14). Its top
level is **closed** (D-WC-11).

| Field | Type | Required |
|---|---|---|
| `clientContractVersion` | Contract Version string | Yes |
| `traceContext` | Trace Context, the draft's definition (closed) | Yes |
| `inbound` | Forwarded Context | No: present when the call is triggered by an inbound event |

No platform-stamped field is admitted, `envelopeVersion` included (PF §11).

## Forwarded Context (`inbound`)

A received envelope that the client forwards, with its seal (D-WC-06, D-WC-11).

| Field | Type | Required | Note |
|---|---|---|---|
| `envelope` | Envelope, **open**, carried **as received** | Yes | Unknown fields are kept and preserved into the newly stamped envelope (PF FR-005 a) |
| `seal` | Seal | Yes | Exactly as received in the `Delivery` |

The wrapper itself is closed: it holds exactly these two fields.

## Seal

An opaque string the perimeter computes when it stamps an envelope (D-WC-06). It proves
**to the perimeter of the same environment** that the envelope is one it stamped,
unaltered. It does **not** prove that the envelope was delivered to whoever forwards it,
or that it is recent (an accepted residual, business-rules.md Section 14). It is not a
credential, gives no authority, and cannot be verified by a client.

| Property | Value |
|---|---|
| Computed over | The RFC 8785 (JCS) canonical form of the envelope |
| Bound to | The environment: computed with that environment's own sealing material, never shared |
| Form | An opaque string. Algorithm, key identification, and rotation are decided at NFR Design |
| Travels | In the `Delivery` beside the envelope, and in `inbound` beside the forwarded envelope |

## Delivery

One event on a subscriber's stream (`delivery.schema.json`).

| Field | Type | Required |
|---|---|---|
| `envelope` | `$ref` to the Envelope | Yes |
| `seal` | Seal | Yes |
| `payload` | any JSON value, opaque to the platform (I9) | Yes |

Payloads are JSON only in M1 (D-WC-12). A content-type field can be added later as an
optional field, which is compatible.

## Contract Version and Client Contract Version

| Entity | Form | Meaning |
|---|---|---|
| Contract Version | SemVer with major version 0, for example `0.1.0`. Published at the git tag `contract-v0.1.0` | The version of the whole contract: the envelope and Delivery schemas, the conventions, and the surface documents |
| Client Contract Version | The same string | The contract version a client was built against. It is declared in the draft, or in the `Soorma-Contract-Version` header on a call without a draft (D-WC-08) |
| Envelope Version | integer, `1` | The envelope's own version, in the envelope. It is distinct from both of the above (PF §7b) |

## Problem

An error response, as RFC 9457 Problem Details (`application/problem+json`) (D-WC-09).

| Field | Type | Required in the schema | soorma-core always emits | Note |
|---|---|---|---|---|
| `type` | string, no pattern | No | Yes, as `urn:soorma:problem:{code}` | A client accepts any value, `about:blank` included. RFC 9457: absent means `about:blank` |
| `title` | string | No | Yes | Generic. Never internal detail |
| `status` | integer | No | Yes | The HTTP status |
| `code` | open string | No | Yes | Stable and machine-readable. Clients tolerate codes they do not know, and problems with none |
| `instance` | string, no pattern | No | Yes, as `urn:soorma:request:{request id}` | Equals the response's `Soorma-Request-Id` |
| `errors` | list of `{ pointer, detail }` | No | On validation errors | `pointer` is a JSON Pointer into the request body |
| `supportedVersions` | list of Contract Version | No | On `unsupported_contract_version` | |

**A received schema** (amendments A2 and A3; BR-ERR-08). A client also receives problems that
a gateway or proxy emits, usually `about:blank` with no `code` or `instance`. So, following
RFC 9457, the schema **requires no field** and constrains no value's form, and the generated
type makes every member optional. **What soorma-core emits is a published convention**: the
five fields above, always, with the `urn:soorma:` forms. U3's perimeter tests verify it.

## Credential Presentation

| Element | Rule |
|---|---|
| Slot | `Authorization: Bearer {credential}`. **One credential per request** |
| Kind | Readable from the credential's **typed prefix**, without verifying it (D-WC-07) |
| Reserved | `Soorma-Delegation` header, for a later delegation credential. Refused in M1 |
| Not a credential | The registration secret and enrollment material. They are sent in a request body, never as a bearer token |

| Kind | Prefix | Presented at |
|---|---|---|
| Agent credential | `soorma_ac_` | S3 renewal; S4 publish and subscribe |
| Human environment credential | `soorma_ec_` | S2, in its own environment only |
| Organization sign-in | `soorma_si_` | S1; and S2's environment credential issuance only |
| Delegation credential | `soorma_dc_` | Reserved. No M1 path issues one |
| Registration secret (material) | `soorma_rs_` | S3 bootstrap request body |
| Enrollment material (material) | `soorma_em_` | S1 first authentication request body |

---

## Identifier Kinds

Syntax and lengths are set per kind in [business-rules.md](business-rules.md), BR-ID.
**They constrain only what the platform accepts** (BR-ID-11). Wherever an identifier is
received, in the envelope, the Delivery, or a response, it is a plain string, and
consumers never validate its syntax. Human principal identifiers are ASCII-only in M1
(BR-ID-12).

| Kind | Examples | Allocated by |
|---|---|---|
| Configured Identifier | organization, project, environment | Configuration |
| Logical Agent Identifier | a registration's agent | U5 decides: client-chosen or platform-allocated. The syntax fits both |
| Platform Reference | registration reference, credential reference, grant, request id | The platform |
| Instance Identifier | an agent instance | Asserted by the agent at bootstrap |
| Human Principal Identifier | an email address, or an `issuer`, a vertical bar, and a `subject` | Configuration (first Admin); later registration |
| Permission Identifier | `agent:register`, `event:publish` | Plane PRDs (GAP-INT-006) |

---

## Relationships and Cardinality

| From | To | Cardinality | Constraint |
|---|---|---|---|
| Envelope | Scope | exactly 1 | Every scope part is configured |
| Envelope | Actor Reference | 1 to 32, ordered | Most recent last; appended only |
| Envelope | Re-broadening Record | 0 or 1 to 32 | Each `hop` < the chain's length; no duplicate `hop` |
| Envelope | Delegating Principal Reference | 0 or 1 | Exactly 1 when `originMode` is `delegated`; 0 in M1 |
| Envelope | Trace Context | exactly 1 | |
| Delivery | Envelope, Seal | exactly 1 each | The seal is over that envelope |
| Envelope | its JCS serialization | at most 16 KiB | Refused at stamping when exceeded (BR-ENV-10) |
| Draft | Forwarded Context | 0 or 1 | |
| Forwarded Context | Envelope, Seal | exactly 1 each | Its scope equals the receiving environment's scope |
| Request | Credential | 0 or 1 | 0 only on the unauthenticated surfaces: bootstrap, sign-in, first authentication |
