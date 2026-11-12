// SPDX-License-Identifier: FSL-1.1-ALv2
//
// TC-AC-070 (NFR-AC-24): U1's code checks (sql, compare, inject) cover U6's
// code, so no === on a secret-derived value can enter it unreported: the
// real-tree runs in code-checks.test.ts and `pnpm check:code` in the gate
// include every project listed here. And no U6 code path updates or deletes a
// registration or a registration secret (S3's role holds no such privilege,
// D-ID-AC-07; this is the source-level half).
import { readdirSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';
import { sourceProjects } from '../checks/code.ts';
import { repoRoot } from '../checks/workspace.ts';

const U6_PROJECTS = [
  'packages/agent-identity/tsconfig.json',
  'packages/abuse-bound/tsconfig.json',
  'packages/credentials/tsconfig.json',
  'packages/perimeter/tsconfig.json',
  'packages/attribution/tsconfig.json',
  'packages/registry/tsconfig.json',
  'seams/identity-resolution/tsconfig.json',
  'services/data-gateway/tsconfig.json',
];

describe("TC-AC-070: the code checks cover U6's code", () => {
  it('every project U6 adds to or extends is one the checks run over', () => {
    const projects = sourceProjects().map((p) => p.slice(repoRoot.length + 1));
    for (const project of U6_PROJECTS) expect(projects, project).toContain(project);
  });

  it('no statement in S3 or P6’s agent half updates or deletes a registration or a secret', () => {
    const sources = ['packages/agent-identity/src', 'services/data-gateway/src'].flatMap((dir) =>
      readdirSync(join(repoRoot, dir), { recursive: true, encoding: 'utf8' })
        .filter((f) => f.endsWith('.ts'))
        .map((f) => join(repoRoot, dir, f)),
    );
    expect(sources.length).toBeGreaterThan(0);
    const writes = /\b(UPDATE|DELETE\s+FROM|TRUNCATE)\s+(registrations|registration_secrets)\b/i;
    expect(sources.filter((f) => writes.test(readFileSync(f, 'utf8')))).toEqual([]);
  });
});
