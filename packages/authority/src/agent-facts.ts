// SPDX-License-Identifier: FSL-1.1-ALv2
//
// Agent facts, the request snapshot, and the cache (U3 NFR Design NP-04, the
// user's design; NFR-AE-08 to 16, 22).
//
// - One port returns, for a list of agents in ONE call, each one's
//   Registration View and standing set, or not found. A failure rejects the
//   whole call. U5 fills it from P4 with one query
// - It is read once, at the start of step 9, for the presenter and every
//   distinct upstream agent, all or nothing. Steps 5 to 8 read nothing
// - The read becomes an immutable request snapshot. Origin reads the
//   presenter's view from it; P11's agent GrantSource is an adapter over it.
//   So no second round trip is possible. A principal missing from the
//   snapshot is a defect, never a read
// - Humans never pass through here: a human's grants go straight to U4's
//   source, uncached (NFR-AE-14)
//
// The caching decorator, one per environment per process:
// - Keys carry organization, project, environment, and agent (I1)
// - Hits within the TTL are served; misses go to the port in one batched call
// - An agent already being read by a concurrent request is awaited, not
//   re-read; if that read fails, every waiter fails too
// - Only found agents from a successful call are stored. Failures and not
//   found are never cached (NFR-AE-12)
// - The TTL is the propagation bound, measured from when the batched read was
//   ISSUED, not when it completed: a slow read never extends an entry's life.
//   No entry is served past it, outage or not (NFR-AE-10, 15)
// - At most `max` (4096) entries; least recently used evicted, by deleting
//   and re-inserting on each hit in a Map (NFR-AE-11)
//
// Staleness in M1: none possible (NFR-AE-16). No M1 operation changes a
// standing set, a re-broadening declaration, or autonomy declared, or
// suspends or retires an agent. The unit that first adds one must account for
// this cache's window, up to the propagation bound.
import type {
  EnvironmentRef,
  PermissionId,
  PermissionSet,
  PrincipalRef,
} from '@soorma/policy-decision-seam';

/** What P3 reads from a registration besides its standing set (PF §7a). */
export interface RegistrationView {
  /** Default no (PF §7a). Decides BR-OR-01 to 04. */
  readonly autonomyDeclared: boolean;
  readonly reBroadeningDeclaration: PermissionSet;
}

export interface AgentFacts {
  readonly registrationView: RegistrationView;
  readonly standingSet: PermissionSet;
}

/** The agent-facts port: one call for a list of agents. An agent absent is not found. */
export interface AgentFactsSource {
  load(
    environment: EnvironmentRef,
    agents: readonly string[],
  ): Promise<ReadonlyMap<string, AgentFacts>>;
}

/** Milliseconds, injected so tests control time. */
export interface Clock {
  now(): number;
}

/** P11's GrantSource, by shape: P3 does not import P11 (NP-05). */
export interface GrantSource {
  grantsOf(principal: PrincipalRef, environment: EnvironmentRef): Promise<Iterable<PermissionId>>;
}

/** A cache key: organization, project, environment, and agent (I1; P-ND-06). */
export function cacheKey(environment: EnvironmentRef, agent: string): string {
  return JSON.stringify([
    environment.organization,
    environment.project,
    environment.environment,
    agent,
  ]);
}

interface Entry {
  readonly facts: AgentFacts;
  readonly issuedAt: number;
}

export interface CacheOptions {
  /** The propagation bound, in milliseconds: the one number M1-NFR-01 publishes. */
  readonly ttl: number;
  /** At most this many entries; 4096 by default. */
  readonly max?: number;
  readonly clock: Clock;
}

/** The one caching decorator on the agent-facts port. */
export function createCachingAgentFacts(
  source: AgentFactsSource,
  options: CacheOptions,
): AgentFactsSource & { readonly size: () => number } {
  const { ttl, clock } = options;
  const max = options.max ?? 4096;
  if (!(ttl > 0) || !(max > 0)) throw new RangeError('the TTL and the size bound must be positive');
  const entries = new Map<string, Entry>();
  const inFlight = new Map<string, Promise<ReadonlyMap<string, AgentFacts>>>();

  function store(key: string, entry: Entry): void {
    entries.delete(key);
    entries.set(key, entry);
    while (entries.size > max) entries.delete(entries.keys().next().value!);
  }

  return Object.freeze({
    size: (): number => entries.size,
    async load(
      environment: EnvironmentRef,
      agents: readonly string[],
    ): Promise<ReadonlyMap<string, AgentFacts>> {
      const now = clock.now();
      const result = new Map<string, AgentFacts>();
      const misses: string[] = [];
      const waits: [string, Promise<ReadonlyMap<string, AgentFacts>>][] = [];

      for (const agent of new Set(agents)) {
        const key = cacheKey(environment, agent);
        const entry = entries.get(key);
        if (entry && now - entry.issuedAt < ttl) {
          entries.delete(key);
          entries.set(key, entry);
          result.set(agent, entry.facts);
          continue;
        }
        if (entry) entries.delete(key);
        const pending = inFlight.get(key);
        if (pending) waits.push([agent, pending]);
        else misses.push(agent);
      }

      if (misses.length > 0) {
        const issuedAt = now;
        const read = source.load(environment, misses);
        const keys = misses.map((agent) => cacheKey(environment, agent));
        for (const key of keys) inFlight.set(key, read);
        const settle = (): void => {
          for (const key of keys) if (inFlight.get(key) === read) inFlight.delete(key);
        };
        read.then((found) => {
          settle();
          for (const [i, agent] of misses.entries()) {
            const facts = found.get(agent);
            if (facts) store(keys[i]!, { facts, issuedAt });
          }
        }, settle);
        waits.push(...misses.map((agent) => [agent, read] as [string, typeof read]));
      }

      // All or nothing: any failed read fails the whole call.
      const settled = await Promise.all(waits.map(([, p]) => p));
      for (const [i, [agent]] of waits.entries()) {
        const facts = settled[i]!.get(agent);
        if (facts) result.set(agent, facts);
      }
      return result;
    },
  });
}

/** One request's facts: immutable, and the only source of agent sets in it. */
export interface RequestSnapshot {
  /** The agent's facts; undefined when it was read and not found. */
  facts(agent: string): AgentFacts | undefined;
  /** Whether the agent was part of this request's read. */
  wasRead(agent: string): boolean;
}

export function requestSnapshot(
  agents: readonly string[],
  found: ReadonlyMap<string, AgentFacts>,
): RequestSnapshot {
  const read = new Set(agents);
  const facts = new Map([...found].filter(([agent]) => read.has(agent)));
  return Object.freeze({
    facts: (agent: string): AgentFacts | undefined => facts.get(agent),
    wasRead: (agent: string): boolean => read.has(agent),
  });
}

/**
 * P11's GrantSource for one request: an agent's granted set is its standing
 * set, from the snapshot (empty when not found); a human's goes straight to
 * U4's source. An agent this request did not read is a defect: it throws,
 * and the surface's handler answers internal_error.
 */
export function requestGrantSource(snapshot: RequestSnapshot, humans: GrantSource): GrantSource {
  return Object.freeze({
    grantsOf(
      principal: PrincipalRef,
      environment: EnvironmentRef,
    ): Promise<Iterable<PermissionId>> {
      if (principal.kind === 'human') return humans.grantsOf(principal, environment);
      if (!snapshot.wasRead(principal.agent))
        return Promise.reject(new Error('defect: an agent outside the request snapshot'));
      return Promise.resolve(snapshot.facts(principal.agent)?.standingSet ?? []);
    },
  });
}
