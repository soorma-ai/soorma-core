// SPDX-License-Identifier: FSL-1.1-ALv2
//
// The environment store's test-database harness, per test file (U4
// D-CG-EHA-07): a database cloned from the migrated environment template,
// env-roles.sql run against it (database-level privileges do not copy from a
// template), and a store connected as soorma_env_app, so tests exercise the
// real privileges (TC-EHA-080).
import { randomBytes } from 'node:crypto';
import type pg from 'pg';
import { inject } from 'vitest';
import type { Store } from '@soorma/service-kit';
import { connect } from '../../../org-identity/test/harness/global-setup.ts';
import { connectEnvStore } from '../../src/index.ts';
import type { EnvDatabaseInfo } from './global-setup.ts';
import { ENV_APP, ENV_DATA, ENV_INGEST, ENV_MIGRATOR, runEnvRolesSql } from './roles.ts';

export interface TestEnvDatabase {
  name: string;
  info: EnvDatabaseInfo;
  /** The environment store, as the app role. */
  store: Store;
  /** The settings the store connected with: for a second runtime over the same store. */
  settings: { host: string; port: number; database: string; user: string; password: string };
  /** A client as the server's superuser, for inspection only. */
  superuser(): Promise<pg.Client>;
  /** A client as the app role, outside the Store, to observe raw errors. */
  app(): Promise<pg.Client>;
  /** A client as the migrator role. */
  migrator(): Promise<pg.Client>;
  /** A client as S3's role, soorma_env_data (U6 D-ID-AC-07). */
  data(): Promise<pg.Client>;
  /** A client as S4's role, soorma_env_ingest (U7 D-ID-ET-04). */
  ingest(): Promise<pg.Client>;
  drop(): Promise<void>;
}

export function envDatabaseInfo(): EnvDatabaseInfo {
  const info = inject('soormaEnvDatabase');
  if (!info)
    throw new Error(
      'TEST_DATABASE_URL is not set. Start the test database with `pnpm db:test`, ' +
        'export the TEST_DATABASE_URL it prints, and run the tests again.',
    );
  return info;
}

async function createDatabase(admin: pg.Client, name: string, template?: string): Promise<void> {
  const statement =
    `CREATE DATABASE ${admin.escapeIdentifier(name)}` +
    (template ? ` TEMPLATE ${admin.escapeIdentifier(template)}` : '');
  for (let attempt = 0; ; attempt++) {
    try {
      await admin.query(statement);
      return;
    } catch (error) {
      // 55006: the template is briefly in use by a concurrent clone.
      if ((error as { code?: string }).code !== '55006' || attempt >= 50) throw error;
      await new Promise((r) => setTimeout(r, 100));
    }
  }
}

/** A fresh environment database; from the migrated template unless `empty`. */
export async function testEnvDatabase(options: { empty?: boolean } = {}): Promise<TestEnvDatabase> {
  const info = envDatabaseInfo();
  const adminDb = new URL(info.url).pathname.slice(1) || 'postgres';
  const name = `soorma_env_test_${randomBytes(6).toString('hex')}`;
  const admin = connect(info.url, adminDb);
  await admin.connect();
  try {
    await createDatabase(admin, name, options.empty ? undefined : info.template);
  } finally {
    await admin.end();
  }
  const su = connect(info.url, name);
  await su.connect();
  try {
    await runEnvRolesSql(su, name);
  } finally {
    await su.end();
  }
  const u = new URL(info.url);
  const settings = {
    host: u.hostname,
    port: Number(u.port || 5432),
    database: name,
    user: ENV_APP,
    password: info.appPassword,
  };
  const store = connectEnvStore(settings);
  const client = async (user?: string, password?: string): Promise<pg.Client> => {
    const c = connect(info.url, name, user, password);
    await c.connect();
    return c;
  };
  return {
    name,
    info,
    store,
    settings,
    superuser: () => client(),
    app: () => client(ENV_APP, info.appPassword),
    migrator: () => client(ENV_MIGRATOR, info.migratorPassword),
    data: () => client(ENV_DATA, info.dataPassword),
    ingest: () => client(ENV_INGEST, info.ingestPassword),
    async drop() {
      await store.close();
      const a = connect(info.url, adminDb);
      await a.connect();
      try {
        await a.query(`DROP DATABASE IF EXISTS ${a.escapeIdentifier(name)} WITH (FORCE)`);
      } finally {
        await a.end();
      }
    },
  };
}
