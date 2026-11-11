// SPDX-License-Identifier: FSL-1.1-ALv2
//
// The human-only class (U3 D-AE-03; PF §8b, FR-016; ID FR-013; ID OB-16):
// the permissions the plane PRDs declare human-only. Never an agent's,
// whatever its standing set holds. **One definition**: P3 refuses them at
// evaluation (defence in depth), and U5's registration check imports this
// export, never a copy. Matched literally, never by pattern. A later plane PRD
// declaring another adds it here.
export const HUMAN_ONLY_PERMISSIONS: readonly string[] = Object.freeze([
  'grant:human',
  'human:manage',
  'agent:delegate',
]);
