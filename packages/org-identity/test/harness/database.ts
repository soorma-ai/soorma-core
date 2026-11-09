// SPDX-License-Identifier: FSL-1.1-ALv2
//
// The test-database harness, per test file (D-CG-OI-15): a database cloned
// from the migrated template, roles.sql run against it (database-level
// privileges do not copy from a template), and a Store connected as the app
// role, so tests exercise the real privileges (TC-OI-022, 051).
import { randomBytes } from 'node:crypto';
import pg from 'pg';
import { inject } from 'vitest';
import { Store } from '../../src/store/store.ts';
import { connect, type DatabaseInfo } from './global-setup.ts';
import { APP, MIGRATOR, runRolesSql } from './roles.ts';

export interface TestDatabase {
  name: string;
  info: DatabaseInfo;
  /** The store, as the app role. */
  store: Store;
  /** A client as the server's superuser, for inspection only. */
  superuser(): Promise<pg.Client>;
  /** A client as the app role, outside the Store, to observe raw errors. */
  app(): Promise<pg.Client>;
  /** A client as the migrator role. */
  migrator(): Promise<pg.Client>;
  drop(): Promise<void>;
}

export function databaseInfo(): DatabaseInfo {
  const info = inject('soormaDatabase');
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

/** A fresh database; from the migrated template unless `empty`. */
export async function testDatabase(options: { empty?: boolean } = {}): Promise<TestDatabase> {
  const info = databaseInfo();
  const adminDb = new URL(info.url).pathname.slice(1) || 'postgres';
  const name = `soorma_test_${randomBytes(6).toString('hex')}`;
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
    await runRolesSql(su, name);
  } finally {
    await su.end();
  }
  const u = new URL(info.url);
  const store = Store.connect({
    host: u.hostname,
    port: Number(u.port || 5432),
    database: name,
    user: APP,
    password: info.appPassword,
  });
  const client = async (user?: string, password?: string): Promise<pg.Client> => {
    const c = connect(info.url, name, user, password);
    await c.connect();
    return c;
  };
  return {
    name,
    info,
    store,
    superuser: () => client(),
    app: () => client(APP, info.appPassword),
    migrator: () => client(MIGRATOR, info.migratorPassword),
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
