// SPDX-License-Identifier: FSL-1.1-ALv2
//
// S3's test harness: the real runtime over a test environment store, as S3's
// own role soorma_env_data (D-ID-AC-07), with an injected clock and a captured
// log. Requests go through the real edge application (Fastify's inject), so the
// check order, the filter, and the throttle hooks are S3's own. Registrations
// and their secrets are seeded as the store's owner, with U5's real secret
// generator; revocation through the owner's test-only fixture (D-CG-AC-10).
import { generateKeyPairSync, randomBytes } from 'node:crypto';
import type { NestFastifyApplication } from '@nestjs/platform-fastify';
import { loadEnvironmentKeyRing, type EnvironmentKeyRing } from '@soorma/credentials';
import { connectEnvStore, newRecordId } from '@soorma/env-store';
import { generateRegistrationSecret } from '@soorma/registry';
import { asSecretBytes, Semaphore, type Clock, type Store } from '@soorma/service-kit';
import type { LightMyRequestResponse } from 'fastify';
import type { TestEnvDatabase } from '../../../packages/env-store/test/harness/database.ts';
import { ENV_DATA } from '../../../packages/env-store/test/harness/roles.ts';
import { createEdgeApp } from '../src/apps.ts';
import { ContractValidator } from '../src/contract-validator.ts';
import { assembleRuntime, type Runtime } from '../src/runtime.ts';
import { SecurityLog, type LogSink } from '../src/security-log.ts';
import { PERMIT_WAIT_MS, REQUEST_PERMITS, RETRY_AFTER_SECONDS } from '../src/settings.ts';

export const E = Object.freeze({ organization: 'o1', project: 'p1', environment: 'e' });
export const E2 = Object.freeze({ organization: 'o1', project: 'p1', environment: 'e2' });
export const SPONSOR = 'h@example.com';
export const MINUTE = 60_000;

export type Env = { organization: string; project: string; environment: string };

