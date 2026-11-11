// SPDX-License-Identifier: FSL-1.1-ALv2
//
// Step 9, second half: effective authority (U3 BR-AU-01 to 10; D-AE-02, 03,
// 09, 20, 21; PF FR-014, FR-017, §8b). **The one place effective authority
// is computed** (I5; BR-AU-01): no other module, surface, or seam computes an
// intersection or a union of permission sets.
//
// For a request needing R:
//   S   the presenter's standing set           policy.grantedSet(presenter, E)
//   D   the presenter's re-broadening declaration (its Registration View)
//   P   the delegating principal's set: in autonomous origin it imposes
//       nothing, and is absent
//   U   U1 ∩ … ∩ Un, one term per DISTINCT agent in the forwarded chain, its
//       standing set read now; absent (imposing nothing) with no upstream hop
//
//   N = S ∩ P ∩ U            W = S ∩ P ∩ (U ∪ D)
//   allowed      = R holds no human-only permission, and contains(W, R)
//   load-bearing = allowed, and not contains(N, R)
//
// N and W are composed here, in core; the seam is asked only for granted sets
// and for containment, never for an effective set (BR-AU-02). Neither leaves
// this function. Forwarded re-broadening records are never read: re-broadening
// is local to its hop (D-AE-20). At a first hop W = N, so it is never
// load-bearing (BR-AU-07). W intersects with S, so a declaration wider than
// the standing set grants nothing (BR-AU-04).
//
// An upstream agent that did not resolve has the empty set as its term, exactly
// as a registered agent with no grants, and evaluation continues (D-AE-09). It
// is denied unless the presenter's re-broadening covers R; a denial names
// upstream_unresolved when an upstream agent did not resolve (BR-AU-10).
import type {
  EnvironmentRef,
  PermissionId,
  PermissionSet,
  PolicyDecision,
} from '@soorma/policy-decision-seam';
import { HUMAN_ONLY_PERMISSIONS } from './human-only.ts';

export interface EvaluationInput {
  readonly policy: PolicyDecision;
  readonly environment: EnvironmentRef;
  /** The presenting agent. */
  readonly presenter: string;
  /** D: the presenter's re-broadening declaration. */
  readonly declaration: PermissionSet;
  /** The distinct agents of the forwarded chain; empty at a first hop. */
  readonly upstream: readonly string[];
  /** Upstream agents the agent-facts read did not find. */
  readonly unresolved?: ReadonlySet<string>;
  /** P, the delegating principal's set. Absent: it imposes nothing (autonomous origin). */
  readonly principal?: PermissionSet;
  /** R: non-empty, every member required. */
  readonly required: PermissionSet;
}

export type EvaluationReason = 'human_only_permission' | 'upstream_unresolved' | 'authority_denied';

export interface Evaluation {
  readonly allowed: boolean;
  readonly loadBearing: boolean;
  readonly reason?: EvaluationReason;
}

function meet(a: PermissionSet, b: PermissionSet): Set<PermissionId> {
  return new Set([...a].filter((x) => b.has(x)));
}

function join(a: PermissionSet, b: PermissionSet): Set<PermissionId> {
  return new Set([...a, ...b]);
}

const denied = (reason: EvaluationReason): Evaluation => ({
  allowed: false,
  loadBearing: false,
  reason,
});

export async function evaluateAgent(input: EvaluationInput): Promise<Evaluation> {
  const { policy, environment, required } = input;

  // The human-only class, before containment is asked (BR-AU-03).
  if (HUMAN_ONLY_PERMISSIONS.some((p) => required.has(p))) return denied('human_only_permission');

  // Each distinct agent's granted set, read once (D-AE-21).
  const granted = new Map<string, PermissionSet>();
  const grantedSet = async (agent: string): Promise<PermissionSet> => {
    let set = granted.get(agent);
    if (!set) {
      set = await policy.grantedSet({ kind: 'agent', agent }, environment);
      granted.set(agent, set);
    }
    return set;
  };

  const S = await grantedSet(input.presenter);
  let U: PermissionSet | undefined;
  for (const agent of new Set(input.upstream)) {
    const term = await grantedSet(agent);
    U = U === undefined ? new Set(term) : meet(U, term);
  }

  const SP = input.principal === undefined ? S : meet(S, input.principal);
  const N = U === undefined ? SP : meet(SP, U);
  const W = U === undefined ? SP : meet(SP, join(U, input.declaration));

  if (!policy.contains(W, required))
    return denied(
      input.upstream.some((agent) => input.unresolved?.has(agent))
        ? 'upstream_unresolved'
        : 'authority_denied',
    );
  return { allowed: true, loadBearing: !policy.contains(N, required) };
}
