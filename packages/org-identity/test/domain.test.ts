// SPDX-License-Identifier: FSL-1.1-ALv2
// P10's flows against the org store, clock-controlled: TC-OI-001, 002, 004 to
// 010, 014 to 018, 021, 034 to 038, 040, 041, 053; the internal operations.
import { randomBytes } from 'node:crypto';
import { afterAll, beforeAll, describe, expect, it } from 'vitest';
import {
  asSecretBytes,
  asSecretText,
  codeAt,
  FirstAdminError,
  Pruner,
  stepAt,
  verifySignIn,
  type MaterialChangeResult,
  type PrincipalReference,
  type Result,
} from '../src/index.ts';
import { testDatabase, type TestDatabase } from './harness/database.ts';
import { enrollmentMaterial, testDomain, TestClock, type Domain } from './harness/domain.ts';

let db: TestDatabase;
beforeAll(async () => {
  db = await testDatabase();
});
afterAll(async () => {
  await db?.drop();
});

const K = 'purple garden lantern';
const K2 = 'quiet river compass';

let counter = 0;
const unique = (): string => `user${counter++}-${randomBytes(4).toString('hex')}@example.com`;

function value<T>(r: Result<T>): T {
  if (!r.ok) throw new Error(`refused: ${JSON.stringify(r.refusal)}`);
  return r.value;
}

/** Registers a fresh first Admin; returns its reference and enrollment material. */
async function registered(
  d: Domain,
  environment = 'e',
): Promise<{ ref: PrincipalReference; em: string }> {
  const principal = unique();
  const em = enrollmentMaterial();
  await d.identity.ensureFirstAdmin(
    [{ principal, registeredBy: environment }],
    [{ principal, material: asSecretText(em) }],
  );
  return { ref: { organization: 'o1', principal }, em };
}

/** A fresh active human with K. */
async function active(d: Domain): Promise<PrincipalReference> {
  const { ref, em } = await registered(d);
  value(await d.identity.firstAuthenticate(ref, em, K));
  return ref;
}

function base32Decode(text: string): Buffer {
  const alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567';
  let bits = 0;
  let acc = 0;
  const out: number[] = [];
  for (const c of text) {
    acc = (acc << 5) | alphabet.indexOf(c);
    bits += 5;
    if (bits >= 8) {
      out.push((acc >>> (bits - 8)) & 0xff);
      bits -= 8;
    }
  }
  return Buffer.from(out);
}

/** Enrolls P for an active human: begin and confirm, presenting K. Returns the seed. */
async function enrollP(d: Domain, ref: PrincipalReference): Promise<Buffer> {
  const begun = value(
    await d.identity.changeMaterial(
      ref,
      { secret: K },
      { type: 'beginSecondFactor', authenticatorType: 'totp' },
    ),
  );
  if (begun.type !== 'beginSecondFactor') throw new Error('expected beginSecondFactor');
  const seed = base32Decode(begun.enrollment.setup.seed);
  const code = codeAt(asSecretBytes(seed), stepAt(d.clock.now()));
  value(
    await d.identity.changeMaterial(
      ref,
      { secret: K },
      {
        type: 'confirmSecondFactor',
        enrollment: begun.enrollment.id,
        proof: { type: 'totp', code },
      },
    ),
  );
  return seed;
}

const totp = (d: Domain, seed: Buffer, stepOffset = 0) => ({
  type: 'totp',
  code: codeAt(asSecretBytes(seed), stepAt(d.clock.now()) + stepOffset),
});

async function rows(sql: string, params: unknown[] = []): Promise<Record<string, unknown>[]> {
  const su = await db.superuser();
  try {
    return (await su.query<Record<string, unknown>>(sql, params)).rows;
  } finally {
    await su.end();
  }
}

