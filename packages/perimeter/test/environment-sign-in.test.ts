// SPDX-License-Identifier: FSL-1.1-ALv2
//
// P1's sign-in check as an environment uses it at issuance (U4 NP-EHA-03, 15):
// the environment's leeway, a key source that changes, one refetch on an
// unknown kid, and A7's status. The organization level's own use is
// presenter.test.ts.
import { generateKeyPairSync, randomBytes } from 'node:crypto';
import { KeyRing, mintSignIn } from '@soorma/org-identity';
import {
  UnavailableError,
  type Clock,
  type SignInKeySource,
  type SignInStatus,
} from '@soorma/service-kit';
import { describe, expect, it } from 'vitest';
import { SignInPerimeter } from '../src/index.ts';

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

const S1 = ring();
const now = new Date('2026-11-11T12:00:00Z');
const clock: Clock = { now: () => now };
const ENVIRONMENT = { expSeconds: 30, iatAheadSeconds: 30 };
const MINUTE = 60_000;

/** A sign-in token whose `exp` is `expiresAt`, issued 15 minutes before it. */
async function signIn(expiresAt: Date, keys: KeyRing = S1): Promise<string> {
  const issuedAt = new Date(expiresAt.getTime() - 15 * MINUTE);
  return (
    await mintSignIn(
      {
        organization: 'o1',
        principal: 'h@example.com',
        sid: 'a'.repeat(32),
        authenticatedAt: issuedAt,
        classes: ['K'],
        issuedAt,
        expiresAt,
      },
      keys,
    )
  ).token;
}

/** An environment's verify-key cache, as P1 sees it: read on every check. */
class Cache implements SignInKeySource {
  held: KeyRing[];
  fetches = 0;
  private readonly onFetch: () => KeyRing[] | undefined;
  constructor(onFetch: () => KeyRing[] | undefined = () => undefined, initial: KeyRing[] = []) {
    this.onFetch = onFetch;
    this.held = initial;
  }
  verifyKey(kid: string) {
    for (const k of this.held) {
      const key = k.verifyKey(kid);
      if (key) return key;
    }
    return undefined;
  }
  hasKeys(): boolean {
    return this.held.length > 0;
  }
  readonly refetch = (): Promise<void> => {
    this.fetches += 1;
    const next = this.onFetch();
    if (next) this.held = next;
    return Promise.resolve();
  };
}

const header = (token: string): string[] => ['Authorization', `Bearer ${token}`];

describe('TC-EHA-057: sign-in leeway at issuance; A7 judges expiry on S1’s clock (NFR-EHA-03)', () => {
  it('(a) a never-renewed sign-in 29 s past its expiry is credential_refused: A7 says ended', async () => {
    const token = await signIn(new Date(now.getTime() - 29_000));
    const p = new SignInPerimeter(
      new Cache(undefined, [S1]),
      'o1',
      clock,
      (): Promise<SignInStatus> => Promise.resolve({ status: 'ended' }),
      { tolerance: ENVIRONMENT },
    );
    expect(await p.check(header(token))).toEqual({
      accepted: false,
      code: 'credential_refused',
    });
  });

  it('(b) an older token of a renewed sign-in, 29 s past its own expiry, is accepted with the renewed expiry', async () => {
    const token = await signIn(new Date(now.getTime() - 29_000));
    const renewed = new Date(now.getTime() + 14 * MINUTE);
    const p = new SignInPerimeter(
      new Cache(undefined, [S1]),
      'o1',
      clock,
      (): Promise<SignInStatus> => Promise.resolve({ status: 'live', expiresAt: renewed }),
      { tolerance: ENVIRONMENT },
    );
    const result = await p.check(header(token));
    expect(result.accepted).toBe(true);
    if (result.accepted) expect(result.status.expiresAt).toEqual(renewed);
  });

  it('(c) any sign-in token 31 s past its expiry is credential_expired, with no status call', async () => {
    const token = await signIn(new Date(now.getTime() - 31_000));
    let calls = 0;
    const p = new SignInPerimeter(
      new Cache(undefined, [S1]),
      'o1',
      clock,
      (): Promise<SignInStatus> => {
        calls += 1;
        return Promise.resolve({ status: 'live', expiresAt: now });
      },
      { tolerance: ENVIRONMENT },
    );
    expect(await p.check(header(token))).toEqual({
      accepted: false,
      code: 'credential_expired',
    });
    expect(calls).toBe(0);
  });
});

