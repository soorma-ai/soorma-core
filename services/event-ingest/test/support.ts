// SPDX-License-Identifier: FSL-1.1-ALv2
//
// S4's test harness: the real runtime over a test environment store, as S4's
// own role soorma_env_ingest (D-ID-ET-04), with an injected clock, a manual
// scheduler, and a captured log. Requests go through the real edge
// application, so the check order, the filter, and the throttle hooks are
// S4's own: Fastify's inject for a refusal or a publish, and a real listener
// (plain HTTP, port 0) for a stream, read as server-sent events.
//
// Agent credentials are minted here with a test signing key, as S3 would
// mint them; S4 holds only the verify half (D-ET-30). Registrations are
// seeded as the store's owner; revocation through env-store's test-only
// fixture (D-CG-AC-10). Forwarded envelopes come from real Deliveries, or are
// sealed with E's seal ring through U3's test helpers (TC-ET-019).
import { generateKeyPairSync, randomBytes } from 'node:crypto';
import { request as httpRequest, type IncomingMessage } from 'node:http';
import type { AddressInfo } from 'node:net';
import type { NestFastifyApplication } from '@nestjs/platform-fastify';
import { loadSealKeyRing, type SealKeyRing } from '@soorma/authority';
import {
  loadEnvironmentKeyRing,
  loadVerifyKeyRing,
  mintAgentCredential,
  type EnvironmentKeyRing,
  type VerifyKeyRing,
} from '@soorma/credentials';
import { connectEnvStore, newRecordId } from '@soorma/env-store';
import { isRawJson } from '@soorma/jcs';
import { generateRegistrationSecret } from '@soorma/registry';
import { asSecretBytes, Semaphore, type Clock, type Store } from '@soorma/service-kit';
import type { components } from '@soorma/contract/types/components';
import type { LightMyRequestResponse } from 'fastify';
import type { TestEnvDatabase } from '../../../packages/env-store/test/harness/database.ts';
import { ENV_INGEST } from '../../../packages/env-store/test/harness/roles.ts';
import {
  seedAgentRevocation,
  seedCredentialRevocation,
} from '../../../packages/env-store/test/harness/seed.ts';
import { createEdgeApp } from '../src/apps.ts';
import type { Channel } from '../src/channel/channel.ts';
import { assembleRuntime, type CacheFactories, type Runtime } from '../src/runtime.ts';
import type { Scheduler, Timer } from '../src/scheduler.ts';
import { SecurityLog, type LogSink } from '../src/security-log.ts';
import { PERMIT_WAIT_MS, REQUEST_PERMITS, RETRY_AFTER_SECONDS } from '../src/settings.ts';

export const E = Object.freeze({ organization: 'o1', project: 'p1', environment: 'e' });
export const E2 = Object.freeze({ organization: 'o1', project: 'p1', environment: 'e2' });
export const SPONSOR = 'h@example.com';
export const TRACEPARENT = '00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01';
export const MINUTE = 60_000;
export const L = 15 * MINUTE;

export type Env = { organization: string; project: string; environment: string };
export const envParts = (env: Env): string[] => [env.organization, env.project, env.environment];

export class TestClock implements Clock {
  ms: number;
  constructor(iso = '2026-11-13T12:00:00Z') {
    this.ms = Date.parse(iso);
  }
  now(): Date {
    return new Date(this.ms);
  }
}

/**
 * A manual scheduler driven with the test clock (NP-ET-12): `advance` moves
 * the clock and runs every timer that falls due, in time order.
 */
export class ManualScheduler implements Scheduler {
  private readonly clock: TestClock;
  private timers: { at: number; every?: number; fn: () => void; live: boolean }[] = [];

  constructor(clock: TestClock) {
    this.clock = clock;
  }

  after(ms: number, fn: () => void): Timer {
    const t = { at: this.clock.ms + Math.max(0, ms), fn, live: true };
    this.timers.push(t);
    return { cancel: () => (t.live = false) };
  }

  every(ms: number, fn: () => void): Timer {
    const t = { at: this.clock.ms + ms, every: ms, fn, live: true };
    this.timers.push(t);
    return { cancel: () => (t.live = false) };
  }