describe('TC-OI-001 and TC-OI-017: the configured first Admin', () => {
  it('registers an absent first Admin as pending, with one enrollment record from configuration', async () => {
    const d = await testDomain(db);
    const { ref, em } = await registered(d, 'e2');
    const [p] = await rows('SELECT * FROM principals WHERE principal = $1', [ref.principal]);
    expect(p).toMatchObject({
      organization: 'o1',
      state: 'pending',
      registered_by_environment: 'e2',
    });
    expect(p!.registered_at).toEqual(d.clock.now());
    const m = await rows('SELECT * FROM materials WHERE principal = $1', [ref.principal]);
    expect(m).toHaveLength(1);
    expect(m[0]).toMatchObject({ class: 'K', state: 'enrollment', enrolled_by: 'configuration' });
    expect(m[0]!.verifier).toMatch(/^\$argon2id\$/);
    expect(m[0]!.verifier).not.toContain(em);
  });

  it('never re-registers or re-enrolls an existing principal; it reports the material ignored', async () => {
    const d = await testDomain(db);
    const { ref, em } = await registered(d);
    const before = await rows('SELECT * FROM materials WHERE principal = $1', [ref.principal]);
    const again = await d.identity.ensureFirstAdmin(
      [{ principal: ref.principal, registeredBy: 'e' }],
      [{ principal: ref.principal, material: asSecretText(enrollmentMaterial()) }],
    );
    expect(again).toEqual({ registered: [], ignored: [ref] });
    expect(await rows('SELECT * FROM materials WHERE principal = $1', [ref.principal])).toEqual(
      before,
    );
    // After activation, configured material still cannot act as a reset.
    value(await d.identity.firstAuthenticate(ref, em, K));
    await d.identity.ensureFirstAdmin(
      [{ principal: ref.principal, registeredBy: 'e' }],
      [{ principal: ref.principal, material: asSecretText(em) }],
    );
    expect((await d.identity.firstAuthenticate(ref, em, K2)).ok).toBe(false);
  });

  it('refuses to start when an absent first Admin has no material; concurrent start-ups register once', async () => {
    const d = await testDomain(db);
    await expect(
      d.identity.ensureFirstAdmin([{ principal: unique(), registeredBy: 'e' }], []),
    ).rejects.toThrow(FirstAdminError);
    const principal = unique();
    const config = [
      [{ principal, registeredBy: 'e' }],
      [{ principal, material: asSecretText(enrollmentMaterial()) }],
    ] as const;
    const outcomes = await Promise.all([
      d.identity.ensureFirstAdmin(...config),
      d.identity.ensureFirstAdmin(...config),
    ]);
    expect(outcomes.flatMap((o) => o.registered)).toHaveLength(1);
    expect(await rows('SELECT id FROM materials WHERE principal = $1', [principal])).toHaveLength(
      1,
    );
  });
});

describe('TC-OI-002, 009, 034, 035: first authentication', () => {
  it('sets H’s own K and activates H, in the same record, and issues a sign-in with [K]', async () => {
    const d = await testDomain(db);
    const { ref, em } = await registered(d);
    const before = await rows('SELECT id FROM materials WHERE principal = $1', [ref.principal]);
    const out = value(await d.identity.firstAuthenticate(ref, em, K));
    expect(out.state).toBe('active');
    expect(out.signIn?.classes).toEqual(['K']);
    expect(out.signIn?.expiresAt.getTime()).toBe(d.clock.ms + 15 * 60_000);
    const [p] = await rows('SELECT state, activated_at FROM principals WHERE principal = $1', [
      ref.principal,
    ]);
    expect(p).toEqual({ state: 'active', activated_at: d.clock.now() });
    const m = await rows('SELECT * FROM materials WHERE principal = $1', [ref.principal]);
    expect(m).toHaveLength(1);
    expect(m[0]).toMatchObject({
      id: before[0]!.id,
      state: 'active',
      established_by_organization: 'o1',
      established_by_principal: ref.principal,
    });
    const verified = await verifySignIn(out.signIn!.token, d.keys, 'o1', d.clock.now());
    expect(verified.status).toBe('valid');
  });

  it('refuses reused enrollment material (TC-OI-009), and the material on authenticate', async () => {
    const d = await testDomain(db);
    const { ref, em } = await registered(d);
    value(await d.identity.firstAuthenticate(ref, em, K));
    expect(await d.identity.firstAuthenticate(ref, em, K2)).toEqual({
      ok: false,
      refusal: { code: 'authentication_failed' },
    });
    expect((await d.identity.authenticate(ref, em)).ok).toBe(false);
  });

  it('a policy refusal is secret_rejected at /newSecret and consumes nothing', async () => {
    const d = await testDomain(db);
    const { ref, em } = await registered(d);
    expect(await d.identity.firstAuthenticate(ref, em, 'password')).toEqual({
      ok: false,
      refusal: { code: 'secret_rejected', pointer: '/newSecret', reason: 'breached' },
    });
    // Enrollment material contains "soorma", so reusing it is refused as a
    // context word, before the reuse check is reached.
    expect(await d.identity.firstAuthenticate(ref, em, em)).toEqual({
      ok: false,
      refusal: { code: 'secret_rejected', pointer: '/newSecret', reason: 'context_word' },
    });
    expect((await d.identity.firstAuthenticate(ref, em, K)).ok).toBe(true);
  });

  it('two concurrent first authentications with the same material succeed at most once (TC-OI-034)', async () => {
    const d = await testDomain(db);
    const { ref, em } = await registered(d);
    const results = await Promise.all([
      d.identity.firstAuthenticate(ref, em, K),
      d.identity.firstAuthenticate(ref, em, K2),
    ]);
    expect(results.filter((r) => r.ok)).toHaveLength(1);
    expect(results.filter((r) => !r.ok)[0]).toEqual({
      ok: false,
      refusal: { code: 'authentication_failed' },
    });
  });

  it('where P is required, activates H and issues no sign-in (TC-OI-035)', async () => {
    const d = await testDomain(db, { secondFactorRequired: true });
    const { ref, em } = await registered(d);
    expect(value(await d.identity.firstAuthenticate(ref, em, K))).toEqual({
      principal: ref,
      state: 'active',
      secondFactorEnrollmentRequired: true,
    });
    expect(
      await rows('SELECT id FROM sign_ins WHERE principal = $1', [ref.principal]),
    ).toHaveLength(0);
  });
});

