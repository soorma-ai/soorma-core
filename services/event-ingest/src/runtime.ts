// SPDX-License-Identifier: FSL-1.1-ALv2
//
// S4's components, wired once (NP-ET-02). assembleRuntime takes the already
// built store, E's verify-only ring, E's seal ring, the clock, and the
// scheduler, so tests wire the same graph over a test store; start (main.ts)
// builds them from configuration.
//
// **One bound** (D-ET-15; BR-BND-01): PROPAGATION_BOUND_MS, imported from
// @soorma/credentials, is the `ttl` of both caches: P5's revocation cache
// (steps 4 and every stream check) and U3's agent-facts cache. The two cache
// factories are parameters, with those defaults, so the composition test sees
// exactly what each receives. No configuration key names a bound.
//
// S4 holds no organization-level client, no signing key, no human key ring,
// and nothing of P2 or P3 but the entry point and its construction helpers
// (BR-EP-03; NP-ET-03).
import { randomBytes } from 'node:crypto';
import {
  createCachingAgentFacts,
  createEnvelopeAdmission,
  type AgentFactsSource,
  type CacheOptions,
  type EnvelopeAdmission,
  type GrantSource,
  type SealKeyRing,
} from '@soorma/authority';
import {
  createRevocationCache,
  directRevocationSource,
  PROPAGATION_BOUND_MS,
  type RevocationCacheOptions,
  type RevocationSource,
  type VerifyKeyRing,
} from '@soorma/credentials';
import { SUPPORTED_VERSIONS } from '@soorma/perimeter';
import { createPolicyDecision } from '@soorma/policy-decision';
import type { EnvironmentRef } from '@soorma/policy-decision-seam';
import { agentFactsFromStore } from '@soorma/registry';
import type { Clock, Semaphore, Store } from '@soorma/service-kit';
import { createInProcessChannel, type Channel, type OrderKey } from './channel/channel.ts';
import type { Scheduler, Timer } from './scheduler.ts';
import type { SecurityLog } from './security-log.ts';
import { SWEEP_INTERVAL_MS } from './settings.ts';
import { StreamRegistry } from './stream/registry.ts';
import type { Ending, Stream } from './stream/stream.ts';

/**
 * Human grants at S4 (D-ET-14; BR-EP-04): the empty set for any principal. No
 * human enters an agent's chain in M1, so it never decides; if one did, deny
 * by default holds. S4's role has no privilege on `grants`.
 */
export const humanGrants: GrantSource = Object.freeze({
  grantsOf: (): Promise<Iterable<string>> => Promise.resolve([]),
});

/** The two cache factories, injectable for the composition test (NP-ET-02). */
export interface CacheFactories {
  readonly createRevocationCache: (
    source: RevocationSource,
    options: RevocationCacheOptions,
  ) => RevocationSource;
  readonly createCachingAgentFacts: (
    source: AgentFactsSource,
    options: CacheOptions,
  ) => AgentFactsSource;
}

export const DEFAULT_FACTORIES: CacheFactories = Object.freeze({
  createRevocationCache,
  createCachingAgentFacts,
});

export interface Runtime {
  /** E's configured identity: S4 serves this environment only (O4). */
  readonly environment: EnvironmentRef;
  /** E's store, as soorma_env_ingest (D-ID-ET-04). */
  readonly store: Store;
  /** E's agent verify halves: S4 holds no signing key (D-ET-30). */
  readonly ring: VerifyKeyRing;
  /** P5's fail-closed cache, ttl PROPAGATION_BOUND_MS. */
  readonly revocation: RevocationSource;
  /** U3's entry point, built once (BR-EP-01). */
  readonly admission: EnvelopeAdmission;
  /** E's fan-out channel (NP-ET-08). */
  readonly channel: Channel;
  readonly streams: StreamRegistry;
  readonly clock: Clock;
  readonly scheduler: Scheduler;
  readonly log: SecurityLog;
  /** The request permits (NFR-ET-12). */
  readonly requests: Semaphore;
  /**
   * A new stream's order key: its opening time in milliseconds, then 128
   * CSPRNG bits. On one instance the opening time is max(the clock, the last
   * one + 1) (D-CG-ET-30), so a later subscribe here always orders after an
   * earlier one and supersedes it (BR-FO-04); across instances, the same
   * millisecond is decided by the id (BR-FO-05).
   */
  orderKey(): OrderKey;
  /** A stream left `open`: out of the registry, and one log event. */
  ended(stream: Stream, ending: Ending): void;
  /** Starts the sweep (every R). */
  start(): void;
  /** Stops the sweep and leaves the channel. Streams are ended by the caller first. */
  stop(): void;
}

export function assembleRuntime(parts: {
  environment: EnvironmentRef;
  store: Store;
  ring: VerifyKeyRing;
  sealKeys: SealKeyRing;
  clock: Clock;
  scheduler: Scheduler;
  log: SecurityLog;
  requests: Semaphore;
  channel?: Channel;
  factories?: CacheFactories;
}): Runtime {
  const environment: EnvironmentRef = Object.freeze({
    organization: parts.environment.organization,
    project: parts.environment.project,
    environment: parts.environment.environment,
  });
  const factories = parts.factories ?? DEFAULT_FACTORIES;
  const { clock, log } = parts;
  const revocation = factories.createRevocationCache(directRevocationSource(parts.store), {
    ttl: PROPAGATION_BOUND_MS,
    clock,
  });
  const facts = factories.createCachingAgentFacts(agentFactsFromStore(parts.store), {
    ttl: PROPAGATION_BOUND_MS,
    clock: { now: () => clock.now().getTime() },
  });
  const admission = createEnvelopeAdmission({
    acceptedVersions: SUPPORTED_VERSIONS,
    scope: environment,
    keyRing: parts.sealKeys,
    facts,
    policyFactory: createPolicyDecision,
    humanGrants,
    securityLog: log,
  });
  const channel = parts.channel ?? createInProcessChannel();
  const streams = new StreamRegistry(channel);
  let sweep: Timer | undefined;
  // D-CG-ET-30: a new stream on this instance never orders before an earlier one.
  let lastOpenedAt = Number.NEGATIVE_INFINITY;

  return {
    environment,
    store: parts.store,
    ring: parts.ring,
    revocation,
    admission,
    channel,
    streams,
    clock,
    scheduler: parts.scheduler,
    log,
    requests: parts.requests,
    orderKey(): OrderKey {
      lastOpenedAt = Math.max(clock.now().getTime(), lastOpenedAt + 1);
      return { openedAt: lastOpenedAt, id: randomBytes(16).toString('hex') };
    },
    ended(stream: Stream, ending: Ending): void {
      streams.remove(stream);
      const { requestId, agent, instance } = stream.who;
      if (ending.code === 'credential_refused')
        log.agentEvent('stream.revoked', requestId, { agent, instance, reason: ending.reason });
      else if (ending.code === 'overflow')
        log.agentEvent('stream.overflow', requestId, { agent, instance });
      else
        log.agentEvent('stream.ended', requestId, {
          agent,
          instance,
          code: ending.code ?? 'client_closed',
          ...(ending.reason === undefined ? {} : { reason: ending.reason }),
        });
    },
    start(): void {
      sweep ??= parts.scheduler.every(SWEEP_INTERVAL_MS, () => streams.sweep());
    },
    stop(): void {
      sweep?.cancel();
      sweep = undefined;
      streams.close();
    },
  };
}
