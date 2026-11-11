// SPDX-License-Identifier: FSL-1.1-ALv2
//
// A direct human operation's authority (U4 D-EHA-13; BR-EV-01 to 06; ID §8b
// O8). Effective authority for a human is the human's grants in E, read
// through the seam (grantedSet, then contains), computed here and nowhere
// else (I5): no surface, P4, or P7 composes or tests a human's set.
//
// - evaluateHuman: allowed when the human's granted set contains every
//   required permission. Deny by default: no grant, no permission
// - holdsAnyGrant: true when the human holds at least one grant in E, the
//   condition of environment credential issuance (ID FR-010)
// - No human-only refusal for a human (BR-EV-03): that class applies to agents
// - A read failure rejects, and the caller answers unavailable (BR-EV-06)
import type { EnvironmentRef, PermissionId, PolicyDecision } from '@soorma/policy-decision-seam';

export interface HumanAuthorityInput {
  /** P11, built for E over P4's human GrantSource (D-EHA-14). */
  readonly policy: PolicyDecision;
  readonly environment: EnvironmentRef;
  readonly principal: string;
}

export async function evaluateHuman(
  input: HumanAuthorityInput & { readonly required: Iterable<PermissionId> },
): Promise<{ readonly allowed: boolean }> {
  const required = new Set(input.required);
  if (required.size === 0) throw new RangeError('evaluateHuman requires at least one permission');
  const granted = await input.policy.grantedSet(
    { kind: 'human', principal: input.principal },
    input.environment,
  );
  return { allowed: input.policy.contains(granted, required) };
}

export async function holdsAnyGrant(input: HumanAuthorityInput): Promise<boolean> {
  const granted = await input.policy.grantedSet(
    { kind: 'human', principal: input.principal },
    input.environment,
  );
  return granted.size > 0;
}
