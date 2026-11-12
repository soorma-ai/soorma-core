// SPDX-License-Identifier: FSL-1.1-ALv2
//
// P4's registrations and secrets over a real environment store, as the app
// role (U5 NP-AR-01, 03, 04, 06): the primary key, the privileges, the
// constraints, the cap under its lock, and the agent-facts statement.
import { newRecordId, withTransaction } from '@soorma/env-store';
import { ConflictError, UnavailableError, type Queryable } from '@soorma/service-kit';
import { afterAll, beforeAll, describe, expect, it } from 'vitest';
import {
  agentFactsFromStore,
  digestRegistrationSecret,
  findRegistration,
  insertRegistration,
  insertSecretUnderCap,
  MAX_ACTIVE_SECRETS,
} from '../src/index.ts';
import { testEnvDatabase, type TestEnvDatabase } from '../../env-store/test/harness/database.ts';

const E = { organization: 'o1', project: 'p1', environment: 'e' };
const E2 = { organization: 'o1', project: 'p1', environment: 'e2' };
const now = new Date('2026-11-12T12:00:00Z');
const HELD = ['agent:register', 'event:publish', 'event:subscribe', 'grant:human'];
let n = 0;
const agentId = (): string => `agent-${n++}-${Date.now()}`;

let db: TestEnvDatabase;
beforeAll(async () => {
  db = await testEnvDatabase();
});
afterAll(async () => {
  await db?.drop();
});

const register = (agent: string, environment = E, standing = ['event:publish']) =>
  withTransaction(db.store, (tx) =>
    insertRegistration(tx, {
      environment,
      agent,
      sponsor: 'h@example.com',
      ceilingSnapshot: HELD,
      standingPermissions: standing,
      reBroadeningDeclaration: [],
      autonomyDeclared: true,
      registeredAt: now,
    }),
  );

const issue = (registration: string, environment = E) =>
  withTransaction(db.store, (tx) =>
    insertSecretUnderCap(tx, {
      id: newRecordId(),
      environment,
      registration,
      issuer: 'h@example.com',
      digest: digestRegistrationSecret(Buffer.alloc(32, n++ % 256)),
      issuedAt: now,
    }),
  );

describe('TC-AR-001, 019: a registration is written once, with every attribute', () => {
  it('stores the sets sorted and de-duplicated, and reads back exactly', async () => {
    const agent = agentId();
    const written = await withTransaction(db.store, (tx) =>
      insertRegistration(tx, {
        environment: E,
        agent,
        sponsor: 'h@example.com',
        ceilingSnapshot: ['grant:human', 'event:publish', 'agent:register', 'event:publish'],
        standingPermissions: ['event:publish'],
        reBroadeningDeclaration: [],
        autonomyDeclared: true,
        registeredAt: now,
      }),
    );
    expect(written.kind).toBe('registered');
    const read = await findRegistration(db.store, E, agent);
    expect(read).toEqual({
      agent,
      environment: E,
      sponsor: 'h@example.com',
      ceilingSnapshot: ['agent:register', 'event:publish', 'grant:human'],
      standingPermissions: ['event:publish'],
      reBroadeningDeclaration: [],
      autonomyDeclared: true,
      registeredAt: now,
      state: 'registered',
    });
  });
});

describe('TC-AR-023, 024: a taken identifier is exists; concurrent registrations write one row', () => {
  it('a second registration of one agent is exists, and writes nothing', async () => {
    const agent = agentId();
    expect((await register(agent)).kind).toBe('registered');
    expect(await register(agent)).toEqual({ kind: 'exists' });
  });

  it('two concurrent registrations of one agent: exactly one is registered', async () => {
    const agent = agentId();
    const results = await Promise.all([register(agent), register(agent)]);
    expect(results.map((r) => r.kind).sort()).toEqual(['exists', 'registered']);
    const client = await db.superuser();
    try {
      const { rows } = await client.query(
        `SELECT count(*)::int AS c FROM registrations WHERE agent = $1`,
        [agent],
      );
      expect(rows[0].c).toBe(1);
    } finally {
      await client.end();
    }
  });
});

