// SPDX-License-Identifier: FSL-1.1-ALv2
//
// S3's refusals (business-logic-model §7; business-rules §8 to §11):
// TC-AC-007, 008, 009, 012, 013, 014, 018, 022, 025, 029, 030, 037, 042, 043,
// 048, 050, 061, 064, and the shared assertion on every Problem.
import { AGENT_BOOTSTRAP_LIMITS } from '@soorma/abuse-bound';
import { mintAgentCredential } from '@soorma/credentials';
import { newRecordId } from '@soorma/env-store';
import { afterAll, beforeAll, beforeEach, describe, expect, it } from 'vitest';
import {
  testEnvDatabase,
  type TestEnvDatabase,
} from '../../../packages/env-store/test/harness/database.ts';
import {
  seedAgentRevocation,
  seedCredentialRevocation,
} from '../../../packages/env-store/test/harness/seed.ts';
import {
  agentId,
  agentRing,
  bootstrap,
  BOOTSTRAP,
  claims,
  credentialFor,
  dataStore,
  E,
  E2,
  flushAttempts,
  gateway,
  MINUTE,
  problem,
  registered,
  renew,
  request,
  RENEWAL,
  rows,
  type Gateway,
  type Response,
} from './support.ts';

let db: TestEnvDatabase;
let g: Gateway;
let g2: Gateway;
beforeAll(async () => {
  db = await testEnvDatabase();
  g = await gateway(db);
  g2 = await gateway(db, { environment: E2, clock: g.clock });
});
afterAll(async () => {
  await g2?.close();
  await g?.close();
  await db?.drop();
});
beforeEach(() => {
  g.log.lines.length = 0;
});

const ENV = ['o1', 'p1', 'e'];

