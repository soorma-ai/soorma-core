// SPDX-License-Identifier: FSL-1.1-ALv2
//
// P3's registration checks (U5 D-AR-07, 10; NP-AR-05): readHumanAuthority
// reads once and decides through evaluateHeld; checkRegistrationRequest
// decides the human-only class and the declaration within the standing set.
import { createPolicyDecision, inMemoryGrantSource } from '@soorma/policy-decision';
import type { PermissionSet, PolicyDecision, PrincipalRef } from '@soorma/policy-decision-seam';
import { describe, expect, it } from 'vitest';
import { checkRegistrationRequest, evaluateHeld, readHumanAuthority } from '../src/index.ts';

const E = { organization: 'o1', project: 'p1', environment: 'e' };
const h = (principal: string): PrincipalRef => ({ kind: 'human', principal });
const HELD = ['event:subscribe', 'grant:human', 'agent:register', 'event:publish', 'human:manage'];
const policy = createPolicyDecision({
  environment: E,
  grants: inMemoryGrantSource([[h('h'), HELD]]),
});

function counting(inner: PolicyDecision): PolicyDecision & { reads: number } {
  const c = {
    reads: 0,
    grantedSet: (p: PrincipalRef, env: typeof E): Promise<PermissionSet> => {
      c.reads += 1;
      return inner.grantedSet(p, env);
    },
    contains: (a: PermissionSet, b: PermissionSet): boolean => inner.contains(a, b),
  };
  return c;
}

describe('TC-AR-038 (P3): readHumanAuthority reads the held set once', () => {
  it('serves agent:register, the ceiling, and the Admin test from one read', async () => {
    const c = counting(policy);
    const auth = await readHumanAuthority({ policy: c, environment: E, principal: 'h' });
    expect(auth.allows(['agent:register'])).toBe(true);
    expect(auth.allows(['event:publish', 'event:subscribe'])).toBe(true);
    expect(auth.allows(['grant:human', 'human:manage'])).toBe(true);
    expect(auth.exceeding(['event:publish'])).toEqual([]);
    expect(c.reads).toBe(1);
  });

  it('decides exactly as evaluateHeld does over the same set', async () => {
    const auth = await readHumanAuthority({ policy, environment: E, principal: 'h' });
    const held = new Set(HELD);
    for (const required of [
      ['agent:register'],
      ['agent:retire'],
      ['event:publish', 'agent:retire'],
    ]) {
      expect(auth.allows(required)).toBe(evaluateHeld({ policy, held, required }).allowed);
    }
  });

  it('refuses an empty required set, as evaluateHeld does', async () => {
    const auth = await readHumanAuthority({ policy, environment: E, principal: 'h' });
    expect(() => auth.allows([])).toThrow(RangeError);
  });
});

describe('TC-AR-002, 029 (P3): the snapshot and the ceiling', () => {
  it('snapshots the whole held set, sorted, human-only included, frozen', async () => {
    const auth = await readHumanAuthority({ policy, environment: E, principal: 'h' });
    expect(auth.snapshot()).toEqual([...HELD].sort());
    expect(Object.isFrozen(auth.snapshot())).toBe(true);
    expect(Object.isFrozen(auth)).toBe(true);
  });

  it('names each standing entry not held, in request order', async () => {
    const auth = await readHumanAuthority({ policy, environment: E, principal: 'h' });
    expect(auth.exceeding(['event:publish', 'agent:retire', 'credential:revoke'])).toEqual([1, 2]);
  });

  it('a human with no grant holds nothing: everything exceeds, the snapshot is empty', async () => {
    const auth = await readHumanAuthority({ policy, environment: E, principal: 'nobody' });
    expect(auth.allows(['agent:register'])).toBe(false);
    expect(auth.exceeding(['event:publish'])).toEqual([0]);
    expect(auth.snapshot()).toEqual([]);
  });
});

describe('TC-AR-010, 011, 012, 030 (P3): checkRegistrationRequest', () => {
  it('names each human-only entry of the standing set', () => {
    const check = checkRegistrationRequest({
      policy,
      standing: ['grant:human', 'event:publish', 'agent:delegate', 'human:manage'],
      declared: [],
    });
    expect(check.humanOnly).toEqual([0, 2, 3]);
    expect(check.outsideStanding).toEqual([]);
  });

  it('names each declared entry outside the standing set; empty and equal declarations pass', () => {
    const standing = ['event:publish', 'event:subscribe'];
    expect(
      checkRegistrationRequest({ policy, standing, declared: ['event:subscribe', 'agent:retire'] })
        .outsideStanding,
    ).toEqual([1]);
    expect(checkRegistrationRequest({ policy, standing, declared: [] }).outsideStanding).toEqual(
      [],
    );
    expect(
      checkRegistrationRequest({ policy, standing, declared: standing }).outsideStanding,
    ).toEqual([]);
  });

  it('reads no state', () => {
    const c = counting(policy);
    checkRegistrationRequest({ policy: c, standing: ['grant:human'], declared: ['x:y'] });
    expect(c.reads).toBe(0);
  });
});
