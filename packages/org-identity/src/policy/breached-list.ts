// SPDX-License-Identifier: FSL-1.1-ALv2
//
// The breached-secret list (BR-K-05; NFR-OI-13): SecLists' top 1,000,000
// passwords, held locally as a pinned derived artifact. Each entry is
// NFKC-normalized, hashed with SHA-256, and truncated to its first 64 bits;
// the prefixes are sorted and stored big-endian, 8 bytes each. Neither K nor
// any hash of it leaves the process.
//
// The file is loaded once, and its SHA-256 is checked against MANIFEST.md
// before it is used: a mismatch stops start-up.
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import type { SecretText } from '@soorma/service-kit';

export const BREACHED_FILE = 'top-1m.sha256-64.bin';
export const BREACHED_MANIFEST = 'MANIFEST.md';
const PREFIX_BYTES = 8;

export class BreachedListError extends Error {
  constructor(reason: string) {
    super(`the breached list cannot be used: ${reason}`);
    this.name = 'BreachedListError';
  }
}

/** The 64-bit prefix of SHA-256 over the NFKC form, as a big-endian integer. */
export function breachedPrefix(value: string): bigint {
  return createHash('sha256').update(value.normalize('NFKC'), 'utf8').digest().readBigUInt64BE(0);
}

/** The derived file's SHA-256, as MANIFEST.md records it. */
export function manifestDigest(manifest: string): string | undefined {
  return /^\| Derived file SHA-256 \| `([0-9a-f]{64})` \|$/m.exec(manifest)?.[1];
}

export class BreachedList {
  private readonly prefixes: Buffer;
  readonly size: number;

  private constructor(prefixes: Buffer) {
    this.prefixes = prefixes;
    this.size = prefixes.length / PREFIX_BYTES;
  }

  /** Loads `dir`/top-1m.sha256-64.bin, refusing it unless its digest matches the manifest. */
  static load(dir: string): BreachedList {
    let bytes: Buffer;
    let manifest: string;
    try {
      bytes = readFileSync(join(dir, BREACHED_FILE));
      manifest = readFileSync(join(dir, BREACHED_MANIFEST), 'utf8');
    } catch {
      throw new BreachedListError(`${BREACHED_FILE} or ${BREACHED_MANIFEST} cannot be read`);
    }
    const expected = manifestDigest(manifest);
    if (!expected) throw new BreachedListError('the manifest records no derived SHA-256');
    if (createHash('sha256').update(bytes).digest('hex') !== expected)
      throw new BreachedListError('its SHA-256 does not match the manifest');
    return BreachedList.fromPrefixes(bytes);
  }

  /** From sorted, distinct prefixes; refuses anything else. */
  static fromPrefixes(bytes: Buffer): BreachedList {
    if (bytes.length === 0 || bytes.length % PREFIX_BYTES !== 0)
      throw new BreachedListError('its length is not a whole number of 64-bit prefixes');
    for (let i = PREFIX_BYTES; i < bytes.length; i += PREFIX_BYTES) {
      if (bytes.readBigUInt64BE(i - PREFIX_BYTES) >= bytes.readBigUInt64BE(i))
        throw new BreachedListError('its prefixes are not sorted and distinct');
    }
    return new BreachedList(bytes);
  }

  /** True when the secret's NFKC form is on the list (a binary search over the prefixes). */
  has(secret: SecretText): boolean {
    const target = breachedPrefix(secret);
    let low = 0;
    let high = this.size - 1;
    while (low <= high) {
      const mid = (low + high) >>> 1;
      const value = this.prefixes.readBigUInt64BE(mid * PREFIX_BYTES);
      if (value === target) return true;
      if (value < target) low = mid + 1;
      else high = mid - 1;
    }
    return false;
  }
}
