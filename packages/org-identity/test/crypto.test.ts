// SPDX-License-Identifier: FSL-1.1-ALv2
// Cryptography and keys: TC-OI-003 (token), 039, 043, 044, 052 (step 3), 054;
// P-01 to 03, 09, 10, 12; NFR-OI-07 to 12, 20, 29, 30.
import { execFileSync } from 'node:child_process';
import { generateKeyPairSync, randomBytes } from 'node:crypto';
import { calculateJwkThumbprint, decodeJwt, decodeProtectedHeader, SignJWT } from 'jose';
import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest';
import {
  asSecretBytes,
  asSecretText,
  asTotpCode,
  asVerifier,
  canonicalJson,
  KeyMaterialError,
  pseudonym,
  secretEqual,
  thumbprint,
  UnavailableError,
  verifySignIn,
} from '@soorma/service-kit';
import {
  base32,
  codeAt,
  decryptSeed,
  defaultPermits,
  encryptSeed,
  HashSemaphore,
  KeyRing,
  matchStep,
  mintSignIn,
  newSeed,
  otpauthUri,
  SecretHasher,
  SeedDecryptionError,
  stepAt,
  type KeyMaterialInput,
} from '../src/index.ts';

function pem(): { privatePem: Buffer; publicPem: Buffer } {
  const { privateKey, publicKey } = generateKeyPairSync('ed25519');
  return {
    privatePem: Buffer.from(privateKey.export({ format: 'pem', type: 'pkcs8' })),
    publicPem: Buffer.from(publicKey.export({ format: 'pem', type: 'spki' })),
  };
}

const signing = pem();
const caller = pem();

function material(change: Partial<KeyMaterialInput> = {}): KeyMaterialInput {
  return {
    signingKey: signing.privatePem,
    verifyKeys: [],
    seedKeys: { current: 's1', keys: [{ id: 's1', key: randomBytes(32) }] },
    counterSecret: randomBytes(32),
    logPseudonymKey: randomBytes(32),
    internalCallers: [{ environment: 'e', publicKey: caller.publicPem }],
    ...change,
  };
}

const keys = KeyRing.fromConfiguration(material());
const H = { organization: 'o1', principal: 'h@example.com' };

afterEach(() => {
  vi.useRealTimers();
});

describe('secretEqual (NFR-OI-29)', () => {
  it('compares values of any length, in constant time over their digests', () => {
    expect(secretEqual(asSecretText('abc'), asSecretText('abc'))).toBe(true);
    expect(secretEqual(asSecretText('abc'), asSecretText('abcd'))).toBe(false);
    expect(secretEqual(Buffer.from('x'), asSecretBytes(Buffer.from('x')))).toBe(true);
  });
});

describe('P-09: the hashing semaphore (TC-OI-052 step 3)', () => {
  it('defaults to the lower of 2 × CPUs and the budget ÷ 64 MiB, at least 1', () => {
    expect(defaultPermits(512, 16)).toBe(8);
    expect(defaultPermits(512, 2)).toBe(4);
    expect(defaultPermits(64, 8)).toBe(1);
    expect(defaultPermits(32, 8)).toBe(1);
  });

  it('refuses with unavailable after 2 seconds when every permit is held', async () => {
    vi.useFakeTimers();
    const semaphore = new HashSemaphore(1);
    let release!: () => void;
    const gate = new Promise<void>((r) => (release = r));
    const held = semaphore.run(() => gate);
    const waiting = semaphore.run(() => Promise.resolve('never'));
    const outcome = waiting.catch((e: unknown) => e);
    await vi.advanceTimersByTimeAsync(1999);
    await vi.advanceTimersByTimeAsync(1);
    const error = await outcome;
    expect(error).toBeInstanceOf(UnavailableError);
    expect((error as UnavailableError).retryAfterSeconds).toBe(2);
    release();
    await held;
  });

  it('serves waiters first in, first out, and frees the permit after an error', async () => {
    const semaphore = new HashSemaphore(1, 10_000);
    const order: number[] = [];
    let release!: () => void;
    const gate = new Promise<void>((r) => (release = r));
    const first = semaphore.run(() => gate);
    const second = semaphore.run(() => Promise.resolve(order.push(2)));
    const third = semaphore.run(() => Promise.resolve(order.push(3)));
    release();
    await Promise.all([first, second, third]);
    expect(order).toEqual([2, 3]);
    await expect(semaphore.run(() => Promise.reject(new Error('x')))).rejects.toThrow('x');
    await expect(semaphore.run(() => Promise.resolve(1))).resolves.toBe(1);
  });
});

