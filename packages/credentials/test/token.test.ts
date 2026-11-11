// SPDX-License-Identifier: FSL-1.1-ALv2
//
// P5's token and key ring, with no store: NP-EHA-01 steps 1 to 8, NP-EHA-02.
import { generateKeyPairSync } from 'node:crypto';
import { newRecordId } from '@soorma/env-store';
import {
  asSecretBytes,
  asSecretText,
  KeyMaterialError,
  type SecretText,
} from '@soorma/service-kit';
import { SignJWT } from 'jose';
import { describe, expect, it } from 'vitest';
import {
  loadEnvironmentKeyRing,
  mintEnvironmentCredential,
  verifyEnvironmentCredential,
  type CredentialClaims,
  type EnvironmentKeyRing,
} from '../src/index.ts';

const E = { organization: 'o1', project: 'p1', environment: 'e' };
const now = new Date('2026-11-11T12:00:00Z');
const MINUTE = 60_000;

function pem() {
  const { privateKey } = generateKeyPairSync('ed25519');
  return asSecretBytes(Buffer.from(privateKey.export({ format: 'pem', type: 'pkcs8' })));
}

function ring(...names: string[]): {
  ring: EnvironmentKeyRing;
  pems: Map<string, ReturnType<typeof pem>>;
} {
  const pems = new Map(names.map((n) => [n, pem()] as const));
  return {
    ring: loadEnvironmentKeyRing({
      signing: names[0]!,
      verify: names.map((name) => ({ name, pem: pems.get(name)! })),
    }),
    pems,
  };
}

const claims = (over: Partial<CredentialClaims> = {}): CredentialClaims => ({
  environment: E,
  principal: 'h@example.com',
  cid: newRecordId(),
  jti: newRecordId(),
  issuedAt: now,
  expiresAt: new Date(now.getTime() + 15 * MINUTE),
  ...over,
});

const { ring: E_RING } = ring('e-signing-key-1');
const { ring: E2_RING } = ring('e2-signing-key-1');

async function rawToken(
  header: Record<string, unknown>,
  payload: Record<string, unknown>,
  signer: EnvironmentKeyRing = E_RING,
): Promise<SecretText> {
  const iat = Math.floor(now.getTime() / 1000);
  const jws = await new SignJWT({
    env: E,
    sub: 'h@example.com',
    cid: 'c1',
    jti: 'j1',
    iat,
    exp: iat + 900,
    ...payload,
  })
    .setProtectedHeader({ alg: 'Ed25519', typ: 'soorma-ec+jwt', kid: signer.signingKid, ...header })
    .sign(signer.signingKey);
  return asSecretText(`soorma_ec_${jws}`);
}

const verify = (token: SecretText, at = now, r = E_RING, env = E) =>
  verifyEnvironmentCredential(token, r, env, at);

describe('TC-EHA-002: a minted token verifies, with exactly its claims', () => {
  it('round-trips env, sub, cid, jti, iat, exp; the header is alg Ed25519, typ soorma-ec+jwt, kid', async () => {
    const c = claims();
    const token = await mintEnvironmentCredential(c, E_RING);
    expect(token.startsWith('soorma_ec_')).toBe(true);
    const header = JSON.parse(Buffer.from(token.slice(10).split('.')[0]!, 'base64url').toString());
    expect(header).toEqual({ alg: 'Ed25519', typ: 'soorma-ec+jwt', kid: E_RING.signingKid });
    const payload = JSON.parse(Buffer.from(token.split('.')[1]!, 'base64url').toString()) as object;
    expect(Object.keys(payload).sort()).toEqual(['cid', 'env', 'exp', 'iat', 'jti', 'sub']);
    expect(await verify(token)).toEqual({ ok: true, claims: c });
  });
});