  /** Moves time forward by `ms`, running each timer as its moment arrives. */
  advance(ms: number): void {
    const until = this.clock.ms + ms;
    for (;;) {
      this.timers = this.timers.filter((t) => t.live);
      const due = this.timers.filter((t) => t.at <= until).sort((a, b) => a.at - b.at)[0];
      if (!due) break;
      this.clock.ms = Math.max(this.clock.ms, due.at);
      if (due.every === undefined) due.live = false;
      else due.at += due.every;
      due.fn();
    }
    this.clock.ms = until;
  }
}

export class CapturedLog implements LogSink {
  readonly lines: string[] = [];
  log(message: unknown): void {
    this.lines.push(JSON.stringify(message));
  }
  error(message: unknown): void {
    this.lines.push(JSON.stringify(message));
  }
  events(): Record<string, unknown>[] {
    return this.lines.map((l) => JSON.parse(l) as Record<string, unknown>);
  }
  named(event: string): Record<string, unknown>[] {
    return this.events().filter((e) => e.event === event);
  }
}

/** An agent key pair: the signing ring S3 would hold, and S4's verify-only ring. */
export interface AgentKeys {
  signing: EnvironmentKeyRing;
  verify: VerifyKeyRing;
}

export function agentKeys(kid = 'k1'): AgentKeys {
  const { privateKey, publicKey } = generateKeyPairSync('ed25519');
  const signing = loadEnvironmentKeyRing({
    signing: kid,
    verify: [
      {
        name: kid,
        pem: asSecretBytes(Buffer.from(privateKey.export({ format: 'pem', type: 'pkcs8' }))),
      },
    ],
  });
  const verify = loadVerifyKeyRing({
    verify: [
      {
        name: kid,
        pem: asSecretBytes(Buffer.from(publicKey.export({ format: 'pem', type: 'spki' }))),
      },
    ],
  });
  return { signing, verify };
}

/** E's seal ring: one 256-bit key. */
export const sealRing = (): SealKeyRing =>
  loadSealKeyRing({ current: 's1', keys: [{ id: 's1', key: randomBytes(32) }] });

/** The test store as S4's own role. */
export function ingestStore(db: TestEnvDatabase): Store {
  return connectEnvStore({ ...db.settings, user: ENV_INGEST, password: db.info.ingestPassword });
}

export interface Ingest {
  runtime: Runtime;
  edge: NestFastifyApplication;
  log: CapturedLog;
  clock: TestClock;
  scheduler: ManualScheduler;
  keys: AgentKeys;
  seal: SealKeyRing;
  /** The store S4 runs over, as soorma_env_ingest. */
  store: Store;
  /** A client as the store's owner, for seeding and inspection. */
  owner: Awaited<ReturnType<TestEnvDatabase['migrator']>>;
  /** The edge's base URL once `listen()` has run (plain HTTP). */
  url(): string;
  listen(): Promise<string>;
  close(): Promise<void>;
}

export async function ingest(
  db: TestEnvDatabase,
  options: {
    store?: Store;
    requests?: Semaphore;
    keys?: AgentKeys;
    seal?: SealKeyRing;
    environment?: Env;
    clock?: TestClock;
    channel?: Channel;
    factories?: CacheFactories;
  } = {},
): Promise<Ingest> {
  const clock = options.clock ?? new TestClock();
  const scheduler = new ManualScheduler(clock);
  const captured = new CapturedLog();
  const environment = options.environment ?? E;
  const log = new SecurityLog(captured, environment.environment);
  const keys = options.keys ?? agentKeys();
  const seal = options.seal ?? sealRing();
  const own = options.store === undefined;
  const store = options.store ?? ingestStore(db);
  const runtime = assembleRuntime({
    environment,
    store,
    ring: keys.verify,
    sealKeys: seal,
    clock,
    scheduler,
    log,
    requests:
      options.requests ??
      new Semaphore({
        permits: REQUEST_PERMITS,
        waitMs: PERMIT_WAIT_MS,
        reason: 'requests',
        retryAfterSeconds: RETRY_AFTER_SECONDS,
      }),
    ...(options.channel ? { channel: options.channel } : {}),
    ...(options.factories ? { factories: options.factories } : {}),
  });
  runtime.start();
  const edge = await createEdgeApp(runtime);
  const owner = await db.migrator();
  let base: string | undefined;
  return {
    runtime,
    edge,
    log: captured,
    clock,
    scheduler,
    keys,
    seal,
    store,
    owner,
    url: () => {
      if (!base) throw new Error('listen() first');
      return base;
    },
    async listen() {
      await edge.listen(0, '127.0.0.1');
      const { port } = edge.getHttpServer().address() as AddressInfo;
      base = `http://127.0.0.1:${port}`;
      return base;
    },
    async close() {
      runtime.streams.endAll('unavailable');
      // The ended streams' grace timers: run them, so no socket outlives the test.
      scheduler.advance(10_000);
      await edge.close();
      runtime.stop();
      await owner.end();
      if (own) await store.close();
    },
  };
}

