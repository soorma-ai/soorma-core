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
import { createHmac, randomUUID } from 'node:crypto';
import {
  type Clock,
  type PrincipalReference,
  type Queryable,
  referenceJson,
  type SecretBytes,
} from '@soorma/service-kit';
import { SQL } from './sql.ts';

export const SLOT_COUNT = 2 ** 20;
export const WINDOW_MS = 15 * 60 * 1000;
export const MAX_LIVE_ENTRIES = 10;
export const BACKOFF_FROM_FAILURE = 5;
export const BACKOFF_CAP_SECONDS = 900;

/** An admitted attempt's entry, settled once verification is done. */
export interface Reservation {
  slot: number;
  entryId: string;
}

export type Admission =
  { admitted: true; reservation: Reservation } | { admitted: false; retryAfterSeconds: number };

/** The slot of a presented reference: the HMAC as a big-endian integer, mod 2^20. */
export function slotOf(reference: PrincipalReference, counterSecret: SecretBytes): number {
  const mac = createHmac('sha256', counterSecret).update(referenceJson(reference), 'utf8').digest();
  return mac.readUInt32BE(mac.length - 4) % SLOT_COUNT;
}

/** The later of the window wait and the backoff wait, in whole seconds, at least 1 (P-05). */
export function retryAfterSeconds(
  entries: readonly { at: number }[],
  nextAllowedMs: number | null,
  nowMs: number,
): number {
  const live = entries.map((e) => e.at).filter((at) => at > nowMs - WINDOW_MS);
  const windowWait = live.length >= MAX_LIVE_ENTRIES ? Math.min(...live) + WINDOW_MS - nowMs : 0;
  const backoffWait = nextAllowedMs === null ? 0 : nextAllowedMs - nowMs;
  return Math.max(1, Math.ceil(Math.max(windowWait, backoffWait) / 1000));
}

export class AbuseBound {
  private readonly store: Queryable;
  private readonly counterSecret: SecretBytes;
  private readonly clock: Clock;

  constructor(store: Queryable, counterSecret: SecretBytes, clock: Clock) {
    this.store = store;
    this.counterSecret = counterSecret;
    this.clock = clock;
  }

  async admit(reference: PrincipalReference): Promise<Admission> {
    const slot = slotOf(reference, this.counterSecret);
    const entryId = randomUUID();
    const now = this.clock.now().getTime();
    const admitted = await this.store.query(SQL.admit, [
      slot,
      entryId,
      now,
      WINDOW_MS,
      MAX_LIVE_ENTRIES,
    ]);
    if (admitted.length === 1) return { admitted: true, reservation: { slot, entryId } };
    const [state] = await this.store.query<{
      entries: { at: number }[];
      next_allowed_ms: string | null;
    }>(SQL.slotState, [slot]);
    return {
      admitted: false,
      retryAfterSeconds: retryAfterSeconds(
        state?.entries ?? [],
        state?.next_allowed_ms == null ? null : Number(state.next_allowed_ms),
        now,
      ),
    };
  }

  async settleFailure(reservation: Reservation): Promise<void> {
    await this.store.query(SQL.settleFailure, [
      reservation.slot,
      this.clock.now().getTime(),
      BACKOFF_FROM_FAILURE,
      BACKOFF_CAP_SECONDS,
    ]);
  }

  async settleSuccess(reservation: Reservation): Promise<void> {
    await this.store.query(SQL.settleSuccess, [reservation.slot, reservation.entryId]);
  }
}
