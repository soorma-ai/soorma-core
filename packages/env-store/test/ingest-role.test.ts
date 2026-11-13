// SPDX-License-Identifier: FSL-1.1-ALv2
//
// Migrations 0005 and 0006, and S4's role soorma_env_ingest (U7 NP-ET-14, 15;
// D-ID-ET-04): TC-ET-081, TC-ET-082. The privilege test runs **the real
// statement objects** S4 will run (U5's agent facts, P4's sponsor for the
// record, P5's revocation read, P7's insert), so a grant that fits no
// statement, or a statement no grant fits, fails here. U4's, U5's, and U6's
// store and privilege tests are unchanged.
import { randomBytes } from 'node:crypto';
import { readdirSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import type pg from 'pg';
import { afterAll, beforeAll, describe, expect, it } from 'vitest';
import { SQL as P7 } from '../../attribution/src/sql.ts';
import { SQL as P5 } from '../../credentials/src/sql.ts';
import { SQL as P4 } from '../../registry/src/sql.ts';
import { checkRoleAttributes } from '../../org-identity/test/harness/roles.ts';
import { ENV_MIGRATIONS_DIR } from '../src/index.ts';
import { testEnvDatabase, type TestEnvDatabase } from './harness/database.ts';
import { ENV_INGEST } from './harness/roles.ts';

const E = ['o1', 'p1', 'e'] as const;
const T0 = new Date('2026-11-13T08:00:00Z');
const id = (): string => randomBytes(16).toString('base64url');

let db: TestEnvDatabase;
let owner: pg.Client;
let ingest: pg.Client;

beforeAll(async () => {
  db = await testEnvDatabase();
  owner = await db.migrator();
  ingest = await db.ingest();
});
afterAll(async () => {
  await Promise.all([owner?.end(), ingest?.end()]);
  await db?.drop();
});

/** A registration in E, written as the owner. */
async function registered(agent: string): Promise<void> {
  await owner.query(
    `INSERT INTO registrations (organization, project, environment, agent, sponsor,
       ceiling_snapshot, standing_permissions, re_broadening_declaration, autonomy_declared,
       registered_at, state)
     VALUES ($1, $2, $3, $4, 'h@example.com', '{event:publish}', '{event:publish}', '{}', true,
       $5, 'registered')`,
    [...E, agent, T0],
  );
}

const denied = async (text: string, params: unknown[] = []): Promise<void> => {
  await expect(ingest.query(text, params), text).rejects.toMatchObject({ code: '42501' });
};

describe('TC-ET-081: migrations 0005 and 0006 apply after 0001 to 0004', () => {
  it('the store has applied all six, in order', async () => {
    const su = await db.superuser();
    const { rows } = await su
      .query<{ version: string }>('SELECT version FROM schema_migrations ORDER BY version')
      .finally(() => su.end());
    expect(rows.map((r) => r.version)).toEqual([
      '0001_init',
      '0002_registrations',
      '0003_agent_credentials',
      '0004_attribution_envelope_free',
      '0005_attribution_envelope_bearing',
      '0006_event_ingest_role',
    ]);
    expect(readdirSync(ENV_MIGRATIONS_DIR).filter((f) => f.endsWith('.sql'))).toHaveLength(6);
  });

  it('0005 holds the one CHECK, alone', () => {
    const text = readFileSync(
      join(ENV_MIGRATIONS_DIR, '0005_attribution_envelope_bearing.sql'),
      'utf8',
    );
    expect(text.match(/ADD CONSTRAINT/g)).toHaveLength(1);
    expect(text).toContain('attribution_envelope_bearing_operations');
  });
});

describe('TC-ET-082: S4’s role runs exactly its statements, and nothing else', () => {
  it('its attributes are U4’s (no superuser, no create, no inherit, no replication, no bypass)', async () => {
    const su = await db.superuser();
    try {
      await checkRoleAttributes(su, [ENV_INGEST]);
    } finally {
      await su.end();
    }
  });

  it('the real statements succeed as soorma_env_ingest', async () => {
    const agent = `a-${id()}`;
    await registered(agent);
    // U5's agent-facts statement, behind U3's port.
    const facts = await ingest.query(P4.agentFacts, [...E, [agent]]);
    expect(facts.rows).toEqual([
      {
        agent,
        autonomy_declared: true,
        re_broadening_declaration: [],
        standing_permissions: ['event:publish'],
      },
    ]);
    // P4's sponsor for the record.
    const sponsor = await ingest.query(P4.sponsorForRecord, [...E, agent]);
    expect(sponsor.rows).toEqual([{ sponsor: 'h@example.com' }]);
    // P5's revocation read, both granularities.
    const revoked = await ingest.query(P5.revoked, [...E, id(), agent]);
    expect(revoked.rows).toEqual([{ credential_revoked: false, agent_revoked: false }]);
    // P7's insert: a publish record with its envelope facts.
    await ingest.query(P7.insertRecord, [
      id(),
      T0,
      'r1',
      ...E,
      'publish',
      'agent',
      null,
      'agentCredential',
      id(),
      agent,
      'i-1',
      'h@example.com',
      null,
      null,
      false,
      JSON.stringify([{ agent, instance: 'i-1' }]),
      JSON.stringify({ originMode: 'autonomous' }),
      false,
      null,
    ]);
  });

  it('each forbidden statement fails with permission denied', async () => {
    await denied('SELECT ceiling_snapshot FROM registrations');
    await denied('SELECT * FROM registrations');
    await denied('SELECT * FROM registration_secrets');
    await denied('SELECT * FROM grants');
    await denied('SELECT * FROM credentials');
    await denied('SELECT * FROM agent_credentials');
    await denied('SELECT * FROM attribution_records');
    await denied('SELECT * FROM schema_migrations');
    await denied("UPDATE attribution_records SET operation = 'x'");
    await denied('DELETE FROM attribution_records');
    await denied("UPDATE registrations SET sponsor = 'x'");
    await denied('DELETE FROM credential_revocations');
    await denied(
      `INSERT INTO registrations (organization, project, environment, agent, sponsor,
         ceiling_snapshot, standing_permissions, re_broadening_declaration, autonomy_declared,
         registered_at, state)
       VALUES ('o1', 'p1', 'e', 'x', 'h', '{}', '{}', '{}', true, now(), 'registered')`,
    );
  });
});
