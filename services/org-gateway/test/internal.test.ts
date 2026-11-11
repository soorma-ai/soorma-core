// SPDX-License-Identifier: FSL-1.1-ALv2
// The internal listener and the health listener: TC-OI-045, 046, 047; P-06,
// P-07; BR-INT-01 to 07.
import { request as httpRequest } from 'node:http';
import type { AddressInfo } from 'node:net';
import { HEALTH_HOST, listenHealth, signInternalRequest } from '@soorma/service-kit';
import { afterAll, beforeAll, describe, expect, it } from 'vitest';
import {
  testDatabase,
  type TestDatabase,
} from '../../../packages/org-identity/test/harness/database.ts';
import { active, gateway, get, internalGet, post, K, type Gateway } from './support.ts';

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

function refused(r: { status: number; body: any; headers: Record<string, unknown> }): void {
  expect(r.status).toBe(401);
  expect(r.body.code).toBe('credential_refused');
  expect(r.body).not.toHaveProperty('errors');
}

describe('TC-OI-046: each internal operation discloses only what it states', () => {
  it('verifyOnlyMaterial is a JWKS of public keys only', async () => {
    const r = await internalGet(g, '/verify-keys');
    expect(r.status).toBe(200);
    expect(Object.keys(r.body as object)).toEqual(['keys']);
    for (const key of r.body.keys as Record<string, unknown>[]) {
      expect(Object.keys(key).sort()).toEqual(['alg', 'crv', 'kid', 'kty', 'use', 'x']);
      expect(key).toMatchObject({ kty: 'OKP', crv: 'Ed25519', alg: 'Ed25519', use: 'sig' });
    }
  });

  it('principalExists answers yes or no, and nothing else', async () => {
    const { principal } = await active(g);
    const yes = await internalGet(
      g,
      `/principals/exists?organization=o1&principal=${encodeURIComponent(principal.principal)}`,
    );
    expect(yes.body).toEqual({ exists: true });
    const no = await internalGet(g, '/principals/exists?organization=o1&principal=nobody%40x.io');
    expect(no.body).toEqual({ exists: false });
    const otherOrg = await internalGet(
      g,
      `/principals/exists?organization=o2&principal=${encodeURIComponent(principal.principal)}`,
    );
    expect(otherOrg.body).toEqual({ exists: false });
  });

  it('signInStatus answers live with its expiry, ended, or unknown, and nothing else (A7)', async () => {
    const { token } = await active(g);
    const { sid, exp } = JSON.parse(Buffer.from(token.split('.')[1]!, 'base64url').toString()) as {
      sid: string;
      exp: number;
    };
    const live = (await internalGet(g, `/sign-ins/${sid}/status`)).body as {
      status: string;
      expiresAt: string;
    };
    expect(Object.keys(live).sort()).toEqual(['expiresAt', 'status']);
    expect(live.status).toBe('live');
    expect(Math.floor(Date.parse(live.expiresAt) / 1000)).toBe(exp);
    await post(g.edge, '/sign-ins/current/end', undefined, { authorization: `Bearer ${token}` });
    expect((await internalGet(g, `/sign-ins/${sid}/status`)).body).toEqual({ status: 'ended' });
    expect(
      (await internalGet(g, '/sign-ins/0123456789abcdef0123456789abcdef/status')).body,
    ).toEqual({
      status: 'unknown',
    });
  });
});