/** The shared assertion on every Problem soorma-core emits (U1 errors.md). */
function assertProblem(r: Response): void {
  expect(r.headers['content-type']).toMatch(/^application\/problem\+json/);
  const body = r.body as Record<string, unknown>;
  expect(body.type).toBe(`urn:soorma:problem:${String(body.code)}`);
  expect(body.status).toBe(r.status);
  expect(typeof body.title).toBe('string');
  expect(body.instance).toBe(`urn:soorma:request:${String(r.headers['soorma-request-id'])}`);
  expect(r.headers['soorma-contract-version']).toBe('0.1.0');
  if (r.status === 401) expect(r.headers['www-authenticate']).toBe('Bearer');
  else expect(r.headers['www-authenticate']).toBeUndefined();
  expect(r.text).not.toMatch(/soorma_rs_|soorma_ac_|stack|at \w+ \(/);
}

/** A registration secret with its last characters changed: right shape, wrong value. */
function corrupt(value: string): string {
  return value.slice(0, -4) + (value.endsWith('AAAA') ? 'BBBB' : 'AAAA');
}

/** A trust refusal names nothing beyond its code (BR-RF-AC-01). */
function bare(r: Response): Record<string, unknown> {
  const rest = { ...(r.body as Record<string, unknown>) };
  delete rest.instance;
  return rest;
}

async function failedAttempts(agent: string): Promise<Record<string, any>[]> {
  await flushAttempts(g);
  return rows(g, 'failed_bootstrap_attempts', agent);
}

describe('TC-AC-007: a wrong secret is refused, and the failure recorded against the registration', () => {
  it('authentication_failed, no detail; a row secret_mismatch; the event names no secret', async () => {
    const agent = agentId();
    const secret = await registered(g, agent);
    const r = await bootstrap(g, agent, corrupt(secret.value));
    expect(problem(r)).toEqual({ status: 403, code: 'authentication_failed' });
    assertProblem(r);
    expect(r.body).not.toHaveProperty('errors');
    expect(await failedAttempts(agent)).toMatchObject([
      { agent, reason: 'secret_mismatch', refused_by_bound: false },
    ]);
    const [event] = g.log.named('bootstrap.refused');
    expect(event).toMatchObject({ agent, instance: 'i-1', code: 'secret_mismatch' });
    const line = g.log.lines.join('\n');
    expect(line).not.toContain(secret.value);
    expect(line).not.toContain(secret.id);
  });
});

describe('TC-AC-048: every bootstrap failure is the same response', () => {
  it('the same status, code, body shape, and headers for each cause; only the log differs', async () => {
    const unregisteredAgent = agentId();
    const known = agentId();
    const s = await registered(g, known);
    const revoked = agentId();
    const sr = await registered(g, revoked);
    await seedAgentRevocation(g.owner, ENV, revoked, g.clock.now());
    const other = agentId();
    const so = await registered(g, other);
    const cases: [string, Promise<Response>, string][] = [
      ['unknown registration', bootstrap(g, unregisteredAgent, s.value), 'unknown_registration'],
      ['another registration’s secret', bootstrap(g, known, so.value), 'unknown_secret'],
      ['a wrong secret', bootstrap(g, known, corrupt(s.value)), 'secret_mismatch'],
      ['a revoked agent', bootstrap(g, revoked, sr.value), 'agent_revoked'],
      [
        'material of another type',
        bootstrap(g, known, 'soorma_em_AAAAAAAAAAAA'),
        'unsupported_material',
      ],
      ['a malformed secret', bootstrap(g, known, 'soorma_rs_short'), 'malformed_secret'],
    ];
    const answers = await Promise.all(cases.map(([, r]) => r));
    const reference = answers[0]!;
    for (const [i, r] of answers.entries()) {
      const name = cases[i]![0];
      expect(problem(r), name).toEqual({ status: 403, code: 'authentication_failed' });
      assertProblem(r);
      expect(bare(r), name).toEqual(bare(reference));
      expect(Object.keys(r.headers).sort(), name).toEqual(Object.keys(reference.headers).sort());
    }
    const reasons = g.log.named('bootstrap.refused').map((e) => e.code);
    expect(reasons.sort()).toEqual(cases.map(([, , reason]) => reason).sort());
  });
});

describe('TC-AC-048: the states a later milestone adds are refused the same way', () => {
  // The M1 store admits only a `registered` registration and an `active`
  // secret (0002's CHECKs), so S3's two state checks are defensive until
  // deregistration and secret revocation exist. They are reached here on a
  // database of their own, whose owner drops those two CHECKs: test-only, and
  // never a change to the schema.
  let other: TestEnvDatabase;
  let h: Gateway;
  beforeAll(async () => {
    other = await testEnvDatabase();
    h = await gateway(other);
    await h.owner.query('ALTER TABLE registrations DROP CONSTRAINT registrations_state');
    await h.owner.query(
      'ALTER TABLE registration_secrets DROP CONSTRAINT registration_secrets_state',
    );
  });
  afterAll(async () => {
    await h?.close();
    await other?.drop();
  });

  it.each([
    ['a secret no longer active', { secretState: 'revoked' }, 'secret_not_active'],
    ['a registration not registered', { state: 'deregistered' }, 'registration_not_registered'],
  ])('%s: authentication_failed, recorded with its reason', async (_name, state, reason) => {
    const agent = agentId();
    const s = await registered(h, agent, state);
    const r = await bootstrap(h, agent, s.value);
    expect(problem(r)).toEqual({ status: 403, code: 'authentication_failed' });
    expect(h.log.named('bootstrap.refused').at(-1)).toMatchObject({ code: reason });
    await h.runtime.attempts.flush();
    expect(await rows(h, 'failed_bootstrap_attempts', agent)).toMatchObject([{ reason }]);
  });

  it('a registration no longer registered cannot renew its credentials', async () => {
    const c = await credentialFor(h);
    await h.owner.query(`UPDATE registrations SET state = 'deregistered' WHERE agent = $1`, [
      c.agent,
    ]);
    expect(problem(await renew(h, c.credential))).toEqual({
      status: 401,
      code: 'credential_refused',
    });
    expect(h.log.named('renewal.refused').at(-1)).toMatchObject({
      code: 'registration_not_registered',
    });
  });
});

describe('TC-AC-014: bootstrap for an unknown registration is refused', () => {
  it('authentication_failed; no failed-attempt row; the bound still counts it', async () => {
    const agent = agentId();
    const r = await bootstrap(g, agent, 'soorma_rs_' + 'A'.repeat(22) + '.' + 'A'.repeat(43));
    expect(problem(r)).toEqual({ status: 403, code: 'authentication_failed' });
    await flushAttempts(g);
    const counted = await g.owner.query<{ n: string }>(
      `SELECT count(*) AS n FROM failed_bootstrap_attempts WHERE agent = $1`,
      [agent],
    );
    expect(Number(counted.rows[0]!.n)).toBe(0);
    const slot = g.runtime.bound.slotOf(
      (await import('@soorma/abuse-bound')).agentSlotKey(E, agent),
    );
    const held = await g.owner.query<{ consecutive: number }>(
      'SELECT consecutive FROM attempt_slots WHERE slot = $1',
      [slot],
    );
    expect(held.rows[0]?.consecutive).toBeGreaterThanOrEqual(1);
  });
});

describe('TC-AC-022: bootstrap material of an unsupported type is rejected', () => {
  it('a soorma_em_ value is authentication_failed after the bound, recorded unsupported_material', async () => {
    const agent = agentId();
    await registered(g, agent);
    const r = await bootstrap(g, agent, 'soorma_em_' + 'A'.repeat(40));
    expect(problem(r)).toEqual({ status: 403, code: 'authentication_failed' });
    expect(await failedAttempts(agent)).toMatchObject([{ reason: 'unsupported_material' }]);
  });
});

describe('TC-AC-025: a revoked agent cannot bootstrap, and its credentials cannot renew', () => {
  it('renewal credential_refused; bootstrap the one refusal, recorded agent_revoked', async () => {
    const c = await credentialFor(g);
    await seedAgentRevocation(g.owner, ENV, c.agent, g.clock.now());
    expect(problem(await renew(g, c.credential))).toEqual({
      status: 401,
      code: 'credential_refused',
    });
    expect(problem(await bootstrap(g, c.agent, c.secret.value))).toEqual({
      status: 403,
      code: 'authentication_failed',
    });
    expect(await failedAttempts(c.agent)).toMatchObject([{ reason: 'agent_revoked' }]);
  });

  it('renewal logs agent_revoked, not credential_revoked (BR-RN-03; BR-RF-AC-03)', async () => {
    const c = await credentialFor(g);
    await seedAgentRevocation(g.owner, ENV, c.agent, g.clock.now());
    expect(problem(await renew(g, c.credential))).toEqual({
      status: 401,
      code: 'credential_refused',
    });
    expect(g.log.named('renewal.refused').at(-1)).toMatchObject({
      agent: c.agent,
      code: 'agent_revoked',
    });
  });
});

describe('BR-RN-03: both granularities revoked, the agent’s takes precedence (D-CG-AC-31)', () => {
  it('a revoked cid of a revoked agent: credential_refused, logged agent_revoked', async () => {
    const c = await credentialFor(g);
    await seedCredentialRevocation(g.owner, ENV, c.cid, g.clock.now());
    await seedAgentRevocation(g.owner, ENV, c.agent, g.clock.now());
    const r = await renew(g, c.credential);
    expect(problem(r)).toEqual({ status: 401, code: 'credential_refused' });
    assertProblem(r);
    expect(g.log.named('renewal.refused').at(-1)).toMatchObject({ code: 'agent_revoked' });
  });
});

describe('BR-RN-03: the read inside renewal’s transaction names the granularity too', () => {
  // A revocation committed after P1's read is caught by the transaction's
  // read (D-CG-AC-24). The hook seeds it right after P1's read, the only
  // revocation read made through the store itself: the transaction's goes
  // through its own client.
  let hook: (() => Promise<void>) | undefined;
  let store: ReturnType<typeof dataStore>;
  let h: Gateway;
  beforeAll(async () => {
    store = dataStore(db);
    const pool = store.pool;
    const query = pool.query.bind(pool) as (...args: unknown[]) => Promise<unknown>;
    pool.query = (async (...args: unknown[]) => {
      const result = await query(...args);
      if (typeof args[0] === 'string' && args[0].includes('agent_revocations') && hook) {
        const run = hook;
        hook = undefined;
        await run();
      }
      return result;
    }) as typeof pool.query;
    h = await gateway(db, { store });
  });
  afterAll(async () => {
    await h?.close();
    await store?.close();
  });

  it.each([
    ['the cid', 'credential_revoked'],
    ['the agent', 'agent_revoked'],
  ] as const)(
    '%s revoked after P1’s read: credential_refused, logged %s, nothing written',
    async (_n, reason) => {
      const c = await credentialFor(h);
      const before = (await rows(h, 'attribution_records', c.agent)).length;
      hook = () =>
        reason === 'agent_revoked'
          ? seedAgentRevocation(h.owner, ENV, c.agent, h.clock.now())
          : seedCredentialRevocation(h.owner, ENV, c.cid, h.clock.now());
      expect(problem(await renew(h, c.credential))).toEqual({
        status: 401,
        code: 'credential_refused',
      });
      expect(hook).toBeUndefined();
      expect(h.log.named('renewal.refused').at(-1)).toMatchObject({ code: reason });
      expect((await rows(h, 'attribution_records', c.agent)).length).toBe(before);
    },
  );
});

describe('TC-AC-009: a revoked credential is refused at renewal, at once', () => {
  it('credential_refused immediately after the cid’s revocation is seeded', async () => {
    const c = await credentialFor(g);
    await seedCredentialRevocation(g.owner, ENV, c.cid, g.clock.now());
    const r = await renew(g, c.credential);
    expect(problem(r)).toEqual({ status: 401, code: 'credential_refused' });
    assertProblem(r);
    expect(g.log.named('renewal.refused').at(-1)).toMatchObject({ code: 'credential_revoked' });
  });
});

describe('TC-AC-012: a human credential is refused by kind, without verifying', () => {
  it.each([
    ['an environment credential', 'soorma_ec_eyJhbGciOiJFZERTQSJ9.e30.c2ln'],
    ['a sign-in', 'soorma_si_eyJhbGciOiJFZERTQSJ9.e30.c2ln'],
    ['a delegation credential', 'soorma_dc_eyJhbGciOiJFZERTQSJ9.e30.c2ln'],
    ['an unknown prefix', 'eyJhbGciOiJFZERTQSJ9.e30.c2ln'],
  ])('%s at renewal: credential_refused, refused at the presenter', async (_name, token) => {
    const r = await renew(g, token);
    expect(problem(r)).toEqual({ status: 401, code: 'credential_refused' });
    assertProblem(r);
    expect(g.log.named('renewal.refused').at(-1)).toMatchObject({ code: 'presenter' });
  });

  it('two credentials, or a Soorma-Delegation header, are refused unverified', async () => {
    const c = await credentialFor(g);
    const both = await request(g.edge, RENEWAL, {
      credential: c.credential,
      headers: { 'soorma-delegation': 'soorma_dc_x' },
    });
    expect(problem(both)).toEqual({ status: 401, code: 'credential_refused' });
  });
});

describe('TC-AC-013: a credential from E2 is refused at E’s data gateway', () => {
  it('E2’s agent credential at E’s renewal: credential_refused, no expiry disclosed', async () => {
    const c2 = await credentialFor(g2);
    const fresh = await renew(g, c2.credential);
    expect(problem(fresh)).toEqual({ status: 401, code: 'credential_refused' });
    g.clock.advance(20 * MINUTE);
    const expired = await renew(g, c2.credential);
    expect(problem(expired)).toEqual({ status: 401, code: 'credential_refused' });
    g.clock.advance(-20 * MINUTE);
  });

  it('E2’s secret at E’s bootstrap: authentication_failed', async () => {
    const agent = agentId();
    const s2 = await registered(g2, agent, { env: E2 });
    await registered(g, agent);
    expect(problem(await bootstrap(g, agent, s2.value))).toEqual({
      status: 403,
      code: 'authentication_failed',
    });
  });

  it('a token signed for E with E2’s ring is refused (wrong key)', async () => {
    const forged = await mintAgentCredential(
      {
        environment: E,
        agent: 'a',
        instance: 'i-1',
        cid: newRecordId(),
        jti: newRecordId(),
        issuedAt: g.clock.now(),
        expiresAt: new Date(g.clock.now().getTime() + MINUTE),
      },
      agentRing(),
    );
    expect(problem(await renew(g, forged))).toEqual({ status: 401, code: 'credential_refused' });
    expect(g.log.named('renewal.refused').at(-1)).toMatchObject({ code: 'unknown_key' });
  });
});

describe('TC-AC-050: a token whose record is missing or names another instance is refused', () => {
  it('no record: credential_refused, nothing written', async () => {
    const token = await mintAgentCredential(
      {
        environment: E,
        agent: agentId(),
        instance: 'i-1',
        cid: newRecordId(),
        jti: newRecordId(),
        issuedAt: g.clock.now(),
        expiresAt: new Date(g.clock.now().getTime() + MINUTE),
      },
      g.ring,
    );
    expect(problem(await renew(g, token))).toEqual({ status: 401, code: 'credential_refused' });
    expect(g.log.named('renewal.refused').at(-1)).toMatchObject({ code: 'no_record' });
  });

  it('a record naming another instance: credential_refused, nothing written', async () => {
    const c = await credentialFor(g);
    const c1 = claims(c.credential);
    const token = await mintAgentCredential(
      {
        environment: E,
        agent: c.agent,
        instance: 'i-other',
        cid: c.cid,
        jti: newRecordId(),
        issuedAt: g.clock.now(),
        expiresAt: new Date(c1.exp * 1000),
      },
      g.ring,
    );
    const before = (await rows(g, 'attribution_records', c.agent)).length;
    expect(problem(await renew(g, token))).toEqual({ status: 401, code: 'credential_refused' });
    expect(g.log.named('renewal.refused').at(-1)).toMatchObject({ code: 'record_mismatch' });
    expect((await rows(g, 'attribution_records', c.agent)).length).toBe(before);
  });
});

describe('TC-AC-029: bootstrap refuses a credential header with malformed_request', () => {
  it.each([
    ['Authorization', { authorization: 'Bearer soorma_ac_x' }, ['Authorization']],
    ['Soorma-Delegation', { 'soorma-delegation': 'soorma_dc_x' }, ['Soorma-Delegation']],
    [
      'both',
      { authorization: 'Bearer x', 'soorma-delegation': 'y' },
      ['Authorization', 'Soorma-Delegation'],
    ],
  ])('%s: 400 naming the header; nothing counted', async (_name, headers, named) => {
    const agent = agentId();
    const s = await registered(g, agent);
    const r = await bootstrap(g, agent, s.value, 'i-1', headers);
    expect(problem(r)).toEqual({ status: 400, code: 'malformed_request' });
    assertProblem(r);
    expect((r.body.errors as { header: string }[]).map((e) => e.header)).toEqual(named);
    expect(r.text).not.toContain('soorma_ac_x');
    expect(g.log.named('bootstrap.refused')).toEqual([]);
    expect((await bootstrap(g, agent, s.value)).status).toBe(200);
  });
});

describe('TC-AC-037: a draft envelope or an extra field in the bootstrap body is refused', () => {
  it.each([
    ['an envelope', { envelope: { clientContractVersion: '0.1.0' } }, '/envelope'],
    ['an environment', { environment: 'e2' }, '/environment'],
  ])('%s: malformed_request with a pointer; nothing counted', async (_name, extra, pointer) => {
    const agent = agentId();
    const s = await registered(g, agent);
    const r = await request(g.edge, BOOTSTRAP, {
      body: { agent, secret: s.value, instance: 'i-1', ...extra },
    });
    expect(problem(r)).toEqual({ status: 400, code: 'malformed_request' });
    expect(JSON.stringify(r.body.errors)).toContain(pointer);
    expect(g.log.named('bootstrap.refused')).toEqual([]);
    expect(g.log.named('bound.refused')).toEqual([]);
  });
});

describe('TC-AC-064: body bounds at S3', () => {
  it('a body over 16 KiB is payload_too_large; a non-JSON body malformed_request at ""', async () => {
    const big = await request(g.edge, BOOTSTRAP, {
      body: { agent: 'a', secret: 'x'.repeat(17 * 1024), instance: 'i-1' },
    });
    expect(problem(big)).toEqual({ status: 413, code: 'payload_too_large' });
    const text = await request(g.edge, BOOTSTRAP, {
      body: 'not json',
      headers: { 'content-type': 'text/plain' },
    });
    expect(problem(text)).toEqual({ status: 400, code: 'malformed_request' });
    expect(text.body.errors[0].pointer).toBe('');
  });

  it('a secret over 256 characters fails the schema', async () => {
    const r = await request(g.edge, BOOTSTRAP, {
      body: { agent: 'a', secret: 'soorma_rs_' + 'A'.repeat(247), instance: 'i-1' },
    });
    expect(problem(r)).toEqual({ status: 400, code: 'malformed_request' });
  });

  it('a missing or wrong contract version is unsupported_contract_version', async () => {
    const r = await request(g.edge, BOOTSTRAP, {
      body: { agent: 'a', secret: 'x', instance: 'i-1' },
      headers: { 'soorma-contract-version': '9.9.9' },
    });
    expect(problem(r)).toEqual({ status: 400, code: 'unsupported_contract_version' });
  });
});

describe('TC-AC-030, 018: any other path or method on S3 is a bare 404', () => {
  it.each([
    ['GET', BOOTSTRAP],
    ['GET', RENEWAL],
    ['POST', '/agent-credentials/current'],
    ['GET', '/revocations'],
    ['POST', '/agent-credentials/current/revocation'],
    ['DELETE', BOOTSTRAP],
    ['POST', '/environment-credentials'],
  ] as const)('%s %s: 404, no body, the Soorma headers', async (method, path) => {
    const r = await request(g.edge, path, { method });
    expect(r.status).toBe(404);
    expect(r.text).toBe('');
    expect(r.headers['soorma-contract-version']).toBe('0.1.0');
    expect(r.headers['soorma-request-id']).toBeDefined();
  });
});

describe('TC-AC-008, 061: the bootstrap bound', () => {
  it('backoff from the 10th failure; refused with Retry-After; recorded; lifted within 60 s', async () => {
    const agent = agentId();
    const s = await registered(g, agent);
    const statuses: number[] = [];
    for (let i = 0; i < AGENT_BOOTSTRAP_LIMITS.backoffFrom; i++)
      statuses.push((await bootstrap(g, agent, corrupt(s.value))).status);
    expect(statuses.every((x) => x === 403)).toBe(true);
    // The 10th consecutive failure sets a wait: the next attempt, even correct, is refused.
    const refused = await bootstrap(g, agent, s.value);
    expect(problem(refused)).toMatchObject({ status: 429, code: 'too_many_attempts' });
    expect(Number(refused.headers['retry-after'])).toBeGreaterThanOrEqual(1);
    assertProblem(refused);
    expect(g.log.named('bound.refused').at(-1)).toMatchObject({ agent });
    const recorded = await failedAttempts(agent);
    expect(recorded.filter((a) => a.refused_by_bound).length).toBe(1);
    expect(recorded.filter((a) => a.reason === 'bound_refused').length).toBe(1);
    // TC-AC-061: renewal is outside the bound; a lineage renews meanwhile.
    const c = await credentialFor(g);
    expect((await renew(g, c.credential)).status).toBe(200);
    // After the wait (at most 60 seconds after the attack stops), the correct secret succeeds.
    g.clock.advance(AGENT_BOOTSTRAP_LIMITS.backoffCapSeconds * 1000);
    expect((await bootstrap(g, agent, s.value)).status).toBe(200);
  });

  it('the bound does not reveal whether the agent exists: an unknown agent is refused the same', async () => {
    const unknown = agentId();
    let last: Response | undefined;
    for (let i = 0; i <= AGENT_BOOTSTRAP_LIMITS.backoffFrom; i++)
      last = await bootstrap(g, unknown, 'soorma_rs_' + 'A'.repeat(22) + '.' + 'A'.repeat(43));
    expect(problem(last!)).toMatchObject({ status: 429, code: 'too_many_attempts' });
  });
});

describe('TC-AC-042: every S3 refusal holds for a raw call', () => {
  it('a raw HTTP request with no client library gets each specified code', async () => {
    const raw = (headers: Record<string, string>, payload?: string) =>
      g.edge
        .getHttpAdapter()
        .getInstance()
        .inject({ method: 'POST', url: RENEWAL, headers, ...(payload ? { payload } : {}) });
    expect((await raw({})).statusCode).toBe(401);
    expect((await raw({ authorization: 'Bearer soorma_ac_x' })).statusCode).toBe(401);
    const c = await credentialFor(g);
    expect((await raw({ authorization: `Bearer ${c.credential}` })).statusCode).toBe(400);
    expect(
      (
        await raw({
          authorization: `Bearer ${c.credential}`,
          'soorma-contract-version': '0.1.0',
        })
      ).statusCode,
    ).toBe(200);
  });
});

describe('TC-AC-043: the same credential from another address resolves the same', () => {
  it('the same agent and instance whatever the client address; no credential anywhere else', async () => {
    const c = await credentialFor(g);
    const from = (remoteAddress: string) =>
      g.edge
        .getHttpAdapter()
        .getInstance()
        .inject({
          method: 'POST',
          url: RENEWAL,
          remoteAddress,
          headers: { authorization: `Bearer ${c.credential}`, 'soorma-contract-version': '0.1.0' },
        });
    const a = await from('10.0.0.1');
    const b = await from('192.168.7.9');
    for (const r of [a, b]) {
      const body = JSON.parse(r.body) as { agent: string; instance: string };
      expect(r.statusCode).toBe(200);
      expect({ agent: body.agent, instance: body.instance }).toEqual({
        agent: c.agent,
        instance: 'i-1',
      });
    }
    const inCookie = await g.edge
      .getHttpAdapter()
      .getInstance()
      .inject({
        method: 'POST',
        url: RENEWAL,
        headers: { cookie: `credential=${c.credential}`, 'soorma-contract-version': '0.1.0' },
      });
    expect(inCookie.statusCode).toBe(401);
    const inQuery = await g.edge
      .getHttpAdapter()
      .getInstance()
      .inject({
        method: 'POST',
        url: `${RENEWAL}?access_token=${c.credential}`,
        headers: { 'soorma-contract-version': '0.1.0' },
      });
    expect(inQuery.statusCode).toBe(401);
  });
});
