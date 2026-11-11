// SPDX-License-Identifier: FSL-1.1-ALv2
//
// P11, the policy-decision seam's default (PF §8b Core Baseline; PF §12;
// U3 BR-SEAM-03, 04):
//
// - Flat, opaque identifiers with set semantics
// - Literal containment: requiredSet ⊆ effectiveSet by exact string
//   comparison. No wildcard, no hierarchy, no pattern (ID OB-16)
// - Deny by default: an empty or unknown set contains nothing
// - Scoped to one environment: built for E, it answers only for E, and
//   returns the empty set for any other environment (PF FR-021; I1)
//
// Grants are read through a GrantSource port: an agent's granted set is its
// standing set (served from the request's agent-facts read, U3 NP-04); a
// human's is the union of its grants in E (U4 fills it). A read failure
// propagates, and the caller fails closed.
import type {
  EnvironmentRef,
  PermissionId,
  PermissionSet,
  PolicyDecision,
  PrincipalRef,
} from '@soorma/policy-decision-seam';

/** The port P11 reads grants through. A failure rejects; it never means "none". */
export interface GrantSource {
  grantsOf(principal: PrincipalRef, environment: EnvironmentRef): Promise<Iterable<PermissionId>>;
}

const EMPTY: PermissionSet = new Set<PermissionId>();

function sameEnvironment(a: EnvironmentRef, b: EnvironmentRef): boolean {
  return (
    a.organization === b.organization && a.project === b.project && a.environment === b.environment
  );
}

export function createPolicyDecision(options: {
  environment: EnvironmentRef;
  grants: GrantSource;
}): PolicyDecision {
  const environment: EnvironmentRef = Object.freeze({
    organization: options.environment.organization,
    project: options.environment.project,
    environment: options.environment.environment,
  });
  const { grants } = options;
  return Object.freeze({
    async grantedSet(principal: PrincipalRef, of: EnvironmentRef): Promise<PermissionSet> {
      if (!sameEnvironment(of, environment)) return EMPTY;
      return new Set(await grants.grantsOf(principal, environment));
    },
    contains(effectiveSet: PermissionSet, requiredSet: PermissionSet): boolean {
      for (const permission of requiredSet) if (!effectiveSet.has(permission)) return false;
      return true;
    },
  });
}

/** An in-memory GrantSource, for tests and fixtures. */
export function inMemoryGrantSource(
  grants: Iterable<readonly [PrincipalRef, Iterable<PermissionId>]>,
): GrantSource {
  const key = (p: PrincipalRef): string =>
    p.kind === 'agent' ? `agent\u0000${p.agent}` : `human\u0000${p.principal}`;
  const table = new Map<string, PermissionId[]>();
  for (const [principal, set] of grants) table.set(key(principal), [...set]);
  return {
    grantsOf(principal: PrincipalRef): Promise<Iterable<PermissionId>> {
      return Promise.resolve(table.get(key(principal)) ?? []);
    },
  };
}
