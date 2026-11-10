// SPDX-License-Identifier: FSL-1.1-ALv2
//
// Step 9, first half: origin (U3 BR-OR-01 to 06; D-AE-01, 07, 24). Origin is
// computed here only, from the presenter's Registration View in the
// request's agent-facts read, never from the draft (BR-DV-04; seam
// containment: origin stamping, O12 included, stays in core).
//
// | Situation                                        | Outcome                           |
// |--------------------------------------------------|-----------------------------------|
// | presenter not found                              | forbidden, presenter_unresolved   |
// | no inbound; autonomy declared                    | autonomous, stamped here          |
// | no inbound; not declared                         | forbidden, o12_undeclared (O12)   |
// | inbound autonomous; declared                     | autonomous, propagated unchanged  |
// | inbound autonomous; not declared                 | forbidden, o12_undeclared         |
// | inbound delegated, or a value this version lacks | forbidden, origin_unsupported     |
//
// The fifth row is GAP-AE-001's work-around (soorma-prd#30; pre-release
// statement 9): an autonomous origin, stamped or propagated, requires the
// presenter's own declaration. Allowing it later is additive. Autonomy
// declared defaults to no (PF §7a).
import { ok, refuse, type Result, type VerifiedInbound } from '@soorma/envelope';
import type { RegistrationView } from './agent-facts.ts';

export type Origin = 'autonomous';

export function resolveOrigin(
  presenter: RegistrationView | undefined,
  inbound: VerifiedInbound | undefined,
): Result<Origin> {
  if (!presenter) return refuse('forbidden', 'presenter_unresolved');
  if (inbound && inbound.originMode !== 'autonomous')
    return refuse('forbidden', 'origin_unsupported');
  if (presenter.autonomyDeclared !== true) return refuse('forbidden', 'o12_undeclared');
  return ok('autonomous');
}
