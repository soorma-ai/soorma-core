// SPDX-License-Identifier: FSL-1.1-ALv2
//
// P8's agent half (U6 D-AC-06, 22; NFR-AC-06 to 11; NFR Design NP-AC-07): the
// bootstrap bound per logical agent, on P8's generic core.
//
// - Keyed on the **presented** agent in E, known or not, so the bound reveals
//   no registration (D-AC-06): the slot is HMAC-SHA-256, under E's counter
//   secret, of the RFC 8785 form of { agent, environment }, mod 2^20, in E's
//   own attempt_slots table
// - The agent's values (NFR-AC-06, 07): at most 60 live attempts in any 60 s;
//   backoff from the 10th consecutive failure, doubling from 1 s, capped at
//   60 s. A security bound, not a tenant quota (NFR-AC-27)
// - Failed attempts are written off the response path by U2's writer pattern;
//   the statement itself joins registrations, so an unknown agent leaves no
//   row (BR-FA-01, 02). Nothing presented is in a record (BR-FA-03)
import { canonicalize } from '@soorma/jcs';
import type { Clock, Queryable, SecretBytes } from '@soorma/service-kit';
import { BatchWriter, type WriterOptions } from './batch-writer.ts';
import { SlotBound, type SlotLimits } from './slot-bound.ts';
import { SQL } from './sql.ts';

/** An environment's identity, as configured. */
export interface AgentEnvironment {
  readonly organization: string;
  readonly project: string;
  readonly environment: string;
}

/** The agent bound's values (NFR-AC-06, 07). */
export const AGENT_BOOTSTRAP_LIMITS: SlotLimits = Object.freeze({
  windowMs: 60_000,
  maxLive: 60,
  backoffFrom: 10,
  backoffCapSeconds: 60,
});

/** The canonical string an agent's slot is keyed on: RFC 8785 of { agent, environment }. */
export function agentSlotKey(environment: AgentEnvironment, agent: string): string {
  return canonicalize({
    agent,
    environment: {
      environment: environment.environment,
      organization: environment.organization,
      project: environment.project,
    },
  }).text;
}

/** The bootstrap bound for one environment's store. */
export class AgentBound extends SlotBound {
  constructor(store: Queryable, counterSecret: SecretBytes, clock: Clock) {
    super(store, counterSecret, clock, AGENT_BOOTSTRAP_LIMITS);
  }
}

/** Why a bootstrap failed, as recorded (failed_bootstrap_attempts.reason). */
export type BootstrapFailureReason =
  | 'bound_refused'
  | 'unsupported_material'
  | 'malformed_secret'
  | 'unknown_secret'
  | 'secret_not_active'
  | 'secret_mismatch'
  | 'registration_not_registered'
  | 'agent_revoked'
  | 'store_unavailable';

export interface FailedBootstrapAttempt {
  readonly environment: AgentEnvironment;
  /** The presented agent: recorded only if it is registered in E. */
  readonly agent: string;
  readonly at: Date;
  readonly refusedByBound: boolean;
  readonly reason: BootstrapFailureReason;
}

/** The Failed Bootstrap Attempt writer: U2's writer pattern, with U6's insert. */
export class FailedBootstrapAttemptWriter extends BatchWriter<FailedBootstrapAttempt> {
  constructor(store: Queryable, options: WriterOptions = {}) {
    super(
      store,
      SQL.insertFailedBootstrapAttempts,
      (batch) => [
        batch.map((a) => a.environment.organization),
        batch.map((a) => a.environment.project),
        batch.map((a) => a.environment.environment),
        batch.map((a) => a.agent),
        batch.map((a) => a.at.toISOString()),
        batch.map((a) => a.refusedByBound),
        batch.map((a) => a.reason),
      ],
      options,
    );
  }
}
