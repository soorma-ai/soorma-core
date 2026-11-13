// SPDX-License-Identifier: FSL-1.1-ALv2
// TC-AR-065: U3's admission benchmark re-run with P4's agent-facts source
// (NFR-AR-16; NFR-AE-07), measured and REPORTED, never a gate. Build and
// Test's (U5 D-CG-AR-06). It runs over a test environment store:
//
//   pnpm db:test   # prints TEST_DATABASE_URL and TEST_DATABASE_CONTAINER
//   TEST_DATABASE_URL=… pnpm test:perf:agent-facts
//
// A timed loop under `vitest run`, not `vitest bench`: bench mode runs the
// global setups twice, and the second run re-passwords the cluster-wide test
// roles after the first run's passwords were provided to the workers.
//
// The input is TC-AE-040's: a maximum-size forwarding draft (a sealed
// forwarded envelope with a 31-entry chain, so the stamped chain has 32,
// padded just under 16384 bytes, and a 512-character tracestate). The 32
// agents are registrations in the store, read by P4's one statement
// (agentFactsFromStore) behind U3's one caching decorator, as S4 wires them.
// Three figures, each p50 and p99:
//
// - warm: the cache holds every agent, so no read is timed (TC-AE-040's
//   path, with P4 behind the cache)
// - cold: the cache's clock passes the TTL before every admit, so each one
//   runs P4's statement for the 32 agents (the query's share of the budget)
// - the statement alone, for the same 32 agents
//
// There is no assertion on time. `pnpm test` and CI skip it.
import { withTransaction } from '@soorma/env-store';
import { createCachingAgentFacts, createEnvelopeAdmission } from '@soorma/authority';
import { createPolicyDecision, inMemoryGrantSource } from '@soorma/policy-decision';
import { describe, expect, it } from 'vitest';
import { agentFactsFromStore, insertRegistration } from '../../src/index.ts';
import { testEnvDatabase } from '../../../env-store/test/harness/database.ts';
import {
  BOUND_MS,
  CollectingLog,
  draft,
  E,
  envelope,
  padTo,
  request,
  ringE,
  sealed,
  TestClock,
  TRACEPARENT,
} from '../../../authority/test/support.ts';

const enabled = process.env.SOORMA_PERF === '1' && process.env.TEST_DATABASE_URL !== undefined;
const WARMUP = 500;
const SAMPLES = 5000;

const chain = Array.from({ length: 31 }, (_, i) => `agent-${i}`);
const agents = [...chain, 'b'];

const tracestate = Array.from({ length: 32 }, (_, i) => `k${i}=${'v'.repeat(10)}`)
  .join(',')
  .padEnd(512, 'v')
  .slice(0, 512);
const base = envelope(chain);
const stampedShape = {
  ...base,
  actorChain: [...(base.actorChain as unknown[]), { agent: 'b', instance: 'b-i' }],
  traceContext: { traceparent: TRACEPARENT, tracestate },
};
const forwarded = { ...base, 'x-pad': padTo(stampedShape, 16384 - 16)['x-pad'] };
const req = request(
  'b',
  draft({ traceContext: { traceparent: TRACEPARENT, tracestate }, inbound: sealed(forwarded) }),
);

/** The q-quantile of the samples (nearest rank). */
const quantile = (sorted: number[], q: number): number =>
  sorted[Math.min(sorted.length - 1, Math.ceil(q * sorted.length) - 1)]!;

async function measure(f: () => Promise<unknown>): Promise<{ p50: number; p99: number }> {
  for (let i = 0; i < WARMUP; i++) await f();
  const samples: number[] = [];
  for (let i = 0; i < SAMPLES; i++) {
    const t = performance.now();
    await f();
    samples.push(performance.now() - t);
  }
  samples.sort((a, b) => a - b);
  return { p50: quantile(samples, 0.5), p99: quantile(samples, 0.99) };
}

describe.skipIf(!enabled)(
  'TC-AR-065: admit with P4 agent-facts source (reported, not a gate)',
  () => {
    it('measures admit warm, admit cold (the P4 read included), and the statement alone', async () => {
      const db = await testEnvDatabase();
      try {
        for (const agent of agents)
          await withTransaction(db.store, (tx) =>
            insertRegistration(tx, {
              environment: E,
              agent,
              sponsor: 'h@example.com',
              ceilingSnapshot: ['event:publish'],
              standingPermissions: ['event:publish'],
              reBroadeningDeclaration: [],
              autonomyDeclared: true,
              registeredAt: new Date(),
            }),
          );
        const source = agentFactsFromStore(db.store);
        const clock = new TestClock();
        const admission = createEnvelopeAdmission({
          acceptedVersions: ['0.1.0'],
          scope: E,
          keyRing: ringE,
          facts: createCachingAgentFacts(source, { ttl: BOUND_MS, clock }),
          policyFactory: createPolicyDecision,
          humanGrants: inMemoryGrantSource([]),
          securityLog: new CollectingLog(),
        });

        // The input is admitted with a 32-entry chain, and P4 finds every agent.
        const first = await admission.admit(req);
        expect('admitted' in first).toBe(true);
        if (!('admitted' in first)) return;
        expect(first.admitted.envelope.actorChain as unknown[]).toHaveLength(32);
        expect((await source.load(E, agents)).size).toBe(32);

        const warm = await measure(() => admission.admit(req));
        const cold = await measure(() => {
          clock.t += BOUND_MS + 1;
          return admission.admit(req);
        });
        const read = await measure(() => source.load(E, agents));
        const ms = (n: number): number => Number(n.toFixed(3));
        console.log(
          JSON.stringify({
            tc: 'TC-AR-065',
            samples: SAMPLES,
            admitWarmMs: { p50: ms(warm.p50), p99: ms(warm.p99) },
            admitColdMs: { p50: ms(cold.p50), p99: ms(cold.p99) },
            agentFactsStatementMs: { p50: ms(read.p50), p99: ms(read.p99) },
            targetMs: { admitP99ExcludingTermReads: 2 },
          }),
        );
      } finally {
        await db.drop();
      }
    }, 600_000);
  },
);
