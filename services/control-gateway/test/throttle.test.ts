// SPDX-License-Identifier: FSL-1.1-ALv2
//
// The request throttle on a real listener (NP-EHA-05; NFR-EHA-04): permits
// taken before the body is read, released once on response or abort. The
// permit wait runs on injected timers, so no test waits for real time.
import { connect, type Socket } from 'node:net';
import type { AddressInfo } from 'node:net';
import { Semaphore, type Timers } from '@soorma/service-kit';
import { afterAll, beforeAll, describe, expect, it } from 'vitest';
import {
  testEnvDatabase,
  type TestEnvDatabase,
} from '../../../packages/env-store/test/harness/database.ts';
import { logUnavailable } from '../src/apps.ts';
import { OrgLevelUnavailableError } from '../src/org-level.ts';
import { UnavailableError } from '@soorma/service-kit';
import { gateway, type Gateway } from './support.ts';

/** Timers fired by hand: `fire()` runs every pending callback. */
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
  for (let i = 0; i < 400; i++) {
    if (condition()) return;
    await new Promise((r) => setImmediate(r));
    await new Promise((r) => setTimeout(r, 5));
  }
  throw new Error(`timed out waiting for ${label}`);
};

let db: TestEnvDatabase;
let g: Gateway;
let timers: ManualTimers;
let permits: Semaphore;
let port: number;
beforeAll(async () => {
  db = await testEnvDatabase();
  timers = new ManualTimers();
  permits = new Semaphore({
    permits: 64,
    waitMs: 1000,
    reason: 'requests',
    retryAfterSeconds: 5,
    timers,
  });
  g = await gateway(db, { requests: permits });
  await g.edge.listen(0, '127.0.0.1');
  port = (g.edge.getHttpServer().address() as AddressInfo).port;
});
afterAll(async () => {
  await g?.close();
  await db?.drop();
});

/** A request whose headers are sent, and whose body never finishes. */
function halfRequest(): Socket {
  const socket = connect(port, '127.0.0.1');
  socket.on('error', () => undefined);
  socket.write(
    'POST /grants HTTP/1.1\r\nHost: localhost\r\nContent-Type: application/json\r\n' +
      'Soorma-Contract-Version: 0.1.0\r\nContent-Length: 1000\r\n\r\n{"target":',
  );
  return socket;
}

/** A complete request; resolves to its raw response text. */
function fullRequest(): Promise<string> {
  return new Promise((resolve, reject) => {
    const socket = connect(port, '127.0.0.1');
    let text = '';
    socket.on('data', (d) => (text += d.toString()));
    socket.on('end', () => resolve(text));
    socket.on('error', reject);
    socket.write(
      'POST /environment-credentials HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n' +
        'Soorma-Contract-Version: 0.1.0\r\n\r\n',
    );
  });
}

describe('TC-EHA-059: aborted requests release their permits exactly once (the user’s test)', () => {
  it('64 requests aborted mid-body release all 64; the next request gets a permit', async () => {
    const sockets = Array.from({ length: 64 }, () => halfRequest());
    await until(() => permits.available === 0, '64 permits held');
    for (const s of sockets) s.destroy();
    await until(() => permits.available === 64, 'all 64 released');
    const r = await fullRequest();
    expect(r).toMatch(/^HTTP\/1\.1 401/); // a permit, then the check order (no credential)
    await until(() => permits.available === 64, 'released after the answer');
    expect(permits.available).toBe(64);
  });

  it('an answered request releases once: the count returns to 64, never 65', async () => {
    for (let i = 0; i < 5; i++) await fullRequest();
    await until(() => permits.available === 64, 'released');
    expect(permits.available).toBe(64);
  });

  it('a request aborted while it waits leaves the queue and holds nothing', async () => {
    const held = Array.from({ length: 64 }, () => halfRequest());
    await until(() => permits.available === 0, '64 held');
    const waiter = halfRequest();
    await until(() => permits.waiting === 1, 'one waiter');
    waiter.destroy();
    await until(() => permits.waiting === 0, 'the waiter left');
    for (const s of held) s.destroy();
    await until(() => permits.available === 64, 'released');
  });
});

describe('TC-EHA-058: the 65th request is refused after its wait', () => {
  it('503, Retry-After 5, throttle.refused; a waiter proceeds when a permit frees', async () => {
    const held = Array.from({ length: 64 }, () => halfRequest());
    await until(() => permits.available === 0, '64 held');
    const refused = fullRequest();
    await until(() => permits.waiting === 1, 'the 65th waits');
    timers.fire(); // its 1-second wait ends
    const text = await refused;
    expect(text).toMatch(/^HTTP\/1\.1 503/);
    expect(text).toMatch(/retry-after: 5/i);
    expect(g.log.named('throttle.refused').at(-1)?.code).toBe('requests');
    const waiting = fullRequest();
    await until(() => permits.waiting === 1, 'another waits');
    held[0]!.destroy();
    expect(await waiting).toMatch(/^HTTP\/1\.1 401/);
    for (const s of held) s.destroy();
    await until(() => permits.available === 64, 'released');
  });
});

describe('TC-EHA-060 (the log half): each 503 logs its event', () => {
  it('maps S1 failures, the S1-call throttle, missing keys, and the store to their events', () => {
    const events: [string, unknown][] = [];
    const rt = {
      log: {
        event: (name: string, _id: unknown, f: { code?: unknown } = {}) =>
          events.push([name, f.code]),
      },
    };
    const log = (e: UnavailableError) => logUnavailable(rt as never, 'r', e);
    log(new OrgLevelUnavailableError('signInStatus', 'deadline'));
    log(new UnavailableError('s1_calls', 5));
    log(new UnavailableError('no verify keys held', 5));
    log(new UnavailableError('the env store cannot be reached or refused the statement'));
    expect(events).toEqual([
      ['orglevel.unavailable', 'signInStatus'],
      ['throttle.refused', 's1_calls'],
      ['orglevel.unavailable', 'verify_keys'],
      ['store.unavailable', undefined],
    ]);
  });
});
