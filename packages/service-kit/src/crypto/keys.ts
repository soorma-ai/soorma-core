// SPDX-License-Identifier: FSL-1.1-ALv2
//
// Ed25519 public keys by RFC 7638 thumbprint (P-02): the `kid` of every
// signing, verify, and caller key. Moved from @soorma/org-identity's key ring
// (U4 NP-EHA-15); the ring itself stays there.
import { createHash, type KeyObject } from 'node:crypto';

/** A public Ed25519 key as a JWK, for the JWKS. */
export interface PublicJwk {
  kty: 'OKP';
  crv: 'Ed25519';
  x: string;
  kid: string;
  alg: 'Ed25519';
  use: 'sig';
}

export interface VerifyKey {
  kid: string;
  key: KeyObject;
  jwk: PublicJwk;
}

export interface CallerKey {
  environment: string;
  kid: string;
  key: KeyObject;
}

/** The RFC 7638 thumbprint of an Ed25519 public key (SHA-256, base64url). */
export function thumbprint(key: KeyObject): string {
  const { x } = key.export({ format: 'jwk' });
  const members = `{"crv":"Ed25519","kty":"OKP","x":"${String(x)}"}`;
  return createHash('sha256').update(members).digest('base64url');
}
