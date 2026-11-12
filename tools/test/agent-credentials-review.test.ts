// SPDX-License-Identifier: FSL-1.1-ALv2
//
// U6's reviews, each with a check (Step 36): TC-AC-041 (nothing reads code
// identity or deployment topology), TC-AC-046 (no revocation initiation or
// rotation surface, and no seeding path in any image), TC-AC-047 (no tenant
// constant in U6's code), TC-AC-074 (nothing is pruned; the store keeps U4's
// guarantees), TC-AC-075 (no new external dependency: S3's are S2's, at S2's
// versions; `pnpm audit` runs in the gate).
import { readdirSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';
import { repoRoot } from '../checks/workspace.ts';

const U6_SOURCES = [
  'services/data-gateway/src',
  'packages/agent-identity/src',
  'packages/abuse-bound/src',
  'packages/credentials/src',
  'packages/perimeter/src',
  'seams/identity-resolution/src',
];

const files = (dir: string): { path: string; text: string }[] =>
  readdirSync(join(repoRoot, dir), { recursive: true, encoding: 'utf8' })
    .filter((f) => f.endsWith('.ts'))
    .map((f) => ({ path: `${dir}/${f}`, text: readFileSync(join(repoRoot, dir, f), 'utf8') }));
const sources = U6_SOURCES.flatMap(files);
/** Source with comments removed, so a rule's prose never matches a code check. */
const code = (text: string): string =>
  text.replace(/\/\*[\s\S]*?\*\//g, '').replace(/(^|[^:'"`])\/\/.*$/gm, '$1');
const matching = (pattern: RegExp): string[] =>
  sources.filter((f) => pattern.test(code(f.text))).map((f) => f.path);

describe('TC-AC-041: nothing reads code identity or deployment topology', () => {
  it('no host, container, or address read in U6’s code; identity from the credential only', () => {
    expect(matching(/\bos\.hostname\b|\bhostname\(\)|HOSTNAME|POD_NAME|KUBERNETES_/)).toEqual([]);
    expect(
      matching(/\.ip\b|\.ips\b|remoteAddress|x-forwarded-for|x-real-ip|request\.socket/i),
    ).toEqual([]);
  });
});

describe('TC-AC-046: no revocation initiation, no rotation surface, no seeding path ships', () => {
  it('no source writes revocation state, and S3 has no route but its two operations', () => {
    expect(matching(/INSERT\s+INTO\s+(credential_revocations|agent_revocations)/i)).toEqual([]);
    const routes = [
      ...readFileSync(
        join(repoRoot, 'services/data-gateway/src/edge/edge.module.ts'),
        'utf8',
      ).matchAll(/@(Get|Post|Put|Patch|Delete)\('([^']*)'\)/g),
    ].map((m) => `${m[1]} ${m[2]}`);
    expect(routes.sort()).toEqual(
      ['Post agent-credentials', 'Post agent-credentials/current/renewal'].sort(),
    );
  });

  it('the seeding helpers live under test/ and e2e/ only, and no Dockerfile copies either', () => {
    const dockerfiles = [
      'services/data-gateway',
      'services/control-gateway',
      'services/org-gateway',
    ]
      .map((d) => readFileSync(join(repoRoot, d, 'Dockerfile'), 'utf8'))
      .join('\n');
    expect(dockerfiles).not.toMatch(/COPY\s+\S*(\/test\/|e2e)/);
    for (const f of sources)
      expect(f.text, f.path).not.toMatch(/seedAgentRevocation|seedRegistration/);
  });
});

describe('TC-AC-047: no tenant constant in U6’s code', () => {
  it('no organization, project, environment, agent, or human named as a string', () => {
    const tenantLike = /['"`](o1|p1|e|e2|h@example\.com|i-1|a-1|b-1)['"`]/;
    expect(matching(tenantLike)).toEqual([]);
  });
});

describe('TC-AC-074: nothing is pruned, and the store keeps U4’s guarantees', () => {
  it('no DELETE or TRUNCATE of U6’s tables anywhere in its code; S3 asserts synchronous_commit', () => {
    expect(
      matching(
        /\b(DELETE\s+FROM|TRUNCATE)\s+(agent_credentials|credential_revocations|agent_revocations|attempt_slots|failed_bootstrap_attempts|attribution_records)\b/i,
      ),
    ).toEqual([]);
    const main = readFileSync(join(repoRoot, 'services/data-gateway/src/main.ts'), 'utf8');
    expect(main).toContain("synchronous_commit !== 'on'");
  });
});

describe('TC-AC-075: no new external dependency', () => {
  const manifest = (dir: string) =>
    JSON.parse(readFileSync(join(repoRoot, dir, 'package.json'), 'utf8')) as {
      dependencies?: Record<string, string>;
      devDependencies?: Record<string, string>;
    };
  const external = (deps: Record<string, string> = {}) =>
    Object.fromEntries(Object.entries(deps).filter(([n]) => !n.startsWith('@soorma/')));

  it('S3’s external dependencies are S2’s, at S2’s exact versions', () => {
    const s2 = external(manifest('services/control-gateway').dependencies);
    for (const [name, version] of Object.entries(
      external(manifest('services/data-gateway').dependencies),
    ))
      expect(s2[name], name).toBe(version);
  });

  it('P6’s agent half and the seam add none', () => {
    for (const dir of ['packages/agent-identity', 'seams/identity-resolution']) {
      const m = manifest(dir);
      expect(external(m.dependencies), dir).toEqual({});
      expect(external(m.devDependencies), dir).toEqual({});
    }
  });
});
