// SPDX-License-Identifier: FSL-1.1-ALv2
//
// The registration secret's format, verifier, parser, and the cap's lock key
// (U5 NFR-AR-01 to 05; NP-AR-02, 03). The literal vectors were computed
// independently of this code.
import { asSecretText } from '@soorma/service-kit';
import { describe, expect, it } from 'vitest';
import {
  digestRegistrationSecret,
  generateRegistrationSecret,
  parseRegistrationSecret,
  registrationLockKey,
  registrationSecretMatches,
} from '../src/index.ts';

const VALUE = /^soorma_rs_[A-Za-z0-9_-]{22}\.[A-Za-z0-9_-]{43}$/;
const FIXED = Buffer.from(Array.from({ length: 32 }, (_, i) => i));
const FIXED_PART = 'AAECAwQFBgcICQoLDA0ODxAREhMUFRYXGBkaGxwdHh8';
const ID = 'AAAAAAAAAAAAAAAAAAAAAA';

describe('TC-AR-048: a value has the specified format, and values are distinct', () => {
  it('soorma_rs_{22}.{43}, at most 256 characters, 10,000 distinct', () => {
    const seen = new Set<string>();
    for (let i = 0; i < 10_000; i += 1) {
      const g = generateRegistrationSecret();
      const v: string = g.value;
      expect(v).toMatch(VALUE);
      expect(v.length).toBeLessThanOrEqual(256);
      expect(v.slice(10, 32)).toBe(g.id);
      expect(g.digest).toHaveLength(32);
      seen.add(v);
    }
    expect(seen.size).toBe(10_000);
  });

  it('a generated value parses back to its id, and its digest matches', () => {
    const g = generateRegistrationSecret();
    const parsed = parseRegistrationSecret(g.value);
    expect(parsed.kind).toBe('parsed');
    if (parsed.kind !== 'parsed') return;
    expect(parsed.id).toBe(g.id);
    expect(registrationSecretMatches(parsed.secretBytes, g.digest)).toBe(true);
  });
});

describe('TC-AR-049: the digest matches its test vector', () => {
  it('SHA-256("soorma.registration-secret.v1" || 0x00 || bytes 0..31)', () => {
    expect(digestRegistrationSecret(FIXED).toString('hex')).toBe(
      '5759b949849fee0334e6058a36e6bc4d2b36f3e5040103782f94b69e7d140f39',
    );
  });

  it('a different secret does not match; a stored digest of another length never matches', () => {
    const stored = digestRegistrationSecret(FIXED);
    expect(registrationSecretMatches(Buffer.alloc(32), stored)).toBe(false);
    expect(registrationSecretMatches(FIXED, stored.subarray(0, 31))).toBe(false);
    expect(registrationSecretMatches(FIXED, Buffer.concat([stored, Buffer.alloc(1)]))).toBe(false);
  });
});

describe('TC-AR-050: each malformed value is refused by the parser, without throwing', () => {
  const good = `soorma_rs_${ID}.${FIXED_PART}`;
  it('accepts the canonical form', () => {
    expect(parseRegistrationSecret(asSecretText(good)).kind).toBe('parsed');
  });
  it.each([
    ['no prefix', `${ID}.${FIXED_PART}`],
    ['another prefix', `soorma_ec_${ID}.${FIXED_PART}`],
    ['no separator', `soorma_rs_${ID}${FIXED_PART}`],
    ['two separators', `soorma_rs_${ID}.${FIXED_PART}.x`],
    ['a 21-character id', `soorma_rs_${ID.slice(1)}.${FIXED_PART}`],
    ['a 23-character id', `soorma_rs_${ID}A.${FIXED_PART}`],
    ['a 42-character secret', `soorma_rs_${ID}.${FIXED_PART.slice(1)}`],
    ['a 44-character secret', `soorma_rs_${ID}.${FIXED_PART}A`],
    ['a non-canonical final character', `soorma_rs_${ID}.${FIXED_PART.slice(0, 42)}9`],
    ['padding', `soorma_rs_${ID}.${FIXED_PART}=`],
    ['a non-base64url character', `soorma_rs_${ID}.${FIXED_PART.slice(0, 42)}+`],
    ['an empty value', ''],
    ['too long', `soorma_rs_${ID}.${FIXED_PART}${'A'.repeat(200)}`],
  ])('%s', (_name, value) => {
    expect(parseRegistrationSecret(asSecretText(value))).toEqual({ kind: 'invalid' });
  });
});

describe('TC-AR-053: the lock key is derived as specified', () => {
  const E = { organization: 'o1', project: 'p1', environment: 'e' };
  it('the first 63 bits of the domain-separated SHA-256, as a decimal string', () => {
    expect(registrationLockKey(E, 'a')).toBe('8117271241882858540');
  });
  it('differs by registration and by environment', () => {
    expect(registrationLockKey(E, 'b')).not.toBe(registrationLockKey(E, 'a'));
    expect(registrationLockKey({ ...E, environment: 'e2' }, 'a')).not.toBe(
      registrationLockKey(E, 'a'),
    );
  });
});
