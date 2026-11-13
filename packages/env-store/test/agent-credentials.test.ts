// SPDX-License-Identifier: FSL-1.1-ALv2
//
// U6's store (NFR Design NP-AC-02 to 07; Infrastructure Design D-ID-AC-07):
// migrations 0003 and 0004, S3's role soorma_env_data, and the statements S3
// runs. The privilege tests run **the real statement objects** (D-CG-AC-03;
// the user's addition at Infrastructure Design approval): P8's from
// packages/abuse-bound, and S3's from packages/credentials, registry,
// agent-identity, attribution, so a grant that fits no statement, or a
// statement no grant fits, fails here. U4's TC-EHA-080 cases are unchanged.
import { createHash, randomBytes, randomUUID } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import type pg from 'pg';
import { afterAll, beforeAll, describe, expect, it } from 'vitest';
import { SQL as P8 } from '../../abuse-bound/src/sql.ts';
import { SQL as P6 } from '../../agent-identity/src/sql.ts';
import { SQL as P7 } from '../../attribution/src/sql.ts';
import { SQL as P5 } from '../../credentials/src/sql.ts';
import { SQL as P4 } from '../../registry/src/sql.ts';
import { checkRoleAttributes } from '../../org-identity/test/harness/roles.ts';
import { ENV_MIGRATIONS_DIR } from '../src/index.ts';
import { testEnvDatabase, type TestEnvDatabase } from './harness/database.ts';
import { ENV_DATA } from './harness/roles.ts';
import { seedAgentRevocation, seedCredentialRevocation } from './harness/seed.ts';

const E = ['o1', 'p1', 'e'] as const;
const E2 = ['o1', 'p1', 'e2'] as const;
const T0 = new Date('2026-11-12T08:00:00Z');
const at = (s: number): Date => new Date(T0.getTime() + s * 1000);
const id = (): string => randomBytes(16).toString('base64url');

let db: TestEnvDatabase;
let owner: pg.Client;
let data: pg.Client;
let app: pg.Client;

/** A registration and one active secret in an environment, written as the owner. */
async function registered(env: readonly string[], agent: string): Promise<{ secret: string }> {
  await owner.query(
    `INSERT INTO registrations (organization, project, environment, agent, sponsor,
       ceiling_snapshot, standing_permissions, re_broadening_declaration, autonomy_declared,
       registered_at, state)
     VALUES ($1, $2, $3, $4, 'h@example.com', '{event:publish}', '{event:publish}', '{}', true,
       $5, 'registered')`,
    [...env, agent, T0],
  );
  const secret = id();
  await owner.query(
    `INSERT INTO registration_secrets (id, organization, project, environment, registration,
       issuer, digest, issued_at, state)
     VALUES ($1, $2, $3, $4, $5, 'h@example.com', $6, $7, 'active')`,
    [secret, ...env, agent, randomBytes(32), T0],
  );
  return { secret };
}

/** A credential row, written as S3's role through the real insert. */
async function credential(env: readonly string[], agent: string, secret: string): Promise<string> {
  const cid = id();
  await data.query(P5.insertAgentCredential, [
    cid,
    ...env,
    agent,
    'i-1',
    secret,
    T0,
    at(86_400),
    at(900),
  ]);
  return cid;
}

const denied = async (client: pg.Client, text: string, params: unknown[] = []): Promise<void> => {
  await expect(client.query(text, params), text).rejects.toMatchObject({ code: '42501' });
};

beforeAll(async () => {
  db = await testEnvDatabase();
  owner = await db.migrator();
  data = await db.data();
  app = await db.app();
});
afterAll(async () => {
  await Promise.all([owner?.end(), data?.end(), app?.end()]);
  await db?.drop();
});

describe('TC-AC-076: migrations 0003 and 0004 apply after 0001 and 0002, which are unchanged', () => {
  it('the store has applied all four, in order', async () => {
    const su = await db.superuser();
    try {
      const { rows } = await su.query<{ version: string }>(
        'SELECT version FROM schema_migrations ORDER BY version',
      );
      expect(rows.map((r) => r.version)).toEqual([
        '0001_init',
        '0002_registrations',
        '0003_agent_credentials',
        '0004_attribution_envelope_free',
        '0005_attribution_envelope_bearing',
        '0006_event_ingest_role',
      ]);
    } finally {
      await su.end();
    }
  });

  it('0001 and 0002 are byte-identical to the files U4 and U5 merged', () => {
    const sha = (f: string): string =>
      createHash('sha256')
        .update(readFileSync(join(ENV_MIGRATIONS_DIR, f)))
        .digest('hex');
    // The files as merged to main by soorma-core#19 (U4) and #21 (U5).
    expect(sha('0001_init.sql')).toBe(
      'cad58262847f87921ce4f0f8445b16e8c352897efbd91a93fb451b5110711300',
    );
    expect(sha('0002_registrations.sql')).toBe(
      'bc846fa43d2130b649f8929a77f68d99f2a5daaf7d846094bbfd7e989c16f34a',
    );
  });
});

