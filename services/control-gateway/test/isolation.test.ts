// SPDX-License-Identifier: FSL-1.1-ALv2
//
// What E holds and what it calls, and what of E2 reaches E, through S2's real
// edge over a test environment store with a stub S1:
//  - TC-EHA-022: E holds only verify material for the sign-in (public keys),
//    and no E operation issues a sign-in;
//  - TC-EHA-031: ending, a grant denied at authority, and an ended credential
//    make no call to S1;
//  - TC-EHA-050: identity comes from the credential alone, never from the
//    network (source address, forwarding headers, Host);
//  - TC-EHA-051: nothing of E2's reaches E: E2's credential is refused at each
//    of E's operations, a grant in E2 gives nothing at E, and a human's log
//    pseudonym differs per environment.
// The stack halves of TC-EHA-022, 050 and 067 are in the smoke test and the
// Compose-model test.
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { afterAll, beforeAll, describe, expect, it } from 'vitest';
import {
  testEnvDatabase,
  type TestEnvDatabase,
} from '../../../packages/env-store/test/harness/database.ts';
import {
  adminCredential,
  credentialFor,
  E2,
  environmentRing,
  gateway,
  grant,
  member,
  post,
  problem,
  unique,
  type Gateway,
} from './support.ts';

let db: TestEnvDatabase;
let g: Gateway;
beforeAll(async () => {
  db = await testEnvDatabase();
  g = await gateway(db);
});
afterAll(async () => {
  await g?.close();
  await db?.drop();
});

const OPERATIONS = [
  '/environment-credentials',
  '/environment-credentials/current/renewal',
  '/environment-credentials/current/end',
  '/grants',
] as const;

describe('TC-EHA-022: E holds only verify material for the organization sign-in', () => {
  it("S1's keys at E are public keys only", () => {
    const kids = g.stub.ring.jwks().keys.map((k) => k.kid);
    expect(kids.length).toBeGreaterThan(0);
    for (const kid of kids) expect(g.cache.verifyKey(kid)?.type, kid).toBe('public');
  });

  it("S2's operations are exactly its contract's four, and U5's two: none issues a sign-in", () => {
    const contract = readFileSync(
      resolve(import.meta.dirname, '../../../contract/control-gateway.openapi.yaml'),
      'utf8',
    );
    const paths = [...contract.matchAll(/^ {2}(\/[^:\s]*):\s*$/gm)].map((m) => m[1]);
    expect(paths.sort()).toEqual(
      // U5's two (D-CG-AR-16): registerAgent and issueRegistrationSecret
      [...OPERATIONS, '/registration-secrets', '/registrations'].sort(),
    );
    const fastify = g.edge.getHttpAdapter().getInstance();
    for (const url of OPERATIONS) expect(fastify.hasRoute({ method: 'POST', url }), url).toBe(true);
    for (const url of ['/sign-ins', '/first-authentication', '/sign-ins/current/renewal'])
      expect(fastify.hasRoute({ method: 'POST', url }), url).toBe(false);
  });
});

describe('TC-EHA-031: ending, a denied grant, and an ended credential make no call to S1', () => {
  it('the stub records no call for any of the three', async () => {
    const m = await member(g, ['agent:register']); // holds no grant:human
    const { credential: ended } = await adminCredential(g);
    expect(
      (await post(g.edge, '/environment-credentials/current/end', { credential: ended })).status,
    ).toBe(204);
    const live = await credentialFor(g, m.principal);
    const before = g.stub.calls.length;

    // 1. Ending a credential.
    expect(
      (await post(g.edge, '/environment-credentials/current/end', { credential: live.credential }))
        .status,
    ).toBe(204);
    // 2. grantToHuman by a principal without grant:human: denied at authority.
    expect(problem(await grant(g, m.credential, unique(), ['agent:register']))).toEqual({
      status: 403,
      code: 'forbidden',
    });
    // 3. An ended credential, at each operation that takes one.
    for (const url of OPERATIONS.slice(1))
      expect(problem(await post(g.edge, url, { credential: ended })), url).toEqual({
        status: 401,
        code: 'credential_refused',
      });

    expect(g.stub.calls.slice(before)).toEqual([]);
  });
});

