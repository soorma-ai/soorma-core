# Business Logic Model: U5 `agent-registration`

**Unit**: U5 `agent-registration` (soorma-core#8). Control face, environment level
**Built against**: PF @ `prd-platform-foundations-v1.3`, ID @ `prd-identity-v1.0`
**Rules**: [business-rules.md](business-rules.md). **Entities**:
[domain-entities.md](domain-entities.md)

---

## 1. Where U5 Sits

```text
+------------------------------------------------------------+
| Environment E                                              |
|   control-gateway (S2): U4's four operations, and U5's     |
|   registerAgent and issueRegistrationSecret                |
|     P1 presenter + environment-credential checks (U4)      |
|     -> P3 readHumanAuthority: ONE read of the held set     |
|          allows = evaluateHeld (the one evaluator)         |
|     -> P3 request check: human-only class, declaration     |
|     -> P4 registration / secret write + P7 record (one Tx) |
|   env store: grants, credentials, attribution (U4);        |
|     registrations, registration secrets (U5)               |
|   read later by: U3 agent facts (one query, P4);           |
|     U6 bootstrap (secrets); U6, U7 sponsor resolution      |
+------------------------------------------------------------+
```

*Text alternative*: U5 adds two operations to S2 in each environment. Each passes U4's presenter
and environment-credential checks, then P3 reads the presenter's held set once and every test of
it goes through one evaluator (`evaluateHeld`). P3 also checks the request's sets. P4 writes the
registration or secret, and P7 its attribution record, in one transaction in E's store. U3 later
reads registrations through one agent-facts query; U6 bootstraps against the secrets; U6 and U7
resolve sponsors through the registrations. **Neither operation calls the organization level.**

---

## 2. `registerAgent` (`POST /registrations`)

**Input**: `Authorization: Bearer soorma_ec_…`; `Soorma-Contract-Version`; body
`{ agent, standingPermissions, reBroadeningDeclaration?, autonomyDeclared? }`.

1. **Body size** (step 1): over the bound is `payload_too_large`
2. **Presenter** (step 2; BR-PR-AR): exactly one `soorma_ec_`, no delegation header. An agent
   credential is `credential_refused` here, so **an agent cannot register an agent**
3. **Verify, expiry, O4, O3** (steps 3, 4; U4 BR-EC-02): E's material only; the record live and
   uncached. Yields the Checked Human Context: H = `{ organization, principal }`
4. **Contract version** (step 5)
5. **Request** (step 6; BR-RQ):
   1. Schema: `agent` well-formed; sets unique and within bounds; no extra field, no `sponsor`
   2. Accepted identifiers over both sets: else `unknown_permission`
   3. P3 request check, human-only: standing ∩ {`grant:human`, `human:manage`,
      `agent:delegate`} non-empty: `human_only_permission`
   4. P3 request check, declaration: any declared entry not contained by the standing set:
      `declaration_outside_standing`
   5. Defaults: declaration `[]`, autonomy `false`
6. **Authority and ceiling** (step 9; BR-SP):
   1. `auth = readHumanAuthority(H, E)`: one uncached read. Failure: `unavailable`
   2. `auth.allows({ agent:register })`: else `forbidden`
   3. Standing non-empty and not `auth.allows(standing)`: `exceeds_sponsor_ceiling`, pointing at
      `auth.exceeding(standing)`
   4. `snapshot = auth.snapshot()`
7. **Write** (one transaction; BR-RG, BR-AT-AR): the registration (`sponsor` = H,
   `ceilingSnapshot` = snapshot, `registeredAt` = now, `state` = `registered`) and the
   attribution record (human actor H with the credential; operation `registerAgent`; target the
   registration; scope E). `agent` taken in E: `registration_exists`, nothing written. Any other
   failure: `unavailable`, nothing written
8. **Response** `200`: the registration, every attribute

## 3. `issueRegistrationSecret` (`POST /registration-secrets`)

**Input**: as above; body `{ registration }`.

1. Steps 1 to 5 as for `registerAgent`; step 6 is the schema only
2. **Authority** (step 9; BR-SE):
   1. `auth = readHumanAuthority(H, E)`: failure `unavailable`
   2. `auth.allows({ agent:register })`: else `forbidden`
   3. The registration in E: absent, `unknown_registration`
   4. H equals its `sponsor` (exactly), **or** `auth.allows({ grant:human, human:manage })`: else
      `forbidden`
3. **Write** (one transaction): the secret record (verification material only; `issuer` = H;
   `state` = `active`) and the attribution record (operation `issueRegistrationSecret`; target
   the registration)
4. **Response** `200`: `{ id, registration, secret, issuedAt }`. The value exists nowhere else

## 4. The Agent-Facts Query (for U3)

`load(E, [a1, …, an])`: one statement over E's registrations, constrained on E's three columns
and `agent` in the list, returning `autonomyDeclared`, `reBroadeningDeclaration`, and
`standingPermissions` per found agent. Absent agents are not found. A failure rejects all. U3
calls it once at the start of its step 9 for the presenter and every distinct upstream agent, and
caches found agents only, so a registration written by U5 is visible on the next publish.

---

## 5. Worked Examples

**Setup** (U2, U4; ID §1 trace steps 1 to 5): E's configuration names H as first Admin; H holds
`grant:human`, `human:manage` (configuration grant). H signs in, obtains E's credential, and
self-grants `agent:register`, `event:publish`, `event:subscribe`. **H's held set**:
{`grant:human`, `human:manage`, `agent:register`, `event:publish`, `event:subscribe`}.

### 5.1 *Done when* 1 (ID §1 trace steps 6 to 9; TC-AR-001, 002, 007, 008)

| Request | Outcome |
|---|---|
| `registerAgent { agent: "a", standingPermissions: ["event:publish"], autonomyDeclared: true }` | `200`. Sponsor H; snapshot = H's whole held set (five entries, human-only included); standing {`event:publish`}; declaration []; autonomy `true`; `registered`. Attribution: actor H with the credential, target `a`, scope E |
| `registerAgent { agent: "b", standingPermissions: ["event:subscribe"], autonomyDeclared: true }` | `200`. Its own record and snapshot |
| `issueRegistrationSecret { registration: "a" }`, then `"b"` | `200` each, a `soorma_rs_` value once; issuer H (sponsor). Attribution target `a`, `b` |

Two registrations in E, each with its own sponsor reference and ceiling snapshot, both attributed
to H: *done when* 1.

### 5.2 Rejections

| Request (by H unless stated) | Step | Outcome |
|---|---|---|
| standing [`event:publish`, `agent:retire`] (H lacks `agent:retire`) | 9 | `exceeds_sponsor_ceiling`, pointer `/standingPermissions/1` (TC-AR-009) |
| standing [`grant:human`] (H holds it) | 6 | `human_only_permission`, `/standingPermissions/0` (TC-AR-010) |
| standing [`human:manage`]; standing [`agent:delegate`] | 6 | `human_only_permission` each (TC-AR-011) |
| standing [`event:publish`], declaration [`event:subscribe`] | 6 | `declaration_outside_standing`, `/reBroadeningDeclaration/0` (TC-AR-012) |
| standing [`billing:approve`] | 6 | `unknown_permission`, `/standingPermissions/0` (TC-AR-013; GAP-INT-006) |
| standing [`event:publish`], by D who holds only `event:publish` | 9 | `forbidden`: no `agent:register` (TC-AR-014) |
| `agent: "a"` again | write | `registration_exists`, `/agent` |
| `issueRegistrationSecret`, by D without `agent:register` | 9 | `forbidden` (TC-AR-015) |
| `issueRegistrationSecret { registration: "zz" }` | 9 | `unknown_registration`, `/registration` (TC-AR-017) |
| Agent credential `soorma_ac_…` on either operation | 2 | `credential_refused` (TC-AR-016) |
| The held-set read fails | 9 | `unavailable`, `Retry-After`; nothing written (TC-AR-021) |

### 5.3 Who may issue (D-AR-01)

D holds `agent:register` and `event:publish` and registers `d1`. A holds `agent:register`,
`grant:human`, `human:manage`. M holds `grant:human`, `human:manage` only.

| Presenter | Registration | Outcome | Why |
|---|---|---|---|
| D | `d1` | `200` | Sponsor |
| D | `a` (H's) | `forbidden` | Neither sponsor nor Admin |
| A | `d1` | `200` | Admin with `agent:register` |
| M | `d1` | `forbidden` | No `agent:register` (BR-SE-02 first) |
| H | `d1` | `200` | Admin (H holds all three) |

### 5.4 The snapshot is fixed (TC-AR-019)

After `a` is registered, H self-grants `attribution:read`. `a`'s snapshot is unchanged; a new
registration `c` by H has a snapshot with six entries.

### 5.5 Sponsorship resolution (I4; PF §7b)

An event published by an instance of `a` carries `actorChain[0].agent` = `a`. From any record
naming that hop: `a` → E's registration `a` → `sponsor` = H. Two hops, through a record that is
never deleted, and resolvable after H's deactivation when that exists (ID §7b).

---

## 6. State

| Record | States in M1 | Transitions in M1 |
|---|---|---|
| Logical Agent Registration | `registered` | none after creation |
| Registration Secret | `active` | none after creation |

PF's `suspended` and `retired` (registration) and retirement (secret) are unreachable: the
operations are absent from M1.
