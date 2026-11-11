// SPDX-License-Identifier: FSL-1.1-ALv2
//
// S2 fails closed (SECURITY-15): a store it cannot use, an organization level
// that cannot answer, no verify keys, an attribution write that fails; and the
// configured first grant under concurrency.
import { afterAll, beforeAll, describe, expect, it } from 'vitest';
import {
  testEnvDatabase,
  type TestEnvDatabase,
} from '../../../packages/env-store/test/harness/database.ts';
import { connectEnvStore } from '@soorma/env-store';
import {
  adminCredential,
  credentialFor,
  gateway,
  grant,
  MINUTE,
  post,
  problem,
  StubOrgLevel,
  TestClock,
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

describe('TC-EHA-023: a store S2 cannot read is unavailable, never a pass', () => {
  it('start-up fails closed on a store it cannot reach (BR-FG-05)', async () => {
    const down = connectEnvStore({
      host: '127.0.0.1',
      port: 1,
      database: 'x',
      user: 'x',
      password: 'x',
    });
    await expect(gateway(db, { store: down, admin: unique() })).rejects.toThrow();
    await down.close();
  });

  it('a request whose O3 read fails is 503, Retry-After 5, and logs store.unavailable', async () => {
    const c = await adminCredential(g);
    const su = await db.superuser();
    try {
      await su.query('REVOKE SELECT ON credentials FROM soorma_env_app');
      const r = await post(g.edge, '/environment-credentials/current/end', {
        credential: c.credential,
      });
      expect(problem(r)).toEqual({ status: 503, code: 'unavailable', retryAfter: '5' });
      expect(g.log.named('store.unavailable').length).toBeGreaterThan(0);
    } finally {
      await su.query('GRANT SELECT ON credentials TO soorma_env_app');
      await su.end();
    }
  });
});

describe('TC-EHA-043 (at S2), 031: S1 down, and what never calls it', () => {
  it('issuance, renewal, and a grant’s target check are 503 with Retry-After 5; ending succeeds', async () => {
    const c = await adminCredential(g);
    const s = await g.stub.signIn(g.admin);
    g.stub.down = true;
    try {
      expect(
        problem(await post(g.edge, '/environment-credentials', { credential: s.token })),
      ).toEqual({
        status: 503,
        code: 'unavailable',
        retryAfter: '5',
      });
      expect(
        problem(
          await post(g.edge, '/environment-credentials/current/renewal', {
            credential: c.credential,
          }),
        ),
      ).toEqual({
        status: 503,
        code: 'unavailable',
        retryAfter: '5',
      });
      expect(problem(await grant(g, c.credential, unique(), ['agent:register']))).toEqual({
        status: 503,
        code: 'unavailable',
        retryAfter: '5',
      });
      expect(g.log.named('orglevel.unavailable').length).toBeGreaterThanOrEqual(3);
      expect(
        (await post(g.edge, '/environment-credentials/current/end', { credential: c.credential }))
          .status,
      ).toBe(204);
    } finally {
      g.stub.down = false;
    }
  });

  it('ending, O3, and a denied grant make no call to S1', async () => {
    const m = await (async () => {
      const { credential } = await adminCredential(g);
      const p = unique();
      g.stub.principals.add(p);
      await grant(g, credential, p, ['agent:register']);
      return { principal: p, ...(await credentialFor(g, p)) };
    })();
    const calls = g.stub.calls.length;
    expect((await grant(g, m.credential, g.admin, ['agent:register'])).status).toBe(403);
    expect(
      (await post(g.edge, '/environment-credentials/current/end', { credential: m.credential }))
        .status,
    ).toBe(204);
    expect(
      (await post(g.edge, '/environment-credentials/current/end', { credential: m.credential }))
        .status,
    ).toBe(401);
    expect(g.stub.calls.length).toBe(calls);
  });
});

describe('TC-EHA-048: a failed attribution write rolls back its operation; refusals write no record', () => {
  it('grant, issuance, renewal, and ending each leave nothing behind', async () => {
    const fresh = await testEnvDatabase();
    const f = await gateway(fresh);
    const c = await adminCredential(f);
    const target = unique();
    f.stub.principals.add(target);
    const su = await fresh.superuser();
    const count = async (sql: string, params: unknown[]) => {
      const app = await fresh.app();
      try {
        return Number((await app.query<{ n: string }>(sql, params)).rows[0]!.n);
      } finally {
        await app.end();
      }
    };
    try {
      const credentialsBefore = await count('SELECT count(*) AS n FROM credentials', []);
      await su.query('REVOKE INSERT ON attribution_records FROM soorma_env_app');
      expect(problem(await grant(f, c.credential, target, ['agent:register'])).status).toBe(503);
      expect(await count('SELECT count(*) AS n FROM grants WHERE principal = $1', [target])).toBe(
        0,
      );
      const s = await f.stub.signIn(f.admin);
      expect(
        problem(await post(f.edge, '/environment-credentials', { credential: s.token })).status,
      ).toBe(503);
      expect(await count('SELECT count(*) AS n FROM credentials', [])).toBe(credentialsBefore);
      expect(
        problem(
          await post(f.edge, '/environment-credentials/current/end', { credential: c.credential }),
        ).status,
      ).toBe(503);
      expect(await count("SELECT count(*) AS n FROM credentials WHERE state = 'ended'", [])).toBe(
        0,
      );
    } finally {
      await su.query('GRANT INSERT ON attribution_records TO soorma_env_app');
      await su.end();
      await f.close();
      await fresh.drop();
    }
  });

  it('a refused grant writes no attribution record', async () => {
    const app = await db.app();
    try {
      const before = Number(
        (
          await app.query<{ n: string }>(
            "SELECT count(*) AS n FROM attribution_records WHERE operation = 'grantToHuman'",
          )
        ).rows[0]!.n,
      );
      const p = unique();
      g.stub.principals.add(p);
      const m = await credentialFor(g, g.admin);
      await grant(g, m.credential, p, ['tenant:custom']);
      const after = Number(
        (
          await app.query<{ n: string }>(
            "SELECT count(*) AS n FROM attribution_records WHERE operation = 'grantToHuman'",
          )
        ).rows[0]!.n,
      );
      expect(after).toBe(before);
    } finally {
      await app.end();
    }
  });
});

describe('TC-EHA-035, 037: the configured first grant', () => {
  it('two runtimes starting at once on a fresh store write one grant and one record; a restart writes nothing', async () => {
    for (let i = 0; i < 5; i++) {
      const fresh = await testEnvDatabase();
      const admin = unique();
      const clock = new TestClock('2026-11-11T12:00:00Z');
      try {
        const [a, b] = await Promise.all([
          gateway(fresh, { admin, clock }),
          gateway(fresh, { admin, clock }),
        ]);
        const restarted = await gateway(fresh, { admin, clock });
        const app = await fresh.app();
        try {
          const grants = await app.query('SELECT id FROM grants WHERE principal = $1', [admin]);
          expect(grants.rows).toHaveLength(1);
          const records = await app.query(
            "SELECT 1 FROM attribution_records WHERE operation = 'configureFirstGrant'",
          );
          expect(records.rows).toHaveLength(1);
        } finally {
          await app.end();
        }
        await Promise.all([a.close(), b.close(), restarted.close()]);
      } finally {
        await fresh.drop();
      }
    }
  });

  it('start-up fails if the first grant cannot be written (BR-FG-05)', async () => {
    const fresh = await testEnvDatabase();
    const su = await fresh.superuser();
    try {
      await su.query('REVOKE INSERT ON grants FROM soorma_env_app');
      await expect(gateway(fresh)).rejects.toThrow();
      const app = await fresh.app();
      try {
        expect((await app.query('SELECT 1 FROM attribution_records')).rows).toHaveLength(0);
      } finally {
        await app.end();
      }
    } finally {
      await su.end();
      await fresh.drop();
    }
  });
});

describe('TC-EHA-064, 066 (over HTTP): the issuance key flow', () => {
  it('with no verify keys held, issuance fetches once, then is 503 if S1 cannot answer', async () => {
    const clock = new TestClock('2026-11-11T12:00:00Z');
    const stub = new StubOrgLevel(clock);
    const n = await gateway(db, { stub, clock, loadKeys: false, admin: unique() });
    try {
      const s = await stub.signIn(n.admin);
      stub.down = true;
      const r = await post(n.edge, '/environment-credentials', { credential: s.token });
      expect(problem(r)).toEqual({ status: 503, code: 'unavailable', retryAfter: '5' });
      expect(n.log.named('orglevel.unavailable').map((e) => e.code)).toContain('verify_keys');
      stub.down = false;
      clock.advance(31);
      expect((await post(n.edge, '/environment-credentials', { credential: s.token })).status).toBe(
        200,
      );
    } finally {
      await n.close();
    }
  });

  it('a sign-in under a key S2 lacks is accepted after exactly one refetch; one signInStatus call', async () => {
    const clock = new TestClock('2026-11-11T12:00:00Z');
    const stub = new StubOrgLevel(clock);
    const n = await gateway(db, { stub, clock, admin: unique() });
    try {
      clock.advance(31);
      const { organizationRing } = await import('./support.ts');
      stub.ring = organizationRing(); // S1 rotated: S2 does not hold the new key
      const fetches = stub.count('verifyKeys');
      const s = await stub.signIn(n.admin);
      const before = stub.count('signInStatus');
      const r = await post(n.edge, '/environment-credentials', { credential: s.token });
      expect(r.status).toBe(200);
      expect(stub.count('verifyKeys') - fetches).toBe(1);
      expect(stub.count('signInStatus') - before).toBe(1);
    } finally {
      await n.close();
    }
  });

  it('TC-EHA-057 (a) over HTTP: a never-renewed sign-in 29 s past its expiry is credential_refused', async () => {
    const clock = new TestClock('2026-11-11T12:00:00Z');
    const stub = new StubOrgLevel(clock);
    const n = await gateway(db, { stub, clock, admin: unique() });
    try {
      const s = await stub.signIn(n.admin, { expiresAt: new Date(clock.now().getTime() + MINUTE) });
      clock.advance(60 + 29);
      expect(
        problem(await post(n.edge, '/environment-credentials', { credential: s.token })),
      ).toEqual({
        status: 401,
        code: 'credential_refused',
      });
      clock.advance(2);
      expect(
        problem(await post(n.edge, '/environment-credentials', { credential: s.token })),
      ).toEqual({
        status: 401,
        code: 'credential_expired',
      });
    } finally {
      await n.close();
    }
  });
});
