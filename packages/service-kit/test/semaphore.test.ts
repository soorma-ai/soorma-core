// SPDX-License-Identifier: FSL-1.1-ALv2
import { afterEach, describe, expect, it, vi } from 'vitest';
import { AcquireAbortedError, Semaphore, UnavailableError } from '../src/index.ts';

const options = { reason: 'test bound', retryAfterSeconds: 5 };

afterEach(() => {
  vi.useRealTimers();
});

describe('Semaphore (U4 NP-EHA-05; TC-EHA-058, 059, 060)', () => {
  it('grants at once while permits are free, then refuses at the deadline with Retry-After', async () => {
    vi.useFakeTimers();
    const s = new Semaphore({ permits: 2, waitMs: 1000, ...options });
    const a = await s.acquire();
    await s.acquire();
    expect(s.available).toBe(0);
    const outcome = s.acquire().catch((e: unknown) => e);
    await vi.advanceTimersByTimeAsync(999);
    expect(s.waiting).toBe(1);
    await vi.advanceTimersByTimeAsync(1);
    const error = await outcome;
    expect(error).toBeInstanceOf(UnavailableError);
    expect((error as UnavailableError).retryAfterSeconds).toBe(5);
    expect((error as UnavailableError).message).toBe('test bound');
    expect(s.waiting).toBe(0);
    a();
    expect(s.available).toBe(1);
  });

  it('serves waiters first in, first out', async () => {
    const s = new Semaphore({ permits: 1, waitMs: 10_000, ...options });
    const order: number[] = [];
    const first = await s.acquire();
    const second = s.acquire().then((r) => (order.push(2), r));
    const third = s.acquire().then((r) => (order.push(3), r));
    first();
    (await second)();
    (await third)();
    expect(order).toEqual([2, 3]);
    expect(s.available).toBe(1);
  });

  it('releases exactly once, so the count never drifts above the permits', async () => {
    const s = new Semaphore({ permits: 2, waitMs: 1000, ...options });
    const release = await s.acquire();
    release();
    release();
    release();
    expect(s.available).toBe(2);
  });

  it('a waiter whose signal aborts leaves the queue and holds nothing', async () => {
    const s = new Semaphore({ permits: 1, waitMs: 10_000, ...options });
    const held = await s.acquire();
    const controller = new AbortController();
    const waiting = s.acquire(controller.signal).catch((e: unknown) => e);
    expect(s.waiting).toBe(1);
    controller.abort();
    expect(await waiting).toBeInstanceOf(AcquireAbortedError);
    expect(s.waiting).toBe(0);
    held();
    expect(s.available).toBe(1);
  });

  it('refuses an already-aborted signal without taking a permit', async () => {
    const s = new Semaphore({ permits: 1, waitMs: 1000, ...options });
    const controller = new AbortController();
    controller.abort();
    await expect(s.acquire(controller.signal)).rejects.toBeInstanceOf(AcquireAbortedError);
    expect(s.available).toBe(1);
  });

  it('run releases its permit however the work ends', async () => {
    const s = new Semaphore({ permits: 1, waitMs: 1000, ...options });
    await expect(s.run(() => Promise.reject(new Error('x')))).rejects.toThrow('x');
    await expect(s.run(() => Promise.resolve(1))).resolves.toBe(1);
    expect(s.available).toBe(1);
  });

  it('refuses a permit count below 1', () => {
    expect(() => new Semaphore({ permits: 0, waitMs: 1, ...options })).toThrow(RangeError);
  });
});
