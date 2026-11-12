// SPDX-License-Identifier: FSL-1.1-ALv2
// P8's agent half (U6 NP-AC-07; D-AC-06, 22; NFR-AC-06 to 11), on environment
// stores as S3's role soorma_env_data: TC-AC-081 (U2's API unchanged; the
// agent slot's own vectors), TC-AC-057 (the window), TC-AC-058 (the backoff),
// TC-AC-059 (Retry-After), TC-AC-060 (atomic per slot; one table per
// environment), TC-AC-062 (the writer), TC-AC-049 (the writer's half).
// U2's abuse-bound.test.ts and canonical vectors are unchanged.
import { randomBytes, randomUUID } from 'node:crypto';
import { connectEnvStore } from '@soorma/env-store';
import { asSecretBytes, type Clock, type Queryable, type Store } from '@soorma/service-kit';
import { afterAll, beforeAll, describe, expect, it } from 'vitest';
import { testEnvDatabase, type TestEnvDatabase } from '../../env-store/test/harness/database.ts';
import {
  AGENT_BOOTSTRAP_LIMITS,
  AgentBound,
  agentSlotKey,
  FailedBootstrapAttemptWriter,
  retryAfterFor,
  slotOfKey,
  type Admission,
} from '../src/index.ts';

class TestClock implements Clock {
  ms = Date.parse('2026-11-12T08:00:00Z');
  now(): Date {
    return new Date(this.ms);
  }
  advance(seconds: number): void {
    this.ms += seconds * 1000;
  }
}

const E = { organization: 'o1', project: 'p1', environment: 'e' };
const secret = asSecretBytes(randomBytes(32));
const agent = (): string => `a-${randomBytes(6).toString('hex')}`;

let db: TestEnvDatabase;
let db2: TestEnvDatabase;
let data: Store;
let data2: Store;
const asData = (d: TestEnvDatabase): Store =>
  connectEnvStore({ ...d.settings, user: 'soorma_env_data', password: d.info.dataPassword });

beforeAll(async () => {
  [db, db2] = await Promise.all([testEnvDatabase(), testEnvDatabase()]);
  data = asData(db);
  data2 = asData(db2);
});
afterAll(async () => {
  await Promise.all([data?.close(), data2?.close()]);
  await Promise.all([db?.drop(), db2?.drop()]);
});

const admitted = (a: Admission): boolean => a.admitted;

describe('TC-AC-081: the agent slot has its own canonical form and vectors', () => {
  it('RFC 8785 of { agent, environment }, and its slots under a fixed secret', () => {
    const fixed = asSecretBytes(Buffer.alloc(32, 7));
    const v = (env: typeof E, a: string) => slotOfKey(agentSlotKey(env, a), fixed);
    expect(agentSlotKey(E, 'a')).toBe(
      '{"agent":"a","environment":{"environment":"e","organization":"o1","project":"p1"}}',
    );
    expect(v(E, 'a')).toBe(704919);
    expect(v({ ...E, environment: 'e2' }, 'a')).toBe(776748);
    expect(v(E, 'agent.with~chars-1')).toBe(411088);
  });

  it("the agent limits are NFR-AC-06, 07's, frozen", () => {
    expect(AGENT_BOOTSTRAP_LIMITS).toEqual({
      windowMs: 60_000,
      maxLive: 60,
      backoffFrom: 10,
      backoffCapSeconds: 60,
    });
    expect(Object.isFrozen(AGENT_BOOTSTRAP_LIMITS)).toBe(true);
  });
});

describe('TC-AC-057: at most 60 live attempts per agent in any 60 s', () => {
  it('60 at once are admitted; the 61st refused; a failure frees its place at 60 s', async () => {
    const clock = new TestClock();
    const bound = new AgentBound(data, secret, clock);
    const k = agentSlotKey(E, agent());
    const first = await Promise.all(Array.from({ length: 60 }, () => bound.admit(k)));
    expect(first.every(admitted)).toBe(true);
    const refused = await bound.admit(k);
    expect(refused).toMatchObject({ admitted: false, retryAfterSeconds: 60 });
    for (const a of first) if (a.admitted) await bound.settleFailure(a.reservation);
    clock.advance(60);
    // The backoff from 60 consecutive failures is capped at 60 s, so both waits end now.
    expect((await bound.admit(k)).admitted).toBe(true);
  });

  it('60 parallel successes are all admitted, and free their places at once', async () => {
    const bound = new AgentBound(data, secret, new TestClock());
    const k = agentSlotKey(E, agent());
    const all = await Promise.all(Array.from({ length: 60 }, () => bound.admit(k)));
    expect(all.every(admitted)).toBe(true);
    for (const a of all) if (a.admitted) await bound.settleSuccess(a.reservation);
    expect(
      (await Promise.all(Array.from({ length: 60 }, () => bound.admit(k)))).every(admitted),
    ).toBe(true);
  });
});

