// SPDX-License-Identifier: FSL-1.1-ALv2
//
// S2's operations through its real edge, over a test environment store, with
// a stub S1: the issuance, renewal, ending, and grant flows, and their
// refusals in the check order (Functional Design §11).
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
  MINUTE,
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

async function rows(sql: string, params: unknown[] = []): Promise<Record<string, any>[]> {
  const c = await db.app();
  try {
    return (await c.query(sql, params)).rows as Record<string, any>[];
  } finally {
    await c.end();
  }
}

const payload = (token: string): Record<string, any> =>
  JSON.parse(Buffer.from(token.split('.')[1]!, 'base64url').toString()) as Record<string, any>;

describe('TC-EHA-001: configuration grants the first Admin grant:human and human:manage', () => {
  it('writes one configuration grant and one configuration record, at start-up', async () => {
    const grants = await rows('SELECT * FROM grants WHERE principal = $1', [g.admin]);
    expect(grants).toHaveLength(1);
    expect(grants[0]).toMatchObject({
      granted_by_kind: 'configuration',
      permissions: ['grant:human', 'human:manage'],
      self_grant: false,
    });
    const records = await rows(
      "SELECT * FROM attribution_records WHERE operation = 'configureFirstGrant' AND target_id = $1",
      [grants[0]!.id],
    );
    expect(records).toHaveLength(1);
    expect(records[0]).toMatchObject({ actor_kind: 'configuration', request_id: null });
  });
});

describe('TC-EHA-002, 055: an environment credential is issued from a live sign-in', () => {
  it('returns { credential, expiresAt }: a soorma-ec+jwt token, 15 minutes, with one signInStatus call', async () => {
    const before = g.stub.count('signInStatus');
    const s = await g.stub.signIn(g.admin);
    const r = await post(g.edge, '/environment-credentials', { credential: s.token });
    expect(r.status).toBe(200);
    expect(Object.keys(r.body as object).sort()).toEqual(['credential', 'expiresAt']);
    const token = r.body.credential as string;
    expect(token.startsWith('soorma_ec_')).toBe(true);
    const claims = payload(token);
    expect(claims.env).toEqual({ organization: 'o1', project: 'p1', environment: 'e' });
    expect(claims.sub).toBe(g.admin);
    expect(claims.exp - claims.iat).toBe(15 * 60);
    expect(r.body.expiresAt).toBe(new Date(claims.exp * 1000).toISOString());
    expect(g.stub.count('signInStatus') - before).toBe(1);
    const [record] = await rows('SELECT * FROM credentials WHERE id = $1', [claims.cid]);
    expect(record).toMatchObject({ state: 'live', issued_from: s.sid, principal: g.admin });
    const [attribution] = await rows(
      "SELECT * FROM attribution_records WHERE operation = 'issueEnvironmentCredential' AND target_id = $1",
      [claims.cid],
    );
    expect(attribution).toMatchObject({
      actor_kind: 'human',
      credential_kind: 'signIn',
      credential_id: s.sid,
    });
    expect(g.log.named('credential.issued').at(-1)?.pseudonym).toMatch(/^hp_/);
  });

  it('caps the expiry at the sign-in’s: 6 minutes left gives 6 minutes (TC-EHA-019)', async () => {
    const left = new Date(g.clock.now().getTime() + 6 * MINUTE);
    const c = await credentialFor(g, g.admin, { expiresAt: left });
    expect(c.expiresAt).toBe(left.toISOString());
  });
});

