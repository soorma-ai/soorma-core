// SPDX-License-Identifier: FSL-1.1-ALv2
//
// S2's registerAgent and issueRegistrationSecret (U5 agent-registration),
// in process over a test environment store and a stub organization level:
// every request is a raw HTTP request to S2, with no client library.
import { recordAttribution } from '@soorma/attribution';
import { newRecordId, withTransaction } from '@soorma/env-store';
import { digestRegistrationSecret, parseRegistrationSecret } from '@soorma/registry';
import { asSecretText, Semaphore, type Timers } from '@soorma/service-kit';
import { afterAll, beforeAll, describe, expect, it } from 'vitest';
import {
  testEnvDatabase,
  type TestEnvDatabase,
} from '../../../packages/env-store/test/harness/database.ts';
import { agentId, H_HELD, issueSecret, register, sponsor } from './registration-support.ts';
import {
  credentialFor,
  E2,
  gateway,
  grant,
  member,
  post,
  problem,
  unique,
  type Gateway,
  type Response,
} from './support.ts';

let db: TestEnvDatabase;
let g: Gateway;
let h: { principal: string; credential: string };
beforeAll(async () => {
  db = await testEnvDatabase();
  g = await gateway(db);
  h = await sponsor(g);
});
afterAll(async () => {
  await g?.close();
  await db?.drop();
});

const pointers = (r: Response): unknown =>
  (r.body as { errors?: { pointer?: string }[] }).errors?.map((e) => e.pointer);

async function rows<T>(sql: string, params: unknown[] = []): Promise<T[]> {
  const su = await db.superuser();
  try {
    return (await su.query(sql, params)).rows as T[];
  } finally {
    await su.end();
  }
}

const registrationRow = async (agent: string) =>
  (
    await rows<Record<string, unknown>>(
      `SELECT * FROM registrations WHERE environment = 'e' AND agent = $1`,
      [agent],
    )
  )[0];

describe('TC-AR-001, 002, 008: a registration with all eight attributes, sponsored by H', () => {
  it('200, every attribute in the response and the row; the snapshot is H held set', async () => {
    const a = agentId();
    const r = await register(g, h.credential, {
      agent: a,
      standingPermissions: ['event:publish'],
      reBroadeningDeclaration: [],
      autonomyDeclared: true,
    });
    expect(r.status).toBe(200);
    expect(r.body).toEqual({
      agent: a,
      environment: { organization: 'o1', project: 'p1', environment: 'e' },
      sponsor: { organization: 'o1', principal: h.principal },
      ceilingSnapshot: [...H_HELD],
      standingPermissions: ['event:publish'],
      reBroadeningDeclaration: [],
      autonomyDeclared: true,
      registeredAt: g.clock.now().toISOString(),
      state: 'registered',
    });
    const row = await registrationRow(a);
    expect(row).toMatchObject({
      sponsor: h.principal,
      ceiling_snapshot: [...H_HELD],
      standing_permissions: ['event:publish'],
      re_broadening_declaration: [],
      autonomy_declared: true,
      state: 'registered',
    });
  });

  it('two agents, each with its own sponsor reference and snapshot', async () => {
    const a = agentId();
    const b = agentId();
    const ra = await register(g, h.credential, {
      agent: a,
      standingPermissions: ['event:publish'],
      autonomyDeclared: true,
    });
    const rb = await register(g, h.credential, {
      agent: b,
      standingPermissions: ['event:subscribe'],
      autonomyDeclared: true,
    });
    expect([ra.status, rb.status]).toEqual([200, 200]);
    expect(ra.body.sponsor).toEqual(rb.body.sponsor);
    expect((await registrationRow(a))?.standing_permissions).toEqual(['event:publish']);
    expect((await registrationRow(b))?.standing_permissions).toEqual(['event:subscribe']);
  });
});

