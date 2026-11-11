<!-- SPDX-License-Identifier: FSL-1.1-ALv2 -->

# `@soorma/env-store`

An environment's store: PostgreSQL 18, **one instance per environment**, holding that
environment's credentials, grants, and attribution records. It owns:

- **the one migration sequence** (`migrations/NNNN_*.sql`), applied by `{env}-migrate` as the
  migrator role, under the advisory lock `ENV_MIGRATION_LOCK_KEY` (the first 63 bits of
  SHA-256 of `soorma.env.migrate`). Later units add their tables to this sequence;
- **the pool**, `connectEnvStore(settings)`, as the app role, over TLS with full verification;
- **`withTransaction(store, work)`**: one operation's writes across
  [`registry`](../registry/README.md), [`credentials`](../credentials/README.md), and
  [`attribution`](../attribution/README.md) commit or roll back together. Each package runs its
  own statements over the `Tx` handle it is given.

## Privileges are part of the migrations

The app role holds only what each operation needs, granted in the migration that creates the
table:

| Table                 | App role                                                                           |
| --------------------- | ---------------------------------------------------------------------------------- |
| `credentials`         | `SELECT`, `INSERT`; `UPDATE` of `expires_at`, `state`, `ended_at`, `ended_by` only |
| `grants`              | `SELECT`, `INSERT` (a grant is never changed or deleted)                           |
| `attribution_records` | `SELECT`, `INSERT`                                                                 |

Every table carries its environment as three columns (organization, project, environment), and
every statement constrains on them. The store's `CHECK` constraints refuse an inconsistent
attribution record a second time, after the writer's own check.

The role and database names are the same in every environment (`soorma_env`,
`soorma_env_migrator`, `soorma_env_app`); the stores are separate instances.

## Tests

`pnpm db:test` starts a throwaway PostgreSQL and prints `TEST_DATABASE_URL`. This package's test
harness builds a migrated template database on that server once per run, with the real runner
and roles; each test file clones its own database and connects as `soorma_env_app`, so tests
exercise the real privileges. Without `TEST_DATABASE_URL`, the database tests fail rather than
skip.
