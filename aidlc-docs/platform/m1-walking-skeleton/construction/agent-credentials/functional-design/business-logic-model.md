# Business Logic Model: U6 `agent-credentials`

**Unit**: U6 `agent-credentials` (soorma-core#9). Data face, environment level
**Built against**: PF @ `prd-platform-foundations-v1.3`, ID @ `prd-identity-v1.0`
**Rules**: [business-rules.md](business-rules.md). **Entities**:
[domain-entities.md](domain-entities.md). **B**, **L**, **M**: the propagation bound, the
credential's lifetime, a lineage's maximum age (NFR Requirements)

---

## 1. Where U6 Sits

```text
+------------------------------------------------------------+
| Environment E                                              |
|   data-gateway (S3), new: exchangeBootstrap and            |
|   renewAgentCredential; no envelope on either              |
|     bootstrap: P8 bound -> P6 agent half (secret) ->       |
|       registration state -> agent revocation (direct) ->   |
|       P5 record + P7 record (one Tx) -> token (agent ring) |
|     renewal: P1 checkAgentRequest (O1, O2, O4, O3 direct)  |
|       -> record, registration -> expiry + P7 (one Tx)      |
|   env store: U4's and U5's tables; agent credentials,      |
|     revocation state, bound slots, failed attempts (U6)    |
|   P5's revocation cache: built here, wired at S4 by U7     |
|   no call to the organization level                        |
+------------------------------------------------------------+
```

*Text alternative*: U6 adds S3 to each environment, with two operations, neither carrying an
envelope. Bootstrap passes the attempt bound, then P6's agent half verifies the registration
secret, then the registration's state and the agent's revocation are checked directly in the
store; the credential record and its attribution record are written in one transaction, and the
token is signed with E's agent key ring. Renewal runs P1's `checkAgentRequest` with a direct
revocation read, checks the record and the registration, then moves the expiry and writes the
attribution record in one transaction. P5's fail-closed revocation cache is built and tested
here and wired at S4 by U7. **S3 never calls the organization level.**

---

## 2. `exchangeBootstrap` (`POST /agent-credentials`)

**Input**: `Soorma-Contract-Version`; body `{ agent, secret, instance }`. No credential header.

1. **Body size** (step 1): over the bound is `payload_too_large`
2. **No credential header** (BR-PR-AC-02): `Authorization` or `Soorma-Delegation` present is
   `malformed_request`, naming the header
3. **Contract version** (step 5)
4. **Schema** (step 6; BR-BQ-01): closed; `agent`, `secret` (at most 256), `instance`, all
   required. A failure is `malformed_request` and is **not counted** by the bound (BR-BQ-02)
5. **The bound** (BR-AB-AC-01): admit (E, `agent`), known or not. Refused: `too_many_attempts`
   with `Retry-After`; a Failed Bootstrap Attempt is queued (refused-by-bound)
6. **Resolution** (BR-BS; each failure is `authentication_failed`, the bound settled as a
   failure, a Failed Bootstrap Attempt queued, a security-log event written):
   1. The prefix is `soorma_rs_`, else `unsupported_material`
   2. `parseRegistrationSecret`, else `malformed_secret`; compute the digest
   3. One read: the registration `agent` in E, and the secret record by its `id`. No
      registration: `unknown_registration`; no record, or a record of another registration:
      `unknown_secret`; not `active`: `secret_not_active`
   4. `registrationSecretMatches`, in constant time, else `secret_mismatch`
   5. The registration is `registered`, else `registration_not_registered`
   6. The agent is not revoked (direct read), else `agent_revoked`. A read failure is
      `unavailable` (503), settled as a failure
7. **Write** (one transaction; BR-BS-06, BR-AT-AC-01): the credential record (new `cid`, E,
   agent, instance, the secret's `id`, `issuedAt` = now, `lineageEndsAt` = now + M,
   `expiresAt` = min(now + L, `lineageEndsAt`)) and the attribution record (operation
   `exchangeBootstrap`; agent actor with registration, instance, the resolved sponsor; target the
   `cid`; no envelope facts). Any failure: `unavailable`, nothing written
8. **Settle** the bound as a success (its own reservation removed)
9. **Mint** the token with E's agent key ring: `env`, `sub` = agent, `inst`, `cid`, a new `jti`,
   `iat` = now, `exp` = `expiresAt`
10. **Response** `200`, `Cache-Control: no-store`:
    `{ credential, agent, environment, instance, expiresAt }`

The Failed Bootstrap Attempt writer runs **off the response path** and writes only when the
named registration exists (BR-FA-02).

## 3. `renewAgentCredential` (`POST /agent-credentials/current/renewal`)

**Input**: `Authorization: Bearer soorma_ac_…`; `Soorma-Contract-Version`; no body.

1. **Body size** (step 1)
2. **Presenter** (step 2; BR-PR-AC-03, 04): exactly one `soorma_ac_`, no `Soorma-Delegation`.
   A `soorma_ec_` or `soorma_si_` is `credential_refused`, unverified
3. **`checkAgentRequest`** (steps 3, 4; D-AC-27), with the **direct** revocation source:
   1. Verify with E's agent key ring (O1); a failure is `credential_refused`
   2. Expiry (O2), only after the signature verifies: `credential_expired`
   3. `env` equals E's configured identity, field by field (O4), else `credential_refused`
   4. O3: the `cid` or the agent revoked, `credential_refused`; a read failure `unavailable`
   5. Yields the Checked Agent Context: scope, agent, instance, `cid`
4. **The record** (BR-RN-02): by `cid` in E; absent, or naming another agent or instance:
   `credential_refused`
5. **Contract version** (step 5); **no body** (step 6), else `malformed_request`
6. **The registration** is `registered` (BR-RN-04), else `credential_refused`
7. **The new expiry** (BR-RN-06): min(now + L, `lineageEndsAt`)
8. **Write** (one transaction; BR-RN-07): the record's `expiresAt` = the later of its value and
   the new expiry; the attribution record (operation `renewAgentCredential`; agent actor with the
   presented `cid`; target the `cid`; no envelope facts). Any failure: `unavailable`
9. **Mint** a new token: same `env`, `sub`, `inst`, `cid`; a new `jti`; `exp` = the new expiry
10. **Response** `200`, `Cache-Control: no-store`: the same shape as bootstrap

The registration secret is **not** consulted (D-AC-15; PF FR-008).

---

## 4. The Lineage, Worked (D-AC-02, D-AC-14)

Take L = 15 minutes and M = 24 hours (illustrative; the values are NFR Requirements').

| Time | Event | Record | Token |
|---|---|---|---|
| 00:00 | Instance `i-1` of A bootstraps | `cid` c1, `lineageEndsAt` 24:00, `expiresAt` 00:15 | t1, `exp` 00:15 |
| 00:10 | Renews with t1 | `expiresAt` 00:25 | t2, `exp` 00:25 (t1 still valid to 00:15) |
| … | Renews every 10 minutes | | |
| 23:50 | Renews | `expiresAt` 24:00 (capped) | tn, `exp` 24:00 |
| 23:58 | Renews with tn | `expiresAt` 24:00 (no later allowed) | `exp` 24:00 |
| 24:00 | Renewal with tn | — | `credential_expired` |
| 24:00 | `i-1` bootstraps again with its secret | `cid` c2: a new lineage | t1', `exp` 24:15 |

If c1 is revoked at 12:00, the renewal at 12:10 is refused (direct read, D-AC-01); at S4 (U7),
every request with any token of c1 is refused within B.

## 5. The Cache, Worked (BR-RC; built in P5, wired at S4 by U7)

Take B = 30 seconds (illustrative).

| Time | Store | Request for c1 | Answer |
|---|---|---|---|
| 0 s | up | miss: read issued at 0 s | `not_revoked`, cached |
| 20 s | up | hit (age 20 s) | `not_revoked` |
| 25 s | **down** | hit (age 25 s) | `not_revoked`: a brief outage is invisible |
| 30 s | down | age reaches B: re-read fails, not cached | **unknown → deny**, `unavailable` |
| 40 s | up | miss: read issued at 40 s | `not_revoked`, cached |
| 45 s | up; c1 revoked at 45 s | hit (age 5 s) | `not_revoked` (inside B) |
| 70 s | up | age reaches B: re-read | `revoked`, kept: refused from now on |

The revocation at 45 s takes effect by 70 s, within B of it.

## 6. *Done When* 2, by Raw Calls (US-07; D-AC-31)

After *done when* 1 (U5): H registered A and B in E and issued a secret for each.

1. A's instance `a-1` calls `POST /agent-credentials` on E's S3 with `{ agent: A, secret: sA,
   instance: a-1 }`: `200`, a `soorma_ac_` credential asserting A, E, `a-1`, with `expiresAt`
2. B's instance `b-1` does the same with sB: `200`
3. Each calls `POST /agent-credentials/current/renewal` with its credential: `200`, a new token,
   the same binding, a later `expiresAt`
4. The store holds two credential records and four attribution records (two `exchangeBootstrap`,
   two `renewAgentCredential`), each with the agent actor and the resolved sponsor H, and none
   with a chain or origin

No SDK; the calls conform to `contract/data-gateway.openapi.yaml`.

## 7. Each Refusal (TC-AC Inception Specs)

| TC | Case | Where it stops | Response |
|---|---|---|---|
| TC-AC-037 | A draft envelope in the bootstrap body (TC-AC-004 is the converse: both succeed with none) | §2 step 4 | `malformed_request` |
| TC-AC-007 | A wrong secret | §2 step 6.4 | `authentication_failed`; a Failed Bootstrap Attempt for A |
| TC-AC-008 | Attempts beyond the bound | §2 step 5 | `too_many_attempts`, `Retry-After`; each recorded |
| TC-AC-009 | A revoked credential at renewal | §3 step 3.4 | `credential_refused` at once (D-AC-01) |
| TC-AC-010 | Revocation state unreadable | §3 step 3.4 | `unavailable` (renewal needs the store); past B at S4, deny |
| TC-AC-011 | An expired credential | §3 step 3.2 | `credential_expired`; bootstrap then succeeds |
| TC-AC-012 | A human credential at renewal | §3 step 2 | `credential_refused`, unverified |
| TC-AC-013 | A credential from E2 | §3 step 3.1 | `credential_refused` (E2's `kid` or signature) |
| TC-AC-014 | An unknown agent | §2 step 6.3 | `authentication_failed`; nothing recorded (no registration) |
| TC-AC-018 | Any probe of revocation state | — | No operation exists; refusals reveal nothing |
| TC-AC-022 | A `soorma_em_` value as the secret | §2 step 6.1 | `authentication_failed`; recorded against A |

TC-AC-009, 010, and 015 are adjusted at the QA construction enrichment for D-AC-01: at S3 the
refusal is immediate, and the bound's timeline is tested in P5 (§5) and at S4 by U7.