describe('TC-AR-025, 039: registrations and secrets are per environment', () => {
  it('the same agent in E and E2 is two registrations; each is found only in its own', async () => {
    const agent = agentId();
    expect((await register(agent, E)).kind).toBe('registered');
    expect((await register(agent, E2, ['event:subscribe'])).kind).toBe('registered');
    expect((await findRegistration(db.store, E, agent))?.standingPermissions).toEqual([
      'event:publish',
    ]);
    expect((await findRegistration(db.store, E2, agent))?.standingPermissions).toEqual([
      'event:subscribe',
    ]);
  });

  it('a secret is counted, and its foreign key resolved, in its own environment only', async () => {
    const agent = agentId();
    await register(agent, E);
    await register(agent, E2);
    for (let i = 0; i < 3; i += 1) expect((await issue(agent, E2)).kind).toBe('issued');
    expect((await issue(agent, E)).kind).toBe('issued');
    const client = await db.superuser();
    try {
      const { rows } = await client.query(
        `SELECT environment, count(*)::int AS c FROM registration_secrets
          WHERE registration = $1 GROUP BY environment ORDER BY environment`,
        [agent],
      );
      expect(rows).toEqual([
        { environment: 'e', c: 1 },
        { environment: 'e2', c: 3 },
      ]);
    } finally {
      await client.end();
    }
  });

  it('a secret for a registration absent from its environment is refused by the foreign key', async () => {
    const agent = agentId();
    await register(agent, E2);
    await expect(issue(agent, E)).rejects.toThrow();
  });
});

describe('TC-AR-027: the app role holds only SELECT and INSERT on both tables', () => {
  it('UPDATE and DELETE fail with insufficient_privilege', async () => {
    const agent = agentId();
    await register(agent);
    await issue(agent);
    const app = await db.app();
    try {
      for (const statement of [
        `UPDATE registrations SET sponsor = 'x' WHERE agent = '${agent}'`,
        `UPDATE registrations SET standing_permissions = '{}' WHERE agent = '${agent}'`,
        `DELETE FROM registrations WHERE agent = '${agent}'`,
        `UPDATE registration_secrets SET state = 'active' WHERE registration = '${agent}'`,
        `DELETE FROM registration_secrets WHERE registration = '${agent}'`,
      ])
        await expect(app.query(statement)).rejects.toMatchObject({ code: '42501' });
      const { rows } = await app.query(`SELECT count(*)::int AS c FROM registrations`);
      expect(rows[0].c).toBeGreaterThan(0);
    } finally {
      await app.end();
    }
  });
});

describe('TC-AR-070: the store refuses rows that break its constraints', () => {
  const base = (agent: string) => ({
    agent,
    snapshot: ['agent:register', 'event:publish', 'event:subscribe'],
    standing: ['event:publish'],
    declaration: [] as string[],
    state: 'registered',
  });
  const insert = (
    client: Awaited<ReturnType<TestEnvDatabase['migrator']>>,
    r: ReturnType<typeof base>,
  ) =>
    client.query(
      `INSERT INTO registrations (organization, project, environment, agent, sponsor,
         ceiling_snapshot, standing_permissions, re_broadening_declaration, autonomy_declared,
         registered_at, state)
       VALUES ('o1', 'p1', 'e', $1, 'h', $2, $3, $4, false, now(), $5)`,
      [r.agent, r.snapshot, r.standing, r.declaration, r.state],
    );

  it.each([
    [
      'standing not within the snapshot',
      { standing: ['agent:retire'] },
      'registrations_standing_within_snapshot',
    ],
    [
      'a declaration not within standing',
      { declaration: ['event:subscribe'] },
      'registrations_declaration_within_standing',
    ],
    [
      '33 standing entries',
      {
        snapshot: Array.from({ length: 33 }, (_, i) => `x:p${i}`),
        standing: Array.from({ length: 33 }, (_, i) => `x:p${i}`),
      },
      'registrations_standing_bound',
    ],
    [
      '33 declared entries',
      {
        snapshot: Array.from({ length: 33 }, (_, i) => `x:p${i}`),
        standing: Array.from({ length: 32 }, (_, i) => `x:p${i}`),
        declaration: Array.from({ length: 33 }, (_, i) => `x:p${i}`),
      },
      'registrations_declaration_bound',
    ],
    ['the state retired', { state: 'retired' }, 'registrations_state'],
  ])('%s', async (_name, change, constraint) => {
    const client = await db.migrator();
    try {
      await expect(insert(client, { ...base(agentId()), ...change })).rejects.toMatchObject({
        constraint,
      });
    } finally {
      await client.end();
    }
  });

  it('a secret with a 31-byte digest, a retired state, or no registration', async () => {
    const agent = agentId();
    await register(agent);
    const client = await db.migrator();
    const secret = (registration: string, environment: string, digest: Buffer, state = 'active') =>
      client.query(
        `INSERT INTO registration_secrets (id, organization, project, environment, registration,
           issuer, digest, issued_at, state)
         VALUES ($1, 'o1', 'p1', $2, $3, 'h', $4, now(), $5)`,
        [newRecordId(), environment, registration, digest, state],
      );
    try {
      await expect(secret(agent, 'e', Buffer.alloc(31))).rejects.toMatchObject({
        constraint: 'registration_secrets_digest_length',
      });
      await expect(secret(agent, 'e', Buffer.alloc(32), 'retired')).rejects.toMatchObject({
        constraint: 'registration_secrets_state',
      });
      await expect(secret('no-such-agent', 'e', Buffer.alloc(32))).rejects.toMatchObject({
        constraint: 'registration_secrets_registration_fkey',
      });
      await expect(secret(agent, 'e2', Buffer.alloc(32))).rejects.toMatchObject({
        constraint: 'registration_secrets_registration_fkey',
      });
    } finally {
      await client.end();
    }
  });
});

