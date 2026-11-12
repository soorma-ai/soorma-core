// SPDX-License-Identifier: FSL-1.1-ALv2
//
// P8's generic core (U6 NP-AC-07; D-CG-AC-05): the abuse bound over a fixed
// slot table, for any subject. U2's principal bound (abuse-bound.ts) and U6's
// agent bound are both this core, with their own canonical key and limits.
//
// - The slot is HMAC-SHA-256(counter secret, the subject's canonical string),
//   its last four bytes read big-endian, mod 2^20, in a fixed table named
//   `attempt_slots` in the subject's store. A collision can only over-count
// - Reserve, then settle: admission appends an entry atomically, with no
//   transaction open while hashing. A failure keeps the entry; a success
//   removes exactly its own. A crash between leaves the entry: fail closed
// - It limits rate and recovers with time; it never locks permanently
import { createHmac, randomUUID } from 'node:crypto';
import type { Clock, Queryable, SecretBytes } from '@soorma/service-kit';
import { SQL } from './sql.ts';

export const SLOT_COUNT = 2 ** 20;

/** A bound's values: the window, the live attempts it admits, and the backoff. */
export interface SlotLimits {
  /** The sliding window, in milliseconds. */
  readonly windowMs: number;
  /** At most this many live entries in the window. */
  readonly maxLive: number;
  /** Backoff starts at this consecutive failure. */
  readonly backoffFrom: number;
  /** The backoff's cap, in seconds. */
  readonly backoffCapSeconds: number;
}

/** An admitted attempt's entry, settled once verification is done. */
export interface Reservation {
  slot: number;
  entryId: string;
}

export type Admission =
  { admitted: true; reservation: Reservation } | { admitted: false; retryAfterSeconds: number };

/** The slot of a canonical subject string: the HMAC as a big-endian integer, mod 2^20. */
export function slotOfKey(canonical: string, counterSecret: SecretBytes): number {
  const mac = createHmac('sha256', counterSecret).update(canonical, 'utf8').digest();
  return mac.readUInt32BE(mac.length - 4) % SLOT_COUNT;
}

/** The later of the window wait and the backoff wait, in whole seconds, at least 1. */
export function retryAfterFor(
  limits: SlotLimits,
  entries: readonly { at: number }[],
  nextAllowedMs: number | null,
  nowMs: number,
): number {
  const live = entries.map((e) => e.at).filter((at) => at > nowMs - limits.windowMs);
  const windowWait =
    live.length >= limits.maxLive ? Math.min(...live) + limits.windowMs - nowMs : 0;
  const backoffWait = nextAllowedMs === null ? 0 : nextAllowedMs - nowMs;
  return Math.max(1, Math.ceil(Math.max(windowWait, backoffWait) / 1000));
}

export class SlotBound {
  private readonly store: Queryable;
  private readonly counterSecret: SecretBytes;
  private readonly clock: Clock;
  private readonly limits: SlotLimits;

  constructor(store: Queryable, counterSecret: SecretBytes, clock: Clock, limits: SlotLimits) {
    this.store = store;
    this.counterSecret = counterSecret;
    this.clock = clock;
    this.limits = limits;
  }

  /** The slot a canonical subject string maps to, under this bound's secret. */
  slotOf(canonical: string): number {
    return slotOfKey(canonical, this.counterSecret);
  }

  async admit(canonical: string): Promise<Admission> {
    const slot = this.slotOf(canonical);
    const entryId = randomUUID();
    const now = this.clock.now().getTime();
    const admitted = await this.store.query(SQL.admit, [
      slot,
      entryId,
      now,
      this.limits.windowMs,
      this.limits.maxLive,
    ]);
    if (admitted.length === 1) return { admitted: true, reservation: { slot, entryId } };
    const [state] = await this.store.query<{
      entries: { at: number }[];
      next_allowed_ms: string | null;
    }>(SQL.slotState, [slot]);
    return {
      admitted: false,
      retryAfterSeconds: retryAfterFor(
        this.limits,
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
      this.limits.backoffFrom,
      this.limits.backoffCapSeconds,
    ]);
  }

  async settleSuccess(reservation: Reservation): Promise<void> {
    await this.store.query(SQL.settleSuccess, [reservation.slot, reservation.entryId]);
  }
}
