// SPDX-License-Identifier: FSL-1.1-ALv2
// S1's edge through HTTP: the five operations, the check order, and every
// response against the contract. TC-OI-002 to 007, 010, 011, 014, 020, 023,
// 024, 026, 027, 042 (over HTTP), 047 (edge side), 052, 055.
import { asSecretBytes, codeAt, stepAt, Store } from '@soorma/org-identity';
import { afterAll, beforeAll, describe, expect, it } from 'vitest';
import {
  testDatabase,
  type TestDatabase,
} from '../../../packages/org-identity/test/harness/database.ts';
import { HashSemaphore } from '@soorma/org-identity';
import {
  active,
  gateway,
  K,
  K2,
  post,
  registered,
  validator,
  get,
  type Gateway,
  type Response,
} from './support.ts';

let db: TestDatabase;
let g: Gateway;
beforeAll(async () => {
  db = await testDatabase();
  g = await gateway(db);
});
afterAll(async () => {
  await g?.close();
  await db?.drop();
});

/** Every response: the Soorma headers; every Problem: the emission rules (BR-ERR-08). */
function expectProblem(r: Response, status: number, code: string): void {
  expect(r.status).toBe(status);
  expect(r.headers['soorma-contract-version']).toBe('0.1.0');
  const id = r.headers['soorma-request-id'];
  expect(id).toMatch(/^[0-9a-f-]{36}$/);
  expect(r.headers['content-type']).toBe('application/problem+json; charset=utf-8');
  expect(r.body).toMatchObject({
    type: `urn:soorma:problem:${code}`,
    title: expect.any(String),
    status,
    code,
    instance: `urn:soorma:request:${String(id)}`,
  });
  expect(validator.conforms('components', 'Problem', r.body)).toBe(true);
  if (status === 401) expect(r.headers['www-authenticate']).toBe('Bearer');
  else expect(r.headers['www-authenticate']).toBeUndefined();
  if (status === 429 || status === 503) expect(Number(r.headers['retry-after'])).toBeGreaterThan(0);
}

const bearer = (token: string) => ({ authorization: `Bearer ${token}` });

describe('TC-OI-002, 003, 005, 006, 023: the operations, valid against the contract', () => {
  it('first authentication, then sign-in, renewal, and the logout', async () => {
    const { principal, em } = await registered(g);
    const first = await post(g.edge, '/first-authentication', {
      principal,
      enrollmentMaterial: em,
      newSecret: K,
    });
    expect(first.status).toBe(200);
    expect(first.headers['soorma-contract-version']).toBe('0.1.0');
    expect(first.headers['content-type']).toBe('application/json; charset=utf-8');
    expect(validator.conforms('org-gateway', 'FirstAuthenticateResponse', first.body)).toBe(true);
    expect(first.body).toMatchObject({
      principal,
      state: 'active',
      signIn: { classes: ['K'], subject: principal },
    });

    const signIn = await post(g.edge, '/sign-ins', { principal, secret: K });
    expect(signIn.status).toBe(200);
    expect(validator.conforms('org-gateway', 'SignInResponse', signIn.body)).toBe(true);
    const token = signIn.body.signIn.token as string;

    g.clock.advance(60);
    const renewed = await post(g.edge, '/sign-ins/current/renewal', undefined, bearer(token));
    expect(renewed.status).toBe(200);
    expect(validator.conforms('org-gateway', 'SignInResponse', renewed.body)).toBe(true);
    expect(renewed.body.signIn.authenticatedAt).toBe(signIn.body.signIn.authenticatedAt);

    const ended = await post(g.edge, '/sign-ins/current/end', undefined, bearer(token));
    expect(ended.status).toBe(204);
    expect(ended.text).toBe('');
    expect(ended.headers['soorma-request-id']).toBeDefined();
    // Every token of the ended sign-in is refused (O3).
    expectProblem(
      await post(
        g.edge,
        '/sign-ins/current/renewal',
        undefined,
        bearer(renewed.body.signIn.token as string),
      ),
      401,
      'credential_refused',
    );
  });

  it('material change: replace K; then begin and confirm a second factor (TC-OI-007)', async () => {
    const { principal } = await active(g);
    const replaced = await post(g.edge, '/material-changes', {
      principal,
      current: { secret: K },
      change: { type: 'replaceSecret', newSecret: K2 },
    });
    expect(replaced.status).toBe(200);
    expect(validator.conforms('org-gateway', 'ChangeMaterialResponse', replaced.body)).toBe(true);
    expect(replaced.body).toEqual({ type: 'replaceSecret', retired: ['K'], signInsEnded: 1 });

    const begun = await post(g.edge, '/material-changes', {
      principal,
      current: { secret: K2 },
      change: { type: 'beginSecondFactor', authenticatorType: 'totp' },
    });
    expect(begun.status).toBe(200);
    expect(validator.conforms('org-gateway', 'ChangeMaterialResponse', begun.body)).toBe(true);
    const { setup } = begun.body.enrollment as { setup: { seed: string; otpauthUri: string } };
    expect(setup.otpauthUri).toContain(`secret=${setup.seed}`);
  });
});

