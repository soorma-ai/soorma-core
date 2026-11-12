// SPDX-License-Identifier: FSL-1.1-ALv2
// The fail-closed revocation cache (U6 D-AC-18; BR-RC; NP-AC-05; NFR-AC-01, 15):
// TC-AC-054 (B = 60 s, its timeline across an outage), TC-AC-015 (the P5
// half: a revocation takes effect within B), TC-AC-065 (bounded, misses
// shared, failures never cached, eviction never admits), TC-AC-034 (the key
// includes E). Injected clock and source; the direct source is tested in
// packages/env-store/test/agent-credentials.test.ts (TC-AC-078). The cache is
// wired at S4 by U7.
import { UnavailableError, type Clock } from '@soorma/service-kit';
import { describe, expect, it } from 'vitest';
import {
  createRevocationCache,
  PROPAGATION_BOUND_MS,
  type RevocationAnswer,
  type RevocationSource,
  type RevocationTarget,
} from '../src/index.ts';

class TestClock implements Clock {
  ms = Date.parse('2026-11-12T08:00:00Z');
  now(): Date {
    return new Date(this.ms);
  }
  advance(ms: number): void {
    this.ms += ms;
  }
}

const E = { organization: 'o1', project: 'p1', environment: 'e' };
const E2 = { organization: 'o1', project: 'p1', environment: 'e2' };
const c1: RevocationTarget = { environment: E, cid: 'c1', agent: 'a' };

/** A source whose answers and availability the test sets, counting reads. */
class StubSource implements RevocationSource {
  reads = 0;
  down = false;
  revoked = new Set<string>();
  gate: Promise<void> | undefined;
  async isRevoked(t: RevocationTarget): Promise<RevocationAnswer> {
    this.reads++;
    if (this.gate) await this.gate;
    if (this.down) throw new Error('store down');
    const key = `${t.environment.environment}/${t.cid ?? ''}/${t.agent}`;
    return this.revoked.has(key) || this.revoked.has(`${t.environment.environment}//${t.agent}`)
      ? 'revoked'
      : 'not_revoked';
  }
}

function setup(max?: number) {
  const clock = new TestClock();
  const source = new StubSource();
  const cache = createRevocationCache(source, { ttl: PROPAGATION_BOUND_MS, clock, max });
  return { clock, source, cache };
}

describe('TC-AC-054: B is 60 s from the one constant, and past it with the store down the answer is deny', () => {
  it('a not-revoked answer is served at 59.999 s and re-read at 60 s', async () => {
    const { clock, source, cache } = setup();
    expect(await cache.isRevoked(c1)).toBe('not_revoked');
    clock.advance(59_999);
    expect(await cache.isRevoked(c1)).toBe('not_revoked');
    expect(source.reads).toBe(1);
    clock.advance(1);
    expect(await cache.isRevoked(c1)).toBe('not_revoked');
    expect(source.reads).toBe(2);
  });

  it('with the store down: served at 59.999 s; at 60 s unavailable (deny)', async () => {
    const { clock, source, cache } = setup();
    await cache.isRevoked(c1);
    source.down = true;
    clock.advance(59_999);
    expect(await cache.isRevoked(c1)).toBe('not_revoked');
    clock.advance(1);
    await expect(cache.isRevoked(c1)).rejects.toBeInstanceOf(UnavailableError);
  });

  it('the business-logic model §5 timeline, at the real B of 60 s', async () => {
    const { clock, source, cache } = setup();
    expect(await cache.isRevoked(c1)).toBe('not_revoked'); // 0 s: read, cached
    clock.advance(50_000);
    source.down = true;
    expect(await cache.isRevoked(c1)).toBe('not_revoked'); // 50 s: an outage is invisible
    clock.advance(10_000);
    await expect(cache.isRevoked(c1)).rejects.toBeInstanceOf(UnavailableError); // 60 s: deny
    clock.advance(20_000);
    source.down = false;
    expect(await cache.isRevoked(c1)).toBe('not_revoked'); // 80 s: read again, cached
    source.revoked.add('e/c1/a'); // revoked at 80 s, inside the cached answer's life
    clock.advance(59_999);
    expect(await cache.isRevoked(c1)).toBe('not_revoked'); // 139.999 s: still within B
    clock.advance(1);
    expect(await cache.isRevoked(c1)).toBe('revoked'); // 140 s: re-read, refused from now on
  });
});

