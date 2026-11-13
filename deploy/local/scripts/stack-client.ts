// SPDX-License-Identifier: FSL-1.1-ALv2
//
// What the stack's scripted checks share (the smoke test, TC-OI-056 and
// TC-EHA-086; the S1-stopped demonstration, TC-EHA-084 and 085): Compose, a
// TLS client trusting only the local CA, and a pass/fail tally.
import { execFileSync, spawnSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import { request } from 'node:https';
import type { IncomingHttpHeaders } from 'node:http';
import { join, resolve } from 'node:path';

export const LOCAL = resolve(import.meta.dirname, '..');
export const SECRETS = join(LOCAL, '.secrets');
export const COMPOSE = ['compose', '-f', join(LOCAL, 'compose.yaml')];
export const PRINCIPAL = { organization: 'o1', principal: 'h@example.com' };

let failures = 0;
export function check(name: string, ok: boolean, detail = ''): void {
  console.log(`${ok ? 'ok  ' : 'FAIL'} ${name}${detail ? ` (${detail})` : ''}`);
  if (!ok) failures += 1;
}
export const failed = (): number => failures;

export const docker = (args: string[]): string =>
  execFileSync('docker', args, { encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] }).trim();

/**
 * `docker` with `input` on stdin: how a script hands a container a secret or a
 * token without putting it on a command line or in an environment variable.
 * Never throws: it returns the exit status and both streams.
 */
export function dockerWithInput(
  args: string[],
  input: string,
): { status: number; stdout: string; stderr: string } {
  const r = spawnSync('docker', args, { input, encoding: 'utf8' });
  return { status: r.status ?? -1, stdout: r.stdout.trim(), stderr: r.stderr.trim() };
}

export interface Reply {
  status: number;
  body: string;
  protocol: string | null;
  retryAfter: string | undefined;
  /** The response's headers (U7: S4's smoke checks read the Soorma headers). */
  headers: IncomingHttpHeaders;
}

/** A POST to one of the stack's edges: S1 on 8441 by default; E's S2 on 8442, E2's on 8443. */
export function call(
  path: string,
  options: {
    body?: unknown;
    token?: string;
    ca?: Buffer | null;
    maxVersion?: 'TLSv1.2';
    port?: number;
  } = {},
): Promise<Reply> {
  const ca = options.ca === undefined ? readFileSync(join(SECRETS, 'stack-ca.pem')) : options.ca;
  return new Promise((done, fail) => {
    const req = request(
      {
        host: 'localhost',
        port: options.port ?? 8441,
        path,
        method: 'POST',
        agent: false,
        ...(ca ? { ca } : {}),
        ...(options.maxVersion ? { maxVersion: options.maxVersion } : {}),
        headers: {
          'soorma-contract-version': '0.1.0',
          ...(options.body === undefined ? {} : { 'content-type': 'application/json' }),
          ...(options.token ? { authorization: `Bearer ${options.token}` } : {}),
        },
      },
      (res) => {
        const protocol =
          (res.socket as { getProtocol?: () => string | null }).getProtocol?.() ?? null;
        const retryAfter = res.headers['retry-after'];
        let body = '';
        res.on('data', (c: Buffer) => (body += c.toString()));
        res.on('end', () =>
          done({
            status: res.statusCode ?? 0,
            body,
            protocol,
            retryAfter: typeof retryAfter === 'string' ? retryAfter : undefined,
            headers: res.headers,
          }),
        );
      },
    );
    req.on('error', fail);
    req.end(options.body === undefined ? undefined : JSON.stringify(options.body));
  });
}

/** S3's edges (U6 D-ID-AC-02): E's on 8444, E2's on 8445. */
export const DATA_GATEWAY = { e: 8444, e2: 8445 } as const;
/** S2's edges: E's on 8442, E2's on 8443. */
export const CONTROL_GATEWAY = { e: 8442, e2: 8443 } as const;

/**
 * An agent of the environment, registered through S2 with an environment
 * credential holding agent:register, and one registration secret issued for it
 * (U6's stack checks: TC-AC-092, TC-AC-017). Returns the secret's value, a
 * secret the caller keeps out of every log line and argument; '' on failure.
 * U7's checks pass the further fields (standing permissions, autonomy).
 */
