// SPDX-License-Identifier: FSL-1.1-ALv2
//
// The hashing semaphore (P-09; NFR-OI-20). Every Argon2id operation, decoys
// included, holds a permit, so hashing memory is bounded at permits × 64 MiB.
// A waiter is served first in, first out, and waits at most `waitMs`; then the
// request is refused with `unavailable` (503). It is a resource bound, not
// state (M1-TECH-03).
import { availableParallelism } from 'node:os';
import { UnavailableError } from '../errors.ts';

/** Memory per Argon2id operation (NFR-OI-11). */
export const HASH_MEMORY_MIB = 64;
/** How long a request waits for a permit (NFR-OI-20). */
export const HASH_WAIT_MS = 2000;

/** The default permits: the lower of 2 × CPUs and the memory budget ÷ 64 MiB, at least 1. */
export function defaultPermits(budgetMiB: number, cpus: number = availableParallelism()): number {
  return Math.max(1, Math.min(2 * cpus, Math.floor(budgetMiB / HASH_MEMORY_MIB)));
}

interface Waiter {
  grant: () => void;
  timer: ReturnType<typeof setTimeout>;
}

export class HashSemaphore {
  readonly permits: number;
  private readonly waitMs: number;
  private available: number;
  private readonly queue: Waiter[] = [];

  constructor(permits: number, waitMs: number = HASH_WAIT_MS) {
    if (!Number.isInteger(permits) || permits < 1) throw new RangeError('permits must be >= 1');
    this.permits = permits;
    this.available = permits;
    this.waitMs = waitMs;
  }

  /** Runs `work` holding a permit. Refuses with UnavailableError after waiting `waitMs`. */
  async run<T>(work: () => Promise<T>): Promise<T> {
    await this.acquire();
    try {
      return await work();
    } finally {
      this.release();
    }
  }

  private acquire(): Promise<void> {
    if (this.available > 0 && this.queue.length === 0) {
      this.available -= 1;
      return Promise.resolve();
    }
    return new Promise<void>((resolve, reject) => {
      const waiter: Waiter = {
        grant: () => {
          clearTimeout(waiter.timer);
          resolve();
        },
        timer: setTimeout(() => {
          const i = this.queue.indexOf(waiter);
          if (i !== -1) this.queue.splice(i, 1);
          reject(new UnavailableError('hashing budget exhausted', Math.ceil(this.waitMs / 1000)));
        }, this.waitMs),
      };
      this.queue.push(waiter);
    });
  }

  private release(): void {
    const next = this.queue.shift();
    if (next) next.grant();
    else this.available += 1;
  }
}
