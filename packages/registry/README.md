<!-- SPDX-License-Identifier: FSL-1.1-ALv2 -->

# `@soorma/registry` (P4)

An environment's grants to human principals, and the accepted permission identifiers.
Registrations and their secrets join it with the agent units.

## Accepted identifiers

`ACCEPTED_PERMISSIONS` is the one definition of the nine permission identifiers a grant may
carry in M1:

`agent:register`, `credential:revoke`, `agent:retire`, `grant:human`, `event:publish`,
`event:subscribe`, `attribution:read`, `human:manage`, `agent:delegate`.

The contract's schema accepts any well-formed identifier, so acceptance is checked here, by
literal match (`isAcceptedIdentifier`, `unacceptedPositions`). An unaccepted identifier is
refused `unknown_permission`. Widening the set is additive.

## Grants

- `createGrant(tx, …)` writes one grant: its permissions a sorted, de-duplicated set, written
  once. The app role has no `UPDATE` or `DELETE` on grants. `selfGrant` records that the target
  is the actor.
- `applyFirstGrant(tx, …)` applies the environment's configured first grant to its first Admin
  **at most once per principal**, enforced by a partial unique index, so concurrent start-ups
  write it once.
- `createHumanGrantSource(store, environment)` is the `GrantSource` that
  [`@soorma/authority`](../authority/README.md) reads: the union of a principal's grants in
  the environment, **uncached**, so a grant is visible to the next request.

Every write runs over the caller's transaction ([`env-store`](../env-store/README.md)'s
`withTransaction`), so it commits with its attribution record.
