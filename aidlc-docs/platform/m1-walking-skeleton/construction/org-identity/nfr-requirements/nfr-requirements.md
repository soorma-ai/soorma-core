# NFR Requirements: U2 `org-identity`

**Unit**: U2 `org-identity` (soorma-core#5). Control face, organization level
**Built against**: ID @ `prd-identity-v1.0`, PF @ `prd-platform-foundations-v1.3`
**Decisions from**: the NFR Requirements plan, Q1 to Q12, answered 2026-11-08 (verbatim in
`audit.md`). Every answer is technology (I11); no specification gap
**Companion**: [tech-stack-decisions.md](tech-stack-decisions.md)
**Functional Design**: [../functional-design/business-rules.md](../functional-design/business-rules.md)
(§14 lists what it carried here; every item is answered below)

---

## 1. The Plane-Face Profile: ID §10, carried forward

U2 is a control-face unit citing **ID §10 *NFR Profile*** @ `prd-identity-v1.0`
(nfr-requirements.md Step 1.5). Its properties are settled. **No data-face property is
added**: no per-request latency target, and no cache-bounded availability.

| Property | ID §10 | Met by |
|---|---|---|
| Consistency | Read-your-writes for the actor | NFR-OI-16 (one primary; no replicas) |
| Durability | **Highest** for the human principal record | NFR-OI-15 |
| Human-in-the-loop latency | Interactive for sign-in | NFR-OI-19 |
| Auditability | Every operation recorded | Functional Design BR-REC; NFR-OI-21, 25 |
| Abuse resistance | Sign-in and first authentication bounded per principal | NFR-OI-02 to 06 |
| Coverage checks | Fan out per environment | **N/A**: no organization-wide operation in M1 (ID FR-014 out) |
| The organization level | Its outage stops new sign-ins at once | Accepted; NFR-OI-20 |

## 2. Categories That Do Not Apply

| Category | Status | Reason |
|---|---|---|
| Scalability targets | N/A in M1 | Throughput is low (ID §10). S1 is stateless (M1-TECH-03): every piece of state, the abuse counters included, is in the org store, so it scales out behind the contract |
| Availability target | N/A in M1 | A local stack (M1-NFR-05). No hosted deployment exists |
| Usability (end users) | N/A | No user interface (no HTML, BR-CR-09). Errors are the contract's (D-OI-13) |

---

## 3. Requirements

Each has a verification target. Code Generation implements them, and Build and Test runs them.
**Time-based behaviour is tested with an injected clock**, never with real waiting.

### Sign-In Lifetimes (Q1 A)

| ID | Requirement | Source | Verification |
|---|---|---|---|
| NFR-OI-01 | **A sign-in token lives 15 minutes. Renewal never extends it past `authenticatedAt` + 12 hours** (the absolute maximum). The new expiry is the earlier of the two (BR-SI-04) | Q1 A; ID FR-009; SECURITY-12 | Clock tests: a renewal at 11 h 50 min gets an expiry at 12 h; at 12 h the token is expired and cannot be renewed (TC-OI-020) |

### The Abuse Bound (Q2 C, Q3 A)

| ID | Requirement | Source | Verification |
|---|---|---|---|
| NFR-OI-02 | **Window**: at most **10 failed attempts per slot in any sliding 15 minutes**. At the bound, attempts are refused until the oldest failure leaves the window. **Window counts only decay; nothing resets them**, a success included | Q2 C | Clock tests: the 11th failure within 15 minutes is refused; one is admitted once the oldest leaves the window; a success in between does not restore the allowance |
| NFR-OI-03 | **Backoff**: from the **5th consecutive failure**, each further attempt must wait twice as long as the previous wait, **from 1 second, capped at 15 minutes**. **A success resets the backoff only** (not the window) | Q2 C | Clock tests: waits of 1, 2, 4 s… up to 900 s; a success resets the consecutive count |
| NFR-OI-04 | A refusal by either is `too_many_attempts` with **`Retry-After` = the later of the two waits**, in whole seconds, rounded up | BR-ERR-06; BR-AB-02 | Test over both |
| NFR-OI-05 | **The counter table is fixed-size and lives in the org store** (not process memory, M1-TECH-03). The presented reference `{organization, principal}` is hashed with **HMAC-SHA-256** under a **secret from organization-level configuration** (at least 256 bits; delivery is Infrastructure Design's) into one of **2^20 slots**. A slot row holds a fixed-size window record and the backoff state, so the table can never exceed 2^20 rows. **A collision can only over-count**: never looser for a real principal | Q3 A; BR-AB-05 | Test: two references forced into one slot share its count; the row count never exceeds the slot count; the key comes from configuration |
| NFR-OI-06 | **Admission and recording are atomic per slot**: concurrent attempts cannot together exceed the bound | BR-AB-01 | Concurrency test: 20 parallel wrong attempts admit at most 10 |

**What the bound achieves, stated plainly (Q2's correction)**: about **96 guesses a day** per
principal at the backoff cap, and at most 960 a day through the window alone. **Neither fits
NIST SP 800-63B's limit of 100 consecutive failed attempts**, which assumes a lockout. M1 has
none (BR-AB-04), so no option meets that figure; C comes closest. K's minimum length, the
breached-list check (NFR-OI-13), and P where enrolled carry the rest.

**Accepted residual (Q2)**: **an attacker who knows a principal's identifier can keep its
allowance used up**, so that principal's correct attempts are refused too, for as long as the
attack lasts. It never becomes permanent (BR-AB-04), and **detection is NFR-OI-23's alert**
on bound refusals. **Counting attempts per source, as well as per principal, is carried to
the first hosted deployment** (an availability control, never an identity decision, I3).

**In the same class, also accepted for the local M1 (added at the NFR Requirements
review)**: **a flood of distinct unknown identifiers** is admitted, because each lands on its
own counter slot, and **forces one decoy hash each** (BR-RF-03). The hashing concurrency
bound (NFR-OI-20) keeps memory safe, but the result is **`unavailable` (503) for every
caller, the real Admin included**, while the flood lasts. Carried, with per-source counting,
to the first hosted deployment.

### The Second Factor: TOTP (Q4 A)

| ID | Requirement | Source | Verification |
|---|---|---|---|
| NFR-OI-07 | **P's M1 type is TOTP (RFC 6238)**: HMAC-SHA-1, 6 digits, 30-second step, one step of drift either side. `authenticatorType` is `totp`. `beginSecondFactor` returns the seed (Base32) and an `otpauth://` URI | Q4 A; BR-P-08 | RFC 6238 Appendix B test vectors; drift tests at ±1 and ±2 steps |
| NFR-OI-08 | **Each code is accepted at most once per principal**: the last accepted step is stored with the P record, and a code for that step or an earlier one is refused | BR-P-09 | Replay test: the same code twice, and an earlier step's code after a later one, are refused |
| NFR-OI-09 | **The seed is 160 bits from the CSPRNG, and is stored encrypted at rest** under organization-level key material (the scheme and key are NFR Design's). It is never logged, and returned only once, by `beginSecondFactor` | Q4 A; SECURITY-01, 12 | Test: the stored seed is not the plaintext seed; NFR Design names the cipher |
| NFR-OI-10 | **A Pending P Enrollment lives 10 minutes** | Q4 A; D-OI-25 | Clock test: confirmation at 10 min 1 s is `second_factor_not_confirmed` |

A wrong TOTP code at `authenticate` or `changeMaterial` is a failed material verification and
counts against the bound (BR-AB-03). A failed confirmation does not (BR-P-06).

### The K Hash (Q6 A)

| ID | Requirement | Source | Verification |
|---|---|---|---|
| NFR-OI-11 | **Argon2id (RFC 9106) through Node's built-in `crypto.argon2`**: memory 64 MiB, 3 passes, parallelism 1, a 16-byte salt from the CSPRNG, a 32-byte tag. **Input: the UTF-8 encoding of the NFKC-normalized K, whole**, never truncated. The algorithm and parameters are stored with each verifier, so they can be raised later without a reset. **Enrollment material uses the same hash**, so `firstAuthenticate` costs the same whether or not the principal exists. The **decoy verifier** (BR-RF-03) uses the same parameters | Q6 A; BR-K-08; M1-NFR-09 | Tests: two Ks differing only after byte 72, and only in their last code point at 256, both verify distinctly; the stored form records `argon2id` and its parameters |
| NFR-OI-12 | **Condition (the user's, Q6)**: `crypto.argon2` must be marked **Stable** in Node 26's documentation. **Confirmed at Code Generation. If it is still Experimental, generation stops and asks.** The recorded fallback is **scrypt** through `crypto.scrypt` (N = 2^17, r = 8, p = 1), which also takes the full input | Q6 | Code Generation stop condition |

The probe of 2026-11-08 (Node 26.13.0, this workstation): Argon2id at these parameters took
**169 ms**, and printed no experimental warning. That is not the stability check above.

### The Breached-Secret List (Q7 A)

| ID | Requirement | Source | Verification |
|---|---|---|---|
| NFR-OI-13 | **SecLists' top 1,000,000 passwords (MIT)**, shipped as a **pinned artifact**: each entry NFKC-normalized and hashed with SHA-256, truncated to 64 bits, sorted, and committed as one binary file (8 MiB). A **manifest** records the source repository, commit, path, licence, the SHA-256 of the source file, and the SHA-256 of the derived file. **The build checks the derived file's SHA-256 against the manifest**, as U1 checks its meta-schema (NFR-WC-11). A script regenerates it from the pinned source. The licence is checked again at Code Generation | Q7 A; BR-K-05 | Build check: digest match; test: a listed password is `secret_rejected` with `breached` (TC-OI-013) |
| NFR-OI-14 | **Context words are refused as well**: a K that, case-folded, contains the principal identifier, the organization identifier, or `soorma`. Only identifiers of 4 or more characters are matched, so a short identifier does not refuse common Ks | Q7 A; NIST SP 800-63B | Tests for each word, and a 3-character identifier not matched |

Neither K nor any digest of it leaves the organization level: the list is searched in memory,
and no outside service is called (BR-K-05). With 64-bit digests, a false match is negligible
(10^6 entries in 2^64).

### The Org Store (Q8 A)

| ID | Requirement | Source | Verification |
|---|---|---|---|
| NFR-OI-15 | **PostgreSQL 18**, one database for the organization level. **Durability**: `synchronous_commit` on; a response reports success only after the transaction commits. Every multi-record change (BR-FA-02, BR-MC-03, BR-P-05) is **one transaction**. Single use is a conditional update on `state = 'enrollment'` that must affect exactly one row (D-OI-04) | Q8 A; ID §10 durability | Tests: a concurrent double first authentication commits once; a failure mid-transaction leaves no partial change |
| NFR-OI-16 | **Read-your-writes**: one primary, no read replicas in M1. A write is visible to the actor's next call | ID §10 | Test: sign in, end, renew with the same token: refused at once |
| NFR-OI-17 | **Access through `pg` with plain parameterized SQL only.** No SQL is built by string concatenation or template interpolation of a value. Identifiers in SQL are constants | Q8 A; SECURITY-05 | A lint or test rule: every query call passes a constant SQL text and a values array; review at Code Generation |
| NFR-OI-18 | **Migrations** are versioned SQL files, applied by an in-house runner **under a PostgreSQL advisory lock** (one fixed key), so concurrent runs are safe. *Amended at Infrastructure Design (D-ID-OI-02, the user's change)*: **the runner is a one-shot service, `org-migrate`, run before S1 starts, as the migrator role. S1 never holds the migrator password**, and starts only after `org-migrate` completes successfully, holding only the app role. Each migration runs in its own transaction and is recorded with its checksum. **A changed, already-applied migration fails `org-migrate`, so S1 does not start** | Q8 A; D-ID-OI-02 | Tests: two concurrent migrate runs apply each migration once; an edited applied migration fails the run; S1's configuration carries no migrator credential |

The store being unreachable fails closed: S1 answers `unavailable` (503, `Retry-After`) and
never issues a sign-in or changes material without its write committed (SECURITY-15).

### Latency and Hashing Concurrency (Q5 A)

| ID | Requirement | Source | Verification |
|---|---|---|---|
| NFR-OI-19 | **p95 at most 500 ms** for `authenticate` and `firstAuthenticate`, hashing included; **p95 at most 200 ms** for every other S1 operation. Measured on the local stack | Q5 A; ID §10 interactive | Performance test at Build and Test |
| NFR-OI-20 | **Hashing is bounded in concurrency**: at most **2 hash operations per CPU** (`os.availableParallelism()`) at once, decoys included. A request waits at most **2 seconds** for a slot; then it is `unavailable` (503, `Retry-After`). Memory for hashing is therefore bounded at 2 × CPUs × 64 MiB | Q5 A; SECURITY-11, 15 | Test: with the semaphore full, a request gets 503 after 2 s (clock-controlled) |

### The Failed Attempt Write (Q11 A)

| ID | Requirement | Source | Verification |
|---|---|---|---|
| NFR-OI-21 | **An in-process bounded queue of 10,000 records**, written after the response is sent. When full, a record is **dropped**, and the drop is counted and logged (with no secret). On graceful shutdown the queue is flushed. **A crash may lose what is queued: accepted**, because the bound lives in the counters (NFR-OI-05), not in these records | Q11 A; D-OI-27 | Tests: the response does not wait for the write; a full queue drops and logs; shutdown flushes |

### Logging, Alerting, and Retention (Q12 A; SECURITY-03, 14)

| ID | Requirement | Source | Verification |
|---|---|---|---|
| NFR-OI-22 | **Structured JSON logs to stdout**, through NestJS's built-in logger in JSON mode. Every line has time, level, the request id (`Soorma-Request-Id`), and, for security events, an event name. **No K, P proof or seed, enrollment material, token, or keyed-hash secret** appears in a log, in whole or part (BR-RF-05). *Amended at Infrastructure Design (the user's SECURITY-03 decision, 2026-11-08)*: **no human principal identifier appears in a log either**, known or merely presented, since identifiers are typically email addresses (BR-ID-05). Wherever a log line names a human, it carries the **log pseudonym**: `hp_` + base64url of the first 128 bits of **HMAC-SHA-256 under a dedicated log-pseudonym key** from organization-level configuration (separate from the counter secret), over the reference `{organization, principal}` in its canonical form (RFC 8785). Database records (Failed Attempt, sign-in) keep the identifier | SECURITY-03 | A test runs every S1 flow with known secret values **and known presented identifiers (existing and unknown)** and asserts none appears in the captured logs, and that each security event naming a human carries its pseudonym |
| NFR-OI-23 | **Named security events**: `auth.failed`, `auth.bound_refused`, `auth.second_factor_required`, `signin.issued`, `signin.ended`, `material.changed`, `failed_attempt.dropped`, `internal.call_refused`, `config.enrollment_ignored`. **Alert rules and a monitoring dashboard are defined as files** in `deploy/`, with thresholds over these events: at least repeated `auth.failed` **per log pseudonym** (*Amended at Infrastructure Design (the user's SECURITY-03 decision, 2026-11-08)*; never per identifier), any `auth.bound_refused`, any `internal.call_refused`, and any `failed_attempt.dropped`. The file format is Infrastructure Design's | Q12 A; SECURITY-14 | The files exist, and each rule names an event this list defines; a test asserts every event is emitted by its flow |
| NFR-OI-24 | **The user's SECURITY-14 decision (Q12, 2026-11-08), recorded as theirs**: in M1, alert rules and the dashboard are defined as files and the security events are named. **Log integrity and 90-day log retention are not applicable in M1**, because M1 is a local stack with no hosted deployment. **Carried as an obligation to Build and Test, and to the first hosted deployment** | Q12 (the user's decision) | Listed in the Build and Test summary |
| NFR-OI-25 | **Record retention**: Failed Attempt records, and ended or expired sign-in records, are kept **90 days**, then pruned by a **daily** job that runs under an advisory lock, so only one instance prunes. **Principal and material records are never pruned** (BR-HP-03) | Q12 A; BR-REC-06 | Clock test: a 91-day-old record is pruned, an 89-day-old one kept; principals untouched |

### Carried Without a Question (D-NFR-OI-01 to 06)

| ID | Requirement | Source | Verification |
|---|---|---|---|
| NFR-OI-26 | U1's toolchain and dependency policy apply unchanged: register, exact versions, the **7-day cooldown**, the licence allowlist, the **empty lifecycle-script allowlist** (U1 NFR-WC-12 to 20). Every version in tech-stack-decisions.md was chosen past the cooldown | D-NFR-OI-01 | `check:deps` in CI |
| NFR-OI-27 | **Request body bound at S1: 16 KiB** | D-NFR-OI-02; SECURITY-05 | Test: 16 KiB + 1 byte is `payload_too_large` |
| NFR-OI-28 | Validators are compiled once at start-up from the contract's schemas | D-NFR-OI-03 | Start-up test |
| NFR-OI-29 | **Every comparison of secret-derived values is constant-time** (`crypto.timingSafeEqual`) | D-NFR-OI-04 | Review; a lint check for `===` on verifier values |
| NFR-OI-30 | All random values come from Node's CSPRNG | D-NFR-OI-05 | Review |
| NFR-OI-31 | TLS on S1's edge and internal listeners; encryption at rest for the org store and the TOTP seeds. *Amended at Infrastructure Design*: TLS 1.3 everywhere (Q3 A); the TOTP seeds encrypted in the application (P-03); **the org store's encryption at rest is not applicable in M1, by the user's decision (Q4 B)**, carried to the first hosted deployment | D-NFR-OI-06; SECURITY-01 | Designed at NFR Design and Infrastructure Design |

---

## 4. Obligations Carried Forward

| To | Item |
|---|---|
| **NFR Design (U2)** | The sign-in token's claims and `soorma_si_` framing (within BR-CR-05); minting and verify-only key material and rotation; the TOTP seed encryption and its key; the slot row's layout (NFR-OI-05); the internal interface's caller credential (D-OI-22); the global error handler; how the request id is generated |
| **Infrastructure Design (U2)** | `deploy/local/` for the organization level and PostgreSQL 18; delivery of enrollment material (M1-TECH-06), the keyed-hash secret, and key material; TLS; the alert-rule and dashboard file format |
| **Code Generation (U2)** | The Q6 stop condition (NFR-OI-12); the SecLists licence re-check (NFR-OI-13); **mark the derived breached-list file `binary` in `.gitattributes`** (NFR-OI-13); the A4 contract work (Functional Design §14) |
| **Build and Test** | The performance test (NFR-OI-19); the SECURITY-14 decision and its obligation (NFR-OI-24); the SECURITY-03 centralized-log-service decision (not applicable in M1, the user's) and its obligation; the accepted residuals: the allowance exhaustion (Q2), the unknown-identifier flood (503 for every caller), and the K or K + P compromise (Functional Design §15) |
| **First hosted deployment** | Counting attempts per source as well as per principal (Q2), which also answers the unknown-identifier flood; log integrity and 90-day log retention, an alerting service, and a **centralized log service** (NFR-OI-24; SECURITY-03, the user's decision) |

---

## 5. Security Compliance at NFR Requirements

| Rule | Status | Note |
|---|---|---|
| SECURITY-01 | N/A at this stage | Encryption at rest and in transit are designed at NFR Design and Infrastructure Design (NFR-OI-09, 31) |
| SECURITY-02, 06, 07 | N/A at this stage | Infrastructure Design |
| SECURITY-03 | Compliant, **except the centralized log service: not applicable in M1, by the user's decision** | NFR-OI-22. *Amended at Infrastructure Design (the user's SECURITY-03 decision, 2026-11-08)*: the earlier "Compliant" here did not check the centralized-log-service clause. That clause is not applicable in M1, on the same grounds as SECURITY-14 and SECURITY-01 at rest (a local stack, no hosted deployment), and is carried to Build and Test and the first hosted deployment with NFR-OI-24's obligations. The PII clause is met by the log pseudonym (NFR-OI-22) |
| SECURITY-04 | N/A | No HTML served |
| SECURITY-05 | Compliant | NFR-OI-17, 27, 28 |
| SECURITY-08 | Compliant | Unchanged from Functional Design |
| SECURITY-09 | Compliant | Current, supported versions; no default credentials (every secret from configuration) |
| SECURITY-10 | Compliant | NFR-OI-26; each new dependency past the cooldown (tech-stack-decisions.md) |
| SECURITY-11 | Compliant | The bound (NFR-OI-02 to 06); hashing concurrency (NFR-OI-20); misuse cases. **Accepted residuals** (local M1): allowance exhaustion (Q2), and the unknown-identifier flood that saturates hashing and returns 503 to every caller |
| SECURITY-12 | Compliant | Argon2id over the full input (NFR-OI-11); breached list (NFR-OI-13, 14); TOTP for MFA (NFR-OI-07 to 10); sessions of 15 minutes and 12 hours (NFR-OI-01); the bound. **Accepted residual**: compromise of K or K + P is unrecoverable in M1 (Functional Design §15) |
| SECURITY-13 | Compliant | Pinned breached-list artifact with a digest check (NFR-OI-13); jose with one algorithm fixed in code (tech-stack T-OI-03); parameterized SQL |
| SECURITY-14 | **Not applicable in M1, by the user's decision** | M1 is a local stack with no hosted deployment. Alert rules and the dashboard are **defined as files**, and the security events are named (NFR-OI-23), but **nothing evaluates them in M1**. Log integrity and 90-day log retention are N/A for the same reason. The user's decision of 2026-11-08 (NFR-OI-24), carried to Build and Test and to the first hosted deployment |
| SECURITY-15 | Compliant | Fail closed on an unreachable store and on hashing saturation (503); the global error handler is NFR Design's |

**Security findings**: none blocking.

## 6. Invariant Compliance at NFR Requirements

| Code | Status | Note |
|---|---|---|
| I1, I2, I4, I5, I6, I9 | No change | As in [invariant-coverage-matrix.md](../functional-design/invariant-coverage-matrix.md) |
| I3 | Covered | Per-source counting is carried as an availability control, never an identity input; the keyed-hash secret comes from configuration |
| I7 | Covered | No contract change at this stage |
| I8 | Covered | Every dependency is open source under the allowlist; nothing commercial |
| I10 | Covered | Nothing depends on a managed runtime; state is in the org store, not the process |
| I11 | N/A | Construction is where technology is selected |

**Invariant findings**: none blocking.