/** A unique logical agent identifier. */
export const agentId = (): string => `a-${newRecordId()}`;

/** What a seeded registration holds (U5's columns). */
export interface RegistrationSpec {
  standing?: string[];
  declaration?: string[];
  autonomy?: boolean;
  env?: Env;
  sponsor?: string;
}

/** A registration of `agent`, seeded as the owner. */
export async function registered(
  g: Ingest,
  agent: string,
  spec: RegistrationSpec = {},
): Promise<void> {
  const env = spec.env ?? g.runtime.environment;
  await g.owner.query(
    `INSERT INTO registrations (organization, project, environment, agent, sponsor,
       ceiling_snapshot, standing_permissions, re_broadening_declaration, autonomy_declared,
       registered_at, state)
     VALUES ($1, $2, $3, $4, $5, $6, $6, $7, $8, $9, 'registered')`,
    [
      ...envParts(env),
      agent,
      spec.sponsor ?? SPONSOR,
      spec.standing ?? [],
      spec.declaration ?? [],
      spec.autonomy ?? true,
      g.clock.now(),
    ],
  );
}

/** An instance's credential, as S3 would mint it for `env` with `keys`. */
export interface Credential {
  agent: string;
  instance: string;
  cid: string;
  token: string;
  expiresAt: Date;
}

export async function credential(
  g: Ingest,
  agent: string,
  options: {
    instance?: string;
    cid?: string;
    env?: Env;
    keys?: AgentKeys;
    issuedAt?: Date;
    lifetimeMs?: number;
  } = {},
): Promise<Credential> {
  const instance = options.instance ?? 'i-1';
  const cid = options.cid ?? newRecordId();
  const issuedAt = options.issuedAt ?? g.clock.now();
  const expiresAt = new Date(issuedAt.getTime() + (options.lifetimeMs ?? L));
  const token = await mintAgentCredential(
    {
      environment: options.env ?? g.runtime.environment,
      agent,
      instance,
      cid,
      jti: newRecordId(),
      issuedAt,
      expiresAt,
    },
    (options.keys ?? g.keys).signing,
  );
  return { agent, instance, cid, token, expiresAt };
}

/** A registered agent with `standing`, and an instance's live credential. */
export async function agentWith(
  g: Ingest,
  standing: string[],
  spec: Omit<RegistrationSpec, 'standing'> & { instance?: string } = {},
): Promise<Credential> {
  const agent = agentId();
  await registered(g, agent, { ...spec, standing });
  return credential(g, agent, spec.instance === undefined ? {} : { instance: spec.instance });
}

export const PUBLISHER = ['event:publish'];
export const SUBSCRIBER = ['event:subscribe'];

/**
 * Revokes a lineage. Its credential record is written first, as S3 would have
 * at bootstrap (with a registration secret): a revocation names a record.
 */
export async function revokeCredential(g: Ingest, c: Credential, env: Env = E): Promise<void> {
  const secret = generateRegistrationSecret();
  const at = g.clock.now();
  await g.owner.query(
    `INSERT INTO registration_secrets (id, organization, project, environment, registration,
       issuer, digest, issued_at, state)
     VALUES ($1, $2, $3, $4, $5, $6, $7, $8, 'active')`,
    [secret.id, ...envParts(env), c.agent, SPONSOR, secret.digest, at],
  );
  await g.owner.query(
    `INSERT INTO agent_credentials (id, organization, project, environment, agent, instance,
       secret, issued_at, lineage_ends_at, expires_at)
     VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
     ON CONFLICT (id) DO NOTHING`,
    [c.cid, ...envParts(env), c.agent, c.instance, secret.id, at, c.expiresAt, c.expiresAt],
  );
  await seedCredentialRevocation(g.owner, envParts(env), c.cid, at);
}