describe('TC-AR-003, 004, 005, 018: defaults, the declaration, and the ceiling boundary', () => {
  it('autonomy declared defaults to false', async () => {
    const r = await register(g, h.credential, {
      agent: agentId(),
      standingPermissions: ['event:publish'],
    });
    expect(r.body.autonomyDeclared).toBe(false);
  });

  it('a declaration within the standing set is recorded; empty and omitted are empty', async () => {
    const r = await register(g, h.credential, {
      agent: agentId(),
      standingPermissions: ['event:subscribe', 'event:publish'],
      reBroadeningDeclaration: ['event:subscribe'],
    });
    expect(r.status).toBe(200);
    expect(r.body.standingPermissions).toEqual(['event:publish', 'event:subscribe']);
    expect(r.body.reBroadeningDeclaration).toEqual(['event:subscribe']);
    for (const body of [{ reBroadeningDeclaration: [] }, {}]) {
      const e = await register(g, h.credential, {
        agent: agentId(),
        standingPermissions: ['event:publish'],
        ...body,
      });
      expect(e.body.reBroadeningDeclaration).toEqual([]);
    }
  });

  it('a standing set equal to the non-human-only held set, and an empty one, are accepted', async () => {
    const full = await register(g, h.credential, {
      agent: agentId(),
      standingPermissions: ['agent:register', 'event:publish', 'event:subscribe'],
    });
    expect(full.status).toBe(200);
    expect(full.body.ceilingSnapshot).toEqual([...H_HELD]);
    const empty = await register(g, h.credential, { agent: agentId(), standingPermissions: [] });
    expect(empty.status).toBe(200);
  });
});

describe('TC-AR-009, 029: the sponsor ceiling', () => {
  it('exceeds_sponsor_ceiling (403), pointing at each standing entry not held; nothing written', async () => {
    const a = agentId();
    const r = await register(g, h.credential, {
      agent: a,
      standingPermissions: ['event:publish', 'agent:retire', 'credential:revoke'],
    });
    expect(problem(r)).toEqual({ status: 403, code: 'exceeds_sponsor_ceiling' });
    expect(pointers(r)).toEqual(['/standingPermissions/1', '/standingPermissions/2']);
    expect(r.headers['www-authenticate']).toBeUndefined();
    expect(await registrationRow(a)).toBeUndefined();
    expect(g.log.named('registration.refused').at(-1)?.code).toBe('ceiling_exceeded');
  });
});

describe('TC-AR-010, 011, 012, 013, 030, 035: the request sets, decided at step 6', () => {
  it.each([
    [['grant:human'], ['/standingPermissions/0']],
    [['human:manage'], ['/standingPermissions/0']],
    [['agent:delegate'], ['/standingPermissions/0']],
    [
      ['grant:human', 'event:publish', 'agent:delegate'],
      ['/standingPermissions/0', '/standingPermissions/2'],
    ],
  ])('human_only_permission for %j, whatever H holds', async (standing, expected) => {
    const r = await register(g, h.credential, { agent: agentId(), standingPermissions: standing });
    expect(problem(r)).toEqual({ status: 400, code: 'human_only_permission' });
    expect(pointers(r)).toEqual(expected);
  });

  it('declaration_outside_standing, pointing at each declared entry outside', async () => {
    const r = await register(g, h.credential, {
      agent: agentId(),
      standingPermissions: ['event:publish'],
      reBroadeningDeclaration: ['event:subscribe'],
    });
    expect(problem(r)).toEqual({ status: 400, code: 'declaration_outside_standing' });
    expect(pointers(r)).toEqual(['/reBroadeningDeclaration/0']);
  });

  it('unknown_permission in either set, before the human-only class', async () => {
    const standing = await register(g, h.credential, {
      agent: agentId(),
      standingPermissions: ['invoice:approve'],
    });
    expect(problem(standing)).toEqual({ status: 400, code: 'unknown_permission' });
    expect(pointers(standing)).toEqual(['/standingPermissions/0']);
    const both = await register(g, h.credential, {
      agent: agentId(),
      standingPermissions: ['grant:human', 'billing:approve'],
      reBroadeningDeclaration: ['invoice:approve'],
    });
    expect(problem(both).code).toBe('unknown_permission');
    expect(pointers(both)).toEqual(['/reBroadeningDeclaration/0', '/standingPermissions/1']);
  });

  it('a caller without agent:register gets the step-6 codes, which disclose no state', async () => {
    const d = await member(g, ['event:publish']);
    const r = await register(g, d.credential, {
      agent: agentId(),
      standingPermissions: ['grant:human'],
    });
    expect(problem(r).code).toBe('human_only_permission');
  });
});