describe('TC-OI-003, 010, 018, 028: authenticate', () => {
  it('issues a sign-in for K, and records it (TC-OI-021)', async () => {
    const d = await testDomain(db);
    const ref = await active(d);
    const s = value(await d.identity.authenticate(ref, K));
    const [row] = await rows('SELECT * FROM sign_ins WHERE id = $1', [s.sid]);
    expect(row).toMatchObject({
      organization: 'o1',
      principal: ref.principal,
      classes: ['K'],
      state: 'live',
      authenticated_at: d.clock.now(),
      expires_at: s.expiresAt,
    });
  });

  it('refuses a wrong K, counts it, and queues a Failed Attempt for the existing principal', async () => {
    const d = await testDomain(db);
    const ref = await active(d);
    expect(await d.identity.authenticate(ref, 'wrong secret')).toEqual({
      ok: false,
      refusal: { code: 'authentication_failed' },
    });
    expect(d.failures.records).toEqual([
      { ...ref, surface: 'authenticate', at: d.clock.now(), refusedByBound: false },
    ]);
  });

  it('refuses an unknown principal, or another organization, the same way, and queues nothing', async () => {
    const d = await testDomain(db);
    const ref = await active(d);
    const unknown = await d.identity.authenticate({ organization: 'o1', principal: unique() }, K);
    const otherOrg = await d.identity.authenticate({ ...ref, organization: 'o2' }, K);
    expect(unknown).toEqual({ ok: false, refusal: { code: 'authentication_failed' } });
    expect(otherOrg).toEqual(unknown);
    expect(d.failures.records).toEqual([]);
  });

  it('a pending principal cannot authenticate (D-OI-02)', async () => {
    const d = await testDomain(db);
    const { ref } = await registered(d);
    expect((await d.identity.authenticate(ref, K)).ok).toBe(false);
  });

  it('a bound refusal is too_many_attempts, recorded as refused by the bound (TC-OI-011)', async () => {
    const d = await testDomain(db);
    const ref = await active(d);
    for (let n = 1; n <= 10; n++) {
      if (n >= 6) d.clock.advance(2 ** (n - 6));
      expect((await d.identity.authenticate(ref, 'wrong')).ok).toBe(false);
    }
    d.clock.advance(32);
    const refused = await d.identity.authenticate(ref, K);
    expect(refused).toEqual({
      ok: false,
      refusal: { code: 'too_many_attempts', retryAfterSeconds: expect.any(Number) },
    });
    expect(d.failures.records.at(-1)).toMatchObject({ refusedByBound: true });
  });
});

