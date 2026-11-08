// SPDX-License-Identifier: FSL-1.1-ALv2
//
// The workspace configuration (NFR-WC-12, 15, 16, 19; D-CG-13; Q-CG-1 A):
// - every dependency version is exact
// - the 7-day release cooldown, and lifecycle scripts refused with an empty allowlist
// - .node-version is exact, and engines.node is "^" plus it
// - packageManager pins pnpm exactly, and the running pnpm is that version
// - pmOnFail is "ignore" (so the lockfile stays one document GitHub can read)
// - no Corepack anywhere
import { directDependencies, type Finding, type PackageManifest } from './workspace.ts';

const EXACT = /^\d+\.\d+\.\d+(-[0-9A-Za-z.-]+)?$/;

export interface ConfigurationInput {
  manifests: PackageManifest[];
  settings: Record<string, unknown>;
  nodeVersion: string;
  /** `pnpm --version` as run, when known. */
  runningPnpm?: string;
  /** Files to scan for Corepack: package manifests, workflows, settings. */
  texts: { path: string; text: string }[];
}

export function configurationFindings(input: ConfigurationInput): Finding[] {
  const findings: Finding[] = [];
  const add = (location: string, message: string): void => {
    findings.push({ check: 'configuration', location, message });
  };

  for (const d of directDependencies(input.manifests)) {
    if (!EXACT.test(d.version))
      add(`${d.manifest}: ${d.name}`, `version ${d.version} is not exact`);
  }

  const s = input.settings;
  if (s.minimumReleaseAge !== 10080)
    add('pnpm-workspace.yaml: minimumReleaseAge', 'must be 10080 (7 days)');
  if (s.saveExact !== true) add('pnpm-workspace.yaml: saveExact', 'must be true');
  if (s.strictDepBuilds !== true) add('pnpm-workspace.yaml: strictDepBuilds', 'must be true');
  const allow = s.allowBuilds;
  if (typeof allow !== 'object' || allow === null || Object.keys(allow).length > 0) {
    add(
      'pnpm-workspace.yaml: allowBuilds',
      'the lifecycle-script allowlist must be empty in U1 ({})',
    );
  }
  if ('onlyBuiltDependencies' in s)
    add('pnpm-workspace.yaml: onlyBuiltDependencies', 'use allowBuilds, which must be empty');
  if (s.pmOnFail !== 'ignore') {
    add(
      'pnpm-workspace.yaml: pmOnFail',
      'must be "ignore", so pnpm-lock.yaml stays a single document (Q-CG-1)',
    );
  }

  if (!EXACT.test(input.nodeVersion))
    add('.node-version', `${input.nodeVersion} is not an exact x.y.z version`);
  const root = input.manifests.find((m) => m.path === 'package.json');
  if (!root) {
    add('package.json', 'missing');
    return findings;
  }
  const engines = root.engines?.node;
  if (engines !== `^${input.nodeVersion}`) {
    add(
      'package.json: engines.node',
      `must be ^${input.nodeVersion}, from .node-version; found ${engines ?? 'nothing'}`,
    );
  }
  const pm = /^pnpm@(\d+\.\d+\.\d+)$/.exec(root.packageManager ?? '');
  if (!pm) {
    add(
      'package.json: packageManager',
      `must pin pnpm exactly (pnpm@x.y.z); found ${root.packageManager ?? 'nothing'}`,
    );
  } else if (input.runningPnpm !== undefined && input.runningPnpm !== pm[1]) {
    add('pnpm --version', `running pnpm ${input.runningPnpm}, but packageManager pins ${pm[1]}`);
  }

  for (const { path, text } of input.texts) {
    if (/\bcorepack\s+(enable|prepare|use|install)\b|\bCOREPACK_[A-Z_]+/i.test(text)) {
      add(path, 'uses Corepack; pnpm is installed without it (NFR-WC-19)');
    }
  }
  return findings;
}