export class TestClock implements Clock {
  ms: number;
  constructor(iso = '2026-11-12T12:00:00Z') {
    this.ms = Date.parse(iso);
  }
  now(): Date {
    return new Date(this.ms);
  }
  advance(ms: number): void {
    this.ms += ms;
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

/** A fresh agent ring with one key, as E's configured `{env}-agent-signing-key-1`. */
export function agentRing(): EnvironmentKeyRing {
  const pem = asSecretBytes(
    Buffer.from(generateKeyPairSync('ed25519').privateKey.export({ format: 'pem', type: 'pkcs8' })),
  );
  return loadEnvironmentKeyRing({ signing: 'k1', verify: [{ name: 'k1', pem }] });
}

/** The test store as S3's own role. */
export function dataStore(db: TestEnvDatabase): Store {
  return connectEnvStore({ ...db.settings, user: ENV_DATA, password: db.info.dataPassword });
}

export const validator = new ContractValidator();

export interface Gateway {
  runtime: Runtime;
  edge: NestFastifyApplication;
  log: CapturedLog;
  clock: TestClock;
  ring: EnvironmentKeyRing;
  /** The store S3 runs over, as soorma_env_data. */
  store: Store;
  /** A client as the store's owner, for seeding and inspection. */
  owner: Awaited<ReturnType<TestEnvDatabase['migrator']>>;
  close(): Promise<void>;
}

export async function gateway(
  db: TestEnvDatabase,
  options: {
    store?: Store;
    requests?: Semaphore;
    ring?: EnvironmentKeyRing;
    environment?: Env;
    clock?: TestClock;
    counterSecret?: Buffer;
  } = {},
): Promise<Gateway> {
  const clock = options.clock ?? new TestClock();
  const captured = new CapturedLog();
  const environment = options.environment ?? E;
  const log = new SecurityLog(captured, environment.environment);
  const ring = options.ring ?? agentRing();
  const own = options.store === undefined;
  const store = options.store ?? dataStore(db);
  const runtime = assembleRuntime({
    environment,
    store,
    ring,
    counterSecret: asSecretBytes(options.counterSecret ?? randomBytes(32)),
    clock,
    log,
    validator,
    requests:
      options.requests ??
      new Semaphore({
        permits: REQUEST_PERMITS,
        waitMs: PERMIT_WAIT_MS,
        reason: 'requests',
        retryAfterSeconds: RETRY_AFTER_SECONDS,
      }),
  });
  const edge = await createEdgeApp(runtime);
  const owner = await db.migrator();
  return {
    runtime,
    edge,
    log: captured,
    clock,
    ring,
    store,
    owner,
    async close() {
      await edge.close();
      await runtime.attempts.stop();
      await owner.end();
      if (own) await store.close();
    },
  };
}

/** A unique logical agent identifier. */
export const agentId = (): string => `a-${newRecordId()}`;

/**
 * A registration of `agent` in `env`, with one secret, seeded as the owner;
 * returns the secret's value and id. `state` sets the registration's state,
 * and `secretState` the secret's.
 */
export async function registered(
  g: Gateway,
  agent: string,
  options: { env?: Env; state?: string; secretState?: string; autonomy?: boolean } = {},
): Promise<{ value: string; id: string }> {
  const env = options.env ?? g.runtime.environment;
  const at = g.clock.now();
  await g.owner.query(
    `INSERT INTO registrations (organization, project, environment, agent, sponsor,
       ceiling_snapshot, standing_permissions, re_broadening_declaration, autonomy_declared,
       registered_at, state)
     VALUES ($1, $2, $3, $4, $5, '{}', '{}', '{}', $6, $7, $8)`,
    [
      env.organization,
      env.project,
      env.environment,
      agent,
      SPONSOR,
      options.autonomy ?? true,
      at,
      options.state ?? 'registered',
    ],
  );
  return secretFor(g, agent, { env, state: options.secretState ?? 'active' });
}

/** Another secret for an existing registration. */
export async function secretFor(
  g: Gateway,
  agent: string,
  options: { env?: Env; state?: string } = {},
): Promise<{ value: string; id: string }> {
  const env = options.env ?? g.runtime.environment;
  const s = generateRegistrationSecret();
  await g.owner.query(
    `INSERT INTO registration_secrets (id, organization, project, environment, registration,
       issuer, digest, issued_at, state)
     VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)`,
    [
      s.id,
      env.organization,
      env.project,
      env.environment,
      agent,
      SPONSOR,
      s.digest,
      g.clock.now(),
      options.state ?? 'active',
    ],
  );
  return { value: s.value, id: s.id };
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

export async function request(
  app: NestFastifyApplication,
  url: string,
  options: {
    method?: 'POST' | 'GET' | 'PUT' | 'DELETE';
    credential?: string;
    body?: unknown;
    headers?: Record<string, string>;
  } = {},
): Promise<Response> {
  const r = await app
    .getHttpAdapter()
    .getInstance()
    .inject({
      method: options.method ?? 'POST',
      url,
      headers: {
        'soorma-contract-version': '0.1.0',
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

export const BOOTSTRAP = '/agent-credentials';
export const RENEWAL = '/agent-credentials/current/renewal';

export function bootstrap(
  g: Gateway,
  agent: string,
  secret: string,
  instance = 'i-1',
  headers?: Record<string, string>,
): Promise<Response> {
  return request(g.edge, BOOTSTRAP, {
    body: { agent, secret, instance },
    ...(headers ? { headers } : {}),
  });
}

export function renew(g: Gateway, credential: string): Promise<Response> {
  return request(g.edge, RENEWAL, { credential });
}

/** A registered agent's first credential; throws unless bootstrap answers 200. */
export async function credentialFor(
  g: Gateway,
  agent = agentId(),
  instance = 'i-1',
): Promise<{
  agent: string;
  secret: { value: string; id: string };
  credential: string;
  cid: string;
}> {
  const secret = await registered(g, agent);
  const r = await bootstrap(g, agent, secret.value, instance);
  if (r.status !== 200) throw new Error(`bootstrap failed: ${r.status} ${r.text}`);
  const credential = r.body.credential as string;
  return { agent, secret, credential, cid: claims(credential).cid as string };
}

/** A token's header and claims, decoded without verifying (the test reads its own tokens). */
export function decoded(token: string): {
  header: Record<string, unknown>;
  claims: Record<string, any>;
} {
  const [h, p] = token.slice('soorma_ac_'.length).split('.');
  return {
    header: JSON.parse(Buffer.from(h!, 'base64url').toString('utf8')) as Record<string, unknown>,
    claims: JSON.parse(Buffer.from(p!, 'base64url').toString('utf8')) as Record<string, any>,
  };
}

export const claims = (token: string): Record<string, any> => decoded(token).claims;

/** The Problem's code and status, and its Retry-After, for compact assertions. */
export function problem(r: Response): { status: number; code: unknown; retryAfter?: unknown } {
  return {
    status: r.status,
    code: (r.body as { code?: unknown } | undefined)?.code,
    ...(r.headers['retry-after'] === undefined ? {} : { retryAfter: r.headers['retry-after'] }),
  };
}

/** Rows of a table for one agent, as the owner sees them. */
export async function rows(
  g: Gateway,
  table: 'agent_credentials' | 'attribution_records' | 'failed_bootstrap_attempts',
  agent: string,
): Promise<Record<string, any>[]> {
  const column = table === 'attribution_records' ? 'registration' : 'agent';
  const r = await g.owner.query(`SELECT * FROM ${table} WHERE ${column} = $1`, [agent]);
  return r.rows as Record<string, any>[];
}

/** Waits for the Failed Bootstrap Attempt writer to drain its queue. */
export async function flushAttempts(g: Gateway): Promise<void> {
  await g.runtime.attempts.flush();
}