describe('TC-OI-043: K is stored only as Argon2id over the full normalized input', () => {
  const hasher = new SecretHasher(new HashSemaphore(4));
  beforeAll(async () => {
    await hasher.prepareDecoy();
  });

  it('stores a PHC string recording argon2id and its parameters, never the secret', async () => {
    const k = asSecretText('correct horse battery staple');
    const verifier = await hasher.hash(k);
    expect(verifier).toMatch(
      /^\$argon2id\$v=19\$m=65536,t=3,p=1\$[A-Za-z0-9+/]{22}\$[A-Za-z0-9+/]{43}$/,
    );
    expect(verifier).not.toContain(k);
    expect(await hasher.verify(k, verifier)).toBe(true);
    expect(await hasher.verify(asSecretText('correct horse battery stapler'), verifier)).toBe(
      false,
    );
    expect(await hasher.hash(k)).not.toBe(verifier);
  });

  it('hashes the whole input: Ks differing only after byte 72, or in the 256th code point, differ', async () => {
    const prefix = 'p'.repeat(80);
    const a = await hasher.hash(asSecretText(`${prefix}a`));
    expect(await hasher.verify(asSecretText(`${prefix}b`), a)).toBe(false);
    const base = 'é'.repeat(255);
    const b = await hasher.hash(asSecretText(`${base}x`));
    expect(await hasher.verify(asSecretText(`${base}y`), b)).toBe(false);
    expect(await hasher.verify(asSecretText(`${base}x`), b)).toBe(true);
  });

  it('hashes the NFKC form: composed and decomposed input verify alike', async () => {
    const verifier = await hasher.hash(asSecretText('café-passphrase'));
    expect(await hasher.verify(asSecretText('café-passphrase'), verifier)).toBe(true);
  });

  it('never matches a malformed verifier, and the decoy always fails', async () => {
    expect(await hasher.verify(asSecretText('x'), asVerifier('$scrypt$whatever'))).toBe(false);
    expect(await hasher.verifyDecoy(asSecretText('anything'))).toBe(false);
  });

  it('crypto.argon2 emits no ExperimentalWarning (Q-CG-1 A; stop condition 4)', () => {
    const script = `
      const warnings = [];
      process.on('warning', (w) => warnings.push(w.name));
      const { argon2 } = await import('node:crypto');
      await new Promise((resolve, reject) => argon2('argon2id', {
        message: Buffer.from('x'), nonce: Buffer.alloc(16), memory: 8192, passes: 1,
        parallelism: 1, tagLength: 32 }, (e) => (e ? reject(e) : resolve())));
      await new Promise((r) => setImmediate(r));
      console.log(JSON.stringify(warnings));
    `;
    const out = execFileSync(process.execPath, ['--input-type=module', '--eval', script], {
      encoding: 'utf8',
      stdio: ['ignore', 'pipe', 'pipe'],
    });
    expect(JSON.parse(out.trim()) as string[]).not.toContain('ExperimentalWarning');
  });
});

describe('P-02: the key ring', () => {
  it('serves only public keys, with RFC 7638 thumbprints as kid', async () => {
    const jwks = keys.jwks();
    expect(jwks.keys).toHaveLength(1);
    const [jwk] = jwks.keys;
    expect(jwk).not.toHaveProperty('d');
    expect(jwk!.kid).toBe(await calculateJwkThumbprint({ kty: 'OKP', crv: 'Ed25519', x: jwk!.x }));
    expect(keys.signingKid).toBe(jwk!.kid);
    expect(keys.callerByKid(thumbprint(keys.callers[0]!.key))?.environment).toBe('e');
  });

  it('refuses malformed or missing key material, listing every problem', () => {
    const notEd = Buffer.from(
      generateKeyPairSync('ec', { namedCurve: 'P-256' }).privateKey.export({
        format: 'pem',
        type: 'pkcs8',
      }),
    );
    let problems: readonly string[] = [];
    try {
      KeyRing.fromConfiguration(
        material({
          signingKey: notEd,
          verifyKeys: [Buffer.from('nope')],
          seedKeys: { current: 's2', keys: [{ id: 's1', key: randomBytes(16) }] },
          counterSecret: randomBytes(8),
          internalCallers: [{ environment: 'e', publicKey: Buffer.from('nope') }],
        }),
      );
    } catch (error) {
      expect(error).toBeInstanceOf(KeyMaterialError);
      problems = (error as KeyMaterialError).problems;
    }
    expect(problems).toEqual([
      'the signing key is not an Ed25519 private key',
      'verify key 0 is not a PEM public key',
      'seed key s1 is not 256 bits',
      'the current seed key is not configured',
      'the counter secret is under 256 bits',
      'the caller key for environment e is not a PEM public key',
    ]);
  });
});

