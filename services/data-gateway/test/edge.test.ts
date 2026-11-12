// SPDX-License-Identifier: FSL-1.1-ALv2
//
// S3's edge on real listeners: TC-AC-063 (at most 64 requests in flight, as
// S2's throttle), TC-AC-071 (TLS 1.3 at the edge; TLS 1.3, verify-full to the
// store), TC-AC-072 (the logs name events, never a secret or a human).
import { execFileSync } from 'node:child_process';
import { mkdtempSync, readFileSync, rmSync } from 'node:fs';
import { request as httpsRequest } from 'node:https';
import { connect, type AddressInfo, type Socket } from 'node:net';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import type { TLSSocket } from 'node:tls';
import { poolConfig, Semaphore, type Timers } from '@soorma/service-kit';
import { afterAll, beforeAll, describe, expect, it } from 'vitest';
import {
  testEnvDatabase,
  type TestEnvDatabase,
} from '../../../packages/env-store/test/harness/database.ts';
import { seedCredentialRevocation } from '../../../packages/env-store/test/harness/seed.ts';
import { createEdgeApp } from '../src/apps.ts';
import { storeSettings } from '../src/main.ts';
import { SECURITY_EVENTS } from '../src/security-log.ts';
import {
  agentId,
  bootstrap,
  credentialFor,
  gateway,
  registered,
  renew,
  type Gateway,
} from './support.ts';

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
beforeAll(async () => {
  db = await testEnvDatabase();
});
afterAll(async () => {
  await db?.drop();
});

describe('TC-AC-063: S3 holds at most 64 requests in flight', () => {
  let g: Gateway;
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
    g = await gateway(db, { requests: permits });
    await g.edge.listen(0, '127.0.0.1');
    port = (g.edge.getHttpServer().address() as AddressInfo).port;
  });
  afterAll(async () => {
    await g?.close();
  });

  /** A bootstrap whose headers are sent, and whose body never finishes. */
  function halfRequest(): Socket {
    const socket = connect(port, '127.0.0.1');
    socket.on('error', () => undefined);
    socket.write(
      'POST /agent-credentials HTTP/1.1\r\nHost: localhost\r\nContent-Type: application/json\r\n' +
        'Soorma-Contract-Version: 0.1.0\r\nContent-Length: 1000\r\n\r\n{"agent":',
    );
    return socket;
  }

  /** A complete renewal with no credential; resolves to its raw response text. */
  function fullRequest(): Promise<string> {
    return new Promise((resolve, reject) => {
      const socket = connect(port, '127.0.0.1');
      let text = '';
      socket.on('data', (d) => (text += d.toString()));
      socket.on('end', () => resolve(text));
      socket.on('error', reject);
      socket.write(
        'POST /agent-credentials/current/renewal HTTP/1.1\r\nHost: localhost\r\n' +
          'Connection: close\r\nSoorma-Contract-Version: 0.1.0\r\n\r\n',
      );
    });
  }

  it('the 65th waits, then is 503 with Retry-After 5 and throttle.refused', async () => {
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
    expect(permits.available).toBe(64);
  });
});

