// SPDX-License-Identifier: FSL-1.1-ALv2
//
// Build and Test: latency on the RUNNING local stack, measured and REPORTED,
// never a gate. Each figure is a p95 printed beside its target; nothing here
// asserts a time. It measures, through each deployable's real edge (TLS 1.3,
// a new connection per request, as a raw client makes it; no SDK):
//
// - TC-EHA-070 (NFR-EHA-15): E's S2 with the real S1: issuance and renewal
//   (target 300 ms), ending and grantToHuman (200 ms). U4's in-process
//   figures (services/control-gateway/test/perf) used a stub S1 and no TLS
// - TC-AR-064 (NFR-AR-15): registerAgent and issueRegistrationSecret (no
//   target; reported)
// - TC-AC-067 (NFR-AC-17): E's S3, exchangeBootstrap and renewAgentCredential
//   (target 200 ms)
// - TC-ET-036 (NFR-ET-15): E's S4, opening a stream (200 ms), publish
//   (200 ms), and publish to delivery (250 ms), from the publish's request to
//   the Delivery read off B's stream
//
// Run on a fresh stack (`down -v`, `stack:up`), the workspace built:
//
//   SOORMA_PERF_SECRET_FILE=<a path outside the repository> pnpm test:perf:stack
//
// If that file is absent, H's first authentication happens here, from the
// handover file, and K is written to the file (mode 0600) and never printed,
// so that TC-OI-059 (`pnpm test:perf`) can sign in with it afterwards. If it
// exists, K is read from it. K never goes in an environment variable.
//
// `pnpm test`, `pnpm test:e2e`, and CI skip it.
import { existsSync, readFileSync, writeFileSync } from 'node:fs';
import { request } from 'node:https';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';
import {
  agentCredentialOf,
  bootstrapAgent,
  CONTROL_GATEWAY,
  draft,
  EVENT_INGEST,
  publishAt,
  renewAgent,
} from '../../deploy/local/scripts/stack-client.ts';
import { call, firstAuthentication, json, PRINCIPAL, SECRETS } from '../support.ts';

const secretFile = process.env.SOORMA_PERF_SECRET_FILE;
const enabled = process.env.SOORMA_PERF === '1' && secretFile !== undefined;

const S2_RUNS = 500;
const REGISTRATIONS = 200;
const PUBLISHES = 200;
const OPENINGS = 200;
const RUN = Date.now().toString(36);

/** The q-quantile of the samples (nearest rank). */
function quantile(samples: number[], q: number): number {
  const sorted = [...samples].sort((a, b) => a - b);
  return sorted[Math.min(sorted.length - 1, Math.ceil(q * sorted.length) - 1)]!;
}

const summary = (samples: number[]) => ({
  samples: samples.length,
  p50: Number(quantile(samples, 0.5).toFixed(1)),
  p95: Number(quantile(samples, 0.95).toFixed(1)),
  max: Number(Math.max(...samples).toFixed(1)),
});

async function timed<T>(f: () => Promise<T>, into: number[]): Promise<T> {
  const t = performance.now();
  const value = await f();
  into.push(performance.now() - t);
  return value;
}

const report = (tc: string, figures: Record<string, number[]>, targetsMs: object): void =>
  console.log(
    JSON.stringify({
      tc,
      ms: Object.fromEntries(Object.entries(figures).map(([k, v]) => [k, summary(v)])),
      targetsMs,
      gate: false,
    }),
  );

/** One open S4 stream, recording when its head and each Delivery arrived. */
interface TimedStream {
  status: number;
  /** performance.now() at each Delivery, by the payload's `seq`. */
  arrivals: Map<number, number>;
  next(seq: number, ms?: number): Promise<number>;
  close(): void;
}

