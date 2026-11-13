// SPDX-License-Identifier: FSL-1.1-ALv2
//
// P7 over a real environment store: each actor kind recoverable from its row
// alone (TC-EHA-046), and the writer refusing an inconsistent record before
// any SQL (TC-EHA-047, the writer half).
import { newRecordId, withTransaction } from '@soorma/env-store';
import { afterAll, beforeAll, describe, expect, it } from 'vitest';
import {
  AttributionRecordError,
  recordAttribution,
  type Actor,
  type AttributionRecord,
} from '../src/index.ts';
import { testEnvDatabase, type TestEnvDatabase } from '../../env-store/test/harness/database.ts';

const E = { organization: 'o1', project: 'p1', environment: 'e' };
const at = new Date('2026-11-11T12:00:00Z');

let db: TestEnvDatabase;
beforeAll(async () => {
  db = await testEnvDatabase();
});
afterAll(async () => {
  await db?.drop();
});

const base = (actor: Actor, over: Partial<AttributionRecord> = {}): AttributionRecord => ({
  id: newRecordId(),
  recordedAt: at,
  requestId: 'r1',
  environment: E,
  operation: 'grantToHuman',
  actor,
  ...over,
});

async function row(id: string): Promise<Record<string, unknown>> {
  const c = await db.app();
  try {
    const { rows } = await c.query('SELECT * FROM attribution_records WHERE id = $1', [id]);
    return rows[0] as Record<string, unknown>;
  } finally {
    await c.end();
  }
}

const human: Actor = {
  kind: 'human',
  principal: 'h@example.com',
  credential: { kind: 'environmentCredential', id: 'c1' },
};
const agent: Actor = {
  kind: 'agent',
  registration: 'reg-b',
  instance: 'inst-b',
  sponsor: 'h@example.com',
  credential: { kind: 'agentCredential', id: 'ac1' },
};

describe('TC-EHA-046: each actor kind is recoverable from its attribution record alone (BR-AT-07)', () => {
  it('a human record: scope, actor, credential, target, self-grant; no chain or origin', async () => {
    const r = base(human, { target: { kind: 'grant', id: 'g1' }, selfGrant: true });
    await withTransaction(db.store, (tx) => recordAttribution(tx, r));
    expect(await row(r.id)).toMatchObject({
      organization: 'o1',
      project: 'p1',
      environment: 'e',
      operation: 'grantToHuman',
      actor_kind: 'human',
      principal: 'h@example.com',
      credential_kind: 'environmentCredential',
      credential_id: 'c1',
      target_kind: 'grant',
      target_id: 'g1',
      self_grant: true,
      chain: null,
      origin: null,
      rebroadening_load_bearing: null,
      sponsor: null,
    });
  });

  it('a configuration record: no request, principal, or credential', async () => {
    const r = base(
      { kind: 'configuration' },
      { operation: 'configureFirstGrant', requestId: undefined },
    );
    await withTransaction(db.store, (tx) => recordAttribution(tx, r));
    expect(await row(r.id)).toMatchObject({
      actor_kind: 'configuration',
      request_id: null,
      principal: null,
      credential_id: null,
    });
  });

  it('an agent record with no envelope: registration, instance, resolved sponsor', async () => {
    const r = base(agent, { operation: 'exchangeBootstrap' });
    await withTransaction(db.store, (tx) => recordAttribution(tx, r));
    expect(await row(r.id)).toMatchObject({
      actor_kind: 'agent',
      registration: 'reg-b',
      instance: 'inst-b',
      sponsor: 'h@example.com',
      chain: null,
    });
  });

  it('an agent record at zero hops, and across a multi-hop chain with load-bearing re-broadening', async () => {
    const zero = base(agent, {
      operation: 'publish',
      envelope: {
        chain: [{ instance: 'inst-a' }],
        origin: { originMode: 'autonomous' },
        reBroadening: { loadBearing: false },
      },
    });
    const two = base(agent, {
      operation: 'subscribe',
      envelope: {
        chain: [{ instance: 'inst-a' }, { instance: 'inst-b' }],
        origin: { originMode: 'autonomous' },
        reBroadening: { loadBearing: true, hop: 1 },
      },
    });
    await withTransaction(db.store, async (tx) => {
      await recordAttribution(tx, zero);
      await recordAttribution(tx, two);
    });
    expect(await row(zero.id)).toMatchObject({
      chain: [{ instance: 'inst-a' }],
      origin: { originMode: 'autonomous' },
      rebroadening_load_bearing: false,
      rebroadening_hop: null,
    });
    expect(await row(two.id)).toMatchObject({
      chain: [{ instance: 'inst-a' }, { instance: 'inst-b' }],
      sponsor: 'h@example.com',
      rebroadening_load_bearing: true,
      rebroadening_hop: 1,
    });
  });
});

describe('TC-EHA-047 (the writer half): an inconsistent record is refused before any SQL', () => {
  const envelope = {
    chain: [{ instance: 'a' }],
    origin: { originMode: 'autonomous' },
    reBroadening: { loadBearing: false },
  };
  it.each([
    ['a human actor with an envelope', base(human, { envelope })],
    ['a configuration actor with an envelope', base({ kind: 'configuration' }, { envelope })],
    [
      'an agent actor without a sponsor',
      base({ ...agent, sponsor: '' }, { operation: 'exchangeBootstrap' }),
    ],
    [
      'a hop without load-bearing',
      base(agent, { envelope: { ...envelope, reBroadening: { loadBearing: false, hop: 0 } } }),
    ],
    [
      'load-bearing with no hop',
      base(agent, { envelope: { ...envelope, reBroadening: { loadBearing: true } } }),
    ],
    [
      'a hop outside the chain',
      base(agent, { envelope: { ...envelope, reBroadening: { loadBearing: true, hop: 1 } } }),
    ],
  ])('refuses %s', async (_name, record) => {
    await expect(
      withTransaction(db.store, (tx) => recordAttribution(tx, record)),
    ).rejects.toBeInstanceOf(AttributionRecordError);
    const c = await db.app();
    try {
      const { rows } = await c.query('SELECT 1 FROM attribution_records WHERE id = $1', [
        record.id,
      ]);
      expect(rows).toHaveLength(0);
    } finally {
      await c.end();
    }
  });
});

describe('append-only (BR-AT-08): the app role cannot change a written record', () => {
  it('refuses UPDATE and DELETE', async () => {
    const r = base(human);
    await withTransaction(db.store, (tx) => recordAttribution(tx, r));
    const c = await db.app();
    try {
      await expect(
        c.query("UPDATE attribution_records SET operation = 'x' WHERE id = $1", [r.id]),
      ).rejects.toMatchObject({ code: '42501' });
      await expect(
        c.query('DELETE FROM attribution_records WHERE id = $1', [r.id]),
      ).rejects.toMatchObject({ code: '42501' });
    } finally {
      await c.end();
    }
  });
});
