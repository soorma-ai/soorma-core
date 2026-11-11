// SPDX-License-Identifier: FSL-1.1-ALv2
//
// TC-OI-044's "refused", where S1 serves it (U4 D-CG-EHA-16). verifySignIn now
// answers `unknownKey` for a kid the key ring lacks; P1 at S1's settings, with
// no refetch, still answers credential_refused for those tokens.
import { generateKeyPairSync, randomBytes } from 'node:crypto';
import { KeyRing, mintSignIn } from '@soorma/org-identity';
import {
  ORGANIZATION_TOLERANCE,
  verifySignIn,
  type Clock,
  type SignInStatus,
} from '@soorma/service-kit';
import { describe, expect, it } from 'vitest';
import { SignInPerimeter } from '../src/index.ts';

const pem = () => {
  const { privateKey, publicKey } = generateKeyPairSync('ed25519');
  return {
    privatePem: Buffer.from(privateKey.export({ format: 'pem', type: 'pkcs8' })),
    publicPem: Buffer.from(publicKey.export({ format: 'pem', type: 'spki' })),
  };
};

function ring(signingKey: Buffer, verifyKeys: Buffer[] = []): KeyRing {
  return KeyRing.fromConfiguration({
    signingKey,
    verifyKeys,
    seedKeys: { current: 's1', keys: [{ id: 's1', key: randomBytes(32) }] },
    counterSecret: randomBytes(32),
    logPseudonymKey: randomBytes(32),
    internalCallers: [],
  });
}

const now = new Date('2026-11-11T12:00:00Z');
const clock: Clock = { now: () => now };
const live = (): Promise<SignInStatus> =>
  Promise.resolve({ status: 'live', expiresAt: new Date(now.getTime() + 15 * 60_000) });

/** P1 exactly as S1 builds it: its own tolerance, no refetch (services/org-gateway runtime.ts). */
const atS1 = (keys: KeyRing) =>
  new SignInPerimeter(keys, 'o1', clock, live, { tolerance: ORGANIZATION_TOLERANCE });

const header = (token: string): string[] => ['Authorization', `Bearer ${token}`];

async function mint(keys: KeyRing): Promise<string> {
  return (
    await mintSignIn(
      {
        organization: 'o1',
        principal: 'h@example.com',
        sid: 'sid-1',
        authenticatedAt: now,
        classes: ['K'],
        issuedAt: now,
        expiresAt: new Date(now.getTime() + 15 * 60_000),
      },
      keys,
    )
  ).token;
}

describe('TC-OI-044 at S1: tokens verifySignIn answers unknownKey for are credential_refused (D-CG-EHA-16)', () => {
  it('a token with an unknown kid', async () => {
    const keys = ring(pem().privatePem);
    const token = await mint(ring(pem().privatePem));
    expect((await verifySignIn(token, keys, 'o1', now)).status).toBe('unknownKey');
    expect(await atS1(keys).check(header(token))).toEqual({
      accepted: false,
      code: 'credential_refused',
    });
  });

  it('a token whose key was removed after a rotation (P-02)', async () => {
    const old = pem();
    const next = pem();
    const token = await mint(ring(old.privatePem));
    const removed = ring(next.privatePem);
    expect((await verifySignIn(token, removed, 'o1', now)).status).toBe('unknownKey');
    expect(await atS1(removed).check(header(token))).toEqual({
      accepted: false,
      code: 'credential_refused',
    });
  });
});
