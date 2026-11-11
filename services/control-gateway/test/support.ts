// SPDX-License-Identifier: FSL-1.1-ALv2
//
// S2's test harness: the real runtime over a test environment store, as the
// app role, with a stub of S1's internal interface (logical-components §6),
// an injected clock, and a captured log. Requests go through the real edge
// application (Fastify's inject), so the check order, the filter, and the
// throttle hooks are S2's own.
import { createPublicKey, generateKeyPairSync, randomBytes, type KeyObject } from 'node:crypto';
import type { NestFastifyApplication } from '@nestjs/platform-fastify';
import { loadEnvironmentKeyRing, type EnvironmentKeyRing } from '@soorma/credentials';
import { KeyRing, mintSignIn } from '@soorma/org-identity';
import {
  asSecretBytes,
  Semaphore,
  type PrincipalReference,
  type SignInStatus,
  type Store,
} from '@soorma/service-kit';
import type { LightMyRequestResponse } from 'fastify';
import { TestClock } from '../../../packages/org-identity/test/harness/domain.ts';
import type { TestEnvDatabase } from '../../../packages/env-store/test/harness/database.ts';
import { createEdgeApp } from '../src/apps.ts';
import { ContractValidator } from '../src/contract-validator.ts';
import { applyConfiguredFirstGrant } from '../src/first-grant.ts';
import { OrgLevelUnavailableError, type OrgLevel } from '../src/org-level.ts';
import { assembleRuntime, type Runtime } from '../src/runtime.ts';
import { SecurityLog, type LogSink } from '../src/security-log.ts';
import { PERMIT_WAIT_MS, REQUEST_PERMITS, RETRY_AFTER_SECONDS } from '../src/settings.ts';
import { VerifyKeyCache } from '../src/verify-keys.ts';

export { TestClock };

export const E = Object.freeze({ organization: 'o1', project: 'p1', environment: 'e' });
export const E2 = Object.freeze({ organization: 'o1', project: 'p1', environment: 'e2' });
export const MINUTE = 60_000;

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

let counter = 0;
export const unique = (): string =>
  `user${counter++}-${randomBytes(4).toString('hex')}@example.com`;

export function organizationRing(): KeyRing {
  return KeyRing.fromConfiguration({
    signingKey: Buffer.from(
      generateKeyPairSync('ed25519').privateKey.export({ format: 'pem', type: 'pkcs8' }),
    ),
    verifyKeys: [],
    seedKeys: { current: 's1', keys: [{ id: 's1', key: randomBytes(32) }] },
    counterSecret: randomBytes(32),
    logPseudonymKey: randomBytes(32),
    internalCallers: [],
  });
}

export function environmentRing(): EnvironmentKeyRing {
  const pem = asSecretBytes(
    Buffer.from(generateKeyPairSync('ed25519').privateKey.export({ format: 'pem', type: 'pkcs8' })),
  );
  return loadEnvironmentKeyRing({ signing: 'k1', verify: [{ name: 'k1', pem }] });
}

/**
 * A stub of S1's internal interface, in-process: sign-ins it minted and their
 * status (A7), the principals that exist, and its verify keys. Every call is
 * counted; `down` makes each one unavailable; `hold` keeps calls pending.
 */
export class StubOrgLevel implements OrgLevel {
  ring: KeyRing = organizationRing();
  readonly statuses = new Map<string, SignInStatus>();
  readonly principals = new Set<string>();
  readonly calls: string[] = [];
  down = false;
  hold: Promise<void> | undefined;
  private readonly clock: TestClock;

  constructor(clock: TestClock) {
    this.clock = clock;
  }

  count(operation: string): number {
    return this.calls.filter((c) => c === operation).length;
  }

  /** A sign-in for `principal`, as S1 would issue it; A7 answers live until `expiresAt`. */
  async signIn(
    principal: string,
    options: { expiresAt?: Date; issuedAt?: Date; ring?: KeyRing; status?: SignInStatus } = {},
  ): Promise<{ token: string; sid: string; expiresAt: Date }> {
    const issuedAt = options.issuedAt ?? this.clock.now();
    const expiresAt = options.expiresAt ?? new Date(issuedAt.getTime() + 15 * MINUTE);
    const sid = randomBytes(16).toString('hex');
    const { token } = await mintSignIn(
      {
        organization: 'o1',
        principal,
        sid,
        authenticatedAt: issuedAt,
        classes: ['K'],
        issuedAt,
        expiresAt,
      },
      options.ring ?? this.ring,
    );
    this.principals.add(principal);
    this.statuses.set(sid, options.status ?? { status: 'live', expiresAt });
    return { token, sid, expiresAt };
  }

  async signInStatus(sid: string): Promise<SignInStatus> {
    this.calls.push('signInStatus');
    if (this.down) throw new OrgLevelUnavailableError('signInStatus', 'stub_down');
    if (this.hold) await this.hold;
    const status = this.statuses.get(sid) ?? { status: 'unknown' };
    // A7 judges expiry on S1's clock, with no leeway.
    if (status.status === 'live' && status.expiresAt.getTime() <= this.clock.now().getTime())
      return { status: 'ended' };
    return status;
  }

