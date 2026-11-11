# Services and Orchestration: soorma-core M1

The **services** are the four deployables, S1 to S4 ([components.md](components.md)). Each
is stateless, and each discharges its own perimeter obligations (O10). Orchestration below
follows the user journey ([stories.md](../user-stories/stories.md)). Each step names the
service, then the internal modules it calls, in order. Business rules are Functional
Design's.

| Service | Surface | NFR profile | Serves |
|---|---|---|---|
| S1 `org-gateway` | Organization, control | ID §10: interactive sign-in; highest durability of the principal record | Humans (sign-in, self-service) |
| S2 `control-gateway` | Environment, control | PF §10 and ID §10: low throughput; read-your-writes; every operation attributed | Humans in E |
| S3 `data-gateway` | Environment, data | PF §9: startup and periodic classes | Agent instances (bootstrap, renewal) |
| S4 `event-ingest` | Environment, data | PF §9: the per-request hot path; revocation read never dominant | Agent instances (publish, subscribe) |

---

## Orchestration by Journey Step

**US-01: Configure** (start-up; no request)
1. S1 starts: `config.loadOrganization` → `org-identity.ensureFirstAdmin` for each
   environment's first Admin. The principal is registered `pending` with enrollment
   material only if absent
2. Each environment's S2 starts: `config.loadEnvironment` → `registry.createGrant(H,
   {grant:human, human:manage}, granted-by = configuration)` → `attribution.record`
3. Each environment's **S2** fetches `org-identity.verifyOnlyMaterial` (internal, cached). S3 and S4 do not

**US-02: Activate and sign in** (S1)
1. `perimeter.classifyPresenter` (none: an unauthenticated surface) → `abuse-bound.admit`
   (per principal)
2. `identity-resolution.resolve(enrollment material)` → `org-identity.setMaterial(K, and
   P)` → principal `active` → `issueSignIn`
3. Failures: `abuse-bound.recordFailure`. Enrollment reuse is refused

**US-03: Environment credential** (S2 in E)
1. `perimeter.checkHumanRequest(SignIn)`: verified with **verify-only** material; accepted
   only at issuance
2. `registry.heldSet(H, E)` is non-empty (a grant in E) → `credentials.mint(human, H, E)`

*Corrected at U4 Functional Design (2026-11-11, D-EHA-13, D-EHA-02)*: step 1 also calls
`signInStatus` (fail closed); step 2 is `authority.holdsAnyGrant(H, E)`, so no module but P3
tests a human's set (I5); the credential's expiry is capped at the sign-in's current expiry.
See `construction/env-human-access/functional-design/business-rules.md`.

**US-04: Self-grant** (S2)
1. `perimeter.checkHumanRequest(EnvironmentCredential)` → `credentials.isRevoked`
2. `authority.evaluateHuman(grants, grant:human)` → `registry.isAcceptedIdentifier` for
   each requested identifier → `org-identity.principalExists(target)` →
   `registry.createGrant` (self-grant flagged) → `attribution.record` (human actor; no
   origin)

**US-05: Register A and B** (S2)
1. `perimeter.checkHumanRequest` → `credentials.isRevoked` →
   `authority.evaluateHuman(agent:register)`
2. `registry.createRegistration`: the ceiling against `heldSet`, the human-only class,
   declaration ⊆ standing, accepted identifiers. The snapshot is recorded; both declare
   autonomy
3. `attribution.record`

**US-06: Issue secrets** (S2)
1. As US-05, step 1 → `registry.createSecret(registration, issuer = H)` →
   `attribution.record`

**US-07: Bootstrap and renew** (S3)
1. Bootstrap: `abuse-bound.admit(registration)` → `identity-resolution.resolve(secret)` →
   `registry.getRegistration` (live, not retired) → `credentials.mint(agent, …)`.
   Failures go to `abuse-bound.recordFailure`
2. Renew: `perimeter.checkAgentRequest` (O1 to O3) → `credentials.isRevoked` → `mint`
3. Neither call carries an envelope (GAP-INT-008 work-around, option 1)

**US-08: Publish and subscribe** (S4)
1. `perimeter.classifyPresenter`: agent credential alone. Human credentials and
   delegation credentials are refused (ID FR-023; A-4)
2. `perimeter.checkAgentRequest` (O1 to O4, O9 to O11) → `credentials.isRevoked`, failing
   closed
3. `envelope.validateDraft`: reject stamped fields, origin included (GAP-INT-007)
4. `authority.resolveOrigin`: autonomous from the registration, or **denied (O12)**
5. `authority.evaluateAgent(event:publish | event:subscribe)` →
   `policy-decision.contains`
6. `envelope.stamp` → publish: hand to the **env fan-out channel**; subscribe: open the
   SSE stream, whose events each carry a `Delivery`
7. `attribution.record`
8. A delivery timer and revocation checks end the stream within the propagation bound
   (T-2)

**US-09: B's envelope** (S4 delivering to B)
1. The delivered envelope is the one `stamp` produced: scope E, `autonomous`, chain
   `[A's instance]`
2. B, triggered, calls `subscribe` **forwarding A's envelope**. `resolveOrigin`
   propagates it; `evaluateAgent` with A's term lacking `event:subscribe` and B's
   declaration holding it gives Allow, re-broadening load-bearing at B's hop. `stamp`
   records it, the chain grows, and `maxChainDepth` is enforced

**US-10: Cross-environment** (S4 in E, and S3 in E)
1. `credentials.verify(credential from E2, E)` → Refusal (O4). E holds only its own
   minting material and has no means to accept E2's
2. Nothing on E's fan-out channel reaches E2: one channel per environment deployment

**US-11: Stamped field in a draft** (S4. S3 takes no draft, per GAP-INT-008)
1. `envelope.validateDraft` → Reject(field). It is never overwritten

**US-12: Logout and material change** (S1, S2)
1. S1 `endSignIn`, `renewSignIn`, and `changeMaterial` (current material required)
2. S2 `endEnvironmentCredential` → `credentials.markEnded` → refused thereafter (O3)

---

## Cross-Service Interactions

| From | To | What | Pattern | On a per-request path? |
|---|---|---|---|---|
| S2 (each environment) | S1, organization level | Verify-only sign-in material | Internal pull, cached; refreshed on rotation | **No** (ID FR-009) |
| S2 | Organization level | `principalExists` for a grant target | Internal synchronous call, control face only | No; control operations only |
| S4 instance | S4 instances in the same E | Live events | Env fan-out channel | Yes, within E only |
| Any S | Env store, org store | Records | Datastore access; technology at NFR Requirements | As the operation requires |

**S3 and S4 never call the organization level**, so agent data-plane traffic is unaffected by an organization-level outage (M1-NFR-08). They refuse human credentials by kind, which needs no verification. **No service calls another environment's service.** The organization level is the only
cross-environment component. It holds human records and material only, never grants or
credentials (ID §6).