describe('TC-OI-044: sign-in verification is strict, and the token asserts no environment', () => {
  const now = new Date('2026-11-08T12:00:00Z');
  const mint = () =>
    mintSignIn(
      {
        ...H,
        sid: 'sid-1',
        authenticatedAt: now,
        classes: ['K', 'P'],
        issuedAt: now,
        expiresAt: new Date(now.getTime() + 15 * 60_000),
      },
      keys,
    );

  it('mints soorma_si_ + an Ed25519 JWT with every claim, and no aud or environment', async () => {
    const { token, claims } = await mint();
    expect(token).toMatch(/^soorma_si_[A-Za-z0-9._~+/-]+=*$/);
    expect(token.length).toBeLessThanOrEqual(4096);
    const jws = token.slice('soorma_si_'.length);
    expect(decodeProtectedHeader(jws)).toEqual({
      alg: 'Ed25519',
      typ: 'soorma-si+jwt',
      kid: keys.signingKid,
    });
    const payload = decodeJwt(jws);
    expect(Object.keys(payload).sort()).toEqual(
      ['amr', 'auth_time', 'exp', 'iat', 'iss', 'jti', 'sid', 'sub'].sort(),
    );
    expect(payload).toMatchObject({
      iss: 'urn:soorma:org:o1',
      sub: 'h@example.com',
      sid: 'sid-1',
      amr: ['pwd', 'otp'],
    });
    expect(claims.classes).toEqual(['K', 'P']);
    expect(await verifySignIn(token, keys, 'o1', now)).toEqual({ status: 'valid', claims });
  });

  it('reports expiry only at or after exp, with no leeway', async () => {
    const { token } = await mint();
    const exp = new Date(now.getTime() + 15 * 60_000);
    expect((await verifySignIn(token, keys, 'o1', new Date(exp.getTime() - 1000))).status).toBe(
      'valid',
    );
    expect((await verifySignIn(token, keys, 'o1', exp)).status).toBe('expired');
  });

  it('refuses another organization, a missing prefix, and a tampered signature', async () => {
    const { token } = await mint();
    expect((await verifySignIn(token, keys, 'o2', now)).status).toBe('invalid');
    expect((await verifySignIn(token.slice(10), keys, 'o1', now)).status).toBe('invalid');
    const tampered = token.slice(0, -2) + (token.endsWith('AA') ? 'BB' : 'AA');
    expect((await verifySignIn(tampered, keys, 'o1', now)).status).toBe('invalid');
  });

  async function forged(
    header: Record<string, string>,
    claims: Record<string, unknown>,
    key = keys.signingKey,
  ): Promise<string> {
    const base = {
      iss: 'urn:soorma:org:o1',
      sub: 'h@example.com',
      sid: 'sid-1',
      jti: 'j',
      iat: Math.floor(now.getTime() / 1000),
      exp: Math.floor(now.getTime() / 1000) + 900,
      auth_time: Math.floor(now.getTime() / 1000),
      amr: ['pwd'],
    };
    const jwt = await new SignJWT({ ...base, ...claims })
      .setProtectedHeader({ alg: 'Ed25519', typ: 'soorma-si+jwt', kid: keys.signingKid, ...header })
      .sign(key);
    return `soorma_si_${jwt}`;
  }

  it.each([
    ['another typ', { typ: 'JWT' }, {}],
    ['EdDSA', { alg: 'EdDSA' }, {}],
    ['no sid', {}, { sid: undefined }],
    ['no auth_time', {}, { auth_time: undefined }],
    ['no amr', {}, { amr: undefined }],
    ['an amr without pwd', {}, { amr: ['otp'] }],
    ['an unknown amr', {}, { amr: ['pwd', 'hwk'] }],
  ])('refuses a token with %s', async (_name, header, claims) => {
    const token = await forged(header, claims);
    expect((await verifySignIn(token, keys, 'o1', now)).status).toBe('invalid');
  });

  it('answers unknownKey for a token with an unknown kid (U4 D-CG-EHA-16)', async () => {
    const token = await forged({ kid: 'unknown' }, {});
    expect((await verifySignIn(token, keys, 'o1', now)).status).toBe('unknownKey');
  });

  it('never reports an expired token as expired unless its form verified', async () => {
    const past = Math.floor(now.getTime() / 1000) - 10;
    const malformed = await forged({}, { exp: past, amr: undefined });
    expect((await verifySignIn(malformed, keys, 'o1', now)).status).toBe('invalid');
    const wellFormed = await forged({}, { exp: past });
    expect((await verifySignIn(wellFormed, keys, 'o1', now)).status).toBe('expired');
  });

  it('a key moved to verify-only still verifies; once removed, it is refused (P-02 rotation)', async () => {
    const { token } = await mint();
    const next = pem();
    const rotated = KeyRing.fromConfiguration(
      material({ signingKey: next.privatePem, verifyKeys: [signing.publicPem] }),
    );
    expect((await verifySignIn(token, rotated, 'o1', now)).status).toBe('valid');
    const removed = KeyRing.fromConfiguration(material({ signingKey: next.privatePem }));
    expect((await verifySignIn(token, removed, 'o1', now)).status).toBe('unknownKey');
  });
});