function openStream(credential: string): Promise<TimedStream> {
  const ca = readFileSync(join(SECRETS, 'stack-ca.pem'));
  const body = JSON.stringify({ draft: draft() });
  return new Promise((done, fail) => {
    const req = request(
      {
        host: 'localhost',
        port: EVENT_INGEST.e,
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
        const arrivals = new Map<number, number>();
        const waiters = new Map<number, (at: number) => void>();
        let buffer = '';
        res.setEncoding('utf8');
        res.on('data', (chunk: string) => {
          const at = performance.now();
          buffer += chunk;
          let end: number;
          while ((end = buffer.indexOf('\n\n')) !== -1) {
            const block = buffer.slice(0, end);
            buffer = buffer.slice(end + 2);
            let event = '';
            let data = '';
            for (const line of block.split('\n')) {
              if (line.startsWith('event: ')) event = line.slice(7);
              else if (line.startsWith('data: ')) data = line.slice(6);
            }
            if (event !== 'delivery') continue;
            const seq = (JSON.parse(data) as { payload: { seq: number } }).payload.seq;
            arrivals.set(seq, at);
            waiters.get(seq)?.(at);
          }
        });
        res.on('error', () => undefined);
        done({
          status: res.statusCode ?? 0,
          arrivals,
          next: (seq, ms = 10_000) =>
            arrivals.has(seq)
              ? Promise.resolve(arrivals.get(seq)!)
              : new Promise((resolve, reject) => {
                  const timer = setTimeout(() => reject(new Error(`no delivery ${seq}`)), ms);
                  waiters.set(seq, (at) => {
                    clearTimeout(timer);
                    resolve(at);
                  });
                }),
          close: () => res.destroy(),
        });
      },
    );
    req.on('error', fail);
    req.end(body);
  });
}

const S2 = CONTROL_GATEWAY.e;
const s2 = (path: string, token: string, body?: unknown) => call(path, { token, body, port: S2 });

/** H's K: read from the file, or set by the first authentication and written there. */
async function secretK(): Promise<string> {
  const file = secretFile!;
  if (existsSync(file)) {
    const K = readFileSync(file, 'utf8').trim();
    if (K.length > 0) return K;
  }
  const K = await firstAuthentication();
  writeFileSync(file, K, { mode: 0o600 });
  return K;
}

async function signIn(K: string): Promise<string> {
  const r = await call('/sign-ins', { body: { principal: PRINCIPAL, secret: K } });
  expect(r.status, 'sign-in').toBe(200);
  return (json(r) as { signIn: { token: string } }).signIn.token;
}

