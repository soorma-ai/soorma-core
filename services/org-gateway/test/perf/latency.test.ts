// SPDX-License-Identifier: FSL-1.1-ALv2
// TC-OI-059: sign-in latency on the local stack (NFR-OI-19): p95 at most
// 500 ms for authenticate, hashing included; at most 200 ms for renewal and
// the logout. Runs only at Build and Test, against a running stack:
//
//   SOORMA_PERF=1 SOORMA_PERF_PRINCIPAL=h@example.com \
//   SOORMA_PERF_SECRET_FILE=<a file holding H's K> pnpm test:perf
//
// The CA is passed explicitly (deploy/local/.secrets/stack-ca.pem), never the
// system trust store. K is read from a file, never from the environment.
import { readFileSync } from 'node:fs';
import { request } from 'node:https';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

const run =
  process.env.SOORMA_PERF === '1' &&
  process.env.SOORMA_PERF_PRINCIPAL !== undefined &&
  process.env.SOORMA_PERF_SECRET_FILE !== undefined;
const N = 100;
const root = resolve(import.meta.dirname, '../../../..');

function post(
  path: string,
  body: unknown,
  token?: string,
): Promise<{ status: number; body: string }> {
  const ca = readFileSync(resolve(root, 'deploy/local/.secrets/stack-ca.pem'));
  return new Promise((resolve_, reject) => {
    const req = request(
      {
        host: 'localhost',
        port: 8441,
        path,
        method: 'POST',
        ca,
        agent: false,
        headers: {
          'soorma-contract-version': '0.1.0',
          ...(body === undefined ? {} : { 'content-type': 'application/json' }),
          ...(token ? { authorization: `Bearer ${token}` } : {}),
        },
      },
      (res) => {
        let text = '';
        res.on('data', (c: Buffer) => (text += c.toString()));
        res.on('end', () => resolve_({ status: res.statusCode ?? 0, body: text }));
      },
    );
    req.on('error', reject);
    req.end(body === undefined ? undefined : JSON.stringify(body));
  });
}

async function timed<T>(fn: () => Promise<T>): Promise<[number, T]> {
  const started = performance.now();
  const value = await fn();
  return [performance.now() - started, value];
}

const p95 = (xs: number[]): number => [...xs].sort((a, b) => a - b)[Math.floor(0.95 * xs.length)]!;

describe.runIf(run)('TC-OI-059: sign-in meets its latency targets (local stack)', () => {
  it(`measures ${N} sign-ins, renewals, and logouts`, async () => {
    const principal = { organization: 'o1', principal: process.env.SOORMA_PERF_PRINCIPAL! };
    const secret = readFileSync(process.env.SOORMA_PERF_SECRET_FILE!, 'utf8').trim();
    const authenticate: number[] = [];
    const renew: number[] = [];
    const end: number[] = [];
    for (let i = 0; i < N; i++) {
      const [ta, a] = await timed(() => post('/sign-ins', { principal, secret }));
      expect(a.status).toBe(200);
      authenticate.push(ta);
      const token = (JSON.parse(a.body) as { signIn: { token: string } }).signIn.token;
      const [tr, r] = await timed(() => post('/sign-ins/current/renewal', undefined, token));
      expect(r.status).toBe(200);
      renew.push(tr);
      const [te, e] = await timed(() => post('/sign-ins/current/end', undefined, token));
      expect(e.status).toBe(204);
      end.push(te);
    }
    const report = {
      case: 'TC-OI-059',
      samples: N,
      authenticateP95Ms: p95(authenticate),
      renewP95Ms: p95(renew),
      endP95Ms: p95(end),
    };
    process.stdout.write(`${JSON.stringify(report)}\n`);
    expect(report.authenticateP95Ms).toBeLessThanOrEqual(500);
    expect(report.renewP95Ms).toBeLessThanOrEqual(200);
    expect(report.endP95Ms).toBeLessThanOrEqual(200);
  }, 600_000);
});
