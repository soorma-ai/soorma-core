// SPDX-License-Identifier: FSL-1.1-ALv2
//
// S3 fails closed (SECURITY-15; NFR-AC-10): TC-AC-010 (revocation state
// unreadable at renewal), TC-AC-052 (the store down for both operations:
// unavailable, nothing written, the bound settled as a failure).
import { connectEnvStore } from '@soorma/env-store';
import { afterAll, beforeAll, describe, expect, it } from 'vitest';
import {
  testEnvDatabase,
  type TestEnvDatabase,
} from '../../../packages/env-store/test/harness/database.ts';
import {
  agentId,
  bootstrap,
  credentialFor,
  flushAttempts,
  gateway,
  problem,
  registered,
  renew,
  rows,
  type Gateway,
} from './support.ts';

let db: TestEnvDatabase;
let g: Gateway;
beforeAll(async () => {
  db = await testEnvDatabase();
  g = await gateway(db);
});
afterAll(async () => {
  await g?.close();
  await db?.drop();
});

const UNAVAILABLE = { status: 503, code: 'unavailable', retryAfter: '5' };

/** Runs `work` with a privilege of soorma_env_data revoked, then restores it. */
async function without(privilege: string, work: () => Promise<void>): Promise<void> {
  await g.owner.query(`REVOKE ${privilege} FROM soorma_env_data`);
  try {
    await work();
  } finally {
    await g.owner.query(`GRANT ${privilege} TO soorma_env_data`);
  }
}

describe('TC-AC-010: unconfirmable revocation state fails closed at renewal', () => {
  it.each([
    ['the credential revocations', 'SELECT ON credential_revocations'],
    ['the agent revocations', 'SELECT ON agent_revocations'],
  ])('%s unreadable: 503, Retry-After 5, store.unavailable; nothing written', async (_n, p) => {
    const c = await credentialFor(g);
    const before = await rows(g, 'attribution_records', c.agent);
    const [record] = await rows(g, 'agent_credentials', c.agent);
    await without(p, async () => {
      expect(problem(await renew(g, c.credential))).toEqual(UNAVAILABLE);
    });
    expect(g.log.named('store.unavailable').length).toBeGreaterThan(0);
    expect(await rows(g, 'attribution_records', c.agent)).toEqual(before);
    expect((await rows(g, 'agent_credentials', c.agent))[0]!.expires_at).toEqual(
      record!.expires_at,
    );
  });
});

describe('TC-AC-052: with the store down, both operations fail closed and write nothing', () => {
  it('the bound is admitted, then the secret read fails: 503; settled as a failure', async () => {
    const agent = agentId();
    const s = await registered(g, agent);
    await without('SELECT ON registration_secrets', async () => {
      expect(problem(await bootstrap(g, agent, s.value))).toEqual(UNAVAILABLE);
    });
    expect(await rows(g, 'agent_credentials', agent)).toEqual([]);
    expect(await rows(g, 'attribution_records', agent)).toEqual([]);
    expect(g.log.named('bootstrap.refused').at(-1)).toMatchObject({
      agent,
      code: 'store_unavailable',
    });
    await flushAttempts(g);
    expect(await rows(g, 'failed_bootstrap_attempts', agent)).toMatchObject([
      { reason: 'store_unavailable', refused_by_bound: false },
    ]);
  });

  it('the agent’s revocation unreadable at bootstrap: 503, nothing written', async () => {
    const agent = agentId();
    const s = await registered(g, agent);
    await without('SELECT ON agent_revocations', async () => {
      expect(problem(await bootstrap(g, agent, s.value))).toEqual(UNAVAILABLE);
    });
    expect(await rows(g, 'agent_credentials', agent)).toEqual([]);
  });

  it('a store S3 cannot reach: both operations 503, before any check that needs it', async () => {
    const c = await credentialFor(g);
    const down = connectEnvStore({
      host: '127.0.0.1',
      port: 1,
      database: 'x',
      user: 'x',
      password: 'x',
    });
    const h = await gateway(db, { store: down, ring: g.ring, clock: g.clock });
    try {
      expect(problem(await bootstrap(h, c.agent, c.secret.value))).toEqual(UNAVAILABLE);
      expect(problem(await renew(h, c.credential))).toEqual(UNAVAILABLE);
      // The check order holds with the store down: a bad credential is refused first.
      expect(problem(await renew(h, 'soorma_ec_x.y.z'))).toEqual({
        status: 401,
        code: 'credential_refused',
      });
      expect(problem(await renew(h, 'soorma_ac_eyJhbGciOiJFZERTQSJ9.e30.c2ln'))).toEqual({
        status: 401,
        code: 'credential_refused',
      });
    } finally {
      await h.close();
      await down.close();
    }
  });
});
