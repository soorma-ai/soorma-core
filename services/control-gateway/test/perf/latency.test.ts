// SPDX-License-Identifier: FSL-1.1-ALv2
//
// TC-EHA-070: S2's latency, measured and REPORTED, never a gate (NFR-EHA-15;
// D-CG-EHA-10). Targets: p95 at most 300 ms for issuance and renewal, 200 ms
// for ending and grantToHuman. It runs through S2's real edge over a test
// environment store, with a stub S1, and prints the p95 of each operation for
// the Build and Test summary. It asserts no time.
//
//   SOORMA_PERF=1 TEST_DATABASE_URL=… pnpm test:perf:s2
//
// pnpm test and CI skip it.
import { describe, expect, it } from 'vitest';
import {
  testEnvDatabase,
  type TestEnvDatabase,
} from '../../../../packages/env-store/test/harness/database.ts';
import { adminCredential, credentialFor, gateway, grant, post, unique } from '../support.ts';

const enabled = process.env.SOORMA_PERF === '1';
const RUNS = 500;

const p95 = (samples: number[]): number => {
  const sorted = [...samples].sort((a, b) => a - b);
  return sorted[Math.ceil(sorted.length * 0.95) - 1]!;
};

describe.skipIf(!enabled)('TC-EHA-070: S2 latency, reported (not a gate)', () => {
  it('measures p95 per operation after warm-up', async () => {
    const db: TestEnvDatabase = await testEnvDatabase();
    const g = await gateway(db);
    try {
      const time = async (f: () => Promise<unknown>): Promise<number> => {
        const t = performance.now();
        await f();
        return performance.now() - t;
      };
      const samples: Record<string, number[]> = { issue: [], renew: [], end: [], grant: [] };
      const admin = await adminCredential(g);
      for (let i = 0; i < 20; i++) await credentialFor(g, g.admin); // warm-up
      for (let i = 0; i < RUNS; i++) {
        const s = await g.stub.signIn(g.admin);
        let credential = '';
        samples.issue!.push(
          await time(async () => {
            const r = await post(g.edge, '/environment-credentials', { credential: s.token });
            credential = r.body.credential as string;
          }),
        );
        samples.renew!.push(
          await time(() =>
            post(g.edge, '/environment-credentials/current/renewal', { credential }),
          ),
        );
        const target = unique();
        g.stub.principals.add(target);
        samples.grant!.push(
          await time(() => grant(g, admin.credential, target, ['agent:register'])),
        );
        samples.end!.push(
          await time(() => post(g.edge, '/environment-credentials/current/end', { credential })),
        );
      }
      const report = Object.fromEntries(
        Object.entries(samples).map(([k, v]) => [k, Number(p95(v).toFixed(1))]),
      );
      console.log(
        JSON.stringify({
          tc: 'TC-EHA-070',
          p95Ms: report,
          targetsMs: { issue: 300, renew: 300, end: 200, grant: 200 },
        }),
      );
      expect(Object.keys(report)).toHaveLength(4);
    } finally {
      await g.close();
      await db.drop();
    }
  }, 600_000);
});