describe('TC-EHA-003, 028: renewal', () => {
  it('a new token for the same cid, capped at the sign-in’s current expiry, which A7 reports', async () => {
    const left = new Date(g.clock.now().getTime() + 6 * MINUTE);
    const c = await credentialFor(g, g.admin, { expiresAt: left });
    const first = payload(c.credential);
    // The sign-in is renewed at S1: A7 now reports 15 minutes.
    const renewedTo = new Date(g.clock.now().getTime() + 15 * MINUTE);
    g.stub.statuses.set(c.sid, { status: 'live', expiresAt: renewedTo });
    const r = await post(g.edge, '/environment-credentials/current/renewal', {
      credential: c.credential,
    });
    expect(r.status).toBe(200);
    const next = payload(r.body.credential as string);
    expect(next.cid).toBe(first.cid);
    expect(next.jti).not.toBe(first.jti);
    expect(r.body.expiresAt).toBe(renewedTo.toISOString());
    expect(Object.keys(next).sort()).toEqual(['cid', 'env', 'exp', 'iat', 'jti', 'sub']);
  });
});

describe('TC-EHA-004, 014: ending', () => {
  it('204 with no body, with no call to S1; every token of the credential is refused after', async () => {
    const c = await adminCredential(g);
    const calls = g.stub.calls.length;
    const r = await post(g.edge, '/environment-credentials/current/end', {
      credential: c.credential,
    });
    expect(r.status).toBe(204);
    expect(r.text).toBe('');
    expect(g.stub.calls.length).toBe(calls);
    const [record] = await rows('SELECT * FROM credentials WHERE id = $1', [
      payload(c.credential).cid,
    ]);
    expect(record).toMatchObject({ state: 'ended', ended_by: 'self' });
    for (const url of [
      '/environment-credentials/current/renewal',
      '/environment-credentials/current/end',
    ])
      expect(problem(await post(g.edge, url, { credential: c.credential }))).toEqual({
        status: 401,
        code: 'credential_refused',
      });
    expect(problem(await grant(g, c.credential, unique(), ['agent:register'])).code).toBe(
      'credential_refused',
    );
  });
});

describe('TC-EHA-005 to 008: grants', () => {
  it('a self-grant is recorded as one (TC-EHA-005), and is usable on the next request (TC-EHA-027)', async () => {
    const m = await member(g, ['grant:human']);
    const r = await grant(g, m.credential, m.principal, ['agent:register']);
    expect(r.status).toBe(200);
    expect(r.body).toMatchObject({
      target: { organization: 'o1', principal: m.principal },
      permissions: ['agent:register'],
      selfGrant: true,
    });
    const [attribution] = await rows(
      "SELECT * FROM attribution_records WHERE operation = 'grantToHuman' AND target_id = $1",
      [r.body.id],
    );
    expect(attribution).toMatchObject({ self_grant: true, actor_kind: 'human', chain: null });
    expect(g.log.named('grant.made').length).toBeGreaterThan(0);
  });

  it('a grant to another is not a self-grant, after one principalExists call (TC-EHA-006)', async () => {
    const { credential } = await adminCredential(g);
    const j = unique();
    g.stub.principals.add(j);
    const before = g.stub.count('principalExists');
    const r = await grant(g, credential, j, ['agent:register']);
    expect(r.status).toBe(200);
    expect(r.body.selfGrant).toBe(false);
    expect(g.stub.count('principalExists') - before).toBe(1);
  });

  it('granting does not require holding the permission (TC-EHA-007); human-only ones are grantable (TC-EHA-008)', async () => {
    const { credential } = await adminCredential(g);
    const j = unique();
    g.stub.principals.add(j);
    const r = await grant(g, credential, j, ['event:publish', 'agent:delegate', 'grant:human']);
    expect(r.status).toBe(200);
    expect(r.body.permissions).toEqual(['agent:delegate', 'event:publish', 'grant:human']);
  });

  it('a pending principal may be a target (TC-EHA-091)', async () => {
    const { credential } = await adminCredential(g);
    const pending = unique();
    g.stub.principals.add(pending); // S1 knows it; it has not activated
    expect((await grant(g, credential, pending, ['agent:register'])).status).toBe(200);
  });
});

