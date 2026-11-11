// SPDX-License-Identifier: FSL-1.1-ALv2
//
// The verify-key cache (NP-EHA-03; NFR-EHA-08, 08a): the schedule, the
// on-demand limit, single flight, and S1's rotation, on injected timers and an
// injected clock.
import { generateKeyPairSync, type KeyObject } from 'node:crypto';
import { thumbprint, type Timers } from '@soorma/service-kit';
import { describe, expect, it } from 'vitest';
import { VerifyKeyCache } from '../src/verify-keys.ts';
import { CapturedLog, TestClock } from './support.ts';
import { SecurityLog } from '../src/security-log.ts';

class ManualTimers implements Timers {
  private next = 0;
  readonly pending = new Map<number, { callback: () => void; ms: number }>();
  set(callback: () => void, ms: number): unknown {
    const id = this.next++;
    this.pending.set(id, { callback, ms });
    return id;
  }
  clear(handle: unknown): void {
    this.pending.delete(handle as number);
  }
  /** Fires the scheduled refresh: the 5-minute timer. */
  async refresh(): Promise<void> {
    const due = [...this.pending.entries()].filter(([, t]) => t.ms === 5 * 60_000);
    for (const [id, t] of due) {
      this.pending.delete(id);
      t.callback();
    }
    await new Promise((r) => setImmediate(r));
  }
}

const key = (): { kid: string; key: KeyObject } => {
  const { publicKey } = generateKeyPairSync('ed25519');
  return { kid: thumbprint(publicKey), key: publicKey };
};

/** S1's published keys, as the cache fetches them. */
class Source {
  keys: { kid: string; key: KeyObject }[] = [key()];
  fail = false;
  fetches = 0;
  gate: Promise<void> | undefined;
  readonly fetch = async (): Promise<Map<string, KeyObject>> => {
    this.fetches += 1;
    if (this.gate) await this.gate;
    if (this.fail) throw new Error('S1 unavailable');
    return new Map(this.keys.map((k) => [k.kid, k.key]));
  };
}

function cache() {
  const source = new Source();
  const timers = new ManualTimers();
  const clock = new TestClock('2026-11-11T12:00:00Z');
  const log = new CapturedLog();
  const c = new VerifyKeyCache({ fetch: source.fetch, clock, timers, log: new SecurityLog(log) });
  return { source, timers, clock, log, c };
}

const settle = () => new Promise((r) => setImmediate(r));

describe('TC-EHA-061: refresh every 5 minutes; on demand at most once per 30 seconds', () => {
  it('fetches at start, without blocking, and again at each 5-minute refresh', async () => {
    const { source, timers, c } = cache();
    expect(c.hasKeys()).toBe(false);
    c.start();
    await settle();
    expect(source.fetches).toBe(1);
    expect(c.hasKeys()).toBe(true);
    await timers.refresh();
    expect(source.fetches).toBe(2);
    await timers.refresh();
    expect(source.fetches).toBe(3);
    c.stop();
  });

  it('two on-demand fetches 10 s apart make one fetch; 31 s apart, two', async () => {
    const { source, clock, c } = cache();
    await c.refetch();
    clock.advance(10);
    await c.refetch();
    expect(source.fetches).toBe(1);
    clock.advance(21);
    await c.refetch();
    expect(source.fetches).toBe(2);
  });

  it('a scheduled refresh 5 s after an on-demand fetch still runs, and does not reset the limit', async () => {
    const { source, timers, clock, c } = cache();
    c.start();
    await settle();
    clock.advance(40);
    await c.refetch();
    expect(source.fetches).toBe(2);
    clock.advance(5);
    await timers.refresh();
    expect(source.fetches).toBe(3);
    clock.advance(10); // 15 s after the on-demand fetch: still inside its limit
    await c.refetch();
    expect(source.fetches).toBe(3);
    c.stop();
  });

  it('a failed fetch keeps the keys held, and logs orglevel.unavailable', async () => {
    const { source, log, c } = cache();
    await c.fetch();
    const held = source.keys[0]!.kid;
    source.fail = true;
    await c.fetch();
    expect(c.verifyKey(held)).toBeDefined();
    expect(log.named('orglevel.unavailable').at(-1)?.code).toBe('verify_keys');
  });

  it('concurrent callers share one fetch', async () => {
    const { source, c } = cache();
    let open!: () => void;
    source.gate = new Promise((r) => (open = r));
    const all = Promise.all([c.refetch(), c.refetch(), c.fetch(), c.refetch(), c.fetch()]);
    open();
    await all;
    expect(source.fetches).toBe(1);
  });
});

describe('TC-EHA-062: a rotation at S1, with the 5-minute wait, needs no on-demand fetch', () => {
  it('a key S1 adds is held after the next refresh; a key it removes is dropped by a refresh', async () => {
    const { source, timers, c } = cache();
    c.start();
    await settle();
    const old = source.keys[0]!;
    const next = key();
    source.keys = [old, next]; // step 1: the new key is a verify key
    await timers.refresh(); // 5 minutes later
    const fetches = source.fetches;
    expect(c.verifyKey(next.kid)).toBeDefined(); // step 2's sign-ins verify
    expect(source.fetches).toBe(fetches);
    source.keys = [next]; // step 3: the old key is removed
    await timers.refresh();
    expect(c.verifyKey(old.kid)).toBeUndefined();
    c.stop();
  });
});

describe('TC-EHA-063: a refresh that failed during step 1 is covered by one on-demand fetch', () => {
  it('the new key arrives after exactly one on-demand fetch', async () => {
    const { source, timers, clock, c } = cache();
    c.start();
    await settle();
    const next = key();
    source.keys = [...source.keys, next];
    source.fail = true; // S1 restarting at step 1
    await timers.refresh();
    expect(c.verifyKey(next.kid)).toBeUndefined();
    source.fail = false;
    clock.advance(31);
    const before = source.fetches;
    await c.refetch(); // a sign-in under the new key: unknown kid
    expect(source.fetches - before).toBe(1);
    expect(c.verifyKey(next.kid)).toBeDefined();
    c.stop();
  });
});
