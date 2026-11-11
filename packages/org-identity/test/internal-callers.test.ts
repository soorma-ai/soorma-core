// SPDX-License-Identifier: FSL-1.1-ALv2
//
// TC-EHA-082 and TC-EHA-083 (the key-ring half): a kid names one key of one
// environment, checked on the loaded keys, so two files holding one key are
// caught; a call signed with either of an environment's listed keys is
// attributed to it, and never to another (U4 Infrastructure Design §4; I1).
import { generateKeyPairSync, randomBytes, type KeyObject } from 'node:crypto';
import {
  KeyMaterialError,
  signInternalRequest,
  thumbprint,
  verifyInternalRequest,
} from '@soorma/service-kit';
import { describe, expect, it } from 'vitest';
import { KeyRing } from '../src/index.ts';

const pem = (k: KeyObject): Buffer => Buffer.from(k.export({ format: 'pem', type: 'spki' }));
const pair = () => generateKeyPairSync('ed25519');

function ring(internalCallers: { environment: string; publicKeys: Buffer[] }[]): KeyRing {
  return KeyRing.fromConfiguration({
    signingKey: Buffer.from(pair().privateKey.export({ format: 'pem', type: 'pkcs8' })),
    verifyKeys: [],
    seedKeys: { current: 's1', keys: [{ id: 's1', key: randomBytes(32) }] },
    counterSecret: randomBytes(32),
    logPseudonymKey: randomBytes(32),
    internalCallers,
  });
}

function refusal(fn: () => unknown): readonly string[] {
  try {
    fn();
  } catch (error) {
    if (error instanceof KeyMaterialError) return error.problems;
    throw error;
  }
  throw new Error('expected a KeyMaterialError');
}

describe('TC-EHA-082: S1 refuses an ambiguous internal-caller key ring', () => {
  it('refuses one key twice for one environment, including two PEM files holding it', () => {
    const k = pair();
    const kid = thumbprint(k.publicKey);
    const samePemTwice = Buffer.from(`\n${pem(k.publicKey).toString()}`);
    expect(
      refusal(() => ring([{ environment: 'e', publicKeys: [pem(k.publicKey), samePemTwice] }])),
    ).toEqual([`internal caller key ${kid} appears twice for environment e`]);
  });

  it('refuses one key configured for two environments', () => {
    const k = pair();
    const kid = thumbprint(k.publicKey);
    expect(
      refusal(() =>
        ring([
          { environment: 'e', publicKeys: [pem(k.publicKey)] },
          { environment: 'e2', publicKeys: [Buffer.from(`\n${pem(k.publicKey).toString()}`)] },
        ]),
      ),
    ).toEqual([`internal caller key ${kid} is configured for environments e and e2`]);
  });

  it('loads distinct keys, two of them for one environment', () => {
    const a = pair();
    const b = pair();
    const c = pair();
    const keys = ring([
      { environment: 'e', publicKeys: [pem(a.publicKey), pem(b.publicKey)] },
      { environment: 'e2', publicKeys: [pem(c.publicKey)] },
    ]);
    expect(keys.callerByKid(thumbprint(a.publicKey))?.environment).toBe('e');
    expect(keys.callerByKid(thumbprint(b.publicKey))?.environment).toBe('e');
    expect(keys.callerByKid(thumbprint(c.publicKey))?.environment).toBe('e2');
  });
});

describe("TC-EHA-083: a call is attributed only to its own environment, by either of E's keys", () => {
  const now = new Date('2026-11-11T12:00:00Z');
  const oldKey = pair();
  const newKey = pair();
  const e2Key = pair();
  const keys = ring([
    { environment: 'e', publicKeys: [pem(oldKey.publicKey), pem(newKey.publicKey)] },
    { environment: 'e2', publicKeys: [pem(e2Key.publicKey)] },
  ]);
  const target = '/principals/exists?organization=o1&principal=h%40example.com';

  async function call(key: KeyObject, environment: string): Promise<string | undefined> {
    const token = await signInternalRequest({ environment, method: 'GET', target }, key, 'o1', now);
    return verifyInternalRequest(
      { method: 'GET', target, body: Buffer.alloc(0), authorization: [`Bearer ${token}`] },
      keys,
      'o1',
      now,
    );
  }

  it("either of E's listed keys is attributed to E (rotation with no outage)", async () => {
    expect(await call(oldKey.privateKey, 'e')).toBe('e');
    expect(await call(newKey.privateKey, 'e')).toBe('e');
  });

  it("E2's key naming E as its issuer is refused", async () => {
    expect(await call(e2Key.privateKey, 'e')).toBeUndefined();
    expect(await call(e2Key.privateKey, 'e2')).toBe('e2');
  });
});