describe('TC-AR-014, 015, 016: authority and the presenter', () => {
  it('registration and issuance without agent:register are forbidden', async () => {
    const d = await member(g, ['event:publish']);
    const a = agentId();
    expect(problem(await register(g, d.credential, { agent: a, standingPermissions: [] }))).toEqual(
      { status: 403, code: 'forbidden' },
    );
    expect(await registrationRow(a)).toBeUndefined();
    const own = agentId();
    await register(g, h.credential, { agent: own, standingPermissions: [] });
    expect(problem(await issueSecret(g, d.credential, own))).toEqual({
      status: 403,
      code: 'forbidden',
    });
  });

  it('an agent credential is refused by kind, without verifying, on both operations', async () => {
    const forged = 'soorma_ac_' + 'A'.repeat(40);
    const a = agentId();
    const r1 = await register(g, forged, { agent: a, standingPermissions: [] });
    const r2 = await issueSecret(g, forged, a);
    for (const r of [r1, r2]) {
      expect(problem(r)).toEqual({ status: 401, code: 'credential_refused' });
      expect(r.headers['www-authenticate']).toBe('Bearer');
    }
    expect(await registrationRow(a)).toBeUndefined();
  });
});

describe('TC-AR-006, 017, 020, 036: secret issuance, returned once', () => {
  it('200 with the value once, not cacheable; the row holds the digest only', async () => {
    const a = agentId();
    await register(g, h.credential, { agent: a, standingPermissions: ['event:publish'] });
    const r = await issueSecret(g, h.credential, a);
    expect(r.status).toBe(200);
    expect(r.headers['cache-control']).toBe('no-store');
    expect(Object.keys(r.body as object).sort()).toEqual([
      'id',
      'issuedAt',
      'registration',
      'secret',
    ]);
    expect(r.body.registration).toBe(a);
    const value = r.body.secret as string;
    expect(value).toMatch(/^soorma_rs_[A-Za-z0-9_-]{22}\.[A-Za-z0-9_-]{43}$/);
    expect(value.slice(10, 32)).toBe(r.body.id);
    const parsed = parseRegistrationSecret(asSecretText(value));
    if (parsed.kind !== 'parsed') throw new Error('unparsed');
    const [row] = await rows<Record<string, unknown>>(
      `SELECT * FROM registration_secrets WHERE id = $1`,
      [r.body.id],
    );
    expect(row).toMatchObject({ registration: a, issuer: h.principal, state: 'active' });
    expect(row!.digest).toEqual(digestRegistrationSecret(parsed.secretBytes));
    const secretPart = value.split('.')[1]!;
    for (const v of Object.values(row!))
      if (typeof v === 'string') {
        expect(v).not.toContain(secretPart);
        expect(v).not.toContain(value);
      }
  });

  it('no log line or attribution record carries the value, its secret part, or its digest', async () => {
    const a = agentId();
    await register(g, h.credential, { agent: a, standingPermissions: [] });
    const before = g.log.lines.length;
    const r = await issueSecret(g, h.credential, a);
    await issueSecret(g, h.credential, agentId());
    const value = r.body.secret as string;
    const parsed = parseRegistrationSecret(asSecretText(value));
    if (parsed.kind !== 'parsed') throw new Error('unparsed');
    const digest = digestRegistrationSecret(parsed.secretBytes);
    const forbidden = [
      value,
      value.split('.')[1]!,
      digest.toString('hex'),
      digest.toString('base64'),
      digest.toString('base64url'),
    ];
    const lines = g.log.lines.slice(before).join('\n');
    const records = JSON.stringify(
      await rows(`SELECT * FROM attribution_records WHERE target_id = $1`, [a]),
    );
    for (const f of forbidden) {
      expect(lines).not.toContain(f);
      expect(records).not.toContain(f);
    }
  });

  it('an unknown registration is unknown_registration (400), pointing at /registration', async () => {
    const r = await issueSecret(g, h.credential, agentId());
    expect(problem(r)).toEqual({ status: 400, code: 'unknown_registration' });
    expect(pointers(r)).toEqual(['/registration']);
  });
});

