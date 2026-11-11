// SPDX-License-Identifier: FSL-1.1-ALv2
//
// The hashing semaphore (P-09; NFR-OI-20). Every Argon2id operation, decoys
// included, holds a permit, so hashing memory is bounded at permits × 64 MiB.
// A waiter is served first in, first out, and waits at most `waitMs`; then the
// request is refused with `unavailable` (503). It is a resource bound, not
// state (M1-TECH-03). Built on @soorma/service-kit's Semaphore (U4 NP-EHA-05).
import { availableParallelism } from 'node:os';
import { Semaphore } from '@soorma/service-kit';

/** Memory per Argon2id operation (NFR-OI-11). */
export const HASH_MEMORY_MIB = 64;
/** How long a request waits for a permit (NFR-OI-20). */
export const HASH_WAIT_MS = 2000;

/** The default permits: the lower of 2 × CPUs and the memory budget ÷ 64 MiB, at least 1. */
export function defaultPermits(budgetMiB: number, cpus: number = availableParallelism()): number {
  return Math.max(1, Math.min(2 * cpus, Math.floor(budgetMiB / HASH_MEMORY_MIB)));
}

export class HashSemaphore {
  readonly permits: number;
  private readonly semaphore: Semaphore;

  constructor(permits: number, waitMs: number = HASH_WAIT_MS) {
    this.semaphore = new Semaphore({
      permits,
      waitMs,
      reason: 'hashing budget exhausted',
      retryAfterSeconds: Math.ceil(waitMs / 1000),
    });
    this.permits = permits;
  }

  /** Runs `work` holding a permit. Refuses with UnavailableError after waiting `waitMs`. */
  run<T>(work: () => Promise<T>): Promise<T> {
    return this.semaphore.run(work);
  }
}