describe("TC-AC-079: S2's role has nothing on U6's tables", () => {
  // Each table, with one column to try updating and inserting.
  const tables: [string, string][] = [
    ['agent_credentials', 'organization'],
    ['credential_revocations', 'organization'],
    ['agent_revocations', 'organization'],
    ['attempt_slots', 'consecutive'],
    ['failed_bootstrap_attempts', 'organization'],
  ];
  it.each(tables)('every statement on %s fails as soorma_env_app', async (table, column) => {
    await denied(app, `SELECT 1 FROM ${table}`);
    await denied(app, `INSERT INTO ${table} (${column}) VALUES (DEFAULT)`);
    await denied(app, `UPDATE ${table} SET ${column} = ${column}`);
    await denied(app, `DELETE FROM ${table}`);
  });
});

describe('TC-AC-080: S3’s role runs exactly its statements, and nothing else', () => {
  it('its attributes are U4’s (no superuser, no create, no inherit, no replication, no bypass)', async () => {
    const su = await db.superuser();
    try {
      await checkRoleAttributes(su, [ENV_DATA]);
    } finally {
      await su.end();
    }
  });

  it("P8's real statements succeed as soorma_env_data: admission, the slot's state, a failure with its backoff, a success", async () => {
    const slot = 1000 + Math.floor(Math.random() * 1000);
    const first = randomUUID();
    const now = T0.getTime();
    // Admission: INSERT … ON CONFLICT DO UPDATE … RETURNING, first as an insert.
    expect(await data.query(P8.admit, [slot, first, now, 60_000, 60])).toMatchObject({
      rowCount: 1,
    });
    // A failure, with backoff from the 1st: the UPDATE that sets next_allowed_at.
    await data.query(P8.settleFailure, [slot, now, 1, 60]);
    const state = await data.query<{ next_allowed_ms: string | null }>(P8.slotState, [slot]);
    expect(Number(state.rows[0]!.next_allowed_ms)).toBeGreaterThan(now);
    // Admission again, now through the conflict update, refused by the backoff.
    expect(await data.query(P8.admit, [slot, randomUUID(), now, 60_000, 60])).toMatchObject({
      rowCount: 0,
    });
    // Past the backoff, the conflict update admits; a success removes its entry.
    const second = randomUUID();
    expect(await data.query(P8.admit, [slot, second, now + 2_000, 60_000, 60])).toMatchObject({
      rowCount: 1,
    });
    await data.query(P8.settleSuccess, [slot, second]);
  });

  it("S3's real statements succeed as soorma_env_data: bootstrap's reads and writes, renewal, the revocation reads", async () => {
    const agent = `a-${id()}`;
    const { secret } = await registered(E, agent);
    // The agent half's one read, and the registration's state and sponsor.
    const found = await data.query(P6.secretForBootstrap, [...E, agent, secret]);
    expect(found.rows[0]).toMatchObject({
      agent_exists: true,
      registration: agent,
      state: 'active',
    });
    const reg = await data.query(P4.registrationForBootstrap, [...E, agent]);
    expect(reg.rows[0]).toEqual({ state: 'registered', sponsor: 'h@example.com' });
    // Revocation at bootstrap (no cid yet), the credential, and its attribution.
    const before = await data.query(P5.revoked, [...E, null, agent]);
    expect(before.rows[0]).toEqual({ credential_revoked: false, agent_revoked: false });
    const cid = await credential(E, agent, secret);
    await data.query(P7.insertRecord, [
      id(),
      T0,
      'r1',
      ...E,
      'exchangeBootstrap',
      'agent',
      null,
      null,
      null,
      agent,
      'i-1',
      'h@example.com',
      'agentCredential',
      cid,
      false,
      null,
      null,
      null,
      null,
    ]);
    // Renewal: the record, both granularities, the UPDATE (expires_at) with RETURNING.
    const rec = await data.query(P5.agentCredentialById, [cid, ...E]);
    expect(rec.rows[0]).toMatchObject({ agent, instance: 'i-1', secret });
    const both = await data.query(P5.revoked, [...E, cid, agent]);
    expect(both.rows[0]).toEqual({ credential_revoked: false, agent_revoked: false });
    const renewed = await data.query(P5.renewAgentCredential, [cid, ...E, agent, 'i-1', at(1500)]);
    expect(renewed.rowCount).toBe(1);
    // The failed-attempt batch insert, joined to registrations.
    await data.query(P8.insertFailedBootstrapAttempts, [
      ['o1'],
      ['p1'],
      ['e'],
      [agent],
      [T0.toISOString()],
      [false],
      ['secret_mismatch'],
    ]);
  });

  it('each forbidden statement fails with permission denied', async () => {
    for (const text of [
      'SELECT 1 FROM grants',
      'SELECT 1 FROM credentials',
      'SELECT 1 FROM schema_migrations',
      "INSERT INTO registrations (organization) VALUES ('x')",
      "UPDATE registrations SET sponsor = 'x'",
      "UPDATE registration_secrets SET state = 'active'",
      "INSERT INTO credential_revocations (organization) VALUES ('x')",
      "INSERT INTO agent_revocations (organization) VALUES ('x')",
      'UPDATE credential_revocations SET revoked_at = now()',
      'UPDATE agent_revocations SET revoked_at = now()',
      "UPDATE agent_credentials SET agent = 'x'",
      "UPDATE agent_credentials SET instance = 'x'",
      'UPDATE agent_credentials SET lineage_ends_at = now()',
      'UPDATE attempt_slots SET slot = 1',
      'SELECT 1 FROM failed_bootstrap_attempts',
      'UPDATE failed_bootstrap_attempts SET at = now()',
      'SELECT 1 FROM attribution_records',
      'UPDATE attribution_records SET operation = operation',
      'DELETE FROM agent_credentials',
      'DELETE FROM attempt_slots',
      'DELETE FROM failed_bootstrap_attempts',
      'DELETE FROM attribution_records',
      'DELETE FROM credential_revocations',
      'DELETE FROM agent_revocations',
      'DELETE FROM registrations',
    ])
      await denied(data, text);
  });
});

