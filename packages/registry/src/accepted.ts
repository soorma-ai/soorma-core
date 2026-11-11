// SPDX-License-Identifier: FSL-1.1-ALv2
//
// The accepted-identifier set (BR-ACC-01 to 03; M1-FR-15): exactly the nine
// plane-declared permission identifiers, defined once, here. A recorded
// delivery limit, not specified behaviour: tenant-defined identifiers are
// unbuilt (GAP-INT-006, soorma-prd#24), and widening is additive (pre-release
// statement 4). The schema accepts any well-formed identifier (BR-ACC-02), so
// acceptance is checked in code. Matched literally, never by pattern.

/** PF's seven and ID's two (domain-entities, *Accepted-Identifier Set*). */
export const ACCEPTED_PERMISSIONS: readonly string[] = Object.freeze([
  'agent:register',
  'credential:revoke',
  'agent:retire',
  'grant:human',
  'event:publish',
  'event:subscribe',
  'attribution:read',
  'human:manage',
  'agent:delegate',
]);

const ACCEPTED = new Set(ACCEPTED_PERMISSIONS);

export function isAcceptedIdentifier(identifier: string): boolean {
  return ACCEPTED.has(identifier);
}

/** At most this many pointers on unknown_permission (D-EHA-06). */
export const MAX_UNACCEPTED_POINTERS = 10;

/**
 * The positions of identifiers that are not accepted, in order, at most 10:
 * the pointers of `unknown_permission` (`/permissions/{i}`).
 */
export function unacceptedPositions(permissions: readonly string[]): number[] {
  const out: number[] = [];
  for (const [i, p] of permissions.entries()) {
    if (!ACCEPTED.has(p)) out.push(i);
    if (out.length === MAX_UNACCEPTED_POINTERS) break;
  }
  return out;
}
