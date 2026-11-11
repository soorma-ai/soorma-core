// SPDX-License-Identifier: FSL-1.1-ALv2
//
// P3's human authority (U4 D-EHA-13; BR-EV-01 to 06), over P11 and an
// in-memory GrantSource.
import { createPolicyDecision, inMemoryGrantSource } from '@soorma/policy-decision';
import type { PrincipalRef } from '@soorma/policy-decision-seam';
import { describe, expect, it } from 'vitest';
import { evaluateHuman, holdsAnyGrant } from '../src/index.ts';

const E = { organization: 'o1', project: 'p1', environment: 'e' };
const h = (principal: string): PrincipalRef => ({ kind: 'human', principal });
const policy = createPolicyDecision({
  environment: E,
  grants: inMemoryGrantSource([
    [h('admin'), ['grant:human', 'human:manage']],
    [h('dev'), ['agent:register']],
  ]),
});

describe('TC-EHA-012, 008 (P3): evaluateHuman computes a human authority in one place', () => {
  it('allows a held permission, denies one not held, and denies a human with no grant', async () => {
    expect(
      await evaluateHuman({
        policy,
        environment: E,
        principal: 'admin',
        required: ['grant:human'],
      }),
    ).toEqual({ allowed: true });
    expect(
      await evaluateHuman({ policy, environment: E, principal: 'dev', required: ['grant:human'] }),
    ).toEqual({ allowed: false });
    expect(
      await evaluateHuman({
        policy,
        environment: E,
        principal: 'nobody',
        required: ['grant:human'],
      }),
    ).toEqual({ allowed: false });
  });

  it('applies no human-only refusal to a human (BR-EV-03)', async () => {
    expect(
      await evaluateHuman({
        policy,
        environment: E,
        principal: 'admin',
        required: ['human:manage'],
      }),
    ).toEqual({ allowed: true });
  });

  it('answers nothing for another environment (P11 is scoped to E)', async () => {
    expect(
      await evaluateHuman({
        policy,
        environment: { ...E, environment: 'e2' },
        principal: 'admin',
        required: ['grant:human'],
      }),
    ).toEqual({ allowed: false });
  });

  it('refuses an empty requirement (a defect, never an allow)', async () => {
    await expect(
      evaluateHuman({ policy, environment: E, principal: 'admin', required: [] }),
    ).rejects.toThrow(RangeError);
  });

  it('a read failure rejects (BR-EV-06): never an allow', async () => {
    const failing = createPolicyDecision({
      environment: E,
      grants: { grantsOf: () => Promise.reject(new Error('store down')) },
    });
    await expect(
      evaluateHuman({
        policy: failing,
        environment: E,
        principal: 'admin',
        required: ['grant:human'],
      }),
    ).rejects.toThrow('store down');
  });
});

describe('TC-EHA-011 (P3): holdsAnyGrant is the issuance condition', () => {
  it('true with any grant in E, false with none', async () => {
    expect(await holdsAnyGrant({ policy, environment: E, principal: 'dev' })).toBe(true);
    expect(await holdsAnyGrant({ policy, environment: E, principal: 'nobody' })).toBe(false);
  });
});
