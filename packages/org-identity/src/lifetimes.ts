// SPDX-License-Identifier: FSL-1.1-ALv2
//
// Lifetimes of the organization level's time-bound records (NFR-OI-01, 10).
import { Inject, Injectable } from '@nestjs/common';
import { CLOCK, type Clock } from './clock.ts';

/** A sign-in token lives 15 minutes (NFR-OI-01). */
export const SIGN_IN_LIFETIME_MS = 15 * 60 * 1000;
/** Renewal never extends a sign-in past its authentication time plus 12 hours (NFR-OI-01). */
export const SIGN_IN_ABSOLUTE_MAXIMUM_MS = 12 * 60 * 60 * 1000;
/** A pending second-factor enrollment lives 10 minutes (NFR-OI-10). */
export const PENDING_SECOND_FACTOR_LIFETIME_MS = 10 * 60 * 1000;

@Injectable()
export class Lifetimes {
  private readonly clock: Clock;

  constructor(@Inject(CLOCK) clock: Clock) {
    this.clock = clock;
  }

  /** The expiry of a sign-in issued now: the earlier of 15 minutes and the absolute maximum (BR-SI-04). */
  signInExpiry(authenticatedAt: Date): Date {
    return new Date(
      Math.min(
        this.clock.now().getTime() + SIGN_IN_LIFETIME_MS,
        authenticatedAt.getTime() + SIGN_IN_ABSOLUTE_MAXIMUM_MS,
      ),
    );
  }

  /** The expiry of a pending second-factor enrollment begun now. */
  pendingSecondFactorExpiry(): Date {
    return new Date(this.clock.now().getTime() + PENDING_SECOND_FACTOR_LIFETIME_MS);
  }
}