describe('refusals, in the check order', () => {
  it('TC-EHA-009: a sign-in is refused everywhere but issuance', async () => {
    const s = await g.stub.signIn(g.admin);
    for (const url of [
      '/environment-credentials/current/renewal',
      '/environment-credentials/current/end',
      '/grants',
    ]) {
      const r = await post(g.edge, url, { credential: s.token });
      expect(problem(r)).toEqual({ status: 401, code: 'credential_refused' });
      expect(r.headers['www-authenticate']).toBe('Bearer');
    }
  });

  it("TC-EHA-010: E2's credential is refused at E, before its expiry is read", async () => {
    const e2 = await gateway(db, {
      environment: E2,
      ring: environmentRing(),
      stub: g.stub,
      clock: g.clock,
    });
    try {
      const c = await credentialFor(e2, e2.admin);
      g.clock.advance(20 * 60); // past its expiry: still refused, never credential_expired
      for (const url of [
        '/environment-credentials/current/renewal',
        '/environment-credentials/current/end',
        '/grants',
      ])
        expect(problem(await post(g.edge, url, { credential: c.credential }))).toEqual({
          status: 401,
          code: 'credential_refused',
        });
    } finally {
      g.clock.advance(-20 * 60);
      await e2.close();
    }
  });

  it('TC-EHA-011: a principal with no grant in E gets no credential', async () => {
    const nobody = unique();
    const s = await g.stub.signIn(nobody);
    const r = await post(g.edge, '/environment-credentials', { credential: s.token });
    expect(problem(r)).toEqual({ status: 403, code: 'forbidden' });
    expect(r.headers['www-authenticate']).toBeUndefined();
    expect(await rows('SELECT 1 FROM credentials WHERE principal = $1', [nobody])).toHaveLength(0);
    expect(g.log.named('credential.refused').at(-1)?.code).toBe('no_grant_in_environment');
  });

  it('TC-EHA-012, 042: without grant:human, a grant is forbidden, before any existence check', async () => {
    const m = await member(g, ['agent:register']);
    const before = g.stub.count('principalExists');
    const exists = await grant(g, m.credential, g.admin, ['agent:register']);
    const absent = await grant(g, m.credential, 'nobody@example.com', ['agent:register']);
    expect(problem(exists)).toEqual({ status: 403, code: 'forbidden' });
    expect(absent.status).toBe(exists.status);
    expect({ ...absent.body, instance: undefined }).toEqual({
      ...exists.body,
      instance: undefined,
    });
    expect(g.stub.count('principalExists')).toBe(before);
    expect(g.log.named('grant.denied').at(-1)?.code).toBe('authority_denied');
  });

  it('TC-EHA-013, 038: unknown_permission names each unaccepted identifier, at most 10', async () => {
    const { credential } = await adminCredential(g);
    const permissions = ['agent:register', ...Array.from({ length: 12 }, (_, i) => `x:p${i}`)];
    const r = await grant(g, credential, g.admin, permissions);
    expect(problem(r)).toEqual({ status: 400, code: 'unknown_permission' });
    expect((r.body.errors as { pointer: string }[]).map((e) => e.pointer)).toEqual(
      Array.from({ length: 10 }, (_, i) => `/permissions/${i + 1}`),
    );
  });

  it('TC-EHA-039: a malformed grant body is malformed_request with pointers, before authority', async () => {
    const m = await member(g, ['agent:register']);
    for (const body of [
      { permissions: ['agent:register'] },
      {
        target: { organization: 'o1', principal: g.admin },
        permissions: ['agent:register'],
        extra: 1,
      },
      { target: { organization: 'o1', principal: g.admin }, permissions: [] },
      {
        target: { organization: 'o1', principal: g.admin },
        permissions: ['agent:register', 'agent:register'],
      },
      { target: { organization: 'o1', principal: g.admin }, permissions: ['Not Valid'] },
    ]) {
      const r = await post(g.edge, '/grants', { credential: m.credential, body });
      expect(problem(r)).toEqual({ status: 400, code: 'malformed_request' });
      expect((r.body.errors as unknown[]).length).toBeGreaterThan(0);
    }
  });

  it('TC-EHA-015, 016, 032, 034: other kinds and presentations are refused by kind', async () => {
    const c = await adminCredential(g);
    const presentations: Record<string, string>[] = [
      { authorization: 'Bearer soorma_ac_abc' },
      { authorization: 'Bearer soorma_dc_abc' },
      { authorization: 'Bearer soorma_xx_abc' },
      { authorization: `Bearer ${c.credential}`, 'soorma-delegation': 'anything' },
      { authorization: `Bearer soorma_ec_${'a'.repeat(4087)}` },
    ];
    for (const headers of presentations)
      expect(
        problem(await post(g.edge, '/environment-credentials/current/renewal', { headers })),
      ).toEqual({
        status: 401,
        code: 'credential_refused',
      });
  });

  it('TC-EHA-033: an environment credential at issuance is refused', async () => {
    const c = await adminCredential(g);
    expect(
      problem(await post(g.edge, '/environment-credentials', { credential: c.credential })),
    ).toEqual({
      status: 401,
      code: 'credential_refused',
    });
  });

  it('TC-EHA-017: an expired credential is credential_expired, and cannot be renewed or ended', async () => {
    const c = await adminCredential(g);
    g.clock.advance(15 * 60);
    try {
      for (const url of [
        '/environment-credentials/current/renewal',
        '/environment-credentials/current/end',
        '/grants',
      ])
        expect(problem(await post(g.edge, url, { credential: c.credential }))).toEqual({
          status: 401,
          code: 'credential_expired',
        });
    } finally {
      g.clock.advance(-15 * 60);
    }
  });

  it('TC-EHA-018, 041: an unknown target, or one of another organization (with no call), is unknown_principal', async () => {
    const { credential } = await adminCredential(g);
    const absent = await grant(g, credential, 'nobody@example.com', ['agent:register']);
    expect(problem(absent)).toEqual({ status: 400, code: 'unknown_principal' });
    expect(absent.body.errors).toEqual([{ pointer: '/target', detail: expect.any(String) }]);
    const before = g.stub.count('principalExists');
    const other = await grant(g, credential, g.admin, ['agent:register'], 'o2');
    expect(problem(other).code).toBe('unknown_principal');
    expect(g.stub.count('principalExists')).toBe(before);
  });

  it('TC-EHA-020, 029: after the sign-in ends, renewal is refused; the credential still works to its expiry', async () => {
    const c = await adminCredential(g);
    g.stub.statuses.set(c.sid, { status: 'ended' });
    expect(
      problem(
        await post(g.edge, '/environment-credentials/current/renewal', {
          credential: c.credential,
        }),
      ),
    ).toEqual({
      status: 401,
      code: 'credential_refused',
    });
    const j = unique();
    g.stub.principals.add(j);
    expect((await grant(g, c.credential, j, ['agent:register'])).status).toBe(200);
    expect(
      (await post(g.edge, '/environment-credentials/current/end', { credential: c.credential }))
        .status,
    ).toBe(204);
  });

  it('TC-EHA-025: issuance from an ended sign-in is refused', async () => {
    const s = await g.stub.signIn(g.admin, { status: { status: 'ended' } });
    expect(
      problem(await post(g.edge, '/environment-credentials', { credential: s.token })),
    ).toEqual({
      status: 401,
      code: 'credential_refused',
    });
    expect(g.log.named('credential.refused').at(-1)?.code).toBe('sign_in_refused');
  });

  it('TC-EHA-026: a grant made after issuance applies at once; renewal adds nothing to the token', async () => {
    const m = await member(g, ['agent:register']);
    const target = unique();
    g.stub.principals.add(target);
    expect((await grant(g, m.credential, target, ['agent:register'])).status).toBe(403);
    const { credential } = await adminCredential(g);
    expect((await grant(g, credential, m.principal, ['grant:human'])).status).toBe(200);
    expect((await grant(g, m.credential, target, ['agent:register'])).status).toBe(200);
    const renewed = await post(g.edge, '/environment-credentials/current/renewal', {
      credential: m.credential,
    });
    expect(Object.keys(payload(renewed.body.credential as string)).sort()).toEqual([
      'cid',
      'env',
      'exp',
      'iat',
      'jti',
      'sub',
    ]);
  });

  it('TC-EHA-052: body-less operations refuse a body; the contract version is required', async () => {
    const c = await adminCredential(g);
    const withBody = await post(g.edge, '/environment-credentials/current/renewal', {
      credential: c.credential,
      body: '{}',
    });
    expect(problem(withBody)).toEqual({ status: 400, code: 'malformed_request' });
    expect(withBody.body.errors).toEqual([{ pointer: '', detail: expect.any(String) }]);
    const s = await g.stub.signIn(g.admin);
    for (const version of [undefined, '9.9.9']) {
      const r = await g.edge
        .getHttpAdapter()
        .getInstance()
        .inject({
          method: 'POST',
          url: '/environment-credentials',
          headers: {
            authorization: `Bearer ${s.token}`,
            ...(version === undefined ? {} : { 'soorma-contract-version': version }),
          },
        });
      expect(r.statusCode).toBe(400);
      expect((JSON.parse(r.body) as { code: string }).code).toBe('unsupported_contract_version');
    }
  });

  it('TC-EHA-071: a body over 16 KiB is payload_too_large', async () => {
    const c = await adminCredential(g);
    const big = JSON.stringify({
      target: { organization: 'o1', principal: g.admin },
      permissions: ['agent:register'],
      pad: 'x'.repeat(16 * 1024),
    });
    expect(problem(await post(g.edge, '/grants', { credential: c.credential, body: big }))).toEqual(
      {
        status: 413,
        code: 'payload_too_large',
      },
    );
  });

  it('TC-EHA-074: a token minted before a renewal stays valid until its own expiry', async () => {
    const c = await adminCredential(g);
    const renewed = await post(g.edge, '/environment-credentials/current/renewal', {
      credential: c.credential,
    });
    expect(renewed.status).toBe(200);
    const j = unique();
    g.stub.principals.add(j);
    expect((await grant(g, c.credential, j, ['agent:register'])).status).toBe(200);
    expect(
      (
        await post(g.edge, '/environment-credentials/current/end', {
          credential: renewed.body.credential as string,
        })
      ).status,
    ).toBe(204);
    expect(problem(await grant(g, c.credential, j, ['agent:register'])).code).toBe(
      'credential_refused',
    );
  });

  it('TC-EHA-077: a client-sent request id is replaced; responses carry the contract version', async () => {
    const r = await post(g.edge, '/environment-credentials', {
      headers: { 'soorma-request-id': 'client-chosen' },
    });
    expect(r.headers['soorma-request-id']).not.toBe('client-chosen');
    expect(r.headers['soorma-contract-version']).toBe('0.1.0');
  });

  it('TC-EHA-049: a forged sign-in and a forged environment credential are refused', async () => {
    const other = await g.stub.signIn(g.admin, {
      ring: (await import('./support.ts')).organizationRing(),
    });
    expect(
      problem(await post(g.edge, '/environment-credentials', { credential: other.token })).code,
    ).toBe('credential_refused');
    const e2 = await gateway(db, { ring: environmentRing(), stub: g.stub, clock: g.clock });
    try {
      const forged = await credentialFor(e2, e2.admin);
      expect(problem(await grant(g, forged.credential, unique(), ['agent:register'])).code).toBe(
        'credential_refused',
      );
    } finally {
      await e2.close();
    }
  });
});

describe('TC-EHA-021: a direct human operation is attributed to the human, with no envelope', () => {
  it('every human record has its principal and credential, and no chain, origin, or re-broadening', async () => {
    const records = await rows("SELECT * FROM attribution_records WHERE actor_kind = 'human'");
    expect(records.length).toBeGreaterThan(0);
    for (const r of records) {
      expect(r.principal).toBeTruthy();
      expect(r.credential_id).toBeTruthy();
      expect([r.chain, r.origin, r.rebroadening_load_bearing, r.sponsor]).toEqual([
        null,
        null,
        null,
        null,
      ]);
    }
  });
});
