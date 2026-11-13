// SPDX-License-Identifier: FSL-1.1-ALv2
//
// The installed-packages check (U6 NP-AC-10; D-CG-AC-11): which workspace
// packages a built image actually holds, from its exported file system.
//
//   node tools/checks/run.ts image-packages --image <ref> --forbid <name>[,<name>]
//   node tools/checks/run.ts image-packages --image <ref> --expect <name>[,<name>]
//
// A package is held when any path in the image is inside a directory named for
// it (node_modules/@soorma/<pkg>/, or pnpm's node_modules/.pnpm/@soorma+<pkg>@…/),
// or when any package.json in the image names it. --forbid fails on a held
// package (S2: no @soorma/org-identity; S3: no @soorma/org-identity or
// @soorma/identity-resolution). --expect fails on one not held: S1's image is
// the positive control, so the check is never vacuous. The image is exported
// and read once, with the secret scan, by image-scan.ts (#26).
import type { TarFile } from './tar.ts';
import type { Finding } from './workspace.ts';

export interface PackageQuery {
  readonly forbid: readonly string[];
  readonly expect: readonly string[];
}

const scopedDir = (name: string): string => `node_modules/${name}/`;
const pnpmDir = (name: string): string => `node_modules/.pnpm/${name.replace('/', '+')}@`;

/** The packages, among `names`, that a list of image files holds. */
export function heldPackages(files: readonly TarFile[], names: readonly string[]): Set<string> {
  const held = new Set<string>();
  for (const file of files) {
    for (const name of names) {
      if (file.name.includes(scopedDir(name)) || file.name.includes(pnpmDir(name))) held.add(name);
    }
    if (file.content && /(^|\/)package\.json$/.test(file.name)) {
      try {
        const declared = (JSON.parse(file.content.toString('utf8')) as { name?: unknown }).name;
        if (typeof declared === 'string' && names.includes(declared)) held.add(declared);
      } catch {
        // not JSON: no name to read
      }
    }
  }
  return held;
}

export function packageFindings(
  image: string,
  files: readonly TarFile[],
  query: PackageQuery,
): Finding[] {
  const held = heldPackages(files, [...query.forbid, ...query.expect]);
  return [
    ...query.forbid
      .filter((n) => held.has(n))
      .map((n) => ({ check: 'image-packages', location: image, message: `holds ${n}` })),
    ...query.expect
      .filter((n) => !held.has(n))
      .map((n) => ({ check: 'image-packages', location: image, message: `does not hold ${n}` })),
  ];
}
