// SPDX-License-Identifier: FSL-1.1-ALv2
// P7 closed both ways (U7 D-ET-07; BR-AT-ET-06; NP-ET-14): TC-ET-042. An agent
// record for an operation outside the envelope-free list carries envelope
// facts, in P7's writer and in the store's 0005 CHECK. The user's condition on
// the approved U5 change: an exchangeBootstrap record needs nothing more than
// an agent actor and no envelope (no target, no credential).
import { newRecordId, withTransaction } from '@soorma/env-store';
import { afterAll, beforeAll, describe, expect, it } from 'vitest';
import {
  AttributionRecordError,
  checkRecord,
  ENVELOPE_BEARING_AGENT_OPERATIONS,
  recordAttribution,
  type Actor,
  type AttributionRecord,
} from '../src/index.ts';
import { SQL } from '../src/sql.ts';
import { testEnvDatabase, type TestEnvDatabase } from '../../env-store/test/harness/database.ts';

const E = { organization: 'o1', project: 'p1', environment: 'e' };
const at = new Date('2026-11-13T08:00:00Z');
const agent: Actor = {
  kind: 'agent',
  registration: 'a',
  instance: 'i-1',
  sponsor: 'h@example.com',
};
const envelope = {
  chain: [{ agent: 'a', instance: 'i-1' }],
  origin: { originMode: 'autonomous' },
  reBroadening: { loadBearing: false },
};
const record = (operation: string, over: Partial<AttributionRecord> = {}): AttributionRecord => ({
  id: newRecordId(),
  recordedAt: at,
  environment: E,
  operation,
  actor: agent,
  ...over,
});

let db: TestEnvDatabase;
let owner: Awaited<ReturnType<TestEnvDatabase['migrator']>>;
beforeAll(async () => {
  db = await testEnvDatabase();
  owner = await db.migrator();
});
afterAll(async () => {
  await owner?.end();
  await db?.drop();
});

/** A row for P7's insert, as the owner writes it past the writer. */
const row = (operation: string, chain: unknown[] | null): unknown[] => [
  newRecordId(),
  at,
  null,
  'o1',
  'p1',
  'e',
  operation,
  'agent',
  null,
  null,
  null,
  'a',
  'i-1',
  'h@example.com',
  null,
  null,
  false,
  chain === null ? null : JSON.stringify(chain),
  chain === null ? null : JSON.stringify({ originMode: 'autonomous' }),
  chain === null ? null : false,
  null,
];

describe('TC-ET-042: P7 is closed both ways', () => {
  it('the envelope-bearing list is exactly publish and subscribe, and frozen', () => {
    expect([...ENVELOPE_BEARING_AGENT_OPERATIONS]).toEqual(['publish', 'subscribe']);
    expect(Object.isFrozen(ENVELOPE_BEARING_AGENT_OPERATIONS)).toBe(true);
  });

  it.each(['publish', 'subscribe', 'anyOtherOperation'])(
    'the writer refuses an agent record for %s with no envelope, and accepts one with',
    (operation) => {
      expect(() => checkRecord(record(operation))).toThrow(AttributionRecordError);
      expect(() => checkRecord(record(operation, { envelope }))).not.toThrow();
    },
  );

  it('an exchangeBootstrap record needs only the agent actor and no envelope (the condition on U5’s change)', async () => {
    const r = record('exchangeBootstrap');
    expect(r.target).toBeUndefined();
    expect(agent.kind === 'agent' && agent.credential).toBeUndefined();
    await withTransaction(db.store, (tx) => recordAttribution(tx, r));
    await owner.query(SQL.insertRecord, row('exchangeBootstrap', null));
  });

  it('the store refuses an agent row for publish with no chain, by its own CHECK', async () => {
    await expect(owner.query(SQL.insertRecord, row('publish', null))).rejects.toMatchObject({
      code: '23514',
      constraint: 'attribution_envelope_bearing_operations',
    });
    await owner.query(SQL.insertRecord, row('publish', [{ agent: 'a', instance: 'i-1' }]));
  });

  it('a human or configuration record is not bound by it', async () => {
    const human: Actor = {
      kind: 'human',
      principal: 'h@example.com',
      credential: { kind: 'environmentCredential', id: 'c1' },
    };
    await withTransaction(db.store, async (tx) => {
      await recordAttribution(tx, record('grantToHuman', { actor: human, requestId: 'r1' }));
      await recordAttribution(
        tx,
        record('configureFirstGrant', { actor: { kind: 'configuration' } }),
      );
    });
  });
});