describe.skipIf(!enabled)('Build and Test: latency on the running stack (reported)', () => {
  it('TC-EHA-070, TC-AR-064, TC-AC-067, TC-ET-036', async () => {
    const K = await secretK();
    const signInToken = await signIn(K);
    const issued = await s2('/environment-credentials', signInToken);
    expect(issued.status, 'issuance').toBe(200);
    const admin = (json(issued) as { credential: string }).credential;
    const grant = await s2('/grants', admin, {
      target: PRINCIPAL,
      permissions: ['agent:register', 'event:publish', 'event:subscribe'],
    });
    expect(grant.status, 'self-grant').toBe(200);

    // TC-EHA-070: E's S2 with the real S1 (issuance and renewal call S1's
    // signInStatus; grantToHuman calls S1 for the principal; ending does not).
    const eha: Record<string, number[]> = { issue: [], renew: [], end: [], grantToHuman: [] };
    for (let i = 0; i < 20; i++) await s2('/environment-credentials', signInToken); // warm-up
    for (let i = 0; i < S2_RUNS; i++) {
      const c = await timed(() => s2('/environment-credentials', signInToken), eha.issue!);
      expect(c.status, 'issue').toBe(200);
      const credential = (json(c) as { credential: string }).credential;
      const r = await timed(
        () => s2('/environment-credentials/current/renewal', credential),
        eha.renew!,
      );
      expect(r.status, 'renew').toBe(200);
      const renewed = (json(r) as { credential: string }).credential;
      // BR-GR-06: a permission already held may be granted again, and is
      // recorded; H is M1's only principal.
      const g = await timed(
        () => s2('/grants', admin, { target: PRINCIPAL, permissions: ['agent:register'] }),
        eha.grantToHuman!,
      );
      expect(g.status, 'grantToHuman').toBe(200);
      const e = await timed(() => s2('/environment-credentials/current/end', renewed), eha.end!);
      expect(e.status, 'end').toBe(204);
    }
    report('TC-EHA-070', eha, { issue: 300, renew: 300, end: 200, grantToHuman: 200 });

    // TC-AR-064: registerAgent and issueRegistrationSecret.
    const ar: Record<string, number[]> = { registerAgent: [], issueRegistrationSecret: [] };
    const secrets = new Map<string, string>();
    for (let i = 0; i < REGISTRATIONS; i++) {
      const agent = `perf-${RUN}-${i}`;
      const r = await timed(
        () => s2('/registrations', admin, { agent, standingPermissions: ['event:publish'] }),
        ar.registerAgent!,
      );
      expect(r.status, 'registerAgent').toBe(200);
      const s = await timed(
        () => s2('/registration-secrets', admin, { registration: agent }),
        ar.issueRegistrationSecret!,
      );
      expect(s.status, 'issueRegistrationSecret').toBe(200);
      secrets.set(agent, (json(s) as { secret: string }).secret);
    }
    report('TC-AR-064', ar, { registerAgent: 'none (reported)', issueRegistrationSecret: 'none' });

    // TC-AC-067: each of those agents bootstraps one instance at E's S3, then
    // renews it (one attempt per agent: the abuse bound never engages).
    const ac: Record<string, number[]> = { exchangeBootstrap: [], renewAgentCredential: [] };
    for (const [agent, secret] of secrets) {
      const b = await timed(() => bootstrapAgent('e', agent, secret), ac.exchangeBootstrap!);
      expect(b.status, 'exchangeBootstrap').toBe(200);
      const r = await timed(() => renewAgent('e', agentCredentialOf(b)), ac.renewAgentCredential!);
      expect(r.status, 'renewAgentCredential').toBe(200);
    }
    report('TC-AC-067', ac, { exchangeBootstrap: 200, renewAgentCredential: 200 });

    // TC-ET-036: A (event:publish) and B (event:subscribe), autonomy declared,
    // registered and bootstrapped through the real S2 and S3.
    const credentialOf = async (agent: string, standing: string): Promise<string> => {
      const r = await s2('/registrations', admin, {
        agent,
        standingPermissions: [standing],
        autonomyDeclared: true,
      });
      expect(r.status, `register ${agent}`).toBe(200);
      const s = await s2('/registration-secrets', admin, { registration: agent });
      const secret = (json(s) as { secret: string }).secret;
      const token = agentCredentialOf(await bootstrapAgent('e', agent, secret));
      expect(token, `bootstrap ${agent}`).not.toBe('');
      return token;
    };
    const A = await credentialOf(`perf-a-${RUN}`, 'event:publish');
    const B = await credentialOf(`perf-b-${RUN}`, 'event:subscribe');
    const et: Record<string, number[]> = { open: [], publish: [], publishToDelivery: [] };
    for (let i = 0; i < OPENINGS; i++) {
      const s = await timed(() => openStream(B), et.open!);
      expect(s.status, 'subscribe').toBe(200);
      s.close();
    }
    const stream = await openStream(B);
    expect(stream.status, 'subscribe').toBe(200);
    try {
      for (let seq = 0; seq < PUBLISHES; seq++) {
        const started = performance.now();
        const p = await timed(() => publishAt('e', A, { seq }), et.publish!);
        expect(p.status, 'publish').toBe(202);
        et.publishToDelivery!.push((await stream.next(seq)) - started);
      }
    } finally {
      stream.close();
    }
    report('TC-ET-036', et, { open: 200, publish: 200, publishToDelivery: 250 });
  }, 1_800_000);
});
