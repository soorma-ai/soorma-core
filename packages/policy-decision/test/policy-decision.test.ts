// SPDX-License-Identifier: FSL-1.1-ALv2
// P11 and the seam: TC-AE-006, TC-AE-021 step 1, TC-AE-035; D-AE-02, 16;
// BR-SEAM-01 to 05; L1-09, 10, 13, 15, 26, 35.
import { readFileSync } from 'node:fs';
import ts from 'typescript';
import { describe, expect, it } from 'vitest';
import type { EnvironmentRef, PermissionSet, PrincipalRef } from '@soorma/policy-decision-seam';
import { createPolicyDecision, inMemoryGrantSource, type GrantSource } from '../src/index.ts';

const E: EnvironmentRef = { organization: 'o1', project: 'p1', environment: 'e' };
const E2: EnvironmentRef = { organization: 'o1', project: 'p1', environment: 'e2' };
const A: PrincipalRef = { kind: 'agent', agent: 'a' };
const EMPTY: PrincipalRef = { kind: 'agent', agent: 'empty' };
const H: PrincipalRef = { kind: 'human', principal: 'h@example.com' };

const policy = createPolicyDecision({
  environment: E,
  grants: inMemoryGrantSource([
    [A, ['event:publish']],
    [EMPTY, []],
    [H, ['grant:human']],
  ]),
});
const set = (...ids: string[]): PermissionSet => new Set(ids);

describe('TC-AE-006: the boundary decides containment, never composition', () => {
  it('steps 1 to 4: literal containment of every required member', () => {
    expect(policy.contains(set('event:publish'), set('event:publish'))).toBe(true);
    expect(policy.contains(set(), set('event:publish'))).toBe(false);
    expect(policy.contains(set('event:publish'), set('event:publish', 'event:subscribe'))).toBe(
      false,
    );
    expect(policy.contains(set('event:*'), set('event:publish'))).toBe(false);
    expect(policy.contains(set('EVENT:PUBLISH'), set('event:publish'))).toBe(false);
  });

  it("step 5: one principal's own set, in its environment only", async () => {
    expect(await policy.grantedSet(A, E)).toEqual(set('event:publish'));
    expect(await policy.grantedSet(A, E2)).toEqual(set());
    expect(await policy.grantedSet(H, E)).toEqual(set('grant:human'));
    expect(await policy.grantedSet({ kind: 'agent', agent: 'nobody' }, E)).toEqual(set());
  });

  it('step 6: the seam declares exactly grantedSet and contains, and nothing returns an effective set', () => {
    const path = new URL('../../../seams/policy-decision/src/index.ts', import.meta.url);
    const source = ts.createSourceFile(
      'index.ts',
      readFileSync(path, 'utf8'),
      ts.ScriptTarget.Latest,
    );
    const iface = source.statements.find(
      (s): s is ts.InterfaceDeclaration =>
        ts.isInterfaceDeclaration(s) && s.name.text === 'PolicyDecision',
    );
    expect(iface?.members.map((m) => (m.name as ts.Identifier).text)).toEqual([
      'grantedSet',
      'contains',
    ]);
    // Types only: no runtime statement in the seam.
    expect(
      source.statements.every((s) => ts.isInterfaceDeclaration(s) || ts.isTypeAliasDeclaration(s)),
    ).toBe(true);
  });

  it('a GrantSource failure propagates: never read as an empty set', async () => {
    const failing: GrantSource = { grantsOf: () => Promise.reject(new Error('store down')) };
    const p = createPolicyDecision({ environment: E, grants: failing });
    await expect(p.grantedSet(A, E)).rejects.toThrow('store down');
  });
});

describe('TC-AE-021 step 1: deny by default', () => {
  it('an empty standing set contains nothing', async () => {
    expect(policy.contains(await policy.grantedSet(EMPTY, E), set('event:publish'))).toBe(false);
  });
});

describe('TC-AE-035: the minimal model satisfies L1 to L5 (D-AE-16)', () => {
  const ids = ['event:publish', 'event:subscribe', 'agent:register'];
  // Every subset of the three identifiers: the empty set included.
  const sets: PermissionSet[] = [];
  for (let mask = 0; mask < 1 << ids.length; mask++)
    sets.push(new Set(ids.filter((_, i) => (mask >> i) & 1)));
  const meet = (a: PermissionSet, b: PermissionSet): PermissionSet =>
    new Set([...a].filter((x) => b.has(x)));
  const subset = (a: PermissionSet, b: PermissionSet): boolean => policy.contains(b, a);
  const equal = (a: PermissionSet, b: PermissionSet): boolean => subset(a, b) && subset(b, a);

  it('L1 closure, L2 commutativity, L4 monotonicity, for every pair', () => {
    for (const a of sets)
      for (const b of sets) {
        const ab = meet(a, b);
        expect([...ab].every((x) => ids.includes(x))).toBe(true);
        expect(equal(ab, meet(b, a))).toBe(true);
        expect(subset(ab, a)).toBe(true);
      }
  });

  it('L2 associativity, for every triple', () => {
    for (const a of sets)
      for (const b of sets)
        for (const c of sets) expect(equal(meet(meet(a, b), c), meet(a, meet(b, c)))).toBe(true);
  });

  it('L3 bottom: the empty set contains no non-empty set', () => {
    for (const r of sets) if (r.size > 0) expect(policy.contains(set(), r)).toBe(false);
  });

  it('L5 decidable containment, by exact membership', () => {
    for (const a of sets)
      for (const r of sets) expect(policy.contains(a, r)).toBe([...r].every((x) => a.has(x)));
  });
});
