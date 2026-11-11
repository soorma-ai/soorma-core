// SPDX-License-Identifier: FSL-1.1-ALv2
//
// The human environment credential's record (NP-EHA-01 step 9, NP-EHA-09;
// BR-EC-02, 05, 07). Renewal and ending are conditional updates on
// state = 'live', so a renewal racing an end commits exactly one outcome
// (D-EHA-26). Writes run over the caller's transaction, with the attribution
// record (D-EHA-17).
import { environmentParams, type Tx } from '@soorma/env-store';
import type { EnvironmentRef } from '@soorma/policy-decision-seam';
import type { Queryable } from '@soorma/service-kit';
import { SQL } from './sql.ts';
import type { CredentialClaims } from './token.ts';

export interface CredentialRecord {
  readonly principal: string;
  readonly issuedFrom: string;
  readonly expiresAt: Date;
  readonly state: 'live' | 'ended';
}

export async function insertCredential(
  tx: Tx,
  input: {
    id: string;
    environment: EnvironmentRef;
    principal: string;
    issuedFrom: string;
    issuedAt: Date;
    expiresAt: Date;
  },
): Promise<void> {
  await tx.query(SQL.insertCredential, [
    input.id,
    ...environmentParams(input.environment),
    input.principal,
    input.issuedFrom,
    input.issuedAt,
    input.expiresAt,
  ]);
}

export async function readCredential(
  store: Queryable,
  id: string,
  environment: EnvironmentRef,
): Promise<CredentialRecord | undefined> {
  const [row] = await store.query<{
    principal: string;
    issued_from: string;
    expires_at: Date;
    state: 'live' | 'ended';
  }>(SQL.credentialById, [id, ...environmentParams(environment)]);
  return row
    ? {
        principal: row.principal,
        issuedFrom: row.issued_from,
        expiresAt: row.expires_at,
        state: row.state,
      }
    : undefined;
}

export type O3Result =
  | { readonly ok: true; readonly record: CredentialRecord }
  | { readonly ok: false; readonly reason: 'no_record' | 'credential_ended' | 'record_mismatch' };

/**
 * O3 (NP-EHA-01 step 9): the record by cid in E, uncached; it must exist, be
 * live, and name the token's subject. The environment is in the read itself.
 * A store failure rejects (UnavailableError), and the caller fails closed.
 */
export async function checkCredentialRecord(
  store: Queryable,
  claims: CredentialClaims,
): Promise<O3Result> {
  const record = await readCredential(store, claims.cid, claims.environment);
  if (!record) return { ok: false, reason: 'no_record' };
  if (record.principal !== claims.principal) return { ok: false, reason: 'record_mismatch' };
  if (record.state !== 'live') return { ok: false, reason: 'credential_ended' };
  return { ok: true, record };
}

/** Renewal's write: true when the record was live and is now renewed. */
export async function renewCredential(
  tx: Tx,
  input: { id: string; environment: EnvironmentRef; expiresAt: Date },
): Promise<boolean> {
  const rows = await tx.query(SQL.renewCredential, [
    input.id,
    ...environmentParams(input.environment),
    input.expiresAt,
  ]);
  return rows.length === 1;
}

/** Ending's write: true when the record was live and is now ended. */
export async function endCredential(
  tx: Tx,
  input: { id: string; environment: EnvironmentRef; endedAt: Date },
): Promise<boolean> {
  const rows = await tx.query(SQL.endCredential, [
    input.id,
    ...environmentParams(input.environment),
    input.endedAt,
  ]);
  return rows.length === 1;
}
