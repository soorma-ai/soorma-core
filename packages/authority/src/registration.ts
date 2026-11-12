// SPDX-License-Identifier: FSL-1.1-ALv2
//
// The registration request's own sets (U5 D-AR-10; BR-RQ-03, 04), decided
// before any state is read (check-order step 6):
// - humanOnly: the standing set's members in the human-only class, which has
//   one definition, HUMAN_ONLY_PERMISSIONS (U3 D-AE-03). Never a copy
// - outsideStanding: the declaration's members the standing set does not
//   contain, by the seam's containment (PF FR-019), never a local comparison
// Both are index lists, in request order: the pointers of
// human_only_permission and declaration_outside_standing.
import type { PermissionId, PolicyDecision } from '@soorma/policy-decision-seam';
import { HUMAN_ONLY_PERMISSIONS } from './human-only.ts';

const HUMAN_ONLY = new Set(HUMAN_ONLY_PERMISSIONS);

export interface RegistrationRequestCheck {
  readonly humanOnly: readonly number[];
  readonly outsideStanding: readonly number[];
}

export function checkRegistrationRequest(input: {
  readonly policy: PolicyDecision;
  readonly standing: readonly PermissionId[];
  readonly declared: readonly PermissionId[];
}): RegistrationRequestCheck {
  const standing = new Set(input.standing);
  return {
    humanOnly: input.standing.flatMap((p, i) => (HUMAN_ONLY.has(p) ? [i] : [])),
    outsideStanding: input.declared.flatMap((p, i) =>
      input.policy.contains(standing, new Set([p])) ? [] : [i],
    ),
  };
}
