// SPDX-License-Identifier: FSL-1.1-ALv2
//
// Grants to human principals (BR-GR-05 to 09; BR-FG-01 to 03; NP-EHA-08, 10).
// - A grant is one row, its permissions a sorted, de-duplicated set, written
//   once (the app role has no UPDATE or DELETE on grants)
// - selfGrant: the target is the actor (both are principals of E's
//   organization, which the caller has checked)
// - The configured first grant is applied at most once per principal, by the
//   store's partial unique index: a start-up that loses the race writes nothing
// - The human GrantSource reads the union of a principal's grants in E,
//   uncached, so a grant is visible to the next request (D-EHA-14)
// Writes run over the caller's transaction, so each commits with its
// attribution record (D-EHA-17).
import type { Tx } from '@soorma/env-store';
import { environmentParams } from '@soorma/env-store';
import type { EnvironmentRef, PermissionId, PrincipalRef } from '@soorma/policy-decision-seam';
import type { Queryable } from '@soorma/service-kit';
import { SQL } from './sql.ts';

export type GrantedBy =
  | { readonly kind: 'principal'; readonly principal: string; readonly credential: string }
  | { readonly kind: 'configuration' };

export interface GrantRecord {
  readonly id: string;
  readonly environment: EnvironmentRef;
  readonly principal: string;
  readonly permissions: readonly string[];
  readonly grantedBy: GrantedBy;
  readonly selfGrant: boolean;
  readonly grantedAt: Date;
}

/** A set, as stored: sorted and de-duplicated (NP-EHA-10). */
export function asStoredSet(permissions: Iterable<string>): string[] {
  return [...new Set(permissions)].sort();
}

/** One grant by a principal (BR-GR-05). Granting what is already held is allowed (BR-GR-06). */
export async function createGrant(
  tx: Tx,
  input: {
    id: string;
    environment: EnvironmentRef;
    principal: string;
    permissions: Iterable<string>;
    grantedBy: { principal: string; credential: string };
    grantedAt: Date;
  },
): Promise<GrantRecord> {
  const permissions = asStoredSet(input.permissions);
  if (permissions.length === 0) throw new RangeError('a grant names at least one permission');
  const selfGrant = input.grantedBy.principal === input.principal;
  await tx.query(SQL.insertGrant, [
    input.id,
    ...environmentParams(input.environment),
    input.principal,
    permissions,
    input.grantedBy.principal,
    input.grantedBy.credential,
    selfGrant,
    input.grantedAt,
  ]);
  return {
    id: input.id,
    environment: input.environment,
    principal: input.principal,
    permissions,
    grantedBy: { kind: 'principal', ...input.grantedBy },
    selfGrant,
    grantedAt: input.grantedAt,
  };
}

/**
 * The configured first grant (BR-FG-01, 02): the grant when this call wrote it,
 * or undefined when one already exists for the principal in E.
 */
export async function applyFirstGrant(
  tx: Tx,
  input: {
    id: string;
    environment: EnvironmentRef;
    principal: string;
    permissions: Iterable<string>;
    grantedAt: Date;
  },
): Promise<GrantRecord | undefined> {
  const permissions = asStoredSet(input.permissions);
  const rows = await tx.query<{ id: string }>(SQL.insertFirstGrant, [
    input.id,
    ...environmentParams(input.environment),
    input.principal,
    permissions,
    input.grantedAt,
  ]);
  if (rows.length === 0) return undefined;
  return {
    id: input.id,
    environment: input.environment,
    principal: input.principal,
    permissions,
    grantedBy: { kind: 'configuration' },
    selfGrant: false,
    grantedAt: input.grantedAt,
  };
}

/** P11's GrantSource, by shape (U3 D-AE-02): P4 does not import P11. */
export interface GrantSource {
  grantsOf(principal: PrincipalRef, environment: EnvironmentRef): Promise<Iterable<PermissionId>>;
}

/**
 * The human GrantSource P11 reads through (D-EHA-14): a human's held set in E,
 * uncached. No agent principal reaches S2 in M1 (BR-EV-05), so an agent's set
 * here is empty. A read failure rejects, and the caller fails closed.
 */
export function createHumanGrantSource(store: Queryable): GrantSource {
  return Object.freeze({
    async grantsOf(
      principal: PrincipalRef,
      environment: EnvironmentRef,
    ): Promise<Iterable<PermissionId>> {
      if (principal.kind !== 'human') return [];
      const rows = await store.query<{ permission: string }>(SQL.heldSet, [
        ...environmentParams(environment),
        principal.principal,
      ]);
      return rows.map((r) => r.permission);
    },
  });
}
