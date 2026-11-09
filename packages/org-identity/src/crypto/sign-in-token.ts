// SPDX-License-Identifier: FSL-1.1-ALv2
//
// The organization sign-in token (P-01): `soorma_si_` + a JWT with explicit
// typing (RFC 8725), alg `Ed25519` (RFC 9864) only, signed with jose.
//
// Verification at S1 requires every claim, the exact `typ`, the algorithm
// fixed in code, this organization as `iss`, and `exp` with no leeway (one
// clock). Expiry is reported only for a token whose signature verified
// (BR-ERR-02). The sign-in record's state (O3) is the caller's check.
import { randomUUID } from 'node:crypto';
import { errors, jwtVerify, SignJWT, type JWTPayload } from 'jose';
import type { KeyRing } from './key-ring.ts';

export const SIGN_IN_PREFIX = 'soorma_si_';
export const SIGN_IN_TYP = 'soorma-si+jwt';
const ALGORITHM = 'Ed25519';

/** The material classes, as the contract names them, and their RFC 8176 `amr` values. */
export type MaterialClass = 'K' | 'P';
const AMR: Record<MaterialClass, string> = { K: 'pwd', P: 'otp' };
const CLASS_OF: Record<string, MaterialClass> = { pwd: 'K', otp: 'P' };

export function issuerOf(organization: string): string {
  return `urn:soorma:org:${organization}`;
}

export interface SignInClaims {
  organization: string;
  principal: string;
  /** The sign-in record's id. */
  sid: string;
  /** This token's id; each renewal mints a new one. */
  jti: string;
  issuedAt: Date;
  expiresAt: Date;
  authenticatedAt: Date;
  classes: MaterialClass[];
}

export interface MintInput {
  organization: string;
  principal: string;
  sid: string;
  authenticatedAt: Date;
  classes: MaterialClass[];
  issuedAt: Date;
  expiresAt: Date;
}

export type VerifyResult =
  { status: 'valid'; claims: SignInClaims } | { status: 'expired' } | { status: 'invalid' };

const seconds = (d: Date): number => Math.floor(d.getTime() / 1000);

/** Mints a token. `exp` is whole seconds; the returned claims carry exactly what the token says. */
export async function mintSignIn(
  input: MintInput,
  keys: KeyRing,
): Promise<{ token: string; claims: SignInClaims }> {
  const jti = randomUUID();
  const iat = seconds(input.issuedAt);
  const exp = seconds(input.expiresAt);
  const authTime = seconds(input.authenticatedAt);
  const jws = await new SignJWT({
    sid: input.sid,
    auth_time: authTime,
    amr: input.classes.map((c) => AMR[c]),
  })
    .setProtectedHeader({ alg: ALGORITHM, typ: SIGN_IN_TYP, kid: keys.signingKid })
    .setIssuer(issuerOf(input.organization))
    .setSubject(input.principal)
    .setJti(jti)
    .setIssuedAt(iat)
    .setExpirationTime(exp)
    .sign(keys.signingKey);
  return {
    token: SIGN_IN_PREFIX + jws,
    claims: {
      organization: input.organization,
      principal: input.principal,
      sid: input.sid,
      jti,
      issuedAt: new Date(iat * 1000),
      expiresAt: new Date(exp * 1000),
      authenticatedAt: new Date(authTime * 1000),
      classes: [...input.classes],
    },
  };
}

function claimsOf(payload: JWTPayload, organization: string): SignInClaims | undefined {
  const {
    sub,
    sid,
    jti,
    iat,
    exp,
    auth_time: authTime,
    amr,
  } = payload as JWTPayload & {
    sid?: unknown;
    auth_time?: unknown;
    amr?: unknown;
  };
  if (typeof sub !== 'string' || sub.length === 0) return undefined;
  if (typeof sid !== 'string' || sid.length === 0) return undefined;
  if (typeof jti !== 'string' || jti.length === 0) return undefined;
  if (typeof iat !== 'number' || typeof exp !== 'number') return undefined;
  if (typeof authTime !== 'number' || !Number.isInteger(authTime)) return undefined;
  if (!Array.isArray(amr) || amr.length === 0) return undefined;
  const classes: MaterialClass[] = [];
  for (const value of amr) {
    const c = typeof value === 'string' ? CLASS_OF[value] : undefined;
    if (!c || classes.includes(c)) return undefined;
    classes.push(c);
  }
  if (!classes.includes('K')) return undefined;
  return {
    organization,
    principal: sub,
    sid,
    jti,
    issuedAt: new Date(iat * 1000),
    expiresAt: new Date(exp * 1000),
    authenticatedAt: new Date(authTime * 1000),
    classes,
  };
}

/**
 * Verifies a presented token. `invalid` for anything that does not verify;
 * `expired` only for a token whose signature and form verified and whose
 * `exp` has passed.
 */
export async function verifySignIn(
  token: string,
  keys: KeyRing,
  organization: string,
  now: Date,
): Promise<VerifyResult> {
  if (!token.startsWith(SIGN_IN_PREFIX)) return { status: 'invalid' };
  const jws = token.slice(SIGN_IN_PREFIX.length);
  const options = {
    algorithms: [ALGORITHM],
    typ: SIGN_IN_TYP,
    issuer: issuerOf(organization),
    currentDate: now,
    clockTolerance: 0,
    requiredClaims: ['iss', 'sub', 'sid', 'jti', 'iat', 'exp', 'auth_time', 'amr'],
  };
  const keyFor = (header: { kid?: string }) => {
    const key = header.kid === undefined ? undefined : keys.verifyKey(header.kid);
    if (!key) throw new errors.JWKSNoMatchingKey();
    return key;
  };
  try {
    const { payload } = await jwtVerify(jws, keyFor, options);
    const claims = claimsOf(payload, organization);
    return claims ? { status: 'valid', claims } : { status: 'invalid' };
  } catch (error) {
    if (error instanceof errors.JWTExpired) {
      // jose verifies the signature, typ, and algorithm before the time
      // claims. Re-check the form so a malformed but signed token is never
      // reported as expired.
      return claimsOf(error.payload, organization) ? { status: 'expired' } : { status: 'invalid' };
    }
    return { status: 'invalid' };
  }
}
