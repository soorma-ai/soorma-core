// SPDX-License-Identifier: FSL-1.1-ALv2
// TC-AC-066: the revocation read's cost, measured and REPORTED, never a gate
// (NFR-AC-16; Q5 A at NFR Requirements; D-CG-AC-07). Run at Build and Test with
// `pnpm bench:revocation`; never in `pnpm test` or CI. The target: a cache hit
// at most 0.1 ms p99 in process. A miss is one statement (by review: the
// direct source runs SQL.revoked once). There is no assertion on time.
import { systemClock } from '@soorma/service-kit';
import { test } from 'vitest';
import {
  createRevocationCache,
  PROPAGATION_BOUND_MS,
  type RevocationSource,
} from '../src/index.ts';

const E = { organization: 'o1', project: 'p1', environment: 'e' };
// A source that is never reached once the cache is warm.
const source: RevocationSource = { isRevoked: () => Promise.resolve('not_revoked') };
const cache = createRevocationCache(source, { ttl: PROPAGATION_BOUND_MS, clock: systemClock });
// A realistic population: 4,096 live lineages, each asked about once to warm.
const targets = Array.from({ length: 4096 }, (_, i) => ({
  environment: E,
  cid: `c${i}`,
  agent: `a${i % 64}`,
}));
for (const t of targets) await cache.isRevoked(t);

test('TC-AC-066: a revocation cache hit (reported, not a gate)', async ({ bench, annotate }) => {
  let i = 0;
  const result = await bench('cache hit', async () => {
    await cache.isRevoked(targets[i++ % targets.length]!);
  }).run({ time: 2000, warmupTime: 500 });
  const ms = (n: number): string => n.toFixed(4);
  const report =
    `revocation cache hit: p50 ${ms(result.latency.p50)} ms, p99 ${ms(result.latency.p99)} ms, ` +
    `samples ${result.latency.samplesCount} (target: p99 <= 0.1 ms; reported, not a gate)`;
  console.log(report);
  await annotate(report);
});
