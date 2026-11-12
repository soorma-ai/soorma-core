// SPDX-License-Identifier: FSL-1.1-ALv2
//
// P8, the abuse bound (BR-AB-01 to 07; NFR-OI-02 to 06; P-04, P-05).
//
// - One counter per presented reference, shared by the three surfaces that
//   verify material (authenticate, firstAuthenticate, changeMaterial): the
//   surface is not part of the key (BR-AB-01)
// - Keyed on the presented reference, known or not, so an identifier that
//   names no principal is bounded the same way (BR-AB-06; BR-ERR-04)
// - The slot is HMAC-SHA-256(counter secret, the reference's RFC 8785 form)
//   mod 2^20, in a fixed table in the org store (NFR-OI-05). A collision can
//   only over-count
// - Reserve, then settle: admission appends an entry atomically, with no
//   transaction open while hashing. A failure keeps the entry; a success
//   removes exactly its own. A crash between leaves the entry: fail closed
// - It limits rate and recovers with time; it never locks permanently
//
// Built on P8's generic core since U6 (slot-bound.ts; NP-AC-07, D-CG-AC-05):
// every export, signature, and result here is unchanged.
import {
  type Clock,
  type PrincipalReference,
  type Queryable,
  referenceJson,
  type SecretBytes,
} from '@soorma/service-kit';
import {
  retryAfterFor,
  SLOT_COUNT,
  SlotBound,
  slotOfKey,
  type Admission,
  type Reservation,
  type SlotLimits,
} from './slot-bound.ts';

export { SLOT_COUNT, type Admission, type Reservation };
export const WINDOW_MS = 15 * 60 * 1000;
export const MAX_LIVE_ENTRIES = 10;
export const BACKOFF_FROM_FAILURE = 5;
export const BACKOFF_CAP_SECONDS = 900;

/** U2's values (NFR-OI-02, 03). */
const PRINCIPAL_LIMITS: SlotLimits = {
  windowMs: WINDOW_MS,
  maxLive: MAX_LIVE_ENTRIES,
  backoffFrom: BACKOFF_FROM_FAILURE,
  backoffCapSeconds: BACKOFF_CAP_SECONDS,
};

/** The slot of a presented reference: the HMAC as a big-endian integer, mod 2^20. */
export function slotOf(reference: PrincipalReference, counterSecret: SecretBytes): number {
  return slotOfKey(referenceJson(reference), counterSecret);
}

/** The later of the window wait and the backoff wait, in whole seconds, at least 1 (P-05). */
export function retryAfterSeconds(
  entries: readonly { at: number }[],
  nextAllowedMs: number | null,
  nowMs: number,
): number {
  return retryAfterFor(PRINCIPAL_LIMITS, entries, nextAllowedMs, nowMs);
}

export class AbuseBound {
  private readonly core: SlotBound;

  constructor(store: Queryable, counterSecret: SecretBytes, clock: Clock) {
    this.core = new SlotBound(store, counterSecret, clock, PRINCIPAL_LIMITS);
  }

  admit(reference: PrincipalReference): Promise<Admission> {
    return this.core.admit(referenceJson(reference));
  }

  settleFailure(reservation: Reservation): Promise<void> {
    return this.core.settleFailure(reservation);
  }

  settleSuccess(reservation: Reservation): Promise<void> {
    return this.core.settleSuccess(reservation);
  }
}