describe("TC-AC-077: agent_credentials' constraints", () => {
  it('refuses an expiry past the lineage end, another environment’s registration, and an unknown secret', async () => {
    const agent = `a-${id()}`;
    const { secret } = await registered(E2, agent);
    const insert = (env: readonly string[], sec: string, expires: Date) =>
      owner.query(P5.insertAgentCredential, [
        id(),
        ...env,
        agent,
        'i-1',
        sec,
        T0,
        at(86_400),
        expires,
      ]);
    await expect(insert(E2, secret, at(86_401))).rejects.toMatchObject({ code: '23514' });
    await expect(insert(E, secret, at(900))).rejects.toMatchObject({ code: '23503' });
    await expect(insert(E2, id(), at(900))).rejects.toMatchObject({ code: '23503' });
  });
});

describe('TC-AC-078: revocation names targets in its own environment, and the direct read sees both granularities', () => {
  it('refuses an unknown credential, and another environment’s agent', async () => {
    const agent = `a-${id()}`;
    await registered(E2, agent);
    await expect(seedCredentialRevocation(owner, E, id(), T0)).rejects.toMatchObject({
      code: '23503',
    });
    await expect(seedAgentRevocation(owner, E, agent, T0)).rejects.toMatchObject({
      code: '23503',
    });
  });

  it('answers each granularity on its own: a revoked credential, a revoked agent, both, neither', async () => {
    const agent = `a-${id()}`;
    const { secret } = await registered(E, agent);
    const c1 = await credential(E, agent, secret);
    const c2 = await credential(E, agent, secret);
    const read = async (cid: string | null) =>
      (await data.query(P5.revoked, [...E, cid, agent])).rows[0] as Record<string, boolean>;
    const none = { credential_revoked: false, agent_revoked: false };
    expect(await read(c1)).toEqual(none);
    await seedCredentialRevocation(owner, E, c1, T0);
    expect(await read(c1)).toEqual({ credential_revoked: true, agent_revoked: false });
    expect(await read(c2)).toEqual(none);
    await seedAgentRevocation(owner, E, agent, T0);
    expect(await read(c2)).toEqual({ credential_revoked: false, agent_revoked: true });
    expect(await read(c1)).toEqual({ credential_revoked: true, agent_revoked: true });
    expect(await read(null)).toEqual({ credential_revoked: false, agent_revoked: true });
  });
});

