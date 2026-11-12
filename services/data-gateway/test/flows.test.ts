// SPDX-License-Identifier: FSL-1.1-ALv2
//
// S3's two operations end to end in process, over the test store as
// soorma_env_data (business-logic-model §2, §3, §4): TC-AC-001 to 006, 011,
// 016, 019, 024, 027, 028, 031, 032, 035, 051, 053, 055.
import { AGENT_CREDENTIAL_LIFETIME_MS, LINEAGE_MAX_AGE_MS } from '@soorma/credentials';
import { afterAll, beforeAll, describe, expect, it } from 'vitest';
import {
  testEnvDatabase,
  type TestEnvDatabase,
} from '../../../packages/env-store/test/harness/database.ts';
import {
  seedAgentRevocation,
  seedCredentialRevocation,
} from '../../../packages/env-store/test/harness/seed.ts';
import {
  agentId,
  bootstrap,
  claims,
  credentialFor,
  decoded,
  E,
  gateway,
  MINUTE,
  problem,
  registered,
  renew,
  request,
  RENEWAL,
  rows,
  SPONSOR,
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

const seconds = (ms: number): number => Math.floor(ms / 1000);
const ENV = ['o1', 'p1', 'e'];

describe('TC-AC-001: bootstrap returns a short-lived credential bound to the registration and E', () => {
  it('200, no-store, the body, the token, and the record', async () => {
    const agent = agentId();
    const secret = await registered(g, agent);
    const r = await bootstrap(g, agent, secret.value, 'i-1');
    expect(r.status).toBe(200);
    expect(r.headers['cache-control']).toBe('no-store');
    expect(Object.keys(r.body as object).sort()).toEqual([
      'agent',
      'credential',
      'environment',
      'expiresAt',
      'instance',
    ]);
    expect(r.body).toMatchObject({ agent, environment: { ...E }, instance: 'i-1' });
    const { header, claims: c } = decoded(r.body.credential as string);
    expect(r.body.credential).toMatch(/^soorma_ac_/);
    expect(header).toMatchObject({ typ: 'soorma-ac+jwt', alg: 'Ed25519' });
    expect(Object.keys(c).sort()).toEqual(['cid', 'env', 'exp', 'iat', 'inst', 'jti', 'sub']);
    expect(c).toMatchObject({ env: { ...E }, sub: agent, inst: 'i-1' });
    expect(c.exp - c.iat).toBeLessThanOrEqual(seconds(AGENT_CREDENTIAL_LIFETIME_MS));
    const [row] = await rows(g, 'agent_credentials', agent);
    expect(row).toMatchObject({
      id: c.cid,
      organization: 'o1',
      project: 'p1',
      environment: 'e',
      agent,
      instance: 'i-1',
      secret: secret.id,
    });
    expect(seconds((row!.expires_at as Date).getTime())).toBe(c.exp);
    expect((row!.lineage_ends_at as Date).getTime() - (row!.issued_at as Date).getTime()).toBe(
      LINEAGE_MAX_AGE_MS,
    );
  });
});

describe('TC-AC-002: the instance identifier is recorded, not verified', () => {
  it('two instances bootstrap with their own identifiers and distinct lineages', async () => {
    const agent = agentId();
    const secret = await registered(g, agent);
    const a = await bootstrap(g, agent, secret.value, 'i-1');
    const b = await bootstrap(g, agent, secret.value, 'host-7:i-2');
    expect([a.status, b.status]).toEqual([200, 200]);
    expect([
      claims(a.body.credential as string).inst,
      claims(b.body.credential as string).inst,
    ]).toEqual(['i-1', 'host-7:i-2']);
    expect(claims(a.body.credential as string).cid).not.toBe(
      claims(b.body.credential as string).cid,
    );
  });
});

describe('TC-AC-024: two live credentials may assert the same instance identifier', () => {
  it('both bootstraps and both renewals succeed, with distinct cids', async () => {
    const agent = agentId();
    const secret = await registered(g, agent);
    const a = await bootstrap(g, agent, secret.value, 'i-1');
    const b = await bootstrap(g, agent, secret.value, 'i-1');
    expect([a.status, b.status]).toEqual([200, 200]);
    expect(claims(a.body.credential as string).cid).not.toBe(
      claims(b.body.credential as string).cid,
    );
    expect((await renew(g, a.body.credential as string)).status).toBe(200);
    expect((await renew(g, b.body.credential as string)).status).toBe(200);
  });
});

describe('TC-AC-003, 016, 055: renewal keeps the binding and moves the expiry, capped', () => {
  it('the same cid, sub, inst, env; a new jti; exp = now + L; the row moves to it', async () => {
    const c = await credentialFor(g);
    const before = claims(c.credential);
    g.clock.advance(10 * MINUTE);
    const r = await renew(g, c.credential);
    expect(r.status).toBe(200);
    expect(r.headers['cache-control']).toBe('no-store');
    const after = claims(r.body.credential as string);
    for (const k of ['cid', 'sub', 'inst', 'env']) expect(after[k], k).toEqual(before[k]);
    expect(after.jti).not.toBe(before.jti);
    expect(after.exp).toBe(seconds(g.clock.now().getTime() + AGENT_CREDENTIAL_LIFETIME_MS));
    expect(Date.parse(r.body.expiresAt as string) / 1000).toBe(after.exp);
    expect(Object.keys(after).sort()).toEqual(['cid', 'env', 'exp', 'iat', 'inst', 'jti', 'sub']);
    const [row] = await rows(g, 'agent_credentials', c.agent);
    expect(seconds((row!.expires_at as Date).getTime())).toBe(after.exp);
  });

  it('TC-AC-055: every response’s expiresAt equals its token’s exp, iat + L', async () => {
    const agent = agentId();
    const secret = await registered(g, agent);
    const r = await bootstrap(g, agent, secret.value);
    const c = claims(r.body.credential as string);
    expect(c.exp).toBe(c.iat + seconds(AGENT_CREDENTIAL_LIFETIME_MS));
    expect(Date.parse(r.body.expiresAt as string) / 1000).toBe(c.exp);
  });

  it('near the lineage end, renewal is capped at it, and never extends past it', async () => {
    const c = await credentialFor(g);
    const start = claims(c.credential).iat as number;
    let token = c.credential;
    // Renew every 10 minutes until the lineage end is within L.
    while (
      g.clock.now().getTime() + AGENT_CREDENTIAL_LIFETIME_MS <
      start * 1000 + LINEAGE_MAX_AGE_MS
    ) {
      g.clock.advance(10 * MINUTE);
      const r = await renew(g, token);
      expect(r.status).toBe(200);
      token = r.body.credential as string;
    }
    const capped = claims(token);
    expect(capped.exp).toBe(start + seconds(LINEAGE_MAX_AGE_MS));
    g.clock.advance(MINUTE);
    const again = await renew(g, token);
    expect(again.status).toBe(200);
    expect(claims(again.body.credential as string).exp).toBe(capped.exp);
    // Past the lineage end, the token has expired: the instance bootstraps again.
    g.clock.ms = (capped.exp as number) * 1000;
    expect(problem(await renew(g, token))).toEqual({ status: 401, code: 'credential_expired' });
  });
});

describe('TC-AC-004: neither operation carries an envelope', () => {
  it('the responses hold no envelope field', async () => {
    const c = await credentialFor(g);
    const r = await renew(g, c.credential);
    for (const body of [r.body as object])
      for (const k of ['envelope', 'actorChain', 'originMode', 'chain', 'origin'])
        expect(body).not.toHaveProperty(k);
  });
});

describe('TC-AC-005, 035: bootstrap and renewal are attributed, and the record says why it has no chain', () => {
  it('one record per operation, in the credential’s transaction, readable alone', async () => {
    const c = await credentialFor(g);
    await renew(g, c.credential);
    const records = (await rows(g, 'attribution_records', c.agent)).sort(
      (a, b) => (a.recorded_at as Date).getTime() - (b.recorded_at as Date).getTime(),
    );
    expect(records.map((r) => r.operation as string)).toEqual([
      'exchangeBootstrap',
      'renewAgentCredential',
    ]);
    for (const r of records) {
      expect(r).toMatchObject({
        organization: 'o1',
        project: 'p1',
        environment: 'e',
        actor_kind: 'agent',
        principal: null,
        registration: c.agent,
        instance: 'i-1',
        sponsor: SPONSOR,
        target_kind: 'agentCredential',
        target_id: c.cid,
        chain: null,
        origin: null,
        rebroadening_load_bearing: null,
        rebroadening_hop: null,
      });
    }
    expect(records[0]).toMatchObject({ credential_kind: null, credential_id: null });
    expect(records[1]).toMatchObject({ credential_kind: 'agentCredential', credential_id: c.cid });
  });

  it('TC-AC-035 step 2: a bootstrap whose record cannot be written leaves no credential', async () => {
    const agent = agentId();
    const secret = await registered(g, agent);
    await g.owner.query('REVOKE INSERT ON attribution_records FROM soorma_env_data');
    try {
      expect(problem(await bootstrap(g, agent, secret.value))).toEqual({
        status: 503,
        code: 'unavailable',
        retryAfter: '5',
      });
    } finally {
      await g.owner.query('GRANT INSERT ON attribution_records TO soorma_env_data');
    }
    expect(await rows(g, 'agent_credentials', agent)).toEqual([]);
  });
});

describe('TC-AC-006, 019: the direct revocation read', () => {
  it('an unrevoked credential renews; the read writes no attribution record', async () => {
    const c = await credentialFor(g);
    const before = (await rows(g, 'attribution_records', c.agent)).length;
    expect((await renew(g, c.credential)).status).toBe(200);
    expect((await rows(g, 'attribution_records', c.agent)).length).toBe(before + 1);
  });
});

describe('TC-AC-011: an expired credential cannot be renewed; the instance bootstraps again', () => {
  it('credential_expired after verifying; then bootstrap succeeds with a new cid', async () => {
    const c = await credentialFor(g);
    g.clock.advance(AGENT_CREDENTIAL_LIFETIME_MS);
    expect(problem(await renew(g, c.credential))).toEqual({
      status: 401,
      code: 'credential_expired',
    });
    const again = await bootstrap(g, c.agent, c.secret.value);
    expect(again.status).toBe(200);
    expect(claims(again.body.credential as string).cid).not.toBe(c.cid);
  });
});

describe('TC-AC-027: renewal never consults the registration secret', () => {
  it('renewal succeeds with no privilege on registration_secrets', async () => {
    const c = await credentialFor(g);
    await g.owner.query('REVOKE SELECT ON registration_secrets FROM soorma_env_data');
    try {
      expect((await renew(g, c.credential)).status).toBe(200);
    } finally {
      await g.owner.query('GRANT SELECT ON registration_secrets TO soorma_env_data');
    }
  });
});

describe('TC-AC-028: revocation is terminal; reinstatement is a new issuance', () => {
  it('the revoked lineage stays refused; a new bootstrap is a new lineage that renews', async () => {
    const c = await credentialFor(g);
    await seedCredentialRevocation(g.owner, ENV, c.cid, g.clock.now());
    expect(problem(await renew(g, c.credential))).toEqual({
      status: 401,
      code: 'credential_refused',
    });
    const fresh = await bootstrap(g, c.agent, c.secret.value);
    expect(fresh.status).toBe(200);
    expect(claims(fresh.body.credential as string).cid).not.toBe(c.cid);
    expect((await renew(g, fresh.body.credential as string)).status).toBe(200);
    expect((await renew(g, c.credential)).status).toBe(401);
  });

  it('an agent revocation refuses every lineage of the agent, at once', async () => {
    const c = await credentialFor(g);
    await seedAgentRevocation(g.owner, ENV, c.agent, g.clock.now());
    expect(problem(await renew(g, c.credential))).toEqual({
      status: 401,
      code: 'credential_refused',
    });
  });
});

describe('TC-AC-031: the credential names E’s configured identity', () => {
  it('env equals E’s three parts; nothing names a host', async () => {
    const c = await credentialFor(g);
    expect(claims(c.credential).env).toEqual({ ...E });
    expect(JSON.stringify(claims(c.credential))).not.toMatch(/soorma\.internal|localhost|127\./);
  });
});

describe('TC-AC-032: an agent without autonomy declared bootstraps and renews', () => {
  it('both 200', async () => {
    const agent = agentId();
    const secret = await registered(g, agent, { autonomy: false });
    const r = await bootstrap(g, agent, secret.value);
    expect(r.status).toBe(200);
    expect((await renew(g, r.body.credential as string)).status).toBe(200);
  });
});

describe('TC-AC-051: concurrent renewals of one lineage all succeed', () => {
  it('both 200; the record keeps the later expiry; two attribution records', async () => {
    const c = await credentialFor(g);
    const [a, b] = await Promise.all([renew(g, c.credential), renew(g, c.credential)]);
    expect([a.status, b.status]).toEqual([200, 200]);
    const later = Math.max(
      claims(a.body.credential as string).exp as number,
      claims(b.body.credential as string).exp as number,
    );
    const [row] = await rows(g, 'agent_credentials', c.agent);
    expect(seconds((row!.expires_at as Date).getTime())).toBe(later);
    const renewals = (await rows(g, 'attribution_records', c.agent)).filter(
      (r) => r.operation === 'renewAgentCredential',
    );
    expect(renewals.length).toBe(2);
  });
});

describe('TC-AC-053: an earlier token of a lineage stays valid until its own expiry', () => {
  it('the first token renews again while unexpired', async () => {
    const c = await credentialFor(g);
    g.clock.advance(5 * MINUTE);
    expect((await renew(g, c.credential)).status).toBe(200);
    g.clock.advance(5 * MINUTE);
    expect((await renew(g, c.credential)).status).toBe(200);
  });
});

describe('renewal takes no body', () => {
  it('a body is malformed_request with pointer ""', async () => {
    const c = await credentialFor(g);
    const r = await request(g.edge, RENEWAL, { credential: c.credential, body: {} });
    expect(problem(r)).toEqual({ status: 400, code: 'malformed_request' });
    expect(r.body.errors).toEqual([
      { pointer: '', detail: 'This operation takes no request body' },
    ]);
  });
});
