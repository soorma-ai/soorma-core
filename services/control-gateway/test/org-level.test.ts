// SPDX-License-Identifier: FSL-1.1-ALv2
//
// The real S1 caller against a stub of S1's internal listener over TLS 1.3,
// under a test CA (NP-EHA-04; TC-EHA-043, 060, 023). The stub checks every
// call's signature as S1 does (U2 P-06). Deadlines run on injected timers.
import { execFileSync } from 'node:child_process';
import { generateKeyPairSync, randomBytes, type KeyObject } from 'node:crypto';
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { createServer, type Server } from 'node:https';
import type { AddressInfo } from 'node:net';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import {
  Semaphore,
  thumbprint,
  UnavailableError,
  verifyInternalRequest,
  type Timers,
} from '@soorma/service-kit';
import { afterAll, beforeAll, describe, expect, it } from 'vitest';
import {
  OrgLevelClient,
  OrgLevelUnavailableError,
  parseJwks,
  parseSignInStatus,
} from '../src/org-level.ts';
import { organizationRing, TestClock } from './support.ts';

const NAME = 'org-gateway.soorma.internal';
let dir: string;

function openssl(args: string[]): void {
  execFileSync('openssl', args, { stdio: 'ignore' });
}

/** A CA, and a leaf it signs for `leafName` (serverAuth, the name as its SAN). */
function pki(tag: string, leafName: string): { ca: Buffer; key: Buffer; cert: Buffer } {
  const p = (f: string) => join(dir, `${tag}-${f}`);
  const ec = ['-newkey', 'ec', '-pkeyopt', 'ec_paramgen_curve:P-256', '-nodes'];
  openssl([
    'req',
    '-x509',
    ...ec,
    '-keyout',
    p('ca.key'),
    '-out',
    p('ca.pem'),
    '-days',
    '1',
    '-subj',
    `/CN=test ca ${tag}`,
    '-addext',
    'basicConstraints=critical,CA:TRUE',
    '-addext',
    'keyUsage=critical,keyCertSign',
  ]);
  openssl([
    'req',
    ...ec,
    '-keyout',
    p('leaf.key'),
    '-out',
    p('leaf.csr'),
    '-subj',
    `/CN=${leafName}`,
  ]);
  writeFileSync(p('leaf.ext'), `subjectAltName=DNS:${leafName}\nextendedKeyUsage=serverAuth\n`);
  openssl([
    'x509',
    '-req',
    '-in',
    p('leaf.csr'),
    '-CA',
    p('ca.pem'),
    '-CAkey',
    p('ca.key'),
    '-CAcreateserial',
    '-out',
    p('leaf.pem'),
    '-days',
    '1',
    '-extfile',
    p('leaf.ext'),
  ]);
  return {
    ca: readFileSync(p('ca.pem')),
    key: readFileSync(p('leaf.key')),
    cert: readFileSync(p('leaf.pem')),
  };
}

type Script = (path: string) => { status?: number; body?: string; hold?: boolean };

class StubS1 {
  server!: Server;
  port = 0;
  script: Script = () => ({ body: '{}' });
  readonly seen: string[] = [];
  readonly refused: string[] = [];
  readonly held: (() => void)[] = [];
  private readonly callerPublic: KeyObject;

  constructor(callerPublic: KeyObject) {
    this.callerPublic = callerPublic;
  }

  async listen(tls: { key: Buffer; cert: Buffer }): Promise<void> {
    const caller = { environment: 'e', kid: thumbprint(this.callerPublic), key: this.callerPublic };
    this.server = createServer(
      { key: tls.key, cert: tls.cert, minVersion: 'TLSv1.3' },
      (req, res) => {
        void (async () => {
          const target = req.url ?? '';
          const authorization = req.headers.authorization ? [req.headers.authorization] : [];
          const env = await verifyInternalRequest(
            { method: req.method ?? '', target, body: Buffer.alloc(0), authorization },
            { callerByKid: (kid) => (kid === caller.kid ? caller : undefined) },
            'o1',
            new Date(),
          );
          if (env !== 'e') {
            this.refused.push(target);
            res.writeHead(401).end();
            return;
          }
          this.seen.push(target);
          const answer = this.script(target);
          const send = () =>
            res
              .writeHead(answer.status ?? 200, { 'content-type': 'application/json' })
              .end(answer.body ?? '');
          if (answer.hold) this.held.push(send);
          else send();
        })();
      },
    );
    await new Promise<void>((r) => this.server.listen(0, '127.0.0.1', r));
    this.port = (this.server.address() as AddressInfo).port;
  }