describe('TC-AR-007, 040: attribution, and the sponsor recoverable from the records alone', () => {
  it('each operation is attributed to H with the credential, scope E, no chain or origin', async () => {
    const a = agentId();
    await register(g, h.credential, { agent: a, standingPermissions: [] });
    await issueSecret(g, h.credential, a);
    const records = await rows<Record<string, unknown>>(
      `SELECT * FROM attribution_records WHERE target_id = $1 ORDER BY operation`,
      [a],
    );
    expect(records.map((r) => r.operation)).toEqual(['issueRegistrationSecret', 'registerAgent']);
    for (const r of records)
      expect(r).toMatchObject({
        organization: 'o1',
        project: 'p1',
        environment: 'e',
        actor_kind: 'human',
        principal: h.principal,
        credential_kind: 'environmentCredential',
        target_kind: 'registration',
        target_id: a,
        chain: null,
        origin: null,
        rebroadening_load_bearing: null,
      });
    for (const r of records) expect(r.credential_id).toEqual(expect.any(String));
  });

  it("an agent's record resolves its sponsor through the registration, in two hops", async () => {
    const a = agentId();
    await register(g, h.credential, { agent: a, standingPermissions: ['event:publish'] });
    const id = newRecordId();
    await withTransaction(db.store, (tx) =>
      recordAttribution(tx, {
        id,
        recordedAt: g.clock.now(),
        environment: { organization: 'o1', project: 'p1', environment: 'e' },
        operation: 'constructedAgentOperation',
        actor: { kind: 'agent', registration: a, instance: 'i1', sponsor: h.principal },
      }),
    );
    const [record] = await rows<{ registration: string; sponsor: string; environment: string }>(
      `SELECT registration, sponsor, environment FROM attribution_records WHERE id = $1`,
      [id],
    );
    const registration = await registrationRow(record!.registration);
    expect(record!.environment).toBe('e');
    expect(registration?.sponsor).toBe(h.principal);
    expect(registration?.sponsor).toBe(record!.sponsor);
  });
});

describe('TC-AR-019, 037: the snapshot is fixed; a self-grant counts at once', () => {
  it('a later grant to H leaves an earlier snapshot unchanged, and enters a later one', async () => {
    const fresh = await testEnvDatabase();
    const f = await gateway(fresh);
    try {
      const fh = await sponsor(f);
      const a = agentId();
      await register(f, fh.credential, { agent: a, standingPermissions: [] });
      expect((await grant(f, fh.credential, f.admin, ['attribution:read'])).status).toBe(200);
      const b = await register(f, fh.credential, { agent: agentId(), standingPermissions: [] });
      const su = await fresh.superuser();
      try {
        const { rows: r } = await su.query(
          `SELECT ceiling_snapshot FROM registrations WHERE agent = $1`,
          [a],
        );
        expect(r[0].ceiling_snapshot).toEqual([...H_HELD]);
      } finally {
        await su.end();
      }
      expect(b.body.ceilingSnapshot).toEqual([...H_HELD, 'attribution:read'].sort());
    } finally {
      await f.close();
      await fresh.drop();
    }
  });

  it('H2 is forbidden, self-grants agent:register, and registers on the next request', async () => {
    const h2 = await member(g, ['grant:human', 'event:publish']);
    expect(
      problem(await register(g, h2.credential, { agent: agentId(), standingPermissions: [] })),
    ).toEqual({ status: 403, code: 'forbidden' });
    expect((await grant(g, h2.credential, h2.principal, ['agent:register'])).status).toBe(200);
    const r = await register(g, h2.credential, {
      agent: agentId(),
      standingPermissions: ['event:publish'],
    });
    expect(r.status).toBe(200);
    expect(r.body.ceilingSnapshot).toContain('agent:register');
  });
});

