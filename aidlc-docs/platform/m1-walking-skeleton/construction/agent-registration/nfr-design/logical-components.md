# Logical Components: U5 `agent-registration`

**Unit**: U5 `agent-registration` (soorma-core#8). Control face, environment level
**Patterns**: [nfr-design-patterns.md](nfr-design-patterns.md) (NP-AR-01 to 10)
**Builds on**: U4's logical components (`construction/env-human-access/nfr-design/logical-components.md`:
S2's process and listeners, the packages, the environment store, its roles and migration
sequence). This document lists only what U5 adds or changes

**No new deployable, package, store, network, or secret.** Two one-shot operations services per
environment are added to `compose.yaml` under a profile (§5); they use an existing secret.

---

## 1. S2 `control-gateway`: Two Routes

| Route | Operation | Scheme | Pipeline (U4's, unchanged) | Handler |
|---|---|---|---|---|
| `POST /registrations` | `registerAgent` | `environmentCredential` | throttle slot; body bound; presenter; credential (O1 to O4); contract version; validator | `checkRegistrationRequest` (P3); `readHumanAuthority` (P3); P4 + P7 in one transaction (NP-AR-06) |
| `POST /registration-secrets` | `issueRegistrationSecret` | `environmentCredential` | as above | `readHumanAuthority`; P4 lookup; sponsor or Admin; NP-AR-03 in one transaction; `Cache-Control: no-store` |

No new listener, configuration item, or start-up step. S2's image changes only because its
workspace dependencies' code changes; **no new workspace package joins its Dockerfile** (the
gate still builds the image for every group that touches them).

## 2. Packages

| Package | Change | Owner of |
|---|---|---|
| `packages/authority` (P3) | `evaluateHeld` extracted; `evaluateHuman` over it (unchanged signature); `readHumanAuthority`; `checkRegistrationRequest` (NP-AR-05) | Every test of a human's set; the human-only class |
| `packages/registry` (P4) | Registration and secret writes and reads; the agent-facts source; **`src/registration-secret.ts`** (NP-AR-02); the cap's lock key (NP-AR-03); SQL in `src/sql.ts` | The two tables' statements; the secret's format |
| `packages/env-store` | `migrations/0002_registrations.sql` (NP-AR-01) | The migration sequence |
| `packages/perimeter` (P1) | Six codes in the Problem table | Problem emission |
| `packages/attribution` (P7) | None (called with target kind `registration`) | — |
| `contract/` | Two operations; six codes; `errors.md` text; `CHANGELOG.md` | The published contract |
| `services/control-gateway` (S2) | Two routes; README *Operations*: backup and restore | — |

