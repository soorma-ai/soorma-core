// SPDX-License-Identifier: FSL-1.1-ALv2
//
// TC-AR-031 (I5; U5 D-AR-07, 10; BR-SP-07): a human's held set is tested in
// one place. S2 and P4 call P3's evaluators and nothing else that tests a
// set; the human-only class has one definition, in packages/authority.
import { readdirSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';

const root = join(import.meta.dirname, '../../..');
const sources = (dir: string): { file: string; text: string }[] =>
  readdirSync(join(root, dir), { recursive: true, encoding: 'utf8' })
    .filter((f) => f.endsWith('.ts'))
    .map((f) => ({ file: `${dir}/${f}`, text: readFileSync(join(root, dir, f), 'utf8') }));

const s2 = sources('services/control-gateway/src');
const p4 = sources('packages/registry/src');

describe('TC-AR-031: S2 and P4 import no evaluator or human-only class but P3', () => {
  it('neither calls the seam containment directly; S2 decides only through P3', () => {
    for (const { file, text } of [...s2, ...p4]) expect(text, file).not.toMatch(/\.contains\(/);
    const handlers = s2.find((s) => s.file.endsWith('edge/edge-handlers.ts'))!.text;
    for (const name of ['readHumanAuthority', 'checkRegistrationRequest', 'evaluateHuman'])
      expect(handlers).toContain(name);
    expect(handlers).toMatch(/from '@soorma\/authority'/);
  });

  it('no copy of the human-only class: only P4 accepted set names agent:delegate', () => {
    const naming = [...s2, ...p4].filter(({ text }) => text.includes("'agent:delegate'"));
    expect(naming.map((s) => s.file)).toEqual(['packages/registry/src/accepted.ts']);
    for (const { file, text } of [...s2, ...p4])
      expect(text, file).not.toContain('HUMAN_ONLY_PERMISSIONS');
  });

  it('P4 has no run-time dependency on P3', () => {
    const pkg = JSON.parse(readFileSync(join(root, 'packages/registry/package.json'), 'utf8')) as {
      dependencies: Record<string, string>;
    };
    expect(Object.keys(pkg.dependencies)).not.toContain('@soorma/authority');
  });
});