  async principalExists(reference: PrincipalReference): Promise<boolean> {
    this.calls.push('principalExists');
    if (this.down) throw new OrgLevelUnavailableError('principalExists', 'stub_down');
    if (this.hold) await this.hold;
    return reference.organization === 'o1' && this.principals.has(reference.principal);
  }

  verifyKeys(): Promise<Map<string, KeyObject>> {
    this.calls.push('verifyKeys');
    if (this.down) return Promise.reject(new OrgLevelUnavailableError('verifyKeys', 'stub_down'));
    return Promise.resolve(
      new Map(
        this.ring
          .jwks()
          .keys.map((k) => [
            k.kid,
            createPublicKey({ key: { kty: 'OKP', crv: 'Ed25519', x: k.x }, format: 'jwk' }),
          ]),
      ),
    );
  }
}

export interface Gateway {
  runtime: Runtime;
  edge: NestFastifyApplication;
  stub: StubOrgLevel;
  cache: VerifyKeyCache;
  log: CapturedLog;
  clock: TestClock;
  ring: EnvironmentKeyRing;
  /** E's configured first Admin, granted at start-up. */
  admin: string;
  close(): Promise<void>;
}

export const validator = new ContractValidator();

export async function gateway(
  db: TestEnvDatabase,
  options: {
    store?: Store;
    requests?: Semaphore;
    ring?: EnvironmentKeyRing;
    environment?: { organization: string; project: string; environment: string };
    clock?: TestClock;
    stub?: StubOrgLevel;
    loadKeys?: boolean;
    admin?: string;
  } = {},
): Promise<Gateway> {
  const clock = options.clock ?? new TestClock('2026-11-11T12:00:00Z');
  const stub = options.stub ?? new StubOrgLevel(clock);
  const captured = new CapturedLog();
  const log = new SecurityLog(captured);
  const cache = new VerifyKeyCache({ fetch: () => stub.verifyKeys(), clock, log });
  if (options.loadKeys !== false) await cache.fetch();
  const ring = options.ring ?? environmentRing();
  const runtime = assembleRuntime({
    environment: options.environment ?? E,
    store: options.store ?? db.store,
    ring,
    orgLevel: stub,
    keys: cache,
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
    logPseudonymKey: asSecretBytes(randomBytes(32)),
  });
  const admin = options.admin ?? unique();
  await applyConfiguredFirstGrant(runtime, admin);
  stub.principals.add(admin);
  const edge = await createEdgeApp(runtime);
  return {
    runtime,
    edge,
    stub,
    cache,
    log: captured,
    clock,
    ring,
    admin,
    async close() {
      cache.stop();
      await edge.close();
    },
  };
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

export async function post(
  app: NestFastifyApplication,
  url: string,
  options: { credential?: string; body?: unknown; headers?: Record<string, string> } = {},
): Promise<Response> {
  const r = await app
    .getHttpAdapter()
    .getInstance()
    .inject({
      method: 'POST',
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

/** Issues E's credential to `principal` from a fresh sign-in; the principal must hold a grant. */
export async function credentialFor(
  g: Gateway,
  principal: string,
  signIn: { expiresAt?: Date } = {},
): Promise<{ credential: string; expiresAt: string; sid: string }> {
  const s = await g.stub.signIn(principal, signIn);
  const r = await post(g.edge, '/environment-credentials', { credential: s.token });
  if (r.status !== 200) throw new Error(`issuance failed: ${r.status} ${r.text}`);
  return {
    credential: r.body.credential as string,
    expiresAt: r.body.expiresAt as string,
    sid: s.sid,
  };
}

/** The admin's credential. */
export function adminCredential(g: Gateway) {
  return credentialFor(g, g.admin);
}

export function grant(
  g: Gateway,
  credential: string,
  principal: string,
  permissions: string[],
  organization = 'o1',
): Promise<Response> {
  return post(g.edge, '/grants', {
    credential,
    body: { target: { organization, principal }, permissions },
  });
}

/** A fresh principal holding `permissions` in E, granted by the admin, with a credential. */
export async function member(
  g: Gateway,
  permissions: string[] = ['agent:register'],
): Promise<{ principal: string; credential: string; sid: string }> {
  const principal = unique();
  g.stub.principals.add(principal);
  const { credential: admin } = await adminCredential(g);
  const r = await grant(g, admin, principal, permissions);
  if (r.status !== 200) throw new Error(`grant failed: ${r.status} ${r.text}`);
  const c = await credentialFor(g, principal);
  return { principal, credential: c.credential, sid: c.sid };
}

/** The Problem's code and status, and its Retry-After, for compact assertions. */
export function problem(r: Response): { status: number; code: unknown; retryAfter?: unknown } {
  return {
    status: r.status,
    code: (r.body as { code?: unknown } | undefined)?.code,
    ...(r.headers['retry-after'] === undefined ? {} : { retryAfter: r.headers['retry-after'] }),
  };
}
