// SPDX-License-Identifier: FSL-1.1-ALv2
//
// @soorma/env-store: an environment's store (U4 NP-EHA-06; Q4 A). PostgreSQL
// 18, one instance per environment. It owns:
//   - the one migration sequence (migrations/NNNN_*.sql), run by
//     {env}-migrate through service-kit's runner, as the migrator role, under
//     the environment's own advisory lock
//   - the pool, as the app role, TLS verify-full
//   - withTransaction: one operation's writes across P4, P5, and P7 commit or
//     roll back together (D-EHA-17), each module running its own statements
//     over the Tx handle passed in
// Every table carries its environment as three columns, and every statement
// constrains on them (D-EHA-29).
import { createHash, randomBytes } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import type { EnvironmentRef } from '@soorma/policy-decision-seam';
import {
  migrate as runner,
  runMigrations as runAll,
  Store,
  type ConnectionSettings,
  type Queryable,
} from '@soorma/service-kit';
import type pg from 'pg';

export { SQL } from './sql.ts';

/** The environment store's migrations, shipped with this package. */
export const ENV_MIGRATIONS_DIR = fileURLToPath(new URL('../migrations/', import.meta.url));

/** The advisory lock key: the first 63 bits of SHA-256("soorma.env.migrate"). */
export const ENV_MIGRATION_LOCK_KEY = (
  createHash('sha256').update('soorma.env.migrate').digest().readBigUInt64BE(0) >> 1n
).toString();

/** A store's handle inside one transaction: what P4, P5, and P7 write through. */
export type Tx = Queryable;

/** Opens an environment store's pool as the app role (errors name it `env`). */
export function connectEnvStore(settings: ConnectionSettings): Store {
  return Store.connect(settings, { name: 'env' });
}

/** Runs `work` in one transaction: it commits only if `work` returns. */
export function withTransaction<T>(store: Store, work: (tx: Tx) => Promise<T>): Promise<T> {
  return store.transaction(work);
}

/** Applies every pending migration; returns the versions applied by this run. */
export function migrate(
  client: pg.ClientBase,
  dir: string = ENV_MIGRATIONS_DIR,
): Promise<string[]> {
  return runner(client, dir, ENV_MIGRATION_LOCK_KEY);
}

/** {env}-migrate: connects as the migrator (TLS, verify-full), migrates, and disconnects. */
export function runMigrations(
  settings: ConnectionSettings,
  dir: string = ENV_MIGRATIONS_DIR,
): Promise<string[]> {
  return runAll(settings, dir, ENV_MIGRATION_LOCK_KEY);
}

/** An environment's three columns, as statement parameters, in table order. */
export function environmentParams(environment: EnvironmentRef): [string, string, string] {
  return [environment.organization, environment.project, environment.environment];
}

/**
 * A record id or token id (NP-EHA-11; D-EHA-30): 128 random bits from the
 * CSPRNG, base64url without padding (22 characters). Each is a primary key or
 * unique, so a collision is refused by the store, never an overwrite.
 */
export function newRecordId(): string {
  return randomBytes(16).toString('base64url');
}
