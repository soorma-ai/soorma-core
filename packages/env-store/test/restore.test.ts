// SPDX-License-Identifier: FSL-1.1-ALv2
//
// TC-AR-058, 060 (U5 NFR-AR-09, 10; NP-AR-09): an environment store's backup
// and restore, on the db-test server, through the server's own pg_dump and
// pg_restore (D-CG-AR-04: TEST_DATABASE_CONTAINER names its container, so the
// versions always match and the host needs no PostgreSQL client).
//
// A seeded store is dumped as the migrator, in custom format, to a temporary
// path; restored as the migrator into an EMPTY database; compared; then the
// migration runner must apply nothing, and the app role's privileges must be
// exactly as granted, so a dump that loses the GRANTs fails. The archive
// validity check (PGDMP, then a full read; D-CG-AR-20) is applied to the dump,
// and to two damaged copies. Both
// databases and the temporary path are removed whatever the outcome.
//
// The migrator's password reaches the tools only through a pgpass file
// written inside the container from stdin: never an argument or a variable.
import { execFileSync, spawnSync } from 'node:child_process';
import { randomBytes } from 'node:crypto';
import {
  closeSync,
  existsSync,
  mkdtempSync,
  openSync,
  readFileSync,
  rmSync,
  truncateSync,
  writeFileSync,
} from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import type pg from 'pg';
import { describe, expect, it } from 'vitest';
import {
  ARCHIVE_MAGIC,
  checkArchive,
  FULL_READ,
  hasArchiveMagic,
} from '../../../deploy/local/scripts/backup-archive.ts';
import { migrate } from '../src/index.ts';
import { testEnvDatabase, type TestEnvDatabase } from './harness/database.ts';
import { ENV_MIGRATOR } from './harness/roles.ts';

function container(): string {
  const c = process.env.TEST_DATABASE_CONTAINER;
  if (!c)
    throw new Error(
      'TEST_DATABASE_CONTAINER is not set. `pnpm db:test` prints it beside TEST_DATABASE_URL; ' +
        "CI sets it to the service's container (D-CG-AR-04).",
    );
  return c;
}

/** A pgpass file inside the container, written from stdin, mode 0600; returns its path. */
function pgpass(c: string, password: string): string {
  const path = `/tmp/soorma-pgpass-${randomBytes(6).toString('hex')}`;
  const escaped = password.replace(/\\/g, '\\\\').replace(/:/g, '\\:');
  execFileSync(
    'docker',
    ['exec', '-i', '-u', 'postgres', c, 'sh', '-c', `umask 077; cat > ${path}`],
    {
      input: `127.0.0.1:5432:*:${ENV_MIGRATOR}:${escaped}\n`,
    },
  );
  return path;
}

const tool = (c: string, pass: string, args: string[]): string[] => [
  'exec',
  '-i',
  '-u',
  'postgres',
  '-e',
  `PGPASSFILE=${pass}`,
  c,
  ...args,
];

/** The full read in the container (D-CG-AR-20), the file on stdin: its exit code. */
const readArchive =
  (c: string) =>
  (path: string): Promise<number> =>
    Promise.resolve(
      spawnSync('docker', ['exec', '-i', '-u', 'postgres', c, ...FULL_READ], {
        input: readFileSync(path),
        stdio: ['pipe', 'ignore', 'ignore'],
      }).status ?? 1,
    );

async function seed(db: TestEnvDatabase): Promise<void> {
  const m = await db.migrator();
  try {
    const env = ['o1', 'p1', 'e'];
    await m.query(
      `INSERT INTO grants (id, organization, project, environment, principal, permissions,
         granted_by_kind, granted_by_principal, granted_by_credential, self_grant, granted_at)
       VALUES ('g1', $1, $2, $3, 'h@example.com', '{agent:register,event:publish}',
         'principal', 'h@example.com', 'c1', true, now())`,
      env,
    );
    await m.query(
      `INSERT INTO credentials (id, organization, project, environment, principal, issued_from,
         issued_at, expires_at, state)
       VALUES ('c1', $1, $2, $3, 'h@example.com', 's1', now(), now() + interval '15 minutes', 'live')`,
      env,
    );
    for (const [agent, standing] of [
      ['a', '{event:publish}'],
      ['b', '{}'],
    ])
      await m.query(
        `INSERT INTO registrations (organization, project, environment, agent, sponsor,
           ceiling_snapshot, standing_permissions, re_broadening_declaration, autonomy_declared,
           registered_at, state)
         VALUES ($1, $2, $3, $4, 'h@example.com', '{agent:register,event:publish}', $5, '{}',
           true, now(), 'registered')`,
        [...env, agent, standing],
      );
    for (const id of ['s1', 's2'])
      await m.query(
        `INSERT INTO registration_secrets (id, organization, project, environment, registration,
           issuer, digest, issued_at, state)
         VALUES ($4, $1, $2, $3, 'a', 'h@example.com', $5, now(), 'active')`,
        [...env, id, randomBytes(32)],
      );
    await m.query(
      `INSERT INTO attribution_records (id, recorded_at, request_id, organization, project,
         environment, operation, actor_kind, principal, credential_kind, credential_id,
         target_kind, target_id)
       VALUES ('r1', now(), 'q1', $1, $2, $3, 'registerAgent', 'human', 'h@example.com',
         'environmentCredential', 'c1', 'registration', 'a')`,
      env,
    );
  } finally {
    await m.end();
  }
}

