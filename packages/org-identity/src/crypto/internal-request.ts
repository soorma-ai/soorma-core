// SPDX-License-Identifier: FSL-1.1-ALv2
//
// Signed internal requests (P-06; BR-INT-02; I3). Each call from an
// environment to the internal listener carries a short-lived JWS in
// `Authorization: Bearer`: alg Ed25519, typ soorma-internal+jwt, kid = the
// environment caller key's thumbprint; claims iss (the environment), aud
// (urn:soorma:org:{o}:internal), htm (the method), tgt (the full request
// target, query included, exactly as sent), bsh (base64url SHA-256 of the
// exact body bytes), iat, exp (at most 60 s after iat), jti.
//
// The organization level checks every one of these against the request it
// actually received, with 30 seconds' leeway on the times (two clocks). A
// captured token is therefore good only for the identical call; every
// internal operation is read-only, so an identical replay gains nothing.
// Network location is never the check.
import { createHash, createPublicKey, randomUUID, type KeyObject } from 'node:crypto';
import { errors, jwtVerify, SignJWT, type JWTPayload } from 'jose';
import type { KeyRing } from './key-ring.ts';
import { thumbprint } from './key-ring.ts';

export const INTERNAL_TYP = 'soorma-internal+jwt';
export const INTERNAL_LEEWAY_SECONDS = 30;
export const INTERNAL_MAX_LIFETIME_SECONDS = 60;

export function internalAudience(organization: string): string {
  return `urn:soorma:org:${organization}:internal`;
}

export function bodyHash(body: Buffer | string): string {
  return createHash('sha256').update(body).digest('base64url');
}

export interface ReceivedRequest {
  method: string;
  /** The request target as received: path and query, exactly. */
  target: string;
  body: Buffer;
  /** The Authorization header values, from the raw header list. */
  authorization: readonly string[];
}

/** The calling environment, or undefined: a refusal, with no detail. */
export async function verifyInternalRequest(
  request: ReceivedRequest,
  keys: KeyRing,
  organization: string,
  now: Date,
): Promise<string | undefined> {
  if (request.authorization.length !== 1) return undefined;
  const match = /^Bearer ([A-Za-z0-9\-._~+/]+=*)$/.exec(request.authorization[0]!);
  if (!match) return undefined;
  let environment: string | undefined;
  const keyFor = (header: { kid?: string }) => {
    const caller = header.kid === undefined ? undefined : keys.callerByKid(header.kid);
    if (!caller) throw new errors.JWKSNoMatchingKey();
    environment = caller.environment;
    return caller.key;
  };
  let payload: JWTPayload;
  try {
    ({ payload } = await jwtVerify(match[1]!, keyFor, {
      algorithms: ['Ed25519'],
      typ: INTERNAL_TYP,
      audience: internalAudience(organization),
      currentDate: now,
      clockTolerance: INTERNAL_LEEWAY_SECONDS,
      requiredClaims: ['iss', 'aud', 'htm', 'tgt', 'bsh', 'iat', 'exp', 'jti'],
    }));
  } catch {
    return undefined;
  }
  const { iss, iat, exp, htm, tgt, bsh } = payload as JWTPayload & Record<string, unknown>;
  if (environment === undefined || iss !== environment) return undefined;
  if (typeof iat !== 'number' || typeof exp !== 'number') return undefined;
  if (exp - iat > INTERNAL_MAX_LIFETIME_SECONDS || exp <= iat) return undefined;
  if (iat > now.getTime() / 1000 + INTERNAL_LEEWAY_SECONDS) return undefined;
  if (htm !== request.method || tgt !== request.target) return undefined;
  if (bsh !== bodyHash(request.body)) return undefined;
  return environment;
}

/**
 * Signs an internal request as an environment would. U4 builds the real
 * caller; this is the test caller (D-CG-OI-11), and the reference for U4.
 */
export async function signInternalRequest(
  input: { environment: string; method: string; target: string; body?: Buffer | string },
  key: KeyObject,
  organization: string,
  now: Date,
  lifetimeSeconds: number = INTERNAL_MAX_LIFETIME_SECONDS,
): Promise<string> {
  const iat = Math.floor(now.getTime() / 1000);
  return new SignJWT({
    htm: input.method,
    tgt: input.target,
    bsh: bodyHash(input.body ?? ''),
  })
    .setProtectedHeader({ alg: 'Ed25519', typ: INTERNAL_TYP, kid: thumbprint(publicOf(key)) })
    .setIssuer(input.environment)
    .setAudience(internalAudience(organization))
    .setIssuedAt(iat)
    .setExpirationTime(iat + lifetimeSeconds)
    .setJti(randomUUID())
    .sign(key);
}

function publicOf(key: KeyObject): KeyObject {
  return key.type === 'private' ? createPublicKey(key) : key;
}