describe('TC-OI-045: the internal interface accepts only signed requests bound to their content', () => {
  const url = '/principals/exists?organization=o1&principal=h%40example.com';

  it('refuses no token, and logs the refusal without a token', async () => {
    refused(await get(g.internal, url));
    const line = g.log.events().at(-1)!;
    expect(line.event).toBe('internal.call_refused');
  });

  it('refuses a key no environment is configured with', async () => {
    const { generateKeyPairSync } = await import('node:crypto');
    refused(await internalGet(g, url, { key: generateKeyPairSync('ed25519').privateKey }));
  });

  it("refuses another environment's key under this environment's iss", async () => {
    refused(await internalGet(g, url, { key: g.otherCallerKey, environment: 'e' }));
    expect((await internalGet(g, url, { key: g.otherCallerKey, environment: 'e2' })).status).toBe(
      200,
    );
  });

  it('refuses an expired token, and one reused with another query or body', async () => {
    refused(await internalGet(g, url, { now: new Date(g.clock.ms - 120_000) }));
    refused(
      await internalGet(g, '/principals/exists?organization=o1&principal=other%40example.com', {
        target: url,
      }),
    );
    const token = await signInternalRequest(
      { environment: 'e', method: 'GET', target: url },
      g.callerKey,
      'o1',
      g.clock.now(),
    );
    const withBody = await g.internal
      .getHttpAdapter()
      .getInstance()
      .inject({
        method: 'GET',
        url,
        headers: { authorization: `Bearer ${token}`, 'content-type': 'application/json' },
        payload: '{"x":1}',
      });
    expect(withBody.statusCode).toBe(401);
  });

  it('never takes network location as the check (I3)', async () => {
    refused(
      await get(g.internal, url, { 'x-forwarded-for': '127.0.0.1', 'x-real-ip': '127.0.0.1' }),
    );
    const token = await signInternalRequest(
      { environment: 'e', method: 'GET', target: url },
      g.callerKey,
      'o1',
      g.clock.now(),
    );
    const signed = await get(g.internal, url, {
      authorization: `Bearer ${token}`,
      'x-forwarded-for': '203.0.113.9',
    });
    expect(signed.status).toBe(200);
  });

  it('refuses a token for another audience, method, or with a long lifetime', async () => {
    const other = await signInternalRequest(
      { environment: 'e', method: 'GET', target: url },
      g.callerKey,
      'o2',
      g.clock.now(),
    );
    refused(await get(g.internal, url, { authorization: `Bearer ${other}` }));
    const post_ = await signInternalRequest(
      { environment: 'e', method: 'POST', target: url },
      g.callerKey,
      'o1',
      g.clock.now(),
    );
    refused(await get(g.internal, url, { authorization: `Bearer ${post_}` }));
    const long = await signInternalRequest(
      { environment: 'e', method: 'GET', target: url },
      g.callerKey,
      'o1',
      g.clock.now(),
      3600,
    );
    refused(await get(g.internal, url, { authorization: `Bearer ${long}` }));
  });

  it('a sign-in token is no internal credential', async () => {
    const { token } = await active(g);
    refused(await get(g.internal, '/verify-keys', { authorization: `Bearer ${token}` }));
  });
});

describe('TC-OI-047: the listeners are separate', () => {
  it('serves no edge operation on the internal listener', async () => {
    for (const path of ['/sign-ins', '/first-authentication', '/material-changes']) {
      const r = await post(g.internal, path, {
        principal: { organization: 'o1', principal: 'h@x' },
        secret: K,
      });
      expect(r.status).toBe(404);
    }
  });

  it('the health listener is bound to loopback, answers GET / with 204, and serves nothing else', async () => {
    const server = await listenHealth(0);
    try {
      const address = server.address() as AddressInfo;
      expect(address.address).toBe(HEALTH_HOST);
      const call = (method: string, path: string) =>
        new Promise<{ status: number; body: string }>((resolve, reject) => {
          const req = httpRequest(
            { host: HEALTH_HOST, port: address.port, method, path },
            (res) => {
              let body = '';
              res.on('data', (c: Buffer) => (body += c.toString()));
              res.on('end', () => resolve({ status: res.statusCode ?? 0, body }));
            },
          );
          req.on('error', reject);
          req.end();
        });
      expect(await call('GET', '/')).toEqual({ status: 204, body: '' });
      expect((await call('GET', '/verify-keys')).status).toBe(404);
      expect((await call('POST', '/')).status).toBe(404);
    } finally {
      server.close();
    }
  });
});
