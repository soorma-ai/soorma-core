// SPDX-License-Identifier: FSL-1.1-ALv2
//
// Step 4 at S4, through P5's cache with the bound B (D-ET-12, 15): TC-ET-014
// and 028 (revocation reaches a publish within B, at either granularity),
// 031 (the two granularities are not told apart), 032 (the caches never
// answer across environments), 066 (with the store down, steps 1 to 3 answer
// exactly), 035 (a record that cannot be written: nothing delivered, no
// stream; GAP-ET-001's work-around).
import { afterAll, afterEach, beforeAll, describe, expect, it } from 'vitest';
import {
  testEnvDatabase,
  type TestEnvDatabase,
} from '../../../packages/env-store/test/harness/database.ts';
import {
  agentKeys,
  agentWith,
  credential,
  E2,
  flush,
  ingest,
  ingestStore,
  publish,
  PUBLISHER,
  registered,
  revokeAgent,
  revokeCredential,
  subscribe,
  SUBSCRIBER,
  type Ingest,
  type Response,
} from './support.ts';

let db: TestEnvDatabase;
const open: Ingest[] = [];

beforeAll(async () => {
  db = await testEnvDatabase();
});
afterEach(async () => {
  for (const g of open.splice(0)) await g.close();
});
afterAll(async () => {
  await db?.drop();
});

async function fresh(options: Parameters<typeof ingest>[1] = {}): Promise<Ingest> {
  const g = await ingest(db, options);
  open.push(g);
  return g;
}

/** A Problem with its request id removed: what a client could compare. */
const sameButId = (r: Response): string =>
  r.text.replace(/urn:soorma:request:[0-9a-f-]+/, 'urn:soorma:request:*');

describe('TC-ET-014 and 028: revocation reaches a publish within B, at either granularity', () => {
  it('at 30 s the cached answer may serve; from 60 s after the read, credential_refused', async () => {
    const g = await fresh();
    const a1 = await agentWith(g, PUBLISHER);
    const a2 = await agentWith(g, PUBLISHER);
    for (const a of [a1, a2]) expect((await publish(g, a)).status).toBe(202);
    await revokeCredential(g, a1);
    await revokeAgent(g, a2.agent);
    g.clock.ms += 30_000;
    for (const a of [a1, a2]) expect((await publish(g, a)).status).toBe(202);
    g.clock.ms += 29_999;
    for (const a of [a1, a2]) expect((await publish(g, a)).status).toBe(202);
    g.clock.ms += 1;
    const r1 = await publish(g, a1);
    const r2 = await publish(g, a2);
    for (const r of [r1, r2]) {
      expect(r.status).toBe(401);
      expect(r.body.code).toBe('credential_refused');
    }
    // TC-ET-031: byte-identical apart from the request id; only the log tells them apart.
    expect(sameButId(r1)).toBe(sameButId(r2));
    const reasons = g.log.named('ingest.refused').map((e) => e.reason);
    expect(reasons).toContain('credential_revoked');
    expect(reasons).toContain('agent_revoked');
  });
});

describe('TC-ET-032: S4’s caches never answer across environments', () => {
  it('an agent of the same name revoked in E2 leaves the publish at E unaffected', async () => {
    const g = await fresh();
    const a = await agentWith(g, PUBLISHER);
    // The same agent name, registered and revoked in E2.
    await registered(g, a.agent, { env: E2, standing: PUBLISHER });
    await revokeAgent(g, a.agent, E2);
    expect((await publish(g, a)).status).toBe(202);
    g.clock.ms += 61_000;
    expect((await publish(g, a)).status).toBe(202);
  });
});

describe('TC-ET-066 (BR-CK-05): with the store down, steps 1 to 3 answer exactly', () => {
  it('malformed, foreign, wrong-environment, expired: as with the store up; never unavailable', async () => {
    const store = ingestStore(db);
    const g = await fresh({ store });
    const a = await agentWith(g, PUBLISHER);
    const expired = await credential(g, a.agent, {
      issuedAt: new Date(g.clock.ms - 20 * 60_000),
      lifetimeMs: 15 * 60_000,
    });
    const foreign = await credential(g, a.agent, { keys: agentKeys() });
    const wrongEnv = await credential(g, a.agent, { env: E2 });
    await store.close();
    const expect401 = async (token: string, code: string): Promise<void> => {
      const r = await publish(g, token);
      expect({ status: r.status, code: r.body?.code }).toEqual({ status: 401, code });
    };
    await expect401('soorma_ac_not.a.token', 'credential_refused');
    await expect401(foreign.token, 'credential_refused');
    await expect401(wrongEnv.token, 'credential_refused');
    await expect401(expired.token, 'credential_expired');
    // A well-formed E credential with the cache cold: step 4 cannot answer.
    const cold = await publish(g, a);
    expect({ status: cold.status, retry: cold.headers['retry-after'] }).toEqual({
      status: 503,
      retry: '5',
    });
  });
});

describe('TC-ET-035: a record that cannot be written', () => {
  it('the publish is 503 and delivers nothing; the subscribe is 503 and opens no stream', async () => {
    const store = ingestStore(db);
    const g = await fresh({ store });
    await g.listen();
    const a = await agentWith(g, PUBLISHER);
    const b = await agentWith(g, SUBSCRIBER);
    const c = await agentWith(g, SUBSCRIBER);
    const watcher = await subscribe(g, b);
    // Warm every cache C and A need, then take the store away.
    expect((await publish(g, a)).status).toBe(202);
    const warm = await subscribe(g, c);
    await flush(g);
    await watcher.until(() => watcher.deliveries().length === 1);
    warm.destroy();
    await new Promise((r) => setTimeout(r, 50));
    await store.close();
    const p = await publish(g, a);
    expect({ status: p.status, code: p.body?.code, retry: p.headers['retry-after'] }).toEqual({
      status: 503,
      code: 'unavailable',
      retry: '5',
    });
    const before = g.runtime.streams.size;
    const s = await subscribe(g, await credential(g, c.agent, { cid: c.cid }));
    expect(s.status).toBe(503);
    expect(g.runtime.streams.size).toBe(before);
    await flush(g);
    expect(watcher.deliveries()).toHaveLength(1);
    expect(g.log.named('store.unavailable').length).toBeGreaterThanOrEqual(2);
    s.destroy();
    watcher.destroy();
  });
});
