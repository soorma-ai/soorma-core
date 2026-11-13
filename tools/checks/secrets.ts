// SPDX-License-Identifier: FSL-1.1-ALv2
//
// The secret-pattern check (D-ID-OI-07, 09; M1-NFR-09): no enrollment
// material, sign-in token, or private key in the repository, or in a built
// image's file system.
//
//   node tools/checks/run.ts secrets                   the tracked files
//   node tools/checks/run.ts secrets --image <ref>     an image's exported file system
//                                                      (one export, one pass: image-scan.ts)
//
// Patterns are shaped like the real thing (full length), so a placeholder in
// a test (`soorma_em_x`) does not match. Labelled test fixtures are listed in
// FIXTURE_PATHS; deploy/local/.secrets/ is git-ignored and never tracked.
import { execFileSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { walkTar } from './tar.ts';
import { repoRoot, type Finding } from './workspace.ts';

export const SECRET_PATTERNS: readonly { name: string; pattern: RegExp }[] = [
  { name: 'enrollment material', pattern: /soorma_em_[A-Za-z0-9_-]{40,}/ },
  {
    name: 'a sign-in token',
    pattern: /soorma_si_[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{40,}/,
  },
  {
    // A header alone (as in PEM-parsing code) is not a key: the base64 body
    // and the END line must follow.
    name: 'a private key',
    pattern:
      /-----BEGIN (?:[A-Z]+ )?PRIVATE KEY-----\s+[A-Za-z0-9+/=\s]{64,}-----END (?:[A-Z]+ )?PRIVATE KEY-----/,
  },
  // U6 (NP-AC-12; D-CG-AC-12): an agent credential, shaped as the sign-in
  // token, and a registration secret, exactly its shape (U5 NFR-AR-01).
  {
    name: 'an agent credential',
    pattern: /soorma_ac_[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{40,}/,
  },
  { name: 'a registration secret', pattern: /soorma_rs_[A-Za-z0-9_-]{22}\.[A-Za-z0-9_-]{43}/ },
];

/** Tracked files that hold labelled, non-working test values. */
export const FIXTURE_PATHS: readonly RegExp[] = [/^contract\/fixtures\//];

export function textFindings(path: string, text: string): Finding[] {
  return SECRET_PATTERNS.filter((p) => p.pattern.test(text)).map((p) => ({
    check: 'secrets',
    location: path,
    message: `holds ${p.name}`,
  }));
}

export function repositoryFindings(root: string = repoRoot): Finding[] {
  const files = execFileSync('git', ['ls-files', '-z'], { cwd: root, encoding: 'utf8' })
    .split('\0')
    .filter((f) => f.length > 0 && !FIXTURE_PATHS.some((p) => p.test(f)));
  return files.flatMap((f) => {
    let text: string;
    try {
      text = readFileSync(join(root, f)).toString('latin1');
    } catch {
      return [];
    }
    return textFindings(f, text);
  });
}

/**
 * Scans a tar stream (an exported container file system): each regular
 * file's content, by its path in the archive. Files over 16 MiB are skipped.
 */
export async function tarFindings(stream: AsyncIterable<Buffer>): Promise<Finding[]> {
  const findings: Finding[] = [];
  await walkTar(stream, (file) => {
    if (file.content) findings.push(...textFindings(file.name, file.content.toString('latin1')));
  });
  return findings;
}
