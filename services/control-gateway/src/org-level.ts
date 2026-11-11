// SPDX-License-Identifier: FSL-1.1-ALv2
//
// The S1 caller (NP-EHA-04; D-EHA-23, 27; U2 F-3): every call S2 makes to the
// organization level's internal listener, for three operations only
// (BR-OL-01): signInStatus (A7), principalExists, and the verify keys.
//
// - Two node:https keep-alive pools: the S1-call pool, 8 sockets, for
//   signInStatus and principalExists, each call holding an S1-call permit
//   (NFR-EHA-05); and the key-fetch pool, 1 socket, outside that throttle, so
//   a refresh or refetch never waits behind in-flight calls (the user's change)
// - TLS 1.3, with the local CA as the only trust root, and the server name
//   org-gateway.soorma.internal checked; no client certificate
// - Every call signed with E's caller key (U2 P-06): htm, the exact target
//   with its query, and the empty body's hash
// - One attempt, no retry, a 2-second deadline over connect, TLS, send, and
//   read; a 64 KiB cap on the answer; the answer checked to exactly its shape
// - Any failure is OrgLevelUnavailableError: unavailable (503, Retry-After 5),
//   never a pass. Nothing from S1 is cached here; the verify keys are the
//   cache's (verify-keys.ts)
import { Agent, request } from 'node:https';
import { createPublicKey, type KeyObject } from 'node:crypto';
import {
  globalTimers,
  signInternalRequest,
  thumbprint,
  UnavailableError,
  type Clock,
  type PrincipalReference,
  type Semaphore,
  type SignInStatus,
  type Timers,
} from '@soorma/service-kit';
import { RETRY_AFTER_SECONDS, S1_DEADLINE_MS, S1_RESPONSE_CAP_BYTES } from './settings.ts';

export type OrgLevelOperation = 'signInStatus' | 'principalExists' | 'verifyKeys';

/** The organization level could not answer: unavailable, never a pass (D-EHA-27). */
export class OrgLevelUnavailableError extends UnavailableError {
  readonly operation: OrgLevelOperation;
  /** Why, for the security log only: never in a response. */
  readonly failure: string;

  constructor(operation: OrgLevelOperation, cause: string) {
    super(`organization level unavailable: ${operation} (${cause})`, RETRY_AFTER_SECONDS);
    this.name = 'OrgLevelUnavailableError';
    this.operation = operation;
    this.failure = cause;
  }
}

/** What S2 asks the organization level: the handlers and the cache use this port. */
export interface OrgLevel {
  signInStatus(sid: string): Promise<SignInStatus>;
  principalExists(reference: PrincipalReference): Promise<boolean>;
  verifyKeys(): Promise<Map<string, KeyObject>>;
}

export interface OrgLevelOptions {
  /** E's configured identifier: the iss of every signed call (U2 P-06). */
  environment: string;
  organization: string;
  host: string;
  port: number;
  /** The name the certificate must carry; the host by default. */
  serverName?: string;
  /** The local CA: the only trust root. */
  ca: Buffer;
  /** E's caller key (Ed25519, private). */
  callerKey: KeyObject;
  clock: Clock;
  /** The S1-call permits (NFR-EHA-05). */
  calls: Semaphore;
  timers?: Timers;
}

function isPlainObject(v: unknown): v is Record<string, unknown> {
  return typeof v === 'object' && v !== null && !Array.isArray(v);
}

function exactKeys(v: Record<string, unknown>, keys: readonly string[]): boolean {
  const own = Object.keys(v).sort();
  return own.length === keys.length && [...keys].sort().every((k, i) => own[i] === k);
}

/** A's answer, exactly (U2 BR-INT-05 as amended): nothing else is accepted. */
export function parseSignInStatus(body: unknown): SignInStatus | undefined {
  if (!isPlainObject(body)) return undefined;
  if (body.status === 'live' && exactKeys(body, ['status', 'expiresAt'])) {
    if (typeof body.expiresAt !== 'string') return undefined;
    const at = Date.parse(body.expiresAt);
    return Number.isFinite(at) ? { status: 'live', expiresAt: new Date(at) } : undefined;
  }
  if ((body.status === 'ended' || body.status === 'unknown') && exactKeys(body, ['status']))
    return { status: body.status };
  return undefined;
}

export function parseExists(body: unknown): boolean | undefined {
  if (!isPlainObject(body) || !exactKeys(body, ['exists']) || typeof body.exists !== 'boolean')
    return undefined;
  return body.exists;
}

