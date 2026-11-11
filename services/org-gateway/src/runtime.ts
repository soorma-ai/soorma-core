// SPDX-License-Identifier: FSL-1.1-ALv2
//
// S1's components, wired once. `assembleRuntime` takes the already-built
// store, keys, and clock, so tests wire the same graph over a test database;
// `startRuntime` (main.ts) builds them from configuration.
import {
  ORGANIZATION_TOLERANCE,
  pseudonym,
  type Clock,
  type HumanPseudonym,
  type PrincipalReference,
  type SignInStatus,
} from '@soorma/service-kit';
import { OrgIdentity, type KeyRing } from '@soorma/org-identity';
import { SignInPerimeter } from '@soorma/perimeter';
import type { ContractValidator } from './contract-validator.ts';
import type { SecurityLog } from './security-log.ts';

export interface Runtime {
  organization: string;
  identity: OrgIdentity;
  perimeter: SignInPerimeter;
  keys: KeyRing;
  clock: Clock;
  log: SecurityLog;
  validator: ContractValidator;
  /** The log pseudonym of a reference (NFR-OI-22). */
  pseudonym(reference: PrincipalReference): HumanPseudonym;
}

export function assembleRuntime(parts: {
  organization: string;
  identity: OrgIdentity;
  keys: KeyRing;
  clock: Clock;
  log: SecurityLog;
  validator: ContractValidator;
}): Runtime {
  // O3 from S1's own record, live or not (U4 D-CG-EHA-06). The `live` answer's
  // expiry is the token's; S1 uses none of it.
  const perimeter = new SignInPerimeter(
    parts.keys,
    parts.organization,
    parts.clock,
    async (claims): Promise<SignInStatus> =>
      (await parts.identity.checkSignIn(claims))
        ? { status: 'live', expiresAt: claims.expiresAt }
        : { status: 'ended' },
    { tolerance: ORGANIZATION_TOLERANCE },
  );
  return {
    ...parts,
    perimeter,
    pseudonym: (reference) => pseudonym(reference, parts.keys.logPseudonymKey),
  };
}
