// SPDX-License-Identifier: FSL-1.1-ALv2
// The abuse bound and the Failed Attempt writer: TC-OI-011, 028, 030 to 033,
// 050; NFR-OI-02 to 06, 21; P-04, P-05, P-11.
import { randomBytes } from 'node:crypto';
import {
  asSecretBytes,
  type Clock,
  type PrincipalReference,
  type Queryable,
} from '@soorma/org-identity';
import { afterAll, beforeAll, describe, expect, it } from 'vitest';
import { testDatabase, type TestDatabase } from '../../org-identity/test/harness/database.ts';
import {
  AbuseBound,
  FailedAttemptWriter,
  retryAfterSeconds,
  slotOf,
  type Admission,
  type Reservation,
} from '../src/index.ts';

let db: TestDatabase;
beforeAll(async () => {
  db = await testDatabase();
});
afterAll(async () => {
  await db?.drop();
});

class TestClock implements Clock {
  ms = Date.parse('2026-11-08T12:00:00Z');
  now(): Date {
    return new Date(this.ms);
  }
  advance(seconds: number): void {
    this.ms += seconds * 1000;
  }
}

const secret = asSecretBytes(randomBytes(32));

/**
 * A distinct reference per test, so tests share no slot. None of these
 * principals exists: the bound never looks a principal up (BR-AB-06).
 */
const reference = (): PrincipalReference => ({
  organization: 'o1',
  principal: `${randomBytes(6).toString('hex')}@example.com`,
});

function setup(): { bound: AbuseBound; clock: TestClock; ref: PrincipalReference } {
  const clock = new TestClock();
  return { bound: new AbuseBound(db.store, secret, clock), clock, ref: reference() };
}

function reserved(a: Admission): Reservation {
  if (!a.admitted) throw new Error(`expected an admission, got Retry-After ${a.retryAfterSeconds}`);
  return a.reservation;
}

async function fail(bound: AbuseBound, ref: PrincipalReference): Promise<void> {
  await bound.settleFailure(reserved(await bound.admit(ref)));
}

/** The slot row, read directly, so observing never changes it. */
async function slotRow(
  ref: PrincipalReference,
): Promise<{ entries: { id: string; at: number }[]; consecutive: number; nextMs: number | null }> {
  const su = await db.superuser();
  try {
    const { rows } = await su.query<{
      entries: { id: string; at: number }[];
      consecutive: number;
      next_ms: string | null;
    }>(
      `SELECT entries, consecutive, (extract(epoch FROM next_allowed_at) * 1000)::bigint AS next_ms
         FROM attempt_slots WHERE slot = $1`,
      [slotOf(ref, secret)],
    );
    const r = rows[0]!;
    return {
      entries: r.entries,
      consecutive: r.consecutive,
      nextMs: r.next_ms === null ? null : Number(r.next_ms),
    };
  } finally {
    await su.end();
  }
}

describe('slots and Retry-After (NFR-OI-04, 05; P-05)', () => {
  it('maps a reference into 2^20 slots under the counter secret', () => {
    const ref = reference();
    const slot = slotOf(ref, secret);
    expect(slot).toBeGreaterThanOrEqual(0);
    expect(slot).toBeLessThan(2 ** 20);
    expect(slotOf(ref, secret)).toBe(slot);
    expect(slotOf(ref, asSecretBytes(randomBytes(32)))).not.toBe(slot);
  });

  it('Retry-After is the later wait, in whole seconds rounded up, at least 1', () => {
    const now = 1_000_000_000;
    const ten = Array.from({ length: 10 }, (_, i) => ({ at: now - 60_000 + i }));
    expect(retryAfterSeconds(ten, null, now)).toBe(14 * 60);
    expect(retryAfterSeconds([], now + 1500, now)).toBe(2);
    expect(retryAfterSeconds(ten, now + 900_000, now)).toBe(900);
    expect(retryAfterSeconds([], null, now)).toBe(1);
  });
});