const TABLES: Record<string, string> = {
  grants: 'id',
  credentials: 'id',
  registrations: 'agent',
  registration_secrets: 'id',
  attribution_records: 'id',
  schema_migrations: '1',
};

async function contents(client: pg.Client): Promise<Record<string, unknown[]>> {
  const out: Record<string, unknown[]> = {};
  for (const [table, order] of Object.entries(TABLES))
    out[table] = (await client.query(`SELECT * FROM ${table} ORDER BY ${order}`)).rows;
  return out;
}

/** TC-EHA-080's and TC-AR-027's privilege checks, against any store. */
async function checkPrivileges(app: pg.Client): Promise<void> {
  const denied = [
    `UPDATE credentials SET principal = 'x'`,
    `DELETE FROM credentials`,
    `UPDATE grants SET principal = 'x'`,
    `DELETE FROM grants`,
    `UPDATE attribution_records SET operation = 'x'`,
    `DELETE FROM attribution_records`,
    `SELECT 1 FROM schema_migrations`,
    `UPDATE registrations SET sponsor = 'x'`,
    `DELETE FROM registrations`,
    `UPDATE registration_secrets SET issuer = 'x'`,
    `DELETE FROM registration_secrets`,
  ];
  for (const statement of denied)
    await expect(app.query(statement), statement).rejects.toMatchObject({ code: '42501' });
  for (const table of ['credentials', 'grants', 'attribution_records', 'registrations'])
    await app.query(`SELECT count(*) FROM ${table}`);
  await app.query(`SELECT count(*) FROM registration_secrets`);
  await app.query(`UPDATE credentials SET state = 'live' WHERE id = 'none'`);
}

describe('TC-AR-058, 060: an environment store survives a backup and restore', () => {
  it('restored into an empty database: equal rows, no migration to apply, the grants kept; the archive checked', async () => {
    const c = container();
    const dir = mkdtempSync(join(tmpdir(), 'soorma-restore-'));
    const file = join(dir, 'e.dump');
    let a: TestEnvDatabase | undefined;
    let b: TestEnvDatabase | undefined;
    let pass: string | undefined;
    try {
      a = await testEnvDatabase();
      await seed(a);
      b = await testEnvDatabase({ empty: true });
      pass = pgpass(c, a.info.migratorPassword);

      // Dump A, as the migrator, custom format, stdout to the file.
      const fd = openSync(file, 'wx', 0o600);
      try {
        execFileSync(
          'docker',
          tool(c, pass, [
            'pg_dump',
            '--format=custom',
            '--no-password',
            '-h',
            '127.0.0.1',
            '-U',
            ENV_MIGRATOR,
            '-d',
            a.name,
          ]),
          { stdio: ['ignore', fd, 'pipe'] },
        );
      } finally {
        closeSync(fd);
      }

      // TC-AR-060: the archive validity check passes on the dump.
      expect(hasArchiveMagic(file)).toBe(true);
      expect(await checkArchive(file, readArchive(c))).toEqual({ ok: true });
      // ...and fails on two damaged copies: diagnostics in the stream, a truncation.
      const prepended = join(dir, 'prepended.dump');
      writeFileSync(
        prepended,
        Buffer.concat([Buffer.from('pg_dump: notice\n'), readFileSync(file)]),
      );
      expect(await checkArchive(prepended, readArchive(c))).toEqual({ ok: false, reason: 'magic' });
      const truncated = join(dir, 'truncated.dump');
      writeFileSync(truncated, readFileSync(file));
      truncateSync(truncated, readFileSync(file).length - 1);
      expect(readFileSync(truncated).subarray(0, 5).equals(ARCHIVE_MAGIC)).toBe(true);
      expect(await checkArchive(truncated, readArchive(c))).toEqual({ ok: false, reason: 'read' });

      // Restore into B, which is empty, as the migrator, in one transaction.
      const restored = spawnSync(
        'docker',
        tool(c, pass, [
          'pg_restore',
          '--exit-on-error',
          '--single-transaction',
          '--no-password',
          '-h',
          '127.0.0.1',
          '-U',
          ENV_MIGRATOR,
          '-d',
          b.name,
        ]),
        { input: readFileSync(file), stdio: ['pipe', 'pipe', 'pipe'] },
      );
      expect(restored.status, restored.stderr.toString()).toBe(0);

      // Equal rows, table by table.
      const sa = await a.superuser();
      const sb = await b.superuser();
      try {
        expect(await contents(sb)).toEqual(await contents(sa));
      } finally {
        await sa.end();
        await sb.end();
      }

      // The migration runner applies nothing: the restored checksums match.
      const mb = await b.migrator();
      try {
        expect(await migrate(mb)).toEqual([]);
      } finally {
        await mb.end();
      }

      // The app role's privileges are exactly as granted.
      const app = await b.app();
      try {
        await checkPrivileges(app);
      } finally {
        await app.end();
      }
    } finally {
      if (pass)
        spawnSync('docker', ['exec', '-u', 'postgres', c, 'rm', '-f', pass], { stdio: 'ignore' });
      await a?.drop();
      await b?.drop();
      rmSync(dir, { recursive: true, force: true });
      expect(existsSync(dir)).toBe(false);
    }
  });
});
