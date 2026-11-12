// SPDX-License-Identifier: FSL-1.1-ALv2
//
// U6 on the local stack, by raw calls to S3 (D-AC-31; D-CG-AC-10, 36). Each
// case seeds its own registration as the store's owner, with U5's real secret
// generator (the user's approval), so it needs no human sign-in and runs in
// any order against U5's file (`test:e2e` runs files one at a time). *Done
// when* 2 itself chains from done when 1's real registrations, in
// agent-registration.test.ts (TC-AC-093).
//
//  - TC-AC-004, 005: neither operation carries an envelope; both are
//    attributed to the agent, with sponsor H, and no chain or origin
//  - TC-AC-009: a revoked lineage is refused at renewal at once, logged
//    credential_revoked
//  - TC-AC-025: a revoked agent cannot renew (logged agent_revoked) or
//    bootstrap (the one refusal)
//  - TC-AC-028: a new bootstrap after revocation is a new lineage that renews;
//    the old lineage stays refused
//  - TC-AC-013: E's agent credential and E's secret are refused at E2's S3
//
// TC-AC-091 is U5's backup round trip in agent-registration.test.ts, run with
// e-data-gateway stopped, removed, and restarted beside e-control-gateway.
//
// Run by `pnpm test:e2e` on a fresh stack; skipped otherwise.
import { describe, expect, it } from 'vitest';
import {
  agentCredentialOf,
  bootstrapAgent,
  claims,
  events,
  json,
  renewAgent,
  seedAgentRevocation,
  seedCredentialRevocation,
  seedRegistration,
  sql,
  SPONSOR,
} from './agent-credentials-support.ts';
import { E2E } from './support.ts';

const id = (): string => `u6-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 6)}`;

/** A seeded agent of E and its first credential. */
async function bootstrapped(): Promise<{ agent: string; secret: string; token: string }> {
  const agent = id();
  const secret = seedRegistration('e', agent);
  const r = await bootstrapAgent('e', agent, secret);
  expect(r.status, r.body).toBe(200);
  return { agent, secret, token: agentCredentialOf(r) };
}

describe.skipIf(!E2E)('U6 agent-credentials on the local stack', () => {
  it('TC-AC-004, 005: no envelope; both operations attributed to the agent, sponsor H, no chain', async () => {
    const { agent, token } = await bootstrapped();
    const renewed = await renewAgent('e', token);
    expect(renewed.status).toBe(200);
    for (const body of [json(renewed) as Record<string, unknown>])
      for (const k of ['envelope', 'actorChain', 'originMode', 'chain', 'origin'])
        expect(body).not.toHaveProperty(k);
    expect(
      sql(
        'e',
        `SELECT operation || ':' || actor_kind || ':' || sponsor || ':' || instance || ':' ||
                (chain IS NULL AND origin IS NULL)::text
           FROM attribution_records WHERE registration = '${agent}' ORDER BY recorded_at;`,
      ).split('\n'),
    ).toEqual([
      `exchangeBootstrap:agent:${SPONSOR}:i-1:true`,
      `renewAgentCredential:agent:${SPONSOR}:i-1:true`,
    ]);
  });

  it('TC-AC-009: a revoked lineage is refused at renewal at once, logged credential_revoked', async () => {
    const { token } = await bootstrapped();
    const since = new Date().toISOString();
    seedCredentialRevocation('e', claims(token).cid as string);
    const r = await renewAgent('e', token);
    expect([r.status, (json(r) as { code?: string }).code]).toEqual([401, 'credential_refused']);
    expect(
      events('e-data-gateway', since).some(
        (e) => e.event === 'renewal.refused' && e.code === 'credential_revoked',
      ),
    ).toBe(true);
  });

  it('TC-AC-025: a revoked agent cannot renew (agent_revoked) or bootstrap (the one refusal)', async () => {
    const { agent, secret, token } = await bootstrapped();
    const since = new Date().toISOString();
    seedAgentRevocation('e', agent);
    const renewed = await renewAgent('e', token);
    expect([renewed.status, (json(renewed) as { code?: string }).code]).toEqual([
      401,
      'credential_refused',
    ]);
    const again = await bootstrapAgent('e', agent, secret, 'i-2');
    expect([again.status, (json(again) as { code?: string }).code]).toEqual([
      403,
      'authentication_failed',
    ]);
    const logged = events('e-data-gateway', since);
    expect(logged.some((e) => e.event === 'renewal.refused' && e.code === 'agent_revoked')).toBe(
      true,
    );
    expect(logged.some((e) => e.event === 'bootstrap.refused' && e.code === 'agent_revoked')).toBe(
      true,
    );
  });

  it('TC-AC-028: revocation is terminal; a new bootstrap is a new lineage that renews', async () => {
    const { agent, secret, token } = await bootstrapped();
    seedCredentialRevocation('e', claims(token).cid as string);
    expect((await renewAgent('e', token)).status).toBe(401);
    const fresh = await bootstrapAgent('e', agent, secret);
    expect(fresh.status).toBe(200);
    const next = agentCredentialOf(fresh);
    expect(claims(next).cid).not.toBe(claims(token).cid);
    expect((await renewAgent('e', next)).status).toBe(200);
    expect((await renewAgent('e', token)).status).toBe(401);
  });

  it("TC-AC-013: E's agent credential and E's secret are refused at E2's S3", async () => {
    const { agent, secret, token } = await bootstrapped();
    const crossed = await renewAgent('e2', token);
    expect([crossed.status, (json(crossed) as { code?: string }).code]).toEqual([
      401,
      'credential_refused',
    ]);
    const elsewhere = await bootstrapAgent('e2', agent, secret);
    expect([elsewhere.status, (json(elsewhere) as { code?: string }).code]).toEqual([
      403,
      'authentication_failed',
    ]);
  });
});