describe('TC-AR-023, 025, 026: identifiers and the sponsor', () => {
  it('a taken identifier is registration_exists (409), only after authority and the ceiling', async () => {
    const a = agentId();
    expect(
      (await register(g, h.credential, { agent: a, standingPermissions: ['event:publish'] }))
        .status,
    ).toBe(200);
    const again = await register(g, h.credential, {
      agent: a,
      standingPermissions: ['event:publish'],
    });
    expect(problem(again)).toEqual({ status: 409, code: 'registration_exists' });
    expect(pointers(again)).toEqual(['/agent']);
    const d = await member(g, ['event:publish']);
    expect(problem(await register(g, d.credential, { agent: a, standingPermissions: [] }))).toEqual(
      { status: 403, code: 'forbidden' },
    );
    expect(
      problem(await register(g, h.credential, { agent: a, standingPermissions: ['agent:retire'] }))
        .code,
    ).toBe('exceeds_sponsor_ceiling');
    const records = await rows(
      `SELECT 1 FROM attribution_records WHERE operation = 'registerAgent' AND target_id = $1`,
      [a],
    );
    expect(records).toHaveLength(1);
  });

  it('the same identifier in E and E2 is two registrations', async () => {
    const e2 = await gateway(db, { environment: E2 });
    try {
      const h2 = await sponsor(e2);
      const a = agentId();
      expect(
        (await register(g, h.credential, { agent: a, standingPermissions: ['event:publish'] }))
          .status,
      ).toBe(200);
      const r = await register(e2, h2.credential, {
        agent: a,
        standingPermissions: ['event:subscribe'],
      });
      expect(r.status).toBe(200);
      expect(r.body.environment.environment).toBe('e2');
      expect(problem(await issueSecret(e2, h2.credential, agentId())).code).toBe(
        'unknown_registration',
      );
    } finally {
      await e2.close();
    }
  });

  it('a body naming a sponsor is malformed_request, pointing at /sponsor', async () => {
    const r = await register(g, h.credential, {
      agent: agentId(),
      standingPermissions: [],
      sponsor: { organization: 'o1', principal: unique() },
    });
    expect(problem(r)).toEqual({ status: 400, code: 'malformed_request' });
    expect(pointers(r)).toEqual(['/sponsor']);
  });
});

describe('TC-AR-033, 034: who may issue a secret (D-AR-01), and several active secrets', () => {
  it('the sponsor and an Admin holding agent:register issue; others are forbidden', async () => {
    const d = await member(g, ['agent:register', 'event:publish']);
    const a2 = await member(g, ['agent:register', 'grant:human', 'human:manage']);
    const m = await member(g, ['grant:human', 'human:manage']);
    const d1 = agentId();
    expect(
      (await register(g, d.credential, { agent: d1, standingPermissions: ['event:publish'] }))
        .status,
    ).toBe(200);
    const hs = agentId();
    await register(g, h.credential, { agent: hs, standingPermissions: [] });
    expect((await issueSecret(g, d.credential, d1)).status).toBe(200);
    expect(problem(await issueSecret(g, d.credential, hs))).toEqual({
      status: 403,
      code: 'forbidden',
    });
    expect(g.log.named('secret.refused').at(-1)?.code).toBe('not_sponsor_or_admin');
    expect((await issueSecret(g, a2.credential, d1)).status).toBe(200);
    expect(problem(await issueSecret(g, m.credential, d1))).toEqual({
      status: 403,
      code: 'forbidden',
    });
    expect(g.log.named('secret.refused').at(-1)?.code).toBe('authority_denied');
    expect((await issueSecret(g, h.credential, d1)).status).toBe(200);
    const issuers = await rows<{ issuer: string }>(
      `SELECT issuer FROM registration_secrets WHERE registration = $1 AND state = 'active'`,
      [d1],
    );
    expect(issuers.map((r) => r.issuer).sort()).toEqual(
      [d.principal, a2.principal, h.principal].sort(),
    );
  });
});

