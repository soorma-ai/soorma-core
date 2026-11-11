# NFR Design Patterns: U4 `env-human-access`

**Unit**: U4 `env-human-access` (soorma-core#7). Control face, environment level
**Built against**: ID @ `prd-identity-v1.0`, PF @ `prd-platform-foundations-v1.3`
**Decisions from**: the NFR Design plan, Q1 to Q4 and P-01 to P-10, answered
2026-11-11T06:27:05Z (verbatim in `audit.md`). Every answer is technology (I11); no
specification gap
**Meets**: [NFR Requirements](../nfr-requirements/nfr-requirements.md) NFR-EHA-01 to 26 and
08a; the Functional Design's rules ([business-rules.md](../functional-design/business-rules.md))
**Companion**: [logical-components.md](logical-components.md)

Pattern ids are **NP-EHA-nn**. Each pattern names the requirements it meets and how it is
verified. Test case ids (TC-EHA-nnn) are assigned at QA construction enrichment.

---

## NP-EHA-01: E's Credential Token (Q1 A)

`soorma_ec_` followed by a **JWS compact serialization** (RFC 7515) of a **JWT** (RFC 7519) with
explicit typing (RFC 8725 §3.11). It stays within BR-CR-05: an RFC 6750 `b64token` of at most
4096 characters.

| Part | Field | Value |
|---|---|---|
| Header | `alg` | `Ed25519` only (RFC 9864), fixed in code (T-EHA-02) |
| | `typ` | `soorma-ec+jwt`, exactly |
| | `kid` | The RFC 7638 thumbprint of the E signing key that minted it (NP-EHA-02) |
| Claims | `env` | `{ organization, project, environment }`: E's configured identity |
| | `sub` | The principal identifier. Its organization is `env.organization` |
| | `cid` | The credential record's `id` (NP-EHA-11) |
| | `jti` | This token's own id (NP-EHA-11). Renewal mints a new token with a new `jti` and the same `cid` |
| | `iat`, `exp` | Seconds since the epoch. `exp` per BR-EC-04 and NFR-EHA-01 |

**No `iss` and no `aud`.** The binding is `env`, compared field by field with E's configured
identity, so the triple never needs a string encoding. The token's kind is carried by `typ` and
the prefix. **Every claim above is required.** A token with any other claim is still accepted,
since unknown claims are ignored, as for the sign-in.

**Minting** (`credentials.mint`, P5) uses E's current signing key only.

**Verification** (`credentials.verify`, P5), in this order. Each step refuses on failure:

| Step | Check | On failure |
|---|---|---|
| 1 | Prefix `soorma_ec_`, at most 4096 characters, `b64token` syntax | `credential_refused` |
| 2 | JWS compact form, protected header only; `typ` exact; `alg` = `Ed25519` | `credential_refused` |
| 3 | `kid` names a key in **E's** verify set (NP-EHA-02). E2's keys are never in it, so **a credential from E2 fails here or at step 4, before its expiry is read** (BR-EC-03) | `credential_refused` |
| 4 | The signature | `credential_refused` |
| 5 | Every claim present and well typed | `credential_refused` |
| 6 | `exp`: **no leeway**. Refused at or after `exp` (NFR-EHA-03) | `credential_expired` |
| 7 | `iat` at most 30 seconds ahead of this instance's clock (NFR-EHA-03) | `credential_refused` |
| 8 | `env` equals E's identity in all three fields (O4, D-EHA-12) | `credential_refused` |
| 9 | **O3**: the record by `cid` and E, uncached (D-EHA-11). It must exist, be `live`, and have the token's `sub` and `env` | `credential_refused`; store unreadable: `unavailable` |

**The record, not the token, governs liveness.** Tokens are not tracked one by one: ending the
record refuses every token minted for it (BR-EC-07). A token minted before a renewal stays valid
until its own earlier `exp`, which gives nothing a newer token does not.

**Meets**: BR-EC-02, 03, 07; NFR-EHA-01, 03; ID §8b O1 to O4; I1.
**Verified by**: tests, each refused at its step:
- a wrong prefix;
- 4097 characters;
- `typ: JWT`;
- `alg: EdDSA`;
- an unknown `kid`;
- an E2-minted token presented at E;
- a flipped signature byte;
- each missing claim;
- `exp` reached;
- `iat` at +31 s;
- each `env` field altered (re-signed with E's key in the test);
- an ended record;
- a record whose `sub` differs.

Also tested: a token minted before a renewal still passes until its own `exp`.

## NP-EHA-02: E's Minting Key Ring (P-01)

E's configuration names **one signing key and a set of verify keys**. Each is an Ed25519 private
key (PKCS #8 PEM) delivered as a secret (Infrastructure Design), with `kid` = its RFC 7638
thumbprint. The ring is built at start-up and held in memory. **No key is written to the
environment store, and nothing is published**: only E's own S2 instances verify E's
credentials.

**Rotation** is a configuration change in three steps:
1. Add the new key as a verify key, and restart every S2 of E.
2. Make it the signing key, and restart every S2 of E.
3. Once every token the old key signed has expired (15 minutes, NFR-EHA-01), remove the old key.

Because step 1 restarts every instance before step 2, no instance ever meets a `kid` it lacks.
Unlike the sign-in's verify keys, these need no refetch.

**Start-up** fails closed (D-EHA-28) in each of these cases: a key missing, a key not Ed25519,
the signing key not among the verify keys, or two keys with one `kid`.

**Meets**: ID §6; PF §6; BR-EC-02, 03; SECURITY-12 (no hard-coded credentials).
**Verified by**:
- start-up tests for each failure;
- a rotation test: a token minted under the old key passes while the old key is a verify key,
  and is refused once the old key is removed;
- E and E2 rings built from distinct secrets: neither verifies the other's tokens.

## NP-EHA-03: The Verify-Key Cache (P-02; NFR-EHA-08, 08a)

One cache per S2 instance holds S1's verify keys, as the JWKS `GET /verify-keys` returns it
(U2 BR-INT-03).

| Behaviour | Design |
|---|---|
| Start-up | The first fetch is started **without blocking**. S2 serves everything; issuance is `unavailable` until a fetch succeeds (BR-IS-02) |
| Schedule | A refresh every **5 minutes**, from an injected scheduler over the `CLOCK` (NP-EHA-13) |
| Single flight | At most one fetch is in progress. A caller that needs a fetch while one runs awaits that one |
| On demand | A sign-in whose verification answers `unknownKey`, including with **no keys held**, triggers one fetch. **At most one on-demand fetch per 30 seconds per instance.** The limit counts on-demand fetches only: **a scheduled refresh neither waits for it nor resets it**. Inside the limit, no fetch is made, and the sign-in is verified again against the keys held (the flow below) |
| Read per verification | The cache is the **key source** P1 and `verifySignIn` take: an object whose **`verifyKey(kid)` reads the cache's current set on every call**. Nothing holds a copy of the set, so a refresh is seen by the next verification |
| Replacement | A fetch replaces the set **only** with a well-formed JWKS of Ed25519 public keys (`kty: OKP`, `crv: Ed25519`, a `kid` matching each key's thumbprint), within 64 KiB. **Keys are dropped only by such a replacement.** A failed or malformed fetch keeps the keys held and logs `orglevel.unavailable` with reason `verify_keys` |
| Transport | The **key-fetch pool** (NP-EHA-04): its own single socket, **outside the S1-call throttle**, so a refresh or refetch never waits behind in-flight calls |

**The unknown-`kid` flow at issuance** (P1's `SignInPerimeter`, as generalised in NP-EHA-15
commit 2):

1. P1 extracts the token, then calls `verifySignIn(token, keySource, organization, now,
   { expSeconds: 30, iatAheadSeconds: 30 })`.
2. **`unknownKey`**: the header's `kid` is absent from the key source. P1 calls the cache's
   **`refetch()`**, which runs or joins the single-flight fetch, or does nothing inside the
   30-second limit. When it settles, P1 **verifies again, exactly once**.
3. The second answer is final:
   - `valid`: continue to step 4.
   - `expired`: `credential_expired`.
   - `invalid` or `unknownKey`: `credential_refused`.
   - **But `unknownKey` while the key source holds no key at all is `unavailable`** (BR-IS-02),
     because the sign-in was never checked.
4. P1 calls the **status callback once**, which is S2's `signInStatus` (A7):
   - `{ status: 'live', expiresAt }` is accepted, and **`expiresAt` is carried in the result**
     for BR-EC-04's cap.
   - `ended` or `unknown` is `credential_refused`.
   - A thrown `UnavailableError` is `unavailable`.

**One `signInStatus` call per request**: P1 makes it, and the handler reuses the answer for the
cap rather than calling again. A token with no `kid` in its header is `invalid`, never
`unknownKey`, because a fetch cannot help it.

**The rotation at the organization level** (U2's signing-key rotation, step 2: "after at least
one environment refresh interval"):
- The refresh interval is 5 minutes, so **step 2 waits at least 5 minutes** after step 1's
  restart. That wait covers the normal case.
- The on-demand fetch covers the rest: an S2 whose refresh failed during step 1's restart of S1,
  and a refresh that runs late.
- **"No valid sign-in is refused during a rotation" depends on both** (NFR Requirements §3).

**Meets**: NFR-EHA-08, 08a; U2 F-1, R-1; BR-IS-02; SECURITY-15.
**Verified by** clock-controlled tests:
- a refresh at 5 minutes;
- two unknown-`kid` sign-ins 10 seconds apart cause one fetch, and 31 seconds apart cause two;
- a scheduled refresh 5 seconds after an on-demand fetch still runs;
- a failed fetch and a malformed answer each keep the old keys;
- concurrent callers share one fetch;
- issuance with no keys held triggers one fetch, then is `unavailable` if it fails;
- NFR-EHA-08a's two cases. First, a key added at S1 and the clock advanced 5 minutes: issuance
  under it succeeds with no on-demand fetch. Second, a refresh fails during step 1: a sign-in
  under the new key succeeds after exactly one on-demand fetch.
- **Through P1** (the flow above), with a stub S1:
  - An unknown `kid` that the refetch brings in: one fetch, two verifications, accepted.
  - An unknown `kid` that the refetch does not bring in: one fetch, two verifications,
    `credential_refused`.
  - An unknown `kid` inside the 30-second limit: no fetch, two verifications,
    `credential_refused`.
  - No keys held and the fetch failing: `unavailable`.
  - A token with no `kid`: `credential_refused`, no fetch.
- **Read per verification**: two sign-ins under a new key with a refresh between them. The first
  is refused within the limit, and the second, after the refresh, is accepted with no on-demand
  fetch.
- **One `signInStatus` call per issuance**: the stub counts exactly one, and the credential's
  expiry is capped at the `expiresAt` it returned.

## NP-EHA-04: The S1 Caller (P-03, as changed)

One module makes every call to S1's internal listener, for three operations:

| Operation | Request | Expected answer (else `unavailable`) |
|---|---|---|
| `signInStatus` | `GET /sign-ins/{sid}/status` | 200 with exactly `{ status: 'live', expiresAt }`, `{ status: 'ended' }`, or `{ status: 'unknown' }` (A7) |
| `principalExists` | `GET /principals/exists?organization=…&principal=…` | 200 with exactly `{ exists: boolean }` |
| Verify keys | `GET /verify-keys` | 200 with a JWKS (NP-EHA-03) |

It has **two connection pools, both `node:https` keep-alive agents**:

| Pool | Sockets | Used by | Throttle |
|---|---|---|---|
| **S1-call pool** | 8 | `signInStatus`, `principalExists` | The S1-call semaphore (8, NP-EHA-05), so no call waits for a socket beyond its permit |
| **Key-fetch pool** (the user's change) | **1** | The verify-key fetch only | **None**. NP-EHA-03's single flight means at most one fetch is ever in progress, so it never waits behind the 8 |

**Both pools** share these settings:
- TLS 1.3 minimum, with **the local CA as the only trust root**.
- The server name must be `org-gateway.soorma.internal`, using Node's default server-identity
  check.
- No client certificate: the caller is authenticated by the signed request.

**Every call**:
- **Signed with E's caller key** (`signInternalRequest`, U2 P-06 / F-3), with `htm` = `GET`,
  `tgt` = the exact path and query sent, and `bsh` over the empty body.
- **A 2-second deadline** from an injected timer: one `AbortSignal` covers connect, TLS, send,
  and read.
- **A 64 KiB cap on the response body**, and the answer checked against exactly the shape above.
- **One attempt, no retry.**

Any failure is an `UnavailableError`, which becomes `unavailable` (503, `Retry-After: 5`). That
covers a refused connection, a TLS failure, the deadline, a non-200 status, an over-cap body, or
a wrong shape. It is logged as `orglevel.unavailable` with the operation and the cause, and never
a token or identifier (D-EHA-27). **Nothing from S1 is cached but the verify keys.**

**Meets**: NFR-EHA-05, 07, 23; D-EHA-23, 27; U2 F-3; SECURITY-15.
**Verified by** tests against a stub S1, each a single attempt and a 503:
- an answer at 2.001 seconds (clock-controlled);
- a 500;
- `{ status: 'live' }` without `expiresAt`;
- an extra field;
- a 65 KiB body;
- a refused connection;
- a server certificate from another CA, or for another name.

Also tested: with 8 S1 calls held open, a verify-key fetch still completes.

## NP-EHA-05: Throttling (P-04, as changed; NFR-EHA-04, 05)

There are **two FIFO semaphores per S2 instance**, generalised from U2's `HashSemaphore` into
service-kit's `Semaphore`: a permit count, a wait deadline, and an injected clock.

| Semaphore | Permits | Wait | Taken | Released |
|---|---|---|---|---|
| **Request** | 64 | 1 second | In Fastify's **`onRequest`** hook, **before the body is read**, so a flood holds at most 64 × 16 KiB of bodies | In **both `onResponse` and `onRequestAbort`**, through a **release-once guard**: whichever fires first releases, and the second does nothing |
| **S1 call** | 8 | 1 second | Around each `signInStatus` and `principalExists` call | When the call settles, in a `finally` |

**The release-once guard**: `acquire` returns a release function that flips a flag on its first
call and ignores later ones. So a request that is aborted and then answered, or answered and
then aborted, frees its permit exactly once, and the count can never drift above 64.

**A request aborted while still waiting** for a permit is removed from the queue, and holds
nothing. A wait that reaches its deadline makes the request `unavailable` (503, `Retry-After: 5`)
and logs `throttle.refused`, with reason `requests` or `s1_calls`.

**Meets**: NFR-EHA-04, 05, 06; SECURITY-11, 15.
**Verified by**:
- With 64 permits held, request 65 gets 503 after 1 second (clock-controlled). When one permit
  is released, a waiting request proceeds.
- **The user's test**: abort 64 requests mid-body, and the next request still gets a permit.
- A request answered and then aborted, and one aborted and then answered, each release once: the
  available count returns to 64, never 65.
- With 8 S1 calls held, a 9th issuance gets 503 after 1 second, while ending a credential (no S1
  call) succeeds.

## NP-EHA-06: The Environment Store and Its Transactions (Q4 A; P-01)

`packages/env-store` owns the environment store, which is PostgreSQL 18, one instance per
environment (NFR-EHA-09). It has three parts.

**The pool**:
- built from E's configuration, as the app role;
- TLS `verify-full` against the local CA;
- `synchronous_commit` on, as U2 (NFR-EHA-10).

**`withTransaction(fn)`**:
- It begins a transaction, passes `fn` a **`Tx` handle**, and commits only if `fn` returns.
- If `fn` throws, it rolls back and rethrows.
- A response reports success only after the commit (NFR-EHA-10).

**The migration sequence**: one directory, `0001_…`, run by `{env}-migrate` through
service-kit's runner, as the migrator role, under the **environment's own advisory lock key**
(the first 63 bits of SHA-256("soorma.env.migrate")). It is a different instance from the org
store's, so the keys could not collide anyway (NFR-EHA-14).

**P4 `registry`, P5 `credentials`, and P7 `attribution` each own their SQL**:
- in their own `src/sql.ts`, through service-kit's `statement()`, so U2's `sql` check covers them;
- run over the `Tx` handle that the caller passes in.

So one S2 operation's writes across modules commit or roll back together (D-EHA-17):

| Operation | One transaction |
|---|---|
| Issuance | P5 insert credential; P7 insert record |
| Renewal, ending | P5 conditional update (NP-EHA-09); P7 insert record |
| `grantToHuman` | P4 insert grant; P7 insert record |
| First grant | P4 insert grant `ON CONFLICT DO NOTHING`; P7 insert record if a row came back (NP-EHA-08) |

**Every statement constrains on the environment** (D-EHA-29), in addition to the store being per
environment. The environment is the three columns `organization`, `project`, `environment` on
every table.

**Isolation**: `READ COMMITTED` is enough. Every race is closed by a constraint (NP-EHA-08) or a
conditional update (NP-EHA-09), not by read-then-write.

**Meets**: NFR-EHA-09 to 14; D-EHA-17, 29; I1; SECURITY-05.
**Verified by**:
- An attribution insert forced to fail rolls back its grant.
- A failure between the two inserts leaves neither.
- Every statement in P4, P5, and P7 has the environment in its `WHERE` or `VALUES`; a review
  rule, plus a test that a row seeded under E2's identity in E's store is invisible to every
  read.
- U2's `sql` check passes over the new packages.

## NP-EHA-07: The Attribution Record (Q3 A)

Each record is one row in `attribution_records`, **with typed columns, and `CHECK` constraints
repeating BR-AT-05**. So an inconsistent record is refused twice: by P7's writer, and by the
store. The full layout is in logical-components.md §3.

| Constraint | Repeats |
|---|---|
| `actor_kind` in (`human`, `configuration`, `agent`) | BR-AT-02 to 04 |
| A `human` actor has `principal`, `credential_kind` (`signIn` or `environmentCredential`), and `credential_id`; and has no `registration`, `instance`, `sponsor`, `chain`, `origin`, or re-broadening | BR-AT-02, 05 |
| A `configuration` actor has none of `principal`, `credential_*`, the agent fields, `chain`, `origin`, or re-broadening | BR-AT-03, 05 |
| An `agent` actor has `registration`, `instance`, and **`sponsor`** | BR-AT-04, 05 |
| `chain`, `origin`, and `rebroadening_load_bearing` are all null or all present, and present only for an agent | BR-AT-04, 05 |
| `rebroadening_hop` is non-null **only if** `rebroadening_load_bearing` is true, and then is at least 0 and less than `jsonb_array_length(chain)` | BR-AT-05 (U3 BR-ST-08) |
| `chain` is a JSON array | BR-AT-04 |

**Left to the writer**: the content of each chain entry. The store checks the shape above, not
what an entry says.

**Written once**: the app role has `INSERT` and `SELECT` on this table, and **no `UPDATE` or
`DELETE`** (BR-AT-08; NFR-EHA-21). **Refusals write no row** (BR-AT-09).

**Meets**: BR-AT-01 to 09; D-EHA-04, 31; I4; PF FR-025.
**Verified by**:
- For each `CHECK`, an insert that violates it, issued directly as the app role, fails. The
  writer refuses the same record before the store does.
- Constructed agent records, at zero hops and with a multi-hop chain, round-trip with their
  scope, actor, sponsor, chain, origin, and outcome recoverable from the row alone (BR-AT-07).
- The app role's `UPDATE` and `DELETE` on the table fail.

## NP-EHA-08: The First Grant, Once (P-05; NFR-EHA-12)

The store holds a **partial unique index** on
`grants (organization, project, environment, principal) WHERE granted_by_kind = 'configuration'`.

At start-up, in one transaction:
1. `INSERT … ON CONFLICT DO NOTHING RETURNING id`.
2. **If a row came back**: insert the attribution record (actor `configuration`, operation
   `configureFirstGrant`, BR-FG-03), log `first_grant.applied`, and commit.
3. **If no row came back**: another start-up has applied it, so write nothing and commit (an empty
   transaction).

Any other error stops S2's start-up (BR-FG-05, D-EHA-28).

**Meets**: BR-FG-01 to 05; D-EHA-07.
**Verified by**:
- **The user's concurrency test**: two start-ups against one fresh store, run at the same time,
  leave exactly one configuration grant and one attribution record, and both start.
- A second start-up alone writes nothing.

## NP-EHA-09: Conditional Renewal and Ending (P-06; D-EHA-26)

Renewal:

```sql
UPDATE credentials
   SET expires_at = $5
 WHERE id = $1 AND organization = $2 AND project = $3 AND environment = $4
   AND state = 'live'
RETURNING id
```

Ending is the same `WHERE` with `SET state = 'ended', ended_at = $5, ended_by = 'self'`.

**Zero rows means the record was ended after step 9 of NP-EHA-01 read it**: `credential_refused`,
the transaction rolls back, and no attribution record is written. One row: the attribution record
is written in the same transaction.

Renewal **never shortens** an expiry (BR-EC-04). The cap only moves later, because a sign-in's
expiry only moves later.

**Meets**: NFR-EHA-11; BR-EC-05, 07.
**Verified by**:
- A renewal and an end racing on one credential commit exactly one outcome. If the end wins, the
  renewal is `credential_refused` with no record. If the renewal wins, the end then succeeds.
- Two concurrent ends: one succeeds, and one is `credential_refused`.

## NP-EHA-10: The Held Set (P-07; D-EHA-14)

Each grant is one row, **its permissions a sorted, de-duplicated `text[]`**, with a `CHECK` that
it is non-empty. P4 sorts and de-duplicates before writing, and BR-ACC has already accepted each
identifier.

An index on `(organization, project, environment, principal)` serves P4's human `GrantSource`
(P11's port, U3 D-AE-02):

```sql
SELECT DISTINCT unnest(permissions) FROM grants
 WHERE organization = $1 AND project = $2 AND environment = $3 AND principal = $4
```

The read is **uncached** (D-EHA-14; U3 NFR-AE-14). `holdsAnyGrant` is an `EXISTS` over the same
index. Grant rows are written once: the app role has no `UPDATE` or `DELETE` on `grants` in M1.

**Meets**: NFR-EHA-10; D-EHA-13, 14; ID §10 read-your-writes.
**Verified by**:
- Read-your-writes: a grant, then the target's next issuance passes `holdsAnyGrant`.
- The union of two grants is their set union.
- A row under another environment's identity is not read.

## NP-EHA-11: Identifiers (P-08; D-EHA-30)

The credential `id`, the grant `id`, the attribution record `id`, and each token's `jti` are each
**128 random bits from `crypto.randomBytes`, encoded base64url without padding** (22 characters).
Each is a primary key or unique column, so a collision is refused by the store and never
overwrites a row.

**Meets**: D-EHA-30; NFR-EHA-25. **Verified by** review, and a test that ids are 22 base64url
characters.

## NP-EHA-12: Listeners, Plumbing, and Events (P-09)

S2 is **one process** with two listeners, as S1's edge and health (U2 P-07). It has **no internal
listener**: nothing calls S2 but clients.

| Listener | Bind | Serves |
|---|---|---|
| Edge | All interfaces; published to the host (ports and networks are Infrastructure Design's); TLS 1.3 | The four operations of `contract/control-gateway.openapi.yaml` |
| Health | `127.0.0.1` inside the container, plain HTTP | `GET /` → 204, for the Compose healthcheck |

**From service-kit, as S1's** (U2 P-08, P-17):
- the Fastify adapter with the **16 KiB body bound** (NFR-EHA-16), keeping raw bytes;
- a **request id generated for every request**, never taken from the client, and returned as
  `Soorma-Request-Id`;
- `Soorma-Contract-Version` on every response;
- the global exception filter mapping refusals to problem documents (BR-RF-04: `Retry-After` on
  503, `WWW-Authenticate: Bearer` on 401);
- the contract validator compiled once at start-up (NFR-EHA-17);
- the JSON `SecurityLog` (NFR-EHA-18).

**S2's security event list** (NFR-EHA-19): `credential.issued`, `credential.renewed`,
`credential.ended`, `credential.refused`, `grant.made`, `grant.denied`, `first_grant.applied`,
`orglevel.unavailable`, `store.unavailable`, `throttle.refused`.

**The log helper still takes no token, key, or principal identifier.** A human is named only by a
`HumanPseudonym` made with **E's log-pseudonym key** (`pseudonym()`), and the internal reason is a
code from a fixed list (BR-RF-03).

**Meets**: NFR-EHA-16 to 20; SECURITY-03, 04 (no HTML), 05, 14 (files only).
**Verified by**:
- NFR-EHA-18's log test, with known tokens and identifiers;
- each event emitted by its flow;
- a 16 KiB + 1 byte body is `payload_too_large`;
- a client-sent `Soorma-Request-Id` is replaced.

## NP-EHA-13: Time (P-10)

Every expiry, leeway, deadline, wait, and schedule reads the **`CLOCK` token** (service-kit), and
timers come from an injected scheduler over it. **No test waits in real time** (NFR-EHA-26).

## NP-EHA-14: Secret Types at S2 (the user's Q2 condition)

The **existing branded types** are used wherever a secret enters or crosses S2, so the `compare`
check's `===` rule covers each one (U2 D-CG-OI-05, NFR-EHA-25):

| Value | Type | From |
|---|---|---|
| E's signing and verify keys' PEM bytes; E's caller key's PEM bytes | `SecretBytes` | The secret reader, until converted into a `KeyObject` once at start-up |
| E's log-pseudonym key | `SecretBytes` | The secret reader |
| A presented token string: `soorma_si_…` or `soorma_ec_…` | `SecretText` | Extracted from `Authorization` by P1, and passed as `SecretText` to the verifier |
| A newly minted `soorma_ec_…` | `SecretText` | Returned by `credentials.mint` to the handler, which writes it into the response body |

No new type is needed. `SecretText`'s doc comment, today "K or enrollment material", widens to
include presented and minted bearer tokens. That is a comment change in U4's code, after the
move. Where a token must be compared, which no U4 rule requires, it goes through `secretEqual`.

**Verified by**: the `compare` check over `services/control-gateway` and the new packages, and a
check-fixture test that `===` on a `SecretText` token fails it.

## NP-EHA-15: The Shared-Code Move (Q2 A, with the user's conditions)

The organization-neutral code moves from `@soorma/org-identity` and `services/org-gateway` into
**`packages/service-kit`** (logical-components.md §2 lists each item). **S2 never depends on
`@soorma/org-identity`**, which keeps component-dependency.md's rule that P10 is linked only into
S1.

**Carried to Code Generation (the user's condition)**:
1. **The move is its own first commit**: a pure move, before any U4 code. Files are moved, and
   imports are updated. Where a moved function took an organization-level constant by default,
   the constant stays in `@soorma/org-identity` and is passed in, so behaviour is unchanged. The
   two such constants are `MIGRATIONS_DIR` and `MIGRATION_LOCK_KEY`. **U2's tests stay green, and
   S1's image is rebuilt in the gate.**
2. **U2's checks keep working.** The migration runner keeps its path,
   **`packages/service-kit/src/store/migrations.ts`**, so `tools/checks/code.ts`'s
   `isMigrationRunner` (`/src/store/migrations.ts$/`) matches it unchanged. `statement()`,
   `migrationStatement()`, and the runner's own statements move to
   `packages/service-kit/src/sql.ts`, which `isSqlModule` also matches. The `statementBrand` and
   secret brands keep their names, so the `sql` and `compare` checks recognise them by brand
   wherever they live. **If any of this cannot hold, the check is updated in the same commit.**
3. **Generalisations come after the move**, in their own commit, still with U2's tests green:
   - `HashSemaphore` becomes `Semaphore`, with the hashing defaults staying in org-identity.
   - The `SecurityLog` takes its service's event list.
   - The contract validator takes its service's OpenAPI document.
   - **Sign-in verification and P1's checker, generalised for S2.** Today they cannot meet
     NFR-EHA-03, NFR-EHA-08, or BR-EC-04 at S2 (*the user's review, 2026-11-11*). Each change
     below keeps U2's tests green and **S1's behaviour unchanged**:

     | Change | Today | After | S1 passes or maps | S2 passes or maps |
     |---|---|---|---|---|
     | **Leeway** | `verifySignIn` hard-codes `clockTolerance: 0` | It takes `{ expSeconds, iatAheadSeconds? }`. `expSeconds` becomes jose's `clockTolerance`. `iatAheadSeconds`, when given, is an **explicit check** that `iat` is at most that far ahead of `now` (else `invalid`); jose does not check a future `iat` itself | `{ expSeconds: 0 }`, with no `iat` check, as today (U2 P-01) | `{ expSeconds: 30, iatAheadSeconds: 30 }` (NFR-EHA-03; U2 F-2) |
     | **Unknown `kid`** | `JWKSNoMatchingKey` collapses into `invalid` | `VerifyResult` gains **`{ status: 'unknownKey' }`** for a `kid` absent from the key source. A missing `kid` stays `invalid` | `unknownKey` → `credential_refused`, unchanged | `refetch()`, then verify again exactly once (NP-EHA-03's flow) |
     | **Status callback** | `isLive(claims) → boolean` | `status(claims) → SignInStatus`, A7's type: `{ status: 'live', expiresAt }`, `{ status: 'ended' }`, or `{ status: 'unknown' }`. The accepted result carries the `live` answer | Its O3 check from its own record, with its meaning kept: live, or not live | S2's `signInStatus` call, made once per request. `expiresAt` is kept for the cap (BR-EC-04) |
     | **Key source** | `KeyRing`, a P10 type | A structural **`SignInKeySource { verifyKey(kid): KeyObject \| undefined; hasKeys(): boolean }`**, **read on every verification**. `@soorma/org-identity` then leaves `@soorma/perimeter`'s runtime dependencies (devDependencies only, for fixtures that mint) | Its `KeyRing`, which already has `verifyKey(kid)` and gains `hasKeys()` (always true) | The verify-key cache (NP-EHA-03), whose `verifyKey(kid)` reads its current set |

     *Found while writing this stage*: P1 imports sign-in verification from org-identity today,
     so without the key-source change, S2 would link P10 through P1.
   - The problem documents (`perimeter/src/problems.ts`, no imports) move to service-kit in
     commit 1, so service-kit never depends on P1 (no cycle).

**Verified by**:
- U2's full test suite after each of the two commits, **unchanged**, so S1's behaviour is unchanged;
- **the sign-in leeway cases through P1 at S2's settings** (NFR-EHA-03):
  - (a) a never-renewed sign-in 29 s past its expiry is `credential_refused`, because A7 says
    `ended`;
  - (b) an older token of a renewed sign-in, 29 s past its own expiry, is accepted and capped at
    the renewed expiry;
  - (c) any token 31 s past its expiry is `credential_expired`;
  - an `iat` 30 s ahead is accepted, and 31 s ahead is `credential_refused`;
- **at S1's settings**, the same tokens give S1's existing answers: no leeway, and no `iat`
  check;
- the unknown-`kid` and key-source tests through P1 (NP-EHA-03);
- `check:code` (sql, compare, inject) clean;
- S1's image built in the gate;
- a dependency check that **`@soorma/org-identity` is not in `services/control-gateway`'s
  production dependency closure**, transitive dependencies included (P1 today would bring it
  in).

---

## Security Compliance at NFR Design

| Rule | Status | Note |
|---|---|---|
| SECURITY-01 | Compliant in transit; **at rest not applicable in M1, by the user's decision** | TLS 1.3 at S2's edge (NP-EHA-12), to S1 (NP-EHA-04), and to the store (`verify-full`, NP-EHA-06) |
| SECURITY-02, 06, 07 | N/A at this stage | Infrastructure Design |
| SECURITY-03 | Compliant, **except the centralized log service: not applicable in M1, by the user's decision** | NP-EHA-12: the log helper takes no token, key, or identifier; E's pseudonym |
| SECURITY-04 | N/A | No HTML served |
| SECURITY-05 | Compliant | Body bound and contract validation (NP-EHA-12); parameterized statements only (NP-EHA-06); a response-size cap and shape checks on S1's answers (NP-EHA-04) |
| SECURITY-08 | Compliant | Every operation needs a credential; tokens fully checked (NP-EHA-01); deny by default (BR-EV) |
| SECURITY-09 | Compliant | No default credentials; every key from configuration (NP-EHA-02) |
| SECURITY-10 | Compliant | No new dependency (T-EHA-01 to 10) |
| SECURITY-11 | Compliant | NP-EHA-05. **Accepted residual (Q2, the user's)**: one valid principal flooding S2 can fill an instance's request slots, so other callers on that instance get 503 until it drains. Per-principal and per-source limits are carried to the first hosted deployment |
| SECURITY-12 | Compliant | 15-minute credentials capped at the sign-in; no `exp` leeway on E's tokens; keys from configuration with rotation (NP-EHA-01, 02). **Accepted residual**: the post-logout credential, at most 15 minutes |
| SECURITY-13 | Compliant | `jose` with `Ed25519` fixed in code; the exact `typ`; checksummed migrations; append-only attribution (NP-EHA-07) |
| SECURITY-14 | **Not applicable in M1, by the user's decision** | Events named (NP-EHA-12); alert rules as files (Infrastructure Design) |
| SECURITY-15 | Compliant | Fail closed on S1 (NP-EHA-04), the store (NP-EHA-06), throttling (NP-EHA-05), and missing keys (NP-EHA-02, 03) |

**Security findings**: none blocking.

## Invariant Compliance at NFR Design

| Code | Status | Note |
|---|---|---|
| I1 | Covered | One store and one key ring per environment; the environment on every row and every statement (NP-EHA-02, 06); `env` compared field by field (NP-EHA-01) |
| I2 | No change | |
| I3 | Covered | S1 authenticated by its certificate under the local CA, and S2 by its signed request; throttling is an availability control, never an identity input |
| I4 | Covered | The attribution record's `CHECK` constraints; recoverable from the row alone (NP-EHA-07) |
| I5 | Covered | The held set is read only through P4's `GrantSource` into P11 and P3 (NP-EHA-10) |
| I6, I9 | No change | |
| I7 | Covered | No contract change at this stage |
| I8 | Covered | service-kit and env-store are core mechanism, FSL, in soorma-core; no new dependency |
| I10 | Covered | State in the environment store; nothing reads a host or deployment label |
| I11 | N/A | Construction is where technology is selected |

**Invariant findings**: none blocking.
