// SPDX-License-Identifier: FSL-1.1-ALv2
// P8's generic core (U6 NP-AC-07; D-CG-AC-05): the bound's limits are
// parameters, the slot comes from a canonical string, and the batch writer
// takes its statement and mapping. U2's tests (abuse-bound.test.ts) and
// canonical vectors run unchanged over U2's API, now built on this core.
import { randomBytes } from 'node:crypto';
import {
  asSecretBytes,
  referenceJson,
  statement,
  type Clock,
  type Queryable,
} from '@soorma/service-kit';
import { afterAll, beforeAll, describe, expect, it } from 'vitest';
import { testDatabase, type TestDatabase } from '../../org-identity/test/harness/database.ts';
import {
  BatchWriter,
  retryAfterFor,
  retryAfterSeconds,
  SlotBound,
  slotOf,
  slotOfKey,
  type Admission,
  type SlotLimits,
} from '../src/index.ts';

let db: TestDatabase;
beforeAll(async () => {
  db = await testDatabase();
});
afterAll(async () => {
  await db?.drop();
});

class TestClock implements Clock {
  ms = Date.parse('2026-11-12T08:00:00Z');
  now(): Date {
    return new Date(this.ms);
  }
  advance(seconds: number): void {
    this.ms += seconds * 1000;
  }
}

const secret = asSecretBytes(randomBytes(32));
const SMALL: SlotLimits = { windowMs: 60_000, maxLive: 3, backoffFrom: 2, backoffCapSeconds: 4 };
const key = (): string => JSON.stringify({ subject: randomBytes(6).toString('hex') });

function admitted(a: Admission): asserts a is Extract<Admission, { admitted: true }> {
  if (!a.admitted) throw new Error(`expected an admission, got Retry-After ${a.retryAfterSeconds}`);
}

describe('NP-AC-07: the slot comes from a canonical string', () => {
  it("a principal's slot is the core's slot of its RFC 8785 form", () => {
    const reference = { organization: 'o1', principal: 'h@example.com' };
    expect(slotOf(reference, secret)).toBe(slotOfKey(referenceJson(reference), secret));
  });

  it('the slot is within 2^20, and differs under another secret', () => {
    const k = key();
    const other = asSecretBytes(randomBytes(32));
    expect(slotOfKey(k, secret)).toBeGreaterThanOrEqual(0);
    expect(slotOfKey(k, secret)).toBeLessThan(2 ** 20);
    const differs = Array.from({ length: 8 }, () => key()).some(
      (x) => slotOfKey(x, secret) !== slotOfKey(x, other),
    );
    expect(differs).toBe(true);
  });
});

describe("NP-AC-07: the bound's limits are parameters", () => {
  it('the window admits maxLive live attempts, then refuses until the oldest leaves', async () => {
    const clock = new TestClock();
    const bound = new SlotBound(db.store, secret, clock, SMALL);
    const k = key();
    for (let i = 0; i < 3; i++) admitted(await bound.admit(k));
    const refused = await bound.admit(k);
    expect(refused.admitted).toBe(false);
    expect(refused.admitted === false && refused.retryAfterSeconds).toBe(60);
    clock.advance(60);
    admitted(await bound.admit(k));
  });

  it('backoff starts at backoffFrom and is capped at backoffCapSeconds', async () => {
    const clock = new TestClock();
    const bound = new SlotBound(db.store, secret, clock, { ...SMALL, maxLive: 100 });
    const k = key();
    const waits: number[] = [];
    for (let i = 0; i < 6; i++) {
      const a = await bound.admit(k);
      if (!a.admitted) {
        waits.push(a.retryAfterSeconds);
        clock.advance(a.retryAfterSeconds);
        i--;
        continue;
      }
      await bound.settleFailure(a.reservation);
    }
    // Failures 2, 3, 4 set waits of 1, 2, 4 s; the cap keeps failure 5's at 4 s.
    expect(waits).toEqual([1, 2, 4, 4]);
  });

  it('a success removes its own entry and resets the backoff', async () => {
    const clock = new TestClock();
    const bound = new SlotBound(db.store, secret, clock, SMALL);
    const k = key();
    const a = await bound.admit(k);
    admitted(a);
    await bound.settleSuccess(a.reservation);
    for (let i = 0; i < 3; i++) admitted(await bound.admit(k));
  });

  it("retryAfterFor with U2's values is U2's retryAfterSeconds", () => {
    const U2: SlotLimits = {
      windowMs: 15 * 60 * 1000,
      maxLive: 10,
      backoffFrom: 5,
      backoffCapSeconds: 900,
    };
    const now = Date.parse('2026-11-12T08:00:00Z');
    const entries = Array.from({ length: 10 }, (_, i) => ({ at: now - 60_000 + i }));
    expect(retryAfterFor(U2, entries, now + 5_000, now)).toBe(
      retryAfterSeconds(entries, now + 5_000, now),
    );
    expect(retryAfterFor(U2, [], null, now)).toBe(retryAfterSeconds([], null, now));
  });
});

describe('NP-AC-07: the batch writer takes its statement and mapping', () => {
  it('writes each batch through the given statement with the mapped parameters', async () => {
    const seen: { text: string; params: unknown[] }[] = [];
    const store: Queryable = {
      query: (text, params) => {
        seen.push({ text, params: params ?? [] });
        return Promise.resolve([]);
      },
    };
    const insert = statement('INSERT INTO t (a) SELECT * FROM unnest($1::int[])');
    const writer = new BatchWriter<number>(store, insert, (b) => [b.map((n) => n * 2)], {
      batchSize: 2,
    });
    for (const n of [1, 2, 3]) writer.record(n);
    await writer.flush();
    expect(seen.map((s) => s.text)).toEqual([insert, insert]);
    expect(seen.map((s) => s.params)).toEqual([[[2, 4]], [[6]]]);
  });

  it('a full queue drops and reports; a failed batch is dropped and reported', async () => {
    const dropped: number[] = [];
    const failing: Queryable = { query: () => Promise.reject(new Error('down')) };
    const writer = new BatchWriter<number>(failing, statement('SELECT 1'), (b) => [b], {
      queueLimit: 2,
      onDropped: (n) => dropped.push(n),
    });
    for (const n of [1, 2, 3]) writer.record(n);
    await writer.flush();
    expect(dropped).toEqual([1, 2]);
  });
});
