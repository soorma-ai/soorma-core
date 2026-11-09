// SPDX-License-Identifier: FSL-1.1-ALv2
//
// The migration runner (NFR-OI-18; D-ID-OI-02): run by org-migrate, as the
// migrator role, before S1 starts. Versioned files (`NNNN_name.sql`), applied
// in order, each in one transaction, with its SHA-256 recorded in
// schema_migrations. The whole run holds a session advisory lock, so
// concurrent runs apply each migration once. A changed or missing applied
// migration fails the run: an applied migration is never edited.
import { createHash } from 'node:crypto';
import { readdirSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import pg from 'pg';
import { migrationStatement, SQL } from '../sql.ts';

/** The migrations shipped with this package. */
export const MIGRATIONS_DIR = fileURLToPath(new URL('../../migrations/', import.meta.url));

/** The advisory lock key: the first 63 bits of SHA-256("soorma.org.migrate"). */
export const MIGRATION_LOCK_KEY = (
  createHash('sha256').update('soorma.org.migrate').digest().readBigUInt64BE(0) >> 1n
).toString();

const FILE = /^(\d{4})_[a-z0-9_]+\.sql$/;

export class MigrationError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'MigrationError';
  }
}

interface Migration {
  version: string;
  checksum: string;
  text: string;
}

function readMigrations(dir: string): Migration[] {
  return readdirSync(dir)
    .filter((f) => FILE.test(f))
    .sort()
    .map((f) => {
      const text = readFileSync(join(dir, f), 'utf8');
      return {
        version: f.replace(/\.sql$/, ''),
        checksum: createHash('sha256').update(text).digest('hex'),
        text,
      };
    });
}

/** Applies every pending migration; returns the versions applied by this run. */
export async function migrate(
  client: pg.ClientBase,
  dir: string = MIGRATIONS_DIR,
): Promise<string[]> {
  const migrations = readMigrations(dir);
  await client.query(SQL.migrationLock, [MIGRATION_LOCK_KEY]);
  try {
    await client.query(SQL.createMigrationsTable);
    const applied = new Map(
      (await client.query<{ version: string; checksum: string }>(SQL.appliedMigrations)).rows.map(
        (r) => [r.version, r.checksum],
      ),
    );
    for (const [version, checksum] of applied) {
      const file = migrations.find((m) => m.version === version);
      if (!file) throw new MigrationError(`applied migration ${version} has no file`);
      if (file.checksum !== checksum)
        throw new MigrationError(`applied migration ${version} has changed`);
    }
    const done: string[] = [];
    for (const m of migrations) {
      if (applied.has(m.version)) continue;
      await client.query(SQL.begin);
      try {
        await client.query(migrationStatement(m.text));
        await client.query(SQL.recordMigration, [m.version, m.checksum]);
        await client.query(SQL.commit);
      } catch (error) {
        await client.query(SQL.rollback).catch(() => undefined);
        const reason = error instanceof Error ? error.message : 'failed';
        throw new MigrationError(`migration ${m.version} failed: ${reason}`);
      }
      done.push(m.version);
    }
    return done;
  } finally {
    await client.query(SQL.migrationUnlock, [MIGRATION_LOCK_KEY]).catch(() => undefined);
  }
}
