// SPDX-License-Identifier: FSL-1.1-ALv2
//
// The org store's migrations (NFR-OI-18; D-ID-OI-02), run by org-migrate. The
// runner moved to @soorma/service-kit (U4 NP-EHA-15); the org store's
// directory and advisory lock key stay here and are passed to it.
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import {
  type ConnectionSettings,
  migrate as runner,
  MigrationError,
  runMigrations as runAll,
} from '@soorma/service-kit';
import type pg from 'pg';

export { MigrationError };

/** The migrations shipped with this package. */
export const MIGRATIONS_DIR = fileURLToPath(new URL('../../migrations/', import.meta.url));

/** The advisory lock key: the first 63 bits of SHA-256("soorma.org.migrate"). */
export const MIGRATION_LOCK_KEY = (
  createHash('sha256').update('soorma.org.migrate').digest().readBigUInt64BE(0) >> 1n
).toString();

/** Applies every pending migration; returns the versions applied by this run. */
export function migrate(client: pg.ClientBase, dir: string = MIGRATIONS_DIR): Promise<string[]> {
  return runner(client, dir, MIGRATION_LOCK_KEY);
}

/** org-migrate: connects as the migrator (TLS, verify-full), migrates, and disconnects. */
export function runMigrations(
  settings: ConnectionSettings,
  dir: string = MIGRATIONS_DIR,
): Promise<string[]> {
  return runAll(settings, dir, MIGRATION_LOCK_KEY);
}
