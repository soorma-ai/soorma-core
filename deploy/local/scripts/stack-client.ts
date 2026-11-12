// SPDX-License-Identifier: FSL-1.1-ALv2
//
// What the stack's scripted checks share (the smoke test, TC-OI-056 and
// TC-EHA-086; the S1-stopped demonstration, TC-EHA-084 and 085): Compose, a
// TLS client trusting only the local CA, and a pass/fail tally.
import { execFileSync, spawnSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import { request } from 'node:https';
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
 */
export async function registeredAgent(
  credential: string,
  env: 'e' | 'e2',
  agent: string,
): Promise<string> {
  const port = CONTROL_GATEWAY[env];
  const r = await call('/registrations', {
    token: credential,
    port,
    body: { agent, standingPermissions: [] },
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
