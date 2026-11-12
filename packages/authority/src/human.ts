// SPDX-License-Identifier: FSL-1.1-ALv2
//
// A direct human operation's authority (U4 D-EHA-13; BR-EV-01 to 06; ID §8b
// O8). Effective authority for a human is the human's grants in E, read
// through the seam (grantedSet, then contains), computed here and nowhere
// else (I5): no surface, P4, or P7 composes or tests a human's set.
//
// - evaluateHeld: the one evaluator of a human's held set (U5 D-AR-07):
//   allowed when the set contains every required permission. Every test of a
//   human's set goes through it, so one read can serve several checks and a
//   recorded snapshot is exactly the set the checks judged
// - evaluateHuman: one read of the human's granted set, then evaluateHeld.
//   Deny by default: no grant, no permission
// - holdsAnyGrant: true when the human holds at least one grant in E, the
//   condition of environment credential issuance (ID FR-010)
// - No human-only refusal for a human (BR-EV-03): that class applies to agents
// - A read failure rejects, and the caller answers unavailable (BR-EV-06)
import type {
  EnvironmentRef,
  PermissionId,
  PermissionSet,
  PolicyDecision,
} from '@soorma/policy-decision-seam';

export interface HumanAuthorityInput {
  /** P11, built for E over P4's human GrantSource (D-EHA-14). */
  readonly policy: PolicyDecision;
  readonly environment: EnvironmentRef;
  readonly principal: string;
}

/** A human's held set, already read once, and the permissions an operation requires. */
export interface HeldEvaluationInput {
  /** P11, whose containment decides (L5). */
  readonly policy: PolicyDecision;
  readonly held: PermissionSet;
  readonly required: Iterable<PermissionId>;
}

/**
 * The one evaluator of a human's held set (U5 D-AR-07): allowed when `held`
 * contains every member of `required`. `required` must not be empty.
 */
export function evaluateHeld(input: HeldEvaluationInput): { readonly allowed: boolean } {
  const required = new Set(input.required);
  if (required.size === 0) throw new RangeError('evaluateHeld requires at least one permission');
  return { allowed: input.policy.contains(input.held, required) };
}

export async function evaluateHuman(
  input: HumanAuthorityInput & { readonly required: Iterable<PermissionId> },
): Promise<{ readonly allowed: boolean }> {
  const required = new Set(input.required);
  if (required.size === 0) throw new RangeError('evaluateHuman requires at least one permission');
  const held = await input.policy.grantedSet(
    { kind: 'human', principal: input.principal },
    input.environment,
  );
  return evaluateHeld({ policy: input.policy, held, required });
}

export async function holdsAnyGrant(input: HumanAuthorityInput): Promise<boolean> {
  const granted = await input.policy.grantedSet(
    { kind: 'human', principal: input.principal },
    input.environment,
  );
  return granted.size > 0;
}
