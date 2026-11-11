// SPDX-License-Identifier: FSL-1.1-ALv2
// TC-AE-034: one read per request, and the cache's rules (NP-04; NFR-AE-08
// to 15, 22; BR-AU-09; BR-OR-06; BR-SEAM-04; L1-11, 14, 15, 30; I1). The
// bound is 60 s for these tests.
import { readFileSync } from 'node:fs';
import { createPolicyDecision } from '@soorma/policy-decision';
import { describe, expect, it } from 'vitest';
import {
  cacheKey,
  createCachingAgentFacts,
  createEnvelopeAdmission,
  requestGrantSource,
  requestSnapshot,
  type GrantSource,
} from '../src/index.ts';
import {
  admissionE,
  BOUND_MS,
  CollectingLog,
  draft,
  E,
  envelope,
  Facts,
  request,
  ringE,
  sealed,
  TestClock,
} from './support.ts';

const PUB = { standing: ['event:publish'] };
const chain31 = Array.from({ length: 31 }, (_, i) => `u${i}`);
const forward31 = () => draft({ inbound: sealed(envelope(chain31)) });
const all = Object.fromEntries([...chain31, 'b'].map((a) => [a, PUB]));

describe('TC-AE-034: one read per request, and the cache’s rules', () => {
  it('1: refusals at steps 5, 6, 7 and 8 make no call', async () => {
    const { admission, facts } = admissionE(all);
    await admission.admit(request('b', []));
    await admission.admit(request('b', draft({ scope: {} })));
    await admission.admit(
      request('b', draft({ inbound: { envelope: envelope(['a']), seal: 'v1.k1.x' } })),
    );
    await admission.admit(request('b', draft({ inbound: sealed(envelope([...chain31, 'z'])) })));
    expect(facts.calls).toEqual([]);
  });

  it('2 to 4: one call for 32 agents cold; none warm at 59 s; one again at 60 s', async () => {
    const { admission, facts, clock } = admissionE(all);
    expect('admitted' in (await admission.admit(request('b', forward31())))).toBe(true);
    expect(facts.calls).toHaveLength(1);
    expect(facts.calls[0]!.agents).toEqual(['b', ...chain31]);
    clock.t = 59_000;
    await admission.admit(request('b', forward31()));
    expect(facts.calls).toHaveLength(1);
    clock.t = 60_000;
    await admission.admit(request('b', forward31()));
    expect(facts.calls).toHaveLength(2);
  });

  it('5: the TTL runs from when the read was ISSUED, not when it completed', async () => {
    const facts = new Facts({ b: PUB });
    const clock = new TestClock();
    const cache = createCachingAgentFacts(facts, { ttl: BOUND_MS, clock });
    clock.t = 1_000;
    let release!: () => void;
    facts.gate = new Promise((r) => (release = r));
    const read = cache.load(E, ['b']);
    clock.t = 11_000; // the read completes at t + 10 s
    release();
    await read;
    facts.gate = undefined;
    clock.t = 1_000 + 59_000;
    await cache.load(E, ['b']);
    expect(facts.calls).toHaveLength(1);
    clock.t = 1_000 + 60_000;
    await cache.load(E, ['b']);
    expect(facts.calls).toHaveLength(2);
  });

  it('6: a failed read is unavailable, Retry-After 1; nothing from it is cached', async () => {
    const { admission, facts, log } = admissionE({ b: PUB });
    facts.failing = true;
    expect(await admission.admit(request('b'))).toEqual({
      refused: { code: 'unavailable', retryAfterSeconds: 1 },
    });
    expect(log.events[0]!.reason).toBe('agent_facts_read_failed');
    facts.failing = false;
    expect('admitted' in (await admission.admit(request('b')))).toBe(true);
    expect(facts.calls).toHaveLength(2);
  });

  it('7: an outage: entries within the bound are served; after it, unavailable', async () => {
    const { admission, facts, clock } = admissionE({ b: PUB });
    await admission.admit(request('b'));
    facts.failing = true;
    clock.t = 30_000;
    expect('admitted' in (await admission.admit(request('b')))).toBe(true);
    clock.t = 60_000;
    expect(await admission.admit(request('b'))).toEqual({
      refused: { code: 'unavailable', retryAfterSeconds: 1 },
    });
  });

  it('8: 20 concurrent requests for one cold agent make one call; a failed one fails all 20, caching nothing', async () => {
    const facts = new Facts({ b: PUB });
    const cache = createCachingAgentFacts(facts, { ttl: BOUND_MS, clock: new TestClock() });
    let release!: () => void;
    facts.gate = new Promise((r) => (release = r));
    const reads = Array.from({ length: 20 }, () => cache.load(E, ['b']));
    release();
    const results = await Promise.all(reads);
    expect(facts.calls).toHaveLength(1);
    expect(results.every((m) => m.get('b') !== undefined)).toBe(true);

    const failing = new Facts({ c: PUB });
    const cold = createCachingAgentFacts(failing, { ttl: BOUND_MS, clock: new TestClock() });
    failing.failing = true;
    let open!: () => void;
    failing.gate = new Promise((r) => (open = r));
    const twenty = Array.from({ length: 20 }, () => cold.load(E, ['c']));
    open();
    const settled = await Promise.allSettled(twenty);
    expect(failing.calls).toHaveLength(1);
    expect(settled.every((s) => s.status === 'rejected')).toBe(true);
    expect(cold.size()).toBe(0);
  });

  it('9: at most 4096 entries; the least recently used is evicted and read again', async () => {
    const agents = Array.from({ length: 4097 }, (_, i) => `x${i}`);
    const facts = new Facts(Object.fromEntries(agents.map((a) => [a, PUB])));
    const cache = createCachingAgentFacts(facts, { ttl: BOUND_MS, clock: new TestClock() });
    await cache.load(E, agents.slice(0, 4096));
    await cache.load(E, ['x0']); // x0 is now the most recently used; x1 the least
    expect(facts.calls).toHaveLength(1);
    await cache.load(E, ['x4096']);
    expect(cache.size()).toBe(4096);
    await cache.load(E, ['x0']);
    expect(facts.calls).toHaveLength(2);
    await cache.load(E, ['x1']);
    expect(facts.calls).toHaveLength(3);
    expect(facts.calls[2]!.agents).toEqual(['x1']);
    expect(cache.size()).toBe(4096);
  });

  it('not found is never cached: a registration added after is seen at once (NFR-AE-12)', async () => {
    const { admission, facts } = admissionE({ b: PUB });
    const fwd = draft({ inbound: sealed(envelope(['x'])) });
    expect(await admission.admit(request('b', fwd))).toEqual({ refused: { code: 'forbidden' } });
    facts.set('x', PUB);
    expect('admitted' in (await admission.admit(request('b', fwd)))).toBe(true);
  });

  it('10: a human principal’s grantedSet goes to humans, never to facts or the cache', async () => {
    const facts = new Facts({ b: PUB });
    const humansCalls: unknown[] = [];
    const humans: GrantSource = {
      grantsOf: (p) => {
        humansCalls.push(p);
        return Promise.resolve(['grant:human']);
      },
    };
    const snapshot = requestSnapshot(['b'], await facts.load(E, ['b']));
    const policy = createPolicyDecision({
      environment: E,
      grants: requestGrantSource(snapshot, humans),
    });
    facts.calls.length = 0;
    expect(await policy.grantedSet({ kind: 'human', principal: 'h@example.com' }, E)).toEqual(
      new Set(['grant:human']),
    );
    expect(humansCalls).toHaveLength(1);
    expect(facts.calls).toEqual([]);
  });

  it('11: within a request, P11’s agent GrantSource makes no call: it reads the snapshot', async () => {
    const { admission, facts } = admissionE(all);
    await admission.admit(request('b', forward31()));
    expect(facts.calls).toHaveLength(1);
    const snapshot = requestSnapshot(['b'], new Map());
    await expect(
      requestGrantSource(snapshot, { grantsOf: () => Promise.resolve([]) }).grantsOf(
        { kind: 'agent', agent: 'nobody' },
        E,
      ),
    ).rejects.toThrow('defect');
  });

  it('12: a cache key carries organization, project, environment, and agent (I1)', () => {
    const key = cacheKey(E, 'b');
    for (const part of ['o1', 'p1', 'e', 'b']) expect(JSON.parse(key)).toContain(part);
    expect(cacheKey({ ...E, environment: 'e2' }, 'b')).not.toBe(key);
    expect(cacheKey({ ...E, project: 'p2' }, 'b')).not.toBe(key);
  });

  it('12: one environment’s entries are never served for another', async () => {
    const facts = new Facts({ b: PUB });
    const cache = createCachingAgentFacts(facts, { ttl: BOUND_MS, clock: new TestClock() });
    await cache.load(E, ['b']);
    await cache.load({ ...E, environment: 'e2' }, ['b']);
    expect(facts.calls).toHaveLength(2);
  });

  it('13: no configuration schema has a cache-lifetime setting: the lifetime is the propagation bound', () => {
    const schema = readFileSync(
      new URL('../../config/schema/tenancy.schema.json', import.meta.url),
      'utf8',
    );
    const keys = [...schema.matchAll(/"([A-Za-z]+)"\s*:/g)].map((m) => m[1]!.toLowerCase());
    expect(keys.filter((k) => /ttl|cache|lifetime/.test(k))).toEqual([]);
  });

  it('NFR-AE-22: two separately built entry points give the same results; only the cache keeps state', async () => {
    const facts = new Facts(all);
    const build = () =>
      createEnvelopeAdmission({
        acceptedVersions: ['0.1.0'],
        scope: E,
        keyRing: ringE,
        facts: createCachingAgentFacts(facts, { ttl: BOUND_MS, clock: new TestClock() }),
        policyFactory: createPolicyDecision,
        humanGrants: { grantsOf: () => Promise.resolve([]) },
        securityLog: new CollectingLog(),
      });
    const one = build();
    const two = build();
    const requests = [
      request('b'),
      request('b', forward31()),
      request('b', draft({ foo: 1 })),
      request('zz'),
    ];
    for (let i = 0; i < 50; i++) {
      const r = requests[i % requests.length]!;
      expect(await one.admit(r)).toEqual(await two.admit(r));
    }
  });
});
