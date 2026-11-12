// SPDX-License-Identifier: FSL-1.1-ALv2
//
// The environment store itself: the app role's privileges (TC-EHA-080), the
// migration runner over the environment's sequence (TC-EHA-068), the CHECK
// constraints that repeat BR-AT-05 (TC-EHA-047, the store half), the first
// grant's partial unique index (TC-EHA-035, the store half), and env-roles.sql
// run concurrently (D-CG-EHA-15).
import { cpSync, mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { MigrationError } from '@soorma/service-kit';
import type pg from 'pg';
import { afterAll, beforeAll, describe, expect, it } from 'vitest';
import { ENV_MIGRATIONS_DIR, migrate } from '../src/index.ts';
import { testEnvDatabase, type TestEnvDatabase } from './harness/database.ts';
import { checkEnvRoleAttributes, runEnvRolesSql } from './harness/roles.ts';

let db: TestEnvDatabase;
beforeAll(async () => {
  db = await testEnvDatabase();
});
afterAll(async () => {
  await db?.drop();
});

async function code(promise: Promise<unknown>): Promise<string | undefined> {
  try {
    await promise;
    return undefined;
  } catch (error) {
    return (error as { code?: string }).code;
  }
}

async function failure(
  promise: Promise<unknown>,
): Promise<{ code?: string; constraint?: string } | undefined> {
  try {
    await promise;
    return undefined;
  } catch (error) {
    return error as { code?: string; constraint?: string };
  }
}

const ENV = ['o1', 'p1', 'e'];
const T0 = '2026-11-11T12:00:00Z';
const T1 = '2026-11-11T12:15:00Z';
let ids = 0;
const id = (): string => `id-${Date.now()}-${ids++}`;

async function liveCredential(app: pg.Client): Promise<string> {
  const credential = id();
  await app.query(
    `INSERT INTO credentials (id, organization, project, environment, principal, issued_from,
       issued_at, expires_at, state) VALUES ($1, $2, $3, $4, 'h@example.com', 'sid', $5, $6, 'live')`,
    [credential, ...ENV, T0, T1],
  );
  return credential;
}

describe('TC-EHA-080: the app role holds only its granted table and column privileges', () => {
  it.each([
    ['UPDATE credentials SET principal', "UPDATE credentials SET principal = 'x' WHERE id = $1"],
    [
      'UPDATE credentials SET issued_from',
      "UPDATE credentials SET issued_from = 'x' WHERE id = $1",
    ],
    [
      'UPDATE credentials SET organization',
      "UPDATE credentials SET organization = 'x' WHERE id = $1",
    ],
    ['DELETE FROM credentials', 'DELETE FROM credentials WHERE id = $1'],
    ['UPDATE grants', "UPDATE grants SET principal = 'x' WHERE id = $1"],
    ['DELETE FROM grants', 'DELETE FROM grants WHERE id = $1'],
    ['UPDATE attribution_records', "UPDATE attribution_records SET operation = 'x' WHERE id = $1"],
    ['DELETE FROM attribution_records', 'DELETE FROM attribution_records WHERE id = $1'],
    ['SELECT schema_migrations', 'SELECT version FROM schema_migrations WHERE version <> $1'],
  ])('refuses %s', async (_name, text) => {
    const app = await db.app();
    try {
      const credential = await liveCredential(app);
      expect(await code(app.query(text, [credential]))).toBe('42501');
    } finally {
      await app.end();
    }
  });

  it('allows ending a live credential: UPDATE of state, ended_at, ended_by, and expires_at', async () => {
    const app = await db.app();
    try {
      const credential = await liveCredential(app);
      const r = await app.query(
        `UPDATE credentials SET state = 'ended', ended_at = $2, ended_by = 'self',
           expires_at = $3 WHERE id = $1 AND state = 'live'`,
        [credential, T0, T1],
      );
      expect(r.rowCount).toBe(1);
    } finally {
      await app.end();
    }
  });
});

describe('TC-EHA-068: environment migrations are locked, checksummed, and run as the migrator', () => {
  it('two concurrent runs on a fresh database apply each migration once', async () => {
    const fresh = await testEnvDatabase({ empty: true });
    try {
      const su = await fresh.superuser();
      await runEnvRolesSql(su, fresh.name);
      await su.end();
      const a = await fresh.migrator();
      const b = await fresh.migrator();
      try {
        const [x, y] = await Promise.all([migrate(a), migrate(b)]);
        expect([...x, ...y].sort()).toEqual([
          '0001_init',
          '0002_registrations',
          '0003_agent_credentials',
          '0004_attribution_envelope_free',
        ]);
      } finally {
        await a.end();
        await b.end();
      }
    } finally {
      await fresh.drop();
    }
  });

  it('a changed, already-applied migration fails the run', async () => {
    const dir = mkdtempSync(join(tmpdir(), 'soorma-env-migrations-'));
    try {
      cpSync(ENV_MIGRATIONS_DIR, dir, { recursive: true });
      writeFileSync(join(dir, '0001_init.sql'), '-- edited\n', { flag: 'a' });
      const m = await db.migrator();
      try {
        await expect(migrate(m, dir)).rejects.toBeInstanceOf(MigrationError);
      } finally {
        await m.end();
      }
    } finally {
      rmSync(dir, { recursive: true, force: true });
    }
  });

  it('env-roles.sql runs twice concurrently, leaving the same roles (D-CG-EHA-15)', async () => {
    const a = await db.superuser();
    const b = await db.superuser();
    try {
      await Promise.all([runEnvRolesSql(a, db.name), runEnvRolesSql(b, db.name)]);
      await checkEnvRoleAttributes(a);
    } finally {
      await a.end();
      await b.end();
    }
  });
});

describe('TC-EHA-047 (the store half): CHECK constraints refuse an inconsistent attribution record', () => {
  const base = {
    id: '',
    recorded_at: T0,
    organization: 'o1',
    project: 'p1',
    environment: 'e',
    operation: 'grantToHuman',
  };
  const insert = async (app: pg.Client, row: Record<string, unknown>) => {
    const full = { ...base, ...row, id: id() };
    const cols = Object.keys(full);
    const values = cols.map((c) => {
      const v = (full as Record<string, unknown>)[c];
      return c === 'chain' || c === 'origin' ? (v === null ? null : JSON.stringify(v)) : v;
    });
    return app.query(
      `INSERT INTO attribution_records (${cols.join(', ')}) VALUES (${cols
        .map((_, i) => `$${i + 1}`)
        .join(', ')})`,
      values,
    );
  };
  const human = {
    actor_kind: 'human',
    principal: 'h@example.com',
    credential_kind: 'environmentCredential',
    credential_id: 'c1',
  };
  const agent = {
    actor_kind: 'agent',
    registration: 'r1',
    instance: 'i1',
    sponsor: 'h@example.com',
  };
  const envelope = {
    chain: [{ agent: 'a' }, { agent: 'b' }],
    origin: { originMode: 'autonomous' },
    rebroadening_load_bearing: false,
  };

  it('accepts a consistent record of each actor kind', async () => {
    const app = await db.app();
    try {
      await insert(app, human);
      await insert(app, { actor_kind: 'configuration' });
      await insert(app, agent);
      await insert(app, { ...agent, ...envelope });
      await insert(app, {
        ...agent,
        ...envelope,
        rebroadening_load_bearing: true,
        rebroadening_hop: 1,
      });
    } finally {
      await app.end();
    }
  });

  it.each([
    ['a human actor with a chain', { ...human, ...envelope }, 'attribution_envelope_agent_only'],
    [
      'a human actor with a registration',
      { ...human, registration: 'r1' },
      'attribution_human_actor',
    ],
    [
      'a human actor without a credential',
      { ...human, credential_id: null },
      'attribution_human_actor',
    ],
    [
      'a configuration actor with a principal',
      { actor_kind: 'configuration', principal: 'h' },
      'attribution_configuration_actor',
    ],
    ['an agent actor without a sponsor', { ...agent, sponsor: null }, 'attribution_agent_actor'],
    [
      'a chain without an origin',
      { ...agent, ...envelope, origin: null },
      'attribution_envelope_all_or_none',
    ],
    [
      'a hop without load-bearing',
      { ...agent, ...envelope, rebroadening_hop: 0 },
      'attribution_hop_when_load_bearing',
    ],
    [
      'a hop equal to the chain length',
      { ...agent, ...envelope, rebroadening_load_bearing: true, rebroadening_hop: 2 },
      'attribution_hop_when_load_bearing',
    ],
    [
      'load-bearing with no hop',
      { ...agent, ...envelope, rebroadening_load_bearing: true },
      'attribution_load_bearing_has_hop',
    ],
    [
      'a chain that is not an array',
      { ...agent, ...envelope, chain: { a: 1 } },
      'attribution_chain_array',
    ],
    ['an unknown actor kind', { actor_kind: 'robot' }, 'attribution_actor_kind'],
  ])('refuses %s', async (_name, row, constraint) => {
    const app = await db.app();
    try {
      const f = await failure(insert(app, row));
      expect(f?.code).toBe('23514');
      expect(f?.constraint).toBe(constraint);
    } finally {
      await app.end();
    }
  });
});

describe('TC-EHA-035 (the store half): at most one configuration grant per principal', () => {
  const grant = (app: pg.Client, kind: 'configuration' | 'principal', principal: string) =>
    app.query(
      `INSERT INTO grants (id, organization, project, environment, principal, permissions,
         granted_by_kind, granted_by_principal, granted_by_credential, self_grant, granted_at)
       VALUES ($1, 'o1', 'p1', 'e', $2, ARRAY['grant:human'], $3, $4, $5, $6, $7)`,
      [
        id(),
        principal,
        kind,
        kind === 'principal' ? 'admin@example.com' : null,
        kind === 'principal' ? 'c1' : null,
        false,
        T0,
      ],
    );

  it('a second configuration grant for one principal is a unique violation; principal grants are not limited', async () => {
    const app = await db.app();
    try {
      const who = `first-${id()}@example.com`;
      await grant(app, 'configuration', who);
      const f = await failure(grant(app, 'configuration', who));
      expect(f?.code).toBe('23505');
      expect(f?.constraint).toBe('grants_one_configuration_grant');
      await grant(app, 'principal', who);
      await grant(app, 'principal', who);
    } finally {
      await app.end();
    }
  });

  it('refuses an inconsistent grant row', async () => {
    const app = await db.app();
    try {
      const f = await failure(
        app.query(
          `INSERT INTO grants (id, organization, project, environment, principal, permissions,
             granted_by_kind, self_grant, granted_at)
           VALUES ($1, 'o1', 'p1', 'e', 'h', ARRAY[]::text[], 'configuration', false, $2)`,
          [id(), T0],
        ),
      );
      expect(f?.code).toBe('23514');
      expect(f?.constraint).toBe('grants_permissions_not_empty');
    } finally {
      await app.end();
    }
  });
});
