// SPDX-License-Identifier: FSL-1.1-ALv2
// The seal and the key ring: TC-AE-032; TC-AE-033 steps 1 (ring checks) to 5;
// TC-AE-024 steps 3, 4 (no MAC computed); NP-01, NP-02; NFR-AE-17, 18;
// L1-37.
import * as crypto from 'node:crypto';
import { readFileSync } from 'node:fs';
import { canonicalize } from '@soorma/jcs';
import { describe, expect, it, vi } from 'vitest';
import { createSealer, loadSealKeyRing, SEAL_LABEL, SealKeyRingError } from '../src/index.ts';
import { envelope, sealerE, sealerE2, testKey } from './support.ts';

vi.mock('node:crypto', async (importOriginal) => {
  const actual = await importOriginal<typeof import('node:crypto')>();
  return { ...actual, createHmac: vi.fn(actual.createHmac) };
});

const fixed = canonicalize(
  envelope(['a'], { actorChain: [{ agent: 'a', instance: 'i-1' }] }),
).bytes;

describe('TC-AE-032: the seal, its vector, and domain separation (NP-01)', () => {
  it('step 1: the committed literal seal, computed independently with OpenSSL', () => {
    expect(fixed.toString('utf8')).toBe(
      '{"actorChain":[{"agent":"a","instance":"i-1"}],"envelopeVersion":1,"originMode":"autonomous",' +
        '"scope":{"environment":"e","organization":"o1","project":"p1"},' +
        '"traceContext":{"traceparent":"00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"}}',
    );
    const seal = sealerE.seal(fixed);
    expect(seal).toBe('v1.k1.Q-eQiLOVy1XmferS0WCQbbFVGda03VvikJg38YuL1-c');
    expect(seal).toMatch(/^v1\.k1\.[A-Za-z0-9_-]{43}$/);
  });

  it('step 2: the MAC without the label differs (computed with OpenSSL too)', () => {
    const unlabelled = crypto.createHmac('sha256', testKey(0x60)).update(fixed).digest('base64url');
    expect(unlabelled).toBe('UifXYKcmHAqY-IC8K5ZKPX0bjn2H3ZPUwfB1j43fDVA');
    expect(sealerE.seal(fixed).endsWith(unlabelled)).toBe(false);
    expect(SEAL_LABEL).toBe('soorma.envelope-seal.v1');
  });

  it('step 3: it verifies, and compares in constant time (source check)', () => {
    expect(sealerE.verify(sealerE.seal(fixed), fixed)).toBe(true);
    const source = readFileSync(new URL('../src/seal.ts', import.meta.url), 'utf8');
    expect(source).toContain('timingSafeEqual(mac(key, jcsBytes), presented)');
    expect(source).not.toMatch(/presented\.equals|===\s*presented|presented\s*===/);
  });

  it("another environment's key fails, and so does any changed byte", () => {
    expect(sealerE.verify(sealerE2.seal(fixed), fixed)).toBe(false);
    const changed = Buffer.from(fixed);
    changed[10] = changed[10]! ^ 1;
    expect(sealerE.verify(sealerE.seal(fixed), changed)).toBe(false);
  });

  it.each([
    ['not a string', 7],
    ['another version', `v2.k1.${'A'.repeat(43)}`],
    ['a kid not in the ring', `v1.k9.${'A'.repeat(43)}`],
    ['a MAC of 42 characters', `v1.k1.${'A'.repeat(42)}`],
    ['a MAC of 44 characters', `v1.k1.${'A'.repeat(44)}`],
    ['a character outside base64url', `v1.k1.${'A'.repeat(42)}+`],
    ['padding', `v1.k1.${'A'.repeat(42)}=`],
    ['a MAC that does not re-encode identically', `v1.k1.${'A'.repeat(42)}B`],
    ['a kid with a dot', `v1.k.1.${'A'.repeat(43)}`],
  ])('TC-AE-024 steps 3, 4: %s fails before any MAC is computed', (_, seal) => {
    const hmac = vi.mocked(crypto.createHmac);
    hmac.mockClear();
    expect(sealerE.verify(seal, fixed)).toBe(false);
    expect(hmac).not.toHaveBeenCalled();
  });
});

describe('TC-AE-033: the key ring, at start-up and through a rotation (NP-02)', () => {
  const k1 = testKey(0x10);
  const k2 = testKey(0x30);

  it.each([
    ['current not among the keys', { current: 'k9', keys: [{ id: 'k1', key: k1 }] }],
    [
      'a duplicate id',
      {
        current: 'k1',
        keys: [
          { id: 'k1', key: k1 },
          { id: 'k1', key: k2 },
        ],
      },
    ],
    ['an id k.1', { current: 'k.1', keys: [{ id: 'k.1', key: k1 }] }],
    [
      'an id of 17 characters',
      { current: 'k'.repeat(17), keys: [{ id: 'k'.repeat(17), key: k1 }] },
    ],
    ['a 128-bit key', { current: 'k1', keys: [{ id: 'k1', key: k1.subarray(0, 16) }] }],
  ])('step 1: refuses %s', (_, input) => {
    expect(() => loadSealKeyRing(input)).toThrow(SealKeyRingError);
  });

  it('steps 2 to 5: rotation is two-phase, and old seals fail once their key is removed', () => {
    const one = createSealer(loadSealKeyRing({ current: 'k1', keys: [{ id: 'k1', key: k1 }] }));
    const s1 = one.seal(fixed);

    const both1 = createSealer(
      loadSealKeyRing({
        current: 'k1',
        keys: [
          { id: 'k1', key: k1 },
          { id: 'k2', key: k2 },
        ],
      }),
    );
    expect(both1.verify(s1, fixed)).toBe(true);
    const s2 = both1.seal(fixed);
    expect(s2.startsWith('v1.k1.')).toBe(true);

    const both2 = createSealer(
      loadSealKeyRing({
        current: 'k2',
        keys: [
          { id: 'k1', key: k1 },
          { id: 'k2', key: k2 },
        ],
      }),
    );
    expect(both2.verify(s1, fixed)).toBe(true);
    const s3 = both2.seal(fixed);
    expect(s3.startsWith('v1.k2.')).toBe(true);
    expect(both1.verify(s3, fixed)).toBe(true);

    const two = createSealer(loadSealKeyRing({ current: 'k2', keys: [{ id: 'k2', key: k2 }] }));
    expect(two.verify(s1, fixed)).toBe(false);
    expect(two.verify(s3, fixed)).toBe(true);
  });

  it('the ring keeps its own copy of each key', () => {
    const key = Buffer.from(k1);
    const sealer = createSealer(loadSealKeyRing({ current: 'k1', keys: [{ id: 'k1', key }] }));
    const before = sealer.seal(fixed);
    key.fill(0);
    expect(sealer.seal(fixed)).toBe(before);
  });
});
