// SPDX-License-Identifier: FSL-1.1-ALv2
//
// Minting the organization sign-in token (P-01): `soorma_si_` + a JWT with
// explicit typing (RFC 8725), alg `Ed25519` (RFC 9864) only, signed with jose
// and the organization's signing key. Verification moved to
// @soorma/service-kit (U4 NP-EHA-15), so environments verify without this
// package.
import { randomUUID } from 'node:crypto';
import {
  issuerOf,
  type MaterialClass,
  SIGN_IN_PREFIX,
  SIGN_IN_TYP,
  type SignInClaims,
} from '@soorma/service-kit';
import { SignJWT } from 'jose';
import { type KeyRing } from './key-ring.ts';

const ALGORITHM = 'Ed25519';
const AMR: Record<MaterialClass, string> = { K: 'pwd', P: 'otp' };

export interface MintInput {
  organization: string;
  principal: string;
  sid: string;
  authenticatedAt: Date;
  classes: MaterialClass[];
  issuedAt: Date;
  expiresAt: Date;
}

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
