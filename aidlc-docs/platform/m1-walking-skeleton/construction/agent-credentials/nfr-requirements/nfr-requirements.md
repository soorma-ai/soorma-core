# NFR Requirements: U6 `agent-credentials`

**Unit**: U6 `agent-credentials` (soorma-core#9). Data face, environment level. A new deployable,
S3 `data-gateway` (`exchangeBootstrap`, `renewAgentCredential`); P5's revocation read and its
fail-closed cache; P8's bound per agent
**Built against**: PF @ `prd-platform-foundations-v1.3`, ID @ `prd-identity-v1.0`
**Decisions from**: the NFR Requirements plan, Q1 to Q5 and P-01 to P-17, answered
2026-11-12 (verbatim in `audit.md`), with the user's precision on P-08 (NFR-AC-05). Every answer
is technology (I11); no specification gap
**Companion**: [tech-stack-decisions.md](tech-stack-decisions.md)
**Functional Design**: [../functional-design/business-rules.md](../functional-design/business-rules.md)
(§17 lists what it carried here: B, L, M, the bound's values with the lockout residual, S3's
throttle, the latency budgets; every item is answered below)

**The three numbers**: **B = 60 seconds** (the propagation bound), **L = 15 minutes** (the agent
credential's lifetime), **M = 24 hours** (a lineage's maximum age). B < L ≤ M.

---

## 1. The Plane-Face Profile: PF §9, carried forward

U6 is a data-face unit citing **PF §9 *NFR Profile*** @ `prd-platform-foundations-v1.3`
(nfr-requirements.md Step 1.5). Its properties are settled. **No control-face property is
added**: no read-your-writes target for a human operator, and no "highest durability" class
(PF §10's, U5's).

| Property | PF §9 | Met by |
|---|---|---|
| Latency: revocation read | **Hot path; must not dominate request latency** | NFR-AC-16: a cache hit is a memory lookup; a miss one indexed read |
| Latency: exchange and renewal | **Startup and periodic; a slower budget is acceptable** | NFR-AC-17 |
| Availability | **High, but bounded by the cache rather than absolute** | At S4 (U7), the cache for B (NFR-AC-01). **At S3 the store is the floor**, both operations writing (NFR-AC-14) |
| Throughput | **Scales with total request volume, not agent count** | One cache entry per active credential per S4 instance (NFR-AC-15); S3 stateless (NFR-AC-14) |
| Isolation | **Per environment; no global revocation list** | One store, cache key space, and bound table per environment (NFR-AC-09; Functional Design BR-RC-04) |
| **Revocation propagation bound** | **Finite, published, platform-set, not tenant-configurable; it *is* the cache TTL** | NFR-AC-01, 04, 05 |

## 2. Categories That Do Not Apply

| Category | Status | Reason |
|---|---|---|
| Availability percentage | N/A in M1 | A local stack (M1-NFR-05). No hosted deployment exists |
| Scalability targets beyond statelessness | N/A in M1 | S3 is stateless and scaled out (NFR-AC-14); no capacity plan for a local stack |
| Usability (end users) | N/A | No user interface. Errors are the contract's problem documents |

---

## 3. Requirements

Each has a verification target. Code Generation implements them, and Build and Test runs them.
Time-based behaviour is tested with an injected clock (NFR-AC-26). Test case ids (TC-AC-nnn) are
assigned at QA construction enrichment: *each verification below names its TC id (QA construction enrichment, 2026-11-12)*.

### The Three Numbers (Q1 B, Q2 A, Q3 B; P-01, P-08 with the user's precision)

| ID | Requirement | Source | Verification |
|---|---|---|---|
| NFR-AC-01 | **B = 60 seconds**: a `not_revoked` answer is served for at most 60 s from its read's issue; past it, with revocation state unreadable, the request is denied. **One defined value**, read by P5's cache and by U3's term cache as its TTL (NFR-AE-10); no second setting exists. *Consistency fix from NFR Design (2026-11-12, plan Q1 A)*: **a constant in code, `PROPAGATION_BOUND_MS` in `packages/credentials`, not deployment configuration** (formerly "one configured value … deployment configuration, never tenant-facing"). PF FR-012 makes the bound "**platform-set and not tenant-configurable**", and rejects "**a tenant-configurable bound — relocates a safety property into configuration**"; soorma-core is self-hosted, and the team running a deployment is typically the tenant (PF §6 *Deployment Note*), so a value in deployment configuration would be one a tenant can change. **U7 passes `PROPAGATION_BOUND_MS` to U3's term cache** (§4) | Q1 B; PF FR-012, §9; D-AC-18; NFR Design Q1 A | Clock tests: served at 59.999 s, re-read at 60 s; with the store down, served at 59.999 s and denied at 60 s; a test that P5's cache is built with `PROPAGATION_BOUND_MS` and that no configuration key for a bound or a TTL exists (U7 adds the term-cache half) (TC-AC-054) |
| NFR-AC-02 | **L = 15 minutes**: a token's `exp` is at most 15 minutes after its `iat`, the same as U4's human environment credential (NFR-EHA-01) | Q2 A; PF FR-010, §7a | Clock tests at bootstrap and renewal (TC-AC-055) |
| NFR-AC-03 | **M = 24 hours**: a lineage's last token expires at most 24 hours after its bootstrap; renewal never sets `exp` past it, so renewing the last token is `credential_expired`, and the instance re-bootstraps | Q3 B; D-AC-02 | Clock tests: a renewal at 23:50 caps `exp` at 24:00; a renewal at 24:00 is `credential_expired`; a bootstrap then starts a new lineage (TC-AC-023) |
| NFR-AC-04 | **B < L ≤ M**, *Consistency fix from NFR Design (2026-11-12, plan Q1 A)*: **checked by a unit test over the three constants** (`PROPAGATION_BOUND_MS`, `AGENT_CREDENTIAL_LIFETIME_MS`, `LINEAGE_MAX_AGE_MS`), formerly "checked at start-up from configuration": the numbers are code, not configuration, so they cannot be misconfigured at a deployment (PF FR-012, "platform-set and not tenant-configurable"; its rejected alternative, "a tenant-configurable bound — relocates a safety property into configuration") | P-01; NFR Design Q1 A | A unit test over the constants; a docs test that the contract's published values equal them (NFR-AC-05) (TC-AC-056) |
| **NFR-AC-05** | **What the contract publishes** (`contract/conventions/credentials.md`, a *Revocation and Lifetimes* section), **as the user stated at P-08**: **B is published as the platform's bound** (PF FR-012): revocation reaches every request within 60 seconds, and past it, with revocation state unreadable, a request is denied. **L and M are published as upper bounds only**, and the contract states that clients: **schedule renewal from the response's `expiresAt`**; **re-bootstrap when renewal answers `credential_expired` at the end of the credential's lifetime**; **never hard-code L or M**. So **L and M can change without a contract break**. The `expiresAt` of every response is the authority, and a shorter one is always compatible | P-08, with the user's precision; PF FR-012, §17 | The docs test: the section exists, states 60 s as the bound and L and M as upper bounds, and contains the three client rules; a test that every response's `expiresAt` is at most L after now and at most the lineage end (TC-AC-038, TC-AC-055) |

### The Bootstrap Bound (Q4 B; P-07)

| ID | Requirement | Source | Verification |
|---|---|---|---|
| NFR-AC-06 | **Window**: at most **60 live attempts per slot in any sliding 60 seconds**. An attempt is live from admission; a success removes exactly its own entry, a failure keeps it until it leaves the window (U2's shape, BR-AB-AC-02). So in-flight attempts count, and **60 instances can start at once** | Q4 B; PF FR-027 | Clock tests: the 61st concurrent attempt is refused; a failure at 0 s frees its place at 60 s; 60 parallel successes all admitted (TC-AC-057) |
| NFR-AC-07 | **Backoff**: from the **10th consecutive failure**, each further attempt waits twice as long as the previous wait, **from 1 second, capped at 60 seconds**. **A success resets the backoff only**, not the window | Q4 B | Clock tests: waits of 1, 2, 4 … 60 s; the cap holds; a success resets the backoff (TC-AC-058) |
| NFR-AC-08 | A refusal by either is `too_many_attempts` with **`Retry-After` = the later of the two waits**, in whole seconds, rounded up (U2 NFR-OI-04) | U2 NFR-OI-04 | Test over both (TC-AC-059) |
| NFR-AC-09 | **The table**: **2^20 fixed slots per environment**, in E's store, chosen by **HMAC-SHA-256 of (E, the presented agent) under E's counter secret**, at least 256 bits, delivered as a mounted file (Infrastructure Design). **Admission and recording are atomic per slot**: concurrent attempts cannot together exceed the window (U2 NFR-OI-05, 06) | P-07; D-AC-06 | Concurrency test: 80 parallel failing attempts admit at most 60; a test that the same agent in E2 uses E2's table and secret (TC-AC-060) |
| NFR-AC-10 | **The lockout residual, quantified** (business-rules §16, the user's wording): an outsider who knows an agent's identifier can stop its new instances from starting **while the attack lasts, and for at most 60 seconds after it stops** (the window drains and the backoff cap is 60 s), while running instances renew unaffected. Stated in S3's README and the Build and Test summary | Q4 B; D-AC-06 | Clock test: after an attack stops, a correct bootstrap succeeds within 60 s; a renewal during the attack succeeds (TC-AC-061) |
| NFR-AC-11 | **The Failed Bootstrap Attempt writer is U2's** (NFR-OI-21): a bounded in-process queue of 10,000, batches of at most 100 every 250 ms, written after the response; a full queue or failed batch drops, counts, and logs (no secret); flushed on graceful shutdown; a crash may lose what is queued | P-09; D-AC-22 | U2's writer tests over the agent record; a test that an unknown agent's attempt writes no record (TC-AC-062, TC-AC-049) |

### Throughput, Availability, and Bounds (P-02 to P-05, P-11)

| ID | Requirement | Source | Verification |
|---|---|---|---|
| NFR-AC-12 | **At most 64 requests in flight per S3 instance**: a slot taken before check-order step 1, released once when the response is sent or the request aborts; one that cannot take a slot within 1 second is `unavailable` (503, `Retry-After: 5`) and logs `throttle.refused` (U4 NFR-EHA-04) | P-04; D-AC-29 | U4's throttle tests at S3, the 64-abort test included (TC-AC-063) |
| NFR-AC-13 | **Body bound 16 KiB** on both routes (U4 NFR-EHA-16); renewal refuses any body (`malformed_request`, pointer `''`) | P-05; SECURITY-05 | 16 KiB + 1 byte is `payload_too_large`; a 1-byte renewal body is `malformed_request` (TC-AC-064) |
| NFR-AC-14 | **S3 is stateless and scaled out**: no state beyond the request, the throttle's counter, and the failed-attempt queue. **Its availability is the environment store's**: a store outage makes both operations `unavailable` (503, `Retry-After: 5`), with nothing half-written. Running instances keep working through their tokens (up to L) and S4's cache (up to B). An accepted consequence of D-AC-01 | P-02, P-03; M1-TECH-03 | A test with the store stopped: both operations `unavailable`, nothing written (TC-AC-052) |
| NFR-AC-15 | **The cache is bounded in memory** per instance, at a maximum entry count set at NFR Design; evicting any entry only causes a re-read, and a `revoked` entry re-reads as `revoked` (terminal), so **eviction never admits anything** | P-11; D-AC-18 | A test at the bound: eviction then re-read; a revoked entry evicted is still refused (TC-AC-065) |

### Latency (Q5 A)

| ID | Requirement | Source | Verification |
|---|---|---|---|
| NFR-AC-16 | **The revocation read**: a cache hit at most **0.1 ms p99 in process**; a miss is **one indexed read** of E's revocation state. **Reported, not gated** | Q5 A; PF §9 | P5's benchmark (`pnpm bench:revocation`), run and reported at Build and Test; a review that the miss is one statement (TC-AC-066) |
| NFR-AC-17 | **`exchangeBootstrap` and `renewAgentCredential` at most 200 ms p95** on the local stack (one transaction each, no call outside E). **Reported, not gated**, as U2's TC-OI-062, U3's TC-AE-040, and U4's TC-EHA-070 | Q5 A; PF §9 | Performance test at Build and Test, reported (TC-AC-067) |

### The Token, Keys, and Cryptography (P-06, P-10, P-14, P-15)

| ID | Requirement | Source | Verification |
|---|---|---|---|
| NFR-AC-18 | **No leeway on `exp`**; an `iat` at most **30 seconds** ahead of the verifying instance's clock is accepted, further ahead `credential_refused` (U4 NFR-EHA-03) | P-06 | Clock tests at both edges (TC-AC-068) |
| NFR-AC-19 | **The agent key ring per environment** (D-AC-03), U4's ring shape (NP-EHA-02): Ed25519, a current signing key and recent verify keys by `kid`, keys of at least the algorithm's full strength. **Rotation keeps a retired key's verify half for at least L (15 minutes)**, stated in S3's README *Operations* with "wait at least 15 minutes" and a docs test (U4's pattern). S4 receives verify halves only (U7) | P-10; D-AC-03 | A rotation test: a token minted before rotation verifies until its `exp`; the docs test (TC-AC-069) |
| NFR-AC-20 | **Constant-time comparison and the CSPRNG**: the secret through `registrationSecretMatches`; `cid`, `jti`, and record ids at least 128 bits from Node's CSPRNG (U4 NFR-EHA-25) | P-15 | U2's `secret-compare` code check covers the new code (TC-AC-070) |
| NFR-AC-21 | **TLS 1.3** on S3's edge and from S3 to its store (U4 NFR-EHA-23). **SECURITY-01 at rest is not applicable in M1** (the user's decision): the store holds no token and no secret value | P-14 | U4's TLS tests at S3 (TC-AC-071) |

### Observability (P-12)

| ID | Requirement | Source | Verification |
|---|---|---|---|
| NFR-AC-22 | **Named security events** in U4's JSON log format: `credential.issued` and `credential.renewed` (agent kind), `bootstrap.refused` and `renewal.refused` with BR-RF-AC-03's internal reason, `bound.refused`, `store.unavailable`, `throttle.refused`. The agent and instance logged encoded as values (BR-ID-09); **never** the secret, its `id`, its digest, or a token | P-12; SECURITY-03 | A test capturing every log line of each operation and refusal, asserting the event names and that no secret-derived value appears (TC-AC-072) |
| NFR-AC-23 | **Alert rules** in `deploy/monitoring/alerts.yaml` (U2's format): bursts of `bootstrap.refused` per agent (guessing or a lockout attempt); any `agent_revoked` or `credential_revoked` refusal (a revoked credential still presented); `bound.refused`. **Nothing evaluates them in M1** (SECURITY-14, the user's decision) | P-12; SECURITY-14 | The alert file's schema test (U2's) (TC-AC-073) |

### Durability, Dependencies, and Time (P-13, P-16, P-17)

| ID | Requirement | Source | Verification |
|---|---|---|---|
| NFR-AC-24 | **U4's store guarantees** (NFR-EHA-10): one primary, `synchronous_commit` on, success reported only after commit; one transaction per operation. **Nothing is pruned in M1** (U4 NFR-EHA-21): credential records, revocation state, failed attempts, attribution records are kept. Credential records grow with bootstraps (each instance start and each lineage end): a residual, with pruning of ended lineages carried to the first hosted deployment | P-13 | Review: no pruning job; the store tests U4 runs (TC-AC-074) |
| NFR-AC-25 | **No new dependency** (§ tech-stack-decisions): `jose`, `pg`, `node:crypto` at U2's locked versions; the cache in-house | P-17; SECURITY-10 | The dependency register unchanged; `pnpm audit` (TC-AC-075) |
| NFR-AC-26 | **Time-based behaviour is tested with an injected clock**, never real waiting: L and M, the cache against B and its outage timeline, the bound's window and backoff, the throttle's wait, the rotation window | P-16 | Every clock test above (TC-AC-023, TC-AC-054, TC-AC-055, TC-AC-057, TC-AC-058, TC-AC-065, TC-AC-068, TC-AC-069) |
| NFR-AC-27 | **The bound's numbers are a security bound, not a tenant quota** (I8): platform constants that cap edge load per agent (PF FR-027), governing no tenant's capacity | Functional Design invariant matrix, I8 table | The I8 table (Code Generation, Build and Test) (TC-AC-046) |

---

## 4. Obligations Carried Forward

| To | Item |
|---|---|
| **NFR Design (U6)** | Tables in `env-store`'s sequence (the agent credential, revocation state, the bound's slots, failed attempts), each with E's three columns; privileges (revocation `SELECT` only; the credential's `expires_at` the only update); **D-AC-33's CHECK in a new migration, `0001` and `0002` untouched** (the user's, at Functional Design approval); the cache's physical form and its entry bound (NFR-AC-15); `packages/agent-identity`; P8 generalised over its subject and counter secret; the closure test; the agent key ring's loading; the configuration of B, L, M and the start-up check (NFR-AC-04) |
| **Infrastructure Design (U6)** | **Runs.** S3 per environment in Compose (E, E2): network, port, health, migrations; **two new secrets per environment**: the agent signing key ring (NFR-AC-19) and the bound's counter secret (NFR-AC-09); B, L, M as configuration; **U4's Compose-model rules applied to S3's services, rendering with every profile** (the user's rule); TC-AC-017 (S1 stopped) |
| **Code Generation (U6)** | NFR-AC-05's contract text in `credentials.md`, with a CHANGELOG entry; S3's README *Operations* (rotation: "wait at least 15 minutes"; the lockout residual, NFR-AC-10); `pnpm bench:revocation`; the alert rules; the tests named in §3 |
| **U7 (soorma-core#10)** | The cache at S4 is built with **`PROPAGATION_BOUND_MS`** (NFR-AC-01, as fixed at NFR Design), and **U7 passes `PROPAGATION_BOUND_MS` to U3's term cache** (`createCachingAgentFacts`'s `ttl`; NFR-AE-10), the user's instruction at NFR Design: one defined value, no configuration key; S4's subscribe stream ends within B of a revocation or of its credential's `exp` (T-2); S4 holds the agent key ring's **verify halves only**, kept for at least L after rotation (NFR-AC-19). Posted on #10 when this stage is approved |
| **soorma-sdk's session** (the brief's consumer: the `soorma-sdk` column of *Repositories and sessions* **consumes `soorma-core`'s wire contract at a pinned tag**; **the brief is not edited**) | **The user's precision on P-08, as the contract will state it** (NFR-AC-05): **B (60 s) is the platform's published bound; L and M are upper bounds only**. The SDK's *acquire* and *renew* (PF §11) **schedule renewal from each response's `expiresAt`**, **re-bootstrap when renewal answers `credential_expired` at the end of the credential's lifetime**, and **never hard-code L or M**, so L and M can change without a contract break. It reaches the SDK session through the contract at the schema tag (state, *soorma-sdk coordination*, step (b)), and is listed in the tag's release notes |
| **Build and Test** | NFR-AC-16 and 17 measured and reported; the residuals: the lockout (NFR-AC-10), S3's availability floor (NFR-AC-14), no pruning (NFR-AC-24); the SECURITY-01 at rest, SECURITY-03 log service, and SECURITY-14 decisions |
| **First hosted deployment** | Pruning of ended lineages (NFR-AC-24); the secret-record mitigation of the lockout (Functional Design §17, the user's Q6 addition); per-registration issuance limits (Functional Design §16) |

**Consistency fixes from NFR Design** (2026-11-12, plan Q1 A, marked in place): NFR-AC-01 and NFR-AC-04 (B, L, M are constants in code, not configuration; PF FR-012). The configuration of B, L, M named in the NFR Design and Infrastructure Design rows above is read as "the constants" (no configuration key).

**Consistency fix to Functional Design** (made at this stage, marked in place): business-rules
§13's row *The propagation bound published* now states B as the platform's bound and L and M as
upper bounds with the three client rules (NFR-AC-05).

---

## 5. Security Compliance at NFR Requirements

| Rule | Status | Note |
|---|---|---|
| SECURITY-01 | Compliant in transit (NFR-AC-21); **at rest not applicable in M1, by the user's decision** | The store holds no token and no secret value |
| SECURITY-02, 07 | N/A at this stage | S3's network and ports are Infrastructure Design's |
| SECURITY-03 | Compliant, **except the centralized log service: not applicable in M1, by the user's decision** | NFR-AC-22: no secret, its `id`, its digest, or a token in any log |
| SECURITY-04 | N/A | No HTML served |
| SECURITY-05 | Compliant | Body bound (NFR-AC-13); closed schemas (BR-BQ-01); parameterized SQL (U4 NFR-EHA-13) |
| SECURITY-06 | Compliant | Separate agent key ring (NFR-AC-19); revocation `SELECT` only (NFR Design) |
| SECURITY-08 | Compliant | Renewal's token verified on every request (NFR-AC-18); bootstrap explicitly unauthenticated and bounded |
| SECURITY-09 | Compliant | No default credentials; generic Problems; B, L, M are code constants checked by a test, so no deployment can misconfigure them (NFR-AC-04, as fixed at NFR Design) |
| SECURITY-10 | Compliant | No new dependency (NFR-AC-25) |
| SECURITY-11 | Compliant | The bound (NFR-AC-06 to 09), the throttle (NFR-AC-12), the alert rules (NFR-AC-23). **Accepted residual**: the lockout, at most 60 s after an attack stops (NFR-AC-10) |
| SECURITY-12 | Compliant | No password-class secret (U5 NFR-AR-02); brute force bounded (NFR-AC-06, 07); credentials expire server-side (NFR-AC-02, 03); no cookies; nothing hard-coded |
| SECURITY-13 | Compliant | Every bootstrap and renewal attributed; write-once records (U4 NFR-EHA-21) |
| SECURITY-14 | **Not applicable in M1, by the user's decision** | Events named and alert rules defined as files (NFR-AC-22, 23) |
| SECURITY-15 | Compliant | Fail closed: store failure `unavailable` (NFR-AC-14); past B, deny (NFR-AC-01); B, L, M not configurable (NFR-AC-04, as fixed at NFR Design) |

**Security findings**: none blocking.

## 6. Invariant Compliance at NFR Requirements

| Code | Status | Note |
|---|---|---|
| I1 | Covered | One bound table and counter secret per environment (NFR-AC-09); the cache keyed on E |
| I2, I3, I5, I6, I9, I10 | No change | As in [invariant-coverage-matrix.md](../functional-design/invariant-coverage-matrix.md) |
| I4 | Covered | Durability as U4's store (NFR-AC-24); nothing pruned |
| I7 | Covered | B published as the bound; L and M as upper bounds, so they can change without a break (NFR-AC-05) |
| I8 | Covered | The bound's numbers are a security bound, not a tenant quota (NFR-AC-27); no new dependency |
| I11 | N/A | Construction is where technology is selected |

**Invariant findings**: none blocking.
