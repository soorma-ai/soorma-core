// SPDX-License-Identifier: FSL-1.1-ALv2
//
// Revocation reads (U6 D-AC-01, 16, 18; BR-RV, BR-RC; NP-AC-04, 05).
//
// - The **direct source**: one statement over both granularities (the
//   credential's cid, the logical agent), constrained on E's three columns,
//   run in the caller's transaction. S3 uses it: both its operations write to
//   the store anyway, so a cache would buy S3 no availability (D-AC-01). It
//   writes no attribution record (GAP-INT-009, D-AC-17)
// - The **fail-closed cache** over a source: a `not_revoked` answer is served
//   while younger than the bound, counted from its read's issue; a `revoked`
//   answer is terminal and kept; a failed read is never cached, and with no
//   answer younger than the bound the request is denied (`unavailable`).
//   Concurrent misses for one key share one read; at most `max` entries,
//   oldest first evicted, so eviction only causes a re-read. Modelled on U3's
//   agent-facts cache (NP-04). **Wired at S4 by U7**, with the bound
//   `PROPAGATION_BOUND_MS`; S3 does not use it
import type { EnvironmentRef } from '@soorma/policy-decision-seam';
import { UnavailableError, type Clock, type Queryable } from '@soorma/service-kit';
import { SQL } from './sql.ts';

/** What is asked about: an agent in E, and its credential's cid once one exists. */
export interface RevocationTarget {
  readonly environment: EnvironmentRef;
  /** The lineage; absent at bootstrap, when only the agent can be revoked. */
  readonly cid?: string;
  readonly agent: string;
}

export type RevocationAnswer = 'revoked' | 'not_revoked';

/** A read of revocation state. A failure rejects; the caller denies (fail closed). */
export interface RevocationSource {
  isRevoked(target: RevocationTarget): Promise<RevocationAnswer>;
}

/** The direct source over a store or a transaction (D-AC-01). */
export function directRevocationSource(store: Queryable): RevocationSource {
  return {
    async isRevoked({ environment, cid, agent }): Promise<RevocationAnswer> {
      const [row] = await store.query<{ revoked: boolean }>(SQL.revoked, [
        environment.organization,
        environment.project,
        environment.environment,
        cid ?? null,
        agent,
      ]);
      return row?.revoked ? 'revoked' : 'not_revoked';
    },
  };
}

export interface RevocationCacheOptions {
  /** The propagation bound in milliseconds: PROPAGATION_BOUND_MS in production. */
  readonly ttl: number;
  /** At most this many entries; 16,384 by default (NP-AC-05). */
  readonly max?: number;
  readonly clock: Clock;
}

interface Entry {
  readonly answer: RevocationAnswer;
  /** When the read that produced it was issued (ms). */
  readonly issuedAt: number;
}

/** The key: the environment's three parts, the cid, and the agent, unambiguously (I1). */
function cacheKey({ environment, cid, agent }: RevocationTarget): string {
  return JSON.stringify([
    environment.organization,
    environment.project,
    environment.environment,
    cid ?? null,
    agent,
  ]);
}

/** The fail-closed cache over a source (D-AC-18; BR-RC-01 to 04). */
export function createRevocationCache(
  source: RevocationSource,
  options: RevocationCacheOptions,
): RevocationSource & { readonly size: () => number } {
  const { ttl, clock } = options;
  const max = options.max ?? 16_384;
  if (!(ttl > 0) || !(max > 0))
    throw new RangeError('the bound and the size bound must be positive');
  const entries = new Map<string, Entry>();
  const inFlight = new Map<string, Promise<Entry>>();

  function store(key: string, entry: Entry): void {
    entries.delete(key);
    entries.set(key, entry);
    while (entries.size > max) entries.delete(entries.keys().next().value!);
  }

  function read(key: string, target: RevocationTarget): Promise<Entry> {
    const pending = inFlight.get(key);
    if (pending) return pending;
    const issuedAt = clock.now().getTime();
    const promise = source
      .isRevoked(target)
      .then((answer) => {
        const entry = { answer, issuedAt };
        store(key, entry);
        return entry;
      })
      .finally(() => inFlight.delete(key));
    inFlight.set(key, promise);
    return promise;
  }

  return Object.freeze({
    size: (): number => entries.size,
    async isRevoked(target: RevocationTarget): Promise<RevocationAnswer> {
      const key = cacheKey(target);
      const entry = entries.get(key);
      const now = clock.now().getTime();
      if (entry && (entry.answer === 'revoked' || now - entry.issuedAt < ttl)) return entry.answer;
      try {
        return (await read(key, target)).answer;
      } catch {
        // Never cached. No answer younger than the bound: unknown, so deny.
        throw new UnavailableError('revocation state unreadable within the bound', 5);
      }
    },
  });
}
