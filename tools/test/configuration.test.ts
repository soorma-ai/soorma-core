// SPDX-License-Identifier: FSL-1.1-ALv2
// The workspace configuration: TC-WC-039.
import { execFileSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';
import { configurationFindings, type ConfigurationInput } from '../checks/configuration.ts';
import { loadWorkflows, loadWorkspace, repoRoot } from '../checks/workspace.ts';

const workspace = loadWorkspace();
const runningPnpm = execFileSync('pnpm', ['--version'], { cwd: repoRoot, encoding: 'utf8' }).trim();

function input(change?: (i: ConfigurationInput) => void): ConfigurationInput {
  const i: ConfigurationInput = structuredClone({
    manifests: workspace.manifests,
    settings: workspace.settings,
    nodeVersion: workspace.nodeVersion,
    runningPnpm,
    texts: loadWorkflows(),
  });
  change?.(i);
  return i;
}

const root = (i: ConfigurationInput): ConfigurationInput['manifests'][number] =>
  i.manifests.find((m) => m.path === 'package.json')!;

describe('TC-WC-039: installs are reproducible, and the toolchain is pinned', () => {
  it('step 1: the workspace as committed passes every item', () => {
    expect(readFileSync(join(repoRoot, 'pnpm-lock.yaml'), 'utf8')).toMatch(/^lockfileVersion:/);
    expect(workspace.nodeVersion).toBe('26.13.0');
    expect(root(input()).engines?.node).toBe('^26.13.0');
    expect(root(input()).packageManager).toMatch(/^pnpm@12\.\d+\.\d+$/);
    expect(workspace.settings).toMatchObject({
      minimumReleaseAge: 10080,
      pmOnFail: 'ignore',
      allowBuilds: {},
      strictDepBuilds: true,
    });
    expect(configurationFindings(input())).toEqual([]);
  });

  it('keeps pnpm-lock.yaml a single YAML document (Q-CG-1)', () => {
    const lock = readFileSync(join(repoRoot, 'pnpm-lock.yaml'), 'utf8');
    expect(lock.split('\n').filter((l) => l === '---')).toEqual([]);
  });

  it('step 3: reports a running pnpm other than packageManager names', () => {
    expect(configurationFindings(input((i) => (i.runningPnpm = '11.0.0')))).toContainEqual(
      expect.objectContaining({ location: 'pnpm --version' }),
    );
  });

  it('step 4: rejects a version range', () => {
    const findings = configurationFindings(
      input((i) => (root(i).devDependencies!.prettier = '^3.9.10')),
    );
    expect(findings).toContainEqual(
      expect.objectContaining({ location: 'package.json: prettier' }),
    );
  });

  it('rejects engines.node that does not agree with .node-version (D-CG-13)', () => {
    expect(
      configurationFindings(input((i) => (root(i).engines = { node: '>=26' }))),
    ).toContainEqual(expect.objectContaining({ location: 'package.json: engines.node' }));
    expect(configurationFindings(input((i) => (i.nodeVersion = '26.14.0')))).toContainEqual(
      expect.objectContaining({ location: 'package.json: engines.node' }),
    );
  });

  it.each([
    ['minimumReleaseAge', 1440],
    ['pmOnFail', 'error'],
    ['allowBuilds', { esbuild: true }],
    ['strictDepBuilds', false],
  ])('rejects %s set to %j', (key, value) => {
    const findings = configurationFindings(input((i) => (i.settings[key] = value)));
    expect(findings).toContainEqual(
      expect.objectContaining({ location: `pnpm-workspace.yaml: ${key}` }),
    );
  });

  it('rejects a step that enables Corepack', () => {
    const findings = configurationFindings(
      input((i) =>
        i.texts.push({
          path: '.github/workflows/x.yml',
          text: 'steps:\n  - run: corepack enable\n',
        }),
      ),
    );
    expect(findings).toContainEqual(
      expect.objectContaining({ location: '.github/workflows/x.yml' }),
    );
  });
});
