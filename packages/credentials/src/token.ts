// SPDX-License-Identifier: FSL-1.1-ALv2
//
// The human environment credential's token (NP-EHA-01; Q1 A): `soorma_ec_` +
// a JWS compact serialization of a JWT with explicit typing (RFC 8725),
// `Ed25519` only (RFC 9864), fixed in code. Claims, every one required:
//   env  { organization, project, environment }: E's configured identity,
//        compared field by field, so the triple needs no string encoding
//   sub  the principal identifier (its organization is env.organization)
//   cid  the credential record's id
//   jti  this token's id; renewal mints a new jti for the same cid
//   iat, exp
// No iss and no aud: the binding is env, and the kind is typ plus the prefix.
//
// verify runs NP-EHA-01's steps 1 to 8 in order and returns a refusal, never
// throwing. Step 9, O3 (the record, uncached), is the caller's: the record,
// not the token, governs liveness.
import { errors, jwtVerify, SignJWT, type JWTPayload } from 'jose';
import type { EnvironmentRef } from '@soorma/policy-decision-seam';
import { asSecretText, type SecretText } from '@soorma/service-kit';
import type { EnvironmentKeyRing } from './key-ring.ts';

export const ENVIRONMENT_CREDENTIAL_PREFIX = 'soorma_ec_';
export const ENVIRONMENT_CREDENTIAL_TYP = 'soorma-ec+jwt';
const ALGORITHM = 'Ed25519';
/** RFC 6750 b64token, at most 4096 characters (BR-CR-05). */
const B64TOKEN = /^[A-Za-z0-9\-._~+/]+=*$/;
const MAX_TOKEN = 4096;
/** An iat this far ahead of the verifying instance's clock is accepted (NFR-EHA-03). */
export const IAT_AHEAD_SECONDS = 30;

export interface CredentialClaims {
  readonly environment: EnvironmentRef;
  readonly principal: string;
  /** The credential record's id. */
  readonly cid: string;
  /** This token's id. */
  readonly jti: string;
  readonly issuedAt: Date;
  readonly expiresAt: Date;
}

/** Why a token is refused, for the security log only (BR-RF-03); never in a response. */
export type TokenRefusalReason =
  | 'malformed'
  | 'header'
  | 'unknown_key'
  | 'signature'
  | 'claims'
  | 'expired'
  | 'issued_ahead'
  | 'wrong_environment';

export type TokenVerification =
  | { readonly ok: true; readonly claims: CredentialClaims }
  | {
      readonly ok: false;
      readonly code: 'credential_refused' | 'credential_expired';
      readonly reason: TokenRefusalReason;
    };

const seconds = (d: Date): number => Math.floor(d.getTime() / 1000);

/** Mints a token with E's current signing key. The returned string is a secret (NP-EHA-14). */
export async function mintEnvironmentCredential(
  claims: CredentialClaims,
  ring: EnvironmentKeyRing,
): Promise<SecretText> {
  const jws = await new SignJWT({
    env: {
      organization: claims.environment.organization,
      project: claims.environment.project,
      environment: claims.environment.environment,
    },
    cid: claims.cid,
  })
    .setProtectedHeader({ alg: ALGORITHM, typ: ENVIRONMENT_CREDENTIAL_TYP, kid: ring.signingKid })
    .setSubject(claims.principal)
    .setJti(claims.jti)
    .setIssuedAt(seconds(claims.issuedAt))
    .setExpirationTime(seconds(claims.expiresAt))
    .sign(ring.signingKey);
  return asSecretText(ENVIRONMENT_CREDENTIAL_PREFIX + jws);
}

function isText(v: unknown): v is string {
  return typeof v === 'string' && v.length > 0;
}

/** Step 5: every claim present and well typed. */
function claimsOf(payload: JWTPayload): CredentialClaims | undefined {
  const { env, sub, cid, jti, iat, exp } = payload as JWTPayload & { env?: unknown; cid?: unknown };
  if (typeof env !== 'object' || env === null || Array.isArray(env)) return undefined;
  const e = env as Record<string, unknown>;
  if (!isText(e.organization) || !isText(e.project) || !isText(e.environment)) return undefined;
  if (!isText(sub) || !isText(cid) || !isText(jti)) return undefined;
  if (!Number.isInteger(iat) || !Number.isInteger(exp)) return undefined;
  return {
    environment: { organization: e.organization, project: e.project, environment: e.environment },
    principal: sub,
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

const refused = (reason: TokenRefusalReason): TokenVerification => ({
  ok: false,
  code: 'credential_refused',
  reason,
});

/**
 * NP-EHA-01's steps 1 to 8. A credential from another environment fails at
 * its kid or signature, before its expiry is read (BR-EC-03), so no expiry is
 * disclosed. Expiry has no leeway: refused at or after exp (NFR-EHA-03).
 */
export async function verifyEnvironmentCredential(
  token: SecretText,
  ring: EnvironmentKeyRing,
  environment: EnvironmentRef,
  now: Date,
): Promise<TokenVerification> {
  // Step 1: prefix, length, syntax.
  if (token.length > MAX_TOKEN || !B64TOKEN.test(token)) return refused('malformed');
  if (!token.startsWith(ENVIRONMENT_CREDENTIAL_PREFIX)) return refused('malformed');
  const jws = token.slice(ENVIRONMENT_CREDENTIAL_PREFIX.length);
  // Steps 2 to 4: the header, a key E holds, the signature; then 5 and 6.
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
      typ: ENVIRONMENT_CREDENTIAL_TYP,
      currentDate: now,
      clockTolerance: 0,
      requiredClaims: ['env', 'sub', 'cid', 'jti', 'iat', 'exp'],
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
  // Step 8: E's identity, field by field (O4; D-EHA-12).
  if (!sameEnvironment(claims.environment, environment)) return refused('wrong_environment');
  return { ok: true, claims };
}