describe('the check order for operations naming no scheme (business-logic-model §1)', () => {
  it('TC-OI-026: a credential header is malformed_request naming it, before the version', async () => {
    const { principal } = await active(g);
    for (const [header, value] of [
      ['authorization', 'Bearer soorma_si_x'],
      ['soorma-delegation', 'soorma_dc_x'],
    ] as const) {
      const r = await post(
        g.edge,
        '/sign-ins',
        { principal, secret: K },
        { [header]: value, 'soorma-contract-version': '9.9.9' },
      );
      expectProblem(r, 400, 'malformed_request');
      expect(r.body.errors).toEqual([
        {
          header: header === 'authorization' ? 'Authorization' : 'Soorma-Delegation',
          detail: expect.any(String),
        },
      ]);
      expect(r.text).not.toContain(value);
    }
    // Not counted: well past the bound, the right K still signs in.
    for (let i = 0; i < 12; i++)
      await post(g.edge, '/sign-ins', { principal, secret: K }, { authorization: 'x' });
    expect((await post(g.edge, '/sign-ins', { principal, secret: K })).status).toBe(200);
  });

  it('refuses a missing or unaccepted contract version, listing the supported versions', async () => {
    const { principal } = await active(g);
    for (const version of ['0.2.0', '']) {
      const r = await post(
        g.edge,
        '/sign-ins',
        { principal, secret: K },
        { 'soorma-contract-version': version },
      );
      expectProblem(r, 400, 'unsupported_contract_version');
      expect(r.body.supportedVersions).toEqual(['0.1.0']);
    }
  });

  it('refuses a body that is not JSON, or fails the schema, naming the field', async () => {
    const { principal } = await active(g);
    expectProblem(await post(g.edge, '/sign-ins', '{not json'), 400, 'malformed_request');
    expectProblem(
      await post(g.edge, '/sign-ins', { principal, secret: K }, { 'content-type': 'text/plain' }),
      400,
      'malformed_request',
    );
    const unknown = await post(g.edge, '/sign-ins', { principal, secret: K, remember: true });
    expectProblem(unknown, 400, 'malformed_request');
    expect(unknown.body.errors).toContainEqual({
      pointer: '/remember',
      detail: expect.any(String),
    });
    const short = await post(g.edge, '/material-changes', {
      principal,
      current: { secret: K },
      change: { type: 'beginSecondFactor', authenticatorType: 'sms' },
    });
    expectProblem(short, 400, 'malformed_request');
  });

  it('TC-OI-055: a body over 16 KiB is payload_too_large', async () => {
    const r = await post(g.edge, '/sign-ins', {
      principal: { organization: 'o1', principal: 'h@x' },
      secret: 'x'.repeat(17_000),
    });
    expectProblem(r, 413, 'payload_too_large');
  });
});

describe('refusals over HTTP', () => {
  it('TC-OI-010: a wrong K is 403 authentication_failed, with no WWW-Authenticate', async () => {
    const { principal } = await active(g);
    expectProblem(
      await post(g.edge, '/sign-ins', { principal, secret: 'wrong secret' }),
      403,
      'authentication_failed',
    );
  });

  it('TC-OI-011: beyond the bound, 429 too_many_attempts with Retry-After', async () => {
    const { principal } = await active(g);
    for (let n = 1; n <= 10; n++) {
      if (n >= 6) g.clock.advance(2 ** (n - 6));
      await post(g.edge, '/sign-ins', { principal, secret: 'wrong' });
    }
    g.clock.advance(32);
    const r = await post(g.edge, '/sign-ins', { principal, secret: K });
    expectProblem(r, 429, 'too_many_attempts');
    expect(r.headers['retry-after']).toBe(String(900 - 63));
  });

  it('TC-OI-042 over HTTP: secret_rejected carries one errors[] entry with pointer and reason', async () => {
    const { principal } = await active(g);
    const r = await post(g.edge, '/material-changes', {
      principal,
      current: { secret: K },
      change: { type: 'replaceSecret', newSecret: 'password' },
    });
    expectProblem(r, 400, 'secret_rejected');
    expect(r.body.errors).toEqual([{ pointer: '/change/newSecret', reason: 'breached' }]);
    expect(r.body).not.toHaveProperty('reason');
  });

  it('TC-OI-014: where P is required and not enrolled, 403 second_factor_enrollment_required', async () => {
    const strict = await gateway(db, { secondFactorRequired: true });
    try {
      const { principal, em } = await registered(strict);
      const first = await post(strict.edge, '/first-authentication', {
        principal,
        enrollmentMaterial: em,
        newSecret: K,
      });
      expect(first.body).toEqual({
        principal,
        state: 'active',
        secondFactorEnrollmentRequired: true,
      });
      expectProblem(
        await post(strict.edge, '/sign-ins', { principal, secret: K }),
        403,
        'second_factor_enrollment_required',
      );
    } finally {
      await strict.close();
    }
  });
});

