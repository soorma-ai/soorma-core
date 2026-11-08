// SPDX-License-Identifier: FSL-1.1-ALv2
// Type-aware lint catches unhandled promises: TC-WC-041.
import { join } from 'node:path';
import { ESLint } from 'eslint';
import { describe, expect, it } from 'vitest';
import { repoRoot } from '../checks/workspace.ts';

const fixture = join(repoRoot, 'tools/test/fixtures/lint/floating-promise.ts');

describe('TC-WC-041: type-aware lint catches unhandled promises', () => {
  it('the normal lint run excludes the fixture', async () => {
    const eslint = new ESLint({ cwd: repoRoot });
    expect(await eslint.isPathIgnored(fixture)).toBe(true);
  });

  it('linting the fixture through the Node API finds exactly the floating promise', async () => {
    const eslint = new ESLint({ cwd: repoRoot, ignore: false });
    const [result] = await eslint.lintFiles([fixture]);
    const errors = (result?.messages ?? []).filter((m) => m.severity === 2);
    expect(errors.map((m) => m.ruleId)).toEqual(['@typescript-eslint/no-floating-promises']);
    expect(errors[0]?.line).toBe(13);
  });
});
