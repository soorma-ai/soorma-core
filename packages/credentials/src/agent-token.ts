// SPDX-License-Identifier: FSL-1.1-ALv2
//
// The agent credential's token (U6 D-AC-13; NP-AC-09): `soorma_ac_` + a JWS
// compact serialization of a JWT with explicit typing (RFC 8725),
// `typ` `soorma-ac+jwt`, `Ed25519` only (RFC 9864), fixed in code; signed with
// E's **agent** key ring, never the human one (D-AC-03). Claims, every one
// required:
//   env  { organization, project, environment }: E's configured identity,
//        compared field by field (O4)
//   sub  the logical agent
//   inst the instance, asserted, never verified (D-AC-23)
//   cid  the credential record: the lineage, kept by renewal (D-AC-14)
//   jti  this token; renewal mints a new one
//   iat, exp (exp at most L after iat, never past the lineage end)
// No iss and no aud: the binding is env, and the kind is typ plus the prefix.
//
// U4's token.ts (the human environment credential) is not refactored (NP-AC-09;
// stop condition 3); NP-EHA-01's steps are repeated here for this kind.
// verifyAgentCredential runs steps 1 to 8 and returns a refusal, never
// throwing. O3 (revocation) and the record are the caller's.
import { errors, jwtVerify, SignJWT, type JWTPayload } from 'jose';
import type { EnvironmentRef } from '@soorma/policy-decision-seam';
import { asSecretText, type SecretText } from '@soorma/service-kit';
import type { EnvironmentKeyRing, VerifyKeyRing } from './key-ring.ts';
import { IAT_AHEAD_SECONDS, type TokenRefusalReason, type TokenVerification } from './token.ts';

export const AGENT_CREDENTIAL_PREFIX = 'soorma_ac_';
export const AGENT_CREDENTIAL_TYP = 'soorma-ac+jwt';
const ALGORITHM = 'Ed25519';
/** RFC 6750 b64token, at most 4096 characters (U1 BR-CR-05). */
const B64TOKEN = /^[A-Za-z0-9\-._~+/]+=*$/;
const MAX_TOKEN = 4096;

export interface AgentCredentialClaims {
  readonly environment: EnvironmentRef;
  /** The logical agent (sub). */
  readonly agent: string;
  /** The asserted instance (inst). */
  readonly instance: string;
  /** The credential record: the lineage. */
  readonly cid: string;
  /** This token. */
  readonly jti: string;
  readonly issuedAt: Date;
  readonly expiresAt: Date;
}

export type AgentTokenVerification =
  | { readonly ok: true; readonly claims: AgentCredentialClaims }
  | Extract<TokenVerification, { ok: false }>;

const seconds = (d: Date): number => Math.floor(d.getTime() / 1000);

/** Mints a token with E's current agent signing key. The returned string is a secret. */
export async function mintAgentCredential(
  claims: AgentCredentialClaims,
  ring: EnvironmentKeyRing,
): Promise<SecretText> {
  const jws = await new SignJWT({
    env: {
      organization: claims.environment.organization,
      project: claims.environment.project,
      environment: claims.environment.environment,
    },
    inst: claims.instance,
    cid: claims.cid,
  })
    .setProtectedHeader({ alg: ALGORITHM, typ: AGENT_CREDENTIAL_TYP, kid: ring.signingKid })
    .setSubject(claims.agent)
    .setJti(claims.jti)
    .setIssuedAt(seconds(claims.issuedAt))
    .setExpirationTime(seconds(claims.expiresAt))
    .sign(ring.signingKey);
  return asSecretText(AGENT_CREDENTIAL_PREFIX + jws);
}

function isText(v: unknown): v is string {
  return typeof v === 'string' && v.length > 0;
}

/** Step 5: every claim present and well typed. */
function claimsOf(payload: JWTPayload): AgentCredentialClaims | undefined {
  const { env, sub, inst, cid, jti, iat, exp } = payload as JWTPayload & {
    env?: unknown;
    inst?: unknown;
    cid?: unknown;
  };
  if (typeof env !== 'object' || env === null || Array.isArray(env)) return undefined;
  const e = env as Record<string, unknown>;
  if (!isText(e.organization) || !isText(e.project) || !isText(e.environment)) return undefined;
  if (!isText(sub) || !isText(inst) || !isText(cid) || !isText(jti)) return undefined;
  if (!Number.isInteger(iat) || !Number.isInteger(exp)) return undefined;
  return {
    environment: { organization: e.organization, project: e.project, environment: e.environment },
    agent: sub,
    instance: inst,
    cid,
    jti,
    issuedAt: new Date((iat as number) * 1000),
    expiresAt: new Date((exp as number) * 1000),
  };
}

function sameEnvironment(a: EnvironmentRef, b: EnvironmentRef): boolean {
  return (
    a.organization === b.organization && a.project === b.project && a.environment === b.environment
  );
}

const refused = (reason: TokenRefusalReason): AgentTokenVerification => ({
  ok: false,
  code: 'credential_refused',
  reason,
});

/**
 * NP-EHA-01's steps 1 to 8, for the agent kind (BR-CR-AC-03). A token from
 * another environment, or of the human kind, fails at its kid, typ, or
 * signature before its expiry is read, so no expiry is disclosed. No leeway
 * on exp (NFR-AC-18).
 */
export async function verifyAgentCredential(
  token: SecretText,
  ring: VerifyKeyRing,
  environment: EnvironmentRef,
  now: Date,
): Promise<AgentTokenVerification> {
  // Step 1: prefix, length, syntax.
  if (token.length > MAX_TOKEN || !B64TOKEN.test(token)) return refused('malformed');
  if (!token.startsWith(AGENT_CREDENTIAL_PREFIX)) return refused('malformed');
  const jws = token.slice(AGENT_CREDENTIAL_PREFIX.length);
  // Steps 2 to 4: the header, a key E's agent ring holds, the signature; then 5 and 6.
  let unknownKey = false;
  const keyFor = (header: { kid?: string }) => {
    const key = header.kid === undefined ? undefined : ring.verifyKey(header.kid);
    if (!key) {
      unknownKey = true;
      throw new errors.JWKSNoMatchingKey();
    }
    return key;
  };
  let payload: JWTPayload;
  try {
    ({ payload } = await jwtVerify(jws, keyFor, {
      algorithms: [ALGORITHM],
      typ: AGENT_CREDENTIAL_TYP,
      currentDate: now,
      clockTolerance: 0,
      requiredClaims: ['env', 'sub', 'inst', 'cid', 'jti', 'iat', 'exp'],
    }));
  } catch (error) {
    if (unknownKey) return refused('unknown_key');
    if (error instanceof errors.JWTExpired) {
      // jose verifies the signature, typ, and algorithm before the time
      // claims; the form is re-checked so a malformed but signed token is
      // never reported as expired.
      return claimsOf(error.payload)
        ? { ok: false, code: 'credential_expired', reason: 'expired' }
        : refused('claims');
    }
    if (error instanceof errors.JWSSignatureVerificationFailed) return refused('signature');
    if (error instanceof errors.JWTClaimValidationFailed) return refused('claims');
    return refused('header');
  }
  const claims = claimsOf(payload);
  if (!claims) return refused('claims');
  // Step 7: an iat at most 30 s ahead.
  if (seconds(claims.issuedAt) > seconds(now) + IAT_AHEAD_SECONDS) return refused('issued_ahead');
  // Step 8: E's identity, field by field (O4).
  if (!sameEnvironment(claims.environment, environment)) return refused('wrong_environment');
  return { ok: true, claims };
}
