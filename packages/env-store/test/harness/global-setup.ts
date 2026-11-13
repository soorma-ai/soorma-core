// SPDX-License-Identifier: FSL-1.1-ALv2
//
// The environment store's test-database harness, global part (U4 D-CG-EHA-07),
// beside U2's (D-CG-OI-15) on the same test server. Connected as the server's
// superuser (TEST_DATABASE_URL), once per test run:
//   1. creates an environment template database
//   2. runs env-roles.sql against it, and checks the roles' attributes
//   3. sets both environment roles' passwords for this run (and, since U6,
//      the data role's: D-ID-AC-07; since U7, the ingest role's: D-ID-ET-04)
//   4. migrates the template as soorma_env_migrator, with the real runner
// Each test file then clones its own database (database.ts) and connects as
// soorma_env_app, so tests exercise the real privileges (TC-EHA-080). Without
// TEST_DATABASE_URL, nothing is set up, and every database test fails (never
// skips) when it asks for a database.
import { randomBytes } from 'node:crypto';
import type { TestProject } from 'vitest/node';
import { connect } from '../../../org-identity/test/harness/global-setup.ts';
import { migrate } from '../../src/index.ts';
import {
  checkEnvRoleAttributes,
  ENV_APP,
  ENV_DATA,
  ENV_INGEST,
  ENV_MIGRATOR,
  runEnvRolesSql,
} from './roles.ts';

export interface EnvDatabaseInfo {
  /** The superuser URL. */
  url: string;
  template: string;
  appPassword: string;
  migratorPassword: string;
  /** S3's role's password for this run (U6). */
  dataPassword: string;
  /** S4's role's password for this run (U7). */
  ingestPassword: string;
}

declare module 'vitest' {
  export interface ProvidedContext {
    soormaEnvDatabase: EnvDatabaseInfo | null;
  }
}

export default async function setup(project: TestProject): Promise<(() => Promise<void>) | void> {
  const url = process.env.TEST_DATABASE_URL;
  if (!url) {
    project.provide('soormaEnvDatabase', null);
    return;
  }
  const template = `soorma_env_template_${randomBytes(6).toString('hex')}`;
  const appPassword = randomBytes(24).toString('base64url');
  const migratorPassword = randomBytes(24).toString('base64url');
  const dataPassword = randomBytes(24).toString('base64url');
  const ingestPassword = randomBytes(24).toString('base64url');
  const adminDb = new URL(url).pathname.slice(1) || 'postgres';
  const admin = connect(url, adminDb);
  await admin.connect();
  try {
    await admin.query(`CREATE DATABASE ${admin.escapeIdentifier(template)}`);
    const t = connect(url, template);
    await t.connect();
    try {
      await runEnvRolesSql(t, template);
      await checkEnvRoleAttributes(t);
      await t.query(`ALTER ROLE ${ENV_MIGRATOR} PASSWORD ${t.escapeLiteral(migratorPassword)}`);
      await t.query(`ALTER ROLE ${ENV_APP} PASSWORD ${t.escapeLiteral(appPassword)}`);
      await t.query(`ALTER ROLE ${ENV_DATA} PASSWORD ${t.escapeLiteral(dataPassword)}`);
      await t.query(`ALTER ROLE ${ENV_INGEST} PASSWORD ${t.escapeLiteral(ingestPassword)}`);
    } finally {
      await t.end();
    }
    const m = connect(url, template, ENV_MIGRATOR, migratorPassword);
    await m.connect();
    try {
      await migrate(m);
    } finally {
      await m.end();
    }
  } finally {
    await admin.end();
  }
  project.provide('soormaEnvDatabase', {
    url,
    template,
    appPassword,
    migratorPassword,
    dataPassword,
    ingestPassword,
  });
  return async () => {
    const a = connect(url, adminDb);
    await a.connect();
    try {
      await a.query(`DROP DATABASE IF EXISTS ${a.escapeIdentifier(template)} WITH (FORCE)`);
    } finally {
      await a.end();
    }
  };
}