describe('TC-EHA-073: each malformed or altered credential is refused at its step', () => {
  it.each([
    [
      'a wrong prefix',
      async () => asSecretText((await rawToken({}, {})).replace('soorma_ec_', 'soorma_si_')),
      'malformed',
    ],
    [
      '4097 characters',
      () => Promise.resolve(asSecretText(`soorma_ec_${'a'.repeat(4087)}`)),
      'malformed',
    ],
    ['typ JWT', () => rawToken({ typ: 'JWT' }, {}), 'claims'],
    ['an unknown kid', () => rawToken({ kid: 'unknown' }, {}), 'unknown_key'],
    ['a token minted by E2', () => rawToken({}, {}, E2_RING), 'unknown_key'],
    ['no env', () => rawToken({}, { env: undefined }), 'claims'],
    ['no sub', () => rawToken({}, { sub: undefined }), 'claims'],
    ['no cid', () => rawToken({}, { cid: undefined }), 'claims'],
    ['no jti', () => rawToken({}, { jti: undefined }), 'claims'],
    ['no iat', () => rawToken({}, { iat: undefined }), 'claims'],
    [
      'an env missing its project',
      () => rawToken({}, { env: { organization: 'o1', environment: 'e' } }),
      'claims',
    ],
  ])('refuses %s', async (_name, make, reason) => {
    expect(await verify(await make())).toEqual({ ok: false, code: 'credential_refused', reason });
  });

  it('refuses alg EdDSA (the algorithm is fixed in code)', async () => {
    const r = await verify(await rawToken({ alg: 'EdDSA' }, {}));
    expect(r.ok).toBe(false);
    if (!r.ok) expect(r.code).toBe('credential_refused');
  });

  it('refuses a flipped signature byte', async () => {
    const token = await rawToken({}, {});
    const parts = token.split('.');
    const sig = Buffer.from(parts[2]!, 'base64url');
    sig[0] = sig[0]! ^ 1;
    const r = await verify(asSecretText(`${parts[0]}.${parts[1]}.${sig.toString('base64url')}`));
    expect(r).toEqual({ ok: false, code: 'credential_refused', reason: 'signature' });
  });

  it('a token from E2 at E is refused before its expiry is read (BR-EC-03; TC-EHA-010)', async () => {
    const expired = await mintEnvironmentCredential(
      claims({
        environment: { ...E, environment: 'e2' },
        expiresAt: new Date(now.getTime() - MINUTE),
      }),
      E2_RING,
    );
    expect(await verify(expired)).toEqual({
      ok: false,
      code: 'credential_refused',
      reason: 'unknown_key',
    });
  });
});

describe('TC-EHA-056: no exp leeway; iat up to 30 seconds ahead', () => {
  it('accepts 1 ms before exp, and reports expiry at exp', async () => {
    const token = await mintEnvironmentCredential(claims(), E_RING);
    const exp = now.getTime() + 15 * MINUTE;
    expect((await verify(token, new Date(exp - 1))).ok).toBe(true);
    expect(await verify(token, new Date(exp))).toEqual({
      ok: false,
      code: 'credential_expired',
      reason: 'expired',
    });
  });

  it('accepts an iat 30 s ahead and refuses one 31 s ahead', async () => {
    const at = (s: number) => new Date(now.getTime() + s * 1000);
    const ahead30 = await mintEnvironmentCredential(
      claims({ issuedAt: at(30), expiresAt: at(930) }),
      E_RING,
    );
    const ahead31 = await mintEnvironmentCredential(
      claims({ issuedAt: at(31), expiresAt: at(931) }),
      E_RING,
    );
    expect((await verify(ahead30)).ok).toBe(true);
    expect(await verify(ahead31)).toEqual({
      ok: false,
      code: 'credential_refused',
      reason: 'issued_ahead',
    });
  });

  it('never reports a malformed but signed token as expired', async () => {
    const past = Math.floor(now.getTime() / 1000) - 60;
    const r = await verify(await rawToken({}, { exp: past, cid: undefined }));
    expect(r).toEqual({ ok: false, code: 'credential_refused', reason: 'claims' });
  });
});

