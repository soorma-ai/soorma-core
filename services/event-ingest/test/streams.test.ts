// SPDX-License-Identifier: FSL-1.1-ALv2
//
// A stream's life, on real connections with injected time (NP-ET-12):
// TC-ET-016 (expiry), 017 (revocation within B, then the sweep), 029
// (revocation unreadable), 054 (heartbeat), 060 (shutdown), 062 to 064 and
// 048 (superseding), 039 (nothing crosses environments).
import { afterAll, afterEach, beforeAll, describe, expect, it } from 'vitest';
import {
  testEnvDatabase,
  type TestEnvDatabase,
} from '../../../packages/env-store/test/harness/database.ts';
import { createInProcessChannel, type Channel } from '../src/channel/channel.ts';
import { drain } from '../src/main.ts';
import {
  agentWith,
  credential,
  E,
  E2,
  flush,
  ingest,
  ingestStore,
  MINUTE,
  publish,
  PUBLISHER,
  registered,
  revokeAgent,
  revokeCredential,
  subscribe,
  SUBSCRIBER,
  TestClock,
  type Ingest,
  type SseClient,
} from './support.ts';

let db: TestEnvDatabase;
const open: Ingest[] = [];
const streams: SseClient[] = [];

beforeAll(async () => {
  db = await testEnvDatabase();
});
afterEach(async () => {
  for (const s of streams.splice(0)) s.destroy();
  for (const g of open.splice(0)) await g.close();
});
afterAll(async () => {
  await db?.drop();
});

async function fresh(options: Parameters<typeof ingest>[1] = {}): Promise<Ingest> {
  const g = await ingest(db, options);
  await g.listen();
  open.push(g);
  return g;
}

async function sub(g: Ingest, c: Parameters<typeof subscribe>[1]): Promise<SseClient> {
  const s = await subscribe(g, c);
  expect(s.status).toBe(200);
  streams.push(s);
  return s;
}

/** Advances in steps of one second, letting each sweep's read finish. */
async function advance(g: Ingest, ms: number): Promise<void> {
  for (let left = ms; left > 0; left -= 1000) {
    g.scheduler.advance(Math.min(1000, left));
    await flush(g);
  }
}

describe('TC-ET-016: a stream ends at its credential’s exp exactly', () => {
  it('end credential_expired at exp, and a later publish is not delivered', async () => {
    const g = await fresh();
    const a = await agentWith(g, PUBLISHER);
    const b = await agentWith(g, SUBSCRIBER);
    const short = await credential(g, b.agent, { lifetimeMs: 2 * MINUTE });
    const s = await sub(g, short);
    await advance(g, 2 * MINUTE - 1000);
    g.scheduler.advance(999);
    await flush(g);
    expect(s.ended()).toBeUndefined();
    g.scheduler.advance(1);
    await flush(g);
    await s.until(() => s.ended() !== undefined);
    expect(s.ended()).toEqual({ code: 'credential_expired' });
    await publish(g, a);
    await flush(g);
    expect(s.deliveries()).toEqual([]);
    expect(g.log.named('stream.ended').at(-1)).toMatchObject({ code: 'credential_expired' });
  });
});

describe('TC-ET-017 and 031: revocation reaches an open stream within B, at either granularity', () => {
  it('deliveries until revocation + B, none after; end credential_refused within R', async () => {
    const g = await fresh();
    const a = await agentWith(g, PUBLISHER);
    const b1 = await agentWith(g, SUBSCRIBER);
    const b2 = await agentWith(g, SUBSCRIBER);
    const s1 = await sub(g, b1);
    const s2 = await sub(g, b2);
    // Both answers were read at 0. Revoked at 1 s: the lineage, and the other agent.
    g.scheduler.advance(1000);
    await revokeCredential(g, b1);
    await revokeAgent(g, b2.agent);
    await advance(g, 58_000);
    // At 59 s the cached not_revoked (read at 0) is younger than B: delivered.
    expect((await publish(g, a, { at: 59 })).status).toBe(202);
    await flush(g);
    await s1.until(() => s1.deliveries().length === 1);
    await s2.until(() => s2.deliveries().length === 1);
    // At 60 s the sweep re-reads: revoked. No Delivery after this.
    await advance(g, 1000);
    await s1.until(() => s1.ended() !== undefined);
    await s2.until(() => s2.ended() !== undefined);
    expect(s1.ended()).toEqual({ code: 'credential_refused' });
    expect(s2.ended()).toEqual({ code: 'credential_refused' });
    expect(s1.events.at(-1)!.data).toBe(s2.events.at(-1)!.data);
    const revoked = g.log.named('stream.revoked').map((e) => e.reason);
    expect(revoked.sort()).toEqual(['agent_revoked', 'credential_revoked']);
  });
});