export async function revokeAgent(g: Ingest, agent: string, env: Env = E): Promise<void> {
  await seedAgentRevocation(g.owner, envParts(env), agent, g.clock.now());
}

/** A draft: version 0.1.0 and a traceparent, plus `extra`. */
export function draft(extra: Record<string, unknown> = {}): Record<string, unknown> {
  return { clientContractVersion: '0.1.0', traceContext: { traceparent: TRACEPARENT }, ...extra };
}

export interface Response {
  status: number;
  headers: Record<string, string | string[] | number | undefined>;
  body: any;
  text: string;
}

function wrap(r: LightMyRequestResponse): Response {
  const text = r.body;
  let body: unknown;
  try {
    body = text.length > 0 ? JSON.parse(text) : undefined;
  } catch {
    body = undefined;
  }
  return { status: r.statusCode, headers: r.headers, body, text };
}

export const PUBLISH = '/events';
export const SUBSCRIBE = '/subscriptions';

/** One request through Fastify's inject: for refusals and publishes, never a stream. */
export async function send(
  app: NestFastifyApplication,
  url: string,
  options: {
    credential?: string;
    body?: unknown;
    headers?: Record<string, string>;
  } = {},
): Promise<Response> {
  const r = await app
    .getHttpAdapter()
    .getInstance()
    .inject({
      method: 'POST',
      url,
      headers: {
        ...(options.body === undefined ? {} : { 'content-type': 'application/json' }),
        ...(options.credential === undefined
          ? {}
          : { authorization: `Bearer ${options.credential}` }),
        ...options.headers,
      },
      ...(options.body === undefined
        ? {}
        : {
            payload: typeof options.body === 'string' ? options.body : JSON.stringify(options.body),
          }),
    });
  return wrap(r);
}

/** A publish: `{ draft, payload }`, or the raw text given. */
export function publish(
  g: Ingest,
  c: Credential | string,
  payload: unknown = { k: 'v' },
  options: { draft?: Record<string, unknown>; raw?: string; headers?: Record<string, string> } = {},
): Promise<Response> {
  return send(g.edge, PUBLISH, {
    credential: typeof c === 'string' ? c : c.token,
    body: options.raw ?? { draft: options.draft ?? draft(), payload },
    ...(options.headers ? { headers: options.headers } : {}),
  });
}

/** A subscribe refused before its stream (through inject: a 200 would never end). */
export function subscribeRefused(
  g: Ingest,
  c: Credential | string,
  options: { draft?: Record<string, unknown>; raw?: string; headers?: Record<string, string> } = {},
): Promise<Response> {
  return send(g.edge, SUBSCRIBE, {
    credential: typeof c === 'string' ? c : c.token,
    body: options.raw ?? { draft: options.draft ?? draft() },
    ...(options.headers ? { headers: options.headers } : {}),
  });
}

/** One server-sent event as read off the wire. */
export interface SseEvent {
  event: string;
  data: string;
}

/**
 * An open stream, read over a real connection: every raw chunk is kept, and
 * parsed into events (`delivery`, `end`) and comments (heartbeats).
 */
export class SseClient {
  /** Every stream read in this test file, for checks across them all. */
  static readonly all: SseClient[] = [];
  readonly status: number;
  readonly headers: IncomingMessage['headers'];
  readonly raw: string[] = [];
  readonly events: SseEvent[] = [];
  comments = 0;
  closed = false;
  private readonly res: IncomingMessage;
  private buffer = '';
  private waiters: (() => void)[] = [];

  constructor(res: IncomingMessage) {
    this.res = res;
    SseClient.all.push(this);
    this.status = res.statusCode ?? 0;
    this.headers = res.headers;
    res.setEncoding('utf8');
    res.on('data', (chunk: string) => {
      this.raw.push(chunk);
      this.buffer += chunk;
      let at: number;
      while ((at = this.buffer.indexOf('\n\n')) !== -1) {
        const block = this.buffer.slice(0, at);
        this.buffer = this.buffer.slice(at + 2);
        if (block.startsWith(':')) {
          this.comments += 1;
          continue;
        }
        const event = { event: '', data: '' };
        for (const line of block.split('\n')) {
          if (line.startsWith('event: ')) event.event = line.slice(7);
          else if (line.startsWith('data: ')) event.data = line.slice(6);
        }
        this.events.push(event);
      }
      this.wake();
    });
    const done = (): void => {
      this.closed = true;
      this.wake();
    };
    res.on('end', done);
    res.on('close', done);
    res.on('error', done);
  }

