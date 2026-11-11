// SPDX-License-Identifier: FSL-1.1-ALv2
//
// The migration runner (NFR-OI-18; D-ID-OI-02): run by a one-shot migrate
// service, as the migrator role, before its service starts. Moved from
// @soorma/org-identity (U4 NP-EHA-15); each store passes its migrations
// directory and its advisory lock key. Versioned files (`NNNN_name.sql`), applied
// in order, each in one transaction, with its SHA-256 recorded in
// schema_migrations. The whole run holds a session advisory lock, so
// concurrent runs apply each migration once. A changed or missing applied
// migration fails the run: an applied migration is never edited.
import { createHash } from 'node:crypto';
import { readdirSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import pg from 'pg';
import { migrationStatement, SQL } from '../sql.ts';
import { poolConfig, type ConnectionSettings } from './store.ts';

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
  dir: string,
  lockKey: string,
): Promise<string[]> {
  const migrations = readMigrations(dir);
  await client.query(SQL.migrationLock, [lockKey]);
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
    await client.query(SQL.migrationUnlock, [lockKey]).catch(() => undefined);
  }
}

/** A migrate service: connects as the migrator (TLS, verify-full), migrates, and disconnects. */
export async function runMigrations(
  settings: ConnectionSettings,
  dir: string,
  lockKey: string,
): Promise<string[]> {
  const { max: _max, ...config } = poolConfig(settings);
  void _max;
  const client = new pg.Client(config);
  await client.connect();
  try {
    return await migrate(client, dir, lockKey);
  } finally {
    await client.end();
  }
}
