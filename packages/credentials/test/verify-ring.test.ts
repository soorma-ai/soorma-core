// SPDX-License-Identifier: FSL-1.1-ALv2
// The verify-only key ring (U7 NP-ET-07): TC-ET-078. S4 verifies E's agent
// credentials with the SPKI verify halves stack:init writes, never holding a
// signing key. U4's and U6's credentials tests are unchanged.
import { generateKeyPairSync } from 'node:crypto';
import { asSecretBytes, KeyMaterialError } from '@soorma/service-kit';
import { describe, expect, it } from 'vitest';
import {
  loadEnvironmentKeyRing,
  loadVerifyKeyRing,
  mintAgentCredential,
  verifyAgentCredential,
} from '../src/index.ts';

const E = { organization: 'o1', project: 'p1', environment: 'e' };
const T0 = new Date('2026-11-13T08:00:00Z');

function pair(): { privatePem: Buffer; publicPem: Buffer } {
  const { privateKey, publicKey } = generateKeyPairSync('ed25519');
  return {
    privatePem: Buffer.from(privateKey.export({ format: 'pem', type: 'pkcs8' })),
    publicPem: Buffer.from(publicKey.export({ format: 'pem', type: 'spki' })),
  };
}

function problems(run: () => unknown): readonly string[] {
  try {
    run();
  } catch (e) {
    expect(e).toBeInstanceOf(KeyMaterialError);
    return (e as KeyMaterialError).problems;
  }
  throw new Error('expected a KeyMaterialError');
}

describe('TC-ET-078: the verify-only key ring', () => {
  it("verifies S3's token with the verify half alone, returning its expiry", async () => {
    const k = pair();
    const signing = loadEnvironmentKeyRing({
      signing: 'k1',
      verify: [{ name: 'k1', pem: asSecretBytes(k.privatePem) }],
    });
    const verifying = loadVerifyKeyRing({
      verify: [{ name: 'e-agent-verify-key-1', pem: asSecretBytes(k.publicPem) }],
    });
    expect(verifying.kids).toEqual(signing.kids);
    expect(Object.keys(verifying)).not.toContain('signingKey');
    const expiresAt = new Date(T0.getTime() + 15 * 60_000);
    const token = await mintAgentCredential(
      {
        environment: E,
        agent: 'a',
        instance: 'i-1',
        cid: 'c1',
        jti: 'j1',
        issuedAt: T0,
        expiresAt,
      },
      signing,
    );
    const verified = await verifyAgentCredential(token, verifying, E, T0);
    expect(verified).toMatchObject({ ok: true, claims: { agent: 'a', cid: 'c1', expiresAt } });
  });

  it('refuses a token signed with a key it does not hold', async () => {
    const other = pair();
    const signing = loadEnvironmentKeyRing({
      signing: 'k1',
      verify: [{ name: 'k1', pem: asSecretBytes(other.privatePem) }],
    });
    const verifying = loadVerifyKeyRing({
      verify: [{ name: 'v1', pem: asSecretBytes(pair().publicPem) }],
    });
    const token = await mintAgentCredential(
      {
        environment: E,
        agent: 'a',
        instance: 'i-1',
        cid: 'c1',
        jti: 'j1',
        issuedAt: T0,
        expiresAt: new Date(T0.getTime() + 60_000),
      },
      signing,
    );
    expect(await verifyAgentCredential(token, verifying, E, T0)).toMatchObject({ ok: false });
  });

  it('refuses a private key, a repeated key, no key, a non-Ed25519 key, and a non-key', () => {
    const k = pair();
    const ec = generateKeyPairSync('ec', { namedCurve: 'P-256' }).publicKey;
    const ecPem = Buffer.from(ec.export({ format: 'pem', type: 'spki' }));
    expect(
      problems(() =>
        loadVerifyKeyRing({ verify: [{ name: 'p', pem: asSecretBytes(k.privatePem) }] }),
      ),
    ).toEqual(['p is a private key; only verify halves are accepted']);
    expect(
      problems(() =>
        loadVerifyKeyRing({
          verify: [
            { name: 'a', pem: asSecretBytes(k.publicPem) },
            { name: 'b', pem: asSecretBytes(k.publicPem) },
          ],
        }),
      )[0],
    ).toMatch(/^verify key b repeats a key already configured/);
    expect(problems(() => loadVerifyKeyRing({ verify: [] }))).toEqual([
      'no verify key is configured',
    ]);
    expect(
      problems(() => loadVerifyKeyRing({ verify: [{ name: 'ec', pem: asSecretBytes(ecPem) }] })),
    ).toEqual(['ec is not an Ed25519 key']);
    expect(
      problems(() =>
        loadVerifyKeyRing({ verify: [{ name: 'x', pem: asSecretBytes(Buffer.from('nope')) }] }),
      ),
    ).toEqual(['x is not a PEM public key']);
  });
});