describe('TC-EHA-064: the unknown-kid flow through P1: refetch, then verify exactly once more', () => {
  const live = (): Promise<SignInStatus> =>
    Promise.resolve({ status: 'live', expiresAt: new Date(now.getTime() + 10 * MINUTE) });
  const valid = () => signIn(new Date(now.getTime() + 10 * MINUTE));

  it('the refetch brings the key: one fetch, accepted', async () => {
    const cache = new Cache(() => [S1], [ring()]);
    const p = new SignInPerimeter(cache, 'o1', clock, live, {
      tolerance: ENVIRONMENT,
      refetch: cache.refetch,
    });
    expect((await p.check(header(await valid()))).accepted).toBe(true);
    expect(cache.fetches).toBe(1);
  });

  it('the refetch does not bring it: one fetch, credential_refused', async () => {
    const cache = new Cache(() => [ring()], [ring()]);
    const p = new SignInPerimeter(cache, 'o1', clock, live, {
      tolerance: ENVIRONMENT,
      refetch: cache.refetch,
    });
    expect(await p.check(header(await valid()))).toEqual({
      accepted: false,
      code: 'credential_refused',
    });
    expect(cache.fetches).toBe(1);
  });

  it('inside the limit (the refetch fetches nothing): credential_refused', async () => {
    const cache = new Cache(() => undefined, [ring()]);
    const p = new SignInPerimeter(cache, 'o1', clock, live, {
      tolerance: ENVIRONMENT,
      refetch: cache.refetch,
    });
    expect(await p.check(header(await valid()))).toEqual({
      accepted: false,
      code: 'credential_refused',
    });
  });

  it('no keys held and the fetch failing: unavailable, with the configured Retry-After', async () => {
    const cache = new Cache(() => undefined, []);
    const p = new SignInPerimeter(cache, 'o1', clock, live, {
      tolerance: ENVIRONMENT,
      refetch: cache.refetch,
      retryAfterSeconds: 5,
    });
    const error = await p.check(header(await valid())).catch((e: unknown) => e);
    expect(error).toBeInstanceOf(UnavailableError);
    expect((error as UnavailableError).retryAfterSeconds).toBe(5);
    expect(cache.fetches).toBe(1);
  });

  it('a status call that cannot reach S1 propagates unavailable, never a pass', async () => {
    const p = new SignInPerimeter(
      new Cache(undefined, [S1]),
      'o1',
      clock,
      () => Promise.reject(new UnavailableError('organization level unreachable', 5)),
      { tolerance: ENVIRONMENT },
    );
    await expect(p.check(header(await valid()))).rejects.toBeInstanceOf(UnavailableError);
  });

  it('an unknown status is credential_refused', async () => {
    const p = new SignInPerimeter(
      new Cache(undefined, [S1]),
      'o1',
      clock,
      () => Promise.resolve({ status: 'unknown' }),
      { tolerance: ENVIRONMENT },
    );
    expect((await p.check(header(await valid()))).accepted).toBe(false);
  });
});

describe('TC-EHA-065: the key source is read on every check', () => {
  it('a key that arrives between two checks is seen by the second, with no refetch', async () => {
    const cache = new Cache(() => undefined, [ring()]);
    const live = (): Promise<SignInStatus> =>
      Promise.resolve({ status: 'live', expiresAt: new Date(now.getTime() + MINUTE) });
    const p = new SignInPerimeter(cache, 'o1', clock, live, { tolerance: ENVIRONMENT });
    const token = await signIn(new Date(now.getTime() + 10 * MINUTE));
    expect((await p.check(header(token))).accepted).toBe(false);
    cache.held = [S1];
    expect((await p.check(header(token))).accepted).toBe(true);
    expect(cache.fetches).toBe(0);
  });
});