describe('TC-AC-015 (the P5 half): a revocation takes effect within B, and never later', () => {
  it('seeded at 45 s while a not-revoked answer read at 40 s is cached: revoked by 100 s', async () => {
    const { clock, source, cache } = setup();
    clock.advance(40_000);
    expect(await cache.isRevoked(c1)).toBe('not_revoked');
    clock.advance(5_000);
    source.revoked.add('e/c1/a');
    clock.advance(54_999); // 99.999 s: the answer read at 40 s is 59.999 s old
    expect(await cache.isRevoked(c1)).toBe('not_revoked');
    clock.advance(1); // 100 s: within 60 s of the revocation (at 45 s)
    expect(await cache.isRevoked(c1)).toBe('revoked');
  });

  it('a revoked answer is terminal: kept with the store down, and long past B', async () => {
    const { clock, source, cache } = setup();
    source.revoked.add('e//a');
    expect(await cache.isRevoked(c1)).toBe('revoked');
    source.down = true;
    clock.advance(10 * PROPAGATION_BOUND_MS);
    expect(await cache.isRevoked(c1)).toBe('revoked');
  });
});

describe('TC-AC-065: bounded, misses shared, failures never cached, eviction never admits', () => {
  it('concurrent misses for one key share one read', async () => {
    const { source, cache } = setup();
    let open!: () => void;
    source.gate = new Promise((r) => (open = r));
    const asks = Array.from({ length: 10 }, () => cache.isRevoked(c1));
    open();
    expect(await Promise.all(asks)).toEqual(Array(10).fill('not_revoked'));
    expect(source.reads).toBe(1);
  });

  it('a failed read is not cached: the next ask reads again', async () => {
    const { source, cache } = setup();
    source.down = true;
    await expect(cache.isRevoked(c1)).rejects.toBeInstanceOf(UnavailableError);
    source.down = false;
    expect(await cache.isRevoked(c1)).toBe('not_revoked');
    expect(source.reads).toBe(2);
  });

  it('at the bound the oldest is evicted, and an evicted revoked target re-reads as revoked', async () => {
    const { source, cache } = setup(3);
    source.revoked.add('e/c0/a');
    const t = (n: number): RevocationTarget => ({ environment: E, cid: `c${n}`, agent: 'a' });
    expect(await cache.isRevoked(t(0))).toBe('revoked');
    for (const n of [1, 2, 3]) await cache.isRevoked(t(n));
    expect(cache.size()).toBe(3);
    const before = source.reads;
    expect(await cache.isRevoked(t(0))).toBe('revoked'); // evicted, so re-read
    expect(source.reads).toBe(before + 1);
  });

  it('the default bound is 16,384 entries', async () => {
    const { cache } = setup();
    for (let n = 0; n < 16_385; n++)
      await cache.isRevoked({ environment: E, cid: `c${n}`, agent: 'a' });
    expect(cache.size()).toBe(16_384);
  });
});

describe('TC-AC-034: the cache key includes the environment', () => {
  it("E2's revoked answer is never served for E", async () => {
    const { source, cache } = setup();
    source.revoked.add('e2/c1/a');
    expect(await cache.isRevoked({ environment: E2, cid: 'c1', agent: 'a' })).toBe('revoked');
    expect(await cache.isRevoked(c1)).toBe('not_revoked');
    expect(source.reads).toBe(2);
  });
});