describe('TC-AC-071: TLS 1.3 at S3’s edge, and to its store', () => {
  let dir: string;
  let g: Gateway;
  beforeAll(async () => {
    g = await gateway(db);
    dir = mkdtempSync(join(tmpdir(), 'soorma-tls-'));
    execFileSync(
      'openssl',
      [
        'req',
        '-x509',
        '-newkey',
        'ec',
        '-pkeyopt',
        'ec_paramgen_curve:P-256',
        '-nodes',
        '-keyout',
        join(dir, 'key.pem'),
        '-out',
        join(dir, 'cert.pem'),
        '-days',
        '1',
        '-subj',
        '/CN=localhost',
        '-addext',
        'subjectAltName=DNS:localhost,IP:127.0.0.1',
      ],
      { stdio: 'ignore' },
    );
  });
  afterAll(async () => {
    await g?.close();
    rmSync(dir, { recursive: true, force: true });
  });

  function call(
    port: number,
    ca: Buffer,
    options: { maxVersion?: 'TLSv1.2' | 'TLSv1.3' } = {},
  ): Promise<{ status: number; protocol: string | null }> {
    return new Promise((resolve, reject) => {
      const req = httpsRequest(
        {
          host: '127.0.0.1',
          servername: 'localhost',
          port,
          path: '/agent-credentials/current/renewal',
          method: 'POST',
          ca,
          agent: false,
          ...options,
          headers: { 'soorma-contract-version': '0.1.0' },
        },
        (res) => {
          const protocol = (res.socket as TLSSocket).getProtocol();
          res.resume();
          res.on('end', () => resolve({ status: res.statusCode ?? 0, protocol }));
        },
      );
      req.on('error', reject);
      req.end();
    });
  }

  it('the edge serves TLS 1.3 and refuses TLS 1.2', async () => {
    const pem = Buffer.concat([
      readFileSync(join(dir, 'key.pem')),
      readFileSync(join(dir, 'cert.pem')),
    ]);
    const app = await createEdgeApp(g.runtime, { pem });
    try {
      await app.listen(0, '127.0.0.1');
      const port = (app.getHttpServer().address() as AddressInfo).port;
      const ca = readFileSync(join(dir, 'cert.pem'));
      expect(await call(port, ca)).toEqual({ status: 401, protocol: 'TLSv1.3' });
      await expect(call(port, ca, { maxVersion: 'TLSv1.2' })).rejects.toThrow();
    } finally {
      await app.close();
    }
  });

  it('the store connection is S3’s own role over TLS 1.3, verify-full against the stack CA', () => {
    const ca = Buffer.from('CA');
    const settings = storeSettings(
      {
        organization: 'o1',
        project: 'p1',
        environment: 'e',
        edge: { port: 8443 },
        health: { port: 8080 },
        database: {
          host: 'env-db.e.soorma.internal',
          port: 5432,
          name: 'soorma_env',
          user: 'soorma_env_data',
        },
      },
      {
        edgeTls: Buffer.from('TLS'),
        databasePassword: 'data-e',
        databaseCa: ca,
        verifyKeys: [],
        signing: 'k1',
        counterSecret: Buffer.alloc(32),
      },
    );
    expect(settings.user).toBe('soorma_env_data');
    const pool = poolConfig(settings);
    expect(pool.ssl).toMatchObject({ rejectUnauthorized: true, minVersion: 'TLSv1.3', ca });
  });
});

describe('TC-AC-072: S3’s logs name events, never a secret or a human', () => {
  it('every line of each operation and refusal: a named event, no secret-derived value', async () => {
    const g = await gateway(db);
    try {
      const agent = agentId();
      const s = await registered(g, agent);
      const ok = await bootstrap(g, agent, s.value);
      const token = ok.body.credential as string;
      await renew(g, token);
      await bootstrap(g, agent, s.value.slice(0, -2) + 'zz');
      await bootstrap(g, agentId(), s.value);
      const c = await credentialFor(g);
      await seedCredentialRevocation(g.owner, ['o1', 'p1', 'e'], c.cid, g.clock.now());
      await renew(g, c.credential);
      await renew(g, 'soorma_ec_x.y.z');
      const events = g.log.events();
      expect(events.length).toBeGreaterThan(0);
      for (const e of events) {
        if ('event' in e) expect(SECURITY_EVENTS).toContain(e.event);
        for (const key of Object.keys(e))
          expect(['event', 'requestId', 'environment', 'agent', 'instance', 'code']).toContain(key);
      }
      for (const name of [
        'credential.issued',
        'credential.renewed',
        'bootstrap.refused',
        'renewal.refused',
      ])
        expect(g.log.named(name).length, name).toBeGreaterThan(0);
      const text = g.log.lines.join('\n');
      for (const secret of [s.value, s.id, token, c.credential, c.secret.value, c.secret.id])
        expect(text).not.toContain(secret);
      expect(text).not.toMatch(/soorma_rs_|soorma_ac_|pseudonym|principal|hp_/);
      expect(g.log.named('credential.issued')[0]).toMatchObject({
        environment: 'e',
        agent,
        instance: 'i-1',
      });
    } finally {
      await g.close();
    }
  });
});
