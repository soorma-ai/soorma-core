// SPDX-License-Identifier: FSL-1.1-ALv2
//
// One subscriber's stream (NP-ET-10, 12; BR-SM; BR-SR): the raw response,
// written by S4 itself after the subscribe's record commits.
//
// - Open: `200`, `text/event-stream; charset=utf-8`, `Cache-Control:
//   no-store`, the two Soorma headers; the socket's idle timeout off (the
//   stream lives at most until its credential's `exp`, L); a timer at `exp`
//   exactly; a heartbeat comment after 15 s of silence, re-armed by every write
// - **A serial chain per stream**: each Delivery offered is checked, then
//   written, in the order offered. The check: the credential has not expired,
//   and P5's cache answers `not_revoked` for its cid and its agent, so no
//   Delivery is written after revocation + B (BR-SR-04). The sweep (every R)
//   runs the same check on the chain, writing nothing
// - **The send buffer**: bytes queued on the chain plus bytes handed to the
//   socket and not yet drained. A Delivery that would take it past 1 MiB ends
//   the stream `overflow`; the queued deliveries are discarded (BR-SM-06)
// - **Every end writes exactly one `end` event** (`{ code }`), then ends the
//   response; a response that cannot take it is destroyed after the 5 s grace.
//   The client closing its connection ends the stream silently (BR-SM-07, 09)
// - Nothing about the subscriber's own stamped envelope is written: the
//   stream carries `delivery` and `end` events only (BR-SB-04)
import type { components } from '@soorma/contract/types/event-ingest';
import type { RevocationSource } from '@soorma/credentials';
import type { EnvironmentRef } from '@soorma/policy-decision-seam';
import type { Clock } from '@soorma/service-kit';
import type { OrderKey } from '../channel/channel.ts';
import type { Scheduler, Timer } from '../scheduler.ts';
import { END_GRACE_MS, HEARTBEAT_MS, SEND_BUFFER_BYTES } from '../settings.ts';

/** The `end` event's data, as the contract defines it (event-ingest.openapi.yaml). */
type StreamEnd = components['schemas']['StreamEnd'];

/** Why a stream ended: the codes S4 writes, each in the contract's open set (StreamEndCode). */
export type EndCode =
  'credential_expired' | 'credential_refused' | 'unavailable' | 'superseded' | 'overflow';

/** What a stream needs of its HTTP response: Node's ServerResponse has it all. */
export interface StreamResponse {
  writeHead(status: number, headers: Record<string, string>): unknown;
  flushHeaders(): void;
  write(chunk: string): boolean;
  end(chunk?: string): unknown;
  destroy(): unknown;
  setTimeout(ms: number): unknown;
  readonly writableLength: number;
  readonly destroyed: boolean;
  on(event: 'close', listener: () => void): unknown;
}

/** Who holds the stream: from the verified credential and the request. */
export interface StreamIdentity {
  readonly requestId: string;
  readonly environment: EnvironmentRef;
  readonly agent: string;
  readonly instance: string;
  /** The credential lineage: one open stream per cid (D-ET-05). */
  readonly cid: string;
  /** The presented credential's `exp`: the stream ends there exactly (BR-SR-01). */
  readonly expiresAt: Date;
  readonly order: OrderKey;
}

/** How a stream's end is reported: the code, or none when the client went away. */
export type Ending =
  | { readonly code: EndCode; readonly reason?: string }
  | { readonly code: undefined; readonly reason: 'client_closed' };

export interface StreamDeps {
  readonly clock: Clock;
  readonly scheduler: Scheduler;
  /** P5's cache: the same one step 4 reads (BR-SR-02). */
  readonly revocation: RevocationSource;
  /** Called once, when the stream leaves `open`. */
  readonly onEnded: (stream: Stream, ending: Ending) => void;
}

export const deliveryFrame = (json: string): string => `event: delivery\ndata: ${json}\n\n`;
export const endFrame = (code: EndCode): string => {
  const end: StreamEnd = { code };
  return `event: end\ndata: ${JSON.stringify(end)}\n\n`;
};
const HEARTBEAT = ':\n\n';

export class Stream {
  readonly who: StreamIdentity;
  private readonly res: StreamResponse;
  private readonly deps: StreamDeps;
  private state: 'open' | 'ending' | 'closed' = 'open';
  /** The serial chain: checks and writes, in order. */
  private chain: Promise<void> = Promise.resolve();
  /** Bytes of Deliveries on the chain, not yet written. */
  private queued = 0;
  /** Bumped at the end: links queued before it write nothing. */
  private generation = 0;
  private sweepPending = false;
  private expiry: Timer | undefined;
  private heartbeat: Timer | undefined;
  private grace: Timer | undefined;