  /** Each Delivery read, typed by the contract's generated definition. */
  deliveries(): components['schemas']['Delivery'][] {
    return this.events
      .filter((e) => e.event === 'delivery')
      .map((e) => JSON.parse(e.data) as components['schemas']['Delivery']);
  }

  ended(): { code: string } | undefined {
    const end = this.events.find((e) => e.event === 'end');
    return end ? (JSON.parse(end.data) as { code: string }) : undefined;
  }

  /** Waits until `ready()` holds, or fails after `ms`. */
  async until(ready: () => boolean, ms = 5_000): Promise<void> {
    const deadline = Date.now() + ms;
    while (!ready()) {
      if (Date.now() > deadline) throw new Error('timed out waiting on the stream');
      await new Promise<void>((resolve) => {
        this.waiters.push(resolve);
        setTimeout(resolve, 25).unref();
      });
    }
  }

  pause(): void {
    this.res.pause();
  }

  destroy(): void {
    this.res.destroy();
  }

  private wake(): void {
    const waiters = this.waiters;
    this.waiters = [];
    for (const w of waiters) w();
  }
}

/**
 * A subscribe over a real connection. Resolves with the stream once the
 * response's head arrives; a refusal resolves too, with its body as `raw`.
 */
export function subscribe(
  g: Ingest,
  c: Credential | string,
  options: { draft?: Record<string, unknown>; headers?: Record<string, string> } = {},
): Promise<SseClient> {
  const body = JSON.stringify({ draft: options.draft ?? draft() });
  return new Promise((resolve, reject) => {
    const req = httpRequest(
      `${g.url()}${SUBSCRIBE}`,
      {
        method: 'POST',
        headers: {
          'content-type': 'application/json',
          'content-length': Buffer.byteLength(body),
          authorization: `Bearer ${typeof c === 'string' ? c : c.token}`,
          ...options.headers,
        },
      },
      (res) => resolve(new SseClient(res)),
    );
    req.on('error', reject);
    req.end(body);
  });
}

/** Lets the event loop run the streams' chains and the sockets' writes. */
export async function flush(g: Ingest): Promise<void> {
  for (let i = 0; i < 3; i++) {
    await g.runtime.streams.settled();
    await new Promise((resolve) => setImmediate(resolve));
  }
}

/** The Problem's code and status, and its Retry-After, for compact assertions. */
export function problem(r: Response): { status: number; code: unknown; retryAfter?: unknown } {
  return {
    status: r.status,
    code: (r.body as { code?: unknown } | undefined)?.code,
    ...(r.headers['retry-after'] === undefined ? {} : { retryAfter: r.headers['retry-after'] }),
  };
}

/** The attribution records of one agent, as the owner sees them. */
export async function records(g: Ingest, agent: string): Promise<Record<string, any>[]> {
  const r = await g.owner.query(
    'SELECT * FROM attribution_records WHERE registration = $1 ORDER BY recorded_at, id',
    [agent],
  );
  return r.rows as Record<string, any>[];
}

/**
 * Two parsed JSON values are equal in value, walked with an explicit stack
 * (any depth): the same types, array items in order, the same member names in
 * any order, and each number by its exact source text (raw values).
 */
export function sameJson(a: unknown, b: unknown): boolean {
  const pending: [unknown, unknown][] = [[a, b]];
  while (pending.length > 0) {
    const [x, y] = pending.pop()!;
    if (isRawJson(x) || isRawJson(y)) {
      if (!isRawJson(x) || !isRawJson(y) || x.rawJSON !== y.rawJSON) return false;
    } else if (Array.isArray(x) || Array.isArray(y)) {
      if (!Array.isArray(x) || !Array.isArray(y) || x.length !== y.length) return false;
      x.forEach((v, i) => pending.push([v, y[i]]));
    } else if (typeof x === 'object' && x !== null && typeof y === 'object' && y !== null) {
      const kx = Object.keys(x).sort();
      const ky = Object.keys(y).sort();
      if (kx.join('\u0000') !== ky.join('\u0000')) return false;
      for (const k of kx)
        pending.push([(x as Record<string, unknown>)[k], (y as Record<string, unknown>)[k]]);
    } else if (x !== y) return false;
  }
  return true;
}
