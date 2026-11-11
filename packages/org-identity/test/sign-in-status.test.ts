// SPDX-License-Identifier: FSL-1.1-ALv2
//
// TC-EHA-090: S1's signInStatus answers A7's shape (U2 BR-INT-05 as amended;
// U4 D-EHA-02). Expiry is judged on S1's clock, with no leeway.
import { randomBytes } from 'node:crypto';
import { asSecretText, verifySignIn } from '@soorma/service-kit';
import { afterAll, beforeAll, describe, expect, it } from 'vitest';
import type { Result } from '../src/index.ts';
import { testDatabase, type TestDatabase } from './harness/database.ts';
import { enrollmentMaterial, testDomain, TestClock } from './harness/domain.ts';

let db: TestDatabase;
beforeAll(async () => {
  db = await testDatabase();
});
afterAll(async () => {
  await db?.drop();
});

const K = 'purple garden lantern';

function value<T>(r: Result<T>): T {
  if (!r.ok) throw new Error(`refused: ${JSON.stringify(r.refusal)}`);
  return r.value;
}

describe('TC-EHA-090: signInStatus answers A7: live with its expiry, ended, or unknown', () => {
  it('live while the sign-in is live and unexpired; ended once expired or ended; unknown when absent', async () => {
    const clock = new TestClock();
    const d = await testDomain(db, { clock });
    const principal = `a7-${randomBytes(4).toString('hex')}@example.com`;
    const ref = { organization: 'o1', principal };
    const em = enrollmentMaterial();
    await d.identity.ensureFirstAdmin(
      [{ principal, registeredBy: 'e' }],
      [{ principal, material: asSecretText(em) }],
    );
    value(await d.identity.firstAuthenticate(ref, em, K));

    const expiring = value(await d.identity.authenticate(ref, K));
    expect(await d.identity.signInStatus(expiring.sid)).toEqual({
      status: 'live',
      expiresAt: expiring.expiresAt,
    });
    clock.advance((expiring.expiresAt.getTime() - clock.now().getTime()) / 1000 - 1);
    expect((await d.identity.signInStatus(expiring.sid)).status).toBe('live');
    clock.advance(1);
    expect(await d.identity.signInStatus(expiring.sid)).toEqual({ status: 'ended' });

    const ended = value(await d.identity.authenticate(ref, K));
    const verified = await verifySignIn(ended.token, d.keys, 'o1', clock.now());
    if (verified.status !== 'valid') throw new Error(`not valid: ${verified.status}`);
    value(await d.identity.endSignIn(verified.claims));
    expect(await d.identity.signInStatus(ended.sid)).toEqual({ status: 'ended' });

    expect(await d.identity.signInStatus('0123456789abcdef0123456789abcdef')).toEqual({
      status: 'unknown',
    });
  });
});
