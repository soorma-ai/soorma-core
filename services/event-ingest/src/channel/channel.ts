// SPDX-License-Identifier: FSL-1.1-ALv2
//
// E's fan-out channel (NP-ET-08; BR-FO-01 to 03): the port, and the one
// implementation M1 runs, in process. One channel per S4 process, so one per
// environment (NFR-ET-13): nothing on E's channel reaches E2. The channel
// stores, replays, orders, and acknowledges nothing (GAP-INT-003).

/** A stream's order key: its opening time, then a 128-bit id (D-ET-05; NP-ET-09). */
export interface OrderKey {
  readonly openedAt: number;
  /** 32 lowercase hex characters, from the CSPRNG. */
  readonly id: string;
}

export type ChannelMessage =
  /** One accepted publish: its SSE frame, serialized once (NP-ET-11). */
  | { readonly kind: 'delivery'; readonly frame: string }
  /** A stream of lineage `cid` opened with `order`: earlier ones of that lineage end. */
  | { readonly kind: 'supersede'; readonly cid: string; readonly order: OrderKey };

export interface Channel {
  publish(message: ChannelMessage): void;
  /** Returns the unsubscribe. */
  subscribe(handler: (message: ChannelMessage) => void): () => void;
}

/** The in-process channel: every handler of this object, in order, synchronously. */
export function createInProcessChannel(): Channel {
  const handlers = new Set<(message: ChannelMessage) => void>();
  return Object.freeze({
    publish(message: ChannelMessage): void {
      for (const handler of [...handlers]) handler(message);
    },
    subscribe(handler: (message: ChannelMessage) => void): () => void {
      handlers.add(handler);
      return () => handlers.delete(handler);
    },
  });
}

/** True when `a` is ordered before `b`: earlier opening, then the smaller id. */
export function orderedBefore(a: OrderKey, b: OrderKey): boolean {
  return a.openedAt < b.openedAt || (a.openedAt === b.openedAt && a.id < b.id);
}
