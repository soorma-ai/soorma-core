// SPDX-License-Identifier: FSL-1.1-ALv2
//
// P4 over a real environment store, as the app role.
import { newRecordId, withTransaction } from '@soorma/env-store';
import { HUMAN_ONLY_PERMISSIONS } from '@soorma/authority';
import { createPolicyDecision } from '@soorma/policy-decision';
import { afterAll, beforeAll, describe, expect, it } from 'vitest';
import {
  ACCEPTED_PERMISSIONS,
  applyFirstGrant,
  createGrant,
  createHumanGrantSource,
  isAcceptedIdentifier,
  unacceptedPositions,
} from '../src/index.ts';
import { testEnvDatabase, type TestEnvDatabase } from '../../env-store/test/harness/database.ts';

const E = { organization: 'o1', project: 'p1', environment: 'e' };
const E2 = { organization: 'o1', project: 'p1', environment: 'e2' };
const now = new Date('2026-11-11T12:00:00Z');
let n = 0;
const someone = (): string => `p${n++}-${Date.now()}@example.com`;

let db: TestEnvDatabase;
beforeAll(async () => {
  db = await testEnvDatabase();
});
afterAll(async () => {
  await db?.drop();
});

const grant = (principal: string, permissions: string[], by = 'admin@example.com') =>
  withTransaction(db.store, (tx) =>
    createGrant(tx, {
      id: newRecordId(),
      environment: E,
      principal,
      permissions,
      grantedBy: { principal: by, credential: 'c1' },
      grantedAt: now,
    }),
  );

describe('TC-EHA-013 (the accepted set): exactly the nine plane-declared identifiers (BR-ACC-01)', () => {
  it('accepts the nine, the human-only three among them, and nothing else', () => {
    expect([...ACCEPTED_PERMISSIONS].sort()).toEqual(
      [
        'agent:delegate',
        'agent:register',
        'agent:retire',
        'attribution:read',
        'credential:revoke',
        'event:publish',
        'event:subscribe',
        'grant:human',
        'human:manage',
      ].sort(),
    );
    for (const p of HUMAN_ONLY_PERMISSIONS) expect(isAcceptedIdentifier(p), p).toBe(true);
    expect(isAcceptedIdentifier('tenant:custom')).toBe(false);
    expect(isAcceptedIdentifier('Agent:register')).toBe(false);
  });
});

describe('TC-EHA-038: unknown_permission reports at most 10 positions, in order', () => {
  it('lists the first 10 unaccepted positions', () => {
    const list = [
      'agent:register',
      ...Array.from({ length: 12 }, (_, i) => `x:p${i}`),
      'grant:human',
    ];
    expect(unacceptedPositions(list)).toEqual([1, 2, 3, 4, 5, 6, 7, 8, 9, 10]);
    expect(unacceptedPositions(['agent:register'])).toEqual([]);
  });
});

describe('TC-EHA-005, 006, 076: a grant is one record; the held set is the union, read uncached', () => {
  it('records a self-grant, and another grant as not self (BR-GR-05)', async () => {
    const admin = someone();
    const self = await grant(admin, ['event:publish', 'agent:register', 'agent:register'], admin);
    expect(self.selfGrant).toBe(true);
    expect(self.permissions).toEqual(['agent:register', 'event:publish']);
    const other = await grant(someone(), ['agent:register'], admin);
    expect(other.selfGrant).toBe(false);
  });

  it('the held set is the union of two overlapping grants, visible at once (TC-EHA-027, 076)', async () => {
    const j = someone();
    const source = createHumanGrantSource(db.store);
    await grant(j, ['agent:register']);
    expect([...(await source.grantsOf({ kind: 'human', principal: j }, E))]).toEqual([
      'agent:register',
    ]);
    await grant(j, ['agent:register', 'human:manage']);
    expect([...(await source.grantsOf({ kind: 'human', principal: j }, E))].sort()).toEqual([
      'agent:register',
      'human:manage',
    ]);
  });

  it('feeds P11, so a human with no grant holds nothing (deny by default)', async () => {
    const policy = createPolicyDecision({
      environment: E,
      grants: createHumanGrantSource(db.store),
    });
    const set = await policy.grantedSet({ kind: 'human', principal: someone() }, E);
    expect(set.size).toBe(0);
  });

  it('an agent principal holds nothing through the human source (BR-EV-05)', async () => {
    const source = createHumanGrantSource(db.store);
    expect([...(await source.grantsOf({ kind: 'agent', agent: 'a' }, E))]).toEqual([]);
  });
});

describe('TC-EHA-040 (P4): every read constrains on the environment (D-EHA-29)', () => {
  it("a grant row under E2's identity in E's store is not in the held set", async () => {
    const j = someone();
    const app = await db.app();
    try {
      await app.query(
        `INSERT INTO grants (id, organization, project, environment, principal, permissions,
           granted_by_kind, self_grant, granted_at)
         VALUES ($1, $2, $3, $4, $5, ARRAY['grant:human'], 'configuration', false, $6)`,
        [newRecordId(), E2.organization, E2.project, E2.environment, j, now],
      );
    } finally {
      await app.end();
    }
    const source = createHumanGrantSource(db.store);
    expect([...(await source.grantsOf({ kind: 'human', principal: j }, E))]).toEqual([]);
    expect([...(await source.grantsOf({ kind: 'human', principal: j }, E2))]).toEqual([
      'grant:human',
    ]);
  });
});

describe('TC-EHA-035 (P4): the configured first grant is written once', () => {
  const first = (principal: string) =>
    withTransaction(db.store, (tx) =>
      applyFirstGrant(tx, {
        id: newRecordId(),
        environment: E,
        principal,
        permissions: ['human:manage', 'grant:human'],
        grantedAt: now,
      }),
    );

  it('the first call writes it; a second writes nothing', async () => {
    const h = someone();
    const a = await first(h);
    expect(a?.permissions).toEqual(['grant:human', 'human:manage']);
    expect(a?.grantedBy).toEqual({ kind: 'configuration' });
    expect(await first(h)).toBeUndefined();
  });

  it('twenty concurrent calls write exactly one', async () => {
    const h = someone();
    const results = await Promise.all(Array.from({ length: 20 }, () => first(h)));
    expect(results.filter((r) => r !== undefined)).toHaveLength(1);
    const app = await db.app();
    try {
      const { rows } = await app.query<{ n: string }>(
        `SELECT count(*) AS n FROM grants WHERE principal = $1 AND granted_by_kind = 'configuration'`,
        [h],
      );
      expect(rows[0]!.n).toBe('1');
    } finally {
      await app.end();
    }
  });
});
