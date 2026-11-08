// SPDX-License-Identifier: FSL-1.1-ALv2
//
// D-CG-12: the repository settings NFR-WC-17 depends on, read through `gh api`.
// Run at Build and Test with the developer's `gh` session: reading them needs
// repository admin access, which a workflow's GITHUB_TOKEN does not have.
//   - Dependabot vulnerability alerts are enabled
//   - the dependency graph is enabled and reads the lockfile: its SBOM lists the
//     workspace's direct dependencies (a two-document pnpm-lock.yaml would leave
//     it empty, Q-CG-1)
import type { Finding } from './workspace.ts';

export const REPOSITORY = 'soorma-ai/soorma-core';

export interface GithubSettings {
  /** HTTP status of GET /repos/{repo}/vulnerability-alerts: 204 when enabled, 404 when not. */
  vulnerabilityAlertsStatus: number;
  /** Package names from GET /repos/{repo}/dependency-graph/sbom, or undefined when it failed. */
  sbomPackages: string[] | undefined;
}

export function githubSettingsFindings(settings: GithubSettings, directNames: string[]): Finding[] {
  const findings: Finding[] = [];
  if (settings.vulnerabilityAlertsStatus !== 204) {
    findings.push({
      check: 'github-settings',
      location: `${REPOSITORY}: vulnerability alerts`,
      message: `not enabled (GET vulnerability-alerts returned ${settings.vulnerabilityAlertsStatus})`,
    });
  }
  if (settings.sbomPackages === undefined) {
    findings.push({
      check: 'github-settings',
      location: `${REPOSITORY}: dependency graph`,
      message: 'not enabled, or its SBOM could not be read',
    });
    return findings;
  }
  const listed = new Set(settings.sbomPackages.map((n) => n.replace(/^npm:/, '')));
  const missing = directNames.filter((n) => !listed.has(n));
  if (missing.length > 0) {
    findings.push({
      check: 'github-settings',
      location: `${REPOSITORY}: dependency graph`,
      message: `does not list ${missing.join(', ')}: it is not reading pnpm-lock.yaml`,
    });
  }
  return findings;
}

/** Package names from the dependency graph's SPDX SBOM response. */
export function sbomPackageNames(response: unknown): string[] {
  const packages = (response as { sbom?: { packages?: { name?: string }[] } }).sbom?.packages ?? [];
  return packages.map((p) => p.name ?? '').filter((n) => n !== '');
}
