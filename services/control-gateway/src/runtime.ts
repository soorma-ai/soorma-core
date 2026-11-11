// SPDX-License-Identifier: FSL-1.1-ALv2
//
// S2's components, wired once (logical-components §1). assembleRuntime takes
// the already-built store, key ring, clock, and S1 port, so tests wire the
// same graph over a test store and a stub organization level; start
// (main.ts) builds them from configuration.
import type { EnvironmentKeyRing } from '@soorma/credentials';
import { SignInPerimeter } from '@soorma/perimeter';
import { createPolicyDecision } from '@soorma/policy-decision';
import type { EnvironmentRef, PolicyDecision } from '@soorma/policy-decision-seam';
import { createHumanGrantSource } from '@soorma/registry';
import {
  pseudonym,
  type Clock,
  type HumanPseudonym,
  type SecretBytes,
  type Semaphore,
  type SignInKeySource,
  type Store,
} from '@soorma/service-kit';
import type { ContractValidator } from './contract-validator.ts';
import type { OrgLevel } from './org-level.ts';
import type { SecurityLog } from './security-log.ts';
import { RETRY_AFTER_SECONDS, SIGN_IN_TOLERANCE } from './settings.ts';

export interface Runtime {
  /** E's configured identity (D-EHA-12). */
  environment: EnvironmentRef;
  store: Store;
  ring: EnvironmentKeyRing;
  orgLevel: OrgLevel;
  /** S1's verify keys, read on every sign-in check. */
  keys: SignInKeySource;
  /** The issuance check (P1): S2's tolerance, one refetch, A7's status. */
  signIn: SignInPerimeter;
  /** P11 over P4's uncached human GrantSource (D-EHA-14). */
  policy: PolicyDecision;
  clock: Clock;
  log: SecurityLog;
  validator: ContractValidator;
  /** The request permits (NFR-EHA-04). */
  requests: Semaphore;
  /** A human in E, named only by E's own log pseudonym (NFR-EHA-18). */
  pseudonym(principal: string): HumanPseudonym;
}

export function assembleRuntime(parts: {
  environment: EnvironmentRef;
  store: Store;
  ring: EnvironmentKeyRing;
  orgLevel: OrgLevel;
  keys: SignInKeySource & { refetch?: () => Promise<void> };
  clock: Clock;
  log: SecurityLog;
  validator: ContractValidator;
  requests: Semaphore;
  logPseudonymKey: SecretBytes;
}): Runtime {
  const environment: EnvironmentRef = Object.freeze({ ...parts.environment });
  const signIn = new SignInPerimeter(
    parts.keys,
    environment.organization,
    parts.clock,
    (claims) => parts.orgLevel.signInStatus(claims.sid),
    {
      tolerance: SIGN_IN_TOLERANCE,
      ...(parts.keys.refetch ? { refetch: parts.keys.refetch } : {}),
      retryAfterSeconds: RETRY_AFTER_SECONDS,
    },
  );
  return {
    environment,
    store: parts.store,
    ring: parts.ring,
    orgLevel: parts.orgLevel,
    keys: parts.keys,
    signIn,
    policy: createPolicyDecision({ environment, grants: createHumanGrantSource(parts.store) }),
    clock: parts.clock,
    log: parts.log,
    validator: parts.validator,
    requests: parts.requests,
    pseudonym: (principal) =>
      pseudonym({ organization: environment.organization, principal }, parts.logPseudonymKey),
  };
}
