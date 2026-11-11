# Domain Entities: U4 `env-human-access`

**Unit**: U4 `env-human-access` (soorma-core#7). Control face, environment level. Adds S2
`control-gateway` (its human operations)
**Built against**: ID @ `prd-identity-v1.0` (the main source), PF @ `prd-platform-foundations-v1.3`
**Companions**: [business-rules.md](business-rules.md) (rules BR-* and decisions D-EHA-01 to
D-EHA-31), [business-logic-model.md](business-logic-model.md),
[l1-coverage-matrix.md](l1-coverage-matrix.md),
[invariant-coverage-matrix.md](invariant-coverage-matrix.md)

U4 introduces the **environment store**: one per environment deployment (Application Design Q1
A). Its technology is NFR Requirements'. Every record here lives in it, carries its environment,
and is read only with a constraint on it (D-EHA-29). Field names are camelCase (D-WC-01). Wire
shapes are added to `contract/control-gateway.openapi.yaml` at Code Generation (§13 of the
business rules).

---

## Entity Map

| Entity | Kind | Owner (module) | Lifetime | Source |
|---|---|---|---|---|
| Human Environment Credential | record | P5 `credentials` | issued → ended or expired; never deleted in M1 | ID §7a; FR-010 |
| Environment Credential Token | value (wire) | P5 | until its expiry | ID FR-010; credentials.md |
| Grant | record | P4 `registry` | written once; never deleted in M1 (revocation absent) | PF §7a *Permission Grant*; ID FR-004, FR-015 |
| Held Set | view | P4, through the human `GrantSource` | one request | PF FR-016 (*grantable = held*), §8b |
| Accepted-Identifier Set | constant | P4 | the build | GAP-INT-006 work-around; M1-FR-15 |
| Attribution Record | record | P7 `attribution` | written once; never modified (pruning absent in M1) | PF FR-025; ID §7b *Recoverability* |
| Checked Human Context | value | P1, from the verified credential | one request | ID §8b |
| Sign-In Claims | value | P1, from the verified sign-in (U2's token) | one request | ID FR-009; U2 F-2 |
| Sign-In Status | value (from S1) | the S1 caller | one call; never cached | U2 BR-INT-05, **amendment A7** (D-EHA-02) |
| Verify Keys | cached value (from S1) | the S1 caller | refreshed on a schedule and on an unknown `kid` | ID FR-009; U2 F-1 |
| Environment Configuration | value | P9 `config`, the environment half | the process | ID FR-004; PF FR-022 |
| Problem Table additions | constant | P1 | the build | D-EHA-05, 06 |

---

## Human Environment Credential (record)

| Attribute | Meaning | Source |
|---|---|---|
| `id` | The credential's identifier: at least 128 random bits, unique within E, composed with E (BR-ID-07). Format NFR Design's (D-EHA-30) | ID §6 *Credential identifiers*; PF §6 |
| `environment` | `{ organization, project, environment }`: E's **configured** identity | ID §6; PF FR-022 |
| `subject` | `{ organization, principal }`, the human principal (composed, never allocated) | ID FR-001, §6 |
| `issuedFrom` | The sign-in's `id` (U2's `sid`) | ID §7a *issued-from* |
| `issuedAt` | When E issued it | ID §7a |
| `expiresAt` | The **current** expiry. Set at issuance and moved later at each renewal, never past the sign-in's current expiry (BR-EC-04) | ID FR-010; D-EHA-02 |
| `state` | `live` → `ended`. Expiry is not a state: a credential past `expiresAt` is expired whatever its state | ID §7a (*revoked* is `ended` here: self-service end is the only M1 path) |
| `endedAt`, `endedBy` | Set together when ended; `endedBy` = `self` in M1 | ID FR-011 |

**Carries no permission set.** Authority is read per request from the Grants (D-EHA-10).

## Environment Credential Token (wire)

Opaque to clients: `soorma_ec_` followed by a body whose format NFR Design chooses (BR-CR-05: an
RFC 6750 `b64token`, at most 4096 characters). It asserts, at least:

| Claim | Meaning |
|---|---|
| kind | Human environment credential (must match the `soorma_ec_` prefix, BR-CR-04) |
| credential id | The record's `id` |
| subject | `{ organization, principal }` |
| environment | `{ organization, project, environment }` |
| issued-at, expiry | This token's own; renewal mints a new token for the same `id` |

It asserts **a binding, never a location or code identity** (ID §8b *What a credential
asserts*). It is minted and verified with **E's own material only** (ID §6; PF §6).

## Grant (record)

| Attribute | Meaning | Source |
|---|---|---|
| `id` | Identifier, unique within E | BR-ID-07 |
| `environment` | E's configured identity | PF §7a *Environment scope* |
| `principal` | `{ organization, principal }`: a human principal of E's organization | PF §7a *Principal reference*; ID FR-001 |
| `permissions` | A non-empty set of accepted permission identifiers (flat, opaque, set semantics) | PF FR-018, §7a |
| `grantedAt` | When written | PF §7a |
| `grantedBy` | **One of**: `{ kind: 'principal', principal: { organization, principal }, credential: <environment credential id> }`, or `{ kind: 'configuration' }` (the environment's configuration) | PF §7a *Granted-by*; ID FR-004 |
| `selfGrant` | `true` when `grantedBy` is a principal equal to `principal`, both parts compared exactly; `false` otherwise, and always `false` for the configuration | ID FR-015 ("every self-grant is recorded"); BR-ID-08 |

**At most one configuration grant per principal in E** (D-EHA-07): the store enforces it.

## Held Set (view)

The union of `permissions` over every Grant to a principal in E. Read on every call, uncached
(D-EHA-14; U3 NFR-AE-14). It is what P11's human `GrantSource` returns, and so what
`grantedSet({ kind: 'human', principal }, E)` returns. An empty set is the bottom (L3).

## Accepted-Identifier Set (constant)

The plane-declared identifiers (M1-FR-15; GAP-INT-006, soorma-prd#24):

| Declared by | Identifiers |
|---|---|
| PF | `agent:register`, `credential:revoke`, `agent:retire`, `grant:human`, `event:publish`, `event:subscribe`, `attribution:read` |
| ID | `human:manage`, `agent:delegate` |

Defined once, in P4 (`packages/registry`). Used by `grantToHuman` (U4) and by U5's standing
sets. The human-only class (`grant:human`, `human:manage`, `agent:delegate`) is defined in P3
(U3 D-AE-03) and is a subset of it.

## Attribution Record (record)

One record per state-changing operation (D-EHA-03). **The whole shape is defined here, once**,
for every actor kind (D-EHA-04). Everything FR-025's grant-scoped read would return (scope,
actor, chain, origin, resolved sponsor) is recoverable **from the record alone**.

| Attribute | Present for | Meaning | Source |
|---|---|---|---|
| `id` | all | Identifier, unique within E | BR-ID-07 |
| `recordedAt` | all | When the operation took effect | PF FR-025 |
| `requestId` | all but the configured grant | The `Soorma-Request-Id` of the request | SECURITY-03 (correlation) |
| `scope` | all | `{ organization, project, environment }`: E's configured identity | PF §7b *Recoverability* (Scope); ID §7b |
| `operation` | all | The operation's identifier (§ *Operation identifiers* below) | PF FR-025 |
| `actor` | all | **One of the three kinds below** | PF §7b; ID §7b *Recoverability* (Actor) |
| `target` | all | What the operation acted on (below) | PF FR-025 |
| `selfGrant` | `grantToHuman` | As on the Grant | ID FR-015 |
| `chain` | agent actor, envelope-bearing operation | The stamped envelope's actor chain, as stamped, most recent last | PF FR-006, §7b (Actor chain) |
| `origin` | agent actor, envelope-bearing operation | `{ mode, delegatingPrincipal? }` as stamped | PF §7b (Origin) |
| `reBroadening` | agent actor, envelope-bearing operation | `{ loadBearing: boolean, hop?: number }`: U3's outcome for this hop (U3 BR-ST-08); `hop` present exactly when `loadBearing` | PF FR-017, §8b *Record*; the user's Q4 addition |

**Actor kinds**:

| Kind | Fields | Written by |
|---|---|---|
| `human` | `principal` `{ organization, principal }`; `presented`: `{ kind: 'signIn', id }` or `{ kind: 'environmentCredential', id }` | U4, U5 |
| `configuration` | none beyond the kind: "the environment's configuration" | U4 (the first grant) |
| `agent` | `agent` (logical agent id); `instance` (instance id, asserted, never verified); `credential` (agent credential id, where one was presented); `registration` (the registration reference); **`sponsor`**: `{ organization, principal }`, the registration's sponsor **as resolved when the record was written** | U6, U7 |

**Rules on the shape** (BR-AT):
- A `human` or `configuration` actor has **no `chain`, no `origin`, no `reBroadening`**: a direct
  human operation has no origin mode (ID §7b; ID FR-022)
- An agent actor on an envelope-bearing operation (U7) has all three. An agent actor on an
  operation with no envelope (U6's bootstrap and renewal; GAP-INT-008 work-around) has none of
  them, and U6 records why
- `sponsor` is present exactly for an agent actor (the user's Q4 addition)

**Operation identifiers** written by U4: `issueEnvironmentCredential`,
`renewEnvironmentCredential`, `endEnvironmentCredential`, `grantToHuman`, `configureFirstGrant`.
Later units add their own (`registerAgent`, `issueRegistrationSecret`, `exchangeBootstrap`,
`renewAgentCredential`, `publish`, `subscribe`).

**Targets** written by U4: `{ kind: 'environmentCredential', id }` (the three credential
operations); `{ kind: 'grant', id, principal: { organization, principal } }` (`grantToHuman`,
`configureFirstGrant`).

## Checked Human Context (value)

Built by P1 at step 4, from a verified environment credential whose record is `live`:
`{ credential: id, subject: { organization, principal }, environment, issuedFrom }`. The
environment is the credential's, already compared equal to E's configured identity (D-EHA-12).
Every later step reads identity **only** from it (I3).

## Sign-In Claims (value)

From U2's token, verified per U2 F-2: `sid`, `sub`, the organization (from `iss`,
`urn:soorma:org:{organization}`), `iat`, `exp`, `auth_time`, `amr`, `jti`. E uses `sid` and
`sub`; the rest is checked, not used.

## Sign-In Status (value, from S1; U2 amendment A7)

| Answer | When |
|---|---|
| `{ status: 'live', expiresAt }` | The sign-in record is `live`, its current expiry has not passed, and its principal is `active`. `expiresAt` is the sign-in's **current** expiry (moved by each renewal at S1) |
| `{ status: 'ended' }` | Otherwise, for an existing sign-in of this organization: ended, expired, or its principal not `active` |
| `{ status: 'unknown' }` | No sign-in with that id in this organization |

Nothing else (minimum disclosure, as BR-INT-05). **Never cached** by E.

## Verify Keys (cached value, from S1)

The organization's sign-in verify keys, as a JWKS from `verifyOnlyMaterial`: **public only;
they can verify, never mint** (ID FR-009). Cached by each S2 instance; refreshed on a schedule
and on an unknown `kid`, rate-limited (U2 F-1). The schedule and rate are NFR Design's.

## Environment Configuration (value)

E's part of `deploy/local/config/tenancy.yaml`, validated at start-up (P9, the environment
half): the organization, project, and environment identity; the first Admin's identifier (only
the identifier, never enrollment material: U2 D-OI-12); and the names of S2's secrets (E's
minting material, E's caller key for S1, E's log-pseudonym key). **Identity comes from this file
only**, never from the host (PF FR-022; O11). The secrets' layout is Infrastructure Design's.

## Problem Table Additions (constant, in P1)

| Code | Status | Detail |
|---|---|---|
| `unknown_principal` | 400 | `errors[]` with one entry, `pointer` `/target` (D-EHA-05) |
| `unknown_permission` | 400 | `errors[]`, one entry per identifier not accepted, `pointer` `/permissions/{i}`, at most 10 by pointer (D-EHA-06) |

---

## Relationships

| From | To | Cardinality | Constraint |
|---|---|---|---|
| Human Environment Credential | Organization Sign-In (S1's) | many to one (`issuedFrom`) | Referenced by id only; E holds no sign-in record |
| Human Environment Credential | Human Principal (S1's) | many to one (`subject`) | Referenced by `{ organization, principal }` only |
| Grant | Human Principal | many to one | Same organization as E; the target existed when written (BR-GR-04) |
| Grant (configuration) | Human Principal | at most one per principal in E | D-EHA-07, enforced by the store |
| Held Set | Grant | union of all to the principal in E | — |
| Attribution Record | its operation's write | one to one, **same transaction** | D-EHA-17 |
| Attribution Record (agent actor) | Logical Agent Registration (U5's) | many to one | `registration` and `sponsor` both recorded |

Every relationship stays inside E: no record references another environment's record (I1).
