// SPDX-License-Identifier: FSL-1.1-ALv2
//
// The secret-pattern check (D-ID-OI-07, 09; M1-NFR-09): no enrollment
// material, sign-in token, or private key in the repository, or in a built
// image's file system.
//
//   node tools/checks/run.ts secrets                   the tracked files
//   node tools/checks/run.ts secrets --image <ref>     an image's exported file system
//
// Patterns are shaped like the real thing (full length), so a placeholder in
// a test (`soorma_em_x`) does not match. Labelled test fixtures are listed in
// FIXTURE_PATHS; deploy/local/.secrets/ is git-ignored and never tracked.
import { execFileSync, spawn } from 'node:child_process';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
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
  let buffer = Buffer.alloc(0);
  let pending: { name: string; size: number; skip: boolean } | undefined;
  let longName: string | undefined;
  const take = (n: number): Buffer => {
    const out = buffer.subarray(0, n);
    buffer = buffer.subarray(n);
    return out;
  };
  for await (const chunk of stream) {
    buffer = Buffer.concat([buffer, chunk]);
    for (;;) {
      if (!pending) {
        if (buffer.length < 512) break;
        const header = take(512);
        if (header.every((b) => b === 0)) continue;
        const field = (start: number, length: number): string =>
          header
            .subarray(start, start + length)
            .toString('utf8')
            .replace(/\0.*$/s, '');
        const prefix = field(345, 155);
        const name = longName ?? (prefix ? `${prefix}/${field(0, 100)}` : field(0, 100));
        longName = undefined;
        const size = parseInt(field(124, 12).trim() || '0', 8);
        const type = field(156, 1);
        pending = {
          name,
          size,
          skip: (type !== '0' && type !== '' && type !== 'L') || size > 16 * 2 ** 20,
        };
        if (type === 'L') pending = { name: '\0longname', size, skip: false };
      }
      const padded = Math.ceil(pending.size / 512) * 512;
      if (buffer.length < padded) break;
      const content = take(padded).subarray(0, pending.size);
      if (pending.name === '\0longname') longName = content.toString('utf8').replace(/\0.*$/s, '');
      else if (!pending.skip)
        findings.push(...textFindings(pending.name, content.toString('latin1')));
      pending = undefined;
    }
  }
  return findings;
}

export async function imageFindings(image: string): Promise<Finding[]> {
  const id = execFileSync('docker', ['create', image], { encoding: 'utf8' }).trim();
  try {
    const exported = spawn('docker', ['export', id], { stdio: ['ignore', 'pipe', 'inherit'] });
    const findings = await tarFindings(exported.stdout as AsyncIterable<Buffer>);
    return findings.map((f) => ({ ...f, location: `${image}:/${f.location}` }));
  } finally {
    execFileSync('docker', ['rm', id], { stdio: 'ignore' });
  }
}