describe('TC-AR-051: at most 10 active secrets, shown only to a permitted caller', () => {
  it('the 10th is issued, the 11th is secret_limit_reached (409), a non-permitted caller forbidden', async () => {
    const c = agentId();
    await register(g, h.credential, { agent: c, standingPermissions: [] });
    for (let i = 0; i < 10; i += 1)
      expect((await issueSecret(g, h.credential, c)).status).toBe(200);
    const eleventh = await issueSecret(g, h.credential, c);
    expect(problem(eleventh)).toEqual({ status: 409, code: 'secret_limit_reached' });
    expect((eleventh.body as { errors?: unknown }).errors).toBeUndefined();
    const d = await member(g, ['agent:register']);
    expect(problem(await issueSecret(g, d.credential, c))).toEqual({
      status: 403,
      code: 'forbidden',
    });
  });
});

describe('TC-AR-021, 041, 054: failures write nothing; success only after commit', () => {
  it('an unreadable held set is unavailable (503, Retry-After), nothing written', async () => {
    const su = await db.superuser();
    const a = agentId();
    try {
      await su.query('REVOKE SELECT ON grants FROM soorma_env_app');
      const r = await register(g, h.credential, { agent: a, standingPermissions: [] });
      expect(problem(r)).toEqual({ status: 503, code: 'unavailable', retryAfter: '5' });
      expect(g.log.named('registration.refused').at(-1)?.code).toBe('held_set_unreadable');
    } finally {
      await su.query('GRANT SELECT ON grants TO soorma_env_app');
      await su.end();
    }
    expect(await registrationRow(a)).toBeUndefined();
  });

  it('a failed attribution write leaves no registration and no secret', async () => {
    const a = agentId();
    await register(g, h.credential, { agent: a, standingPermissions: [] });
    const b = agentId();
    const su = await db.superuser();
    try {
      await su.query('REVOKE INSERT ON attribution_records FROM soorma_env_app');
      expect(
        problem(await register(g, h.credential, { agent: b, standingPermissions: [] })).status,
      ).toBe(503);
      expect(problem(await issueSecret(g, h.credential, a)).status).toBe(503);
    } finally {
      await su.query('GRANT INSERT ON attribution_records TO soorma_env_app');
      await su.end();
    }
    expect(await registrationRow(b)).toBeUndefined();
    expect(await rows(`SELECT 1 FROM registration_secrets WHERE registration = $1`, [a])).toEqual(
      [],
    );
  });

  it('a 200 is sent only after the commit: the row is visible to another connection at once', async () => {
    const a = agentId();
    const r = await register(g, h.credential, { agent: a, standingPermissions: [] });
    expect(r.status).toBe(200);
    const app = await db.app();
    try {
      const { rows: seen } = await app.query(`SELECT agent FROM registrations WHERE agent = $1`, [
        a,
      ]);
      expect(seen).toHaveLength(1);
    } finally {
      await app.end();
    }
  });
});

describe('TC-AR-042, 043: wrong presenters, and every rejection by raw request', () => {
  it("E2's credential, a sign-in, the delegation header, and a forged credential are refused", async () => {
    const e2 = await gateway(db, { environment: E2 });
    const other = await gateway(db);
    try {
      const atE2 = await credentialFor(e2, e2.admin);
      const s = await g.stub.signIn(g.admin);
      const forged = await credentialFor(other, other.admin);
      const a = agentId();
      const body = { agent: a, standingPermissions: [] };
      for (const credential of [atE2.credential, s.token, forged.credential])
        for (const url of ['/registrations', '/registration-secrets'])
          expect(
            problem(await post(g.edge, url, { credential, body: { ...body, registration: a } })),
            url,
          ).toEqual({ status: 401, code: 'credential_refused' });
      const delegated = await post(g.edge, '/registrations', {
        credential: h.credential,
        body,
        headers: { 'soorma-delegation': 'soorma_dc_x' },
      });
      expect(problem(delegated)).toEqual({ status: 401, code: 'credential_refused' });
      expect(await registrationRow(a)).toBeUndefined();
    } finally {
      await e2.close();
      await other.close();
    }
  });
});

