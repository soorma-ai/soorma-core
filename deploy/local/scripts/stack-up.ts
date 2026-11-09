// SPDX-License-Identifier: FSL-1.1-ALv2
//
// pnpm stack:up: checks the minimum versions, then builds and starts the
// local stack and waits for it to be healthy.
//
// The secrets design (Infrastructure Design §3, amended: Q-CG-4 B) mounts
// each service's own subpath of its level's secrets volume, which needs:
//   - Docker Engine 26 or later (Engine API 1.45 added volume subpaths)
//   - Docker Compose 2.26.0 or later (the first release that passes a
//     volume's subpath to the Engine; 2.25 parses it and drops it)
// It refuses to start with a clear message otherwise.
import { execFileSync, spawnSync } from 'node:child_process';
import { join, resolve } from 'node:path';

export const MIN_ENGINE = [26, 0, 0] as const;
export const MIN_COMPOSE = [2, 26, 0] as const;
const COMPOSE_FILE = join(resolve(import.meta.dirname, '..'), 'compose.yaml');

/** The x.y.z at the start of a version string (`v2.38.2`, `28.0.4`, `5.1.4-desktop.1`). */
export function parseVersion(text: string): [number, number, number] | undefined {
  const m = /^v?(\d+)\.(\d+)\.(\d+)/.exec(text.trim());
  return m ? [Number(m[1]), Number(m[2]), Number(m[3])] : undefined;
}

export function atLeast(version: readonly number[], minimum: readonly number[]): boolean {
  for (let i = 0; i < 3; i++) {
    if (version[i]! !== minimum[i]!) return version[i]! > minimum[i]!;
  }
  return true;
}

/** The problems with the installed versions; none when both meet the minimums. */
export function versionProblems(engine: string, compose: string): string[] {
  const problems: string[] = [];
  const e = parseVersion(engine);
  const c = parseVersion(compose);
  if (!e || !atLeast(e, MIN_ENGINE))
    problems.push(
      `Docker Engine ${engine || 'unknown'} is too old: the stack needs ${MIN_ENGINE.join('.')} or later (volume subpaths).`,
    );
  if (!c || !atLeast(c, MIN_COMPOSE))
    problems.push(
      `Docker Compose ${compose || 'unknown'} is too old: the stack needs ${MIN_COMPOSE.join('.')} or later (it passes volume subpaths to the Engine).`,
    );
  return problems;
}

function read(args: string[]): string {
  try {
    return execFileSync('docker', args, {
      encoding: 'utf8',
      stdio: ['ignore', 'pipe', 'ignore'],
    }).trim();
  } catch {
    return '';
  }
}

if (import.meta.main) {
  const problems = versionProblems(
    read(['version', '--format', '{{.Server.Version}}']),
    read(['compose', 'version', '--short']),
  );
  if (problems.length > 0) {
    for (const p of problems) console.error(p);
    console.error('pnpm stack:up refused to start. Upgrade Docker, then run it again.');
    process.exit(1);
  }
  const up = spawnSync(
    'docker',
    ['compose', '-f', COMPOSE_FILE, 'up', '-d', '--build', '--wait', ...process.argv.slice(2)],
    { stdio: 'inherit' },
  );
  process.exit(up.status ?? 1);
}
