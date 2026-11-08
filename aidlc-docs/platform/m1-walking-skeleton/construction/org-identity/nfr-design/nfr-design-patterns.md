# NFR Design Patterns: U2 `org-identity`

**Unit**: U2 `org-identity` (soorma-core#5). Control face, organization level
**Decisions from**: the NFR Design plan, Q1 to Q4 and D-ND-OI-01 to 13, answered 2026-11-08
(verbatim in `audit.md`). All technology (I11)
**Meets**: [../nfr-requirements/nfr-requirements.md](../nfr-requirements/nfr-requirements.md)
(NFR-OI-01 to 31). **Components**: [logical-components.md](logical-components.md)

Each pattern names the NFR-OI rows it meets and how it is verified. Every time-based
behaviour reads the injected `Clock` (P-14).

---

## P-01: The Sign-In Token (Q1 A)

**A JWT (RFC 7519) with explicit typing (RFC 8725)**, signed with `jose`, alg `Ed25519`
(RFC 9864) only.

```text
soorma_si_<JWS compact: base64url(header).base64url(claims).base64url(signature)>
```

| Part | Field | Value |
|---|---|---|
| Header | `alg` | `Ed25519`, and nothing else is accepted |
| | `typ` | `soorma-si+jwt`, required exactly |
| | `kid` | The signing key's RFC 7638 thumbprint (P-02) |
| Claims | `iss` | `urn:soorma:org:{organization}` |
| | `sub` | The principal identifier |
| | `sid` | The sign-in record's id |
| | `jti` | This token's id: each renewal mints a new one |
| | `iat`, `exp` | Issue time; expiry, at most 15 minutes later, never past `auth_time` + 12 hours (NFR-OI-01) |
| | `auth_time` | `authenticatedAt`, unchanged by renewal |
| | `amr` | RFC 8176 values: `pwd` for K, `otp` for TOTP (`["pwd"]` or `["pwd","otp"]`) |

- **No `aud`**: the token is accepted at the organization level and at **every**
  environment's issuance (ID FR-009). Its kind is carried by `typ` and the `soorma_si_`
  prefix (BR-CR-03), and the environments' own credentials are signed with their own keys,
  so it can be confused with none of them
- **Verifiers require every claim above**, the exact `typ`, and the algorithm fixed in code.
  A missing claim, another `typ`, or any other `alg` is `credential_refused`
- **Size**: about 450 characters, well inside U1's 4096 (BR-CR-05). Every character is in
  the RFC 6750 `b64token` set
- The response's `signIn` object repeats `subject`, `authenticatedAt`, `classes`, and
  `expiresAt` for convenience. **`classes` maps `amr` back to the contract's classes**
  (`pwd` → `K`, `otp` → `P`)

**Verification at S1** (D-ND-OI-12): strip the prefix; verify with the configured verify
keys; check `typ`, `alg`, `iss` (this organization), and `exp` with **no leeway** (one
clock); read the sign-in record by `sid` for O3. **Environments** (U4) allow at most 30
seconds of leeway on `exp` and `iat` (D-ND-OI-13).

**Meets**: BR-SI-02, 03, 06, 07; NFR-OI-01. **Verified by**: token tests (each claim
missing or altered is refused; `EdDSA` and other algorithms refused; a token with another
`typ` refused); TC-OI-003, 020, 024.

## P-02: Key Material from Configuration (Q2 A)

**Every key comes from organization-level configuration**, delivered as a secret
(Infrastructure Design). **No key is ever written to the org store.**

| Key | Holds | Served |
|---|---|---|
| **Signing key** | One Ed25519 private key; signs sign-in tokens | Never leaves the process |
| **Verify keys** | A set of Ed25519 public keys, each with its `kid` (RFC 7638 thumbprint), the signing key's public half included | As a **JWKS** through `verifyOnlyMaterial` (BR-INT-03): the verify-only material environments hold |
| **Seed-encryption keys** | AES-256 keys, each with a key id; one is *current* | Never |
| **Counter secret** | At least 256 bits; the HMAC-SHA-256 key for slots (NFR-OI-05) | Never |
| **Environment caller keys** | Per configured environment, its Ed25519 **public** key (P-06) | Never; used to verify |

**Rotating the signing key** is a configuration change in three steps:
1. Add the new key as a **verify key**, and restart. Environments now fetch it (P-06 and
   the U4 obligation below)
2. After at least one environment refresh interval, make it the **signing key**, and
   restart
3. Once every token the old key signed has expired (15 minutes), remove the old verify key

**Recorded with Q2** (the user's three records):

| # | Record |
|---|---|
| R-1 | **U4 obligation**: environments **refetch the verify keys on an unknown `kid`**, rate-limited, and **refresh on a schedule shorter than the rotation's restart interval**, so no valid sign-in is refused during a rotation. Posted on soorma-core#7 when this stage is approved |
| R-2 | **Rotating the counter secret remaps every slot, so every counter resets.** That briefly loosens the bound (every principal's window and backoff start again), so **it is rotated only deliberately**, never on a schedule |
| R-3 | **An old seed-encryption key stays in configuration while any ciphertext uses it.** In M1, old keys are kept. **Re-encrypting seeds under the current key is carried as a later obligation** |

**Meets**: BR-SI-03; BR-INT-03; NFR-OI-05, 09; SECURITY-12 (no hardcoded credentials).
**Verified by**: start-up tests (a missing or malformed key stops start-up, BR-CFG-08); a
rotation test (a token signed by a verify-only key still verifies; after removal it is
refused).

## P-03: Seed Encryption (D-ND-OI-02)

**AES-256-GCM in the application** (`node:crypto`), a 96-bit random nonce per encryption.
**Associated data binds the ciphertext to its row**: the principal reference and the P
record's id. A ciphertext copied to another row fails to decrypt. The stored form is
`{ keyId, nonce, ciphertext, tag }`. Decryption uses the key the `keyId` names (R-3).

**Meets**: NFR-OI-09; SECURITY-01 (at rest, for the most sensitive column). **Verified by**:
a stored seed is not the plaintext; a ciphertext moved to another row fails; an unknown
`keyId` fails closed.

## P-04: Reserve, Then Settle (Q4 A)

Admission is atomic **without a transaction open during hashing**.

**The slot row**: `slot` (0 to 2^20 − 1), `entries` (the window: **individual timestamped
entries**, each with its own id), `consecutive` (consecutive failures), `nextAllowedAt`.
Entries older than 15 minutes are dropped on every write. A slot never holds more than 10
live entries, because admission refuses the 11th, so the row has a fixed maximum size.

```text
admit(reference):
  slot := HMAC-SHA-256(counter secret, reference) mod 2^20
  one statement, under the slot row's lock (insert or update):
    drop entries older than 15 minutes
    if live entries >= 10, or now < nextAllowedAt  -> refuse (Retry-After: P-05)
    append entry { id: random, at: now }           -> reservation = (slot, entry id)

after verification:
  failure: keep the entry;  consecutive += 1
           if consecutive >= 5: nextAllowedAt := now + min(2^(consecutive - 5) s, 900 s)
  success: remove exactly entry (slot, entry id);  consecutive := 0;  nextAllowedAt := null
```

- **A success removes exactly its own reservation**, never another attempt's (Q4's
  record). A success is not a failure, so this does not reset the window: every other
  entry decays only with time (NFR-OI-02)
- **A crash between admit and settle leaves the entry as a failure**: it fails closed
- Unknown references take exactly this path (BR-AB-06)
- **The backoff wait** for the *n*-th consecutive failure (n ≥ 5) is 2^(n−5) seconds,
  capped at 900: 1, 2, 4 … 512, 900 (NFR-OI-03)

**Meets**: NFR-OI-02 to 06; BR-AB-01 to 06. **Verified by**: the concurrency test (20
parallel wrong attempts admit at most 10); a crash-between test; a concurrent success that
removes only its own entry; the clock tests of NFR-OI-02 and 03.

## P-05: `Retry-After`

The later of: the time until the oldest live entry leaves the window (if 10 are live), and
`nextAllowedAt` − now. In whole seconds, rounded up, at least 1 (NFR-OI-04).

## P-06: Signed Internal Requests (Q3 A)

Each call from an environment's S2 to the internal listener carries a short-lived JWS, in
`Authorization: Bearer`.

| Part | Field | Value |
|---|---|---|
| Header | `alg` | `Ed25519` only |
| | `typ` | `soorma-internal+jwt`, exactly |
| | `kid` | The environment caller key's thumbprint |
| Claims | `iss` | The environment's configured identifier |
| | `aud` | `urn:soorma:org:{organization}:internal` |
| | `htm` | The HTTP method |
| | `tgt` | **The full request target, query included** (origin form: path and query, exactly as sent) |
| | `bsh` | **base64url(SHA-256(the exact request body bytes))**; for an empty body, of the empty string |
| | `iat`, `exp` | `exp` at most **60 seconds** after `iat` |
| | `jti` | Random |

**The organization level checks** (any failure is a refusal, logged as
`internal.call_refused`, BR-INT-07): the `kid` names a configured environment's key, and
`iss` is that environment; the signature (`Ed25519` only); `typ`; `aud`; `exp` and `iat`
(30 seconds' leeway, two clocks); **`htm`, `tgt`, and `bsh` equal the request actually
received**. Then the body is parsed.

**Why the content is bound** (Q3's record): binding only the method and path would let a
captured `principalExists` token be replayed with other identifiers for 60 seconds. With
`tgt` and `bsh`, a captured token is good only for **the identical call**. Every internal
operation is read-only (BR-INT-06), so an identical replay within 60 seconds gains nothing:
there is no replay cache.

**Meets**: BR-INT-01, 02, 07; I3. **Verified by**: tests: no token, a wrong key, another
environment's key under this `iss`, an expired token, another `aud`, and a token reused with
a different query or body: each refused, from any address.

## P-07: Two Listeners, One Process (D-ND-OI-01)

S1 runs **two NestJS applications** in one process: the **edge** (the five contract
operations) and the **internal** listener (the three internal operations), each with its own
Fastify instance, port, module graph, and exception filter. **No route of one is registered
in the other.**

**Meets**: BR-INT-01; I6; L1-20. **Verified by**: each internal path is 404 on the edge
port; each edge path is 404 on the internal port.

## P-08: Request Ids and Errors (D-ND-OI-03, 04)

- A request id is generated for every request (`crypto.randomUUID`), **never taken from the
  client**. It is returned as `Soorma-Request-Id`, used as the Problem's `instance`
  (`urn:soorma:request:{id}`), and written on every log line of that request
- **One global exception filter per listener** maps every refusal to a Problem under U1's
  emission rules (BR-ERR-08). An unexpected error is `internal_error` (500): no detail and
  no stack in the response, logged with the request id

**Meets**: BR-ERR-05, 08; SECURITY-03, 09, 15; NFR-OI-22.

## P-09: The Hashing Semaphore (D-ND-OI-07, revised)

A per-process semaphore over every Argon2id operation, decoys included.
- **Permits are configurable.** The default is the **lower** of `2 ×
  os.availableParallelism()` and **a configured memory budget ÷ 64 MiB**. The default
  budget is **512 MiB**, so **8 permits**. (2 × CPUs alone is 32 permits, 2 GiB, on a
  16-thread host, and a container may report the host's CPU count)
- A request waits at most 2 seconds, first in, first out; then `unavailable` (503,
  `Retry-After`)
- It is a resource bound, not state, so M1-TECH-03 holds

**Meets**: NFR-OI-20; SECURITY-11, 15. **Verified by**: with every permit held, a request
gets 503 after 2 seconds (clock-controlled); the permit default under a stubbed CPU count
and budget.

## P-10: The Decoy Verifier (D-ND-OI-06)

Computed once at start-up: Argon2id over random bytes, with the real parameters. Held in
memory. Used whenever the principal does not exist, or has no material of the class
presented, so the work done is the same (BR-RF-03).

## P-11: The Failed Attempt Writer (D-ND-OI-08)

The bounded queue (10,000, NFR-OI-21) drains in batches: at most 100 rows per insert, every
250 ms or as soon as 100 are waiting. A full queue drops and logs `failed_attempt.dropped`.
Shutdown flushes it. It never runs on a request's path.

## P-12: Single-Use TOTP Codes (D-ND-OI-09)

The P record stores the last accepted step. Accepting a code is a **conditional update**
(`last_step < :step`) that must affect exactly one row, so two concurrent uses of one code
cannot both succeed (NFR-OI-08).

## P-13: Atomic State Changes

Every multi-record change is **one transaction** (NFR-OI-15): first authentication; a K
change; a P confirmation; ending sign-ins on a material change. **Single use** is a
conditional update on `state = 'enrollment'` that must affect exactly one row (D-OI-04). A
transaction that fails rolls back, and the response is `unavailable` or `internal_error`,
never a partial success.

## P-14: Time

An injected `Clock` supplies time everywhere: lifetimes, the window, the backoff, TOTP,
pending enrollment, retention (D-ND-OI-05). Tests control it.

## P-15: Store Access (D-ND-OI-11)

`pg` Pool: at most 10 connections per process, a 5-second statement timeout, and a
2-second connection timeout. **A store error fails closed** with `unavailable`.
Parameterized SQL only (NFR-OI-17). Migrations under an advisory lock (NFR-OI-18).

## P-16: Retention (D-ND-OI-10)

A daily timer in every instance; the work runs only in the one that takes
`pg_try_advisory_lock`. It deletes Failed Attempt records and ended or expired sign-in
records older than 90 days. Principals and material are never touched (NFR-OI-25).

## P-17: Logging (NFR-OI-22, 23)

NestJS's `ConsoleLogger` in JSON mode, to stdout. A log helper takes **only** the request
id, an event name from the fixed list, and non-secret fields (a principal reference, a
count, a code). It has no parameter for material or tokens, so a secret cannot be passed
to it by mistake. The no-secret test (NFR-OI-22) runs every flow with known secrets and
searches the captured output.

---

## Forward Obligations to U4 (posted on #7 when this stage is approved)

| # | Obligation |
|---|---|
| F-1 | **Refetch the verify keys on an unknown `kid`** (rate-limited), and **refresh on a schedule shorter than the rotation's restart interval** (R-1) |
| F-2 | Verify sign-ins as P-01 states: the exact `typ`, `Ed25519` only, every claim required; at most **30 seconds' leeway** on `exp` and `iat` (D-ND-OI-13) |
| F-3 | **Sign each internal call** as P-06 states, with E's caller key, binding `htm`, `tgt` (query included), and `bsh` |

## Security and Invariant Compliance at NFR Design

| Rule | Status | Note |
|---|---|---|
| SECURITY-01 | Compliant at this stage | Seed encryption (P-03); TLS on both listeners and at rest for the store are Infrastructure Design's |
| SECURITY-02, 06, 07 | N/A at this stage | Infrastructure Design |
| SECURITY-03 | Compliant | P-08, P-17 |
| SECURITY-04 | N/A | No HTML served |
| SECURITY-05 | Compliant | Validators compiled once; parameterized SQL (P-15); body bound |
| SECURITY-08 | Compliant | Internal calls authenticated per request and bound to their content (P-06) |
| SECURITY-09 | Compliant | No default keys: every key from configuration, and start-up stops without one (P-02) |
| SECURITY-10 | Compliant | No dependency beyond those approved at NFR Requirements |
| SECURITY-11 | Compliant | P-04, P-09, P-10. Accepted residuals unchanged: allowance exhaustion, and the unknown-identifier flood |
| SECURITY-12 | Compliant | P-01 (no algorithm choice to the token), P-02 (no hardcoded credentials), P-12 |
| SECURITY-13 | Compliant | Explicit typing; algorithm fixed; ciphertexts bound to their rows (P-03) |
| SECURITY-14 | **Not applicable in M1, by the user's decision** (NFR-OI-24) | Events named; alert files at Infrastructure Design |
| SECURITY-15 | Compliant | Fail closed on store errors, a full semaphore, an unknown key id; one exception filter per listener |

| Invariant | Status | Note |
|---|---|---|
| I1 | Covered | The token names no environment, and no environment can mint one (P-01, P-02) |
| I3 | Covered, strengthened | P-06: identity of the calling environment from its key, checked per request, never from the network |
| I4 | Covered | No change |
| I6 | Covered | P-07 |
| I10 | Covered | Nothing in these patterns depends on a managed runtime or deployment topology |
| I2, I5, I7, I8, I9 | No change | |
| I11 | N/A | Construction is where technology is selected |

**Findings**: none blocking.