**Dependency direction** (unchanged, checked by U4's dependency test): S2 → P3, P4, P7, P1,
`env-store`; P4 → `env-store`, `service-kit`, the policy-decision seam; P3 → no store package.
**Nothing in S2's graph links `org-identity`.**

## 3. The Environment Store: New Tables

Migration `0002_registrations.sql`, as the migrator role. Every table carries `organization`,
`project`, `environment` (`text NOT NULL`), and every statement constrains on them (D-EHA-29).

### `registrations`

| Column | Type | Rule |
|---|---|---|
| `organization`, `project`, `environment` | `text NOT NULL` | E |
| `agent` | `text NOT NULL` | Client-chosen (D-AR-02) |
| `sponsor` | `text NOT NULL` | The presenter's principal |
| `ceiling_snapshot` | `text[] NOT NULL` | Sorted, de-duplicated |
| `standing_permissions` | `text[] NOT NULL` | Sorted, de-duplicated; `cardinality <= 32`; **`<@ ceiling_snapshot`** |
| `re_broadening_declaration` | `text[] NOT NULL` | Sorted, de-duplicated; `cardinality <= 32`; **`<@ standing_permissions`** |
| `autonomy_declared` | `boolean NOT NULL` | |
| `registered_at` | `timestamptz NOT NULL` | |
| `state` | `text NOT NULL` | `CHECK (state = 'registered')` |

- **Primary key** `(organization, project, environment, agent)`, named so that NP-AR-06 maps
  only its violation to `registration_exists`
- The `<@` constraints carry a comment: flat-set containment, PF FR-018; a migration removes them
  if containment becomes richer (PF FR-019)
- **App role**: `SELECT`, `INSERT`. No `UPDATE` or `DELETE`

### `registration_secrets`

| Column | Type | Rule |
|---|---|---|
| `id` | `text` PK | 22 base64url characters (U4 NP-EHA-11) |
| `organization`, `project`, `environment` | `text NOT NULL` | E |
| `registration` | `text NOT NULL` | **Foreign key** with the three columns → `registrations` |
| `issuer` | `text NOT NULL` | The presenter's principal |
| `digest` | `bytea NOT NULL` | `CHECK (octet_length(digest) = 32)` |
| `issued_at` | `timestamptz NOT NULL` | |
| `state` | `text NOT NULL` | `CHECK (state = 'active')` |

- **Index** `registration_secrets_by_registration` on `(organization, project, environment,
  registration)`
- **App role**: `SELECT`, `INSERT`. No `UPDATE` or `DELETE`

### `attribution_records`

Unchanged. U5's rows: operation `registerAgent` or `issueRegistrationSecret`; human actor; target
kind `registration`, target id the `agent`. Its columns are unconstrained text for target kind
and operation, so no migration change is needed.

## 4. Configuration

None new. E's identity, the store's connection, and the pseudonym key are U4's.

## 5. Backup and Restore (NP-AR-08)

| Component | Where | Change |
|---|---|---|
| `backup/` subdirectory | `{env}-secrets` volume, by `deploy/local/secrets-init/env.sh` | `copy backup 999 "$env-db-migrator-password" stack-ca-cert` |
| `{env}-backup`, `{env}-restore` | `deploy/local/compose.yaml`, written out per environment (U4's rule: every name literal) | `profiles: [backup]`; the pinned PostgreSQL image; user 999; `{env}`'s network only; **only `backup/`** mounted read-only at `/run/secrets`; a `tmpfs` at `/tmp`; U4's hardening anchor; `PGPASSFILE` the only variable; `verify-full` with the stack CA |
| `stack:backup`, `stack:restore` | `deploy/local/scripts/`, `package.json` | Host scripts: `run --rm -T`; the file opened `wx`, `0o600`, in a `0700` directory; the archive validity check after each backup (`PGDMP`; a full read, `pg_restore --file=/dev/null`, exit 0; D-CG-AR-20, corrected in place); stdin streamed to restore |
| `deploy/local/.backups/` | `.gitignore`, `.dockerignore` | Ignored |
| S2's README *Operations* | `services/control-gateway/README.md` | The commands; the dump holds human identifiers; the path and mode; never in the repository |

**The Compose-model test** (U4's, `deploy/test/`) extends to assert, for each of the four
services: the profile; its own environment's network only; mounts only `backup/` of its own
environment's volume plus the `tmpfs`; no secret value, and no variable but `PGPASSFILE`, in its
environment, command, or entrypoint.

## 6. Test Doubles and Harness

| Double or harness | Use |
|---|---|
| A counting `GrantSource` | One held-set read per operation (NFR-AR-21) |
| A counting agent-facts statement | One statement per call (NFR-AR-16) |
| A fault-injecting `Tx` | Rollback when the attribution insert fails (NFR-AR-17) |
| `pnpm db:test`'s server | The concurrency tests (the cap; one `agent`), the privilege test, and the restore round trip with its temporary databases and path (NP-AR-09) |
| CI's stack job | The backup and restore step (NP-AR-09 (2)) |

## 7. Forward Obligations

| To | Item |
|---|---|
| **Code Generation (U5)** | Everything in §1 to §6; the `evaluateHuman` refactor with **U4's tests unchanged** (the user's standing rule); the gate builds S2's image for every group touching its dependencies, and runs the local stack for groups changing its runtime, `compose.yaml`, or `env.sh`; NP-AR-09 (3)'s archive validity check after each backup (a full read, D-CG-AR-20), with its two negative tests |
| **U6 (soorma-core#9)** | Import the secret's format from **`packages/registry`** (`parseRegistrationSecret`, `registrationSecretMatches`), never a copy. **P6's agent half must not make S3 link `@soorma/org-identity`**: today `packages/identity-resolution` depends on it (its human half), so the agent half lives apart from the human half, or the package is split. Read the registration and secret through P4's reads (four-column keys). Posted on #9 when this stage is approved |
| **Build and Test** | The p95 of both operations on the stack (NFR-AR-15); TC-AE-040 re-run with P4's source; the backup and restore step's result; the residuals (NFR-AR-11, 13) |