describe('TC-OI-031: backoff doubles from the 5th failure, to a 15-minute cap', () => {
  it('after the n-th consecutive failure the next attempt waits 2^(n-5) s, capped at 900', async () => {
    const { bound, clock, ref } = setup();
    const waits: (number | null)[] = [];
    for (let n = 1; n <= 16; n++) {
      await fail(bound, ref);
      const row = await slotRow(ref);
      expect(row.consecutive).toBe(n);
      waits.push(row.nextMs === null ? null : (row.nextMs - clock.ms) / 1000);
      if (row.nextMs !== null) {
        // One millisecond early is refused, with Retry-After the remaining wait.
        clock.ms = row.nextMs - 1;
        const early = await bound.admit(ref);
        expect(early).toEqual({
          admitted: false,
          retryAfterSeconds: Math.ceil((row.nextMs - clock.ms) / 1000),
        });
      }
      clock.advance(16 * 60); // past any backoff, and past the window
    }
    expect(waits).toEqual([
      null,
      null,
      null,
      null,
      1,
      2,
      4,
      8,
      16,
      32,
      64,
      128,
      256,
      512,
      900,
      900,
    ]);
  });

  it('a success resets the backoff', async () => {
    const { bound, clock, ref } = setup();
    for (let n = 1; n <= 6; n++) {
      await fail(bound, ref);
      clock.advance(16 * 60);
    }
    await bound.settleSuccess(reserved(await bound.admit(ref)));
    const row = await slotRow(ref);
    expect(row.consecutive).toBe(0);
    expect(row.nextMs).toBeNull();
  });
});

describe('TC-OI-011: attempts beyond the bound are refused', () => {
  it('refuses the 11th attempt within 15 minutes, until the oldest leaves the window', async () => {
    const { bound, clock, ref } = setup();
    const t0 = clock.ms;
    for (let n = 1; n <= 10; n++) {
      if (n >= 6) clock.advance(2 ** (n - 6)); // wait out the backoff: 1, 2, 4, 8, 16 s
      await fail(bound, ref);
    }
    clock.advance(32); // the backoff after the 10th; now t0 + 63 s
    const refused = await bound.admit(ref);
    expect(refused).toEqual({ admitted: false, retryAfterSeconds: 900 - 63 });
    expect((await slotRow(ref)).entries).toHaveLength(10); // a refusal records nothing
    clock.ms = t0 + 900_000 - 1;
    expect((await bound.admit(ref)).admitted).toBe(false);
    clock.ms = t0 + 900_000; // the five entries made at t0 leave the window
    expect((await bound.admit(ref)).admitted).toBe(true);
  });

  it('an admitted attempt never settled counts as a failure: a crash fails closed', async () => {
    const { bound, ref } = setup();
    for (let i = 0; i < 10; i++) reserved(await bound.admit(ref));
    expect((await bound.admit(ref)).admitted).toBe(false);
  });
});

describe('TC-OI-030: a success does not restore the window allowance', () => {
  it('removes only its own entry; the failures stay until they decay', async () => {
    const { bound, clock, ref } = setup();
    for (let n = 1; n <= 9; n++) {
      if (n >= 6) clock.advance(2 ** (n - 6));
      await fail(bound, ref);
    }
    clock.advance(16);
    await bound.settleSuccess(reserved(await bound.admit(ref)));
    expect((await slotRow(ref)).entries).toHaveLength(9);
    await fail(bound, ref); // the 10th live entry; the backoff restarted at 1
    const refused = await bound.admit(ref);
    expect(refused.admitted).toBe(false);
    expect((await slotRow(ref)).consecutive).toBe(1);
  });
});

