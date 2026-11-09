// SPDX-License-Identifier: FSL-1.1-ALv2
// Identity resolution behind the seam: TC-OI-060; TC-OI-029 (its structure at
// this level: one Argon2id call per resolution, with the real parameters, the
// decoy for an absent principal or record); BR-SEAM-01, 02; P-10.
import { generateKeyPairSync, randomBytes } from 'node:crypto';
import {
  ARGON2_PARAMETERS,
  asSecretText,
  codeAt,
  encryptSeed,
  HashSemaphore,
  KeyRing,
  newSeed,
  SecretHasher,
  stepAt,
  type Argon2Call,
  type Clock,
} from '@soorma/org-identity';
import { afterAll, beforeAll, beforeEach, describe, expect, it } from 'vitest';
import { testDatabase, type TestDatabase } from '../../org-identity/test/harness/database.ts';
import { recordingArgon2id } from '../../org-identity/test/harness/domain.ts';
import { StoreIdentityResolver } from '../src/index.ts';

const H = { organization: 'o1', principal: 'h@example.com' };
const G = { organization: 'o1', principal: 'g@example.com' };
const K = 'purple garden lantern';
const ENROLLMENT = `soorma_em_${randomBytes(32).toString('base64url')}`;
const NOW = new Date('2026-11-08T12:00:10Z');
const clock: Clock = { now: () => NOW };

const calls: Argon2Call[] = [];
const recording = recordingArgon2id(calls);

const keys = KeyRing.fromConfiguration({
  signingKey: Buffer.from(
    generateKeyPairSync('ed25519').privateKey.export({ format: 'pem', type: 'pkcs8' }),
  ),
  verifyKeys: [],
  seedKeys: { current: 's1', keys: [{ id: 's1', key: randomBytes(32) }] },
  counterSecret: randomBytes(32),
  logPseudonymKey: randomBytes(32),
  internalCallers: [],
});
const hasher = new SecretHasher(new HashSemaphore(4), recording);
const seed = newSeed();

let db: TestDatabase;
let resolver: StoreIdentityResolver;

async function snapshot(): Promise<unknown> {
  const su = await db.superuser();
  try {
    const p = await su.query('SELECT * FROM principals ORDER BY principal');
    const m = await su.query('SELECT * FROM materials ORDER BY id');
    const s = await su.query('SELECT * FROM sign_ins ORDER BY id');
    return { p: p.rows, m: m.rows, s: s.rows };
  } finally {
    await su.end();
  }
}

beforeAll(async () => {
  db = await testDatabase();
  await hasher.prepareDecoy();
  const app = await db.app();
  try {
    // H: active, with K and P. G: pending, with enrollment material.
    await app.query(
      `INSERT INTO principals (organization, principal, state, registered_at, registered_by_environment, activated_at)
       VALUES ('o1', 'h@example.com', 'active', now(), 'e', now()),
              ('o1', 'g@example.com', 'pending', now(), 'e', NULL)`,
    );
    await app.query(
      `INSERT INTO materials (id, organization, principal, class, state, verifier,
                              established_at, established_by_organization, established_by_principal)
       VALUES ('hk', 'o1', 'h@example.com', 'K', 'active', $1, now(), 'o1', 'h@example.com')`,
      [await hasher.hash(asSecretText(K))],
    );
    await app.query(
      `INSERT INTO materials (id, organization, principal, class, state, authenticator_type, seed, last_step,
                              established_at, established_by_organization, established_by_principal)
       VALUES ('hp', 'o1', 'h@example.com', 'P', 'active', 'totp', $1, $2, now(), 'o1', 'h@example.com')`,
      [JSON.stringify(encryptSeed(seed, H, 'hp', keys)), stepAt(NOW) - 2],
    );
    await app.query(
      `INSERT INTO materials (id, organization, principal, class, state, verifier, enrolled_at, enrolled_by)
       VALUES ('ge', 'o1', 'g@example.com', 'K', 'enrollment', $1, now(), 'configuration')`,
      [await hasher.hash(asSecretText(ENROLLMENT))],
    );
  } finally {
    await app.end();
  }
  resolver = new StoreIdentityResolver(db.store, hasher, keys, clock);
});

afterAll(async () => {
  await db?.drop();
});

beforeEach(() => {
  calls.length = 0;
});

describe('TC-OI-060: the identity-resolution seam decides identity only', () => {
  it('resolves K, P, and enrollment material, right and wrong, and changes no record', async () => {
    const before = await snapshot();
    expect(await resolver.resolve('K', H, K)).toEqual({
      resolved: true,
      principal: H,
      materialId: 'hk',
    });
    expect(await resolver.resolve('K', H, 'wrong secret')).toEqual({ resolved: false });
    const code = codeAt(seed, stepAt(NOW));
    expect(await resolver.resolve('P', H, { type: 'totp', code })).toEqual({
      resolved: true,
      principal: H,
      materialId: 'hp',
      acceptedStep: stepAt(NOW),
    });
    expect(await resolver.resolve('P', H, { type: 'totp', code: '000000' })).toEqual(
      code === '000000' ? expect.anything() : { resolved: false },
    );
    expect(await resolver.resolve('enrollment', G, ENROLLMENT)).toEqual({
      resolved: true,
      principal: G,
      materialId: 'ge',
    });
    expect(await resolver.resolve('enrollment', G, `${ENROLLMENT}x`)).toEqual({ resolved: false });
    // Resolving twice does not use anything up: single use is P10's.
    expect((await resolver.resolve('enrollment', G, ENROLLMENT)).resolved).toBe(true);
    expect((await resolver.resolve('P', H, { type: 'totp', code })).resolved).toBe(true);
    expect(await snapshot()).toEqual(before);
  });

  it('rejects material of the wrong kind for the principal state', async () => {
    expect((await resolver.resolve('K', G, ENROLLMENT)).resolved).toBe(false); // G has no active K
    expect((await resolver.resolve('enrollment', H, K)).resolved).toBe(false); // H has no enrollment
    expect((await resolver.resolve('P', G, { type: 'totp', code: '123456' })).resolved).toBe(false);
    expect((await resolver.resolve('P', H, { type: 'webauthn', code: '123456' })).resolved).toBe(
      false,
    );
  });

  it('refuses a P code for the last accepted step or earlier', async () => {
    const old = codeAt(seed, stepAt(NOW) - 2);
    expect((await resolver.resolve('P', H, { type: 'totp', code: old })).resolved).toBe(false);
  });
});

describe('TC-OI-029 (resolution): exactly one Argon2id verification, known or not', () => {
  const realParameters = {
    memory: ARGON2_PARAMETERS.memory,
    passes: ARGON2_PARAMETERS.passes,
    parallelism: ARGON2_PARAMETERS.parallelism,
    tagLength: ARGON2_PARAMETERS.tagLength,
  };

  it.each([
    ['a known principal, wrong K', 'K', H, 'wrong secret'],
    [
      'an unknown principal, any K',
      'K',
      { organization: 'o1', principal: 'nobody@example.com' },
      'x',
    ],
    ['another organization', 'K', { organization: 'o2', principal: 'h@example.com' }, K],
    ['a pending principal at K', 'K', G, 'x'],
    [
      'an unknown principal, enrollment',
      'enrollment',
      { organization: 'o1', principal: 'z@x.io' },
      'soorma_em_x',
    ],
  ] as const)(
    '%s: one call, with the real parameters',
    async (_name, type, reference, material) => {
      expect((await resolver.resolve(type, reference, material)).resolved).toBe(false);
      expect(calls).toHaveLength(1);
      expect(calls[0]).toMatchObject(realParameters);
    },
  );
});
