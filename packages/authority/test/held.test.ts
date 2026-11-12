// SPDX-License-Identifier: FSL-1.1-ALv2
//
// evaluateHeld, the one evaluator of a human's held set (U5 D-AR-07), over
// P11's containment. U4's evaluateHuman tests (human.test.ts) are unchanged
// and exercise it through evaluateHuman.
import { createPolicyDecision, inMemoryGrantSource } from '@soorma/policy-decision';
import { describe, expect, it } from 'vitest';
import { evaluateHeld, evaluateHuman } from '../src/index.ts';

const E = { organization: 'o1', project: 'p1', environment: 'e' };
const policy = createPolicyDecision({ environment: E, grants: inMemoryGrantSource([]) });
const held = new Set(['agent:register', 'event:publish', 'grant:human']);

describe('TC-AR-038 (P3): evaluateHeld is the one evaluator of a held set', () => {
  it('allows a set the held set contains, equality included', () => {
    expect(evaluateHeld({ policy, held, required: ['agent:register'] })).toEqual({ allowed: true });
    expect(evaluateHeld({ policy, held, required: [...held] })).toEqual({ allowed: true });
  });

  it('denies a set with any member not held, and denies everything for an empty held set', () => {
    expect(evaluateHeld({ policy, held, required: ['agent:register', 'agent:retire'] })).toEqual({
      allowed: false,
    });
    expect(evaluateHeld({ policy, held: new Set(), required: ['event:publish'] })).toEqual({
      allowed: false,
    });
  });

  it('refuses an empty required set', () => {
    expect(() => evaluateHeld({ policy, held, required: [] })).toThrow(RangeError);
  });

  it('is what evaluateHuman decides with: the same answer for the same set', async () => {
    const counting = {
      reads: 0,
      grantedSet: () => {
        counting.reads += 1;
        return Promise.resolve(held);
      },
      contains: (a: ReadonlySet<string>, b: ReadonlySet<string>) => policy.contains(a, b),
    };
    const viaHuman = await evaluateHuman({
      policy: counting,
      environment: E,
      principal: 'h',
      required: ['grant:human'],
    });
    expect(viaHuman).toEqual(evaluateHeld({ policy, held, required: ['grant:human'] }));
    expect(counting.reads).toBe(1);
  });
});
