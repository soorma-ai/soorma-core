// SPDX-License-Identifier: FSL-1.1-ALv2
//
// The e2e proofs' client (U5 D-CG-AR-02): raw HTTPS calls to the local stack,
// through deploy/local/scripts/stack-client.ts, unchanged. No SDK, no client
// library. The stack must be fresh: H's first authentication happens here,
// from the handover file, as the smoke test does; the enrollment material is
// read into the request body only, and never printed.
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import {
  call,
  COMPOSE,
  docker,
  PRINCIPAL,
  SECRETS,
  type Reply,
} from '../deploy/local/scripts/stack-client.ts';

export { call, COMPOSE, docker, PRINCIPAL, SECRETS, type Reply };

/** Set when SOORMA_E2E=1: `pnpm test:e2e`. `pnpm test` never needs a stack. */
export const E2E = process.env.SOORMA_E2E === '1';

/** E's S2 on the host's loopback. */
export const E = 8442;

export const json = (r: Reply): unknown =>
  r.body.length > 0 ? (JSON.parse(r.body) as unknown) : undefined;
export const code = (r: Reply): unknown => (json(r) as { code?: unknown } | undefined)?.code;

/** H's first authentication from the handover file, setting K; returns K. */
export async function firstAuthentication(): Promise<string> {
  const handover = readFileSync(join(SECRETS, 'handover', 'first-admin-1.txt'), 'utf8');
  const material = /enrollmentMaterial: (\S+)/.exec(handover)?.[1] ?? '';
  const K = `e2e ${Date.now().toString(36)} lantern harbour`;
  const r = await call('/first-authentication', {
    body: { principal: PRINCIPAL, enrollmentMaterial: material, newSecret: K },
  });
  if (r.status !== 200) throw new Error(`first authentication: ${r.status}`);
  return K;
}

/** A sign-in with K at S1, then E's environment credential from it. */
export async function environmentCredential(K: string): Promise<string> {
  const s = await call('/sign-ins', { body: { principal: PRINCIPAL, secret: K } });
  if (s.status !== 200) throw new Error(`sign-in: ${s.status}`);
  const token = (json(s) as { signIn: { token: string } }).signIn.token;
  const c = await call('/environment-credentials', { token, port: E });
  if (c.status !== 200) throw new Error(`issuance: ${c.status}`);
  return (json(c) as { credential: string }).credential;
}

export const post = (path: string, token: string, body: unknown): Promise<Reply> =>
  call(path, { token, body, port: E });