  async close(): Promise<void> {
    for (const s of this.held.splice(0)) s();
    this.server.closeAllConnections();
    await new Promise<void>((r) => this.server.close(() => r()));
  }
}

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
    for (const c of due) c();
  }
}

let good: ReturnType<typeof pki>;
let otherCa: ReturnType<typeof pki>;
let wrongName: ReturnType<typeof pki>;
const caller = generateKeyPairSync('ed25519');
let stub: StubS1;

beforeAll(async () => {
  dir = mkdtempSync(join(tmpdir(), 'soorma-s1-stub-'));
  good = pki('good', NAME);
  otherCa = pki('other', NAME);
  wrongName = pki('name', 'elsewhere.soorma.internal');
  stub = new StubS1(caller.publicKey);
  await stub.listen(good);
});
afterAll(async () => {
  await stub?.close();
  rmSync(dir, { recursive: true, force: true });
});

function client(
  options: { ca?: Buffer; port?: number; timers?: ManualTimers; calls?: Semaphore } = {},
) {
  return new OrgLevelClient({
    environment: 'e',
    organization: 'o1',
    host: '127.0.0.1',
    port: options.port ?? stub.port,
    serverName: NAME,
    ca: options.ca ?? good.ca,
    callerKey: caller.privateKey,
    clock: new TestClock(new Date().toISOString()),
    calls:
      options.calls ??
      new Semaphore({ permits: 8, waitMs: 1000, reason: 's1_calls', retryAfterSeconds: 5 }),
    ...(options.timers ? { timers: options.timers } : {}),
  });
}

async function failure(p: Promise<unknown>): Promise<OrgLevelUnavailableError> {
  try {
    await p;
  } catch (error) {
    if (error instanceof OrgLevelUnavailableError) return error;
    throw error;
  }
  throw new Error('expected OrgLevelUnavailableError');
}

describe('the S1 caller: signed calls, exact answers (NP-EHA-04)', () => {
  it('answers A7, existence, and the verify keys, each call signed and its query encoded', async () => {
    const ring = organizationRing();
    const expiresAt = '2026-11-11T12:15:00.000Z';
    stub.script = (path) =>
      path.startsWith('/sign-ins/')
        ? { body: JSON.stringify({ status: 'live', expiresAt }) }
        : path.startsWith('/principals/exists')
          ? { body: '{"exists":true}' }
          : { body: JSON.stringify(ring.jwks()) };
    const c = client();
    try {
      expect(await c.signInStatus('a'.repeat(32))).toEqual({
        status: 'live',
        expiresAt: new Date(expiresAt),
      });
      expect(await c.principalExists({ organization: 'o1', principal: 'h+x@example.com' })).toBe(
        true,
      );
      expect(stub.seen).toContain(
        '/principals/exists?organization=o1&principal=h%2Bx%40example.com',
      );
      expect([...(await c.verifyKeys()).keys()]).toEqual([ring.signingKid]);
      expect(stub.refused).toEqual([]);
    } finally {
      c.close();
    }
  });
});