describe('TC-AR-051, 052: at most 10 active secrets, under concurrency', () => {
  it('the 10th is issued and the 11th is limitReached, writing nothing', async () => {
    const agent = agentId();
    await register(agent);
    for (let i = 0; i < MAX_ACTIVE_SECRETS; i += 1)
      expect((await issue(agent)).kind).toBe('issued');
    expect(await issue(agent)).toEqual({ kind: 'limitReached' });
  });

  it('5 concurrent issuances at 9 active: exactly 1 is issued', async () => {
    const agent = agentId();
    await register(agent);
    for (let i = 0; i < 9; i += 1) await issue(agent);
    const results = await Promise.all(Array.from({ length: 5 }, () => issue(agent)));
    expect(results.filter((r) => r.kind === 'issued')).toHaveLength(1);
    expect(results.filter((r) => r.kind === 'limitReached')).toHaveLength(4);
    const client = await db.superuser();
    try {
      const { rows } = await client.query(
        `SELECT count(*)::int AS c FROM registration_secrets WHERE registration = $1`,
        [agent],
      );
      expect(rows[0].c).toBe(10);
    } finally {
      await client.end();
    }
  });
});

describe('TC-AR-053: the lock serialises one registration only', () => {
  it("another registration's issuance does not wait; the same registration's does", async () => {
    const a = agentId();
    const b = agentId();
    await register(a);
    await register(b);
    let release!: () => void;
    const gate = new Promise<void>((r) => (release = r));
    const holding = withTransaction(db.store, async (tx) => {
      await insertSecretUnderCap(tx, {
        id: newRecordId(),
        environment: E,
        registration: a,
        issuer: 'h',
        digest: Buffer.alloc(32),
        issuedAt: now,
      });
      await gate;
    });
    await new Promise((r) => setTimeout(r, 100));
    expect((await issue(b)).kind).toBe('issued');
    let sameDone = false;
    const same = issue(a).then((r) => {
      sameDone = true;
      return r;
    });
    await new Promise((r) => setTimeout(r, 300));
    expect(sameDone).toBe(false);
    release();
    await holding;
    expect((await same).kind).toBe('issued');
  });
});

describe('TC-AR-072: only the registrations primary key is registration_exists', () => {
  const tx = (error: Error): Queryable => ({ query: () => Promise.reject(error) });
  const input = {
    environment: E,
    agent: 'x',
    sponsor: 'h',
    ceilingSnapshot: [],
    standingPermissions: [],
    reBroadeningDeclaration: [],
    autonomyDeclared: false,
    registeredAt: now,
  };
  it('another constraint is unavailable; the primary key is exists', async () => {
    await expect(
      insertRegistration(tx(new ConflictError('other_key')), input),
    ).rejects.toBeInstanceOf(UnavailableError);
    await expect(
      insertRegistration(tx(new ConflictError(undefined)), input),
    ).rejects.toBeInstanceOf(UnavailableError);
    expect(await insertRegistration(tx(new ConflictError('registrations_pkey')), input)).toEqual({
      kind: 'exists',
    });
  });
});

describe('TC-AR-032: the agent-facts source', () => {
  it('one statement for 33 agents; E only; no snapshot or sponsor; absent agents not found', async () => {
    const agents = Array.from({ length: 32 }, () => agentId());
    for (const a of agents) await register(a);
    await register(agents[0]!, E2, ['event:subscribe']);
    let statements = 0;
    const counting: Queryable = {
      query: (statement, params) => {
        statements += 1;
        return db.store.query(statement, params);
      },
    };
    const facts = await agentFactsFromStore(counting).load(E, [...agents, 'missing']);
    expect(statements).toBe(1);
    expect(facts.size).toBe(32);
    expect(facts.has('missing')).toBe(false);
    const first = facts.get(agents[0]!)!;
    expect([...first.standingSet]).toEqual(['event:publish']);
    expect(first.registrationView).toEqual({
      autonomyDeclared: true,
      reBroadeningDeclaration: new Set(),
    });
    expect(Object.keys(first).sort()).toEqual(['registrationView', 'standingSet']);
  });

  it('no agents is no statement; a failure rejects the whole call', async () => {
    let statements = 0;
    const failing: Queryable = {
      query: () => {
        statements += 1;
        return Promise.reject(new UnavailableError('down'));
      },
    };
    expect((await agentFactsFromStore(failing).load(E, [])).size).toBe(0);
    expect(statements).toBe(0);
    await expect(agentFactsFromStore(failing).load(E, ['a'])).rejects.toBeInstanceOf(
      UnavailableError,
    );
  });
});
