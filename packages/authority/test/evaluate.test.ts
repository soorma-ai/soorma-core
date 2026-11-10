// SPDX-License-Identifier: FSL-1.1-ALv2
// Step 9 at the evaluation level: origin, effective authority, and the
// human-only class. TC-AE-002, 004, 011, 015, 016, 018 to 023, 025, 026;
// BR-OR; BR-AU; D-AE-01, 03, 07, 09, 20, 21; L1-04, 06 to 08, 10, 14, 17,
// 19 to 22, 24, 25, 28, 29, 32, 38; I5, I9.
import { createPolicyDecision, inMemoryGrantSource } from '@soorma/policy-decision';
import type { PermissionSet, PolicyDecision } from '@soorma/policy-decision-seam';
import type { VerifiedInbound } from '@soorma/envelope';
import { describe, expect, it, vi } from 'vitest';
import { evaluateAgent, HUMAN_ONLY_PERMISSIONS, resolveOrigin } from '../src/index.ts';
import { agentFacts, E } from './support.ts';

const set = (...ids: string[]): PermissionSet => new Set(ids);

/** A policy over standing sets by agent. */
function policyOf(standing: Readonly<Record<string, readonly string[]>>): PolicyDecision {
  return createPolicyDecision({
    environment: E,
    grants: inMemoryGrantSource(
      Object.entries(standing).map(([agent, s]) => [{ kind: 'agent', agent }, s] as const),
    ),
  });
}

describe('Origin (BR-OR): TC-AE-002, 011, 023, 025', () => {
  const declared = agentFacts({ autonomy: true }).registrationView;
  const undeclared = agentFacts({ autonomy: false }).registrationView;
  const inbound = (originMode: unknown): VerifiedInbound => ({
    envelope: {},
    actorChain: [{ agent: 'a', instance: 'a-i' }],
    originMode,
  });

  it.each([
    ['TC-AE-002: no inbound, declared', declared, undefined, { ok: true, value: 'autonomous' }],
    [
      'TC-AE-011: no inbound, not declared (O12)',
      undeclared,
      undefined,
      { reason: 'o12_undeclared' },
    ],
    [
      'TC-AE-003: inbound autonomous, declared: propagated',
      declared,
      inbound('autonomous'),
      { ok: true, value: 'autonomous' },
    ],
    [
      'TC-AE-023: inbound autonomous, not declared (GAP-AE-001)',
      undeclared,
      inbound('autonomous'),
      { reason: 'o12_undeclared' },
    ],
    [
      'TC-AE-025: inbound delegated',
      declared,
      inbound('delegated'),
      { reason: 'origin_unsupported' },
    ],
    [
      'TC-AE-025: inbound unknown value',
      declared,
      inbound('x-future-mode'),
      { reason: 'origin_unsupported' },
    ],
    [
      'TC-AE-025: inbound delegated, not declared',
      undeclared,
      inbound('delegated'),
      { reason: 'origin_unsupported' },
    ],
    [
      'TC-AE-021: the presenter not found',
      undefined,
      undefined,
      { reason: 'presenter_unresolved' },
    ],
  ])('%s', (_, view, forwarded, expected) => {
    const result = resolveOrigin(view, forwarded);
    if ('reason' in expected)
      expect(result).toEqual({
        ok: false,
        refusal: { code: 'forbidden', reason: expected.reason },
      });
    else expect(result).toEqual(expected);
  });

  it('autonomy declared defaults to no: anything but true is not declared', () => {
    const odd = { autonomyDeclared: 'yes' as unknown as boolean, reBroadeningDeclaration: set() };
    expect(resolveOrigin(odd, undefined)).toMatchObject({ refusal: { reason: 'o12_undeclared' } });
  });
});