describe('TC-OI-039: TOTP follows RFC 6238, with one step of drift, each code accepted once', () => {
  const rfcSeed = asSecretBytes(Buffer.from('12345678901234567890'));

  it.each([
    [59, '94287082'],
    [1111111109, '07081804'],
    [1111111111, '14050471'],
    [1234567890, '89005924'],
    [2000000000, '69279037'],
    [20000000000, '65353130'],
  ])('matches RFC 6238 Appendix B (SHA-1) at T = %i', (t, expected) => {
    const step = stepAt(new Date(t * 1000));
    expect(codeAt(rfcSeed, step, 8)).toBe(expected);
    expect(codeAt(rfcSeed, step)).toBe(expected.slice(2));
  });

  it('accepts one step of drift either side, and not two', () => {
    const seed = newSeed();
    const now = new Date('2026-11-08T12:00:10Z');
    const step = stepAt(now);
    for (const d of [-1, 0, 1])
      expect(matchStep(seed, codeAt(seed, step + d), now, null)).toBe(step + d);
    for (const d of [-2, 2])
      expect(matchStep(seed, codeAt(seed, step + d), now, null)).toBeUndefined();
    expect(matchStep(seed, asTotpCode('000000'), now, null)).toBe(
      codeAt(seed, step - 1) === '000000' ||
        codeAt(seed, step) === '000000' ||
        codeAt(seed, step + 1) === '000000'
        ? expect.any(Number)
        : undefined,
    );
  });

  it('refuses a code for the last accepted step, or an earlier one', () => {
    const seed = newSeed();
    const now = new Date('2026-11-08T12:00:10Z');
    const step = stepAt(now);
    expect(matchStep(seed, codeAt(seed, step), now, step)).toBeUndefined();
    expect(matchStep(seed, codeAt(seed, step - 1), now, step - 1)).toBeUndefined();
    expect(matchStep(seed, codeAt(seed, step + 1), now, step)).toBe(step + 1);
  });

  it('makes 160-bit seeds, and the Base32 and otpauth forms authenticators read', () => {
    expect(newSeed()).toHaveLength(20);
    expect(base32(Buffer.from('foobar'))).toBe('MZXW6YTBOI');
    expect(base32(Buffer.from('f'))).toBe('MY');
    expect(otpauthUri(rfcSeed, 'o1', 'h@example.com')).toBe(
      'otpauth://totp/soorma:o1:h%40example.com?secret=GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ' +
        '&issuer=soorma&algorithm=SHA1&digits=6&period=30',
    );
  });
});

describe('TC-OI-054: TOTP seeds are encrypted and bound to their row', () => {
  it('stores no plaintext, decrypts in its own row only, and fails closed on an unknown key', () => {
    const seed = newSeed();
    const stored = encryptSeed(seed, H, 'record-1', keys);
    expect(stored.keyId).toBe('s1');
    expect(Buffer.from(stored.ciphertext, 'base64url').equals(seed)).toBe(false);
    expect(decryptSeed(stored, H, 'record-1', keys).equals(seed)).toBe(true);
    expect(() => decryptSeed(stored, H, 'record-2', keys)).toThrow(SeedDecryptionError);
    expect(() =>
      decryptSeed(stored, { ...H, principal: 'g@example.com' }, 'record-1', keys),
    ).toThrow(SeedDecryptionError);
    expect(() => decryptSeed({ ...stored, keyId: 's9' }, H, 'record-1', keys)).toThrow(
      SeedDecryptionError,
    );
    expect(encryptSeed(seed, H, 'record-1', keys).nonce).not.toBe(stored.nonce);
  });
});

describe('the log pseudonym and canonical JSON (NFR-OI-22; P-17)', () => {
  it('serializes a reference in RFC 8785 form', () => {
    expect(canonicalJson({ principal: 'h@example.com', organization: 'o1' })).toBe(
      '{"organization":"o1","principal":"h@example.com"}',
    );
    expect(canonicalJson({ b: 1, a: { d: 'x', c: 2 } })).toBe('{"a":{"c":2,"d":"x"},"b":1}');
  });

  it('is hp_ + 128 bits, keyed, deterministic, and carries no part of the identifier', () => {
    const key = asSecretBytes(randomBytes(32));
    const p = pseudonym(H, key);
    expect(p).toMatch(/^hp_[A-Za-z0-9_-]{22}$/);
    expect(pseudonym(H, key)).toBe(p);
    expect(pseudonym(H, asSecretBytes(randomBytes(32)))).not.toBe(p);
    expect(pseudonym({ ...H, organization: 'o2' }, key)).not.toBe(p);
    expect(p).not.toContain('example');
  });
});