describe('TC-OI-004, 008, 014, 016, 037, 038, 039: the second factor', () => {
  it('where P is required and not enrolled, sign-in is refused, uncounted (TC-OI-014)', async () => {
    const d = await testDomain(db, { secondFactorRequired: true });
    const { ref, em } = await registered(d);
    value(await d.identity.firstAuthenticate(ref, em, K));
    expect(await d.identity.authenticate(ref, K)).toEqual({
      ok: false,
      refusal: { code: 'second_factor_enrollment_required' },
    });
    expect(d.failures.records).toEqual([]);
  });

  it('enrolls P with K alone and no sign-in, then requires K and P (TC-OI-008, 004, 016)', async () => {
    const d = await testDomain(db, { secondFactorRequired: true });
    const { ref, em } = await registered(d);
    value(await d.identity.firstAuthenticate(ref, em, K));
    const seed = await enrollP(d, ref);
    d.clock.advance(30);
    expect((await d.identity.authenticate(ref, K)).ok).toBe(false); // K alone
    const s = value(await d.identity.authenticate(ref, K, totp(d, seed)));
    expect(s.classes).toEqual(['K', 'P']);
    const [p] = await rows("SELECT * FROM materials WHERE principal = $1 AND class = 'P'", [
      ref.principal,
    ]);
    expect(p).toMatchObject({ state: 'active', authenticator_type: 'totp' });
    expect(JSON.stringify(p!.seed)).not.toContain(seed.toString('base64url'));
  });

  it('accepts each code once (TC-OI-039), and a P proof where P is not active fails (BR-P-07)', async () => {
    const d = await testDomain(db);
    const ref = await active(d);
    expect((await d.identity.authenticate(ref, K, { type: 'totp', code: '123456' })).ok).toBe(
      false,
    );
    const seed = await enrollP(d, ref);
    d.clock.advance(30);
    const proof = totp(d, seed);
    expect((await d.identity.authenticate(ref, K, proof)).ok).toBe(true);
    expect((await d.identity.authenticate(ref, K, proof)).ok).toBe(false);
    expect((await d.identity.authenticate(ref, K, totp(d, seed, -1))).ok).toBe(false);
  });

  it('a failed confirmation is uncounted and leaves the enrollment; it expires at 10 minutes (TC-OI-038)', async () => {
    const d = await testDomain(db);
    const ref = await active(d);
    const begun = value(
      await d.identity.changeMaterial(
        ref,
        { secret: K },
        { type: 'beginSecondFactor', authenticatorType: 'totp' },
      ),
    ) as Extract<MaterialChangeResult, { type: 'beginSecondFactor' }>;
    expect(begun.enrollment.expiresAt.getTime()).toBe(d.clock.ms + 10 * 60_000);
    const confirm = (code: string) =>
      d.identity.changeMaterial(
        ref,
        { secret: K },
        {
          type: 'confirmSecondFactor',
          enrollment: begun.enrollment.id,
          proof: { type: 'totp', code },
        },
      );
    const seed = asSecretBytes(base32Decode(begun.enrollment.setup.seed));
    const wrong = codeAt(seed, stepAt(d.clock.now()) + 5);
    expect(await confirm(wrong)).toEqual({
      ok: false,
      refusal: { code: 'second_factor_not_confirmed' },
    });
    expect(d.failures.records).toEqual([]);
    d.clock.advance(10 * 60 + 1);
    expect(await confirm(codeAt(seed, stepAt(d.clock.now())))).toEqual({
      ok: false,
      refusal: { code: 'second_factor_not_confirmed' },
    });
  });

  it('replacing P retires the old one (TC-OI-037)', async () => {
    const d = await testDomain(db);
    const ref = await active(d);
    const first = await enrollP(d, ref);
    d.clock.advance(30);
    const begun = value(
      await d.identity.changeMaterial(
        ref,
        { secret: K, secondFactor: totp(d, first) },
        { type: 'beginSecondFactor', authenticatorType: 'totp' },
      ),
    ) as Extract<MaterialChangeResult, { type: 'beginSecondFactor' }>;
    d.clock.advance(30);
    const second = base32Decode(begun.enrollment.setup.seed);
    const confirmed = value(
      await d.identity.changeMaterial(
        ref,
        { secret: K, secondFactor: totp(d, first) },
        {
          type: 'confirmSecondFactor',
          enrollment: begun.enrollment.id,
          proof: { type: 'totp', code: codeAt(asSecretBytes(second), stepAt(d.clock.now())) },
        },
      ),
    );
    expect(confirmed).toMatchObject({ type: 'confirmSecondFactor', retired: ['P'] });
    const ps = await rows(
      "SELECT state, seed, retired_at FROM materials WHERE principal = $1 AND class = 'P' ORDER BY established_at, state",
      [ref.principal],
    );
    expect(ps.map((p) => p.state).sort()).toEqual(['active', 'retired']);
    const retired = ps.find((p) => p.state === 'retired')!;
    expect(retired.seed).toBeNull();
    expect(retired.retired_at).toEqual(d.clock.now());
  });
});

