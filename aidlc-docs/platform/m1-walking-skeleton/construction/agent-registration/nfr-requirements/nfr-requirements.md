# NFR Requirements: U5 `agent-registration`

**Unit**: U5 `agent-registration` (soorma-core#8). Control face, environment level. Two operations
on S2 `control-gateway`; the environment store gains registrations and registration secrets
**Built against**: PF @ `prd-platform-foundations-v1.3`, ID @ `prd-identity-v1.0`
**Decisions from**: the NFR Requirements plan, Q1 to Q5 and P-01 to P-12, answered
2026-11-11T22:17:08Z (verbatim in `audit.md`), with the user's additions to Q3 and Q4 and
correction to P-07. Every answer is technology (I11); no specification gap
**Companion**: [tech-stack-decisions.md](tech-stack-decisions.md)
**Functional Design**: [../functional-design/business-rules.md](../functional-design/business-rules.md)
(§17 lists what it carried here, with the user's additions at approval; every item is answered
below)

---

## 1. The Plane-Face Profile: PF §10, carried forward

U5 is a control-face unit citing **PF §10 *NFR Profile*** @ `prd-platform-foundations-v1.3`
(nfr-requirements.md Step 1.5). Its properties are settled. **No data-face property is added**:
no per-request latency budget and no cache-bounded availability for U5's operations. The
agent-facts query runs on U3's data-face path and is bound by **U3's** budget (NFR-AR-16).

| Property | PF §10 | Met by |
|---|---|---|
| Consistency | Read-your-writes for the acting principal; eventual elsewhere | NFR-AR-08 (one primary, no replicas); the held set read uncached (D-AR-07); new registrations visible to U3 at once (D-AR-19) |
| **Durability** | **Highest in the initiative**: registration is the sponsorship resolution path | NFR-AR-08 to 11 |
| Human-in-the-loop latency | **Not a constraint** | NFR-AR-15: no target; reported |
| Auditability | Every operation produces an attribution record | Functional Design D-AR-17, 18; NFR-AR-17 |
| Throughput | **Low**: registration and grant volume | NFR-AR-12, 13 |

## 2. Categories That Do Not Apply

| Category | Status | Reason |
|---|---|---|
| Scalability targets | N/A in M1 | Throughput is low (PF §10). S2 is stateless; every record is in the environment store |
| Availability target | N/A in M1 | A local stack (M1-NFR-05). No hosted deployment exists |
| Usability (end users) | N/A | No user interface. Errors are the contract's problem documents |

---

## 3. Requirements

Each has a verification target. Code Generation implements them, and Build and Test runs them.
Time-based behaviour is tested with an injected clock (NFR-AR-22). Test case ids (TC-AR-nnn) are
assigned at QA construction enrichment.

### The Registration Secret (Q1 A, Q2 A; P-01 to P-03)

| ID | Requirement | Source | Verification |
|---|---|---|---|
| NFR-AR-01 | **The value is `soorma_rs_{id}.{secret}`**: `{id}` is the secret record's id, 128 bits from Node's CSPRNG, base64url without padding (as U4 NP-EHA-11's ids); `{secret}` is **256 bits from the CSPRNG**, base64url without padding (43 characters). About 76 characters, within credentials.md's 256. **No checksum** (Q2 A). `.` is outside the base64url alphabet, so the value parses with one split into exactly two parts | Q2 A; P-01; Functional Design §17 (the user's additions) | Format test over generated values (prefix, two parts, lengths, alphabet); a statistical sanity test that 10,000 values are distinct (TC-AR-048) |
| NFR-AR-02 | **The stored verifier is unkeyed** (Q1 A): `SHA-256("soorma.registration-secret.v1" ‖ 0x00 ‖ the 32 decoded secret bytes)`, stored as 32 bytes. **A fast hash, never a slow password hash**: the input carries 256 random bits, so it cannot be guessed or reversed from a stolen row. No server-side key, so no new secret | Q1 A; P-02; the user's addition at Functional Design approval | Test vector: a fixed value and its literal expected digest; a test that the stored row holds 32 bytes and no part of the value (TC-AR-049, TC-AR-006) |
| NFR-AR-03 | **One encoding per value**: a `{secret}` that does not decode to exactly 32 bytes, or does not re-encode to the same 43 characters, is refused before hashing; the same for an `{id}` that is not a well-formed 128-bit id. U6's bootstrap applies it; every such refusal is the unknown-secret refusal (Functional Design §17, U6 row) | P-02 | One test per malformation (U6's, specified here) (TC-AR-050) |
| NFR-AR-04 | **Nothing secret is stored or logged**: the record holds the digest only; the value appears only in the issuance response, which carries **`Cache-Control: no-store`**; no log line, event, attribution record, or Problem carries the value or its digest | P-03; D-AR-16; SECURITY-03, 12 | A test capturing every log line and the attribution row of an issuance and asserting neither contains the value or the digest; a header test (TC-AR-036, TC-AR-006) |
| NFR-AR-05 | **Constant-time comparison and the CSPRNG** (U4 NFR-EHA-25): every comparison of a digest is `crypto.timingSafeEqual` over equal-length buffers; every id and secret comes from `crypto.randomBytes` | U4 NFR-EHA-25 | U2's `secret-compare` code check covers the new code (TC-AR-071) |

### The Cap on Active Secrets (Q3 A; P-07, as corrected)

| ID | Requirement | Source | Verification |
|---|---|---|---|
| NFR-AR-06 | **At most 10 active secrets per registration.** An issuance that would make an 11th is refused with **`secret_limit_reached`** (409, no `errors[]`), at step 9 **after the sponsor-or-Admin check** (BR-SE-04), so only a caller who may issue for the registration learns its count. **In M1 the cap is a lifetime total per registration**: retirement is absent. A new code, compatible (the code set is open) | Q3 A | The 10th succeeds and the 11th is refused; a caller who is neither sponsor nor Admin gets `forbidden`, never `secret_limit_reached` (TC-AR-051) |
| NFR-AR-07 | **The cap holds under concurrency, serialised per registration without `UPDATE` privilege** (the user's correction): a row lock (`SELECT … FOR UPDATE` or `FOR SHARE`) needs `UPDATE` privilege on the table, and D-AR-15 grants the app role none on registrations. The count and the insert run in one transaction under a **transaction-scoped lock keyed on the registration**, for example `pg_advisory_xact_lock` over a key derived from (organization, project, environment, `agent`), released at commit or rollback. **The physical form is NFR Design's** | Q3 A; P-07 as corrected; D-AR-15 | **Concurrency test at the cap**: with 9 active secrets, 5 concurrent issuances: exactly 1 succeeds, 4 are `secret_limit_reached`, and the registration ends with 10 secrets and 1 new attribution record; a test that the app role holds no `UPDATE` on registrations or secrets (TC-AR-052, TC-AR-053, TC-AR-027) |
| NFR-AR-24 | **The cap is a security bound, not a tenant quota** (the user's addition): each active secret is a separate way in, and PF §7a's issuer is only a lower bound on who knows it, so the bound limits exposure per registration. It is a constant of the platform, not configuration, and not a governance boundary over what a tenant may run. Recorded so in the I8 table (Functional Design invariant-coverage-matrix, *I8 Packaging Table*) | Q3's addition; PF §12; I8 | The I8 table, re-checked at Code Generation and Build and Test (TC-AR-046) |

### Durability (Q4 A)

| ID | Requirement | Source | Verification |
|---|---|---|---|
| NFR-AR-08 | **U4's store guarantees apply to registrations and secrets unchanged** (NFR-EHA-09 to 11): PostgreSQL 18, one instance per environment; `synchronous_commit` on; one primary, no read replica; a response reports success only after its transaction commits | PF §10; Q4 A | U4's durability tests extended to a registration: a `200` is returned only after commit (a fault injected before commit returns `unavailable` and leaves no row) (TC-AR-054) |
| NFR-AR-09 | **A documented backup and restore of an environment's store**: `pg_dump` (custom format) and `pg_restore`, as that environment's **migrator role**, in S2's README *Operations* section. **The dump contains human identifiers** (sponsors, issuers, and attribution records' actors), so it is written **only to a git-ignored path** (`deploy/local/.backups/`, added to `.gitignore` and `.dockerignore`), **with mode `0600`** (its directory `0700`), **never into the repository**; the README says so in those words. **Credentials and placement** (*added at approval, the user's, 2026-11-11*): the commands get the migrator's password **from its mounted secret file only, never from `PGPASSWORD`, any environment variable, or a command-line argument**: a pgpass file is built inside the container from `/run/secrets`, and an environment variable may hold only its path (`PGPASSFILE`). They run **inside the environment's network**, because the store is not published: a **one-shot Compose service** (or `run --rm`) on `{env}` that **mounts only the migrator's secret subpath** of `{env}-secrets`. Its mechanics are NFR Design's | Q4 A and the user's additions | A docs test that the README's *Operations* section names the command, the git-ignored path, the mode, and that the dump contains human identifiers; a test that `git check-ignore` covers the path; a test that the written file's mode is `0600` (TC-AR-055, TC-AR-056, TC-AR-057) |
| NFR-AR-10 | **The restore test**: back up a store holding registrations, secrets, and attribution records, restore into an empty store, and compare: the same registrations (every attribute), the same secret digests, the same attribution records. **It writes the dump to a temporary path, and deletes it** whether the test passes or fails | Q4 A and the user's addition | The test itself; it asserts the temporary path no longer exists afterwards. **The Compose-model test** (U4's, `deploy/test/`) **sees no password in the backup service's environment** and that it mounts only the migrator's secret subpath (*added at approval*) (TC-AR-058, TC-AR-059, TC-AR-060, TC-AR-057) |
| NFR-AR-11 | **Carried to the first hosted deployment**: replication, point-in-time recovery, off-host and encrypted backups, and backup retention. **Accepted residual in M1**: `pnpm stack:down -v` or a lost volume, with no backup taken, loses every registration, and with it sponsorship resolution for every record naming those agents | Q4 A | Listed in the Build and Test summary (TC-AR-061) |

### Throughput and Bounds (Q5 A; P-05, P-06)

| ID | Requirement | Source | Verification |
|---|---|---|---|
| NFR-AR-12 | **S2's throttle covers both operations unchanged** (NFR-EHA-04: 64 in flight per instance, a 1-second wait, then 503). Neither calls S1, so NFR-EHA-05 does not apply. Per-principal and per-source limits stay carried to the first hosted deployment (NFR-EHA-06) | P-05; SECURITY-11 | U4's throttle tests, with a registration among the requests (TC-AR-062) |
| NFR-AR-13 | **No bound on the number of registrations in M1** (Q5 A). **Accepted residual**: a holder of `agent:register` in E can create many permanent registrations; each is attributed to them, and S2's throttle limits the rate per instance. A per-sponsor or per-environment quota is carried to the first hosted deployment with NFR-EHA-06's limits; **a quota would be commercial** (PF §12, *Managed operation*), so in core only an abuse bound could be added | Q5 A; I8 | Listed in the Build and Test summary (TC-AR-061) |
| NFR-AR-14 | **The body bound stays 16 KiB** (NFR-EHA-16). The largest `registerAgent` body (a 64-character `agent`, two sets of 32 identifiers of 128 characters) is about 9 KiB | P-06; SECURITY-05 | A test that a maximal valid body is accepted and a 16 KiB + 1 byte body is `payload_too_large` (TC-AR-063) |

### Latency (P-04)

| ID | Requirement | Source | Verification |
|---|---|---|---|
| NFR-AR-15 | **No latency target** for `registerAgent` or `issueRegistrationSecret` (PF §10: "not a constraint"). Their p95 is **measured and reported at Build and Test on the running stack**, beside U4's (NFR-EHA-15), not gated | P-04; PF §10 | The Build and Test report (TC-AR-064) |
| NFR-AR-16 | **The agent-facts query** is one statement: an indexed lookup on the registration's unique key (organization, project, environment, `agent`) for the list of agents. Its share of U3's admission budget (NFR-AE-07) is measured in U3's benchmark (TC-AE-040, `pnpm bench:admit`) once P4 replaces U3's test port | P-08; D-AR-19; U3 NFR-AE-07, 08 | A counting test: one statement for a 33-agent list; TC-AE-040 re-run and reported at Build and Test (TC-AR-032, TC-AR-065) |

### Transactions and Privileges (P-07; D-AR-15, 18)

| ID | Requirement | Source | Verification |
|---|---|---|---|
| NFR-AR-17 | **Every multi-record change is one transaction**: a registration and its attribution record; a secret and its attribution record. Any failure writes nothing and is `unavailable`; a taken `agent` is `registration_exists` and writes nothing | D-AR-18; U4 NFR-EHA-11 | A fault injected at the attribution write leaves no registration (and no secret); the concurrent-registration test (D-AR-26) (TC-AR-041, TC-AR-024) |
| NFR-AR-23 | **The app role holds `INSERT` and `SELECT` only** on registrations and secrets: no `UPDATE`, no `DELETE`, granted in the migration (U4 D-EHA-29 pattern). The migrator role owns the tables | D-AR-15; SECURITY-06 | A privilege test: `UPDATE` and `DELETE` as the app role fail on both tables (TC-AR-027) |

### Observability (P-09)

| ID | Requirement | Source | Verification |
|---|---|---|---|
| NFR-AR-18 | **Named security events**: `registration.created`, `registration.refused`, `secret.issued`, `secret.refused`, each refusal with BR-RF-AR-03's internal reason (plus `secret_limit_reached`). A human is named only by E's log pseudonym; the agent identifier is logged encoded as a value (BR-ID-09); never the value or digest of a secret (NFR-AR-04) | P-09; U4 NFR-EHA-18, 19 | A test capturing the events of each operation and refusal (TC-AR-066) |
| NFR-AR-19 | **Alert rules** added to `deploy/monitoring/alerts.yaml`, in U2's format, for bursts of `exceeds_sponsor_ceiling` and `human_only_permission` (attempted escalation) and of `secret_limit_reached`. **Nothing evaluates them in M1** (SECURITY-14, the user's decision, U4 NFR-EHA-20) | P-09; SECURITY-14 | U2's alert-file format test covers the new rules (TC-AR-067) |

### Dependencies, the Refactor, and Time (P-10 to P-12)

| ID | Requirement | Source | Verification |
|---|---|---|---|
| NFR-AR-20 | **No new dependency**: SHA-256, the CSPRNG, base64url, `timingSafeEqual`, and advisory locks are `node:crypto`, `Buffer`, and PostgreSQL 18 built-ins | P-10; SECURITY-10 | `check:deps` in CI; no register change except workspace rows, if any (TC-AR-068) |
| NFR-AR-21 | **The `evaluateHuman` refactor** (D-AR-07) has no NFR effect beyond one held-set read per operation | P-11 | A counting `GrantSource` test: one read per operation (TC-AR-038) |
| NFR-AR-22 | **Time-based behaviour uses an injected clock**: `registeredAt` and `issuedAt` come from it (U4 NFR-EHA-26) | P-12 | Clock tests on both timestamps (TC-AR-069) |

---

**QA construction enrichment (2026-11-11)**: each verification above names its test case
(`inception/test-cases/agent-registration/`).

## 4. Obligations Carried Forward

| To | Item |
|---|---|
| **NFR Design (U5)** | The tables, the uniqueness on (organization, project, environment, `agent`), and the app role's privileges (NFR-AR-23); **the per-registration serialisation of the cap without `UPDATE` privilege** (NFR-AR-07; for example `pg_advisory_xact_lock` and its key derivation); the agent-facts statement and its index (NFR-AR-16); the secret's generation, parsing, and digest (NFR-AR-01 to 03) as functions U6 imports, so bootstrap and issuance share one definition; the Human Authority's shape in code (D-AR-07); the backup and restore procedure's mechanics (NFR-AR-09, 10): the command, the role it runs as, the path and its mode, and how the restore test obtains an empty store |
| **Infrastructure Design (U5)** | **Skipped** (§5 of tech-stack-decisions.md): no server-side key (Q1 A), and no new deployable, store, network, or secret |
| **Code Generation (U5)** | The `secret_limit_reached` code in the contract (a Functional Design consistency fix, below); `deploy/local/.backups/` in `.gitignore` and `.dockerignore`; S2's README *Operations* section; the tests named in §3 |
| **U6 (soorma-core#9)** | Bootstrap verifies with NFR-AR-02's digest over NFR-AR-01's value, after NFR-AR-03's encoding checks, through the shared functions (NFR Design), comparing with `timingSafeEqual`. Posted on #9 when this stage is approved |
| **Build and Test** | The p95 of both operations on the running stack (NFR-AR-15), reported; TC-AE-040 re-run with P4's agent-facts source (NFR-AR-16); the residuals: no registration bound (NFR-AR-13), the volume-loss residual without a backup (NFR-AR-11); the SECURITY-14, SECURITY-03 centralized-log-service, and SECURITY-01 at-rest decisions |
| **First hosted deployment** | Replication, point-in-time recovery, off-host and encrypted backups, retention (NFR-AR-11); per-sponsor or per-environment registration bounds with NFR-EHA-06's per-principal limits (NFR-AR-13) |

**Consistency fix to Functional Design** (made at this stage, marked in place): the
`secret_limit_reached` code (NFR-AR-06) joins business-rules §10 (check order), §13 (contract
changes), BR-SE-06, and domain-entities' *Problem Table additions*; and the I8 table records the
cap as a security bound (NFR-AR-24).

---

## 5. Security Compliance at NFR Requirements

| Rule | Status | Note |
|---|---|---|
| SECURITY-01 | Compliant in transit (U4 NFR-EHA-23); **at rest not applicable in M1, by the user's decision** | The store holds no secret value: digests only (NFR-AR-02, 04). The backup file is protected by its mode and path (NFR-AR-09); encrypted backups are carried (NFR-AR-11) |
| SECURITY-02, 07 | N/A | No new intermediary or network |
| SECURITY-03 | Compliant, **except the centralized log service: not applicable in M1, by the user's decision** | NFR-AR-18; no secret logged (NFR-AR-04) |
| SECURITY-04 | N/A | No HTML served |
| SECURITY-05 | Compliant | Body bound (NFR-AR-14); closed schemas (Functional Design BR-RQ-01, BR-SE-01); parameterized SQL (U4 NFR-EHA-13) |
| SECURITY-06 | Compliant | The app role holds `INSERT` and `SELECT` only (NFR-AR-23) |
| SECURITY-08 | Compliant | Unchanged from Functional Design (BR-SP, BR-SE): function- and object-level authorization; deny by default |
| SECURITY-09 | Compliant | No default credentials; generic Problems |
| SECURITY-10 | Compliant | No new dependency (NFR-AR-20) |
| SECURITY-11 | Compliant | S2's throttle (NFR-AR-12); the secrets cap (NFR-AR-06); misuse cases (Functional Design §15). **Accepted residual**: no bound on the number of registrations in M1 (NFR-AR-13, Q5 A) |
| SECURITY-12 | Compliant | No password-class secret: the registration secret carries 256 random bits, so a fast domain-separated hash is the appropriate verifier (NFR-AR-02), and SECURITY-12's adaptive-hashing clause, which addresses guessable passwords, does not apply to it; nothing hard-coded |
| SECURITY-13 | Compliant | Every registration and secret attributed (NFR-AR-17); write-once records (NFR-AR-23) |
| SECURITY-14 | **Not applicable in M1, by the user's decision** | Events named and alert rules defined as files (NFR-AR-18, 19) |
| SECURITY-15 | Compliant | Fail closed on store failure (NFR-AR-17); the lock is transaction-scoped, so it is released on rollback (NFR-AR-07) |

**Security findings**: none blocking.

## 6. Invariant Compliance at NFR Requirements

| Code | Status | Note |
|---|---|---|
| I1 | Covered | The per-environment store; the cap's lock key includes the environment (NFR-AR-07); the backup is per environment (NFR-AR-09) |
| I2, I3, I5, I6, I9, I10 | No change | As in [invariant-coverage-matrix.md](../functional-design/invariant-coverage-matrix.md) |
| I4 | Covered | Durability of the resolution target (NFR-AR-08 to 11); write-once privileges (NFR-AR-23) |
| I7 | Covered | One new code, `secret_limit_reached` (compatible) |
| I8 | Covered | The cap is a security bound, not a tenant quota (NFR-AR-24); no registration quota in core (NFR-AR-13); no new dependency |
| I11 | N/A | Construction is where technology is selected |

**Invariant findings**: none blocking.