describe('TC-EHA-043: an unreachable or misbehaving S1 is unavailable, after one attempt', () => {
  it.each([
    ['a 500', () => ({ status: 500, body: '{}' }), 'status_500'],
    ['live without expiresAt', () => ({ body: '{"status":"live"}' }), 'shape'],
    ['an extra field', () => ({ body: '{"status":"ended","x":1}' }), 'shape'],
    [
      '65 KiB',
      () => ({ body: JSON.stringify({ status: 'ended', pad: 'x'.repeat(65 * 1024) }) }),
      'too_large',
    ],
    ['not JSON', () => ({ body: 'nope' }), 'not_json'],
  ])('%s', async (_name, script, cause) => {
    stub.script = script;
    const before = stub.seen.length;
    const c = client();
    try {
      const e = await failure(c.signInStatus('a'.repeat(32)));
      expect(e.failure).toBe(cause);
      expect(e.retryAfterSeconds).toBe(5);
      expect(stub.seen.length - before).toBe(1);
    } finally {
      c.close();
    }
  });

  it('a refused connection', async () => {
    const c = client({ port: 1 });
    try {
      expect(
        (await failure(c.principalExists({ organization: 'o1', principal: 'h' }))).failure,
      ).toBe('ECONNREFUSED');
    } finally {
      c.close();
    }
  });

  it('a certificate from another CA, or for another name, is refused before any call', async () => {
    for (const tls of [otherCa, wrongName]) {
      const s = new StubS1(caller.publicKey);
      await s.listen(tls);
      const c = client({ port: s.port, ca: tls === otherCa ? good.ca : wrongName.ca });
      try {
        await failure(c.signInStatus('a'.repeat(32)));
        expect(s.seen).toEqual([]);
      } finally {
        c.close();
        await s.close();
      }
    }
  });

  it('the 2-second deadline ends a call S1 never answers (injected timers)', async () => {
    stub.script = () => ({ hold: true });
    const timers = new ManualTimers();
    const c = client({ timers });
    try {
      const pending = failure(c.signInStatus('a'.repeat(32)));
      for (let i = 0; i < 200 && stub.held.length === 0; i++)
        await new Promise((r) => setTimeout(r, 5));
      timers.fire();
      expect((await pending).failure).toBe('deadline');
    } finally {
      c.close();
    }
  });
});

describe('TC-EHA-060: eight S1 calls in flight; the key fetch is not throttled', () => {
  it('a ninth call waits for a permit; a key fetch completes while eight are held', async () => {
    for (const s of stub.held.splice(0)) s(); // nothing left from an earlier test
    const ring = organizationRing();
    stub.script = (path) =>
      path === '/verify-keys' ? { body: JSON.stringify(ring.jwks()) } : { hold: true };
    const timers = new ManualTimers();
    const calls = new Semaphore({
      permits: 8,
      waitMs: 1000,
      reason: 's1_calls',
      retryAfterSeconds: 5,
      timers,
    });
    const c = client({ calls });
    try {
      const held = Array.from({ length: 8 }, () =>
        c.signInStatus('b'.repeat(32)).catch(() => undefined),
      );
      for (let i = 0; i < 400 && stub.held.length < 8; i++)
        await new Promise((r) => setTimeout(r, 5));
      expect(stub.held.length).toBe(8);
      expect((await c.verifyKeys()).size).toBe(1);
      const ninth = c.signInStatus('c'.repeat(32)).catch((e: unknown) => e);
      for (let i = 0; i < 100 && calls.waiting === 0; i++)
        await new Promise((r) => setTimeout(r, 5));
      expect(calls.waiting).toBe(1);
      for (const [id, cb] of timers.pending) {
        // Only the permit wait's timer: the in-flight calls' deadlines are left alone.
        if (calls.waiting === 1) {
          timers.pending.delete(id);
          cb();
          break;
        }
      }
      const error = await ninth;
      expect(error).toBeInstanceOf(UnavailableError);
      expect((error as UnavailableError).message).toBe('s1_calls');
      for (const s of stub.held.splice(0)) s();
      await Promise.all(held);
    } finally {
      c.close();
    }
  });
});

describe('the answers S2 accepts, exactly', () => {
  it('A7: live with a parseable expiry, ended, unknown; nothing else', () => {
    expect(parseSignInStatus({ status: 'ended' })).toEqual({ status: 'ended' });
    expect(parseSignInStatus({ status: 'unknown' })).toEqual({ status: 'unknown' });
    expect(parseSignInStatus({ status: 'live', expiresAt: 'not a date' })).toBeUndefined();
    expect(parseSignInStatus({ status: 'gone' })).toBeUndefined();
    expect(parseSignInStatus([])).toBeUndefined();
  });

  it('a JWKS: Ed25519 public keys whose kid is their thumbprint, at least one, no private part', () => {
    const ring = organizationRing();
    const jwks = ring.jwks();
    expect(parseJwks(jwks)?.size).toBe(1);
    expect(parseJwks({ keys: [] })).toBeUndefined();
    expect(parseJwks({ keys: [{ ...jwks.keys[0], kid: 'other' }] })).toBeUndefined();
    expect(
      parseJwks({ keys: [{ ...jwks.keys[0], d: randomBytes(32).toString('base64url') }] }),
    ).toBeUndefined();
  });
});