describe('TC-AR-022, 063: the schema, and the body bound', () => {
  it('a body failing the schema is malformed_request before authority', async () => {
    const r = await register(g, h.credential, { agent: '-bad' });
    expect(problem(r)).toEqual({ status: 400, code: 'malformed_request' });
    const s = await issueSecret(g, h.credential, '');
    expect(problem(s).code).toBe('malformed_request');
  });

  it('a maximal registration body is judged by the rules; 16 KiB + 1 byte is payload_too_large', async () => {
    const ids = (n: number, k: string) =>
      Array.from({ length: n }, (_, i) => `x:${k}${String(i).padStart(2, '0')}${'p'.repeat(118)}`);
    const maximal = {
      agent: 'a'.repeat(64),
      standingPermissions: ids(32, 's'),
      reBroadeningDeclaration: ids(32, 'd'),
      autonomyDeclared: true,
    };
    expect(JSON.stringify(maximal).length).toBeLessThan(16 * 1024);
    expect(problem(await register(g, h.credential, maximal)).code).toBe('unknown_permission');
    const tooLarge = '{"agent":"a","standingPermissions":[],"x":"' + 'p'.repeat(16 * 1024) + '"}';
    expect(problem(await register(g, h.credential, tooLarge as never)).status).toBe(413);
  });
});

class ManualTimers implements Timers {
  private readonly pending = new Map<number, () => void>();
  private next = 1;
  set(callback: () => void): unknown {
    const handle = this.next++;
    this.pending.set(handle, callback);
    return handle;
  }
  clear(handle: unknown): void {
    this.pending.delete(handle as number);
  }
  fire(): void {
    const due = [...this.pending.values()];
    this.pending.clear();
    for (const callback of due) callback();
  }
}

describe('TC-AR-062: S2 throttle covers both operations', () => {
  it('with every permit held, a registration and an issuance wait, then 503 with Retry-After 5', async () => {
    const timers = new ManualTimers();
    const permits = new Semaphore({
      permits: 1,
      waitMs: 1000,
      reason: 'requests',
      retryAfterSeconds: 5,
      timers,
    });
    const t = await gateway(db, { requests: permits });
    try {
      const th = await sponsor(t);
      const release = await permits.acquire();
      const pending = [
        register(t, th.credential, { agent: agentId(), standingPermissions: [] }),
        issueSecret(t, th.credential, agentId()),
      ];
      for (let i = 0; i < 400 && permits.waiting < 2; i += 1)
        await new Promise((r) => setTimeout(r, 5));
      expect(permits.waiting).toBe(2);
      timers.fire();
      for (const r of await Promise.all(pending))
        expect(problem(r)).toEqual({ status: 503, code: 'unavailable', retryAfter: '5' });
      release();
    } finally {
      await t.close();
    }
  });
});

describe('TC-AR-066, 069: events, and the clock', () => {
  it('each operation emits its event, a human only as an hp_ pseudonym', async () => {
    const a = agentId();
    await register(g, h.credential, { agent: a, standingPermissions: [] });
    await issueSecret(g, h.credential, a);
    for (const event of ['registration.created', 'secret.issued', 'registration.refused'])
      expect(g.log.named(event).length, event).toBeGreaterThan(0);
    for (const e of g.log.events())
      if ('pseudonym' in e) expect(e.pseudonym).toMatch(/^hp_[A-Za-z0-9_-]{22}$/);
    expect(g.log.lines.join('\n')).not.toMatch(/@example\.com/);
  });

  it('registeredAt and issuedAt come from the injected clock', async () => {
    const a = agentId();
    const r = await register(g, h.credential, { agent: a, standingPermissions: [] });
    const s = await issueSecret(g, h.credential, a);
    expect(r.body.registeredAt).toBe(g.clock.now().toISOString());
    expect(s.body.issuedAt).toBe(g.clock.now().toISOString());
  });
});