describe('TC-OI-005, 006, 020, 040, 041: renewing and ending a sign-in', () => {
  async function claimsOf(d: Domain, token: string) {
    const v = await verifySignIn(token, d.keys, 'o1', d.clock.now());
    if (v.status !== 'valid') throw new Error(v.status);
    return v.claims;
  }

  it('renews the same sign-in with a later expiry, never past 12 hours (TC-OI-005, 041)', async () => {
    const d = await testDomain(db);
    const ref = await active(d);
    const s = value(await d.identity.authenticate(ref, K));
    d.clock.advance(10 * 60);
    const renewed = value(await d.identity.renewSignIn(await claimsOf(d, s.token)));
    expect(renewed.sid).toBe(s.sid);
    expect(renewed.authenticatedAt).toEqual(s.authenticatedAt);
    expect(renewed.expiresAt.getTime()).toBe(d.clock.ms + 15 * 60_000);
    let token = renewed.token;
    // Renew every 10 minutes up to 11 h 50 min after authentication.
    while (d.clock.ms - s.authenticatedAt.getTime() < (11 * 60 + 50) * 60_000) {
      d.clock.advance(10 * 60);
      token = value(await d.identity.renewSignIn(await claimsOf(d, token))).token;
    }
    const last = await claimsOf(d, token);
    expect(last.expiresAt.getTime()).toBe(s.authenticatedAt.getTime() + 12 * 3_600_000);
    d.clock.ms = last.expiresAt.getTime();
    expect((await verifySignIn(token, d.keys, 'o1', d.clock.now())).status).toBe('expired');
  });

  it('ends the sign-in; it is refused afterwards (TC-OI-006)', async () => {
    const d = await testDomain(db);
    const ref = await active(d);
    const s = value(await d.identity.authenticate(ref, K));
    const claims = await claimsOf(d, s.token);
    expect(await d.identity.checkSignIn(claims)).toBe(true);
    expect(value(await d.identity.endSignIn(claims))).toBeUndefined();
    expect(await d.identity.checkSignIn(claims)).toBe(false);
    expect(await d.identity.renewSignIn(claims)).toEqual({
      ok: false,
      refusal: { code: 'credential_refused' },
    });
    const [row] = await rows('SELECT state, ended_by, ended_at FROM sign_ins WHERE id = $1', [
      s.sid,
    ]);
    expect(row).toEqual({ state: 'ended', ended_by: 'self', ended_at: d.clock.now() });
  });

  it('refuses renewal when P is required and the sign-in lacks it (TC-OI-040)', async () => {
    const d = await testDomain(db);
    const ref = await active(d);
    const s = value(await d.identity.authenticate(ref, K));
    const strict = await testDomain(db, {
      secondFactorRequired: true,
      keys: d.keys,
      clock: d.clock,
    });
    expect(await strict.identity.renewSignIn(await claimsOf(d, s.token))).toEqual({
      ok: false,
      refusal: { code: 'second_factor_enrollment_required' },
    });
  });
});

