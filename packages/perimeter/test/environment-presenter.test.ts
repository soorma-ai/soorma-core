// SPDX-License-Identifier: FSL-1.1-ALv2
//
// P1's presenter rules at S2 (U4 BR-PR-01 to 07): which credential reaches
// which operation, refused by kind without verifying.
import { describe, expect, it } from 'vitest';
import { presentedEnvironmentCredential, presentedSignIn } from '../src/index.ts';

const EC = 'soorma_ec_abc.def.ghi';
const SI = 'soorma_si_abc.def.ghi';

describe('TC-EHA-009, 033 (P1): each operation accepts its one kind', () => {
  it('renewal, ending, and grantToHuman take an environment credential, never a sign-in', () => {
    expect(presentedEnvironmentCredential(['Authorization', `Bearer ${EC}`])).toBe(EC);
    expect(presentedEnvironmentCredential(['Authorization', `Bearer ${SI}`])).toBeUndefined();
  });

  it('issuance takes a sign-in, never an environment credential', () => {
    expect(presentedSignIn(['Authorization', `Bearer ${SI}`])).toBe(SI);
    expect(presentedSignIn(['Authorization', `Bearer ${EC}`])).toBeUndefined();
  });
});

describe('TC-EHA-015, 016, 032, 034 (P1): refused presentations', () => {
  it.each([
    ['an agent credential', ['Authorization', 'Bearer soorma_ac_abc']],
    ['a delegation credential', ['Authorization', 'Bearer soorma_dc_abc']],
    ['an unknown prefix', ['Authorization', 'Bearer soorma_xx_abc']],
    ['no credential', ['Content-Type', 'application/json']],
    ['Bearer with nothing after it', ['Authorization', 'Bearer ']],
    ['a token with a space', ['Authorization', 'Bearer soorma_ec_a b']],
    ['a non-b64token', ['Authorization', 'Bearer soorma_ec_a"b']],
    ['4097 characters', ['Authorization', `Bearer soorma_ec_${'a'.repeat(4087)}`]],
    ['another scheme', ['Authorization', `Basic ${EC}`]],
    [
      'two Authorization headers',
      ['Authorization', `Bearer ${EC}`, 'Authorization', `Bearer ${EC}`],
    ],
    [
      'an agent credential beside a human one',
      ['Authorization', `Bearer ${EC}`, 'Authorization', 'Bearer soorma_ac_x'],
    ],
    [
      'a Soorma-Delegation header',
      ['Authorization', `Bearer ${EC}`, 'Soorma-Delegation', 'anything'],
    ],
  ])('refuses %s', (_name, raw) => {
    expect(presentedEnvironmentCredential(raw)).toBeUndefined();
  });

  it('accepts the header name in any case, and a token of exactly 4096 characters', () => {
    expect(presentedEnvironmentCredential(['authorization', `bearer ${EC}`])).toBe(EC);
    const max = `soorma_ec_${'a'.repeat(4086)}`;
    expect(max).toHaveLength(4096);
    expect(presentedEnvironmentCredential(['Authorization', `Bearer ${max}`])).toBe(max);
  });
});
