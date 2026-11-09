// SPDX-License-Identifier: FSL-1.1-ALv2
//
// S1's components, wired once. `assembleRuntime` takes the already-built
// store, keys, and clock, so tests wire the same graph over a test database;
// `startRuntime` (main.ts) builds them from configuration.
import {
  OrgIdentity,
  pseudonym,
  type Clock,
  type HumanPseudonym,
  type KeyRing,
  type PrincipalReference,
} from '@soorma/org-identity';
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
  const perimeter = new SignInPerimeter(parts.keys, parts.organization, parts.clock, (claims) =>
    parts.identity.checkSignIn(claims),
  );
  return {
    ...parts,
    perimeter,
    pseudonym: (reference) => pseudonym(reference, parts.keys.logPseudonymKey),
  };
}