describe('Effective authority (BR-AU): the one place it is computed', () => {
  const p = 'event:subscribe';
  it('TC-AE-004: every term holds it: allowed, not load-bearing', async () => {
    const r = await evaluateAgent({
      policy: policyOf({ a: ['event:publish'], b: ['event:publish'] }),
      environment: E,
      presenter: 'b',
      declaration: set(),
      upstream: ['a'],
      required: set('event:publish'),
    });
    expect(r).toEqual({ allowed: true, loadBearing: false });
  });

  it('TC-AE-005 and TC-AE-015: an upstream gap; recovered only by a declaration', async () => {
    const base = {
      policy: policyOf({ a: [], b: [p] }),
      environment: E,
      presenter: 'b',
      upstream: ['a'],
      required: set(p),
    };
    expect(await evaluateAgent({ ...base, declaration: set(p) })).toEqual({
      allowed: true,
      loadBearing: true,
    });
    expect(await evaluateAgent({ ...base, declaration: set() })).toEqual({
      allowed: false,
      loadBearing: false,
      reason: 'authority_denied',
    });
  });

  it('TC-AE-016: never recovers what the delegating principal lacked', async () => {
    const r = await evaluateAgent({
      policy: policyOf({ a: [], b: [p] }),
      environment: E,
      presenter: 'b',
      declaration: set(p),
      upstream: ['a'],
      principal: set('event:publish'),
      required: set(p),
    });
    expect(r).toEqual({ allowed: false, loadBearing: false, reason: 'authority_denied' });
  });

  it.each([
    [
      'row 1: in P, in every upstream term, declared',
      { a: [p], b: [p] },
      [p],
      set(p),
      { allowed: true, loadBearing: false },
    ],
    [
      'row 1: in P, in every upstream term, not declared',
      { a: [p], b: [p] },
      [],
      set(p),
      { allowed: true, loadBearing: false },
    ],
    [
      'row 2: in P, missing upstream, declared',
      { a: [], b: [p] },
      [p],
      set(p),
      { allowed: true, loadBearing: true },
    ],
    [
      'row 3: in P, missing upstream, not declared',
      { a: [], b: [p] },
      [],
      set(p),
      { allowed: false, loadBearing: false, reason: 'authority_denied' },
    ],
    [
      'row 4: not in P, upstream holds it, declared',
      { a: [p], b: [p] },
      [p],
      set(),
      { allowed: false, loadBearing: false, reason: 'authority_denied' },
    ],
    [
      'row 4: not in P, missing upstream, declared',
      { a: [], b: [p] },
      [p],
      set(),
      { allowed: false, loadBearing: false, reason: 'authority_denied' },
    ],
  ] as const)(
    'TC-AE-022, the case table %s',
    async (_, standing, declared, principal, expected) => {
      const r = await evaluateAgent({
        policy: policyOf(standing),
        environment: E,
        presenter: 'b',
        declaration: set(...declared),
        upstream: ['a'],
        principal,
        required: set(p),
      });
      expect(r).toEqual(expected);
    },
  );

  it('TC-AE-018: re-broadening is local to its hop: B’s grants D nothing', async () => {
    const base = {
      policy: policyOf({ a: [], b: [p], d: [p] }),
      environment: E,
      presenter: 'd',
      upstream: ['a', 'b'],
      required: set(p),
    };
    expect(await evaluateAgent({ ...base, declaration: set() })).toMatchObject({
      allowed: false,
      reason: 'authority_denied',
    });
    expect(await evaluateAgent({ ...base, declaration: set(p) })).toEqual({
      allowed: true,
      loadBearing: true,
    });
  });

  it('TC-AE-019: a first hop is never load-bearing', async () => {
    const r = await evaluateAgent({
      policy: policyOf({ b: ['event:publish'] }),
      environment: E,
      presenter: 'b',
      declaration: set('event:publish'),
      upstream: [],
      required: set('event:publish'),
    });
    expect(r).toEqual({ allowed: true, loadBearing: false });
  });

  it('TC-AE-020: outside the standing set, always denied, a wider declaration included', async () => {
    const q = 'attribution:read';
    const policy = policyOf({ a: [q], b: ['event:publish'] });
    expect(
      await evaluateAgent({
        policy,
        environment: E,
        presenter: 'b',
        declaration: set(),
        upstream: [],
        required: set(q),
      }),
    ).toMatchObject({ allowed: false });
    expect(
      await evaluateAgent({
        policy,
        environment: E,
        presenter: 'b',
        declaration: set(q),
        upstream: ['a'],
        required: set(q),
      }),
    ).toMatchObject({ allowed: false, reason: 'authority_denied' });
  });

  it('TC-AE-021: an empty standing set; an unresolved upstream agent', async () => {
    expect(
      await evaluateAgent({
        policy: policyOf({ b: [] }),
        environment: E,
        presenter: 'b',
        declaration: set(),
        upstream: [],
        required: set('event:publish'),
      }),
    ).toMatchObject({ allowed: false, reason: 'authority_denied' });
    expect(
      await evaluateAgent({
        policy: policyOf({ b: ['event:publish'] }),
        environment: E,
        presenter: 'b',
        declaration: set('event:publish'),
        upstream: ['x'],
        unresolved: new Set(['x']),
        required: set('event:publish'),
      }),
    ).toEqual({ allowed: false, loadBearing: false, reason: 'upstream_unresolved' });
  });

  it('TC-AE-026: a human-only permission, whatever the standing set holds', async () => {
    const policy = policyOf({ a: [...HUMAN_ONLY_PERMISSIONS] });
    for (const q of HUMAN_ONLY_PERMISSIONS)
      expect(
        await evaluateAgent({
          policy,
          environment: E,
          presenter: 'a',
          declaration: set(q),
          upstream: [],
          required: set(q),
        }),
      ).toEqual({ allowed: false, loadBearing: false, reason: 'human_only_permission' });
  });

  it('TC-AE-026 step 2: the class is exactly the three plane-declared identifiers, frozen (I9)', () => {
    expect(HUMAN_ONLY_PERMISSIONS).toEqual(['grant:human', 'human:manage', 'agent:delegate']);
    expect(Object.isFrozen(HUMAN_ONLY_PERMISSIONS)).toBe(true);
  });

  it('D-AE-21, BR-AU-02: one grantedSet per distinct agent; the seam is asked nothing else', async () => {
    // P11's policy is frozen: a recording double delegates to it.
    const inner = policyOf({ a: ['event:publish'], b: ['event:publish'] });
    const grantedSet = vi.fn<PolicyDecision['grantedSet']>((principal, environment) =>
      inner.grantedSet(principal, environment),
    );
    const contains = vi.fn<PolicyDecision['contains']>((effective, required) =>
      inner.contains(effective, required),
    );
    const policy: PolicyDecision = { grantedSet, contains };
    await evaluateAgent({
      policy,
      environment: E,
      presenter: 'b',
      declaration: set(),
      upstream: ['a', 'b', 'a'],
      required: set('event:publish'),
    });
    expect(grantedSet.mock.calls.map(([principal]) => principal)).toEqual([
      { kind: 'agent', agent: 'b' },
      { kind: 'agent', agent: 'a' },
    ]);
    expect(contains).toHaveBeenCalledTimes(2);
  });
});
