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
// - readHumanAuthority: one read, then every check over that set through
//   evaluateHeld (U5: the agent:register check, the sponsor ceiling, the Admin
//   test), and the set itself as a snapshot. The set is never exposed as a
//   mutable value
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

/**
 * A human's held set in E, read once, behind the one evaluator (U5 D-AR-07;
 * NP-AR-05). Frozen; the set itself is never exposed.
 */
export interface HumanAuthority {
  /** `evaluateHeld` over the held set. `required` must not be empty. */
  allows(required: Iterable<PermissionId>): boolean;
  /** The indexes of `candidate`'s members the held set does not contain, in order. */
  exceeding(candidate: readonly PermissionId[]): number[];
  /** The held set as read, sorted by code unit (D-CG-AR-07), frozen: the ceiling snapshot. */
  snapshot(): readonly PermissionId[];
}

export async function readHumanAuthority(input: HumanAuthorityInput): Promise<HumanAuthority> {
  const read = await input.policy.grantedSet(
    { kind: 'human', principal: input.principal },
    input.environment,
  );
  const held: PermissionSet = new Set(read);
  const { policy } = input;
  const snapshot = Object.freeze([...held].sort());
  const allows = (required: Iterable<PermissionId>): boolean =>
    evaluateHeld({ policy, held, required }).allowed;
  return Object.freeze({
    allows,
    exceeding: (candidate: readonly PermissionId[]): number[] =>
      candidate.flatMap((p, i) => (allows([p]) ? [] : [i])),
    snapshot: (): readonly PermissionId[] => snapshot,
  });
}
