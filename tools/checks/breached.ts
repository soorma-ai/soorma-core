// SPDX-License-Identifier: FSL-1.1-ALv2
//
// NFR-OI-13: the committed breached-secret list matches its manifest, and is
// well formed: a whole number of 64-bit prefixes, sorted and distinct.
import { createHash } from 'node:crypto';
import type { Finding } from './workspace.ts';

export const BREACHED_PATH = 'data/breached/top-1m.sha256-64.bin';
export const MANIFEST_PATH = 'data/breached/MANIFEST.md';

export function breachedFindings(derived: Buffer, manifest: string): Finding[] {
  const findings: Finding[] = [];
  const add = (location: string, message: string): void => {
    findings.push({ check: 'breached', location, message });
  };
  const recorded = /^\| Derived file SHA-256 \| `([0-9a-f]{64})` \|$/m.exec(manifest)?.[1];
  if (!recorded) add(MANIFEST_PATH, 'records no derived file SHA-256');
  else if (createHash('sha256').update(derived).digest('hex') !== recorded)
    add(BREACHED_PATH, 'its SHA-256 differs from the manifest');
  if (derived.length === 0 || derived.length % 8 !== 0) {
    add(BREACHED_PATH, 'its length is not a whole number of 64-bit prefixes');
    return findings;
  }
  for (let i = 8; i < derived.length; i += 8) {
    if (derived.readBigUInt64BE(i - 8) >= derived.readBigUInt64BE(i)) {
      add(BREACHED_PATH, `prefixes are not sorted and distinct at index ${i / 8}`);
      break;
    }
  }
  return findings;
}
