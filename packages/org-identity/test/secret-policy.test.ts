// SPDX-License-Identifier: FSL-1.1-ALv2
// The K policy and the breached list: TC-OI-012, 013, 042 (the policy), 058.
import { createHash } from 'node:crypto';
import { cpSync, mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { afterAll, describe, expect, it } from 'vitest';
import {
  asSecretText,
  BreachedList,
  BreachedListError,
  breachedPrefix,
  SecretPolicy,
  type PolicyContext,
} from '../src/index.ts';

const dataDir = resolve(import.meta.dirname, '../../../data/breached');
const list = BreachedList.load(dataDir);
const policy = new SecretPolicy(list);
const context: PolicyContext = {
  reference: { organization: 'o1', principal: 'h@example.com' },
  replaces: asSecretText('the current passphrase'),
};
const check = (k: string, c: PolicyContext = context) => policy.check(asSecretText(k), c);

const scratch: string[] = [];
afterAll(() => {
  for (const d of scratch) rmSync(d, { recursive: true, force: true });
});

describe('TC-OI-042: the K policy normalizes, measures, and rejects as specified', () => {
  it('accepts 256 code points after NFKC, and refuses 257 as too_long', () => {
    expect(check('𝒶'.repeat(256))).toEqual({ accepted: true, secret: 'a'.repeat(256) });
    expect(check('lantern-'.repeat(32) + 'x')).toEqual({ accepted: false, reason: 'too_long' });
  });

  it('measures after NFKC: 7 code points once normalized is too_short', () => {
    // 8 code points raw; NFKC composes e + U+0301 into é, leaving 7.
    const decomposed = 'cafe\u0301zzq';
    expect([...decomposed].length).toBe(8);
    expect(check(decomposed)).toEqual({ accepted: false, reason: 'too_short' });
    expect(check('lantern')).toEqual({ accepted: false, reason: 'too_short' });
  });

  it('refuses a control character as disallowed_character', () => {
    expect(check('garden\u0007lantern')).toEqual({
      accepted: false,
      reason: 'disallowed_character',
    });
    expect(check('garden\nlantern')).toEqual({ accepted: false, reason: 'disallowed_character' });
  });

  it('refuses context words, case-folded, but not identifiers under 4 characters', () => {
    expect(check('xH@EXAMPLE.COMx')).toEqual({ accepted: false, reason: 'context_word' });
    expect(check('my-SOORMA-lantern')).toEqual({ accepted: false, reason: 'context_word' });
    expect(check('o1-garden-lantern').accepted).toBe(true);
    const longOrg = { ...context, reference: { organization: 'acme', principal: 'h@x.io' } };
    expect(check('ACMEgarden-lantern', longOrg)).toEqual({
      accepted: false,
      reason: 'context_word',
    });
  });

  it('refuses a listed password as breached (TC-OI-012, 013)', () => {
    expect(check('password')).toEqual({ accepted: false, reason: 'breached' });
    expect(check('12345678')).toEqual({ accepted: false, reason: 'breached' });
    expect(check('1234567')).toEqual({ accepted: false, reason: 'too_short' });
  });

  it('refuses the material it replaces as reused, compared on the NFKC form', () => {
    expect(check('the current passphrase')).toEqual({ accepted: false, reason: 'reused' });
    const composed = { ...context, replaces: asSecretText('café lantern garden') };
    expect(check('café lantern garden', composed)).toEqual({ accepted: false, reason: 'reused' });
  });

  it('imposes no composition rule', () => {
    expect(check('purple garden lantern').accepted).toBe(true);
  });
});

describe('TC-OI-058: the breached-list artifact matches its manifest', () => {
  it('loads the committed list: about a million sorted prefixes', () => {
    expect(list.size).toBe(999_996);
    expect(list.has(asSecretText('123456'))).toBe(true);
    expect(list.has(asSecretText('purple garden lantern'))).toBe(false);
  });

  function copy(): string {
    const dir = mkdtempSync(join(tmpdir(), 'soorma-breached-'));
    scratch.push(dir);
    cpSync(dataDir, dir, { recursive: true });
    return dir;
  }

  it('refuses a file whose SHA-256 differs from the manifest', () => {
    const dir = copy();
    const bin = join(dir, 'top-1m.sha256-64.bin');
    const bytes = Buffer.alloc(16);
    bytes.writeBigUInt64BE(1n, 0);
    bytes.writeBigUInt64BE(2n, 8);
    writeFileSync(bin, bytes);
    expect(() => BreachedList.load(dir)).toThrow(BreachedListError);
  });

  it('refuses a manifest without a digest, and prefixes that are not sorted and distinct', () => {
    const dir = copy();
    writeFileSync(join(dir, 'MANIFEST.md'), '# nothing');
    expect(() => BreachedList.load(dir)).toThrow('records no derived SHA-256');
    const unsorted = Buffer.alloc(16);
    unsorted.writeBigUInt64BE(2n, 0);
    unsorted.writeBigUInt64BE(1n, 8);
    expect(() => BreachedList.fromPrefixes(unsorted)).toThrow('not sorted and distinct');
    expect(() => BreachedList.fromPrefixes(Buffer.alloc(7))).toThrow('64-bit prefixes');
  });

  it('hashes NFKC, then SHA-256, then the first 64 bits, as the derivation does', () => {
    const expected = createHash('sha256').update('a').digest().readBigUInt64BE(0);
    expect(breachedPrefix('ａ')).toBe(expected);
  });
});
