// SPDX-License-Identifier: FSL-1.1-ALv2
//
// Retention (P-16; NFR-OI-25): a daily timer in every instance; the work runs
// only in the one that takes the advisory lock. It deletes Failed Attempt
// records, and ended or expired sign-in records, older than 90 days.
// Principals and material are never touched: the app role has no DELETE on
// them (BR-HP-03).
import { createHash } from 'node:crypto';
import type { Clock, Store } from '@soorma/service-kit';
import { SQL } from '../sql.ts';

export const RETENTION_MS = 90 * 24 * 60 * 60 * 1000;
export const PRUNE_INTERVAL_MS = 24 * 60 * 60 * 1000;

/** The advisory lock key: the first 63 bits of SHA-256("soorma.org.prune"). */
export const PRUNE_LOCK_KEY = (
  createHash('sha256').update('soorma.org.prune').digest().readBigUInt64BE(0) >> 1n
).toString();

export interface PruneResult {
  /** False when another instance held the lock. */
  ran: boolean;
  failedAttempts: number;
  signIns: number;
}

export class Pruner {
  private readonly store: Store;
  private readonly clock: Clock;
  private timer: ReturnType<typeof setInterval> | undefined;

  constructor(store: Store, clock: Clock) {
    this.store = store;
    this.clock = clock;
  }

  async prune(): Promise<PruneResult> {
    const cutoff = new Date(this.clock.now().getTime() - RETENTION_MS);
    return this.store.transaction(async (tx) => {
      const [lock] = await tx.query<{ locked: boolean }>(SQL.pruneLock, [PRUNE_LOCK_KEY]);
      if (!lock?.locked) return { ran: false, failedAttempts: 0, signIns: 0 };
      const failedAttempts = (await tx.query(SQL.pruneFailedAttempts, [cutoff])).length;
      const signIns = (await tx.query(SQL.pruneSignIns, [cutoff])).length;
      return { ran: true, failedAttempts, signIns };
    });
  }

  /** Starts the daily timer. A failed run is retried at the next interval. */
  start(intervalMs: number = PRUNE_INTERVAL_MS): void {
    if (this.timer) return;
    this.timer = setInterval(() => {
      this.prune().catch(() => undefined);
    }, intervalMs);
    this.timer.unref();
  }

  stop(): void {
    if (this.timer) clearInterval(this.timer);
    this.timer = undefined;
  }
}
