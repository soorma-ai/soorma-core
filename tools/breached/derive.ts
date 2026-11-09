// SPDX-License-Identifier: FSL-1.1-ALv2
//
// Derives the breached-secret list (NFR-OI-13; D-CG-OI-09, Q-CG-3 B):
//
//   node tools/breached/derive.ts
//
// Fetches the pinned SecLists file and its LICENSE at the pinned commit,
// refuses a licence other than MIT, and writes data/breached/top-1m.sha256-64.bin
// (each entry NFKC-normalized, SHA-256, first 64 bits, sorted, distinct,
// big-endian) and data/breached/MANIFEST.md. The source is never committed.
// `pnpm run check:breached` checks the committed file against the manifest.
import { createHash } from 'node:crypto';
import { mkdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { repoRoot } from '../checks/workspace.ts';

export const SOURCE = {
  repository: 'https://github.com/danielmiessler/SecLists',
  commit: '00f80ec9cc39bed63ee40cf6805a6b1b77e87644',
  commitDate: '2026-10-31',
  path: 'Passwords/Common-Credentials/xato-net-10-million-passwords-1000000.txt',
  unchangedSince: 'c205c36a445bff37f8e58a9ec829105cd4975c58',
  unchangedSinceDate: '2025-05-08',
} as const;

export const DATA_DIR = join(repoRoot, 'data', 'breached');

function raw(path: string): string {
  return `https://raw.githubusercontent.com/danielmiessler/SecLists/${SOURCE.commit}/${path}`;
}

/** The entries: one per line, CR stripped, empty lines skipped, each NFKC-normalized. */
export function entries(source: string): string[] {
  return source
    .split('\n')
    .map((line) => line.replace(/\r$/, ''))
    .filter((line) => line.length > 0)
    .map((line) => line.normalize('NFKC'));
}

/** The derived bytes: distinct 64-bit SHA-256 prefixes, sorted, big-endian. */
export function derive(source: string): Buffer {
  const prefixes = new BigUint64Array(
    [
      ...new Set(
        entries(source).map((e) =>
          createHash('sha256').update(e, 'utf8').digest().readBigUInt64BE(0),
        ),
      ),
    ].sort((a, b) => (a < b ? -1 : a > b ? 1 : 0)),
  );
  const out = Buffer.alloc(prefixes.length * 8);
  prefixes.forEach((p, i) => out.writeBigUInt64BE(p, i * 8));
  return out;
}

const sha256 = (bytes: Buffer | string): string => createHash('sha256').update(bytes).digest('hex');

export function manifest(source: Buffer, derived: Buffer, licenceLine: string): string {
  const text = source.toString('utf8');
  const lines = entries(text);
  return `<!-- SPDX-License-Identifier: FSL-1.1-ALv2 -->

# Breached-Secret List

The list K is checked against (BR-K-05; NFR-OI-13). Derived by
\`node tools/breached/derive.ts\` from the pinned source below, which is never committed.
\`pnpm run check:breached\` checks the derived file's SHA-256 against this manifest, and S1
refuses to start if it differs.

| Field | Value |
| --- | --- |
| Source repository | ${SOURCE.repository} |
| Pinned commit | \`${SOURCE.commit}\` (${SOURCE.commitDate}) |
| Path | \`${SOURCE.path}\` |
| Unchanged since | \`${SOURCE.unchangedSince}\` (${SOURCE.unchangedSinceDate}), the file's only commit, which moved it into \`Common-Credentials\`. SecLists removed \`10-million-password-list-top-1000000.txt\` as its duplicate (\`4ff3ff8\`) |
| Licence | MIT (${licenceLine}), checked at the pinned commit |
| Source SHA-256 | \`${sha256(source)}\` |
| Source size | ${source.length} bytes; ${lines.length} non-empty lines; ${new Set(lines).size} distinct entries after NFKC |
| Derivation | Each entry NFKC-normalized, hashed with SHA-256 over its UTF-8, truncated to the first 64 bits; distinct values sorted ascending; written big-endian, 8 bytes each |
| Derived file | \`top-1m.sha256-64.bin\` (${derived.length / 8} prefixes, ${derived.length} bytes) |
| Derived file SHA-256 | \`${sha256(derived)}\` |
`;
}

async function fetchBytes(url: string): Promise<Buffer> {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`${url}: HTTP ${response.status}`);
  return Buffer.from(await response.arrayBuffer());
}

async function main(): Promise<void> {
  const licence = (await fetchBytes(raw('LICENSE'))).toString('utf8');
  const lines = licence.split('\n').map((l) => l.trim());
  if (lines[0] !== 'MIT License') throw new Error('SecLists is not MIT at the pinned commit');
  const copyright = lines.find((l) => l.startsWith('Copyright')) ?? 'no copyright line';
  const source = await fetchBytes(raw(SOURCE.path));
  const derived = derive(source.toString('utf8'));
  mkdirSync(DATA_DIR, { recursive: true });
  writeFileSync(join(DATA_DIR, 'top-1m.sha256-64.bin'), derived);
  writeFileSync(join(DATA_DIR, 'MANIFEST.md'), manifest(source, derived, copyright));
  console.log(`Wrote data/breached/ (${derived.length / 8} prefixes)`);
}

if (import.meta.main) {
  main().catch((error: unknown) => {
    console.error(error);
    process.exitCode = 1;
  });
}