describe('TC-ET-029: revocation unreadable: served within B, then denied', () => {
  it('a store down: 503 at the record within B, 503 at step 4 past B; the stream ends unavailable', async () => {
    const store = ingestStore(db);
    const g = await fresh({ store });
    const a = await agentWith(g, PUBLISHER);
    const b = await agentWith(g, SUBSCRIBER);
    const s = await sub(g, b);
    expect((await publish(g, a, { warm: true })).status).toBe(202);
    await store.close();
    await advance(g, 30_000);
    const within = await publish(g, a);
    expect({ status: within.status, retry: within.headers['retry-after'] }).toEqual({
      status: 503,
      retry: '5',
    });
    expect(s.ended()).toBeUndefined();
    await advance(g, 30_000);
    const past = await publish(g, a);
    expect(past.status).toBe(503);
    await s.until(() => s.ended() !== undefined);
    expect(s.ended()).toEqual({ code: 'unavailable' });
    expect(g.log.named('store.unavailable').length).toBeGreaterThanOrEqual(2);
  });
});

describe('TC-ET-054: a heartbeat after 15 seconds of silence', () => {
  it('none before 15 s; one at 15 s; a delivery re-arms it', async () => {
    const g = await fresh();
    const a = await agentWith(g, PUBLISHER);
    const s = await sub(g, await agentWith(g, SUBSCRIBER));
    await advance(g, 14_000);
    g.scheduler.advance(900);
    await flush(g);
    expect(s.comments).toBe(0);
    g.scheduler.advance(100);
    await flush(g);
    await s.until(() => s.comments === 1);
    await advance(g, 5_000);
    await publish(g, a);
    await flush(g);
    await s.until(() => s.deliveries().length === 1);
    await advance(g, 14_000);
    expect(s.comments).toBe(1);
    await advance(g, 1_000);
    await s.until(() => s.comments === 2);
  });
});

describe('TC-ET-060: shutdown ends every stream with unavailable', () => {
  it('each stream ends unavailable; a new request is not accepted', async () => {
    const g = await ingest(db);
    await g.listen();
    const s1 = await subscribe(g, await agentWith(g, SUBSCRIBER));
    const s2 = await subscribe(g, await agentWith(g, SUBSCRIBER));
    const a = await agentWith(g, PUBLISHER);
    const started = Date.now();
    await drain(g.edge, g.runtime, 5_000);
    for (const s of [s1, s2]) {
      await s.until(() => s.closed);
      expect(s.ended()).toEqual({ code: 'unavailable' });
    }
    expect(Date.now() - started).toBeLessThan(5_000);
    await expect(fetch(`${g.url()}/events`, { method: 'POST' })).rejects.toThrow();
    void a;
    await g.owner.end();
    await g.store.close();
  });
});

