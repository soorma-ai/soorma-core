// SPDX-License-Identifier: Apache-2.0
//
// NFR-WC-21: every file under contract/ declares Apache-2.0, in its own header
// or, for a file that cannot carry one, through REUSE.toml (D-CG-03).
import { readFileSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { contractRoot, listFiles, type Finding } from './model.ts';

export interface ReuseAnnotation {
  /** A path relative to the repository root, `**` matching any suffix. */
  path: string;
  licence: string;
}

const HEADER = 'SPDX-License-Identifier: Apache-2.0';

/** Reads the `[[annotations]]` of a REUSE.toml written in the repository's own form. */
export function parseReuse(text: string): ReuseAnnotation[] {
  const out: ReuseAnnotation[] = [];
  let current: Partial<ReuseAnnotation> | undefined;
  for (const line of text.split('\n')) {
    const trimmed = line.trim();
    if (trimmed === '[[annotations]]') {
      current = {};
      out.push(current as ReuseAnnotation);
      continue;
    }
    const m = /^([A-Za-z-]+)\s*=\s*"([^"]*)"$/.exec(trimmed);
    if (!m || !current) continue;
    if (m[1] === 'path') current.path = m[2];
    if (m[1] === 'SPDX-License-Identifier') current.licence = m[2];
  }
  return out.filter((a) => a.path && a.licence);
}

function matches(annotationPath: string, repoPath: string): boolean {
  if (annotationPath.endsWith('/**')) return repoPath.startsWith(annotationPath.slice(0, -2));
  return annotationPath === repoPath;
}

/** `files` are paths relative to contract/, with their text. */
export function spdxFindings(
  files: { path: string; text: string }[],
  reuse: ReuseAnnotation[],
): Finding[] {
  const findings: Finding[] = [];
  for (const { path, text } of files) {
    if (path === 'LICENSE') continue;
    const repoPath = `contract/${path}`;
    const annotation = reuse.find((a) => matches(a.path, repoPath));
    if (annotation) {
      if (annotation.licence !== 'Apache-2.0') {
        findings.push({
          check: 'spdx',
          location: path,
          message: `REUSE.toml declares ${annotation.licence}, not Apache-2.0`,
        });
      }
      continue;
    }
    if (path.endsWith('package.json')) {
      if ((JSON.parse(text) as { license?: string }).license !== 'Apache-2.0') {
        findings.push({
          check: 'spdx',
          location: path,
          message: 'package.json license is not Apache-2.0',
        });
      }
      continue;
    }
    const head = text.split('\n').slice(0, 10).join('\n');
    if (!head.includes(HEADER)) {
      findings.push({
        check: 'spdx',
        location: path,
        message: `no "${HEADER}" in the first 10 lines`,
      });
    }
  }
  return findings;
}

/** The SPDX check over the files on disk. */
export function spdxFindingsOnDisk(root: string = contractRoot): Finding[] {
  const files = listFiles(root).map((path) => ({
    path,
    text: readFileSync(join(root, path), 'utf8'),
  }));
  const reuse = parseReuse(readFileSync(resolve(root, '..', 'REUSE.toml'), 'utf8'));
  return spdxFindings(files, reuse);
}
