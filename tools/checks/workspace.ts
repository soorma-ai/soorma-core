// SPDX-License-Identifier: FSL-1.1-ALv2
//
// Reads the workspace: package manifests, pnpm settings, the toolchain pins, the
// dependency register, and the workflows. Each check is a pure function over
// what this module reads, so tests can run it against mutated copies.
import { existsSync, readFileSync, readdirSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { parse as parseYaml } from 'yaml';

export const repoRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..', '..');

export interface Finding {
  check: string;
  location: string;
  message: string;
}

export interface PackageManifest {
  /** Path relative to the repository root. */
  path: string;
  name: string;
  license?: string;
  engines?: Record<string, string>;
  packageManager?: string;
  scripts?: Record<string, string>;
  dependencies?: Record<string, string>;
  devDependencies?: Record<string, string>;
  optionalDependencies?: Record<string, string>;
  peerDependencies?: Record<string, string>;
}

export interface DirectDependency {
  name: string;
  version: string;
  manifest: string;
  kind: 'runtime' | 'development';
}

export interface Workspace {
  manifests: PackageManifest[];
  settings: Record<string, unknown>;
  nodeVersion: string;
  register: string;
}

function readText(path: string): string {
  return readFileSync(join(repoRoot, path), 'utf8');
}

/**
 * The package directories a `packages` entry names: a directory, or `dir/*` for
 * each subdirectory of `dir` holding a package.json. No other glob form is used.
 */
export function expandPackages(entries: string[], root: string = repoRoot): string[] {
  return entries.flatMap((entry) => {
    if (!entry.endsWith('/*')) return [entry];
    const dir = entry.slice(0, -2);
    return readdirSync(join(root, dir), { withFileTypes: true })
      .filter((d) => d.isDirectory() && existsSync(join(root, dir, d.name, 'package.json')))
      .map((d) => `${dir}/${d.name}`)
      .sort();
  });
}

export function loadWorkspace(): Workspace {
  const settings = parseYaml(readText('pnpm-workspace.yaml')) as Record<string, unknown>;
  const packages = expandPackages((settings.packages as string[] | undefined) ?? []);
  const manifests = ['package.json', ...packages.map((p) => `${p}/package.json`)].map((path) => ({
    ...(JSON.parse(readText(path)) as Omit<PackageManifest, 'path'>),
    path,
  }));
  return {
    manifests,
    settings,
    nodeVersion: readText('.node-version').trim(),
    register: readText('DEPENDENCIES.md'),
  };
}

/** The workspace protocol: a dependency on another package of this workspace. */
export const WORKSPACE_PROTOCOL = 'workspace:';

/**
 * Every direct third-party dependency of every workspace package. A dependency
 * on another workspace package (`workspace:*`) is not third-party: it is listed
 * by workspaceDependencies, and checked by the configuration check.
 */
export function directDependencies(manifests: PackageManifest[]): DirectDependency[] {
  return allDependencies(manifests).filter((d) => !d.version.startsWith(WORKSPACE_PROTOCOL));
}

/** Every dependency of one workspace package on another (`workspace:` versions). */
export function workspaceDependencies(manifests: PackageManifest[]): DirectDependency[] {
  return allDependencies(manifests).filter((d) => d.version.startsWith(WORKSPACE_PROTOCOL));
}

function allDependencies(manifests: PackageManifest[]): DirectDependency[] {
  const out: DirectDependency[] = [];
  for (const m of manifests) {
    for (const [name, version] of Object.entries(m.dependencies ?? {})) {
      out.push({ name, version, manifest: m.path, kind: 'runtime' });
    }
    for (const [name, version] of Object.entries(m.optionalDependencies ?? {})) {
      out.push({ name, version, manifest: m.path, kind: 'runtime' });
    }
    for (const [name, version] of Object.entries(m.devDependencies ?? {})) {
      out.push({ name, version, manifest: m.path, kind: 'development' });
    }
  }
  return out;
}

/** The workflow files under .github/workflows/, with their text. */
export function loadWorkflows(): { path: string; text: string }[] {
  const dir = '.github/workflows';
  return readdirSync(join(repoRoot, dir))
    .filter((f) => f.endsWith('.yml') || f.endsWith('.yaml'))
    .sort()
    .map((f) => ({ path: `${dir}/${f}`, text: readText(`${dir}/${f}`) }));
}

/** The rows of the Markdown table under `## {heading}` in the register, as cell arrays. */
export function tableUnder(markdown: string, heading: string): string[][] {
  const start = markdown.indexOf(`\n## ${heading}\n`);
  if (start === -1) return [];
  const rest = markdown.slice(start + heading.length + 5);
  const end = rest.search(/\n## /);
  const section = end === -1 ? rest : rest.slice(0, end);
  return section
    .split('\n')
    .filter((l) => l.trim().startsWith('|'))
    .slice(2)
    .map((l) =>
      l
        .trim()
        .replace(/^\||\|$/g, '')
        .split('|')
        .map((c) => c.trim()),
    );
}

/** The backticked names in a register cell: "`a`, `b-*`" gives ["a", "b-*"]. */
export function namesIn(cell: string): string[] {
  return [...cell.matchAll(/`([^`]+)`/g)].map((m) => m[1] as string);
}