describe('TC-OI-033: concurrent attempts cannot exceed the bound', () => {
  it('admits at most 10 of 20 parallel attempts', async () => {
    const { bound, ref } = setup();
    const results = await Promise.all(Array.from({ length: 20 }, () => bound.admit(ref)));
    expect(results.filter((r) => r.admitted)).toHaveLength(10);
    expect((await slotRow(ref)).entries).toHaveLength(10);
  });

  it('a success removes only its own reservation, even when others are concurrent', async () => {
    const { bound, ref } = setup();
    const [a, b, c] = (
      await Promise.all([bound.admit(ref), bound.admit(ref), bound.admit(ref)])
    ).map(reserved);
    await Promise.all([bound.settleSuccess(a!), bound.settleFailure(b!)]);
    const ids = (await slotRow(ref)).entries.map((e) => e.id).sort();
    expect(ids).toEqual([b!.entryId, c!.entryId].sort());
  });
});

describe('TC-OI-028 and TC-OI-032: one counter per presented reference', () => {
  it('bounds a reference that names no principal exactly like one that does', async () => {
    const { bound, ref } = setup();
    const su = await db.superuser();
    try {
      const { rows } = await su.query('SELECT 1 FROM principals WHERE principal = $1', [
        ref.principal,
      ]);
      expect(rows).toHaveLength(0);
    } finally {
      await su.end();
    }
    for (let i = 0; i < 10; i++) reserved(await bound.admit(ref));
    expect((await bound.admit(ref)).admitted).toBe(false);
  });

  it('takes no surface: authenticate, firstAuthenticate, and changeMaterial share one counter', () => {
    expect(AbuseBound.prototype.admit.length).toBe(1);
  });
});

describe('TC-OI-050: the Failed Attempt writer stays off the response path', () => {
  const H = { organization: 'o1', principal: 'writer@example.com' };

  beforeAll(async () => {
    const app = await db.app();
    try {
      await app.query(
        `INSERT INTO principals
           (organization, principal, state, registered_at, registered_by_environment, activated_at)
         VALUES ($1, $2, 'active', now(), 'e', now())`,
        [H.organization, H.principal],
      );
    } finally {
      await app.end();
    }
  });

  const attempt = () => ({
    ...H,
    surface: 'authenticate' as const,
    at: new Date('2026-11-08T12:00:00Z'),
    refusedByBound: false,
  });

  it('record returns at once, even while the store never answers', () => {
    const stuck: Queryable = { query: () => new Promise(() => undefined) };
    const writer = new FailedAttemptWriter(stuck, { batchSize: 1 });
    const started = performance.now();
    expect(writer.record(attempt())).toBeUndefined();
    writer.record(attempt());
    expect(performance.now() - started).toBeLessThan(50);
  });

  it('a full queue drops and reports; a failed batch is dropped and reported', async () => {
    const dropped: number[] = [];
    const stuck: Queryable = { query: () => new Promise(() => undefined) };
    const full = new FailedAttemptWriter(stuck, {
      queueLimit: 3,
      onDropped: (n) => dropped.push(n),
    });
    for (let i = 0; i < 5; i++) full.record(attempt());
    expect(full.pending).toBe(3);
    expect(dropped).toEqual([1, 1]);

    const failing: Queryable = { query: () => Promise.reject(new Error('down')) };
    const lost: number[] = [];
    const writer = new FailedAttemptWriter(failing, { onDropped: (n) => lost.push(n) });
    writer.record(attempt());
    writer.record(attempt());
    await writer.flush();
    expect(lost).toEqual([2]);
  });

  it('writes in batches of at most 100, and shutdown flushes everything queued', async () => {
    const calls: number[] = [];
    const counting: Queryable = {
      query: (statement, params) => {
        calls.push((params![0] as unknown[]).length);
        return db.store.query(statement, params);
      },
    };
    const writer = new FailedAttemptWriter(counting);
    writer.start();
    for (let i = 0; i < 150; i++) writer.record(attempt());
    await writer.stop();
    expect(writer.pending).toBe(0);
    expect(calls.every((c) => c <= 100)).toBe(true);
    expect(calls.reduce((a, b) => a + b, 0)).toBe(150);
    const { rows } = await db.store.pool.query<{ n: string }>(
      'SELECT count(*) AS n FROM failed_attempts WHERE principal = $1',
      [H.principal],
    );
    expect(rows[0]!.n).toBe('150');
  });
});
