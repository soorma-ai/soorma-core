// SPDX-License-Identifier: FSL-1.1-ALv2
// CI integrity and the GitHub settings check: TC-WC-040.
import { describe, expect, it } from 'vitest';
import { parse } from 'yaml';
import { githubSettingsFindings, sbomPackageNames } from '../checks/github-settings.ts';
import { workflowFindings } from '../checks/workflows.ts';
import { loadWorkflows } from '../checks/workspace.ts';

const workflows = loadWorkflows();
const ci = workflows.find((w) => w.path === '.github/workflows/ci.yml')!;

describe('TC-WC-040: CI runs pinned, least-privilege, and scans every build', () => {
  it('steps 1 and 2: every uses: is SHA-pinned, and permissions default to contents: read', () => {
    expect(workflows.map((w) => w.path)).toEqual([
      '.github/workflows/ci.yml',
      '.github/workflows/cla.yml',
    ]);
    expect(workflowFindings(workflows)).toEqual([]);
  });

  it('step 3: the CI workflow runs every required step', () => {
    const runs = (
      parse(ci.text) as { jobs: { build: { steps: { run?: string; uses?: string }[] } } }
    ).jobs.build.steps
      .map((s) => s.run ?? s.uses ?? '')
      .join('\n');
    for (const step of [
      'pnpm install --frozen-lockfile',
      'pnpm run check:deps',
      'pnpm run check:workflows',
      'pnpm run build',
      'pnpm run lint',
      'pnpm run format:check',
      'pnpm run check:generated',
      'pnpm run check:contract',
      'pnpm test',
      'pnpm audit --audit-level moderate',
      'anchore/sbom-action@',
      'actions/upload-artifact@',
    ]) {
      expect(runs).toContain(step);
    }
  });

  it('step 4: dependency review runs on pull requests, failing at moderate', () => {
    const review = (
      parse(ci.text) as {
        jobs: Record<
          string,
          { if?: string; steps: { uses?: string; with?: Record<string, string> }[] }
        >;
      }
    ).jobs['dependency-review']!;
    expect(review.if).toBe("github.event_name == 'pull_request'");
    expect(
      review.steps.find((s) => s.uses?.startsWith('actions/dependency-review-action@'))?.with?.[
        'fail-on-severity'
      ],
    ).toBe('moderate');
  });

  it('step 6: refuses a uses: pinned to a tag', () => {
    const changed = ci.text.replace(/actions\/checkout@[0-9a-f]{40}/, 'actions/checkout@v4');
    expect(workflowFindings([{ path: ci.path, text: changed }])).toContainEqual(
      expect.objectContaining({
        message: '`uses: actions/checkout@v4` is not pinned by a 40-character commit SHA',
      }),
    );
  });

  it('refuses a widened default, and a job that widens permissions without a reason', () => {
    const widened = ci.text.replace('permissions:\n  contents: read', 'permissions: write-all');
    expect(workflowFindings([{ path: ci.path, text: widened }])).toContainEqual(
      expect.objectContaining({ location: `${ci.path}: permissions` }),
    );
    const job =
      'permissions:\n  contents: read\njobs:\n  x:\n    runs-on: ubuntu-24.04\n    permissions:\n      contents: write\n    steps: []\n';
    expect(workflowFindings([{ path: 'x.yml', text: job }])).toContainEqual(
      expect.objectContaining({ location: 'x.yml: jobs.x.permissions' }),
    );
  });
});

describe('D-CG-12: the GitHub settings check, on recorded responses', () => {
  const sbom = {
    sbom: {
      packages: [
        { name: 'npm:eslint' },
        { name: 'npm:ajv' },
        { name: 'com.github.soorma-ai/soorma-core' },
      ],
    },
  };

  it('passes when alerts are on and the graph lists the direct dependencies', () => {
    expect(
      githubSettingsFindings(
        { vulnerabilityAlertsStatus: 204, sbomPackages: sbomPackageNames(sbom) },
        ['eslint', 'ajv'],
      ),
    ).toEqual([]);
  });

  it('fails when vulnerability alerts are off', () => {
    expect(
      githubSettingsFindings(
        { vulnerabilityAlertsStatus: 404, sbomPackages: sbomPackageNames(sbom) },
        ['eslint'],
      ),
    ).toHaveLength(1);
  });

  it('fails when the graph is off, or does not read the lockfile', () => {
    expect(
      githubSettingsFindings({ vulnerabilityAlertsStatus: 204, sbomPackages: undefined }, [
        'eslint',
      ]),
    ).toHaveLength(1);
    const blind = githubSettingsFindings(
      { vulnerabilityAlertsStatus: 204, sbomPackages: ['com.github.soorma-ai/soorma-core'] },
      ['eslint'],
    );
    expect(blind[0]?.message).toContain('it is not reading pnpm-lock.yaml');
  });
});
