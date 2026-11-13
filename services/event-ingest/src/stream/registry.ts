// SPDX-License-Identifier: FSL-1.1-ALv2
//
// The instance's open streams (NP-ET-09; BR-FO): by id, and by credential
// lineage (`cid`), with the open-stream cap.
//
// - **Superseding on this instance** (BR-FO-04): a new stream of a lineage
//   already open here is registered first, then the one ordered earlier ends
//   `superseded`, so no Delivery accepted in between is missed by both
// - **Across instances** (BR-FO-05): the registering instance then sends a
//   `supersede` message with the cid and the new stream's order key; every
//   instance on E's channel ends its stream of that cid ordered before it.
//   An instance whose own stream of that cid is ordered after the message
//   answers with its own key, so the sender ends its stream: with the order
//   key total, two subscribes of one lineage, raced or in any order across
//   instances, leave exactly the later-ordered one open (BR-FO-05, 07). A
//   lost message leaves the earlier stream open until its own credential's
//   `exp` (BR-FO-06)
// - **The cap** (D-ET-25): at most 256 open streams, counting slots reserved
//   by subscribes between `admit` and their stream; a subscribe of a lineage
//   with a stream open here does not count, since it replaces that stream
import type { Channel, ChannelMessage } from '../channel/channel.ts';
import { orderedBefore } from '../channel/channel.ts';
import { MAX_STREAMS } from '../settings.ts';
import type { EndCode, Stream } from './stream.ts';

/** A slot held between the cap's check and the stream's registration. */
export interface Slot {
  /** Gives the slot back: the subscribe failed before its stream opened. */
  release(): void;
}

export class StreamRegistry {
  private readonly streams = new Set<Stream>();
  private readonly byCid = new Map<string, Stream>();
  private readonly channel: Channel;
  private readonly max: number;
  private reserved = 0;
  private readonly unsubscribe: () => void;

  constructor(channel: Channel, max = MAX_STREAMS) {
    this.channel = channel;
    this.max = max;
    this.unsubscribe = channel.subscribe((message) => this.receive(message));
  }

  get size(): number {
    return this.streams.size;
  }

  /** The open streams, in the order they registered. */
  list(): readonly Stream[] {
    return [...this.streams];
  }

  /** The cap: a slot, or undefined when the instance is full (D-ET-25). */
  reserve(cid: string): Slot | undefined {
    if (!this.byCid.has(cid) && this.streams.size + this.reserved >= this.max) return undefined;
    this.reserved += 1;
    let held = true;
    return {
      release: () => {
        if (!held) return;
        held = false;
        this.reserved -= 1;
      },
    };
  }

  /** Registers an opened stream on its slot, then supersedes (BR-FO-04, 05). */
  register(stream: Stream, slot: Slot): void {
    slot.release();
    this.streams.add(stream);
    const earlier = this.byCid.get(stream.cid);
    if (earlier === undefined) {
      this.byCid.set(stream.cid, stream);
    } else if (orderedBefore(earlier.order, stream.order)) {
      this.byCid.set(stream.cid, stream);
      earlier.end('superseded');
    } else {
      stream.end('superseded');
    }
    this.channel.publish({ kind: 'supersede', cid: stream.cid, order: stream.order });
  }

  /** A stream left `open`: it is no longer offered anything. */
  remove(stream: Stream): void {
    this.streams.delete(stream);
    if (this.byCid.get(stream.cid) === stream) this.byCid.delete(stream.cid);
  }

  /** The sweep (every R): each open stream's expiry and revocation (BR-SR-02). */
  sweep(): void {
    for (const stream of this.streams) stream.check();
  }

  /** Shutdown (BR-SM-08): every stream ends with `code`. */
  endAll(code: EndCode): void {
    for (const stream of [...this.streams]) stream.end(code);
  }

  /** Resolves once every stream's chain has run what is queued so far. */
  async settled(): Promise<void> {
    await Promise.all([...this.streams].map((s) => s.settled()));
  }

  close(): void {
    this.unsubscribe();
  }

  private receive(message: ChannelMessage): void {
    if (message.kind === 'delivery') {
      for (const stream of [...this.streams]) stream.offer(message.frame);
      return;
    }
    const open = this.byCid.get(message.cid);
    if (!open) return;
    if (orderedBefore(open.order, message.order)) open.end('superseded');
    // Ours is the later one: announce it, so the sender ends its stream. Its
    // announcement went out before ours existed, so it cannot know otherwise.
    // The sender, receiving this, holds the earlier stream and only ends it.
    else if (orderedBefore(message.order, open.order))
      this.channel.publish({ kind: 'supersede', cid: message.cid, order: open.order });
  }
}