describe('TC-EHA-050: identity comes from the credential alone, never the network', () => {
  const inject = (
    remoteAddress: string,
    headers: Record<string, string>,
    credential?: string,
    target?: string,
  ) =>
    g.edge
      .getHttpAdapter()
      .getInstance()
      .inject({
        method: 'POST',
        url: '/grants',
        remoteAddress,
        headers: {
          'soorma-contract-version': '0.1.0',
          'content-type': 'application/json',
          ...(credential ? { authorization: `Bearer ${credential}` } : {}),
          ...headers,
        },
        payload: JSON.stringify({
          target: { organization: 'o1', principal: target ?? g.admin },
          permissions: ['agent:register'],
        }),
      });

  it('one credential resolves the same actor from any address, whatever the headers claim', async () => {
    const { credential } = await adminCredential(g);
    const fromHost = await inject('127.0.0.1', {}, credential);
    const fromNetwork = await inject(
      '172.18.0.5',
      {
        'x-forwarded-for': '10.0.0.1',
        'x-real-ip': '10.0.0.2',
        host: 'org-gateway.soorma.internal',
      },
      credential,
    );
    for (const r of [fromHost, fromNetwork]) {
      expect(r.statusCode).toBe(200);
      expect((JSON.parse(r.body) as { selfGrant: boolean }).selfGrant).toBe(true);
    }
  });

  it('no credential is credential_refused, even from the internal network', async () => {
    for (const address of ['127.0.0.1', '172.18.0.5', '10.0.0.1']) {
      const r = await inject(address, { 'x-forwarded-for': '127.0.0.1' });
      expect(r.statusCode).toBe(401);
      expect((JSON.parse(r.body) as { code: string }).code).toBe('credential_refused');
    }
  });
});

describe("TC-EHA-051: nothing of E2's is reachable from E", () => {
  it("E2's credential is refused at each of E's operations; an E2 grant gives nothing at E; pseudonyms differ", async () => {
    const e2 = await gateway(db, {
      environment: E2,
      ring: environmentRing(),
      stub: g.stub,
      clock: g.clock,
    });
    try {
      // H holds agent:register in E, and grant:human in E2 only.
      const h = await member(g, ['agent:register']);
      const { credential: e2Admin } = await adminCredential(e2);
      expect((await grant(e2, e2Admin, h.principal, ['grant:human'])).status).toBe(200);
      const atE2 = await credentialFor(e2, h.principal);

      // 1. E2's credential at each of E's operations.
      for (const url of OPERATIONS)
        expect(problem(await post(g.edge, url, { credential: atE2.credential })), url).toEqual({
          status: 401,
          code: 'credential_refused',
        });

      // 2. At E, H's grant:human from E2 does not apply.
      expect(problem(await grant(g, h.credential, unique(), ['agent:register']))).toEqual({
        status: 403,
        code: 'forbidden',
      });
      // ...while at E2 it does.
      const target = unique();
      g.stub.principals.add(target);
      expect((await grant(e2, atE2.credential, target, ['agent:register'])).status).toBe(200);

      // 3. H's pseudonym differs between E's and E2's logs.
      const pseudonymOf = (gw: Gateway): unknown => {
        const issued = gw.log.named('credential.issued');
        return issued.at(-1)?.pseudonym;
      };
      await credentialFor(g, h.principal);
      const atE = pseudonymOf(g);
      await credentialFor(e2, h.principal);
      const atE2Log = pseudonymOf(e2);
      expect(atE).toMatch(/^hp_/);
      expect(atE2Log).toMatch(/^hp_/);
      expect(atE).not.toBe(atE2Log);
    } finally {
      await e2.close();
    }
  });
});
