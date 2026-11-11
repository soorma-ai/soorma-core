# Business Logic Model: U4 `env-human-access`

**Unit**: U4 `env-human-access` (soorma-core#7). Control face, environment level
**Built against**: ID @ `prd-identity-v1.0`, PF @ `prd-platform-foundations-v1.3`
**Rules**: [business-rules.md](business-rules.md). **Entities**:
[domain-entities.md](domain-entities.md)

---

## 1. Where U4 Sits

```text
+------------------------------------------------------------------+
| Organization level (U2)                                          |
|   org-gateway: edge (S1) + internal listener (verify keys,       |
|   principalExists, signInStatus)                                 |
+------------------------------------------------------------------+
         ^ signed internal calls, network org-internal-{env} only   
         | (issuance, renewal, grant target; verify keys cached)    
+------------------------------------------------------------------+
| Environment E                                                    |
|   control-gateway (S2, U4): issue, renew, end, grantToHuman      |
|     P1 presenter + human checks -> P3 evaluateHuman /            |
|     holdsAnyGrant -> P11 over P4's human GrantSource             |
|     P5 environment credentials; P4 grants; P7 attribution        |
|   env store: credentials, grants, attribution records (U4);      |
|     registrations, secrets (U5); agent credentials (U6)          |
+------------------------------------------------------------------+
```

*Text alternative*: S2 runs in each environment. It calls the organization level only through
signed internal calls on its own environment's internal network, and only at issuance, renewal,
and a grant's target check; the verify keys are cached. S2's own records live in the
environment's store, shared with U5 and U6.

S2 is a control-face deployable (I6). S3 and S4 (U6, U7) are separate deployables and never call
the organization level.

---

## 2. Start-Up

1. P9 loads E's part of `tenancy.yaml` and S2's secrets. Any problem: S2 does not start
   (D-EHA-28)
2. The S1 caller fetches the verify keys (BR-IS-02). If S1 is unreachable, S2 still starts;
   issuance is `unavailable` until the keys arrive, and a scheduled refresh keeps trying
3. **The first grant** (BR-FG): in one transaction, insert the configuration grant for E's first
   Admin (`grant:human`, `human:manage`), relying on the uniqueness constraint over
   configuration grants per (environment, principal):
   - inserted: also insert its attribution record (actor `configuration`, operation
     `configureFirstGrant`), and commit
   - already present (an earlier start-up, or a concurrent one that committed first): write
     nothing, and continue
   - the store fails: S2 does not start
4. Listen

**Two concurrent start-ups** (the user's Q7 addition): both attempt step 3; the constraint lets
exactly one insert commit, and the other inserts nothing, attribution included. Afterwards E holds
one configuration grant and one `configureFirstGrant` record for the first Admin.

---

## 3. `issueEnvironmentCredential` (`POST /environment-credentials`, `signIn`)

1. Body size
2. Presenter: exactly one `Authorization: Bearer soorma_si_…`, no `Soorma-Delegation`
   (BR-PR-01, 02)
3. Verify the sign-in with the cached verify keys, per U2 F-2; an unknown `kid` refetches once,
   rate-limited; no keys loaded: `unavailable`. Then expiry: `credential_expired` (BR-IS-01, 02)
4. `signInStatus(sid)` (A7): `live` gives `signInExpiresAt`; `ended` or `unknown`:
   `credential_refused`; S1 failure: `unavailable` (BR-IS-03)
5. Contract version
6. No body (D-EHA-24)
7. `holdsAnyGrant(sub, E)` (P3, through P11 over the uncached held set): false: `forbidden`
   (BR-EV-02)
8. New credential id; `expiresAt = min(now + lifetime, signInExpiresAt)` (BR-EC-04); mint the
   token with E's material
9. One transaction: the credential record (`live`, `issuedFrom = sid`) and the attribution
   record (actor human, presented `{ signIn, sid }`; target the credential). Failure:
   `unavailable` (D-EHA-17)
10. `200 { credential, expiresAt }`

## 4. `renewEnvironmentCredential` (`POST /environment-credentials/current/renewal`)

1. Body size
2. Presenter: exactly one `soorma_ec_` (BR-PR-01, 03)
3. Verify with E's material; then expiry: `credential_expired` (BR-EC-02, 06)
4. O4: asserted environment equals E's (D-EHA-12). O3: the record, uncached; absent, mismatched,
   or `ended`: `credential_refused`; store failure: `unavailable` (BR-EC-02). Then
   `signInStatus(issuedFrom)`: `live` gives `signInExpiresAt`; `ended` or `unknown`:
   `credential_refused`; S1 failure: `unavailable` (BR-EC-05)
5. Contract version
6. No body
7. `newExpiry = min(now + lifetime, signInExpiresAt)`; mint a new token for the same id
8. One transaction: update `expiresAt` **only if `state` is still `live`** (D-EHA-26; else
   `credential_refused`), and write the attribution record (presented
   `{ environmentCredential, id }`)
9. `200 { credential, expiresAt }`

## 5. `endEnvironmentCredential` (`POST /environment-credentials/current/end`)

1 to 4. As renewal, **without** `signInStatus`: the organization level is not consulted
   (D-EHA-23)
5. Contract version
6. No body
7. One transaction: set `ended`, `endedAt`, `endedBy = self` **only if still `live`** (else
   `credential_refused`), and write the attribution record
8. `204`. Every token of this credential is refused from now on (O3)

## 6. `grantToHuman` (`POST /grants`)

1 to 4. As ending (no organization-level call)
5. Contract version
6. Schema (`malformed_request`), then accepted identifiers (`unknown_permission`) (BR-GR-01, 02)
7. `evaluateHuman(actor, { grant:human })`: denied: `forbidden` (BR-GR-03)
8. Target: another organization: `unknown_principal`; else `principalExists`: `false`:
   `unknown_principal`; S1 failure: `unavailable` (BR-GR-04)
9. One transaction: the Grant (`grantedBy` = the actor and the credential; `selfGrant`) and the
   attribution record (target the grant, with `selfGrant`) (BR-GR-05)
10. `200` with the Grant

---

## 7. Worked Examples

### ID §1 trace, steps 2, 4, 5 (US-01, US-03, US-04)

| Step | What happens at E | Records written in E |
|---|---|---|
| E starts | Configuration names H as first Admin; no configuration grant for H exists | Grant `{ H, {grant:human, human:manage}, configuration, selfGrant false }`; attribution `configureFirstGrant`, actor configuration |
| H signs in at S1 (U2) | Nothing at E | — |
| H calls `issueEnvironmentCredential` with the sign-in | F-2 passes; `signInStatus` is `live` until T; H holds two permissions, so `holdsAnyGrant` is true; `expiresAt = min(now + lifetime, T)` | Credential `{ id c1, H, issuedFrom s1, live }`; attribution `issueEnvironmentCredential`, actor H with `{ signIn, s1 }` |
| H grants themselves `agent:register`, `event:publish`, `event:subscribe` | All accepted; `evaluateHuman(H, {grant:human})` allows; H is a principal of E's organization (`principalExists`) | Grant `{ H, three permissions, grantedBy H with c1, selfGrant true }`; attribution `grantToHuman`, `selfGrant true`, no origin, no chain |
| H's next request (U5's `registerAgent`) | The held set, read uncached, holds `agent:register` at once | (U5's records) |

### US-12: logout (D-EHA-01)

| Act | Effect at E |
|---|---|
| H ends the sign-in s1 at S1 | Nothing at E at once. Credential c1 stays usable in E until its expiry, which is never past s1's expiry |
| H renews c1 | `signInStatus(s1)` is `ended`: `credential_refused` (TC-EHA-020) |
| H issues a new credential with s1 | `signInStatus(s1)` is `ended`: `credential_refused` |
| H ends c1 | `ended`; every c1 token is refused from now on (TC-EHA-014). **This is the logout in E** |

### A renewed sign-in extends renewal (A7)

s1 expires at T. H renews s1 at S1, moving its expiry to T'. H renews c1 at E: `signInStatus(s1)`
answers `live` with T', so c1's new expiry is `min(now + lifetime, T')`. Under the original U2
interface (no expiry), E could not have known T'.

### Cross-environment (TC-EHA-010)

H presents c1 (E's) at E2: the token does not verify with E2's material, so
`credential_refused`. E2 learns nothing about E, and does not disclose c1's expiry.

### Two credentials, or a sign-in in the wrong place (TC-EHA-009, 015, 016)

| Presented to `grantToHuman` | Result |
|---|---|
| The sign-in | `credential_refused` (BR-PR-02) |
| An agent credential | `credential_refused`, by kind (BR-PR-04) |
| An agent credential and c1, as two `Authorization` headers | `credential_refused` (BR-PR-01, 05) |

### A constructed agent attribution record (I4, D-EHA-04)

U4's test writes, with the agent actor kind, a record for a constructed `publish` by B's
instance i-B forwarding A's envelope:

| Field | Value |
|---|---|
| `scope` | E |
| `actor` | `{ agent: B, instance: i-B, credential: ac-B, registration: r-B, sponsor: { O, H } }` |
| `chain` | `[i-A, i-B]` |
| `origin` | `{ mode: autonomous }` |
| `reBroadening` | `{ loadBearing: true, hop: 1 }` |

Scope, actor, chain, origin, the resolved sponsor, and the re-broadening outcome are read back
**from this record alone**. The same at zero hops: `chain [i-A]`,
`reBroadening { loadBearing: false }`.

---

## 8. Problem Emission

Every refusal is a Problem through P1 (D-EHA-21), with `type`, `title`, `status`, `code`,
`instance`, `Soorma-Contract-Version`, and `Soorma-Request-Id`; `WWW-Authenticate: Bearer` on a
401, `Retry-After` on a 503. The two new codes are `unknown_principal` and `unknown_permission`.
