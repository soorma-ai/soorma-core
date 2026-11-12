// SPDX-License-Identifier: FSL-1.1-ALv2
//
// S3's components, wired once (as S2's, D-CG-AC-08). assembleRuntime takes the
// already-built store, agent key ring, and clock, so tests wire the same graph
// over a test store; start (main.ts) builds them from configuration. S3 holds
// no organization-level client, no evaluator, and no human key ring (D-AC-03,
// 11; I5).
import { AgentBound, FailedBootstrapAttemptWriter } from '@soorma/abuse-bound';
import type { EnvironmentKeyRing } from '@soorma/credentials';
import type { EnvironmentRef } from '@soorma/policy-decision-seam';
import type { Clock, SecretBytes, Semaphore, Store } from '@soorma/service-kit';
import type { ContractValidator } from './contract-validator.ts';
import type { SecurityLog } from './security-log.ts';

export interface Runtime {
  /** E's configured identity: S3 serves this environment only. */
  environment: EnvironmentRef;
  /** E's store, as soorma_env_data (D-ID-AC-07). */
  store: Store;
  /** E's agent key ring, separate from its human ring (D-AC-03). */
  ring: EnvironmentKeyRing;
  /** The bootstrap bound (P8's agent half, BR-AB-AC). */
  bound: AgentBound;
  /** Failed Bootstrap Attempts, written off the response path (BR-FA-02). */
  attempts: FailedBootstrapAttemptWriter;
  clock: Clock;
  log: SecurityLog;
  validator: ContractValidator;
  /** The request permits (as S2's). */
  requests: Semaphore;
}

export function assembleRuntime(parts: {
  environment: EnvironmentRef;
  store: Store;
  ring: EnvironmentKeyRing;
  counterSecret: SecretBytes;
  clock: Clock;
  log: SecurityLog;
  validator: ContractValidator;
  requests: Semaphore;
}): Runtime {
  return {
    environment: Object.freeze({ ...parts.environment }),
    store: parts.store,
    ring: parts.ring,
    bound: new AgentBound(parts.store, parts.counterSecret, parts.clock),
    attempts: new FailedBootstrapAttemptWriter(parts.store),
    clock: parts.clock,
    log: parts.log,
    validator: parts.validator,
    requests: parts.requests,
  };
}
