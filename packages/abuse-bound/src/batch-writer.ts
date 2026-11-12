// SPDX-License-Identifier: FSL-1.1-ALv2
//
// P8's generic batch writer (U6 NP-AC-07; D-CG-AC-05), extracted from U2's
// Failed Attempt writer (P-11; NFR-OI-21): records are written off the
// response path, so the response never waits for them and their timing
// cannot say whether the subject exists.
//
// A bounded in-process queue; batches of at most `batchSize` rows, every
// `intervalMs` or as soon as a batch is waiting. A full queue drops the record
// and reports the drop. A failed batch is dropped and reported too. Shutdown
// flushes. A crash may lose what is queued: accepted, because the bound lives
// in the counters, not in these records. The insert statement and the mapping
// from a batch to its parameters are the caller's.
import type { Queryable, Statement } from '@soorma/service-kit';

export const QUEUE_LIMIT = 10_000;
export const BATCH_SIZE = 100;
export const FLUSH_INTERVAL_MS = 250;

export interface WriterOptions {
  queueLimit?: number;
  batchSize?: number;
  intervalMs?: number;
  /** Called with how many records were dropped (a full queue, or a failed batch). */
  onDropped?: (count: number) => void;
}

export class BatchWriter<T> {
  private readonly store: Queryable;
  private readonly insert: Statement;
  private readonly params: (batch: readonly T[]) => unknown[];
  private readonly queueLimit: number;
  private readonly batchSize: number;
  private readonly intervalMs: number;
  private readonly onDropped: (count: number) => void;
  private readonly queue: T[] = [];
  private timer: ReturnType<typeof setInterval> | undefined;
  private draining: Promise<void> = Promise.resolve();

  constructor(
    store: Queryable,
    insert: Statement,
    params: (batch: readonly T[]) => unknown[],
    options: WriterOptions = {},
  ) {
    this.store = store;
    this.insert = insert;
    this.params = params;
    this.queueLimit = options.queueLimit ?? QUEUE_LIMIT;
    this.batchSize = options.batchSize ?? BATCH_SIZE;
    this.intervalMs = options.intervalMs ?? FLUSH_INTERVAL_MS;
    this.onDropped = options.onDropped ?? (() => undefined);
  }

  get pending(): number {
    return this.queue.length;
  }

  /** Queues a record and returns at once: the caller never awaits the write. */
  record(item: T): void {
    if (this.queue.length >= this.queueLimit) {
      this.onDropped(1);
      return;
    }
    this.queue.push(item);
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
      await this.store.query(this.insert, this.params(batch));
    } catch {
      this.onDropped(batch.length);
    }
  }
}
