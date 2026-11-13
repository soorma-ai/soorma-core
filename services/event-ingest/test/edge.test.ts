// SPDX-License-Identifier: FSL-1.1-ALv2
//
// S4's edge on real listeners: TC-ET-061 (the throttle, and a stream holds no
// permit), TC-ET-055 (the open-stream cap), TC-ET-059 (the stream outlives the
// server's ordinary timeouts), TC-ET-068 (the logs name events, never a
// secret, a token, a seal, an envelope, a payload, a trace value, or a human).
import { connect, type Socket } from 'node:net';
import { Semaphore, type Timers } from '@soorma/service-kit';
import { afterAll, beforeAll, describe, expect, it } from 'vitest';
import {
  testEnvDatabase,
  type TestEnvDatabase,
} from '../../../packages/env-store/test/harness/database.ts';
import { SECURITY_EVENTS } from '../src/security-log.ts';
import { MAX_STREAMS } from '../src/settings.ts';
import {
  agentWith,
  credential,
  draft,
  flush,
  ingest,
  publish,
  PUBLISHER,
  records,
  subscribe,
  SUBSCRIBER,
  TRACEPARENT,
  type Ingest,
  type SseClient,
} from './support.ts';

/** Timers fired by hand: `fire()` runs every pending callback (as S3's test). */
class ManualTimers implements Timers {
  private next = 0;
  readonly pending = new Map<number, () => void>();
  set(callback: () => void): unknown {
    const id = this.next++;
    this.pending.set(id, callback);
    return id;
  }
  clear(handle: unknown): void {
    this.pending.delete(handle as number);
  }
  fire(): void {
    const due = [...this.pending.values()];
    this.pending.clear();
    for (const callback of due) callback();
  }
}

const until = async (condition: () => boolean, label: string): Promise<void> => {
  for (let i = 0; i < 800; i++) {
    if (condition()) return;
    await new Promise((r) => setImmediate(r));
    await new Promise((r) => setTimeout(r, 5));
  }
  throw new Error(`timed out waiting for ${label}`);
};

let db: TestEnvDatabase;
beforeAll(async () => {
  db = await testEnvDatabase();
});
afterAll(async () => {
  await db?.drop();
});

describe('TC-ET-061: at most 64 requests in flight, and a stream holds no permit', () => {
  let g: Ingest;
  let timers: ManualTimers;
  let permits: Semaphore;
  let port: number;
  beforeAll(async () => {
    timers = new ManualTimers();
    permits = new Semaphore({
      permits: 64,
      waitMs: 1000,
      reason: 'requests',
      retryAfterSeconds: 5,
      timers,
    });
    g = await ingest(db, { requests: permits });
    port = Number(new URL(await g.listen()).port);
  });
  afterAll(async () => {
    await g?.close();
  });

  function halfRequest(): Socket {
    const socket = connect(port, '127.0.0.1');
    socket.on('error', () => undefined);
    socket.write(
      'POST /events HTTP/1.1\r\nHost: localhost\r\nContent-Type: application/json\r\n' +
        'Content-Length: 1000\r\n\r\n{"draft":',
    );
    return socket;
  }

  function fullRequest(): Promise<string> {
    return new Promise((resolve, reject) => {
      const socket = connect(port, '127.0.0.1');
      let text = '';
      socket.on('data', (d) => (text += d.toString()));
      socket.on('end', () => resolve(text));
      socket.on('error', reject);
      socket.write('POST /events HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n');
    });
  }

  it('the 65th waits, then is 503 with Retry-After 5 and throttle.refused; aborts free each permit once', async () => {
    const held = Array.from({ length: 64 }, () => halfRequest());
    await until(() => permits.available === 0, '64 held');
    const refused = fullRequest();
    await until(() => permits.waiting === 1, 'the 65th waits');
    timers.fire();
    const text = await refused;
    expect(text).toMatch(/^HTTP\/1\.1 503/);
    expect(text).toMatch(/retry-after: 5/i);
    expect(g.log.named('throttle.refused').at(-1)?.code).toBe('requests');
    for (const s of held) s.destroy();
    await until(() => permits.available === 64, 'every permit released once');
    expect(await fullRequest()).toMatch(/^HTTP\/1\.1 401/);
    await until(() => permits.available === 64, 'released after the answer');
  });

  it('with 64 streams open, a publish takes a permit at once', async () => {
    const b = await agentWith(g, SUBSCRIBER);
    const open: SseClient[] = [];
    for (let i = 0; i < 64; i++) {
      const s = await subscribe(g, await credential(g, b.agent));
      expect(s.status).toBe(200);
      open.push(s);
    }
    expect(permits.available).toBe(64);
    const a = await agentWith(g, PUBLISHER);
    expect((await publish(g, a)).status).toBe(202);
    expect(permits.waiting).toBe(0);
    for (const s of open) s.destroy();
  });
});

