// SPDX-License-Identifier: FSL-1.1-ALv2
//
// A bounded, first-in-first-out semaphore with a wait deadline (U2 P-09,
// generalised for U4 NP-EHA-05). A permit is granted at once when one is free
// and nobody is waiting; otherwise the caller waits in order, at most `waitMs`,
// and is then refused with `unavailable` (503). It is a resource bound, not
// state (M1-TECH-03).
//
// - `acquire(signal?)` resolves to a release function that releases exactly
//   once: a second call does nothing, so a permit can never be released twice
//   and the count never drifts above `permits`
// - A waiter whose `signal` aborts leaves the queue and holds nothing
// - Timers are looked up when used, so fake timers in tests apply
import { UnavailableError } from './errors.ts';

export type Release = () => void;

export interface Timers {
  set(callback: () => void, ms: number): unknown;
  clear(handle: unknown): void;
}

/** The global timers, looked up at each call. */
export const globalTimers: Timers = {
  set: (callback, ms) => setTimeout(callback, ms),
  clear: (handle) => clearTimeout(handle as ReturnType<typeof setTimeout>),
};

export interface SemaphoreOptions {
  permits: number;
  waitMs: number;
  /** The refusal's internal reason; it never reaches a response. */
  reason: string;
  /** `Retry-After` on the refusal, in whole seconds. */
  retryAfterSeconds: number;
  timers?: Timers;
}

/** The error a waiter receives when its signal aborts while it waits. */
export class AcquireAbortedError extends Error {
  constructor() {
    super('the wait for a permit was aborted');
    this.name = 'AcquireAbortedError';
  }
}

interface Waiter {
  grant: () => void;
  fail: (error: Error) => void;
  timer: unknown;
}

export class Semaphore {
  readonly permits: number;
  private readonly options: SemaphoreOptions;
  private readonly timers: Timers;
  private free: number;
  private readonly queue: Waiter[] = [];

  constructor(options: SemaphoreOptions) {
    const { permits, waitMs } = options;
    if (!Number.isInteger(permits) || permits < 1) throw new RangeError('permits must be >= 1');
    if (!Number.isFinite(waitMs) || waitMs < 0) throw new RangeError('waitMs must be >= 0');
    this.permits = permits;
    this.options = options;
    this.timers = options.timers ?? globalTimers;
    this.free = permits;
  }

  /** Permits not held: for tests and diagnostics. */
  get available(): number {
    return this.free;
  }

  /** Waiters in the queue: for tests and diagnostics. */
  get waiting(): number {
    return this.queue.length;
  }

  /** A permit, as a release-once function. Refuses with UnavailableError after `waitMs`. */
  acquire(signal?: AbortSignal): Promise<Release> {
    if (signal?.aborted) return Promise.reject(new AcquireAbortedError());
    if (this.free > 0 && this.queue.length === 0) {
      this.free -= 1;
      return Promise.resolve(this.releaser());
    }
    return new Promise<Release>((resolve, reject) => {
      const leave = (): boolean => {
        const i = this.queue.indexOf(waiter);
        if (i === -1) return false;
        this.queue.splice(i, 1);
        return true;
      };
      const onAbort = (): void => {
        if (leave()) {
          this.timers.clear(waiter.timer);
          reject(new AcquireAbortedError());
        }
      };
      const waiter: Waiter = {
        grant: () => {
          this.timers.clear(waiter.timer);
          signal?.removeEventListener('abort', onAbort);
          resolve(this.releaser());
        },
        fail: (error) => {
          signal?.removeEventListener('abort', onAbort);
          reject(error);
        },
        timer: undefined,
      };
      waiter.timer = this.timers.set(() => {
        if (leave())
          waiter.fail(new UnavailableError(this.options.reason, this.options.retryAfterSeconds));
      }, this.options.waitMs);
      signal?.addEventListener('abort', onAbort, { once: true });
      this.queue.push(waiter);
    });
  }

  /** Runs `work` holding a permit, and releases it however `work` ends. */
  async run<T>(work: () => Promise<T>, signal?: AbortSignal): Promise<T> {
    const release = await this.acquire(signal);
    try {
      return await work();
    } finally {
      release();
    }
  }

  private releaser(): Release {
    let released = false;
    return () => {
      if (released) return;
      released = true;
      const next = this.queue.shift();
      if (next) next.grant();
      else this.free += 1;
    };
  }
}
