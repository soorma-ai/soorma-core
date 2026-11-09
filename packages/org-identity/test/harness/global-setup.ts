// SPDX-License-Identifier: FSL-1.1-ALv2
//
// The test-database harness, global part (D-CG-OI-15), shared by `pnpm
// db:test` locally and CI's service container. Connected as the server's
// superuser (TEST_DATABASE_URL), once per test run:
//   1. creates a template database
//   2. runs roles.sql against it: the two roles (created only if absent) and
//      the template's database-level grants; then checks the roles' attributes
//   3. sets both roles' passwords for this run (pg's escapeLiteral)
//   4. migrates the template as soorma_org_migrator, with the real runner
// Each test file then clones its own database (database.ts) and connects as
// soorma_org_app. Without TEST_DATABASE_URL, nothing is set up, and every
// database test fails (never skips) when it asks for a database.
//
// One test run at a time per server: each run sets the roles' passwords.
import { randomBytes } from 'node:crypto';
import pg from 'pg';
import type { TestProject } from 'vitest/node';
import { migrate } from '../../src/store/migrations.ts';
import { APP, checkRoleAttributes, MIGRATOR, runRolesSql } from './roles.ts';

export interface DatabaseInfo {
  /** The superuser URL. */
  url: string;
  template: string;
  appPassword: string;
  migratorPassword: string;
}

declare module 'vitest' {
  export interface ProvidedContext {
    soormaDatabase: DatabaseInfo | null;
  }
}

function connect(url: string, database: string, user?: string, password?: string): pg.Client {
  const u = new URL(url);
  return new pg.Client({
    host: u.hostname,
    port: Number(u.port || 5432),
    database,
    user: user ?? decodeURIComponent(u.username),
    password: password ?? decodeURIComponent(u.password),
  });
}

export { connect };

export default async function setup(project: TestProject): Promise<(() => Promise<void>) | void> {
  const url = process.env.TEST_DATABASE_URL;
  if (!url) {
    project.provide('soormaDatabase', null);
    return;
  }
  const template = `soorma_template_${randomBytes(6).toString('hex')}`;
  const appPassword = randomBytes(24).toString('base64url');
  const migratorPassword = randomBytes(24).toString('base64url');

  const admin = connect(url, new URL(url).pathname.slice(1) || 'postgres');
  await admin.connect();
  try {
    await admin.query(`CREATE DATABASE ${admin.escapeIdentifier(template)}`);
    const t = connect(url, template);
    await t.connect();
    try {
      await runRolesSql(t, template);
      await checkRoleAttributes(t);
      await t.query(`ALTER ROLE ${MIGRATOR} PASSWORD ${t.escapeLiteral(migratorPassword)}`);
      await t.query(`ALTER ROLE ${APP} PASSWORD ${t.escapeLiteral(appPassword)}`);
    } finally {
      await t.end();
    }
    const m = connect(url, template, MIGRATOR, migratorPassword);
    await m.connect();
    try {
      await migrate(m);
    } finally {
      await m.end();
    }
  } finally {
    await admin.end();
  }

  project.provide('soormaDatabase', { url, template, appPassword, migratorPassword });

  return async () => {
    const a = connect(url, new URL(url).pathname.slice(1) || 'postgres');
    await a.connect();
    try {
      await a.query(`DROP DATABASE IF EXISTS ${a.escapeIdentifier(template)} WITH (FORCE)`);
    } finally {
      await a.end();
    }
  };
}
