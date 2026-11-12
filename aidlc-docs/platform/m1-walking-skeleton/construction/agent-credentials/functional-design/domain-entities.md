# Domain Entities: U6 `agent-credentials`

**Unit**: U6 `agent-credentials` (soorma-core#9). Data face, environment level. Adds the
deployable S3 `data-gateway`
**Built against**: PF @ `prd-platform-foundations-v1.3` (the main source), ID @ `prd-identity-v1.0`
**Companions**: [business-rules.md](business-rules.md) (rules BR-* and decisions D-AC-01 to
D-AC-34), [business-logic-model.md](business-logic-model.md),
[l1-coverage-matrix.md](l1-coverage-matrix.md),
[invariant-coverage-matrix.md](invariant-coverage-matrix.md)

Every record here lives in E's **environment store** (U4), carries E's three identity columns,
and is read and written only with a constraint on them (U4 D-EHA-29). Field names are camelCase
(D-WC-01). Wire shapes go into a new `contract/data-gateway.openapi.yaml` at Code Generation
(business-rules §13). Physical design (tables, indexes, privileges) is NFR Design's. **B**, **L**,
and **M** are the propagation bound, the credential's lifetime, and a lineage's maximum age,
valued at NFR Requirements.

---

## Entity Map

| Entity | Kind | Owner (module) | Lifetime | Source |
|---|---|---|---|---|
| Bootstrap Request | value (wire) | S3 | one request | PF FR-009, §9 *Inputs*; D-AC-04, 09 |
| Agent Resolution | value (the seam's answer) | P6's agent half, `agent-identity` | one request | PF §12; D-AC-08, 20 |
| Agent Credential Record | record | P5 `credentials` | written at bootstrap; its expiry moved by renewal; never deleted in M1 | PF §7a, §6 (*per instance*); D-AC-14 |
| Agent Credential Token | value (wire), a secret | P5, minted by S3 | at most L | PF §7a; D-AC-13 |
| Lineage | concept: one record and every token minted for it | P5 | until the lineage end (start + M) | D-AC-02, 14 |
| Agent Key Ring | material | P5, loaded by S3 (signing) and S4 (verify) | per environment, rotated | PF §6; D-AC-03 |
| Revocation State | record | P5 | written only by the test fixture in M1; terminal | PF §7a, FR-011, FR-012; D-AC-16 |
| Revocation Answer | value | P5 (direct source, or the cache) | one read; cached up to B | PF FR-012; D-AC-18 |
| Checked Agent Context | value | P1 `checkAgentRequest` | one request | U3 D-AE-08; D-AC-27 |
| Bootstrap Attempt Slot | record | P8 `abuse-bound` | recovers with time | PF FR-027; D-AC-06 |
| Failed Bootstrap Attempt | record | P8 (U2's writer pattern) | written once | PF FR-027; D-AC-22 |
| Attribution Record | record (U4's) | P7 `attribution` | written once | PF FR-025; D-AC-21 |
| Envelope-Free Agent Operations | constant | P7 | the build | GAP-INT-008; D-AC-33 |

---

## Bootstrap Request (value)

| Field | Meaning | Source |
|---|---|---|
| `agent` | The logical agent's identifier in E (`LogicalAgentIdentifier`): the registration it claims | PF FR-009; U5 D-AR-02 |
| `secret` | The material, at most 256 characters; **its typed prefix declares its type**; only `soorma_rs_{id}.{secret}` is accepted in M1 | D-AC-04; `credentials.md`; U5 NFR-AR-01 |
| `instance` | The instance identifier, **asserted** (`InstanceIdentifier`, 1 to 128) | PF FR-009; D-AC-23 |

**Closed**: no other field. **No environment** (the endpoint names it, D-AC-09) and **no envelope**
(GAP-INT-008, D-AC-28). No credential header (bootstrap names no scheme).

## Agent Resolution (value: the identity seam's agent half)

`resolve('registrationSecret', { environment, agent }, secret)` returns either:
- `{ resolved: true, registration: { environment, agent }, secretId }`: the material is a
  registration secret of that agent in E, and it verifies; or
- `{ resolved: false }`: a rejection that never says why.

It decides **identity only** (D-AC-20): the registration's state, revocation, and what the
credential asserts are decided after it, in core. Types in `seams/identity-resolution`
(Apache 2.0, unpublished, beside the human half); implementation in `packages/agent-identity`
(D-AC-08), importing `parseRegistrationSecret` and `registrationSecretMatches` from
`packages/registry` (D-AC-19).

## Agent Credential Record (record)

| Attribute | Meaning | Source |
|---|---|---|
| `cid` | The credential's id: at least 128 random bits, unique in E. **The lineage's identity**: it survives renewal (D-AC-14) | PF §6 *Credential identifier*; U4 D-EHA-30 |
| `environment` | E's configured identity | PF §6, §7a |
| `agent` | The logical agent, from the resolved registration | PF §7a |
| `instance` | The asserted instance identifier, as presented at bootstrap; never changed | PF FR-009; D-AC-23 |
| `secret` | The `id` of the registration secret record that bootstrapped it (never the value or digest) | D-AC-22; PF FR-008 |
| `issuedAt` | When bootstrap wrote it: **the lineage's start** | PF FR-009 |
| `lineageEndsAt` | `issuedAt` + M; no token of the lineage expires later | D-AC-02 |
| `expiresAt` | The latest expiry minted for it: `min(issuedAt + L, lineageEndsAt)` at bootstrap; moved by renewal, never backwards | D-AC-15; BR-RN-06 |

**Never deleted in M1**; only `expiresAt` changes (BR-CR-AC-05). It has no state of its own:
**liveness is its expiry and Revocation State** (no self-service end for agents exists in M1).

## Agent Credential Token (value: `soorma_ac_`)

| Part | Value | Source |
|---|---|---|
| Prefix | `soorma_ac_` | `credentials.md` |
| Header | `typ` `soorma-ac+jwt`; `alg` `Ed25519` (fixed in code); `kid` of E's agent key ring | D-AC-13; U4 NP-EHA-01 |
| `env` | `{ organization, project, environment }`, compared field by field (O4) | PF §7a; D-AE-08 |
| `sub` | The logical agent | PF §7a, §3 |
| `inst` | The instance (asserted) | PF §7a; I10 |
| `cid` | The record (the lineage) | D-AC-14 |
| `jti` | This token; new at each renewal | D-AC-14 |
| `iat`, `exp` | Issue and expiry; `exp` ≤ the lineage end | D-AC-02 |

It asserts **registration, not code identity** (PF §8b), and no permission. Every response
returns it with `agent`, `environment`, `instance`, and `expiresAt` (D-AC-24). It is a secret from
minting to the response body.

## Lineage (concept)

One Agent Credential Record and every token minted for it: one at bootstrap, one per renewal.
Revoking the `cid` refuses the whole lineage; revoking the agent refuses every lineage of it
(BR-RV-01). It ends at `lineageEndsAt`; the instance then re-bootstraps, starting a new lineage
(a new `cid`).

## Agent Key Ring (material)

E's own Ed25519 keys for agent credentials, **separate from the human environment credential's
ring** (D-AC-03): the current signing key and the verify keys of recent ones, by `kid`. S3 loads
the signing key; S4 (U7) loads verify keys only; S2 loads neither. Never shared with another
environment (PF §6). Delivered as a mounted secret (Infrastructure Design).

## Revocation State (record)

| Attribute | Meaning | Source |
|---|---|---|
| `environment` | E's configured identity | PF §6, §7a |
| `granularity` | `credential` or `agent` | PF FR-011, §7a |
| `target` | A `cid` (credential), or an agent identifier (agent) | PF §9 *Inputs*: "credential or logical agent reference" |
| `revokedAt` | When it was written | PF FR-011 |

**Terminal**: never removed. **Readable by no principal** (BR-RV-04). **No product writer in
M1**: written only by the test fixture with the owner role (D-AC-16).

## Revocation Answer (value)

`revoked` (either granularity), `not_revoked`, or **unknown → deny**, for (E, `cid`, agent). From
the **direct source** (a read in the caller's transaction, used by S3; D-AC-01) or the **cache**
(built in P5, used by S4 from U7): a `not_revoked` answer is served while younger than B, counted
from its read's issue; a `revoked` answer is kept; a failed read is never cached (D-AC-18).

## Checked Agent Context (value)

What P1's `checkAgentRequest` returns from a verified token (D-AC-27): **scope** (E's three
parts, from the token, equal to the configured identity), **agent**, **instance**, and **`cid`**.
U3's Checked Agent Context is scope, agent, and instance (D-AE-08); `cid` is added for S3's
record read and for U7's attribution (the credential presented).

## Bootstrap Attempt Slot (record)

U2's slot shape (D-AC-06): one of a fixed number of slots, chosen by an HMAC of (E, the presented
`agent`) under E's counter secret; it holds the live attempts in the window and the backoff
state. Keyed **known or not**: it names no registration and reveals none. Values at NFR
Requirements.

## Failed Bootstrap Attempt (record)

| Attribute | Meaning | Source |
|---|---|---|
| `environment` | E | PF §6 |
| `agent` | The registration it was attempted on (**existing registrations only**) | PF FR-027 |
| `at` | When | PF FR-027 |
| `refusedByBound` | Whether the bound refused it, or it failed after admission | U2's writer |
| `reason` | An internal class (business-rules BR-RF-AC-03): never in a response | SECURITY-03 |

Nothing presented is in it (BR-FA-03). Written off the response path (BR-FA-02).

## Attribution Record (record, U4's)

One per successful bootstrap or renewal (BR-AT-AC-01): scope E; actor `agent` with
`registration`, `instance`, `sponsor` (resolved at the write), and at renewal the presented
`cid`; target the credential; operation `exchangeBootstrap` or `renewAgentCredential`; **no
chain, origin, or re-broadening, because both operations never carry an envelope**, which the
`operation` itself states (BR-AT-AC-02).

## Envelope-Free Agent Operations (constant)

P7's closed list: `exchangeBootstrap`, `renewAgentCredential`. An agent record for one of them
carries no envelope facts; the writer refuses one that does (D-AC-33). The envelope-bearing
operations are U7's to list (business-rules §17).

## Problem Codes

No new code. **`authentication_failed`** (403) is widened to cover an agent instance at bootstrap
(D-AC-05). S3 also emits `malformed_request`, `payload_too_large`,
`unsupported_contract_version`, `too_many_attempts`, `credential_refused`, `credential_expired`,
`unavailable`, and `internal_error`, all U1's.
