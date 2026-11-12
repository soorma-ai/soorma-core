// SPDX-License-Identifier: FSL-1.1-ALv2
//
// TC-AC-040 (D-AC-11; NP-AC-10; I5): S3's production dependency closure holds
// no organization-level code and no evaluator. The walk is S2's (TC-EHA-078):
// the workspace manifests' production `dependencies`, transitively, across
// packages/, seams/, and services/. The built image is checked separately, by
// `node tools/checks/run.ts image-packages` in CI (TC-AC-083).
import { existsSync, readFileSync, readdirSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';

const ROOT = join(import.meta.dirname, '../../..');
const DIRS = ['packages', 'seams', 'services'];

function manifests(): Map<string, string[]> {
  const out = new Map<string, string[]>();
  for (const base of DIRS) {
    for (const name of readdirSync(join(ROOT, base))) {
      const path = join(ROOT, base, name, 'package.json');
      if (!existsSync(path)) continue;
      const j = JSON.parse(readFileSync(path, 'utf8')) as {
        name: string;
        dependencies?: Record<string, string>;
      };
      out.set(j.name, Object.keys(j.dependencies ?? {}));
    }
  }
  return out;
}

/** Every workspace package reachable through production dependencies, transitively. */
function closure(start: string): Set<string> {
  const all = manifests();
  const seen = new Set<string>();
  const pending = [start];
  while (pending.length > 0) {
    for (const d of all.get(pending.pop()!) ?? [])
      if (d.startsWith('@soorma/') && !seen.has(d)) {
        seen.add(d);
        pending.push(d);
      }
  }
  return seen;
}

function sources(dir: string): string {
  const abs = join(ROOT, dir, 'src');
  return readdirSync(abs, { recursive: true, encoding: 'utf8' })
    .filter((f) => f.endsWith('.ts'))
    .map((f) => readFileSync(join(abs, f), 'utf8'))
    .join('\n');
}

describe('TC-AC-040: S3 never links the organization level or an evaluator', () => {
  it("S3's closure reaches the shared runtime, P5, and P8, and never P10 or P6's human half", () => {
    const s3 = closure('@soorma/data-gateway');
    for (const p of ['@soorma/service-kit', '@soorma/credentials', '@soorma/abuse-bound'])
      expect(s3, p).toContain(p);
    expect(s3).not.toContain('@soorma/org-identity');
    expect(s3).not.toContain('@soorma/identity-resolution');
    expect(s3).not.toContain('@soorma/authority');
  });

  it('the walk finds P10 where it is linked: S1', () => {
    expect(closure('@soorma/org-gateway')).toContain('@soorma/org-identity');
  });

  it("S3's sources import nothing from @soorma/authority (no evaluator at S3, I5)", () => {
    expect(sources('services/data-gateway')).not.toMatch(/@soorma\/authority/);
  });
});
