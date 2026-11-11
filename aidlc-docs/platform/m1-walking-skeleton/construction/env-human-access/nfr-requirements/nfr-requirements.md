# NFR Requirements: U4 `env-human-access`

**Unit**: U4 `env-human-access` (soorma-core#7). Control face, environment level. Adds S2
`control-gateway` and the environment store
**Built against**: ID @ `prd-identity-v1.0`, PF @ `prd-platform-foundations-v1.3`
**Decisions from**: the NFR Requirements plan, Q1 to Q5 and P-01 to P-10, answered
2026-11-11 (verbatim in `audit.md`). Every answer is technology (I11); no specification gap
**Companion**: [tech-stack-decisions.md](tech-stack-decisions.md)
**Functional Design**: [../functional-design/business-rules.md](../functional-design/business-rules.md)
(§17 lists what it carried here; every item is answered below)

---

## 1. The Plane-Face Profile: ID §10, carried forward

U4 is a control-face unit citing **ID §10 *NFR Profile*** @ `prd-identity-v1.0`
(nfr-requirements.md Step 1.5). Its properties are settled. **No data-face property is
added**: no per-request latency budget, and no cache-bounded availability (S2 reads a human's
held set uncached, D-EHA-14; U3 NFR-AE-14).

| Property | ID §10 | Met by |
|---|---|---|
| Consistency | Read-your-writes for the actor | NFR-EHA-10 (one primary; no replicas; uncached held set) |
| Durability | Highest for the human principal record (S1's, U2 NFR-OI-15). PF §10: every operation attributed; the grant is the authority record | NFR-EHA-09, 11 |
| Human-in-the-loop latency | **Interactive** for credential issuance; not a constraint elsewhere | NFR-EHA-15 |
| Auditability | Every operation recorded in each affected environment | Functional Design D-EHA-03, 17; NFR-EHA-21 (nothing pruned) |
| Abuse resistance | Sign-in bounded per principal | S1's bound (U2 NFR-OI-02 to 06), unchanged. S2 has no unauthenticated surface; it is throttled per instance (NFR-EHA-04 to 06) |
| Coverage checks | Fan out per environment | **N/A**: every U4 effect is confined to E |
| The organization level | Its outage stops new sign-ins and organization operations | Accepted residual, Functional Design §16 (D-EHA-23): issuance, renewal, and `grantToHuman` are `unavailable`; ending a credential and O1 to O4 are unaffected. NFR-EHA-07 bounds how long each waits |

## 2. Categories That Do Not Apply

| Category | Status | Reason |
|---|---|---|
| Scalability targets | N/A in M1 | Throughput is low (ID §10). S2 is stateless (M1-TECH-03): every record is in the environment store, so it scales out behind the contract |
| Availability target | N/A in M1 | A local stack (M1-NFR-05). No hosted deployment exists |
| Usability (end users) | N/A | No user interface. Errors are the contract's problem documents |

---

## 3. Requirements

Each has a verification target. Code Generation implements them, and Build and Test runs them.
**Time-based behaviour is tested with an injected clock**, never with real waiting (NFR-EHA-26).
Test case ids (TC-EHA-nnn) are assigned at QA construction enrichment.

### The Environment Credential's Lifetime (Q1 A)

| ID | Requirement | Source | Verification |
|---|---|---|---|
| NFR-EHA-01 | **A human environment credential lives 15 minutes**, the same as a sign-in. Its expiry, at issuance and at every renewal, is the **earlier** of now + 15 minutes and the sign-in's current expiry as `signInStatus` reports it (D-EHA-02, U2 amendment A7). So it never outlives the sign-in's absolute maximum of 12 hours (U2 NFR-OI-01) | Q1 A; ID FR-010; SECURITY-12 | Clock tests: issuance with 20 minutes left on the sign-in gets 15 minutes; with 6 minutes left gets 6; a renewal after the sign-in has been renewed gets a fresh 15 minutes, capped again |
| NFR-EHA-02 | **The residual after a logout at S1 is at most 15 minutes.** Functional Design §16's first residual is bounded by NFR-EHA-01: a credential issued from a sign-in that is then ended stays usable in E for at most its remaining life, unless the human ends it (D-EHA-01; ending the credential is its own logout, SECURITY-12) | Q1 A; Functional Design §16 | Clock test: end the sign-in at S1; the credential passes O1 to O4 until its expiry, is refused at renewal at once (`signInStatus` = `ended`), and is `credential_expired` after expiry |

### Clock Tolerance (P-05)

| ID | Requirement | Source | Verification |
|---|---|---|---|
| NFR-EHA-03 | **On E's own credentials, no leeway on `exp`**: a credential is expired at its expiry. An `iat` **up to 30 seconds ahead** of the verifying instance's clock is accepted (S2 instances' clocks); further ahead is `credential_refused`. **On sign-ins, U2's 30 seconds on `exp` and `iat`** (U2 F-2, BR-IS-01). **The leeway applies only to the token check; A7 (`signInStatus`) judges the sign-in's expiry on S1's clock, with no leeway** | P-05; U2 D-ND-OI-13; U2 amendment A7 | Clock tests: a credential at `exp` is refused, 1 ms before is accepted; `iat` at +30 s accepted, +31 s refused. At issuance, three sign-in cases: **(a)** a sign-in never renewed, its token 29 s past its expiry: `credential_refused`, because A7 reports `ended`; **(b)** an older token from a renewed sign-in, 29 s past its own expiry: accepted, and the credential is capped at the renewed expiry; **(c)** any sign-in token 31 s past its expiry: `credential_expired` |

### Throttling (Q2 A; SECURITY-11)

| ID | Requirement | Source | Verification |
|---|---|---|---|
| NFR-EHA-04 | **At most 64 requests in flight per S2 instance.** A slot is taken before any check (ahead of check-order step 1, Functional Design §11) and released when the response is sent, whatever its outcome. A request that cannot take a slot **within 1 second** is `unavailable` (503) with `Retry-After: 5`, and logs `throttle.refused` | Q2 A; SECURITY-11, 15 | Test: with 64 slots held, the 65th request gets 503 after 1 s (clock-controlled); once one slot is released, a waiting request proceeds |
| NFR-EHA-05 | **At most 8 calls to S1 in flight per S2 instance**, across `signInStatus` and `principalExists` (the verify-key refresh is outside the bound: it is off the request path and at most one is in flight, NFR-EHA-08). A call that cannot take a slot **within 1 second** makes its request `unavailable` (503, `Retry-After: 5`), logged as `throttle.refused` with reason `s1_calls` | Q2 A; SECURITY-11, 15 | Test: with 8 S1 calls held open, a 9th issuance gets 503 after 1 s; ending a credential, which calls no S1, still succeeds |
| NFR-EHA-06 | **Per-principal and per-source rate limits are not built in M1.** They are carried to the first hosted deployment, with U2's per-source counting (U2 §4). The accepted residual is recorded in §5's SECURITY-11 row | Q2 A (the user's) | Listed in the Build and Test summary |

**Accepted residual (Q2, the user's)**: **one valid principal flooding S2 can fill an
instance's request slots**, so **other callers on that instance get `unavailable` (503) until
the flood drains**. The bound keeps S2, its store, and S1 safe, but not fair between callers.
It is the same class as U2's flood residual (NFR-OI-20). Per-principal and per-source limits
are carried to the first hosted deployment.

### Calls to S1 (P-03, P-04)

| ID | Requirement | Source | Verification |
|---|---|---|---|
| NFR-EHA-07 | **One attempt per call, no retry inside a request, a 2-second timeout.** S1 unreachable, a timeout, a non-200 answer, or an answer that does not match its expected shape is `unavailable` (503) with **`Retry-After: 5`**, and logs `orglevel.unavailable` (D-EHA-27). Nothing from S1 is cached but the verify keys | P-03; SECURITY-15; ID §10 interactive | Tests with a stub S1: a 2.001 s answer is a 503 at 2 s; a 500, a malformed body, and a refused connection are each one attempt and a 503 |
| NFR-EHA-08 | **Verify-key freshness (U2 F-1, R-1)**: S2 **refreshes the verify keys every 5 minutes**, off the request path. A sign-in naming an unknown `kid` triggers **at most one refetch per 30 seconds per instance**; after it, still unknown is `credential_refused` (BR-IS-02). **A key is dropped only when a successful refresh no longer lists it**: a failed refresh keeps the keys held. With no verify keys ever loaded, issuance is `unavailable`; the other operations are unaffected | P-04; U2 F-1, R-1 | Clock tests: a refresh at 5 min; two unknown-`kid` sign-ins 10 s apart cause one refetch, 31 s apart cause two; a failed refresh keeps the old keys; a rotation test (below) |

**What P-04's 5-minute refresh sets at the organization level (the user's addition)**: U2's
signing-key rotation (U2 nfr-design-patterns.md P-02, *Rotating the signing key*) says, at
step 2, "after at least one environment refresh interval, make it the signing key". **That
interval is 5 minutes, so step 2 waits at least 5 minutes after step 1's restart.** **The wait
covers the normal case**: every environment's S2 holds the new verify key before any sign-in
is signed with it. **The unknown-`kid` refetch covers the rest**: an S2 whose refresh failed
during step 1's S1 restart, and a refresh that runs late. **"No valid sign-in is refused
during a rotation" depends on both.** Carried to U4 Infrastructure Design (§4): S1's
rotation steps in the operations notes say "wait at least 5 minutes".

| ID | Requirement | Source | Verification |
|---|---|---|---|
| NFR-EHA-08a | **Rotation test**: with S2's refresh clock-controlled, add a new verify key at S1 and advance 5 minutes; S2 holds it. Then sign with it: issuance succeeds with no refetch. Remove the old key after 15 minutes; a refresh drops it, and a sign-in under the old key is `credential_refused`. **Second case**: the refresh fails while S1 restarts at step 1, so S2 still lacks the new key at step 2; a sign-in under the new key then succeeds after exactly one refetch | U2 R-1; the user's P-04 addition | Integration test at Build and Test |

### The Environment Store (Q3 A; P-01)

| ID | Requirement | Source | Verification |
|---|---|---|---|
| NFR-EHA-09 | **PostgreSQL 18, one instance per environment** (`env-db-e`, `env-db-e2`), each with **its own migrator and app roles, its own credentials, and its own server certificate**. No environment's credentials can reach another environment's data. U5 and U6 add their tables to it. Every row also carries its environment (D-EHA-29) | Q3 A; I1; Application Design Q1 A | Test: E's app role cannot connect to E2's instance; every table's rows carry `environment`; Infrastructure Design gives each instance its own volume and secrets |
| NFR-EHA-10 | **Durability and read-your-writes, as U2's org store (NFR-OI-15, 16)**: `synchronous_commit` on; a response reports success only after the transaction commits; one primary, no read replicas. A write is visible to the actor's next call. **The held set is read uncached** (D-EHA-14) | P-01; ID §10 | Tests: grant, then the target's next issuance sees it; end, then the next request with that credential is refused at once |
| NFR-EHA-11 | **Every multi-record change is one transaction** (D-EHA-17): a grant and its attribution record; issuance or renewal and its record; ending and its record; the first grant and its record. **Renewal and ending are conditional updates** that must affect exactly one row (D-EHA-26), so a renewal racing an end leaves exactly one outcome | P-01; PF §10; D-EHA-17, 26 | Tests: an attribution write failing rolls back its grant; a concurrent renew and end commit one; a failure mid-transaction leaves no partial change |
| NFR-EHA-12 | **The first grant is applied once**, under the uniqueness constraint over configuration grants per (environment, principal) (BR-FG-02; its physical form is NFR Design's). **Two S2 start-ups at the same time write at most one configuration grant and one attribution record**; the one that loses writes nothing and starts normally | P-01; D-EHA-07 (the user's Q7 addition) | Concurrency test: two start-ups against one fresh store; exactly one grant row and one record |
| NFR-EHA-13 | **Access through `pg` with plain parameterized SQL only**: a constant SQL text and a values array on every call; no ORM; identifiers in SQL are constants (U2 NFR-OI-17) | P-01; SECURITY-05 | The same lint or test rule as U2's; review at Code Generation |
| NFR-EHA-14 | **Migrations as U2's (NFR-OI-18)**: versioned SQL files, applied by **a one-shot `{env}-migrate` service** (`e-migrate`, `e2-migrate`) as that environment's migrator role, under a PostgreSQL advisory lock, each in its own transaction and recorded with its checksum. **S2 starts only after its migrate service completes successfully, and holds only the app role.** A changed, already-applied migration fails the run, so S2 does not start | P-01; U2 D-ID-OI-02 | Tests: two concurrent migrate runs apply each migration once; an edited applied migration fails the run; S2's configuration carries no migrator credential |

The store being unreachable fails closed: S2 answers `unavailable` (503, `Retry-After: 5`),
logs `store.unavailable`, and never issues, renews, ends, or grants without its write
committed, and never passes O3 or an authority check on an unread record (BR-EC-02, BR-EV-06;
SECURITY-15).

### Latency (Q4 A)

| ID | Requirement | Source | Verification |
|---|---|---|---|
| NFR-EHA-15 | **p95 at most 300 ms for issuance and renewal** (one S1 call and one transaction each), **at most 200 ms for ending and `grantToHuman`**, on the local stack. **Measured and reported at Build and Test, not a gate**, as U2's TC-OI-062 and U3's TC-AE-040 are | Q4 A; ID §10 interactive | Performance test at Build and Test; the figures go in the Build and Test summary |

### Request Bounds (P-02)

| ID | Requirement | Source | Verification |
|---|---|---|---|
| NFR-EHA-16 | **Request body bound at S2: 16 KiB on every route**, as S1 (U2 NFR-OI-27). The three body-less routes refuse any body at all (D-EHA-24: `malformed_request`, pointer `''`) | P-02; SECURITY-05 | Tests: `grantToHuman` with 16 KiB + 1 byte is `payload_too_large`; issuance with a 1-byte body is `malformed_request` |
| NFR-EHA-17 | Validators are compiled once at start-up from the contract's schemas (U2 NFR-OI-28) | P-02 | Start-up test |

### Logging and Events (P-06; SECURITY-03, 14)

| ID | Requirement | Source | Verification |
|---|---|---|---|
| NFR-EHA-18 | **Structured JSON logs to stdout**, through NestJS's built-in logger in JSON mode, as U2 (NFR-OI-22). Every line has time, level, the request id (`Soorma-Request-Id`), and, for security events, an event name. **A human is named only by `hp_` + base64url of the first 128 bits of HMAC-SHA-256 under E's own log-pseudonym key** (shared-infrastructure.md), never by identifier. **No token, key, or identifier** appears in a log, in whole or part | P-06; SECURITY-03; BR-RF-03 | A test runs every S2 flow with known tokens and known presented identifiers (existing and unknown) and asserts none appears in the captured logs, and that each event naming a human carries E's pseudonym |
| NFR-EHA-19 | **Named security events**: `credential.issued`, `credential.renewed`, `credential.ended`, `credential.refused` (with the internal reason, BR-RF-03), `grant.made`, `grant.denied`, `first_grant.applied`, `orglevel.unavailable`, `store.unavailable`, and **`throttle.refused`** (NFR-EHA-04, 05). **Alert rules are added to `deploy/monitoring/alerts.yaml`** over `credential.refused`, `grant.denied`, `orglevel.unavailable`, `store.unavailable`, and `throttle.refused` | P-06; SECURITY-14 | Each rule names an event this list defines; a test asserts every event is emitted by its flow |
| NFR-EHA-20 | **The user's SECURITY-14 and SECURITY-03 decisions apply unchanged** (U2 NFR-OI-24; shared-infrastructure.md): the rules are defined as files and nothing evaluates them in M1; log integrity, 90-day log retention, and a centralized log service are not applicable in M1. Carried to Build and Test and to the first hosted deployment | P-06; P-09 (the user's decisions) | Listed in the Build and Test summary |

`throttle.refused` is added to P-06's list here, because Q2 A introduces the refusal it names. It, and `Retry-After: 5` on every S2 503, were accepted at the user's review (2026-11-11).

### Retention (Q5 A; P-07)

| ID | Requirement | Source | Verification |
|---|---|---|---|
| NFR-EHA-21 | **Nothing is pruned in M1**: grants, credential records, and attribution records are kept (attribution pruning, PF FR-013, is absent from M1). Each attribution record names its credential by id, so the record alone stays recoverable either way (BR-AT-07) | Q5 A; P-07; M1-FR-12; BR-AT-08 | Review: no pruning job, and no `DELETE` on these tables, in S2 or its migrations |

### Carried Without a Question (P-08 to P-10)

| ID | Requirement | Source | Verification |
|---|---|---|---|
| NFR-EHA-22 | **No new dependency**: U1's toolchain and dependency policy apply unchanged (register, exact versions, the 7-day cooldown, the licence allowlist, the empty lifecycle-script allowlist). Every runtime selection is already locked at U2's version ([tech-stack-decisions.md](tech-stack-decisions.md)) | P-08; SECURITY-10 | `check:deps` in CI; `DEPENDENCIES.md` gains only workspace rows for `services/control-gateway` |
| NFR-EHA-23 | **TLS 1.3** on S2's edge, from S2 to its store, and from S2 to S1. S1 is authenticated by its certificate under the local CA (`org-gateway.soorma.internal`); every S1 call is signed with E's caller key (U2 F-3) | P-09; SECURITY-01 in transit; D-EHA-27 | Designed at NFR Design and Infrastructure Design; a test that an S1 stand-in with another CA's certificate is refused |
| NFR-EHA-24 | **SECURITY-01 at rest is not applicable in M1** for the environment store, by the user's decision (shared-infrastructure.md), carried to the first hosted deployment. The store holds no secret material: credential records hold no token (Functional Design, domain-entities) | P-09 (the user's decision) | Listed in the Build and Test summary |
| NFR-EHA-25 | **Every comparison of secret-derived values is constant-time** (`crypto.timingSafeEqual`), and **every id and random value comes from Node's CSPRNG**, at least 128 bits (D-EHA-30), as U2 (NFR-OI-29, 30) | P-08; D-EHA-30 | Review; the lint check for `===` on secret-derived values |
| NFR-EHA-26 | **Time-based behaviour is tested with an injected clock**, never real waiting: expiry and its cap, leeway, the key refresh schedule and refetch rate, the S1 timeout, and the throttling waits | P-10 | Every clock test above uses the injected clock |

---

## 4. Obligations Carried Forward

| To | Item |
|---|---|
| **NFR Design (U4)** | The credential format and E's minting key ring; the verify-key cache's schedule and refetch limiter (NFR-EHA-08); the S1 caller and its signer (NFR-EHA-07; U2 F-3); the two throttling semaphores and where the request slot is taken (NFR-EHA-04, 05); the uniqueness constraint's physical form (NFR-EHA-12); the security events (NFR-EHA-19); request ids and the error handler, as U2 P-08 |
| **Infrastructure Design (U4)** | S2 for E and E2; **one PostgreSQL 18 instance per environment** with its own roles, credentials, certificate, and volume (NFR-EHA-09); `e-migrate` and `e2-migrate` (NFR-EHA-14); `org-internal-{env}`; each environment's secrets volume and init container; E's caller key pair (public half to S1's `internalCallers`); E's minting key; E's log-pseudonym key; `tenancy.yaml` additions; the alert rules in `deploy/monitoring/alerts.yaml` (NFR-EHA-19). **The user's P-04 addition**: S1's signing-key rotation steps in the operations notes say **"wait at least 5 minutes"** at step 2 (NFR-EHA-08) |
| **Code Generation (U4)** | U2 amendment A7 in S1 and U2's tests, with S1's image build in the gate; the four contract operations and two codes; the concurrent start-up test (NFR-EHA-12) |
| **Build and Test** | The performance figures (NFR-EHA-15), reported; the rotation test (NFR-EHA-08a); the S1-stopped demonstration (Functional Design §17, D-EHA-23); the accepted residuals: the logout residual of at most 15 minutes (NFR-EHA-02), the Admin self-grant, the organization-level outage, and the instance flood (Q2); the SECURITY-14, SECURITY-03 centralized-log-service, and SECURITY-01 at-rest decisions (NFR-EHA-20, 24) |
| **First hosted deployment** | Per-principal and per-source rate limits on S2 (NFR-EHA-06), which answer the instance-flood residual; with U2's carried items (log integrity and retention, an alerting service, a centralized log service, encryption at rest) |

---

## 5. Security Compliance at NFR Requirements

| Rule | Status | Note |
|---|---|---|
| SECURITY-01 | Compliant in transit; **at rest not applicable in M1, by the user's decision** | NFR-EHA-23, 24 |
| SECURITY-02, 06, 07 | N/A at this stage | Infrastructure Design |
| SECURITY-03 | Compliant, **except the centralized log service: not applicable in M1, by the user's decision** | NFR-EHA-18, 20. The PII clause is met by E's log pseudonym |
| SECURITY-04 | N/A | No HTML served |
| SECURITY-05 | Compliant | NFR-EHA-13, 16, 17 |
| SECURITY-08 | Compliant | Unchanged from Functional Design: every S2 operation needs a credential; deny by default (BR-PR, BR-EV) |
| SECURITY-09 | Compliant | Current, supported versions; no default credentials (every secret from configuration) |
| SECURITY-10 | Compliant | No new dependency (NFR-EHA-22) |
| SECURITY-11 | Compliant | Per-instance throttling: 64 requests and 8 S1 calls in flight, 1 s wait, then 503 (NFR-EHA-04, 05); sign-in bounded per principal at S1 (U2); no unauthenticated surface on S2; misuse cases (Functional Design §15). **Accepted residual (Q2, the user's)**: one valid principal flooding S2 can fill an instance's request slots, so other callers on that instance get 503 until the flood drains, as U2's flood residual (NFR-OI-20). **Per-principal and per-source limits are carried to the first hosted deployment** (NFR-EHA-06) |
| SECURITY-12 | Compliant | Credentials of 15 minutes, capped at the sign-in (NFR-EHA-01); no leeway on E's own `exp` (NFR-EHA-03); ending the credential is its own logout. **Accepted residual**: the post-logout credential, at most 15 minutes (NFR-EHA-02; Functional Design §16) |
| SECURITY-13 | Compliant | `jose` with `Ed25519` fixed in code; parameterized SQL; checksummed migrations (NFR-EHA-14) |
| SECURITY-14 | **Not applicable in M1, by the user's decision** | Events named and alert rules defined as files (NFR-EHA-19); nothing evaluates them in M1 (NFR-EHA-20) |
| SECURITY-15 | Compliant | Fail closed on an unreachable store, an unreachable or slow S1, and full throttling slots (503, `Retry-After`) (NFR-EHA-04, 05, 07; §3 *The Environment Store*) |

**Security findings**: none blocking.

## 6. Invariant Compliance at NFR Requirements

| Code | Status | Note |
|---|---|---|
| I1 | Covered | One store instance per environment, with its own roles and credentials (NFR-EHA-09) |
| I2, I4, I5, I6, I9 | No change | As in [invariant-coverage-matrix.md](../functional-design/invariant-coverage-matrix.md) |
| I3 | Covered | Throttling is an availability control, never an identity input; per-source counting stays an availability control when built |
| I7 | Covered | No contract change at this stage |
| I8 | Covered | No new dependency; everything open source under the allowlist |
| I10 | Covered | Nothing depends on a managed runtime; state is in the environment store, not the process |
| I11 | N/A | Construction is where technology is selected |

**Invariant findings**: none blocking.
