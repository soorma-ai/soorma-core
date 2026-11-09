// SPDX-License-Identifier: FSL-1.1-ALv2
// The breached-list derivation and its check: TC-OI-058; NFR-OI-13.
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';
import { breachedFindings, BREACHED_PATH, MANIFEST_PATH } from '../checks/breached.ts';
import { derive, entries, manifest, SOURCE } from '../breached/derive.ts';
import { repoRoot } from '../checks/workspace.ts';

const derived = readFileSync(join(repoRoot, BREACHED_PATH));
const committedManifest = readFileSync(join(repoRoot, MANIFEST_PATH), 'utf8');

describe('TC-OI-058: the breached-list artifact matches its manifest', () => {
  it('the committed file passes the check', () => {
    expect(breachedFindings(derived, committedManifest)).toEqual([]);
  });

  it('records the pinned source, the path, its digest, and that it is unchanged since c205c36', () => {
    expect(SOURCE.commit).toBe('00f80ec9cc39bed63ee40cf6805a6b1b77e87644');
    expect(committedManifest).toContain(`| Pinned commit | \`${SOURCE.commit}\``);
    expect(committedManifest).toContain(
      '| Path | `Passwords/Common-Credentials/xato-net-10-million-passwords-1000000.txt` |',
    );
    expect(committedManifest).toMatch(/^\| Source SHA-256 \| `[0-9a-f]{64}` \|$/m);
    expect(committedManifest).toContain(
      '| Unchanged since | `c205c36a445bff37f8e58a9ec829105cd4975c58`',
    );
    expect(committedManifest).toContain('| Licence | MIT (');
  });

  it('fails on a changed byte, a missing digest, and unsorted prefixes', () => {
    const changed = Buffer.from(derived);
    changed[0] = changed[0]! ^ 1;
    expect(breachedFindings(changed, committedManifest).map((f) => f.message)).toContain(
      'its SHA-256 differs from the manifest',
    );
    expect(breachedFindings(derived, '# none').map((f) => f.message)).toEqual([
      'records no derived file SHA-256',
    ]);
    const unsorted = Buffer.alloc(16);
    unsorted.writeBigUInt64BE(5n, 0);
    unsorted.writeBigUInt64BE(4n, 8);
    expect(breachedFindings(unsorted, '# none').map((f) => f.message)).toContain(
      'prefixes are not sorted and distinct at index 1',
    );
  });

  it('derives NFKC, SHA-256, 64-bit, sorted, distinct prefixes; deterministically', () => {
    const source = 'b\r\na\n\nａ\nb\n';
    expect(entries(source)).toEqual(['b', 'a', 'a', 'b']);
    const out = derive(source);
    expect(out).toHaveLength(16);
    expect(out.readBigUInt64BE(0) < out.readBigUInt64BE(8)).toBe(true);
    expect(derive(source).equals(out)).toBe(true);
    const text = manifest(Buffer.from(source), out, 'Copyright (c) 2018 Daniel Miessler');
    expect(breachedFindings(out, text)).toEqual([]);
  });
});
