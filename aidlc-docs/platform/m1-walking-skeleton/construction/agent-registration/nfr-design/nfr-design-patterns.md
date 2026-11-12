# NFR Design Patterns: U5 `agent-registration`

**Unit**: U5 `agent-registration` (soorma-core#8). Control face, environment level
**Decisions from**: the NFR Design plan, Q1 to Q5 and P-01 to P-09, answered
2026-11-11T22:38:59Z (verbatim in `audit.md`), with the user's two corrections to P-09 and
additions to Q3 and Q4. All technology (I11); no specification gap
**Meets**: [../nfr-requirements/nfr-requirements.md](../nfr-requirements/nfr-requirements.md)
NFR-AR-01 to 24. **Components**: [logical-components.md](logical-components.md)
**Builds on**: U4's NFR Design (NP-EHA-06 the store and its transactions, NP-EHA-10 the held set,
NP-EHA-11 identifiers, NP-EHA-12 listeners and events, NP-EHA-14 secret types); U3's NP-04 (the
agent-facts port and cache)

**Changed at approval (2026-11-11, the user's)**: NP-AR-09 (3)'s checksum test and its
normalised-projection design are **dropped** (a custom-format archive's header records its
creation time, so a raw checksum cannot be stable). They are replaced by an **archive validity
check after each backup** (NP-AR-08, NP-AR-09 (3)). The dump stays in custom format. *Step 2 of that
check is a full read, not `--list`: corrected in place at Code Generation (D-CG-AR-20).*

---

## NP-AR-01: The Tables (P-01 to P-03; Q5 A)

**A new migration, `packages/env-store/migrations/0002_registrations.sql`**, in `env-store`'s one
sequence, run by `{env}-migrate` as the migrator role. `0001` is not edited: applied migrations
are checksummed (U2 NFR-OI-18).

**`registrations`**: one row per logical agent in E; never updated or deleted (D-AR-15).

| Rule | Form |
|---|---|
| Identity | **Primary key `(organization, project, environment, agent)`**: the per-environment uniqueness of D-AR-02, and the index the agent-facts statement and the secret's foreign key use |
| Sets | `ceiling_snapshot`, `standing_permissions`, `re_broadening_declaration` as `text[] NOT NULL`, **sorted and de-duplicated by P4** before writing (U4 NP-EHA-10) |
| Bounds | `cardinality(standing_permissions) <= 32`; the same for the declaration |
| **Set invariants (Q5 A)** | `CHECK (standing_permissions <@ ceiling_snapshot)` and `CHECK (re_broadening_declaration <@ standing_permissions)`. **They assume flat-set containment** (PF FR-018's minimal model); a comment beside them says so, and that a migration removes them if Access Policy's model ever makes containment richer (PF FR-019). **P3 still decides** (D-AR-10); the constraints only stop a defect from storing a registration over its ceiling |
| Not in SQL | **The human-only class.** D-AE-03 allows one definition, in `packages/authority`; a SQL copy would be a second |
| State | `CHECK (state = 'registered')`, widened by a migration when a state becomes reachable |
| Privileges | `REVOKE ALL … FROM PUBLIC`; the app role `SELECT, INSERT` only; the migrator role owns the table |

**`registration_secrets`**: one row per issued secret; never updated or deleted in M1.

| Rule | Form |
|---|---|
| Identity | `id` primary key: 128 CSPRNG bits, base64url, 22 characters (U4 NP-EHA-11) |
| Binding | **Foreign key `(organization, project, environment, registration)` → `registrations`**: a secret cannot name a registration of another environment, or none (I1) |
| Verifier | `digest bytea NOT NULL`, `CHECK (octet_length(digest) = 32)` |
| Issuer | `issuer text NOT NULL` (its organization is the row's `organization`) |
| State | `CHECK (state = 'active')` |
| Index | `(organization, project, environment, registration)`, for the cap's count |
| Privileges | The app role `SELECT, INSERT` only |

**Meets**: D-AR-02, 04, 06, 11, 14, 15, 16; NFR-AR-02, 23; I1, I4. **Verified by**:
- the privilege test: `UPDATE` and `DELETE` as the app role fail on both tables;
- a direct insert violating each `CHECK` and the foreign key fails;
- a row under E2's identity in E's store is invisible to every P4 read;
- U2's `sql` check over `packages/registry/src/sql.ts`.

**Test cases** (QA construction enrichment, 2026-11-11): TC-AR-027, TC-AR-070, TC-AR-039, TC-AR-071.

## NP-AR-02: The Registration Secret Module (Q2 A; NFR-AR-01 to 05)

**`packages/registry/src/registration-secret.ts`**, a pure module with no store access, the one
definition S2's issuance and U6's bootstrap import:

| Function | Behaviour |
|---|---|
| `generateRegistrationSecret()` | `id` = 16 bytes and `secret` = 32 bytes from `crypto.randomBytes`, each base64url without padding; returns `{ id, value: SecretText, digest: Buffer }`, `value` = `soorma_rs_{id}.{secret}` |
| `parseRegistrationSecret(value: SecretText)` | Prefix `soorma_rs_`; exactly one `.`; `{id}` decodes to 16 bytes and `{secret}` to 32, **each re-encoding to the same characters** (one encoding per value). Returns `{ id, secretBytes }` or `invalid`, never throwing for a malformed value |
| `digestRegistrationSecret(secretBytes)` | `SHA-256("soorma.registration-secret.v1" ‖ 0x00 ‖ secretBytes)`, 32 bytes |
| `registrationSecretMatches(secretBytes, stored)` | Recompute and `crypto.timingSafeEqual` over two 32-byte buffers; `false` for a stored digest of any other length, without throwing |

**Secret types** (U4 NP-EHA-14): the generated value is a `SecretText` from generation to the
response body; the digest is a `Buffer` never compared with `===` (U2's `compare` check). Neither
is passed to the security log, whose helper takes no secret type.

**Meets**: NFR-AR-01 to 05; D-AR-16; SECURITY-12. **Verified by**: the format test over generated
values; the test vector for the digest; one test per malformation (`parse` returns `invalid`);
a constant-time review check; the `compare` check.

**Test cases** (QA construction enrichment, 2026-11-11): TC-AR-048, TC-AR-049, TC-AR-050, TC-AR-071.

## NP-AR-03: The Cap, Serialised Without `UPDATE` (Q1 A; NFR-AR-06, 07)

Inside `issueRegistrationSecret`'s transaction, after BR-SE-04 has passed outside it:

1. **`SELECT pg_advisory_xact_lock($1)`**, where `$1` is the **first 63 bits** (a non-negative
   `bigint`) of `SHA-256("soorma.registration-secrets.v1" ‖ 0x00 ‖ organization ‖ 0x00 ‖ project ‖
   0x00 ‖ environment ‖ 0x00 ‖ agent)`, computed in P4. The label separates it from `env-store`'s
   migration lock key (U4 NP-EHA-06)
2. `SELECT count(*) FROM registration_secrets WHERE` the four columns `AND state = 'active'`
3. Ten or more: **`secret_limit_reached`**, rollback
4. Insert the secret; P7 inserts the attribution record; commit, which releases the lock

The lock is transaction-scoped, so a rollback or a dropped connection releases it (SECURITY-15).
It needs no table privilege. **A hash collision only serialises two registrations needlessly; it
never admits an eleventh secret.** `READ COMMITTED` suffices: the count is read after the lock,
so it sees every committed issuance of the same registration.

**Meets**: NFR-AR-06, 07; D-AR-04. **Verified by**: the concurrency test at the cap (9 active, 5
concurrent issuances: exactly 1 succeeds, 4 `secret_limit_reached`, 10 secrets and 1 new
attribution record); a test that two different registrations issue concurrently without waiting
on each other's lock (distinct keys); the key-derivation vector.

**Test cases** (QA construction enrichment, 2026-11-11): TC-AR-052, TC-AR-053.

## NP-AR-04: The Agent-Facts Statement (P-04; D-AR-19)

P4's `AgentFactsSource.load(environment, agents)`, one statement through `statement()`:

```sql
SELECT agent, autonomy_declared, re_broadening_declaration, standing_permissions
  FROM registrations
 WHERE organization = $1 AND project = $2 AND environment = $3
   AND agent = ANY($4::text[])
```

It reads **neither the snapshot nor the sponsor** (PF §8b: never consulted per request). Arrays
become frozen `ReadonlySet`s; an agent not returned is absent from the map; any error rejects the
call (U3 BR-AU-09). It is the primary key's index.

**Meets**: D-AR-19; NFR-AR-16; L1-13. **Verified by**: a counting test (one statement for 33
agents); an E2 row with the same `agent` not returned for E; the result carries no snapshot or
sponsor; TC-AE-040 re-run at Build and Test.

**Test cases** (QA construction enrichment, 2026-11-11): TC-AR-032, TC-AR-065.

## NP-AR-05: One Read, One Evaluator, in Code (P-05; D-AR-07)

`packages/authority` (P3):

| Export | Form |
|---|---|
| `evaluateHeld({ policy, held, required })` | `policy.contains(held, required)`; `required` non-empty (U4's `RangeError` kept). **The one evaluator** |
| `evaluateHuman(input)` | One `grantedSet` read, then `evaluateHeld`. **Signature and results unchanged** |
| `holdsAnyGrant(input)` | Unchanged |
| `readHumanAuthority({ policy, environment, principal })` | One `grantedSet` read; returns a **frozen object of three closures** over the set, which is never exposed: `allows(required)` = `evaluateHeld`; `exceeding(candidate)` = the candidate's indexes for which `allows({ p })` is false; `snapshot()` = a sorted, frozen copy |
| `checkRegistrationRequest({ policy, standing, declared })` | `{ humanOnly, outsideStanding }` as index lists: `HUMAN_ONLY_PERMISSIONS` membership; `policy.contains(standing, { p })` per declared entry |

S2 imports these and nothing else that computes authority (BR-SP-07).

**Meets**: D-AR-07, 10; BR-HA-01 to 04; NFR-AR-21; I5. **Verified by**: U4's `evaluateHuman` and
`holdsAnyGrant` tests **unchanged and passing**; a counting `GrantSource` (one read per operation);
a dependency test that S2 and P4 import no evaluator but these.

**Test cases** (QA construction enrichment, 2026-11-11): TC-AR-038, TC-AR-031.

## NP-AR-06: Each Operation's Transaction (P-06; D-AR-18, 26)

| Operation | Before the transaction | In one `withTransaction` |
|---|---|---|
| `registerAgent` | Steps 1 to 6; `readHumanAuthority`; `agent:register`; the ceiling; the snapshot | P4 insert registration; P7 insert record |
| `issueRegistrationSecret` | Steps 1 to 6; `readHumanAuthority`; `agent:register`; the registration lookup; sponsor or Admin | NP-AR-03's lock and count; P4 insert secret; P7 insert record |

- **The held-set read runs before the transaction**, as U4's do: the ceiling is judged at the
  moment of that read (PF FR-016), and no M1 operation removes a grant
- **`registration_exists`**: SQLSTATE `23505` **on the registrations primary-key constraint only**
  (matched by constraint name) maps to it; any other error is `unavailable`
- Nothing is written outside a transaction, and a response is sent only after commit

**Meets**: D-AR-18, 26; NFR-AR-17. **Verified by**: a fault injected at the attribution insert
leaves no registration and no secret; two concurrent registrations of one `agent` write one row
and one record; another constraint's violation is not mapped to `registration_exists`.

**Test cases** (QA construction enrichment, 2026-11-11): TC-AR-041, TC-AR-024, TC-AR-072.

## NP-AR-07: Routes, Responses, Events (P-07, P-08)

- Two routes on S2's edge listener (U4 NP-EHA-12), each through U4's throttle, presenter,
  credential, contract-version, and validator pipeline, with the body bound of 16 KiB
- The issuance response sets **`Cache-Control: no-store`**; no other U5 response needs it
- Events through S2's `SecurityLog`: `registration.created`, `registration.refused`,
  `secret.issued`, `secret.refused`, with reasons from a fixed list (BR-RF-AR-03 plus
  `secret_limit_reached`); a human only by E's log pseudonym; `agent` encoded as a value
- **Three alert rules** in `deploy/monitoring/alerts.yaml`, U2's format: bursts of
  `ceiling_exceeded` with `human_only_in_standing`; bursts of `secret_limit_reached`; any
  `registration.refused` with reason `registration_exists` above a rate (probing). Nothing
  evaluates them in M1

*Corrected in place at Code Generation (2026-11-12, Step 22): U2's rule format has no reason
filter (`groupBy` is `none`, `pseudonym`, `environment`, or `code`), so the three rules are
`registration-refused-repeated` and `secret-refused-repeated` (one human's repeated refusals, 5
in 15 minutes: attempted escalation and probing) and `registration-refused-burst` (one refusal
reason, by `code`, 20 in 15 minutes).*

**Meets**: NFR-AR-04, 12, 14, 18, 19. **Verified by**: a header test; event capture per flow,
asserting no value, digest, or principal identifier appears; U2's alert-file format test.

**Test cases** (QA construction enrichment, 2026-11-11): TC-AR-036, TC-AR-066, TC-AR-067.

## NP-AR-08: Backup and Restore (P-09 as corrected; Q3 A as corrected)

**A dedicated secrets subdirectory** (the user's correction): `env.sh` gains

```sh
copy backup 999 "$env-db-migrator-password" stack-ca-cert
```

so `{env}-secrets` holds `backup/` owned by uid 999 (the pinned PostgreSQL image's user), mode
`0400`, directory `0500`. `migrate/` (uid 65532) is unchanged and unreadable by 999.

**Two one-shot services per environment**, `{env}-backup` and `{env}-restore` (for `e` and `e2`),
under **`profiles: [backup]`**, so `stack:up` never starts them:

| Element | Form |
|---|---|
| Image | The PostgreSQL 18 image U2 pinned by digest |
| User | 999 |
| Network | `{env}`'s network only; the store is not published |
| Mounts | **Only the `backup/` subpath** of `{env}-secrets`, read-only, at `/run/secrets`; a `tmpfs` at `/tmp` (`uid=999`, `mode=0700`) for the pgpass file |
| Hardening | U4's anchor: read-only root, `cap_drop: ALL`, `no-new-privileges` |
| Environment | **`PGPASSFILE=/tmp/pgpass` only**; no password in `environment`, `command`, `entrypoint`, or labels |
| Connection | The migrator role to `{env}`'s store, **`sslmode=verify-full`, `sslrootcert=/run/secrets/stack-ca-cert`**, the host the store's certificate names; `--no-password`, so nothing ever prompts |
| Entrypoint | `umask 077`; build `/tmp/pgpass` from `/run/secrets/{env}-db-migrator-password` (escaping `\` and `:` per pgpass rules); then `exec` the tool. Inline in `compose.yaml`, since the service mounts nothing else |
| Backup | `pg_dump --format=custom` to **stdout**; every diagnostic to **stderr**; never `--verbose` into the dump. Then the archive validity check (NP-AR-09 (3): `PGDMP`, then a full read) |
| Restore | First **refuses a database that is not empty** (any relation in the public schema), exiting non-zero; then `pg_restore --exit-on-error --single-transaction` from **stdin** into it |

**The host scripts** (Node, `deploy/local/scripts/`):

| Command | Behaviour |
|---|---|
| `pnpm stack:backup {env}` | Creates `deploy/local/.backups/` with mode `0700` (and resets it if it exists); **opens `{env}-{UTC time}.dump` with flags `wx` and mode `0o600`**, so the file is never readable by others at any instant; runs **`docker compose --profile backup run --rm -T {env}-backup`** (`-T`: no terminal, so the binary dump is not altered), pipes its stdout to the file and its stderr to the console; on a non-zero exit deletes the partial file and fails; then runs **the archive validity check** (`PGDMP` magic; a full read, `pg_restore --file=/dev/null`, exit 0; NP-AR-09 (3), corrected in place, D-CG-AR-20), deleting the file and failing if it does not pass |
| `pnpm stack:restore {env} {file}` | Runs `docker compose --profile backup run --rm -T {env}-restore` **with stdin open** (`run`'s default) and the file streamed to it; fails on a non-zero exit |

`deploy/local/.backups/` is added to `.gitignore` and `.dockerignore`. S2's README *Operations*
section gives both commands, says the dump **contains human identifiers** (sponsors, issuers,
attribution actors), names the git-ignored path and mode `0600`, and says it never goes into the
repository.

**Meets**: NFR-AR-09 and the user's additions; SECURITY-01 (TLS in transit), 06, 09, 12 (no
password in the environment). **Verified by**:
- **the Compose-model test**: each backup and restore service mounts **only `backup/`** of its
  own environment's volume (and the `tmpfs`), has no password (no value from `.secrets/`) in its
  environment, command, or entrypoint, has `PGPASSFILE` as its only variable, is under the
  `backup` profile, and is on its own environment's network only;
- `git check-ignore deploy/local/.backups/x.dump` succeeds;
- the docs test on the README section;
- the mode test on a written dump (`0600`) and its directory (`0700`).

**Test cases** (QA construction enrichment, 2026-11-11): TC-AR-057, TC-AR-056, TC-AR-055.

## NP-AR-09: The Restore Test and the Archive Validity Check (Q4 A, with the user's additions)

**(1) The data round trip, in the `pnpm db:test` harness** (runs in CI's test job):
1. Create an empty temporary database A as the harness's admin; run the migrations into it; seed
   registrations (with snapshots and declarations), secrets, grants, credentials, and attribution
   records
2. Dump A to a **temporary path** (`fs.mkdtemp`), restore into an **empty** temporary database B
3. Compare B with A: every registration attribute, every secret digest, every attribution record
4. **Run the migration runner against B: it applies nothing**, because B's `schema_migrations`
   rows and checksums match the files (the runner refuses a mismatch)
5. **Re-run the app-role privilege test against B** (U4's TC-EHA-080 test and U5's, both
   parameterised by connection): `INSERT` and `SELECT` where granted, `UPDATE` only on U4's
   credential columns, no `DELETE`. **A dump that loses the `GRANT`s fails here**
6. In a `finally`: drop A and B, and delete the temporary path; assert the path no longer exists

**(2) The stack step, in CI's stack job**, after the smoke test: `stack:backup e`; check the file's
mode (`0600`), its directory's (`0700`), and that it is git-ignored; stop the `e` services and
remove `e`'s store volume; start `env-db-e` alone, so its initialisation creates the roles and an
**empty** database; `stack:restore e {file}`; **run `e-migrate` and assert it applies nothing**;
run the privilege test against the restored store; start the rest of `e`; re-run the smoke test's
registration part; delete the file.

**(3) The archive validity check** (the user's, at approval, replacing a checksum test). What it
catches is **a dump damaged in transit**: a terminal altering the stream, or diagnostics written
into it, or a lost tail. After every backup, before reporting success, `stack:backup`:
1. reads the file's first five bytes and requires them to be **`PGDMP`**, the custom-format
   magic;
2. streams the file to **a full read, `pg_restore --file=/dev/null`**, in the backup service's
   image (`docker compose --profile backup run --rm -T --entrypoint pg_restore {env}-backup
   --file=/dev/null`, with no database connection): every block is read and restored to nowhere,
   and it must **exit 0**.

*Corrected in place at Code Generation (2026-11-12, D-CG-AR-20, the user's answer to Q-CG-AR-1):
step 2 was `pg_restore --list`, which **reads only the archive's header and table of contents**:
run on PostgreSQL 18.4, an archive truncated by one byte at the end passed `--list` (exit 0) and
failed the full read (exit 1). The second negative test below is unchanged, and now holds.*

Either failure deletes the file and fails the command. The data's survival is the round trip's
to prove ((1) and (2) above). **Verified by**: both tests above run it on every dump they take;
and two negative tests: a file with a line prepended (diagnostics in the stream) fails the magic
check, and a valid archive truncated by one byte at the end fails the full read.

**Meets**: NFR-AR-10 and the user's additions; I4 (the resolution target survives a restore).

**Test cases** (QA construction enrichment, 2026-11-11): TC-AR-058, TC-AR-059, TC-AR-060.

## NP-AR-10: Identifiers and Time (P-12)

Secret ids as U4's (NP-EHA-11). `registeredAt` and `issuedAt` from the `CLOCK` token (U4
NP-EHA-13). The registration's `agent` is the client's (D-AR-02).

**Test cases** (QA construction enrichment, 2026-11-11): TC-AR-048, TC-AR-069.

---

## Security Compliance at NFR Design

| Rule | Status | Note |
|---|---|---|
| SECURITY-01 | Compliant in transit (the backup connects `verify-full`); **at rest not applicable in M1, by the user's decision** | Digests only in the store (NP-AR-02); the dump protected by mode, path, and git-ignore (NP-AR-08) |
| SECURITY-02, 04, 07 | N/A | No new intermediary, HTML, or network |
| SECURITY-03 | Compliant, except the centralized log service (the user's M1 decision) | NP-AR-07: no secret, digest, or principal identifier logged |
| SECURITY-05 | Compliant | Parameterized statements; closed schemas; body bound |
| SECURITY-06 | Compliant | App role `SELECT, INSERT` on both tables (NP-AR-01); the backup service holds only the migrator's password and the CA, in its own subdirectory (NP-AR-08) |
| SECURITY-08 | Compliant | Unchanged (Functional Design) |
| SECURITY-09 | Compliant | No default credentials; the restore refuses a non-empty database |
| SECURITY-10 | Compliant | No new dependency; the backup uses the pinned image |
| SECURITY-11 | Compliant | The cap (NP-AR-03); the throttle; misuse cases |
| SECURITY-12 | Compliant | No password in any environment variable or argument (NP-AR-08); the secret's verifier (NP-AR-02) |
| SECURITY-13 | Compliant | Write-once rows; checksummed migrations; the restore's migrate step proves the schema unchanged |
| SECURITY-14 | Not applicable in M1 (the user's decision) | Alert rules as files (NP-AR-07) |
| SECURITY-15 | Compliant | Transaction-scoped lock; partial dump deleted on failure; `--exit-on-error --single-transaction` on restore |

**Security findings**: none blocking.

## Invariant Compliance at NFR Design

| Code | Status | Note |
|---|---|---|
| I1 | Covered | Four-column keys and the foreign key (NP-AR-01); the lock key includes the environment (NP-AR-03); the agent-facts statement constrains on E (NP-AR-04); backup services per environment, each mounting only its own environment's subpath (NP-AR-08) |
| I2, I3, I6, I9, I10 | No change | As in [invariant-coverage-matrix.md](../functional-design/invariant-coverage-matrix.md) |
| I4 | Covered | Write-once privileges; the restore round trip (NP-AR-09) |
| I5 | Covered | One evaluator (NP-AR-05); the set `CHECK`s as defence in depth, P3 deciding (NP-AR-01) |
| I7 | Covered | No contract change at this stage |
| I8 | Covered | No new dependency; nothing commercial |
| I11 | N/A | Construction is where technology is selected |

**Invariant findings**: none blocking.