describe('TC-AC-036 (the store half): an envelope-free operation’s record carries no envelope', () => {
  const row = (operation: string, actor: 'agent' | 'human', chain: string | null) => [
    id(),
    T0,
    null,
    ...E,
    operation,
    actor,
    actor === 'human' ? 'h@example.com' : null,
    actor === 'human' ? 'environmentCredential' : null,
    actor === 'human' ? 'c' : null,
    actor === 'agent' ? 'a' : null,
    actor === 'agent' ? 'i-1' : null,
    actor === 'agent' ? 'h@example.com' : null,
    null,
    null,
    false,
    chain,
    chain === null ? null : JSON.stringify({ originMode: 'autonomous' }),
    chain === null ? null : false,
    null,
  ];
  it('refuses exchangeBootstrap with a chain, and renewAgentCredential by a human', async () => {
    await expect(
      owner.query(P7.insertRecord, row('exchangeBootstrap', 'agent', JSON.stringify([{}]))),
    ).rejects.toMatchObject({ code: '23514', constraint: 'attribution_envelope_free_operations' });
    await expect(
      owner.query(P7.insertRecord, row('renewAgentCredential', 'human', null)),
    ).rejects.toMatchObject({ code: '23514', constraint: 'attribution_envelope_free_operations' });
  });

  it('accepts both operations as an agent with no envelope; another agent operation carries one (U7 D-ET-07)', async () => {
    await owner.query(P7.insertRecord, row('exchangeBootstrap', 'agent', null));
    await owner.query(P7.insertRecord, row('renewAgentCredential', 'agent', null));
    await owner.query(P7.insertRecord, row('publish', 'agent', JSON.stringify([{}])));
    await expect(
      owner.query(P7.insertRecord, row('constructedAgentOperation', 'agent', null)),
    ).rejects.toMatchObject({
      code: '23514',
      constraint: 'attribution_envelope_bearing_operations',
    });
  });
});

describe('TC-AC-049 (the store half): failed attempts are recorded only for an existing registration', () => {
  it('the batch insert, joined to registrations, writes A’s row and drops the unknown agent’s', async () => {
    const agent = `a-${id()}`;
    await registered(E, agent);
    const r = await data.query(P8.insertFailedBootstrapAttempts, [
      ['o1', 'o1'],
      ['p1', 'p1'],
      ['e', 'e'],
      [agent, `nobody-${id()}`],
      [T0.toISOString(), T0.toISOString()],
      [false, true],
      ['secret_mismatch', 'bound_refused'],
    ]);
    expect(r.rowCount).toBe(1);
    const { rows } = await owner.query(
      'SELECT agent, reason, refused_by_bound FROM failed_bootstrap_attempts WHERE agent = $1',
      [agent],
    );
    expect(rows).toEqual([{ agent, reason: 'secret_mismatch', refused_by_bound: false }]);
  });
});

describe('TC-AC-033 (the store half): E’s statements never return or touch E2’s rows', () => {
  it('per access path: the registration, the secret, the record, revocation, failed attempts', async () => {
    const agent = `a-${id()}`;
    const e = await registered(E, agent);
    const e2 = await registered(E2, agent);
    const c2 = await credential(E2, agent, e2.secret);
    await seedAgentRevocation(owner, E2, agent, T0);

    const reg = await data.query(P4.registrationForBootstrap, [...E, `x-${agent}`]);
    expect(reg.rowCount).toBe(0);
    const sec = await data.query(P6.secretForBootstrap, [...E, agent, e2.secret]);
    expect(sec.rows[0]).toMatchObject({ agent_exists: true, registration: null });
    expect((await data.query(P5.agentCredentialById, [c2, ...E])).rowCount).toBe(0);
    expect(
      (await data.query(P5.renewAgentCredential, [c2, ...E, agent, 'i-1', at(1500)])).rowCount,
    ).toBe(0);
    const revoked = await data.query(P5.revoked, [...E, c2, agent]);
    expect(revoked.rows[0]).toEqual({ credential_revoked: false, agent_revoked: false });
    const c1 = await credential(E, agent, e.secret);
    expect((await data.query(P5.agentCredentialById, [c1, ...E])).rowCount).toBe(1);
  });
});