describe('TC-AC-058: backoff from the 10th consecutive failure, doubling from 1 s, capped at 60 s', () => {
  it('waits of 1, 2, 4 … 32, 60, 60; a success resets the backoff only', async () => {
    const clock = new TestClock();
    const bound = new AgentBound(data, secret, clock);
    const k = agentSlotKey(E, agent());
    const waits: number[] = [];
    let failures = 0;
    while (failures < 17) {
      const a = await bound.admit(k);
      if (!a.admitted) {
        waits.push(a.retryAfterSeconds);
        clock.advance(a.retryAfterSeconds);
        continue;
      }
      await bound.settleFailure(a.reservation);
      failures++;
    }
    expect(waits).toEqual([1, 2, 4, 8, 16, 32, 60]);
    clock.advance(60);
    const ok = await bound.admit(k);
    if (!ok.admitted) throw new Error('expected an admission');
    await bound.settleSuccess(ok.reservation);
    expect((await bound.admit(k)).admitted).toBe(true);
  });
});

describe('TC-AC-059: Retry-After is the later of the two waits', () => {
  const now = Date.parse('2026-11-12T08:00:00Z');
  const full = Array.from({ length: 60 }, (_, i) => ({ at: now - 30_000 + i }));

  it('a full window (30 s to free) and a longer backoff (60 s): the backoff’s', () => {
    expect(retryAfterFor(AGENT_BOOTSTRAP_LIMITS, full, now + 60_000, now)).toBe(60);
  });

  it('a full window (30 s to free) and a shorter backoff (10 s): the window’s', () => {
    expect(retryAfterFor(AGENT_BOOTSTRAP_LIMITS, full, now + 10_000, now)).toBe(30);
  });

  it('whole seconds, rounded up, at least 1', () => {
    expect(retryAfterFor(AGENT_BOOTSTRAP_LIMITS, [], now + 1_200, now)).toBe(2);
    expect(retryAfterFor(AGENT_BOOTSTRAP_LIMITS, [], null, now)).toBe(1);
  });
});

describe('TC-AC-060: admission is atomic per slot, and each environment has its own table', () => {
  it('80 parallel failing attempts admit at most 60', async () => {
    const bound = new AgentBound(data, secret, new TestClock());
    const k = agentSlotKey(E, agent());
    const all = await Promise.all(Array.from({ length: 80 }, () => bound.admit(k)));
    expect(all.filter(admitted).length).toBe(60);
  });

  it("the same agent in E2 uses E2's own table, unaffected by E's", async () => {
    const a = agent();
    const inE = new AgentBound(data, secret, new TestClock());
    const inE2 = new AgentBound(data2, secret, new TestClock());
    await Promise.all(Array.from({ length: 61 }, () => inE.admit(agentSlotKey(E, a))));
    expect((await inE2.admit(agentSlotKey({ ...E, environment: 'e2' }, a))).admitted).toBe(true);
  });
});

describe('TC-AC-062, TC-AC-049 (the writer): off the response path; only existing registrations', () => {
  const attempt = (a: string) => ({
    environment: E,
    agent: a,
    at: new Date('2026-11-12T08:00:00Z'),
    refusedByBound: false,
    reason: 'secret_mismatch' as const,
  });

  it('record returns at once; a full queue drops and reports; a failed batch is dropped and reported', async () => {
    const stuck: Queryable = { query: () => new Promise(() => undefined) };
    const dropped: number[] = [];
    const full = new FailedBootstrapAttemptWriter(stuck, {
      queueLimit: 2,
      onDropped: (n) => dropped.push(n),
    });
    const started = performance.now();
    for (let i = 0; i < 4; i++) full.record(attempt('x'));
    expect(performance.now() - started).toBeLessThan(50);
    expect(dropped).toEqual([1, 1]);
    const failing: Queryable = { query: () => Promise.reject(new Error('down')) };
    const lost: number[] = [];
    const w = new FailedBootstrapAttemptWriter(failing, { onDropped: (n) => lost.push(n) });
    w.record(attempt('x'));
    await w.flush();
    expect(lost).toEqual([1]);
  });

  it("writes the registered agent's attempts, and none for an unknown agent", async () => {
    const owner = await db.migrator();
    const known = agent();
    try {
      await owner.query(
        `INSERT INTO registrations (organization, project, environment, agent, sponsor,
           ceiling_snapshot, standing_permissions, re_broadening_declaration, autonomy_declared,
           registered_at, state)
         VALUES ('o1', 'p1', 'e', $1, 'h@example.com', '{}', '{}', '{}', true, now(), 'registered')`,
        [known],
      );
      const w = new FailedBootstrapAttemptWriter(data);
      w.start();
      w.record(attempt(known));
      w.record(attempt(`nobody-${randomUUID()}`));
      await w.stop();
      const { rows } = await owner.query<{ agent: string }>(
        'SELECT agent FROM failed_bootstrap_attempts WHERE agent = $1 OR agent LIKE $2',
        [known, 'nobody-%'],
      );
      expect(rows.map((r) => r.agent)).toEqual([known]);
    } finally {
      await owner.end();
    }
  });
});
