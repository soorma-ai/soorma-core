// SPDX-License-Identifier: FSL-1.1-ALv2
//
// The Failed Attempt writer (P-11; NFR-OI-21; D-OI-27): records are written
// off the response path, so the response never waits for them and their
// timing cannot say whether the principal exists (BR-RF-03).
//
// A bounded in-process queue of 10,000; batches of at most 100 rows, every
// 250 ms or as soon as 100 are waiting. A full queue drops the record and
// reports the drop. A failed batch is dropped and reported too. Shutdown
// flushes. A crash may lose what is queued: accepted, because the bound lives
// in the counters, not in these records.
//
// Only records for an existing principal reach it (D-OI-16), and nothing
// presented is in them: no K, P proof, or enrollment material.
import type { Queryable } from '@soorma/org-identity';
import { SQL } from './sql.ts';

export const QUEUE_LIMIT = 10_000;
export const BATCH_SIZE = 100;
export const FLUSH_INTERVAL_MS = 250;

export type Surface = 'authenticate' | 'firstAuthenticate' | 'changeMaterial';

export interface FailedAttempt {
  organization: string;
  principal: string;
  surface: Surface;
  at: Date;
  refusedByBound: boolean;
}

export interface WriterOptions {
  queueLimit?: number;
  batchSize?: number;
  intervalMs?: number;
  /** Called with how many records were dropped (a full queue, or a failed batch). */
  onDropped?: (count: number) => void;
}

export class FailedAttemptWriter {
  private readonly store: Queryable;
  private readonly queueLimit: number;
  private readonly batchSize: number;
  private readonly intervalMs: number;
  private readonly onDropped: (count: number) => void;
  private readonly queue: FailedAttempt[] = [];
  private timer: ReturnType<typeof setInterval> | undefined;
  private draining: Promise<void> = Promise.resolve();

  constructor(store: Queryable, options: WriterOptions = {}) {
    this.store = store;
    this.queueLimit = options.queueLimit ?? QUEUE_LIMIT;
    this.batchSize = options.batchSize ?? BATCH_SIZE;
    this.intervalMs = options.intervalMs ?? FLUSH_INTERVAL_MS;
    this.onDropped = options.onDropped ?? (() => undefined);
  }

  get pending(): number {
    return this.queue.length;
  }

  /** Queues a record and returns at once: the caller never awaits the write. */
  record(attempt: FailedAttempt): void {
    if (this.queue.length >= this.queueLimit) {
      this.onDropped(1);
      return;
    }
    this.queue.push(attempt);
    if (this.queue.length >= this.batchSize) this.schedule();
  }

  start(): void {
    if (this.timer) return;
    this.timer = setInterval(() => this.schedule(), this.intervalMs);
    this.timer.unref();
  }

  /** Writes everything queued. */
  async flush(): Promise<void> {
    while (this.queue.length > 0) {
      this.schedule();
      await this.draining;
    }
    await this.draining;
  }

  /** Stops the timer and flushes: graceful shutdown. */
  async stop(): Promise<void> {
    if (this.timer) clearInterval(this.timer);
    this.timer = undefined;
    await this.flush();
  }

  private schedule(): void {
    this.draining = this.draining.then(() => this.writeBatch());
  }

  private async writeBatch(): Promise<void> {
    const batch = this.queue.splice(0, this.batchSize);
    if (batch.length === 0) return;
    try {
      await this.store.query(SQL.insertFailedAttempts, [
        batch.map((a) => a.organization),
        batch.map((a) => a.principal),
        batch.map((a) => a.surface),
        batch.map((a) => a.at.toISOString()),
        batch.map((a) => a.refusedByBound),
      ]);
    } catch {
      this.onDropped(batch.length);
    }
  }
}