describe("TC-EHA-045: a credential asserting another environment, signed with E's key, is refused", () => {
  it.each([
    ['organization', { ...E, organization: 'o2' }],
    ['project', { ...E, project: 'p2' }],
    ['environment', { ...E, environment: 'e2' }],
  ])('refuses an altered %s', async (_field, env) => {
    expect(
      await verify(await mintEnvironmentCredential(claims({ environment: env }), E_RING)),
    ).toEqual({ ok: false, code: 'credential_refused', reason: 'wrong_environment' });
  });
});

describe('TC-EHA-036 (the key ring): S2 refuses a bad key ring at start-up (NP-EHA-02)', () => {
  const good = pem();
  const p256 = asSecretBytes(
    Buffer.from(
      generateKeyPairSync('ec', { namedCurve: 'P-256' }).privateKey.export({
        format: 'pem',
        type: 'pkcs8',
      }),
    ),
  );
  const refusal = (fn: () => unknown): readonly string[] => {
    try {
      fn();
    } catch (error) {
      if (error instanceof KeyMaterialError) return error.problems;
      throw error;
    }
    throw new Error('expected a KeyMaterialError');
  };

  it.each([
    [
      'a P-256 key',
      { signing: 'k1', verify: [{ name: 'k1', pem: p256 }] },
      'k1 is not an Ed25519 key',
    ],
    [
      'not a PEM key',
      { signing: 'k1', verify: [{ name: 'k1', pem: asSecretBytes(Buffer.from('nope')) }] },
      'k1 is not a PEM private key',
    ],
    [
      'a signing key not among the verify keys',
      { signing: 'k9', verify: [{ name: 'k1', pem: good }] },
      'the signing key k9 is not among the verify keys',
    ],
    [
      'one key twice',
      {
        signing: 'k1',
        verify: [
          { name: 'k1', pem: good },
          { name: 'k2', pem: good },
        ],
      },
      'verify key k2 repeats a key already configured',
    ],
    ['no verify key', { signing: 'k1', verify: [] }, 'no verify key is configured'],
  ])('refuses %s', (_name, input, message) => {
    expect(refusal(() => loadEnvironmentKeyRing(input)).join('\n')).toContain(message);
  });
});

describe("TC-EHA-075: E's minting key rotates by configuration (NP-EHA-02)", () => {
  it('a token under key 1 verifies while key 1 is a verify key, and is refused once it is removed', async () => {
    const k1 = pem();
    const k2 = pem();
    const one = loadEnvironmentKeyRing({ signing: 'k1', verify: [{ name: 'k1', pem: k1 }] });
    const token = await mintEnvironmentCredential(claims(), one);
    const added = loadEnvironmentKeyRing({
      signing: 'k1',
      verify: [
        { name: 'k1', pem: k1 },
        { name: 'k2', pem: k2 },
      ],
    });
    expect((await verify(token, now, added)).ok).toBe(true);
    const switched = loadEnvironmentKeyRing({
      signing: 'k2',
      verify: [
        { name: 'k1', pem: k1 },
        { name: 'k2', pem: k2 },
      ],
    });
    const next = await mintEnvironmentCredential(claims(), switched);
    const header = JSON.parse(Buffer.from(next.slice(10).split('.')[0]!, 'base64url').toString());
    expect(header.kid).toBe(switched.signingKid);
    expect(header.kid).not.toBe(one.signingKid);
    expect((await verify(token, now, switched)).ok).toBe(true);
    const removed = loadEnvironmentKeyRing({ signing: 'k2', verify: [{ name: 'k2', pem: k2 }] });
    expect(await verify(token, now, removed)).toEqual({
      ok: false,
      code: 'credential_refused',
      reason: 'unknown_key',
    });
  });
});

describe('TC-EHA-072: record and token ids are 128 random bits, base64url', () => {
  it('22 base64url characters, no padding, all distinct', () => {
    const ids = Array.from({ length: 1000 }, () => newRecordId());
    for (const id of ids) expect(id).toMatch(/^[A-Za-z0-9_-]{22}$/);
    expect(new Set(ids).size).toBe(1000);
  });
});
