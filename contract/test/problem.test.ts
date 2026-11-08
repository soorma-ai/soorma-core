// SPDX-License-Identifier: Apache-2.0
// The Problem: TC-WC-024.
import { describe, expect, it } from 'vitest';
import { walkSchema } from '../scripts/checks/model.ts';
import { component, copy, samples, valid } from './helpers.ts';

describe('TC-WC-024: errors follow the Problem definition', () => {
  it('step 1: accepts a validation problem with errors', () => {
    expect(valid('Problem', samples.problem)).toBe(true);
  });

  it('step 2: accepts supportedVersions on unsupported_contract_version', () => {
    expect(
      valid('Problem', {
        code: 'unsupported_contract_version',
        type: 'urn:soorma:problem:unsupported_contract_version',
        supportedVersions: ['0.1.0'],
      }),
    ).toBe(true);
  });

  it('step 3: accepts an unknown code', () => {
    expect(
      valid('Problem', { code: 'some_future_code', type: 'urn:soorma:problem:some_future_code' }),
    ).toBe(true);
  });

  it.each(['type', 'title', 'status', 'code', 'instance'])(
    'step 4: accepts a problem without %s',
    (field) => {
      const p = copy(samples.problem);
      delete p[field];
      expect(valid('Problem', p)).toBe(true);
    },
  );

  it('step 5: accepts about:blank, and an instance that is not a urn:soorma:request: URI', () => {
    expect(valid('Problem', { ...samples.problem, type: 'about:blank' })).toBe(true);
    expect(valid('Problem', { ...samples.problem, instance: 'req-42' })).toBe(true);
  });

  it('step 6: accepts an unknown field', () => {
    expect(valid('Problem', { ...samples.problem, 'x-future': 1 })).toBe(true);
  });

  it('step 7: accepts a long instance with a space, and no Problem property has a pattern', () => {
    expect(
      valid('Problem', { ...samples.problem, instance: `with space ${'x'.repeat(189)}` }),
    ).toBe(true);
    walkSchema(component('schemas', 'Problem'), '', (node, pointer) => {
      expect('pattern' in node, `Problem${pointer} has a pattern`).toBe(false);
    });
  });

  it('step 8: accepts a gateway-style problem, and an empty object', () => {
    expect(valid('Problem', { type: 'about:blank', title: 'Bad Gateway', status: 502 })).toBe(true);
    expect(valid('Problem', {})).toBe(true);
  });

  it('step 9: still checks the type of each field present', () => {
    expect(valid('Problem', { ...samples.problem, status: '400' })).toBe(false);
    expect(valid('Problem', { ...samples.problem, code: 7 })).toBe(false);
  });

  it('requires no field', () => {
    expect(component('schemas', 'Problem')).not.toHaveProperty('required');
  });
});