describe('superseding (D-ET-05; BR-FO)', () => {
  it('TC-ET-063: on one instance, the later subscribe of a lineage supersedes', async () => {
    const g = await fresh();
    const a = await agentWith(g, PUBLISHER);
    const b = await agentWith(g, SUBSCRIBER);
    const first = await sub(g, b);
    // A renewal: the same lineage (cid), a new token.
    const renewed = await credential(g, b.agent, { cid: b.cid });
    const second = await sub(g, renewed);
    await first.until(() => first.ended() !== undefined);
    expect(first.ended()).toEqual({ code: 'superseded' });
    await publish(g, a);
    await flush(g);
    await second.until(() => second.deliveries().length === 1);
    expect(g.runtime.streams.size).toBe(1);
  });

  it('TC-ET-064: on two instances at the same openedAt, the larger id survives', async () => {
    const channel = createInProcessChannel();
    const x = await fresh({ channel });
    const y = await fresh({ channel, keys: x.keys, clock: x.clock });
    const b = await agentWith(x, SUBSCRIBER);
    const keys: { at: string; openedAt: number; id: string }[] = [];
    for (const [at, g] of [
      ['x', x],
      ['y', y],
    ] as const) {
      const original = g.runtime.orderKey.bind(g.runtime);
      (g.runtime as { orderKey: typeof original }).orderKey = () => {
        const k = original();
        keys.push({ at, ...k });
        return k;
      };
    }
    // The same clock reading on both instances, and one lineage.
    const [sx, sy] = await Promise.all([sub(x, b), sub(y, b)]);
    await flush(x);
    await flush(y);
    await Promise.race([
      sx.until(() => sx.ended() !== undefined),
      sy.until(() => sy.ended() !== undefined),
    ]);
    expect(keys).toHaveLength(2);
    expect(keys[0]!.openedAt).toBe(keys[1]!.openedAt);
    const winner = keys.reduce((a, k) => (k.id > a.id ? k : a));
    const [kept, lost] = winner.at === 'x' ? [sx, sy] : [sy, sx];
    expect(kept.ended()).toBeUndefined();
    expect(lost.ended()).toEqual({ code: 'superseded' });
    expect(x.runtime.streams.size + y.runtime.streams.size).toBe(1);
  });

  it('BR-FO-07: with Y’s clock behind X’s, a later subscribe at Y ends itself, and one survives', async () => {
    const channel = createInProcessChannel();
    const x = await fresh({ channel });
    const behind = new TestClock();
    behind.ms = x.clock.ms - 1000;
    const y = await fresh({ channel, keys: x.keys, clock: behind });
    const b = await agentWith(x, SUBSCRIBER);
    const sx = await sub(x, b);
    // Later in real time, but ordered earlier: Y's clock reads one second less.
    const sy = await sub(y, await credential(y, b.agent, { cid: b.cid }));
    await sy.until(() => sy.ended() !== undefined);
    expect(sy.ended()).toEqual({ code: 'superseded' });
    expect(sx.ended()).toBeUndefined();
    expect(x.runtime.streams.size + y.runtime.streams.size).toBe(1);
  });

  it('on one instance, two subscribes in one millisecond: the later one survives (D-CG-ET-30)', async () => {
    const g = await fresh();
    const b = await agentWith(g, SUBSCRIBER);
    const keys: { openedAt: number; id: string }[] = [];
    const original = g.runtime.orderKey.bind(g.runtime);
    (g.runtime as { orderKey: typeof original }).orderKey = () => {
      const k = original();
      keys.push(k);
      return k;
    };
    const first = await sub(g, b);
    const second = await sub(g, b);
    await first.until(() => first.ended() !== undefined);
    expect(first.ended()).toEqual({ code: 'superseded' });
    expect(second.ended()).toBeUndefined();
    // The clock did not move: the instance's own order still separates them.
    expect(keys[1]!.openedAt).toBe(keys[0]!.openedAt + 1);
    expect(g.runtime.streams.list()).toHaveLength(1);
  });

  it('TC-ET-062: across two instances on one channel; a lost supersede leaves both until exp', async () => {
    const channel = createInProcessChannel();
    const x = await fresh({ channel });
    const y = await fresh({ channel, keys: x.keys, clock: x.clock });
    const a = await agentWith(x, PUBLISHER);
    const b = await agentWith(x, SUBSCRIBER);
    const sx = await sub(x, b);
    x.scheduler.advance(1);
    const sy = await sub(y, await credential(y, b.agent, { cid: b.cid }));
    await sx.until(() => sx.ended() !== undefined);
    expect(sx.ended()).toEqual({ code: 'superseded' });
    await publish(x, a);
    await flush(x);
    await flush(y);
    await sy.until(() => sy.deliveries().length === 1);

    // The channel made to lose `supersede`: both stay open until the earlier exp.
    const lossy: Channel = {
      publish: (m) => (m.kind === 'supersede' ? undefined : channel.publish(m)),
      subscribe: (h) => channel.subscribe(h),
    };
    const p = await fresh({ channel: lossy });
    const q = await fresh({ channel: lossy, keys: p.keys, clock: p.clock });
    const c = await agentWith(p, SUBSCRIBER);
    const early = await credential(p, c.agent, { lifetimeMs: 5 * MINUTE });
    const sp = await sub(p, early);
    p.scheduler.advance(1);
    const sq = await sub(q, await credential(q, c.agent, { cid: early.cid }));
    await flush(p);
    expect(sp.ended()).toBeUndefined();
    expect(sq.ended()).toBeUndefined();
    await advance(p, 5 * MINUTE);
    await sp.until(() => sp.ended() !== undefined);
    expect(sp.ended()).toEqual({ code: 'credential_expired' });
    expect(sq.ended()).toBeUndefined();
  });

  it('TC-ET-048: two instances asserting one name each hold their own stream', async () => {
    const g = await fresh();
    const a = await agentWith(g, PUBLISHER);
    const b = await agentWith(g, SUBSCRIBER);
    const twin = await credential(g, b.agent, { instance: b.instance });
    const s1 = await sub(g, b);
    const s2 = await sub(g, twin);
    await publish(g, a);
    await flush(g);
    for (const s of [s1, s2]) await s.until(() => s.deliveries().length === 1);
    expect(s1.ended()).toBeUndefined();
    expect(s2.ended()).toBeUndefined();
  });
});

describe('TC-ET-039: nothing of E2 is delivered or superseded at E', () => {
  it('each environment’s stream receives its own Deliveries; E2’s supersede leaves E’s stream', async () => {
    const e = await fresh();
    const e2 = await fresh({ environment: E2, keys: e.keys });
    const a = await agentWith(e, PUBLISHER);
    const a2 = await agentWith(e2, PUBLISHER, { env: E2 });
    const b = await agentWith(e, SUBSCRIBER);
    const sE = await sub(e, b);
    // The same agent name registered in E2, with a credential of the same cid value.
    await registered(e2, b.agent, { env: E2, standing: SUBSCRIBER });
    const sE2 = await sub(e2, await credential(e2, b.agent, { cid: b.cid, env: E2 }));
    await publish(e, a, { from: E.environment });
    await publish(e2, a2, { from: E2.environment });
    await flush(e);
    await flush(e2);
    await sE.until(() => sE.deliveries().length === 1);
    await sE2.until(() => sE2.deliveries().length === 1);
    expect(sE.deliveries()[0]!.payload).toEqual({ from: 'e' });
    expect(sE2.deliveries()[0]!.payload).toEqual({ from: 'e2' });
    expect(sE.ended()).toBeUndefined();
    expect(sE2.ended()).toBeUndefined();
  });
});
