// SPDX-License-Identifier: FSL-1.1-ALv2
// TC-OI-062: refusal timing for known and unknown principals, measured and
// reported (BR-RF-03). A reported measurement for the Build and Test summary,
// never a gate: it runs only with SOORMA_PERF=1 (`pnpm test:perf`).
//
// In process, over the test database, with real Argon2id. The test clock
// steps 16 minutes between attempts, so the abuse bound (10 per 15 minutes)
// never refuses and every sample is a full verification.
import { afterAll, beforeAll, describe, expect, it } from 'vitest';
import {
  testDatabase,
  type TestDatabase,
} from '../../../../packages/org-identity/test/harness/database.ts';
import { active, gateway, post, type Gateway } from '../support.ts';

const N = Number(process.env.SOORMA_PERF_SAMPLES ?? 200);
const run = process.env.SOORMA_PERF === '1';

function quantile(sorted: number[], q: number): number {
  return sorted[Math.min(sorted.length - 1, Math.floor(q * sorted.length))]!;
}

/** Mann-Whitney U, normal approximation: z and the two-sided p-value. */
function mannWhitney(a: number[], b: number[]): { z: number; p: number } {
  const all = [...a.map((v) => ({ v, g: 0 })), ...b.map((v) => ({ v, g: 1 }))].sort(
    (x, y) => x.v - y.v,
  );
  let rankA = 0;
  all.forEach((x, i) => {
    if (x.g === 0) rankA += i + 1;
  });
  const u = rankA - (a.length * (a.length + 1)) / 2;
  const mean = (a.length * b.length) / 2;
  const sd = Math.sqrt((a.length * b.length * (a.length + b.length + 1)) / 12);
  const z = (u - mean) / sd;
  const erfc = (x: number): number => {
    const t = 1 / (1 + 0.5 * Math.abs(x));
    const y =
      t *
      Math.exp(
        -x * x -
          1.26551223 +
          t *
            (1.00002368 +
              t *
                (0.37409196 +
                  t *
                    (0.09678418 +
                      t *
                        (-0.18628806 +
                          t *
                            (0.27886807 +
                              t *
                                (-1.13520398 +
                                  t * (1.48851587 + t * (-0.82215223 + t * 0.17087277)))))))),
      );
    return x >= 0 ? y : 2 - y;
  };
  return { z, p: erfc(Math.abs(z) / Math.SQRT2) };
}

describe.runIf(run)('TC-OI-062: refusal timing, known against unknown (reported)', () => {
  let db: TestDatabase;
  let g: Gateway;
  beforeAll(async () => {
    db = await testDatabase();
    g = await gateway(db, { realHashing: true });
  });
  afterAll(async () => {
    await g?.close();
    await db?.drop();
  });

  it(`measures ${N} wrong-K attempts each, interleaved`, async () => {
    const { principal } = await active(g);
    const unknown = { organization: 'o1', principal: 'nobody@example.com' };
    const known: number[] = [];
    const absent: number[] = [];
    for (let i = 0; i < N; i++) {
      for (const [target, samples] of [
        [principal, known],
        [unknown, absent],
      ] as const) {
        g.clock.advance(16 * 60);
        const started = performance.now();
        const r = await post(g.edge, '/sign-ins', { principal: target, secret: 'wrong secret' });
        samples.push(performance.now() - started);
        expect(r.status).toBe(403);
      }
    }
    known.sort((a, b) => a - b);
    absent.sort((a, b) => a - b);
    const report = {
      case: 'TC-OI-062',
      samples: N,
      knownMedianMs: quantile(known, 0.5),
      knownP95Ms: quantile(known, 0.95),
      unknownMedianMs: quantile(absent, 0.5),
      unknownP95Ms: quantile(absent, 0.95),
      medianDifferenceMs: quantile(known, 0.5) - quantile(absent, 0.5),
      mannWhitney: mannWhitney(known, absent),
    };
    process.stdout.write(`${JSON.stringify(report)}\n`);
  }, 1_800_000);
});
