// SPDX-License-Identifier: FSL-1.1-ALv2
//
// Attribution records (BR-AT-01 to 09; D-EHA-03, 04, 17, 31; NP-EHA-07). One
// record per state-changing operation, written in the same transaction as its
// write. The whole shape is defined here, once, for every actor kind:
//   human          the principal and the credential presented (a sign-in at
//                  issuance, the environment credential otherwise); no chain,
//                  origin, or re-broadening
//   configuration  no principal, credential, chain, or origin
//   agent          (U6, U7) the registration, the instance, the resolved
//                  sponsor as of the write, the credential where presented;
//                  with an envelope, the stamped chain, origin, and
//                  re-broadening outcome (U3 BR-ST-08)
// The writer refuses an inconsistent record before any SQL (fail closed: a
// programming error), and the store's CHECK constraints refuse it again.
// Scope, actor, chain, origin, and sponsor are recoverable from the row alone
// (BR-AT-07). Refusals write no record (BR-AT-09).
import { environmentParams, type Tx } from '@soorma/env-store';
import type { EnvironmentRef } from '@soorma/policy-decision-seam';
import { SQL } from './sql.ts';

export type Actor =
  | {
      readonly kind: 'human';
      readonly principal: string;
      readonly credential: {
        readonly kind: 'signIn' | 'environmentCredential';
        readonly id: string;
      };
    }
  | { readonly kind: 'configuration' }
  | {
      readonly kind: 'agent';
      readonly registration: string;
      readonly instance: string;
      readonly sponsor: string;
      readonly credential?: { readonly kind: string; readonly id: string };
    };

/** The stamped envelope's facts, for an agent's envelope-bearing operation. */
export interface EnvelopeFacts {
  readonly chain: readonly unknown[];
  readonly origin: { readonly originMode: string; readonly delegatingPrincipal?: string };
  readonly reBroadening: { readonly loadBearing: boolean; readonly hop?: number };
}

export interface AttributionRecord {
  readonly id: string;
  readonly recordedAt: Date;
  /** Absent only for the configured first grant, which has no request. */
  readonly requestId?: string;
  /** The scope: E's configured identity (BR-AT-06). */
  readonly environment: EnvironmentRef;
  readonly operation: string;
  readonly actor: Actor;
  readonly target?: { readonly kind: string; readonly id: string };
  readonly selfGrant?: boolean;
  readonly envelope?: EnvelopeFacts;
}

/** An inconsistent record: a defect in the caller, refused before any write (BR-AT-05). */
export class AttributionRecordError extends Error {
  constructor(reason: string) {
    super(`inconsistent attribution record: ${reason}`);
    this.name = 'AttributionRecordError';
  }
}

/** BR-AT-05, as the store's CHECK constraints repeat it. */
export function checkRecord(record: AttributionRecord): void {
  const { actor, envelope } = record;
  if (actor.kind !== 'agent' && envelope)
    throw new AttributionRecordError(
      `a ${actor.kind} actor carries no chain, origin, or re-broadening`,
    );
  if (actor.kind === 'human' && (!actor.principal || !actor.credential.id))
    throw new AttributionRecordError('a human actor names its principal and credential');
  if (actor.kind === 'agent' && (!actor.registration || !actor.instance || !actor.sponsor))
    throw new AttributionRecordError(
      'an agent actor names its registration, instance, and sponsor',
    );
  if (envelope) {
    const { loadBearing, hop } = envelope.reBroadening;
    if (loadBearing !== (hop !== undefined))
      throw new AttributionRecordError('a hop exactly when re-broadening is load-bearing');
    if (hop !== undefined && (!Number.isInteger(hop) || hop < 0 || hop >= envelope.chain.length))
      throw new AttributionRecordError('the hop is inside the chain');
  }
}

/** Writes one record over the caller's transaction, after BR-AT-05's checks. */
export async function recordAttribution(tx: Tx, record: AttributionRecord): Promise<void> {
  checkRecord(record);
  const { actor, envelope } = record;
  const human = actor.kind === 'human' ? actor : undefined;
  const agent = actor.kind === 'agent' ? actor : undefined;
  const credential = human?.credential ?? agent?.credential;
  await tx.query(SQL.insertRecord, [
    record.id,
    record.recordedAt,
    record.requestId ?? null,
    ...environmentParams(record.environment),
    record.operation,
    actor.kind,
    human?.principal ?? null,
    credential?.kind ?? null,
    credential?.id ?? null,
    agent?.registration ?? null,
    agent?.instance ?? null,
    agent?.sponsor ?? null,
    record.target?.kind ?? null,
    record.target?.id ?? null,
    record.selfGrant ?? false,
    envelope ? JSON.stringify(envelope.chain) : null,
    envelope ? JSON.stringify(envelope.origin) : null,
    envelope ? envelope.reBroadening.loadBearing : null,
    envelope?.reBroadening.hop ?? null,
  ]);
}
