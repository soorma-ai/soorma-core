// SPDX-License-Identifier: FSL-1.1-ALv2
//
// U5's helpers for S2's registration operations, beside U4's support.ts,
// which they use and do not change.
import { randomBytes } from 'node:crypto';
import {
  adminCredential,
  credentialFor,
  grant,
  member,
  post,
  type Gateway,
  type Response,
} from './support.ts';

/** A fresh logical agent identifier: the strict pattern, unique per call. */
export const agentId = (): string => `agent-${randomBytes(6).toString('hex')}`;

/** H's held set after `sponsor`: the configured pair and the three self-granted. */
export const H_HELD = [
  'agent:register',
  'event:publish',
  'event:subscribe',
  'grant:human',
  'human:manage',
] as const;

export function register(
  g: Gateway,
  credential: string,
  body: Record<string, unknown>,
): Promise<Response> {
  return post(g.edge, '/registrations', { credential, body });
}

export function issueSecret(
  g: Gateway,
  credential: string,
  registration: string,
): Promise<Response> {
  return post(g.edge, '/registration-secrets', { credential, body: { registration } });
}

/**
 * H, E's configured first Admin, after self-granting agent:register,
 * event:publish, and event:subscribe (ID §1 trace step 5), with a credential.
 */
export async function sponsor(g: Gateway): Promise<{ principal: string; credential: string }> {
  const { credential } = await adminCredential(g);
  const r = await grant(g, credential, g.admin, [
    'agent:register',
    'event:publish',
    'event:subscribe',
  ]);
  if (r.status !== 200) throw new Error(`self-grant failed: ${r.status} ${r.text}`);
  return { principal: g.admin, credential };
}

/**
 * Every U5 flow once, so each U5 event is emitted: a registration, a secret,
 * and a refusal of each. Returns the values no log line may contain.
 */
export async function registrationFlows(g: Gateway): Promise<string[]> {
  const h = await sponsor(g);
  const a = agentId();
  const created = await register(g, h.credential, {
    agent: a,
    standingPermissions: ['event:publish'],
    autonomyDeclared: true,
  });
  if (created.status !== 200) throw new Error(`registration failed: ${created.text}`);
  await register(g, h.credential, { agent: agentId(), standingPermissions: ['grant:human'] });
  const issued = await issueSecret(g, h.credential, a);
  if (issued.status !== 200) throw new Error(`issuance failed: ${issued.text}`);
  await issueSecret(g, h.credential, agentId());
  const fresh = await credentialFor(g, g.admin);
  const d = await member(g, ['event:publish']);
  return [h.credential, fresh.credential, d.credential, issued.body.secret as string, h.principal];
}
