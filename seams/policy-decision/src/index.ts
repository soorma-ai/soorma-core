// SPDX-License-Identifier: Apache-2.0
//
// The policy-decision seam (PF §12 v1.3; M1-FR-13; U3 D-AE-02; BR-SEAM).
// Type definitions only: no code, no configuration selection, no published
// interface (BR-SEAM-01). The default implementation is P11,
// @soorma/policy-decision.
//
// The seam has the two halves PF §12 states, and **no operation returns an
// effective set** (BR-SEAM-02). It decides containment, never composition:
// the intersection across a chain, origin stamping (O12 included), chain
// append and maxChainDepth, re-broadening, and the human-only class stay in
// core (BR-SEAM-05).

/** A permission identifier: flat, opaque, compared exactly (BR-ID-06, 08). */
export type PermissionId = string;

/** A finite set of permission identifiers. The empty set is the bottom (L3). */
export type PermissionSet = ReadonlySet<PermissionId>;

/** Whose granted set is wanted: an agent, or a human principal. */
export type PrincipalRef =
  | { readonly kind: 'agent'; readonly agent: string }
  | { readonly kind: 'human'; readonly principal: string };

/** An environment: the scope every grant is keyed on (PF FR-021). */
export interface EnvironmentRef {
  readonly organization: string;
  readonly project: string;
  readonly environment: string;
}

/** The policy-decision interface: both halves of PF §12, nothing more. */
export interface PolicyDecision {
  /** One principal's own granted set in an environment. Reads storage. */
  grantedSet(principal: PrincipalRef, environment: EnvironmentRef): Promise<PermissionSet>;
  /** Whether every member of `requiredSet` is in `effectiveSet`. */
  contains(effectiveSet: PermissionSet, requiredSet: PermissionSet): boolean;
}
