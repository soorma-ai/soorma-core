// SPDX-License-Identifier: FSL-1.1-ALv2
// The agent credential's token and the three constants (U6 NP-AC-01, 09;
// D-AC-02, 13; NFR-AC-02 to 04, 18): TC-AC-056 (B < L <= M), TC-AC-055 (L at
// mint and renewal), TC-AC-023 (the lineage cap, its time half), TC-AC-068
// (the time rules), TC-AC-082 (kind separation, the agent verifier's half; U4's
// verifier's half is kind-separation.test.ts). U4's token.test.ts is unchanged.
import { generateKeyPairSync } from 'node:crypto';
import { asSecretBytes, asSecretText } from '@soorma/service-kit';
import { SignJWT } from 'jose';
import { describe, expect, it } from 'vitest';
import {
  AGENT_CREDENTIAL_LIFETIME_MS,
  LINEAGE_MAX_AGE_MS,
  lineageTimes,
  loadEnvironmentKeyRing,
  mintAgentCredential,
  mintEnvironmentCredential,
  PROPAGATION_BOUND_MS,
  renewedExpiry,
  verifyAgentCredential,
  type AgentCredentialClaims,
  type EnvironmentKeyRing,
} from '../src/index.ts';

const E = { organization: 'o1', project: 'p1', environment: 'e' };
const E2 = { organization: 'o1', project: 'p1', environment: 'e2' };
const T0 = new Date('2026-11-12T08:00:00Z');
const MINUTE = 60_000;
const at = (ms: number): Date => new Date(T0.getTime() + ms);

function ring(name = 'k1'): EnvironmentKeyRing {
  const { privateKey } = generateKeyPairSync('ed25519');
  const pem = asSecretBytes(Buffer.from(privateKey.export({ format: 'pem', type: 'pkcs8' })));
  return loadEnvironmentKeyRing({ signing: name, verify: [{ name, pem }] });
}

const claims = (over: Partial<AgentCredentialClaims> = {}): AgentCredentialClaims => ({
  environment: E,
  agent: 'a',
  instance: 'i-1',
  cid: 'c1',
  jti: 'j1',
  issuedAt: T0,
  expiresAt: at(15 * MINUTE),
  ...over,
});

describe('TC-AC-056: B < L <= M, over the constants', () => {
  it('60 s < 15 min <= 24 h', () => {
    expect(PROPAGATION_BOUND_MS).toBe(60_000);
    expect(AGENT_CREDENTIAL_LIFETIME_MS).toBe(15 * MINUTE);
    expect(LINEAGE_MAX_AGE_MS).toBe(24 * 60 * MINUTE);
    expect(PROPAGATION_BOUND_MS).toBeLessThan(AGENT_CREDENTIAL_LIFETIME_MS);
    expect(AGENT_CREDENTIAL_LIFETIME_MS).toBeLessThanOrEqual(LINEAGE_MAX_AGE_MS);
  });
});

describe('TC-AC-055, TC-AC-023: L at bootstrap and renewal, never past the lineage end', () => {
  it('a new lineage: whole seconds; expiry at L; the end at M', () => {
    const t = lineageTimes(new Date(T0.getTime() + 999));
    expect(t.issuedAt).toEqual(T0);
    expect(t.expiresAt).toEqual(at(15 * MINUTE));
    expect(t.lineageEndsAt).toEqual(at(24 * 60 * MINUTE));
  });

  it('a renewal is now + L, capped at the lineage end', () => {
    const end = at(24 * 60 * MINUTE);
    expect(renewedExpiry(at(10 * MINUTE), end)).toEqual(at(25 * MINUTE));
    expect(renewedExpiry(at(23 * 60 * MINUTE + 50 * MINUTE), end)).toEqual(end);
    expect(renewedExpiry(at(23 * 60 * MINUTE + 58 * MINUTE), end)).toEqual(end);
  });
});

