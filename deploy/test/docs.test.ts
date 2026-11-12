// SPDX-License-Identifier: FSL-1.1-ALv2
//
// The operations notes (U4 Infrastructure Design §10; TC-EHA-081): S1's
// signing-key rotation keeps "wait at least 5 minutes" at its step 2, with the
// reason, so the note cannot drift silently from S2's 5-minute verify-key
// refresh (NFR-EHA-08). S2's README keeps its three operations sections, and
// U5's backup and restore section (TC-AR-055).
import { readFileSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

const root = resolve(import.meta.dirname, '../..');
const read = (path: string): string => readFileSync(join(root, path), 'utf8');

/** The text of a `###` section, up to the next heading of level 2 or 3. */
function section(markdown: string, heading: string): string | undefined {
  const lines = markdown.split('\n');
  const start = lines.findIndex((l) => l.trim() === `### ${heading}`);
  if (start < 0) return undefined;
  const end = lines.findIndex((l, i) => i > start && /^#{2,3} /.test(l));
  return lines.slice(start + 1, end < 0 ? undefined : end).join('\n');
}

/** A numbered list's items, each joined into one line. */
function steps(text: string): string[] {
  return text
    .split(/\n(?=\d+\. )/)
    .filter((s) => /^\d+\. /.test(s.trimStart()))
    .map((s) => s.replace(/\s+/g, ' ').trim());
}

describe("TC-EHA-081: S1's README says wait at least 5 minutes in its rotation steps", () => {
  const readme = read('services/org-gateway/README.md');

  it('has the Operations section, with the rotation and internal-caller notes', () => {
    expect(readme).toMatch(/^## Operations$/m);
    expect(section(readme, 'Rotating the signing key')).toBeDefined();
    expect(section(readme, 'Internal callers')).toBeDefined();
  });

  it('says "wait at least 5 minutes" at step 2, and why', () => {
    const rotation = section(readme, 'Rotating the signing key') ?? '';
    const [, second] = steps(rotation.slice(rotation.search(/^1\. /m)));
    expect(second).toMatch(/^2\. /);
    expect(second?.toLowerCase()).toContain('wait at least 5 minutes');
    expect(rotation).toMatch(
      /\*\*Why at least 5 minutes:\*\*[^]*refreshes S1's verify keys every 5 minutes/,
    );
  });
});

describe("S2's README keeps its operations notes", () => {
  const readme = read('services/control-gateway/README.md');

  it('has its three Operations sections', () => {
    expect(readme).toMatch(/^## Operations$/m);
    for (const heading of [
      "Rotating E's minting key",
      "Rotating E's caller key",
      'When the organization level is down',
    ])
      expect(section(readme, heading), heading).toBeDefined();
  });
});

describe("TC-AR-055: S2's README documents backup and restore (U5 NFR-AR-09)", () => {
  const readme = read('services/control-gateway/README.md');
  const text = section(readme, "Backing up and restoring the environment's store") ?? '';

  it('has the section, with both commands', () => {
    expect(text.length).toBeGreaterThan(0);
    expect(text).toContain('pnpm stack:backup e');
    expect(text).toContain('pnpm stack:restore e <file>');
  });

  it('says the dump contains human identifiers, where it goes, its mode, and never the repository', () => {
    const flat = text.replace(/\s+/g, ' ');
    expect(flat).toContain('A dump contains human identifiers');
    expect(flat).toContain('deploy/local/.backups/');
    expect(flat).toContain('git-ignored');
    expect(flat).toContain('mode `0600`');
    expect(flat).toContain('It never goes into the repository');
  });

  it('names how the password arrives, and the archive check', () => {
    const flat = text.replace(/\s+/g, ' ');
    expect(flat).toContain('PGPASSFILE');
    expect(flat).toContain('verify-full');
    expect(flat).toContain('`PGDMP`');
    expect(flat).toContain('pg_restore --file=/dev/null');
  });
});
