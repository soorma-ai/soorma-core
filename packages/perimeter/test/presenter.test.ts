// SPDX-License-Identifier: FSL-1.1-ALv2
// The presenter checks at S1: TC-OI-024, 026, 027; D-OI-05, 26.
import { generateKeyPairSync, randomBytes } from 'node:crypto';
import type { Clock, SignInClaims, SignInStatus } from '@soorma/service-kit';
import { KeyRing, mintSignIn } from '@soorma/org-identity';
import { describe, expect, it } from 'vitest';
import { presentedCredentialHeaders, presentedSignIn, SignInPerimeter } from '../src/index.ts';

function ring(): KeyRing {
  return KeyRing.fromConfiguration({
    signingKey: Buffer.from(
      generateKeyPairSync('ed25519').privateKey.export({ format: 'pem', type: 'pkcs8' }),
    ),
    verifyKeys: [],
    seedKeys: { current: 's1', keys: [{ id: 's1', key: randomBytes(32) }] },
    counterSecret: randomBytes(32),
    logPseudonymKey: randomBytes(32),
    internalCallers: [],
  });
}

const keys = ring();
const now = new Date('2026-11-08T12:00:00Z');
const clock: Clock = { now: () => now };

async function token(at = now, k = keys): Promise<string> {
  return (
    await mintSignIn(
      {
        organization: 'o1',
        principal: 'h@example.com',
        sid: 'sid-1',
        authenticatedAt: at,
        classes: ['K'],
        issuedAt: at,
        expiresAt: new Date(at.getTime() + 15 * 60_000),
      },
      k,
    )
  ).token;
}

describe('TC-OI-026: a credential header on an operation naming no scheme', () => {
  it('names each presented credential header, whatever its value or case', () => {
    expect(presentedCredentialHeaders(['Content-Type', 'application/json'])).toEqual([]);
    expect(presentedCredentialHeaders(['authorization', 'Bearer soorma_si_x'])).toEqual([
      'Authorization',
    ]);
    expect(presentedCredentialHeaders(['AUTHORIZATION', ''])).toEqual(['Authorization']);
    expect(
      presentedCredentialHeaders(['Soorma-Delegation', 'soorma_dc_x', 'Authorization', 'Basic x']),
    ).toEqual(['Authorization', 'Soorma-Delegation']);
  });
});

describe('TC-OI-027: a credential of the wrong kind is refused on the sign-in operations', () => {
  it.each([
    ['no header', []],
    [
      'two Authorization headers',
      ['Authorization', 'Bearer soorma_si_a', 'Authorization', 'Bearer soorma_si_a'],
    ],
    [
      'a Soorma-Delegation header',
      ['Authorization', 'Bearer soorma_si_a', 'Soorma-Delegation', 'x'],
    ],
    ['an environment credential', ['Authorization', 'Bearer soorma_ec_abc']],
    ['an agent credential', ['Authorization', 'Bearer soorma_ac_abc']],
    ['another scheme', ['Authorization', 'Basic soorma_si_abc']],
    ['a non-b64token', ['Authorization', 'Bearer soorma_si_a"b']],
    ['an over-long credential', ['Authorization', `Bearer soorma_si_${'a'.repeat(4096)}`]],
  ])('refuses %s', (_name, raw) => {
    expect(presentedSignIn(raw)).toBeUndefined();
  });

  it('accepts exactly one Bearer soorma_si_ credential', () => {
    expect(presentedSignIn(['authorization', 'bearer soorma_si_abc.def'])).toBe(
      'soorma_si_abc.def',
    );
  });
});

describe('TC-OI-024: a sign-in that fails verification is refused at the organization level', () => {
  const live = (claims: SignInClaims): Promise<SignInStatus> =>
    Promise.resolve({ status: 'live', expiresAt: claims.expiresAt });

  it('accepts a valid, live sign-in', async () => {
    const p = new SignInPerimeter(keys, 'o1', clock, live);
    const result = await p.check(['Authorization', `Bearer ${await token()}`]);
    expect(result.accepted).toBe(true);
  });

  it('refuses one signed by other material, or for another organization, as credential_refused', async () => {
    const foreign = await token(now, ring());
    expect(
      await new SignInPerimeter(keys, 'o1', clock, live).check([
        'Authorization',
        `Bearer ${foreign}`,
      ]),
    ).toEqual({ accepted: false, code: 'credential_refused' });
    expect(
      await new SignInPerimeter(keys, 'o2', clock, live).check([
        'Authorization',
        `Bearer ${await token()}`,
      ]),
    ).toEqual({ accepted: false, code: 'credential_refused' });
  });

  it('reports expiry only for a verified token, and refuses an ended one (O3)', async () => {
    const old = await token(new Date(now.getTime() - 16 * 60_000));
    expect(
      await new SignInPerimeter(keys, 'o1', clock, live).check(['Authorization', `Bearer ${old}`]),
    ).toEqual({ accepted: false, code: 'credential_expired' });
    const oldForeign = await token(new Date(now.getTime() - 16 * 60_000), ring());
    expect(
      await new SignInPerimeter(keys, 'o1', clock, live).check([
        'Authorization',
        `Bearer ${oldForeign}`,
      ]),
    ).toEqual({ accepted: false, code: 'credential_refused' });
    expect(
      await new SignInPerimeter(keys, 'o1', clock, () =>
        Promise.resolve({ status: 'ended' }),
      ).check(['Authorization', `Bearer ${await token()}`]),
    ).toEqual({ accepted: false, code: 'credential_refused' });
  });
});
