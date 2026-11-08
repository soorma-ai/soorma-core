// SPDX-License-Identifier: FSL-1.1-ALv2
//
// Runs the named repository checks against the workspace on disk, and exits
// non-zero on any finding:
//   node tools/checks/run.ts register licence configuration
//   node tools/checks/run.ts workflows
//   node tools/checks/run.ts github-settings
import { execFileSync, spawnSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { configurationFindings } from './configuration.ts';
import { githubSettingsFindings, REPOSITORY, sbomPackageNames } from './github-settings.ts';
import { fromPnpmLicences, licenceFindings, parseLicenceExceptions } from './licence.ts';
import { registerFindings } from './register.ts';
import { workflowFindings } from './workflows.ts';
import {
  directDependencies,
  loadWorkflows,
  loadWorkspace,
  repoRoot,
  type Finding,
  type Workspace,
} from './workspace.ts';

function pnpmJson(args: string[]): Record<string, { name: string; versions?: string[] }[]> {
  const out = execFileSync('pnpm', args, { cwd: repoRoot, encoding: 'utf8' }).trim();
  return out.startsWith('{')
    ? (JSON.parse(out) as Record<string, { name: string; versions?: string[] }[]>)
    : {};
}

const checks: Record<string, (ws: Workspace) => Finding[]> = {
  register: (ws) =>
    registerFindings(
      directDependencies(ws.manifests),
      ws.register,
      (ws.settings.overrides as Record<string, string> | undefined) ?? {},
    ),

  licence: (ws) => {
    const direct = new Set(directDependencies(ws.manifests).map((d) => d.name));
    const packages = fromPnpmLicences(
      // -r: every workspace package's tree, not only the root's. Lists what is
      // installed, so each platform checks its own native packages.
      pnpmJson(['-r', 'licenses', 'list', '--json']),
      pnpmJson(['-r', 'licenses', 'list', '--json', '--prod']),
      direct,
    );
    return licenceFindings(packages, parseLicenceExceptions(ws.register));
  },

  configuration: (ws) =>
    configurationFindings({
      manifests: ws.manifests,
      settings: ws.settings,
      nodeVersion: ws.nodeVersion,
      runningPnpm: execFileSync('pnpm', ['--version'], { cwd: repoRoot, encoding: 'utf8' }).trim(),
      texts: [
        ...ws.manifests.map((m) => ({
          path: m.path,
          text: readFileSync(join(repoRoot, m.path), 'utf8'),
        })),
        {
          path: 'pnpm-workspace.yaml',
          text: readFileSync(join(repoRoot, 'pnpm-workspace.yaml'), 'utf8'),
        },
        ...loadWorkflows(),
      ],
    }),

  workflows: () => workflowFindings(loadWorkflows()),

  'github-settings': (ws) => {
    const alerts = spawnSync('gh', ['api', '-i', `repos/${REPOSITORY}/vulnerability-alerts`], {
      encoding: 'utf8',
    });
    const status = Number(/^HTTP\/[\d.]+ (\d{3})/m.exec(alerts.stdout ?? '')?.[1] ?? 0);
    const sbom = spawnSync('gh', ['api', `repos/${REPOSITORY}/dependency-graph/sbom`], {
      encoding: 'utf8',
    });
    const packages =
      sbom.status === 0 ? sbomPackageNames(JSON.parse(sbom.stdout) as unknown) : undefined;
    const direct = [...new Set(directDependencies(ws.manifests).map((d) => d.name))];
    return githubSettingsFindings(
      { vulnerabilityAlertsStatus: status, sbomPackages: packages },
      direct,
    );
  },
};

if (import.meta.main) {
  const names = process.argv.slice(2);
  const unknown = names.filter((n) => !(n in checks));
  if (names.length === 0 || unknown.length > 0) {
    console.error(`usage: node tools/checks/run.ts <${Object.keys(checks).join('|')}>...`);
    process.exit(2);
  }
  const workspace = loadWorkspace();
  const findings = names.flatMap((n) => checks[n]!(workspace));
  for (const f of findings) console.error(`${f.check}: ${f.location}: ${f.message}`);
  if (findings.length > 0) {
    console.error(`${findings.length} finding(s).`);
    process.exitCode = 1;
  } else {
    console.log(`Passed: ${names.join(', ')}.`);
  }
}
