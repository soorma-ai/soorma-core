// SPDX-License-Identifier: FSL-1.1-ALv2
//
// S1 for tests: the real runtime over a test database (the org-identity
// harness), both NestJS applications initialised and driven through
// Fastify's inject, a captured log, and a test environment caller key for
// environment `e` (D-CG-OI-11).
import { generateKeyPairSync, randomBytes, type KeyObject } from 'node:crypto';
import type { NestFastifyApplication } from '@nestjs/platform-fastify';
import { asSecretText, signInternalRequest, type Store } from '@soorma/service-kit';
import type { HashSemaphore, Argon2id } from '@soorma/org-identity';
import type { LightMyRequestResponse } from 'fastify';
import type { TestDatabase } from '../../../packages/org-identity/test/harness/database.ts';
import {
  CapturingRecorder,
  enrollmentMaterial,
  testDomain,
  testKeys,
  TestClock,
  type Domain,
} from '../../../packages/org-identity/test/harness/domain.ts';
import { createEdgeApp, createInternalApp } from '../src/apps.ts';
import { ContractValidator } from '../src/contract-validator.ts';
import { assembleRuntime, type Runtime } from '../src/runtime.ts';
import { SecurityLog, type LogSink } from '../src/security-log.ts';

export const K = 'purple garden lantern';
export const K2 = 'quiet river compass';

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
}

export interface Gateway {
  domain: Domain;
  runtime: Runtime;
  edge: NestFastifyApplication;
  internal: NestFastifyApplication;
  log: CapturedLog;
  clock: TestClock;
  /** Environment e's caller key (private). */
  callerKey: KeyObject;
  /** Another key, configured for environment e2. */
  otherCallerKey: KeyObject;
  close(): Promise<void>;
}

export const validator = new ContractValidator();

export async function gateway(
  db: TestDatabase,
  options: {
    secondFactorRequired?: boolean;
    argon2id?: Argon2id;
    semaphore?: HashSemaphore;
    store?: Store;
    failures?: CapturingRecorder;
    realHashing?: boolean;
  } = {},
): Promise<Gateway> {
  const e = generateKeyPairSync('ed25519');
  const e2 = generateKeyPairSync('ed25519');
  const pem = (k: KeyObject) => Buffer.from(k.export({ format: 'pem', type: 'spki' }));
  const keys = testKeys([
    { environment: 'e', publicKey: pem(e.publicKey) },
    { environment: 'e2', publicKey: pem(e2.publicKey) },
  ]);
  const clock = new TestClock();
  const domain = await testDomain(db, { ...options, keys, clock });
  const log = new CapturedLog();
  const runtime = assembleRuntime({
    organization: 'o1',
    identity: domain.identity,
    keys,
    clock,
    log: new SecurityLog(log),
    validator,
  });
  const edge = await createEdgeApp(runtime);
  const internal = await createInternalApp(runtime);
  return {
    domain,
    runtime,
    edge,
    internal,
    log,
    clock,
    callerKey: e.privateKey,
    otherCallerKey: e2.privateKey,
    async close() {
      await edge.close();
      await internal.close();
    },
  };
}

let counter = 0;
export const unique = (): string =>
  `user${counter++}-${randomBytes(4).toString('hex')}@example.com`;

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

export async function post(
  app: NestFastifyApplication,
  url: string,
  body: unknown,
  headers: Record<string, string> = {},
): Promise<Response> {
  const r = await app
    .getHttpAdapter()
    .getInstance()
    .inject({
      method: 'POST',
      url,
      headers: {
        'content-type': 'application/json',
        'soorma-contract-version': '0.1.0',
        ...headers,
      },
      ...(body === undefined
        ? {}
        : { payload: typeof body === 'string' ? body : JSON.stringify(body) }),
    });
  return wrap(r);
}

export async function get(
  app: NestFastifyApplication,
  url: string,
  headers: Record<string, string> = {},
): Promise<Response> {
  return wrap(await app.getHttpAdapter().getInstance().inject({ method: 'GET', url, headers }));
}

/** A signed internal GET, as environment e (or as configured). */
export async function internalGet(
  g: Gateway,
  url: string,
  options: { key?: KeyObject; environment?: string; target?: string; now?: Date } = {},
): Promise<Response> {
  const token = await signInternalRequest(
    {
      environment: options.environment ?? 'e',
      method: 'GET',
      target: options.target ?? url,
    },
    options.key ?? g.callerKey,
    'o1',
    options.now ?? g.clock.now(),
  );
  return get(g.internal, url, { authorization: `Bearer ${token}` });
}

/** A fresh first Admin; returns its reference and enrollment material. */
export async function registered(
  g: Gateway,
): Promise<{ principal: { organization: string; principal: string }; em: string }> {
  const principal = unique();
  const em = enrollmentMaterial();
  await g.domain.identity.ensureFirstAdmin(
    [{ principal, registeredBy: 'e' }],
    [{ principal, material: asSecretText(em) }],
  );
  return { principal: { organization: 'o1', principal }, em };
}

/** A fresh active human with K, through the edge; returns its sign-in token. */
export async function active(
  g: Gateway,
): Promise<{ principal: { organization: string; principal: string }; token: string }> {
  const { principal, em } = await registered(g);
  const r = await post(g.edge, '/first-authentication', {
    principal,
    enrollmentMaterial: em,
    newSecret: K,
  });
  if (r.status !== 200) throw new Error(`first authentication: ${r.status} ${r.text}`);
  return { principal, token: (r.body as { signIn: { token: string } }).signIn.token };
}
