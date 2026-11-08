// SPDX-License-Identifier: FSL-1.1-ALv2
//
// NFR-WC-14: the resolved dependency tree against the licence allowlist, by scope.
//
//   Direct and runtime dependencies (runtime transitive included):
//     MIT, Apache-2.0, BSD-2-Clause, BSD-3-Clause, ISC, 0BSD
//   Development-only transitive dependencies may also use:
//     BlueOak-1.0.0, Python-2.0, CC0-1.0, CC-BY-4.0
//   Anything else only through a row under "Licence exceptions" in DEPENDENCIES.md.
//
// An exception row names packages (an exact name, or a prefix ending in `*`) and
// exactly one licence, never a version. A package it names is accepted only while
// its licence equals the row's, so a version bump needs no edit and a licence
// change fails the check (Q-CG-2 A).
import { namesIn, tableUnder, type Finding } from './workspace.ts';

export const STRICT = ['MIT', 'Apache-2.0', 'BSD-2-Clause', 'BSD-3-Clause', 'ISC', '0BSD'];
export const DEV_TRANSITIVE_EXTRA = ['BlueOak-1.0.0', 'Python-2.0', 'CC0-1.0', 'CC-BY-4.0'];

export interface ResolvedPackage {
  name: string;
  version: string;
  licence: string;
  /** Reachable from a runtime dependency. */
  runtime: boolean;
  /** A direct dependency of some workspace package. */
  direct: boolean;
}

export interface LicenceException {
  names: string[];
  licence: string;
}

export function parseLicenceExceptions(register: string): LicenceException[] {
  return tableUnder(register, 'Licence exceptions').map((cells) => ({
    names: namesIn(cells[0] ?? ''),
    licence: (cells[1] ?? '').replace(/`/g, ''),
  }));
}

function named(names: string[], pkg: string): boolean {
  return names.some((n) => (n.endsWith('*') ? pkg.startsWith(n.slice(0, -1)) : n === pkg));
}

/** True when an SPDX expression is satisfied by the allowed licences. */
export function satisfies(expression: string, allowed: string[]): boolean {
  const expr = expression.trim().replace(/^\((.*)\)$/, '$1');
  if (/\sOR\s/.test(expr)) return expr.split(/\s+OR\s+/).some((e) => satisfies(e, allowed));
  if (/\sAND\s/.test(expr)) return expr.split(/\s+AND\s+/).every((e) => satisfies(e, allowed));
  return allowed.includes(expr);
}

export function licenceFindings(
  packages: ResolvedPackage[],
  exceptions: LicenceException[],
): Finding[] {
  const findings: Finding[] = [];
  for (const p of packages) {
    const allowed = p.runtime || p.direct ? STRICT : [...STRICT, ...DEV_TRANSITIVE_EXTRA];
    if (satisfies(p.licence, allowed)) continue;
    const rows = exceptions.filter((e) => named(e.names, p.name));
    if (rows.some((e) => e.licence === p.licence)) continue;
    const scope = p.runtime || p.direct ? 'a direct or runtime' : 'a development-only transitive';
    findings.push({
      check: 'licence',
      location: `${p.name}@${p.version}`,
      message:
        rows.length > 0
          ? `licence ${p.licence} does not match its exception row (${rows.map((r) => r.licence).join(', ')})`
          : `licence ${p.licence} is not allowed for ${scope} dependency, and no exception row names it`,
    });
  }
  return findings;
}

interface PnpmLicenceEntry {
  name: string;
  versions?: string[];
  version?: string;
}

/** Turns `pnpm licenses list --json` output (all, and --prod) into resolved packages. */
export function fromPnpmLicences(
  all: Record<string, PnpmLicenceEntry[]>,
  prod: Record<string, PnpmLicenceEntry[]>,
  directNames: Set<string>,
): ResolvedPackage[] {
  const runtime = new Set(Object.values(prod).flatMap((list) => list.map((e) => e.name)));
  return Object.entries(all).flatMap(([licence, list]) =>
    list.flatMap((e) =>
      (e.versions ?? [e.version ?? '']).map((version) => ({
        name: e.name,
        version,
        licence,
        runtime: runtime.has(e.name),
        direct: directNames.has(e.name),
      })),
    ),
  );
}
