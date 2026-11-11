// SPDX-License-Identifier: FSL-1.1-ALv2
//
// U3's guard on U2's canonical JSON (U3 NFR Design NP-03; TC-AE-036 step 4).
// The vectors and the fixture were written once from U2's canonicalJson
// before U3 swapped its body for a wrapper over @soorma/jcs. This file and
// test/vectors/ must not change after that commit: every assertion here must
// pass unchanged after the swap, or U3's Code Generation stops.
//
// Three callers depend on these bytes: the log pseudonym (referenceJson), P8's
// attempt slot (referenceJson), and the seed's associated data. A changed slot
// would move a principal's live attempt window to another row.
import { generateKeyPairSync } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
// P8 depends on P10, so P10's tests reach P8's slotOf by path, never as a package.
import { slotOf } from '../../abuse-bound/src/abuse-bound.ts';
import { associatedData } from '../src/crypto/seed-cipher.ts';
import { asSecretBytes, pseudonym, referenceJson } from '@soorma/service-kit';
import { decryptSeed, KeyRing, SeedDecryptionError, type StoredSeed } from '../src/index.ts';

interface Reference {
  organization: string;
  principal: string;
}

const vectors = JSON.parse(
  readFileSync(new URL('vectors/canonical-vectors.json', import.meta.url), 'utf8'),
) as {
  keys: { logPseudonymKeyHex: string; counterSecretHex: string };
  references: (Reference & { referenceJsonHex: string; pseudonym: string; slot: number })[];
  seedAssociatedData: (Reference & { recordId: string; bytesHex: string })[];
};

const fixture = JSON.parse(
  readFileSync(new URL('vectors/seed-fixture.json', import.meta.url), 'utf8'),
) as {
  seedKeyId: string;
  seedKeyHex: string;
  reference: Reference;
  recordId: string;
  stored: StoredSeed;
  plaintextHex: string;
};

const ref = ({ organization, principal }: Reference): Reference => ({ organization, principal });
const logKey = asSecretBytes(Buffer.from(vectors.keys.logPseudonymKeyHex, 'hex'));
const counterSecret = asSecretBytes(Buffer.from(vectors.keys.counterSecretHex, 'hex'));

function fixtureKeys(): KeyRing {
  const signing = generateKeyPairSync('ed25519');
  return KeyRing.fromConfiguration({
    signingKey: Buffer.from(signing.privateKey.export({ format: 'pem', type: 'pkcs8' })),
    verifyKeys: [],
    seedKeys: {
      current: fixture.seedKeyId,
      keys: [{ id: fixture.seedKeyId, key: Buffer.from(fixture.seedKeyHex, 'hex') }],
    },
    counterSecret,
    logPseudonymKey: logKey,
    internalCallers: [],
  });
}

describe('TC-AE-036 step 4: U2 canonical JSON, byte for byte (NP-03)', () => {
  it('covers the vectors NP-03 asks for', () => {
    expect(vectors.references.length).toBeGreaterThanOrEqual(8);
    expect(vectors.seedAssociatedData.length).toBeGreaterThanOrEqual(4);
    const principals = vectors.references.map((r) => r.principal).join('');
    for (const c of ["'", '/', '|', '@', '+', ':', '.']) expect(principals).toContain(c);
  });

  it.each(vectors.references.map((v) => [v.principal, v] as const))(
    'referenceJson, its pseudonym, and its attempt slot: %s',
    (_, v) => {
      const reference = ref(v);
      expect(Buffer.from(referenceJson(reference), 'utf8').toString('hex')).toBe(
        v.referenceJsonHex,
      );
      expect(pseudonym(reference, logKey)).toBe(v.pseudonym);
      expect(slotOf(reference, counterSecret)).toBe(v.slot);
    },
  );

  it.each(vectors.seedAssociatedData.map((v) => [v.recordId, v] as const))(
    'the seed associated data: %s',
    (_, v) => {
      expect(associatedData(ref(v), v.recordId).toString('hex')).toBe(v.bytesHex);
    },
  );

  it('decrypts the seed the pre-swap code encrypted', () => {
    const seed = decryptSeed(
      fixture.stored,
      ref(fixture.reference),
      fixture.recordId,
      fixtureKeys(),
    );
    expect(Buffer.from(seed).toString('hex')).toBe(fixture.plaintextHex);
  });

  it('fails to decrypt when one byte of the associated data differs', () => {
    const other = {
      ...fixture.reference,
      principal: `${fixture.reference.principal.slice(0, -1)}n`,
    };
    expect(() => decryptSeed(fixture.stored, other, fixture.recordId, fixtureKeys())).toThrow(
      SeedDecryptionError,
    );
    expect(() =>
      decryptSeed(
        fixture.stored,
        ref(fixture.reference),
        `${fixture.recordId.slice(0, -1)}9`,
        fixtureKeys(),
      ),
    ).toThrow(SeedDecryptionError);
  });
});
