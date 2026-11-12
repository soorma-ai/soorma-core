// SPDX-License-Identifier: FSL-1.1-ALv2
//
// The agent credential's record (U6 NP-AC-03; D-AC-14, 15; BR-CR-AC-05;
// BR-RN-02, 06): one row per lineage. Bootstrap writes it; renewal moves its
// expiry, never backwards, and only for the agent and instance the token
// names; nothing else ever changes it. Writes run over the caller's
// transaction, with the attribution record. Times are whole seconds, so a
// token's exp and the row agree.
import { environmentParams, type Tx } from '@soorma/env-store';
import type { EnvironmentRef } from '@soorma/policy-decision-seam';
import type { Queryable } from '@soorma/service-kit';
import { AGENT_CREDENTIAL_LIFETIME_MS, LINEAGE_MAX_AGE_MS } from './lifetimes.ts';
import { SQL } from './sql.ts';

export interface AgentCredentialRecord {
  readonly agent: string;
  readonly instance: string;
  /** The registration secret record that bootstrapped it. */
  readonly secret: string;
  /** The lineage's start. */
  readonly issuedAt: Date;
  readonly lineageEndsAt: Date;
  /** The latest expiry minted for it. */
  readonly expiresAt: Date;
}

/** A time truncated to whole seconds, as JWT times are. */
export function wholeSeconds(d: Date): Date {
  return new Date(Math.floor(d.getTime() / 1000) * 1000);
}

/** A new lineage's times (BR-BS-06): its end at M, its first expiry at L or the end. */
export function lineageTimes(now: Date): { issuedAt: Date; lineageEndsAt: Date; expiresAt: Date } {
  const issuedAt = wholeSeconds(now);
  const lineageEndsAt = new Date(issuedAt.getTime() + LINEAGE_MAX_AGE_MS);
  const expiresAt = new Date(
    Math.min(issuedAt.getTime() + AGENT_CREDENTIAL_LIFETIME_MS, lineageEndsAt.getTime()),
  );
  return { issuedAt, lineageEndsAt, expiresAt };
}

/** A renewal's expiry (BR-RN-06; D-AC-02): now + L, never past the lineage end. */
export function renewedExpiry(now: Date, lineageEndsAt: Date): Date {
  return new Date(
    Math.min(wholeSeconds(now).getTime() + AGENT_CREDENTIAL_LIFETIME_MS, lineageEndsAt.getTime()),
  );
}

export async function insertAgentCredential(
  tx: Tx,
  input: {
    cid: string;
    environment: EnvironmentRef;
    agent: string;
    instance: string;
    secret: string;
    issuedAt: Date;
    lineageEndsAt: Date;
    expiresAt: Date;
  },
): Promise<void> {
  await tx.query(SQL.insertAgentCredential, [
    input.cid,
    ...environmentParams(input.environment),
    input.agent,
    input.instance,
    input.secret,
    input.issuedAt,
    input.lineageEndsAt,
    input.expiresAt,
  ]);
}

/** The record by cid in E, uncached (BR-RN-02). */
export async function readAgentCredential(
  store: Queryable,
  cid: string,
  environment: EnvironmentRef,
): Promise<AgentCredentialRecord | undefined> {
  const [row] = await store.query<{
    agent: string;
    instance: string;
    secret: string;
    issued_at: Date;
    lineage_ends_at: Date;
    expires_at: Date;
  }>(SQL.agentCredentialById, [cid, ...environmentParams(environment)]);
  return row
    ? {
        agent: row.agent,
        instance: row.instance,
        secret: row.secret,
        issuedAt: row.issued_at,
        lineageEndsAt: row.lineage_ends_at,
        expiresAt: row.expires_at,
      }
    : undefined;
}

/**
 * Renewal's write (BR-RN-06, 07): the record's expiry becomes the later of its
 * value and `expiresAt`, only for the cid, agent, and instance the token
 * names. Undefined when no such record exists in E (`record_mismatch`).
 */
export async function renewAgentCredentialRecord(
  tx: Tx,
  input: {
    cid: string;
    environment: EnvironmentRef;
    agent: string;
    instance: string;
    expiresAt: Date;
  },
): Promise<{ expiresAt: Date; lineageEndsAt: Date } | undefined> {
  const [row] = await tx.query<{ expires_at: Date; lineage_ends_at: Date }>(
    SQL.renewAgentCredential,
    [
      input.cid,
      ...environmentParams(input.environment),
      input.agent,
      input.instance,
      input.expiresAt,
    ],
  );
  return row ? { expiresAt: row.expires_at, lineageEndsAt: row.lineage_ends_at } : undefined;
}