/** A JWKS of Ed25519 public keys, each kid its RFC 7638 thumbprint, at least one. */
export function parseJwks(body: unknown): Map<string, KeyObject> | undefined {
  if (!isPlainObject(body) || !Array.isArray(body.keys) || body.keys.length === 0) return undefined;
  const out = new Map<string, KeyObject>();
  for (const jwk of body.keys) {
    if (!isPlainObject(jwk) || jwk.kty !== 'OKP' || jwk.crv !== 'Ed25519') return undefined;
    if (typeof jwk.x !== 'string' || typeof jwk.kid !== 'string' || 'd' in jwk) return undefined;
    let key: KeyObject;
    try {
      key = createPublicKey({ key: { kty: 'OKP', crv: 'Ed25519', x: jwk.x }, format: 'jwk' });
    } catch {
      return undefined;
    }
    if (thumbprint(key) !== jwk.kid) return undefined;
    out.set(jwk.kid, key);
  }
  return out;
}

export class OrgLevelClient implements OrgLevel {
  private readonly options: OrgLevelOptions;
  private readonly timers: Timers;
  private readonly callPool = new Agent({ keepAlive: true, maxSockets: 8 });
  private readonly keyPool = new Agent({ keepAlive: true, maxSockets: 1 });

  constructor(options: OrgLevelOptions) {
    this.options = options;
    this.timers = options.timers ?? globalTimers;
  }

  async signInStatus(sid: string): Promise<SignInStatus> {
    const body = await this.options.calls.run(() =>
      this.get('signInStatus', `/sign-ins/${encodeURIComponent(sid)}/status`, this.callPool),
    );
    const status = parseSignInStatus(body);
    if (!status) throw new OrgLevelUnavailableError('signInStatus', 'shape');
    return status;
  }

  async principalExists(reference: PrincipalReference): Promise<boolean> {
    // Identifiers are values: encoded in the query, never interpolated raw (BR-OL-05).
    const query = new URLSearchParams({
      organization: reference.organization,
      principal: reference.principal,
    });
    const body = await this.options.calls.run(() =>
      this.get('principalExists', `/principals/exists?${query.toString()}`, this.callPool),
    );
    const exists = parseExists(body);
    if (exists === undefined) throw new OrgLevelUnavailableError('principalExists', 'shape');
    return exists;
  }

  async verifyKeys(): Promise<Map<string, KeyObject>> {
    const body = await this.get('verifyKeys', '/verify-keys', this.keyPool);
    const keys = parseJwks(body);
    if (!keys) throw new OrgLevelUnavailableError('verifyKeys', 'shape');
    return keys;
  }

  close(): void {
    this.callPool.destroy();
    this.keyPool.destroy();
  }

  /** One signed GET: the answer's JSON, or OrgLevelUnavailableError. */
  private async get(operation: OrgLevelOperation, target: string, agent: Agent): Promise<unknown> {
    const o = this.options;
    const token = await signInternalRequest(
      { environment: o.environment, method: 'GET', target },
      o.callerKey,
      o.organization,
      o.clock.now(),
    );
    const controller = new AbortController();
    const timer = this.timers.set(() => controller.abort(), S1_DEADLINE_MS);
    try {
      return await new Promise<unknown>((resolve, reject) => {
        const fail = (cause: string): void =>
          reject(new OrgLevelUnavailableError(operation, cause));
        const req = request(
          {
            host: o.host,
            port: o.port,
            path: target,
            method: 'GET',
            agent,
            ca: o.ca,
            servername: o.serverName ?? o.host,
            minVersion: 'TLSv1.3',
            headers: { authorization: `Bearer ${token}`, accept: 'application/json' },
            signal: controller.signal,
          },
          (res) => {
            const chunks: Buffer[] = [];
            let size = 0;
            res.on('data', (chunk: Buffer) => {
              size += chunk.length;
              if (size > S1_RESPONSE_CAP_BYTES) {
                req.destroy();
                fail('too_large');
                return;
              }
              chunks.push(chunk);
            });
            res.on('end', () => {
              if (res.statusCode !== 200) return fail(`status_${res.statusCode ?? 0}`);
              try {
                resolve(JSON.parse(Buffer.concat(chunks).toString('utf8')) as unknown);
              } catch {
                fail('not_json');
              }
            });
            res.on('error', () => fail('read'));
          },
        );
        req.on('error', (error: Error & { code?: string }) =>
          fail(controller.signal.aborted ? 'deadline' : (error.code ?? 'connect')),
        );
        req.end();
      });
    } finally {
      this.timers.clear(timer);
    }
  }
}
