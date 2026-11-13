# Component Methods: soorma-core M1

Signatures and purpose only. **Business rules, validation detail, error shapes, paths,
and field encodings belong to Functional Design** (per unit) and to the contract schema.
Types are logical; the concrete schema is generated per M1-TECH-02.

**Notation**: `operation(inputs) → output | Refusal`. *Presents* means the credential sent
with the request. *Refusal* is a denial or rejection, which never discloses another
environment (ID FR-014's non-disclosure applies where it applies).

---

## 1. Edge Operations (the wire contract)

### S1 `org-gateway` (organization level, control face)

| Operation | Inputs | Output | Purpose | M1-FR |
|---|---|---|---|---|
| `firstAuthenticate` | principal id; enrollment material; new K; P enrollment (optional, unless required) | `SignIn` | Replace enrollment material with the human's own; principal becomes `active` | 17, 16 |
| `authenticate` | principal id; K; P (where enrolled or required) | `SignIn` | Organization sign-in | 19, 17, 18 |
| `renewSignIn` | presents `SignIn` | `SignIn` | Self-service renewal | 21 |
| `endSignIn` | presents `SignIn` | ended | Self-service end, which is the logout | 21 |
| `changeMaterial` | current material (K, and P where enrolled); new K or new P | changed | Self-service change by presenting the current material. Includes **enrolling P by presenting K without a sign-in** where P is required (M1-TECH-07) | 21, 17 |

`authenticate` and `firstAuthenticate` are unauthenticated surfaces (P8, per principal).

### S2 `control-gateway` (environment E, control face)

| Operation | Inputs | Output | Purpose | M1-FR |
|---|---|---|---|---|
| `issueEnvironmentCredential` | presents `SignIn` | `EnvironmentCredential` (bound to E) | E's credential issuance; the only place E accepts a sign-in | 20, 19 |
| `renewEnvironmentCredential` | presents `EnvironmentCredential` | `EnvironmentCredential` | Renewal; never outlives the sign-in or revocation | 20 |
| `endEnvironmentCredential` | presents `EnvironmentCredential` | ended | Self-service end | 21 |
| `grantToHuman` | presents `EnvironmentCredential`; target principal id; permission set | `Grant` | ID FR-015 ceiling; self-grants recorded; only accepted identifiers (GAP-INT-006) | 15, 12 |
| `registerAgent` | presents `EnvironmentCredential`; standing set; re-broadening declaration; autonomy declared; client-chosen identifier (if the contract allows; Functional Design decides) | `Registration` (reference, ceiling snapshot) | PF FR-007, FR-016, FR-017. The sponsor is the presenting human | 03 |
| `issueRegistrationSecret` | presents `EnvironmentCredential`; registration reference | `RegistrationSecret` (returned once) | PF FR-008 issuance; issuer recorded | 04 |

No operation in S2 accepts an agent credential in M1 (agent registration and issuance are
absent). None carries an envelope (PF FR-001 v1.3).

### S3 `data-gateway` (environment E, data face)

| Operation | Inputs | Output | Purpose | M1-FR |
|---|---|---|---|---|
| `exchangeBootstrap` | registration reference; registration secret; asserted instance id. **No envelope** (GAP-INT-008, option 1) | `AgentCredential` (registration, E, instance, expiry) | PF FR-009; unauthenticated surface (P8, per registration) | 05 |
| `renewAgentCredential` | presents `AgentCredential`. **No envelope** (GAP-INT-008, option 1) | `AgentCredential` | PF FR-010; never weaker than issuance | 06 |

### S4 `event-ingest` (environment E, data face)

| Operation | Inputs | Output | Purpose | M1-FR |
|---|---|---|---|---|
| `publish` | presents `AgentCredential`; draft envelope (client contract version, trace context, forwarded inbound context if any; **no platform-stamped field**); payload (opaque, I9) | accepted | Publish to E's namespace | 11, 01, 08 |
| `subscribe` | presents `AgentCredential`; draft envelope, as for `publish` | **SSE stream** (`text/event-stream`); each event's data is a **`Delivery`** (`contract/delivery.schema.json`: stamped envelope and payload) | Subscribe to E's namespace; live delivery only. The stream ends within the propagation bound on expiry or revocation | 11, 01, 08 |

`subscribe` opens the stream with a request that can carry a draft (for example, a POST
answered with `text/event-stream`). The exact method and path are Functional Design's.
Re-subscribing with a renewed credential is a new stream; overlap handling is Functional
Design's (plan Q4 note).

*Corrected at U7 Functional Design (2026-11-12, plan Q1 to Q6)*: `publish` is `POST /events` with a closed body `{ draft, payload }`, answered `202` with no body; `subscribe` is `POST /subscriptions` with `{ draft }`, answered `200` `text/event-stream` with `delivery` events and one final `end` event (`{ code }`). **At most one stream per credential lineage in E**: a later subscribe supersedes the earlier stream, across instances through E's fan-out channel. Neither operation returns its own stamped envelope. See `construction/event-transport/functional-design/business-rules.md` (D-ET-01 to 06).

---

## 2. Internal Interfaces (`packages/`, `seams/`)

### P1 `perimeter`
| Method | Inputs | Output | Purpose |
|---|---|---|---|
| `classifyPresenter` | the credentials on a request; the surface | presenter kind, or Refusal | ID §8b's matrix: which presenter reaches which surface (ID FR-023; A-4). **Refusal by kind needs no verification**, so S3 and S4 refuse human credentials without organization-level material |
| `checkAgentRequest` | agent credential; E; the surface's obligation set | checked context, or Refusal | O1 to O4, O9 to O11 for agent traffic; O5 to O8 and O12 through P2 and P3 |
| `checkHumanRequest` | human credential (sign-in or environment credential); E or the organization | checked context, or Refusal | ID §8b's human-credential table: O1 to O4, O8 to O11 |

### P2 `envelope`
| Method | Inputs | Output | Purpose |
|---|---|---|---|
| `validateDraft` | draft | valid draft, or Reject(field) | **The draft's top level is closed**: any field the contract does not define is rejected, and so is every platform-stamped field, **origin mode included** (GAP-INT-007). Trace context must be well-formed (W3C), and the client contract version must be present and accepted. **`inbound` stays open**: the forwarded envelope is carried as received, its seal is verified for this environment (a failure is rejected under O5), and its unknown fields are preserved into the stamped envelope (PF FR-005(a)) |
| `stamp` | valid draft; checked context; origin; chain; re-broadening hop (if any) | `Envelope` and its seal | Writes the six stamped fields; appends the instance to the chain; enforces `maxChainDepth`; seals the envelope with this environment's material |

*Corrected at U1 Functional Design (2026-11-08, plan Q6 and Q11): the draft is closed only at its
top level, and envelopes are sealed. See `construction/wire-contract/functional-design/business-rules.md`.*

### P3 `authority`
| Method | Inputs | Output | Purpose |
|---|---|---|---|
| `resolveOrigin` | inbound envelope (if forwarded); registration (autonomy declared) | origin, or Refusal (O12) | Autonomous from the registration; propagated unchanged from inbound; otherwise denied |
| `evaluateAgent` | registration standing set; chain terms; delegating principal term (*yes* in autonomous origin); declared re-broadening set; required permission | Allow { re-broadening load-bearing at hop? }, or Deny | **The one place the intersection is computed.** Re-broadening per PF §8b |
| `evaluateHuman` | the human's grants in E; required permission | Allow, or Deny | Direct human operations (ID §8b O8) |

### P4 `registry`
| Method | Inputs | Output | Purpose |
|---|---|---|---|
| `createRegistration` | sponsor; standing set; declaration; autonomy flag | `Registration`, or Reject | Checks the ceiling against the sponsor's **held** set, the human-only class, declaration ⊆ standing, and accepted identifiers; records the snapshot |
| `getRegistration` | reference | `Registration`, or not found | Used by bootstrap, ingest, and authority |
| `heldSet` | principal; E | permission set | The union of the principal's grants in E |
| `createGrant` | target principal; set; granted-by (principal or configuration) | `Grant`, or Reject | Accepted identifiers only; self-grant flagged |
| `createSecret` | registration; issuer | secret (once), with verification material stored | Issuer recorded |
| `isAcceptedIdentifier` | identifier | yes or no | The plane-declared set (GAP-INT-006 work-around) |

### P5 `credentials`
| Method | Inputs | Output | Purpose |
|---|---|---|---|
| `mint` | kind (agent or human environment); subject; E; lifetime bound | credential | With E's own minting material only |
| `verify` | credential; E | claims, or Refusal | O1 and O2; O4 (bound to E) |
| `isRevoked` | credential reference | revoked, not revoked, or **unknown → deny** | O3: cached at most the propagation bound, failing closed |
| `markEnded` | credential reference | ended | Self-service end (ID FR-011). Agent revocation has no product path (test-only seeding) |

### P6 `identity-resolution` (implements `seams/identity-resolution`)
| Method | Inputs | Output | Purpose |
|---|---|---|---|
| `resolve` | material type; material | agent registration reference, human principal reference, or rejection | Registration secret (environment); K and P (organization). Decides identity only |

### P7 `attribution`
| Method | Inputs | Output | Purpose |
|---|---|---|---|
| `record` | scope; actor (instance, or human and the credential presented); chain; origin (or none for a human); operation; flags (self-grant, configuration) | stored | PF FR-025 recording; no read surface |

### P8 `abuse-bound`
| Method | Inputs | Output | Purpose |
|---|---|---|---|
| `admit` | subject (registration or principal); surface | admitted, or Refusal | The bound. Value and shape are set at NFR Requirements |
| `recordFailure` | subject; surface | stored | Failures recorded against the subject |

### P9 `config`
| Method | Inputs | Output | Purpose |
|---|---|---|---|
| `loadOrganization` | configuration source | organization, projects, environments, membership | Configured, never inferred |
| `loadEnvironment` | configuration source | E's identity; first Admin; first grants | Applies the first grant (*granted-by* = configuration). The first Admin's principal is ensured by S1 at the organization level (`ensureFirstAdmin`, US-01), never by an environment |

### P10 `org-identity`
| Method | Inputs | Output | Purpose |
|---|---|---|---|
| `ensureFirstAdmin` | principal id; enrollment material reference | `pending` principal, or exists | ID FR-004: registers only if absent |
| `principalExists` | principal id | yes or no | Internal lookup for `grantToHuman` targets; not ID FR-017's directory read |
| `verifyOnlyMaterial` | — | verify-only sign-in material | Distributed to each environment's S2 only; can verify, never mint |
| `issueSignIn`, `renewSignIn`, `endSignIn` | as S1 | `SignIn` | Behind S1 |
| `setMaterial` | principal; class; current material; new material | changed | Behind S1 |

### P11 `policy-decision` (implements `seams/policy-decision`)
| Method | Inputs | Output | Purpose |
|---|---|---|---|
| `contains` | permission set; required permission | contained, or not | **Containment only.** The minimal model: flat, opaque identifiers, deny by default |

*Corrected at U3 Functional Design (2026-11-10, plan Q2 and Q4; P-04): P11 also implements
`grantedSet(principal, environment)`, reading through a `GrantSource` port that U5 and U4 fill;
`contains` takes a required **set**. P3 adds `createEnvelopeAdmission(dependencies).admit(request)`, the one entry point a
surface imports (consistency fix from NFR Design, 2026-11-10: formerly `admitEnvelopeRequest`), which runs check-order steps 5 to 10 through P2 and P3. See
`construction/authority-evaluation/functional-design/business-rules.md` (D-AE-02, D-AE-04,
D-AE-10).*

*Corrected at U4 Functional Design (2026-11-11, plan Q2 to Q4; P-06, P-07): P3 implements
`evaluateHuman` over the seam (`grantedSet`, then `contains`) and adds `holdsAnyGrant` for
issuance; P4's `heldSet` is P11's human `GrantSource`, read uncached; P7's `record` takes three
actor kinds (human, configuration, agent), and for an agent the resolved sponsor and, with an
envelope, the chain, origin, and re-broadening outcome; P10's internal `signInStatus` answers
`live` with the sign-in's current expiry (U2 amendment A7). See
`construction/env-human-access/functional-design/business-rules.md` (D-EHA-02, D-EHA-04,
D-EHA-13, D-EHA-14).*

*Corrected at U4 NFR Design (2026-11-11, plan Q2 A and Q4 A): two internal packages are added.*

*`service-kit` (shared runtime; no method holds state of its own):*
- *`verifySignIn(token, keySource, organization, now, { expSeconds, iatAheadSeconds? })` → `valid`, `expired`, `invalid`, or `unknownKey`*
- *`signInternalRequest`, `verifyInternalRequest`*
- *`thumbprint`*
- *`pseudonym(key, reference)`*
- *`secretEqual`*
- *`Semaphore.acquire(deadline)`: returns a release-once function*
- *`migrate(client, dir, lockKey)`*
- *`poolConfig`*
- *the problem documents (`ProblemError`, `problemResponse`)*
- *the HTTP adapter, the exception filter, the security log, the contract validator, and the
  health listener*

*`env-store`:*
- *`pool(settings)`*
- *`withTransaction(fn: (tx: Tx) => …)`: commits only if `fn` returns*
- *P4's, P5's, and P7's write methods take the caller's `Tx`*

*`credentials.mint` returns the token as `SecretText`, and `credentials.verify` takes it as
`SecretText`. See `construction/env-human-access/nfr-design/logical-components.md` (§2) and
`nfr-design-patterns.md` (NP-EHA-01, 06, 14, 15).*

*Corrected at U5 Functional Design (2026-11-11, plan Q1 to Q6; P-03 with the user's condition):
`registerAgent` takes a **client-chosen** `agent` (the "if the contract allows" settled; a taken
one is `registration_exists`); `issueRegistrationSecret` names its registration in the body.
P3 extracts **`evaluateHeld`** as the one evaluator of a human's held set (`evaluateHuman`
becomes "read, then `evaluateHeld`", unchanged in signature and results) and adds
**`readHumanAuthority`** (one read; `allows`, `exceeding`, `snapshot`) and the registration
request check (human-only class; declaration ⊆ standing). **P4's `createRegistration` checks
nothing itself**: the ceiling, the human-only class, and declaration ⊆ standing are P3's, and
P4 writes what S2 passes it (with the snapshot from P3's read). P4 adds the agent-facts query
behind U3's port, replacing `getRegistration` for authority. A registration may hold several
active secrets. See `construction/agent-registration/functional-design/business-rules.md`
(D-AR-02, D-AR-04, D-AR-05, D-AR-07, D-AR-10, D-AR-19).*

*Corrected at U6 Functional Design (2026-11-12, plan Q4 A, Q6 A, Q9 A; P-18): `exchangeBootstrap`
takes `{ agent, secret, instance }`; the **endpoint names the environment**, so the body names
none; the secret's typed prefix declares its material type. P1 adds **`checkAgentRequest`**
(presentation, O1, O2, O4, then O3 through a revocation source the caller passes), returning the
Checked Agent Context with the credential's `cid`. P5's `isRevoked` answers for **both
granularities** (the credential's `cid`, the logical agent) and is read directly by S3 and through
the cache by S4. P6's agent half `resolve` returns the registration reference and the secret
record's id, deciding identity only. P8's `admit` keys on the **presented** agent identifier,
known or not. Renewal keeps the credential's `cid` (the lineage) and never extends it past a
maximum age. See `construction/agent-credentials/functional-design/business-rules.md` (D-AC-01,
D-AC-02, D-AC-04, D-AC-06, D-AC-09, D-AC-14, D-AC-20, D-AC-27).*
