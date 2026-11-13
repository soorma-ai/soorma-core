// SPDX-License-Identifier: FSL-1.1-ALv2
//
// The stream's send buffer and its grace (NP-ET-10; NFR-ET-08): TC-ET-056 (a
// full buffer ends the stream with overflow, others unaffected) and TC-ET-057
// (a stream that cannot take its end is closed after the grace). The response
// is a stand-in whose undrained bytes the test sets, so a slow reader is
// exact rather than left to the kernel's socket buffers.
import { EventEmitter } from 'node:events';
import type { RevocationSource } from '@soorma/credentials';
import { describe, expect, it } from 'vitest';
import { createInProcessChannel, type Channel } from '../src/channel/channel.ts';
import { END_GRACE_MS, SEND_BUFFER_BYTES } from '../src/settings.ts';
import { StreamRegistry } from '../src/stream/registry.ts';
import { deliveryFrame, Stream, type Ending, type StreamResponse } from '../src/stream/stream.ts';
import { E, ManualScheduler, TestClock } from './support.ts';

class FakeResponse extends EventEmitter implements StreamResponse {
  readonly written: string[] = [];
  ended: string | undefined;
  destroyed = false;
  /** Bytes handed over and not yet drained: set by the test. */
  writableLength = 0;
  writeHead(): this {
    return this;
  }
  flushHeaders(): void {}
  setTimeout(): this {
    return this;
  }
  write(chunk: string): boolean {
    this.written.push(chunk);
    return true;
  }
  end(chunk?: string): this {
    this.ended = chunk;
    return this;
  }
  destroy(): this {
    this.destroyed = true;
    this.emit('close');
    return this;
  }
}

const notRevoked: RevocationSource = { isRevoked: () => Promise.resolve('not_revoked') };

function setup(): {
  channel: Channel;
  clock: TestClock;
  scheduler: ManualScheduler;
  registry: StreamRegistry;
  endings: Ending[];
  make: (cid: string) => { stream: Stream; res: FakeResponse };
} {
  const clock = new TestClock();
  const scheduler = new ManualScheduler(clock);
  const channel = createInProcessChannel();
  const registry = new StreamRegistry(channel);
  const endings: Ending[] = [];
  let n = 0;
  const make = (cid: string): { stream: Stream; res: FakeResponse } => {
    const res = new FakeResponse();
    const stream = new Stream(
      {
        requestId: `r${n}`,
        environment: E,
        agent: 'b',
        instance: 'i',
        cid,
        expiresAt: new Date(clock.ms + 15 * 60_000),
        order: { openedAt: clock.ms, id: String(n++).padStart(32, '0') },
      },
      res,
      {
        clock,
        scheduler,
        revocation: notRevoked,
        onEnded: (s, ending) => {
          registry.remove(s);
          endings.push(ending);
        },
      },
    );
    stream.open({});
    const slot = registry.reserve(cid)!;
    registry.register(stream, slot);
    return { stream, res };
  };
  return { channel, clock, scheduler, registry, endings, make };
}

describe('TC-ET-056: a full send buffer ends the stream with overflow', () => {
  it('past 1 MiB undrained: queued deliveries discarded, end overflow written, others unaffected', async () => {
    const { channel, registry, endings, make } = setup();
    const slow = make('slow');
    const fast = make('fast');
    const frame = deliveryFrame(JSON.stringify({ payload: 'x'.repeat(60_000) }));
    // The slow reader has drained nothing of what it was handed.
    slow.res.writableLength = SEND_BUFFER_BYTES - 100_000;
    channel.publish({ kind: 'delivery', frame });
    channel.publish({ kind: 'delivery', frame });
    await registry.settled();
    expect(slow.res.ended).toBe('event: end\ndata: {"code":"overflow"}\n\n');
    expect(slow.res.written).toEqual([]);
    expect(endings).toContainEqual({ code: 'overflow' });
    expect(fast.res.written).toEqual([frame, frame]);
    expect(fast.stream.isOpen).toBe(true);
    expect(registry.size).toBe(1);
  });

  it('a Delivery exactly filling the buffer is written; one byte more overflows', async () => {
    const { registry, make } = setup();
    const { stream, res } = make('edge');
    const frame = deliveryFrame('{}');
    res.writableLength = SEND_BUFFER_BYTES - Buffer.byteLength(frame);
    stream.offer(frame);
    await registry.settled();
    expect(res.written).toEqual([frame]);
    res.writableLength += 1;
    stream.offer(frame);
    expect(stream.isOpen).toBe(false);
    expect(res.ended).toContain('"overflow"');
  });
});

describe('TC-ET-057: a stream that cannot take its end is closed after the grace', () => {
  it('still open at 4.9 s, destroyed at 5 s', () => {
    const { scheduler, make } = setup();
    const { stream, res } = make('stuck');
    stream.end('superseded');
    scheduler.advance(END_GRACE_MS - 100);
    expect(res.destroyed).toBe(false);
    scheduler.advance(100);
    expect(res.destroyed).toBe(true);
  });

  it('an end that finishes cancels the grace', () => {
    const { scheduler, make } = setup();
    const { stream, res } = make('clean');
    stream.end('superseded');
    res.emit('close');
    scheduler.advance(END_GRACE_MS);
    expect(res.destroyed).toBe(false);
  });
});
