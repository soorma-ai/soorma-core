// SPDX-License-Identifier: FSL-1.1-ALv2
//
// What P10's flows need from P8 (the abuse bound) and its Failed Attempt
// writer. Declared here, satisfied structurally by @soorma/abuse-bound, which
// itself builds on this package, so neither imports the other's classes.
import type { PrincipalReference } from '@soorma/service-kit';

export type BoundAdmission<R> =
  { admitted: true; reservation: R } | { admitted: false; retryAfterSeconds: number };

/** P8: admit before any material is checked; settle after (P-04). */
export interface AttemptBound<R = unknown> {
  admit(reference: PrincipalReference): Promise<BoundAdmission<R>>;
  settleFailure(reservation: R): Promise<void>;
  settleSuccess(reservation: R): Promise<void>;
}

export type Surface = 'authenticate' | 'firstAuthenticate' | 'changeMaterial';

/** P8's writer: queues a record and returns at once (D-OI-27). */
export interface FailureRecorder {
  record(attempt: {
    organization: string;
    principal: string;
    surface: Surface;
    at: Date;
    refusedByBound: boolean;
  }): void;
}
