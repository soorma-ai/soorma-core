# Tech Stack Decisions: U5 `agent-registration`

**Unit**: U5 `agent-registration` (soorma-core#8)
**Scope**: U5's selections. U1's toolchain (T-01 to T-16), U2's runtime selections (T-OI-01 to
12), U3's (T-AE-01 to 06), and U4's (T-EHA-01 to 10) apply unchanged
**Dependencies**: **U5 adds none** (NFR-AR-20). The code lands in existing workspaces
(`packages/registry`, `packages/authority`, `packages/env-store`, `packages/perimeter`,
`services/control-gateway`), so the register is unchanged

---

## 1. Decisions

| ID | Selection | Choice | Version | Licence | Kind | Why | Source |
|---|---|---|---|---|---|---|---|
| T-AR-01 | Secret generation | **`node:crypto` `randomBytes`**: 16 bytes for the id, 32 for the secret; base64url via `Buffer` | Node 26.13.0 (U1 T-01) | — | Runtime, built in | The CSPRNG U2 and U4 use (T-OI-04, T-EHA-04) | NFR-AR-01 |
| T-AR-02 | Secret verifier | **SHA-256, unkeyed, domain-separated**, through `node:crypto` `createHash`; compared with `timingSafeEqual` | Node 26.13.0 | — | Runtime, built in | 256 random bits need no slow hash and no key (Q1 A; the user's addition) | NFR-AR-02, 05 |
| T-AR-03 | Cap serialisation | **A PostgreSQL transaction-scoped advisory lock** (`pg_advisory_xact_lock`) keyed on the registration, or an equivalent that needs no `UPDATE` privilege; the exact form at NFR Design | PostgreSQL 18.4 (U4 T-EHA-05) | PostgreSQL Licence | Runtime, built in | A row lock needs `UPDATE` privilege, which the app role does not hold (the user's correction to P-07) | NFR-AR-07 |
| T-AR-04 | Backup and restore | **`pg_dump` and `pg_restore`** (custom format), from the PostgreSQL 18 image U2 pinned by digest | 18.4 | PostgreSQL Licence | Operations tool, in the existing image | No new image or tool; matches the server version | NFR-AR-09, 10 |
| T-AR-05 | Datastore, access, migrations, validation, logging, throttling | **Unchanged**: PostgreSQL 18 per environment, `pg` with plain parameterized SQL through service-kit's `statement()`, `env-store`'s one migration sequence, Ajv 8, NestJS's JSON logger, S2's semaphores | As U4 (T-EHA-05 to 09) | As U4 | Runtime | U5 adds tables and routes, not mechanisms | NFR-AR-08, 12, 14, 18 |

**Lifecycle scripts**: none is added, so the allowlist stays empty (U1 NFR-WC-16).

## 2. Rejected

| Option | Reason |
|---|---|
| A slow password hash (Argon2id, as U2's K) for the secret | The input has 256 random bits; a slow hash adds cost on the unauthenticated bootstrap path and no protection (the user's addition at Functional Design approval) |
| HMAC-SHA-256 under a per-environment key | Q1 B, not chosen: protects only against a store-write attacker, who can already change the agent's standing set and autonomy; it would add a secret and Infrastructure Design |
| A checksum suffix on the value | Q2 B, not chosen: the prefix already serves scanners, and a malformed value costs one indexed read |
| `SELECT … FOR UPDATE` or `FOR SHARE` on the registration | Needs `UPDATE` privilege on the table; D-AR-15 grants the app role none (the user's correction) |
| A per-environment registration quota | Q5 B, not chosen; a tenant quota is commercial (PF §12), and an abuse bound is carried to the first hosted deployment |

## 3. Not Decided Here

| Selection | Decided at |
|---|---|
| Table and column layout, the uniqueness constraint, indexes, the app role's grants; the advisory lock's key derivation; the agent-facts statement; the shared functions for generating, parsing, and verifying a secret; the Human Authority's code shape; the backup command, its role, path, and mode handling; how the restore test obtains an empty store | U5 NFR Design |

## 4. Stages for U5 After This One

| Stage | Decision | Reason |
|---|---|---|
| NFR Design | **Run** | Tables, privileges, the cap's serialisation, the agent-facts statement, the secret functions, the backup procedure |
| Infrastructure Design | **Skipped** | **The verifier is unkeyed (Q1 A), so there is no server-side key, and no new secret to deliver as a mounted file** (the condition the user set at Functional Design approval). U5 adds **no deployable** (its operations run in the existing S2), **no store** (its tables join E's existing store through `env-store`'s migration sequence, run by the existing `{env}-migrate`), **no network**, and **no secret**. The backup path is a git-ignored directory on the host, not infrastructure. *Added at approval*: the backup and restore run as a **one-shot Compose service** (or `run --rm`) on `{env}`'s existing network, mounting only the migrator's existing secret subpath, with the password read from a pgpass file built from `/run/secrets` (NFR-AR-09). It adds no secret, store, or network; its mechanics, and its entry in `compose.yaml` under U4's Compose-model test, are NFR Design's and Code Generation's |
| QA construction enrichment | **Run** after NFR Design | qa-test-cases.md §2.6 |
| Construction Design PR gate | **Run** after enrichment | pr-checkpoint.md Section 5 |
| Code Generation | **Run** after the gate | Always |
