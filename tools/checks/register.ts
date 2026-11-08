// SPDX-License-Identifier: FSL-1.1-ALv2
//
// NFR-WC-13: every direct dependency of every workspace package has a row in
// DEPENDENCIES.md, under "Direct dependencies"; every pnpm override has a row
// under "Overrides" (D-CG-16).
import { namesIn, tableUnder, type DirectDependency, type Finding } from './workspace.ts';

export function registerFindings(
  direct: DirectDependency[],
  register: string,
  overrides: Record<string, string> = {},
): Finding[] {
  const rows = tableUnder(register, 'Direct dependencies');
  const registered = new Set(rows.flatMap((cells) => namesIn(cells[0] ?? '')));
  const overrideRows = new Set(
    tableUnder(register, 'Overrides').flatMap((cells) => namesIn(cells[0] ?? '')),
  );
  return [
    ...direct
      .filter((d) => !registered.has(d.name))
      .map((d) => ({
        check: 'register',
        location: `${d.manifest}: ${d.name}`,
        message: 'direct dependency with no row in DEPENDENCIES.md',
      })),
    ...Object.keys(overrides)
      .filter((o) => !overrideRows.has(o))
      .map((o) => ({
        check: 'register',
        location: `pnpm-workspace.yaml: overrides: ${o}`,
        message: 'override with no row under "Overrides" in DEPENDENCIES.md',
      })),
  ];
}
