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
//
// Generalised for an environment's issuance (U4 NP-EHA-03, 15): the key source
// is read on every verification; an unknown `kid` may trigger one refetch and
// one more verification; the tolerance is the caller's; the status callback
// answers A7's SignInStatus, and an accepted check carries the `live` answer,
// so its expiry can cap what the caller issues.
import {
  asSecretText,
  ORGANIZATION_TOLERANCE,
  SIGN_IN_PREFIX,
  UnavailableError,
  verifySignIn,
  type Clock,
  type SignInClaims,
  type SignInKeySource,
  type SignInStatus,
  type SecretText,
  type SignInTolerance,
} from '@soorma/service-kit';

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

/**
 * The presented credential of the one kind an operation accepts, or undefined
 * when the presentation is refused (BR-PR-01 to 07): exactly one
 * `Authorization: Bearer`, counted on the raw header list, no
 * `Soorma-Delegation`, an RFC 6750 b64token of at most 4096 characters, and the
 * accepted prefix. Any other prefix, an agent's (`soorma_ac_`), a delegation
 * credential's (`soorma_dc_`), or one unknown, is refused by kind, without
 * verifying. The prefix only selects how a credential is checked: it is
 * accepted only after it verifies (BR-PR-07).
 */
export function presentedCredential(
  rawHeaders: readonly string[],
  prefix: string,
): string | undefined {
  if (rawHeaderValues(rawHeaders, 'Soorma-Delegation').length > 0) return undefined;
  const values = rawHeaderValues(rawHeaders, 'Authorization');
  if (values.length !== 1) return undefined;
  const match = /^Bearer ([^\s]+)$/i.exec(values[0]!);
  const credential = match?.[1];
  if (!credential || credential.length > MAX_CREDENTIAL || !B64TOKEN.test(credential))
    return undefined;
  return credential.startsWith(prefix) ? credential : undefined;
}

/** The presented sign-in token, or undefined when the presentation is refused. */
export function presentedSignIn(rawHeaders: readonly string[]): string | undefined {
  return presentedCredential(rawHeaders, SIGN_IN_PREFIX);
}

/** The prefix of a human environment credential (credentials.md). */
export const ENVIRONMENT_CREDENTIAL_PREFIX = 'soorma_ec_';

/**
 * At S2's renewal, ending, and grantToHuman (BR-PR-03): the presented
 * environment credential, as a secret (NP-EHA-14), or undefined: refused.
 */
export function presentedEnvironmentCredential(
  rawHeaders: readonly string[],
): SecretText | undefined {
  const credential = presentedCredential(rawHeaders, ENVIRONMENT_CREDENTIAL_PREFIX);
  return credential === undefined ? undefined : asSecretText(credential);
}

export type SignInCheck =
  | { accepted: true; claims: SignInClaims; status: Extract<SignInStatus, { status: 'live' }> }
  | { accepted: false; code: 'credential_refused' | 'credential_expired' };

export interface SignInPerimeterOptions {
  /** The leeway on the token check; the organization level's own by default (U2 P-01). */
  tolerance?: SignInTolerance;
  /**
   * Fetches the verify keys again, or joins a fetch in progress, or does
   * nothing inside its rate limit (U4 NP-EHA-03). Called at most once per check.
   */
  refetch?: () => Promise<void>;
  /** `Retry-After` when no verify key is held at all (BR-IS-02). */
  retryAfterSeconds?: number;
}

export class SignInPerimeter {
  private readonly keys: SignInKeySource;
  private readonly organization: string;
  private readonly clock: Clock;
  private readonly status: (claims: SignInClaims) => Promise<SignInStatus>;
  private readonly options: SignInPerimeterOptions;

  /**
   * `status` is O3: the sign-in's status as its record says (U2 A7 at an
   * environment; the organization level's own record at S1). Only `live` is
   * accepted. A thrown UnavailableError propagates: unavailable, never a pass.
   */
  constructor(
    keys: SignInKeySource,
    organization: string,
    clock: Clock,
    status: (claims: SignInClaims) => Promise<SignInStatus>,
    options: SignInPerimeterOptions = {},
  ) {
    this.keys = keys;
    this.organization = organization;
    this.clock = clock;
    this.status = status;
    this.options = options;
  }

  async check(rawHeaders: readonly string[]): Promise<SignInCheck> {
    const token = presentedSignIn(rawHeaders);
    if (token === undefined) return { accepted: false, code: 'credential_refused' };
    let verified = await this.verify(token);
    if (verified.status === 'unknownKey' && this.options.refetch) {
      await this.options.refetch();
      verified = await this.verify(token);
    }
    if (verified.status === 'unknownKey' && !this.keys.hasKeys())
      throw new UnavailableError('no verify keys held', this.options.retryAfterSeconds ?? 1);
    if (verified.status === 'expired') return { accepted: false, code: 'credential_expired' };
    if (verified.status !== 'valid') return { accepted: false, code: 'credential_refused' };
    const status = await this.status(verified.claims);
    if (status.status !== 'live') return { accepted: false, code: 'credential_refused' };
    return { accepted: true, claims: verified.claims, status };
  }

  private verify(token: string) {
    return verifySignIn(
      token,
      this.keys,
      this.organization,
      this.clock.now(),
      this.options.tolerance ?? ORGANIZATION_TOLERANCE,
    );
  }
}