describe('TC-ET-055: the open-stream cap', () => {
  it('the 257th is unavailable with no record; a subscribe of an open lineage supersedes', async () => {
    const g = await ingest(db);
    await g.listen();
    try {
      const b = await agentWith(g, SUBSCRIBER);
      const open: SseClient[] = [];
      for (let i = 0; i < MAX_STREAMS; i++) {
        const s = await subscribe(g, await credential(g, b.agent));
        expect(s.status).toBe(200);
        open.push(s);
      }
      expect(g.runtime.streams.size).toBe(256);
      const before = (await records(g, b.agent)).length;
      const extra = await credential(g, b.agent);
      const refused = await subscribe(g, extra);
      expect(refused.status).toBe(503);
      expect(refused.headers['retry-after']).toBe('5');
      expect(g.log.named('throttle.refused').at(-1)?.code).toBe('streams');
      expect((await records(g, b.agent)).length).toBe(before);
      // A renewal of the first lineage: the same cid, so it replaces, not adds.
      const first = open[0]!;
      const again = await subscribe(g, await credential(g, b.agent, { cid: firstCid(g) }));
      expect(again.status).toBe(200);
      await first.until(() => first.ended() !== undefined);
      expect(first.ended()).toEqual({ code: 'superseded' });
      expect(g.runtime.streams.size).toBe(256);
      for (const s of [...open, refused, again]) s.destroy();
    } finally {
      await g.close();
    }
  });
});

/** The lineage of the earliest open stream. */
function firstCid(g: Ingest): string {
  return g.runtime.streams.list()[0]!.cid;
}

describe('TC-ET-059: the stream route outlives the server’s ordinary timeouts', () => {
  it('an idle stream stays open past the idle timeout; a stalled publish is closed by it', async () => {
    const g = await ingest(db);
    const port = Number(new URL(await g.listen()).port);
    try {
      g.edge.getHttpServer().setTimeout(300);
      const s = await subscribe(g, await agentWith(g, SUBSCRIBER));
      const stalled = connect(port, '127.0.0.1');
      let stalledClosed = false;
      stalled.on('close', () => (stalledClosed = true));
      stalled.on('error', () => undefined);
      stalled.write('POST /events HTTP/1.1\r\nHost: localhost\r\nContent-Length: 100\r\n\r\n{');
      await new Promise((r) => setTimeout(r, 900));
      expect(stalledClosed).toBe(true);
      expect(s.closed).toBe(false);
      await publish(g, await agentWith(g, PUBLISHER));
      await flush(g);
      await s.until(() => s.deliveries().length === 1);
      s.destroy();
    } finally {
      await g.close();
    }
  });
});

describe('TC-ET-068: S4’s logs carry no secret, token, seal, envelope, payload, trace value, or human', () => {
  it('every line is JSON with a named event or notice; none carries what it must not', async () => {
    const g = await ingest(db);
    await g.listen();
    try {
      const a = await agentWith(g, PUBLISHER);
      const b = await agentWith(g, SUBSCRIBER);
      const s = await subscribe(g, b);
      const marker = 'payload-marker-7f3a';
      await publish(g, a, { marker });
      await flush(g);
      await s.until(() => s.deliveries().length === 1);
      const { seal } = s.deliveries()[0]!;
      await publish(g, a, {}, { draft: draft({ scope: {} }) });
      await publish(g, 'soorma_ec_AAAA.BBBB.CCCC');
      s.destroy();
      await new Promise((r) => setTimeout(r, 50));
      for (const line of g.log.lines) {
        const entry = JSON.parse(line) as Record<string, unknown>;
        const name = entry.event ?? entry.notice;
        expect(typeof name).toBe('string');
        if (entry.event !== undefined)
          expect(SECURITY_EVENTS).toContain(entry.event as (typeof SECURITY_EVENTS)[number]);
        for (const forbidden of [a.token, b.token, seal, marker, TRACEPARENT, 'actorChain'])
          expect(line).not.toContain(forbidden);
        expect(Object.keys(entry)).not.toContain('principal');
        expect(Object.keys(entry)).not.toContain('pseudonym');
      }
      expect(g.log.named('event.published').length).toBe(1);
      expect(g.log.named('envelope.refused').at(-1)).toMatchObject({
        code: 'stamped_field_set',
        agent: a.agent,
      });
    } finally {
      await g.close();
    }
  });
});
