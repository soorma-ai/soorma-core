// SPDX-License-Identifier: FSL-1.1-ALv2
//
// The clock (P-14). Every time the organization level reads comes from an
// injected Clock, so tests control time.
export const CLOCK = Symbol('soorma.clock');

export interface Clock {
  /** The current time. */
  now(): Date;
}

/** The system clock, provided under CLOCK outside tests. */
export const systemClock: Clock = { now: () => new Date() };