describe('the sign-in operations (TC-OI-020, 024, 027)', () => {
  it('TC-OI-027: refuses a credential of the wrong kind, two credentials, or delegation, as 401', async () => {
    const { token } = await active(g);
    const presentations: Record<string, string>[] = [
      {},
      { authorization: 'Bearer soorma_ec_abc' },
      { authorization: `Basic ${token}` },
      { authorization: `Bearer ${token}`, 'soorma-delegation': 'soorma_dc_x' },
    ];
    for (const headers of presentations) {
      expectProblem(
        await post(g.edge, '/sign-ins/current/renewal', undefined, headers),
        401,
        'credential_refused',
      );
    }
  });

  it('TC-OI-024: refuses a forged token; TC-OI-020: an expired one is credential_expired', async () => {
    const { token } = await active(g);
    const forged = `${token.slice(0, -4)}AAAA`;
    expectProblem(
      await post(g.edge, '/sign-ins/current/renewal', undefined, bearer(forged)),
      401,
      'credential_refused',
    );
    g.clock.advance(15 * 60);
    expectProblem(
      await post(g.edge, '/sign-ins/current/renewal', undefined, bearer(token)),
      401,
      'credential_expired',
    );
  });

  it('takes no body on the sign-in operations', async () => {
    const { token } = await active(g);
    expectProblem(
      await post(g.edge, '/sign-ins/current/end', { x: 1 }, bearer(token)),
      400,
      'malformed_request',
    );
  });
});

describe('TC-OI-047 (edge side): only the five operations are served', () => {
  it('answers an internal path, an unknown path, or another method with a bare 404', async () => {
    for (const r of [
      await get(g.edge, '/verify-keys'),
      await get(g.edge, '/principals/exists?organization=o1&principal=h@x'),
      await get(g.edge, '/sign-ins'),
      await post(g.edge, '/nowhere', {}),
    ]) {
      expect(r.status).toBe(404);
      expect(r.text).toBe('');
      expect(r.headers['soorma-request-id']).toBeDefined();
    }
  });
});

describe('TC-OI-052: S1 fails closed', () => {
  it('a store it cannot reach is 503 unavailable, with Retry-After', async () => {
    const down = Store.connect({
      host: '127.0.0.1',
      port: 1,
      database: 'x',
      user: 'x',
      password: 'x',
    });
    const broken = await gateway(db, { store: down });
    try {
      const r = await post(broken.edge, '/sign-ins', {
        principal: { organization: 'o1', principal: 'h@example.com' },
        secret: K,
      });
      expectProblem(r, 503, 'unavailable');
    } finally {
      await broken.close();
      await down.close();
    }
  });

  it('an exhausted hashing budget is 503 unavailable', async () => {
    const semaphore = new HashSemaphore(1, 50);
    const busy = await gateway(db, { semaphore });
    try {
      const { principal } = await active(busy);
      let release!: () => void;
      const gate = new Promise<void>((r) => (release = r));
      const held = semaphore.run(() => gate);
      const r = await post(busy.edge, '/sign-ins', { principal, secret: K });
      expectProblem(r, 503, 'unavailable');
      release();
      await held;
    } finally {
      await busy.close();
    }
  });
});

describe('TC-OI-004 and TC-OI-016 over HTTP: K and P', () => {
  it('requires a P proof once P is active', async () => {
    const { principal } = await active(g);
    const begun = await post(g.edge, '/material-changes', {
      principal,
      current: { secret: K },
      change: { type: 'beginSecondFactor', authenticatorType: 'totp' },
    });
    const { id, setup } = begun.body.enrollment as { id: string; setup: { seed: string } };
    const seed = asSecretBytes(base32Decode(setup.seed));
    const code = () => codeAt(seed, stepAt(g.clock.now()));
    const confirmed = await post(g.edge, '/material-changes', {
      principal,
      current: { secret: K },
      change: {
        type: 'confirmSecondFactor',
        enrollment: id,
        proof: { type: 'totp', code: code() },
      },
    });
    expect(confirmed.status).toBe(200);
    g.clock.advance(30);
    expectProblem(
      await post(g.edge, '/sign-ins', { principal, secret: K }),
      403,
      'authentication_failed',
    );
    const both = await post(g.edge, '/sign-ins', {
      principal,
      secret: K,
      secondFactor: { type: 'totp', code: code() },
    });
    expect(both.status).toBe(200);
    expect(both.body.signIn.classes).toEqual(['K', 'P']);
  });
});

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
