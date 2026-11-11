// SPDX-License-Identifier: FSL-1.1-ALv2
//
// P1, the sign-in checks at S1 (D-OI-05, 06, 26; BR-RF-06; business-logic-
// model §1). Works on the raw header list, because Node keeps only the first
// of duplicate Authorization headers in its parsed headers: "exactly one"
// can only be checked on the raw list.
//
// - An operation naming no security scheme (firstAuthenticate, authenticate,
//   changeMaterial): any Authorization or Soorma-Delegation header, whatever
//   it holds, is malformed_request naming the header (D-OI-26)
// - renewSignIn and endSignIn: exactly one `Authorization: Bearer soorma_si_…`
//   and no Soorma-Delegation, else credential_refused; then verification with
//   the organization's verify keys (O2); expiry only after verification
//   (credential_expired); then the sign-in record (O3)
import { type Clock, SIGN_IN_PREFIX, type SignInClaims, verifySignIn } from '@soorma/service-kit';
import type { KeyRing } from '@soorma/org-identity';

export const CREDENTIAL_HEADERS = ['Authorization', 'Soorma-Delegation'] as const;
export type CredentialHeader = (typeof CREDENTIAL_HEADERS)[number];

/** RFC 6750 b64token, at most 4096 characters (BR-CR-05). */
const B64TOKEN = /^[A-Za-z0-9\-._~+/]+=*$/;
const MAX_CREDENTIAL = 4096;

/** The values of one header, from Node's raw header list (name, value, name, value, …). */
export function rawHeaderValues(rawHeaders: readonly string[], name: string): string[] {
  const wanted = name.toLowerCase();
  const out: string[] = [];
  for (let i = 0; i + 1 < rawHeaders.length; i += 2) {
    if (rawHeaders[i]!.toLowerCase() === wanted) out.push(rawHeaders[i + 1]!);
  }
  return out;
}

/** On an operation naming no scheme: the credential headers presented, in a fixed order. */
export function presentedCredentialHeaders(rawHeaders: readonly string[]): CredentialHeader[] {
  return CREDENTIAL_HEADERS.filter((h) => rawHeaderValues(rawHeaders, h).length > 0);
}

/** The presented sign-in token, or undefined when the presentation is refused. */
export function presentedSignIn(rawHeaders: readonly string[]): string | undefined {
  if (rawHeaderValues(rawHeaders, 'Soorma-Delegation').length > 0) return undefined;
  const values = rawHeaderValues(rawHeaders, 'Authorization');
  if (values.length !== 1) return undefined;
  const match = /^Bearer ([^\s]+)$/i.exec(values[0]!);
  const credential = match?.[1];
  if (!credential || credential.length > MAX_CREDENTIAL || !B64TOKEN.test(credential))
    return undefined;
  return credential.startsWith(SIGN_IN_PREFIX) ? credential : undefined;
}

export type SignInCheck =
  | { accepted: true; claims: SignInClaims }
  | { accepted: false; code: 'credential_refused' | 'credential_expired' };

export class SignInPerimeter {
  private readonly keys: KeyRing;
  private readonly organization: string;
  private readonly clock: Clock;
  private readonly isLive: (claims: SignInClaims) => Promise<boolean>;

  /** `isLive` is O3: the sign-in record is live and its principal active (P10). */
  constructor(
    keys: KeyRing,
    organization: string,
    clock: Clock,
    isLive: (claims: SignInClaims) => Promise<boolean>,
  ) {
    this.keys = keys;
    this.organization = organization;
    this.clock = clock;
    this.isLive = isLive;
  }

  async check(rawHeaders: readonly string[]): Promise<SignInCheck> {
    const token = presentedSignIn(rawHeaders);
    if (token === undefined) return { accepted: false, code: 'credential_refused' };
    const verified = await verifySignIn(token, this.keys, this.organization, this.clock.now());
    if (verified.status === 'invalid') return { accepted: false, code: 'credential_refused' };
    if (verified.status === 'expired') return { accepted: false, code: 'credential_expired' };
    if (!(await this.isLive(verified.claims)))
      return { accepted: false, code: 'credential_refused' };
    return { accepted: true, claims: verified.claims };
  }
}
