// SPDX-License-Identifier: FSL-1.1-ALv2
//
// Injected time for S4's timers (NP-ET-12): each stream's expiry and
// heartbeat, the grace, the sweep. Production uses the platform's timers;
// tests replace them with a manual scheduler driven with the test clock.

export interface Timer {
  cancel(): void;
}

export interface Scheduler {
  /** Calls `fn` once, after `ms`. */
  after(ms: number, fn: () => void): Timer;
  /** Calls `fn` every `ms`. */
  every(ms: number, fn: () => void): Timer;
}

export const systemScheduler: Scheduler = Object.freeze({
  after(ms: number, fn: () => void): Timer {
    const handle = setTimeout(fn, Math.max(0, ms));
    handle.unref();
    return { cancel: () => clearTimeout(handle) };
  },
  every(ms: number, fn: () => void): Timer {
    const handle = setInterval(fn, ms);
    handle.unref();
    return { cancel: () => clearInterval(handle) };
  },
});