describe('the agent token (D-AC-13)', () => {
  it('round-trips: soorma_ac_, soorma-ac+jwt, Ed25519, every claim', async () => {
    const r = ring();
    const token = await mintAgentCredential(claims(), r);
    expect(token.startsWith('soorma_ac_')).toBe(true);
    const header = JSON.parse(
      Buffer.from(token.slice('soorma_ac_'.length).split('.')[0]!, 'base64url').toString(),
    ) as Record<string, unknown>;
    expect(header).toEqual({ alg: 'Ed25519', typ: 'soorma-ac+jwt', kid: r.signingKid });
    const v = await verifyAgentCredential(token, r, E, T0);
    expect(v).toEqual({ ok: true, claims: claims() });
  });
});

describe('TC-AC-068: no leeway on exp; an iat at most 30 s ahead', () => {
  it('refuses at exp with credential_expired, after the signature verifies', async () => {
    const r = ring();
    const token = await mintAgentCredential(claims(), r);
    expect((await verifyAgentCredential(token, r, E, at(15 * MINUTE - 1000))).ok).toBe(true);
    expect(await verifyAgentCredential(token, r, E, at(15 * MINUTE))).toEqual({
      ok: false,
      code: 'credential_expired',
      reason: 'expired',
    });
  });

  it('accepts an iat 30 s ahead; refuses 31 s ahead', async () => {
    const r = ring();
    const ahead = (s: number) =>
      mintAgentCredential(claims({ issuedAt: at(s * 1000), expiresAt: at(15 * MINUTE) }), r);
    expect((await verifyAgentCredential(await ahead(30), r, E, T0)).ok).toBe(true);
    expect(await verifyAgentCredential(await ahead(31), r, E, T0)).toMatchObject({
      ok: false,
      code: 'credential_refused',
      reason: 'issued_ahead',
    });
  });
});

describe('TC-AC-082 (the agent verifier): every other kind, environment, or key is refused', () => {
  it("a human environment credential's JWS behind soorma_ac_ is refused, by its typ", async () => {
    const r = ring();
    const human = await mintEnvironmentCredential(
      { environment: E, principal: 'h', cid: 'c', jti: 'j', issuedAt: T0, expiresAt: at(MINUTE) },
      r,
    );
    const forged = asSecretText('soorma_ac_' + human.slice('soorma_ec_'.length));
    expect(await verifyAgentCredential(forged, r, E, T0)).toMatchObject({
      ok: false,
      code: 'credential_refused',
    });
  });

  it('a token signed by another ring is unknown_key, and its expiry is never read', async () => {
    const token = await mintAgentCredential(claims({ expiresAt: at(MINUTE) }), ring());
    expect(await verifyAgentCredential(token, ring(), E, at(2 * MINUTE))).toMatchObject({
      ok: false,
      code: 'credential_refused',
      reason: 'unknown_key',
    });
  });

  it("E2's token, signed with a key E also held, is wrong_environment (O4, field by field)", async () => {
    const r = ring();
    const token = await mintAgentCredential(claims({ environment: E2 }), r);
    expect(await verifyAgentCredential(token, r, E, T0)).toMatchObject({
      ok: false,
      reason: 'wrong_environment',
    });
  });

  it('refuses a missing claim, another prefix, and a malformed value', async () => {
    const r = ring();
    const noInst = await new SignJWT({ env: E, cid: 'c' })
      .setProtectedHeader({ alg: 'Ed25519', typ: 'soorma-ac+jwt', kid: r.signingKid })
      .setSubject('a')
      .setJti('j')
      .setIssuedAt(Math.floor(T0.getTime() / 1000))
      .setExpirationTime(Math.floor(T0.getTime() / 1000) + 60)
      .sign(r.signingKey);
    const check = (t: string) => verifyAgentCredential(asSecretText(t), r, E, T0);
    expect(await check('soorma_ac_' + noInst)).toMatchObject({ reason: 'claims' });
    expect(await check('soorma_ec_' + noInst)).toMatchObject({ reason: 'malformed' });
    expect(await check('soorma_ac_not a token')).toMatchObject({ reason: 'malformed' });
  });
});
