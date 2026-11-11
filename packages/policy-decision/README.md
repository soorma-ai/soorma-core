<!-- SPDX-License-Identifier: FSL-1.1-ALv2 -->

# `@soorma/policy-decision` (P11)

The default implementation of the policy-decision seam
([`seams/policy-decision`](../../seams/policy-decision/src/index.ts), PF §12).

| Operation                             | Answers                                                                                                                             |
| ------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| `grantedSet(principal, environment)`  | One principal's own granted set: an agent's standing set, or a human's grants in the environment, read through a `GrantSource` port |
| `contains(effectiveSet, requiredSet)` | Whether every required identifier is in the set                                                                                     |

- **Literal containment.** Identifiers are compared exactly, with no wildcard, hierarchy, or
  pattern.
- **Deny by default.** An empty or unknown set contains nothing.
- **One environment.** Built for E, it answers only for E, and returns the empty set for any
  other environment.

**It decides containment, never composition.** No operation returns an effective set. The
intersection across a chain, origin stamping, chain depth, re-broadening, and the human-only
class stay in core, in `@soorma/authority`.

A `GrantSource` failure propagates, never read as "no grants". The caller fails closed.

`inMemoryGrantSource` is for tests and fixtures.
