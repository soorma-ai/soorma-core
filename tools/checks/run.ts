// SPDX-License-Identifier: FSL-1.1-ALv2
//
// Runs the named repository checks against the workspace on disk, and exits
// non-zero on any finding:
//   node tools/checks/run.ts register licence configuration
//   node tools/checks/run.ts workflows
//   node tools/checks/run.ts github-settings
//   node tools/checks/run.ts breached
//   node tools/checks/run.ts sql compare inject
//   node tools/checks/run.ts secrets [--image <ref>]
//   node tools/checks/run.ts image-packages --image <ref> [--forbid <names>] [--expect <names>]
import { execFileSync, spawnSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { breachedFindings, BREACHED_PATH, MANIFEST_PATH } from './breached.ts';
import { codeFindings } from './code.ts';
import { imagePackageFindings } from './image-packages.ts';
import { imageFindings, repositoryFindings } from './secrets.ts';
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

/** `--image <ref>` on the command line: the secrets check scans that image instead. */
function imageArgument(): string | undefined {
  const i = process.argv.indexOf('--image');
  return i === -1 ? undefined : process.argv[i + 1];
}

/** An option's value from the command line: `--forbid a,b` gives ['a', 'b']. */
function listArgument(option: string): string[] {
  const i = process.argv.indexOf(option);
  return i === -1 ? [] : (process.argv[i + 1] ?? '').split(',').filter((n) => n.length > 0);
}

/** The options that take a value, so their values are not read as check names. */
const VALUE_OPTIONS = ['--image', '--forbid', '--expect'];

const checks: Record<string, (ws: Workspace) => Finding[] | Promise<Finding[]>> = {
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

  sql: () => codeFindings('sql'),
  compare: () => codeFindings('compare'),
  inject: () => codeFindings('inject'),
  secrets: () => {
    const image = imageArgument();
    return image === undefined ? repositoryFindings() : imageFindings(image);
  },

  'image-packages': () => {
    const image = imageArgument();
    return image === undefined
      ? [{ check: 'image-packages', location: '-', message: 'needs --image <ref>' }]
      : imagePackageFindings(image, {
          forbid: listArgument('--forbid'),
          expect: listArgument('--expect'),
        });
  },

  breached: () =>
    breachedFindings(
      readFileSync(join(repoRoot, BREACHED_PATH)),
      readFileSync(join(repoRoot, MANIFEST_PATH), 'utf8'),
    ),

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

async function main(): Promise<void> {
  const image = imageArgument();
  const names = process.argv
    .slice(2)
    .filter((a, i, all) => !VALUE_OPTIONS.includes(a) && !VALUE_OPTIONS.includes(all[i - 1] ?? ''));
  const unknown = names.filter((n) => !(n in checks));
  if (
    names.length === 0 ||
    unknown.length > 0 ||
    (image !== undefined && !names.includes('secrets') && !names.includes('image-packages'))
  ) {
    console.error(
      `usage: node tools/checks/run.ts <${Object.keys(checks).join('|')}>... [--image <ref>] [--forbid <names>] [--expect <names>]`,
    );
    process.exit(2);
  }
  const workspace = loadWorkspace();
  const findings: Finding[] = [];
  for (const n of names) findings.push(...(await checks[n]!(workspace)));
  for (const f of findings) console.error(`${f.check}: ${f.location}: ${f.message}`);
  if (findings.length > 0) {
    console.error(`${findings.length} finding(s).`);
    process.exitCode = 1;
  } else {
    console.log(`Passed: ${names.join(', ')}${image ? ` (${image})` : ''}.`);
  }
}

if (import.meta.main) {
  main().catch((error: unknown) => {
    console.error(error);
    process.exitCode = 1;
  });
}
