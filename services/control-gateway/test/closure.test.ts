// SPDX-License-Identifier: FSL-1.1-ALv2
//
// Structure (D-CG-EHA-08; NP-EHA-15; I5): S2 never links the organization
// level's code, and computes a human's authority only through P3.
import { readFileSync, readdirSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';

const ROOT = join(import.meta.dirname, '../../..');
const DIRS = ['packages', 'seams', 'services'];

function manifests(): Map<string, { dir: string; dependencies: string[] }> {
  const out = new Map<string, { dir: string; dependencies: string[] }>();
  for (const base of DIRS) {
    for (const name of readdirSync(join(ROOT, base))) {
      try {
        const j = JSON.parse(readFileSync(join(ROOT, base, name, 'package.json'), 'utf8')) as {
          name: string;
          dependencies?: Record<string, string>;
        };
        out.set(j.name, { dir: join(base, name), dependencies: Object.keys(j.dependencies ?? {}) });
      } catch {
        // not a package
      }
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
    const name = pending.pop()!;
    for (const d of all.get(name)?.dependencies ?? [])
      if (d.startsWith('@soorma/') && !seen.has(d)) {
        seen.add(d);
        pending.push(d);
      }
  }
  return seen;
}

describe('TC-EHA-078: @soorma/org-identity is not in S2’s production dependency closure', () => {
  it('S2 reaches the shared runtime, and never P10', () => {
    const s2 = closure('@soorma/control-gateway');
    expect(s2).toContain('@soorma/service-kit');
    expect(s2).not.toContain('@soorma/org-identity');
  });

  it('the walk finds P10 where it is linked: S1', () => {
    expect(closure('@soorma/org-gateway')).toContain('@soorma/org-identity');
  });
});

function sources(dir: string): string {
  const abs = join(ROOT, dir, 'src');
  return readdirSync(abs, { recursive: true, encoding: 'utf8' })
    .filter((f) => f.endsWith('.ts'))
    .map((f) => readFileSync(join(abs, f), 'utf8'))
    .join('\n');
}

describe('TC-EHA-044: S2 computes a human’s authority only through P3 (I5; BR-EV-04)', () => {
  it('S2 imports evaluateHuman and holdsAnyGrant from P3, and U5 adds two, and nothing else that computes authority', () => {
    const s2 = sources('services/control-gateway');
    const fromAuthority = [...s2.matchAll(/import \{([^}]*)\} from '@soorma\/authority'/g)]
      .flatMap((m) => m[1]!.split(','))
      .map((n) => n.trim())
      .filter(Boolean);
    expect(fromAuthority.sort()).toEqual(
      // U5's two (D-CG-AR-18; D-AR-07, 10)
      ['checkRegistrationRequest', 'evaluateHuman', 'holdsAnyGrant', 'readHumanAuthority'].sort(),
    );
    expect(s2).not.toMatch(/\.contains\(/);
    expect(s2).not.toMatch(/evaluateAgent/);
  });

  it('P4, P5, and P7 neither evaluate nor test a permission set', () => {
    for (const dir of ['packages/registry', 'packages/credentials', 'packages/attribution']) {
      const src = sources(dir);
      expect(src, dir).not.toMatch(/\.contains\(|evaluateHuman|evaluateAgent|holdsAnyGrant/);
      expect(src, dir).not.toMatch(/@soorma\/authority/);
    }
  });
});
