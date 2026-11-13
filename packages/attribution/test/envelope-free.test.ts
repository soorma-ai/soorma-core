// SPDX-License-Identifier: FSL-1.1-ALv2
// TC-AC-036 (the writer half; D-AC-33; BR-AT-AC-02): exchangeBootstrap and
// renewAgentCredential never carry an envelope, so P7 refuses envelope facts
// on them, and refuses them for any actor but an agent, before any SQL. The
// store's CHECK (env-store 0004) repeats it (the store half is in
// packages/env-store/test/agent-credentials.test.ts). U4's and U5's record
// tests are unchanged: the reverse rule (every other agent operation must
// carry envelope facts) is U7's.
import { describe, expect, it } from 'vitest';
import {
  AttributionRecordError,
  checkRecord,
  ENVELOPE_FREE_AGENT_OPERATIONS,
  type Actor,
  type AttributionRecord,
} from '../src/index.ts';

const agent: Actor = {
  kind: 'agent',
  registration: 'a',
  instance: 'i-1',
  sponsor: 'h@example.com',
};
const human: Actor = {
  kind: 'human',
  principal: 'h@example.com',
  credential: { kind: 'environmentCredential', id: 'c' },
};
const envelope = {
  chain: [{ agent: 'a', instance: 'i-1' }],
  origin: { originMode: 'autonomous' },
  reBroadening: { loadBearing: false },
};
const record = (operation: string, over: Partial<AttributionRecord> = {}): AttributionRecord => ({
  id: 'r',
  recordedAt: new Date('2026-11-12T08:00:00Z'),
  environment: { organization: 'o1', project: 'p1', environment: 'e' },
  operation,
  actor: agent,
  ...over,
});

describe('TC-AC-036: an envelope-free operation’s record carries no envelope', () => {
  it('the list is exactly the two operations, and frozen', () => {
    expect([...ENVELOPE_FREE_AGENT_OPERATIONS]).toEqual([
      'exchangeBootstrap',
      'renewAgentCredential',
    ]);
    expect(Object.isFrozen(ENVELOPE_FREE_AGENT_OPERATIONS)).toBe(true);
  });

  it.each(['exchangeBootstrap', 'renewAgentCredential'])(
    '%s: accepted as an agent with no envelope; refused with one, or by a human',
    (operation) => {
      expect(() => checkRecord(record(operation))).not.toThrow();
      expect(() => checkRecord(record(operation, { envelope }))).toThrow(AttributionRecordError);
      expect(() => checkRecord(record(operation, { actor: human }))).toThrow(
        AttributionRecordError,
      );
    },
  );

  it('other agent operations carry an envelope (U7 D-ET-07, the reverse rule)', () => {
    expect(() => checkRecord(record('publish', { envelope }))).not.toThrow();
    expect(() => checkRecord(record('constructedAgentOperation'))).toThrow(AttributionRecordError);
  });
});
