// SPDX-License-Identifier: FSL-1.1-ALv2
import { generateKeyPairSync, type KeyObject } from 'node:crypto';
import { SignJWT } from 'jose';
import { describe, expect, it } from 'vitest';
import {
  issuerOf,
  ORGANIZATION_TOLERANCE,
  SIGN_IN_PREFIX,
  SIGN_IN_TYP,
  thumbprint,
  verifySignIn,
  type SignInKeySource,
  type SignInTolerance,
} from '../src/index.ts';

const now = new Date('2026-11-11T12:00:00Z');
const at = (offsetSeconds: number): number => Math.floor(now.getTime() / 1000) + offsetSeconds;
const ENVIRONMENT: SignInTolerance = { expSeconds: 30, iatAheadSeconds: 30 };

function keyPair(): { privateKey: KeyObject; publicKey: KeyObject; kid: string } {
  const { privateKey, publicKey } = generateKeyPairSync('ed25519');
  return { privateKey, publicKey, kid: thumbprint(publicKey) };
}

function source(...keys: { publicKey: KeyObject; kid: string }[]): SignInKeySource {
  return {
    verifyKey: (kid) => keys.find((k) => k.kid === kid)?.publicKey,
    hasKeys: () => keys.length > 0,
  };
}

async function signIn(
  key: { privateKey: KeyObject; kid: string },
  claims: { iat: number; exp: number },
  header: { kid?: string | undefined } = {},
): Promise<string> {
  const kid = 'kid' in header ? header.kid : key.kid;
  const jws = await new SignJWT({ sid: 'a'.repeat(32), auth_time: claims.iat, amr: ['pwd'] })
    .setProtectedHeader({ alg: 'Ed25519', typ: SIGN_IN_TYP, ...(kid === undefined ? {} : { kid }) })
    .setIssuer(issuerOf('o1'))
    .setSubject('h@example.com')
    .setJti('j1')
    .setIssuedAt(claims.iat)
    .setExpirationTime(claims.exp)
    .sign(key.privateKey);
  return SIGN_IN_PREFIX + jws;
}

describe('TC-EHA-057: sign-in leeway at the token check, as an environment sets it (NFR-EHA-03)', () => {
  const key = keyPair();
  const keys = source(key);

  it('accepts a token 29 s past its expiry, and reports 31 s past as expired', async () => {
    const t29 = await signIn(key, { iat: at(-900 - 29), exp: at(-29) });
    const t31 = await signIn(key, { iat: at(-900 - 31), exp: at(-31) });
    expect((await verifySignIn(t29, keys, 'o1', now, ENVIRONMENT)).status).toBe('valid');
    expect((await verifySignIn(t31, keys, 'o1', now, ENVIRONMENT)).status).toBe('expired');
  });

  it('accepts an iat 30 s ahead and refuses one 31 s ahead (an explicit check)', async () => {
    const ahead30 = await signIn(key, { iat: at(30), exp: at(930) });
    const ahead31 = await signIn(key, { iat: at(31), exp: at(931) });
    expect((await verifySignIn(ahead30, keys, 'o1', now, ENVIRONMENT)).status).toBe('valid');
    expect((await verifySignIn(ahead31, keys, 'o1', now, ENVIRONMENT)).status).toBe('invalid');
  });

  it("the same tokens at the organization level's tolerance give its existing answers", async () => {
    const t29 = await signIn(key, { iat: at(-900 - 29), exp: at(-29) });
    const ahead31 = await signIn(key, { iat: at(31), exp: at(931) });
    expect((await verifySignIn(t29, keys, 'o1', now, ORGANIZATION_TOLERANCE)).status).toBe(
      'expired',
    );
    expect((await verifySignIn(t29, keys, 'o1', now)).status).toBe('expired');
    // No iat check at the organization level (U2 P-01), as before.
    expect((await verifySignIn(ahead31, keys, 'o1', now)).status).toBe('valid');
  });
});

describe('TC-EHA-064: an unknown kid is distinct from an invalid token (NP-EHA-15)', () => {
  const key = keyPair();
  const other = keyPair();

  it('a kid the source does not hold is unknownKey; with the key, it verifies', async () => {
    const token = await signIn(other, { iat: at(0), exp: at(900) });
    expect((await verifySignIn(token, source(key), 'o1', now)).status).toBe('unknownKey');
    expect((await verifySignIn(token, source(key, other), 'o1', now)).status).toBe('valid');
  });

  it('a missing kid stays invalid: a fetch could not help it', async () => {
    const token = await signIn(key, { iat: at(0), exp: at(900) }, { kid: undefined });
    expect((await verifySignIn(token, source(key), 'o1', now)).status).toBe('invalid');
  });

  it('an empty key source answers unknownKey for any kid', async () => {
    const token = await signIn(key, { iat: at(0), exp: at(900) });
    expect((await verifySignIn(token, source(), 'o1', now)).status).toBe('unknownKey');
  });
});

describe('TC-EHA-065: the key source is read on every verification (NP-EHA-15)', () => {
  it('a key added between two verifications is seen by the second', async () => {
    const key = keyPair();
    const held: { publicKey: KeyObject; kid: string }[] = [];
    const cache: SignInKeySource = {
      verifyKey: (kid) => held.find((k) => k.kid === kid)?.publicKey,
      hasKeys: () => held.length > 0,
    };
    const token = await signIn(key, { iat: at(0), exp: at(900) });
    expect((await verifySignIn(token, cache, 'o1', now)).status).toBe('unknownKey');
    held.push(key);
    expect((await verifySignIn(token, cache, 'o1', now)).status).toBe('valid');
  });
});
