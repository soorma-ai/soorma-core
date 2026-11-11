// SPDX-License-Identifier: FSL-1.1-ALv2
//
// What the stack's scripted checks share (the smoke test, TC-OI-056 and
// TC-EHA-086; the S1-stopped demonstration, TC-EHA-084 and 085): Compose, a
// TLS client trusting only the local CA, and a pass/fail tally.
import { execFileSync } from 'node:child_process';
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