export async function registeredAgent(
  credential: string,
  env: 'e' | 'e2',
  agent: string,
  // U7 (D-CG-ET-13): the registration's further fields. Omitted, the body is
  // exactly as before, { agent, standingPermissions: [] }, byte for byte.
  registration: { standingPermissions?: string[]; autonomyDeclared?: boolean } = {},
): Promise<string> {
  const port = CONTROL_GATEWAY[env];
  const r = await call('/registrations', {
    token: credential,
    port,
    body: { agent, standingPermissions: [], ...registration },
  });
  if (r.status !== 200) return '';
  const s = await call('/registration-secrets', {
    token: credential,
    port,
    body: { registration: agent },
  });
  return s.status === 200 ? (JSON.parse(s.body) as { secret: string }).secret : '';
}

/** S3's bootstrap (exchangeBootstrap) and renewal (renewAgentCredential). */
export const bootstrapAgent = (
  env: 'e' | 'e2',
  agent: string,
  secret: string,
  instance = 'i-1',
): Promise<Reply> =>
  call('/agent-credentials', { port: DATA_GATEWAY[env], body: { agent, secret, instance } });
export const renewAgent = (env: 'e' | 'e2', credential: string): Promise<Reply> =>
  call('/agent-credentials/current/renewal', { port: DATA_GATEWAY[env], token: credential });
export const agentCredentialOf = (r: Reply): string =>
  r.status === 200 ? (JSON.parse(r.body) as { credential: string }).credential : '';

/** S4's edges (U7 D-ID-ET-02): E's on 8446, E2's on 8447. */
export const EVENT_INGEST = { e: 8446, e2: 8447 } as const;

/** A draft with no forwarded context (envelope.md). */
export const draft = (): Record<string, unknown> => ({
  clientContractVersion: '0.1.0',
  traceContext: { traceparent: '00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01' },
});

/** A publish at an environment's S4: `{ draft, payload }`. */
export const publishAt = (
  env: 'e' | 'e2',
  credential: string,
  payload: unknown,
  forward?: Record<string, unknown>,
): Promise<Reply> =>
  call('/events', {
    port: EVENT_INGEST[env],
    token: credential,
    body: { draft: forward ?? draft(), payload },
  });

/** One open S4 stream, read as server-sent events (`delivery`, `end`). */
export interface EventStream {
  status: number;
  protocol: string | null;
  contentType: string | undefined;
  events: { event: string; data: string }[];
  /** Waits until `ready()` holds, up to `ms`; false on timeout or a closed stream. */
  until(ready: () => boolean, ms?: number): Promise<boolean>;
  close(): void;
}

/** A subscribe at an environment's S4 over TLS 1.3; resolves once the head arrives. */
export function subscribeAt(
  env: 'e' | 'e2',
  credential: string,
  forward?: Record<string, unknown>,
): Promise<EventStream> {
  const ca = readFileSync(join(SECRETS, 'stack-ca.pem'));
  const body = JSON.stringify({ draft: forward ?? draft() });
  return new Promise((done, fail) => {
    const req = request(
      {
        host: 'localhost',
        port: EVENT_INGEST[env],
        path: '/subscriptions',
        method: 'POST',
        agent: false,
        ca,
        headers: {
          'soorma-contract-version': '0.1.0',
          'content-type': 'application/json',
          'content-length': Buffer.byteLength(body),
          authorization: `Bearer ${credential}`,
        },
      },
      (res) => {
        const events: { event: string; data: string }[] = [];
        let buffer = '';
        let closed = false;
        res.setEncoding('utf8');
        res.on('data', (chunk: string) => {
          buffer += chunk;
          let at: number;
          while ((at = buffer.indexOf('\n\n')) !== -1) {
            const block = buffer.slice(0, at);
            buffer = buffer.slice(at + 2);
            if (block.startsWith(':')) continue;
            const e = { event: '', data: '' };
            for (const line of block.split('\n')) {
              if (line.startsWith('event: ')) e.event = line.slice(7);
              else if (line.startsWith('data: ')) e.data = line.slice(6);
            }
            events.push(e);
          }
        });
        res.on('close', () => (closed = true));
        res.on('error', () => (closed = true));
        done({
          status: res.statusCode ?? 0,
          protocol: (res.socket as { getProtocol?: () => string | null }).getProtocol?.() ?? null,
          contentType: res.headers['content-type'],
          events,
          async until(ready, ms = 10_000) {
            const deadline = Date.now() + ms;
            while (!ready()) {
              if (closed || Date.now() > deadline) return ready();
              await new Promise((r) => setTimeout(r, 50));
            }
            return true;
          },
          close: () => res.destroy(),
        });
      },
    );
    req.on('error', fail);
    req.end(body);
  });
}