describe('TC-OI-007, 015, 036: changing material', () => {
  it('replaces K by presenting the current K, and ends every live sign-in (TC-OI-007, 036)', async () => {
    const d = await testDomain(db);
    const ref = await active(d);
    const a = value(await d.identity.authenticate(ref, K));
    const b = value(await d.identity.authenticate(ref, K));
    const changed = value(
      await d.identity.changeMaterial(ref, { secret: K }, { type: 'replaceSecret', newSecret: K2 }),
    );
    // Three live sign-ins: the one first authentication issued, and a and b.
    expect(changed).toEqual({ type: 'replaceSecret', retired: ['K'], signInsEnded: 3 });
    expect((await d.identity.authenticate(ref, K)).ok).toBe(false);
    expect((await d.identity.authenticate(ref, K2)).ok).toBe(true);
    const ended = await rows('SELECT ended_by FROM sign_ins WHERE id = ANY ($1)', [[a.sid, b.sid]]);
    expect(ended.map((r) => r.ended_by)).toEqual(['materialChange', 'materialChange']);
    const ks = await rows(
      "SELECT state, verifier FROM materials WHERE principal = $1 AND class = 'K'",
      [ref.principal],
    );
    expect(ks.find((k) => k.state === 'retired')!.verifier).toBeNull();
  });

  it('refuses a change without the current material, counted as changeMaterial (TC-OI-015)', async () => {
    const d = await testDomain(db);
    const ref = await active(d);
    expect(
      await d.identity.changeMaterial(
        ref,
        { secret: 'wrong' },
        { type: 'replaceSecret', newSecret: K2 },
      ),
    ).toEqual({ ok: false, refusal: { code: 'authentication_failed' } });
    expect(d.failures.records[0]).toMatchObject({ surface: 'changeMaterial' });
  });

  it('refuses a new K that fails the policy at /change/newSecret', async () => {
    const d = await testDomain(db);
    const ref = await active(d);
    expect(
      await d.identity.changeMaterial(ref, { secret: K }, { type: 'replaceSecret', newSecret: K }),
    ).toEqual({
      ok: false,
      refusal: { code: 'secret_rejected', pointer: '/change/newSecret', reason: 'reused' },
    });
  });
});

describe('the internal operations (BR-INT-03 to 06)', () => {
  it('answer existence, sign-in status, and verify-only material, changing nothing', async () => {
    const d = await testDomain(db);
    const ref = await active(d);
    const s = value(await d.identity.authenticate(ref, K));
    expect(await d.identity.principalExists(ref)).toBe(true);
    expect(await d.identity.principalExists({ organization: 'o1', principal: unique() })).toBe(
      false,
    );
    expect(await d.identity.signInStatus(s.sid)).toBe('live');
    expect(await d.identity.signInStatus('no-such-id')).toBe('unknown');
    expect(d.identity.verifyOnlyMaterial().keys.every((k) => !('d' in k))).toBe(true);
  });
});

describe('TC-OI-053: retention prunes what it may, and never a principal or material', () => {
  it('deletes Failed Attempts and ended or expired sign-ins older than 90 days, under a lock', async () => {
    const d = await testDomain(db);
    const ref = await active(d);
    const s = value(await d.identity.authenticate(ref, K));
    const app = await db.app();
    try {
      await app.query(
        `INSERT INTO failed_attempts (organization, principal, surface, at, refused_by_bound)
         VALUES ('o1', $1, 'authenticate', $2, false), ('o1', $1, 'authenticate', $3, false)`,
        [ref.principal, new Date(d.clock.ms - 91 * 86_400_000), d.clock.now()],
      );
    } finally {
      await app.end();
    }
    const clock = new TestClock();
    clock.ms = d.clock.ms + 91 * 86_400_000;
    // Another instance holding the lock: this one does nothing.
    const holder = await db.app();
    await holder.query('BEGIN');
    await holder.query('SELECT pg_advisory_xact_lock($1::bigint)', [
      (await import('../src/index.ts')).PRUNE_LOCK_KEY,
    ]);
    expect(await new Pruner(db.store, clock).prune()).toEqual({
      ran: false,
      failedAttempts: 0,
      signIns: 0,
    });
    await holder.query('COMMIT');
    await holder.end();
    const result = await new Pruner(db.store, clock).prune();
    expect(result.ran).toBe(true);
    expect(result.failedAttempts).toBeGreaterThanOrEqual(1);
    expect(await rows('SELECT id FROM sign_ins WHERE id = $1', [s.sid])).toHaveLength(0);
    expect(
      await rows('SELECT 1 FROM principals WHERE principal = $1', [ref.principal]),
    ).toHaveLength(1);
    expect(
      await rows('SELECT 1 FROM materials WHERE principal = $1', [ref.principal]),
    ).toHaveLength(1);
  });
});