  constructor(who: StreamIdentity, res: StreamResponse, deps: StreamDeps) {
    this.who = who;
    this.res = res;
    this.deps = deps;
  }

  get cid(): string {
    return this.who.cid;
  }

  get order(): OrderKey {
    return this.who.order;
  }

  get isOpen(): boolean {
    return this.state === 'open';
  }

  /** Writes the status and headers, and arms the expiry and the heartbeat (NP-ET-10). */
  open(headers: Readonly<Record<string, string>>): void {
    this.res.writeHead(200, {
      'Content-Type': 'text/event-stream; charset=utf-8',
      'Cache-Control': 'no-store',
      ...headers,
    });
    this.res.flushHeaders();
    this.res.setTimeout(0);
    this.res.on('close', () => this.closed());
    const remaining = this.who.expiresAt.getTime() - this.deps.clock.now().getTime();
    this.expiry = this.deps.scheduler.after(remaining, () => this.end('credential_expired'));
    this.armHeartbeat();
  }

  /** A Delivery's frame: checked, then written, on the chain; past the buffer, overflow. */
  offer(frame: string): void {
    if (this.state !== 'open') return;
    const bytes = Buffer.byteLength(frame, 'utf8');
    if (this.queued + this.res.writableLength + bytes > SEND_BUFFER_BYTES) {
      this.end('overflow');
      return;
    }
    this.queued += bytes;
    const generation = this.generation;
    this.chain = this.chain.then(async () => {
      if (generation !== this.generation) return;
      this.queued -= bytes;
      if (!(await this.admissible())) return;
      if (generation !== this.generation) return;
      this.write(frame);
    });
  }

  /** The sweep's check (BR-SR-02): expiry and revocation, on the chain, writing nothing. */
  check(): void {
    if (this.state !== 'open' || this.sweepPending) return;
    this.sweepPending = true;
    const generation = this.generation;
    this.chain = this.chain.then(async () => {
      this.sweepPending = false;
      if (generation !== this.generation) return;
      await this.admissible();
    });
  }

  /** Ends the stream with one `end` event; idempotent (BR-SM-07). */
  end(code: EndCode, reason?: string): void {
    if (this.state !== 'open') return;
    this.state = 'ending';
    this.generation += 1;
    this.queued = 0;
    this.expiry?.cancel();
    this.heartbeat?.cancel();
    this.deps.onEnded(this, reason === undefined ? { code } : { code, reason });
    if (!this.res.destroyed) this.res.end(endFrame(code));
    this.grace = this.deps.scheduler.after(END_GRACE_MS, () => {
      if (this.state !== 'closed') this.res.destroy();
    });
  }

  /** Resolves once every link queued so far has run (for tests and shutdown). */
  settled(): Promise<void> {
    return this.chain;
  }

  /** The check before each delivery (BR-SM-04): true when the Delivery may be written. */
  private async admissible(): Promise<boolean> {
    if (this.state !== 'open') return false;
    if (this.deps.clock.now().getTime() >= this.who.expiresAt.getTime()) {
      this.end('credential_expired');
      return false;
    }
    let answer;
    try {
      answer = await this.deps.revocation.isRevoked({
        environment: this.who.environment,
        cid: this.who.cid,
        agent: this.who.agent,
      });
    } catch {
      // No answer younger than B, and none readable: fail closed (BR-SR-05).
      this.end('unavailable', 'revocation_unreadable');
      return false;
    }
    if (answer !== 'not_revoked') {
      // The granularity goes to the log only (BR-SR-03).
      this.end('credential_refused', answer);
      return false;
    }
    return this.state === 'open';
  }

  private write(text: string): void {
    if (this.state !== 'open') return;
    this.res.write(text);
    this.armHeartbeat();
  }

  private armHeartbeat(): void {
    this.heartbeat?.cancel();
    this.heartbeat = this.deps.scheduler.after(HEARTBEAT_MS, () => this.write(HEARTBEAT));
  }

  /** The response closed: the client went away, or the end finished. */
  private closed(): void {
    if (this.state === 'closed') return;
    const wasOpen = this.state === 'open';
    this.state = 'closed';
    this.generation += 1;
    this.queued = 0;
    this.expiry?.cancel();
    this.heartbeat?.cancel();
    this.grace?.cancel();
    if (wasOpen) this.deps.onEnded(this, { code: undefined, reason: 'client_closed' });
  }
}
