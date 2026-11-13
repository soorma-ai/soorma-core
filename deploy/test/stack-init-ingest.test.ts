// SPDX-License-Identifier: FSL-1.1-ALv2
//
// TC-ET-084 (U7 D-ID-ET-03, 04, 05): `stack:init` writes each environment's
// S4 secrets beside U4's and U6's (their tests unchanged): the seal key
// (base64url, 256 bits), the ingest role's password, and S4's TLS leaf; 0600,
// distinct per environment, and never overwritten.
import { execFileSync } from 'node:child_process';
import { mkdtempSync, readFileSync, rmSync, statSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { afterAll, describe, expect, it } from 'vitest';
import { stackInit } from '../local/scripts/stack-init.ts';

const dirs: string[] = [];
afterAll(() => {
  for (const d of dirs) rmSync(d, { recursive: true, force: true });
});

const U7_SECRETS = (env: string): string[] => [
  `${env}-seal-key-1`,
  `${env}-db-ingest-password`,
  `${env}-event-ingest-tls`,
];

describe('TC-ET-084: stack:init writes each environment’s seal key, never overwriting it', () => {
  it('256 bits of base64url each, distinct per environment, 0600; a second run keeps them', () => {
    const dir = mkdtempSync(join(tmpdir(), 'soorma-stack-'));
    dirs.push(dir);
    const first = stackInit({ dir });
    const all = [...U7_SECRETS('e'), ...U7_SECRETS('e2')];
    expect(first.created).toEqual(expect.arrayContaining(all));
    for (const name of all) expect(statSync(join(dir, name)).mode & 0o777, name).toBe(0o600);
    for (const env of ['e', 'e2']) {
      for (const name of [`${env}-seal-key-1`, `${env}-db-ingest-password`]) {
        const text = readFileSync(join(dir, name), 'utf8').trim();
        expect(text, name).toMatch(/^[A-Za-z0-9_-]{43}$/);
        expect(Buffer.from(text, 'base64url').length, name).toBe(32);
      }
    }
    for (const name of ['seal-key-1', 'db-ingest-password'])
      expect(readFileSync(join(dir, `e-${name}`), 'utf8'), name).not.toBe(
        readFileSync(join(dir, `e2-${name}`), 'utf8'),
      );
    const before = Object.fromEntries(all.map((n) => [n, readFileSync(join(dir, n), 'utf8')]));
    const second = stackInit({ dir });
    expect(second.created).toEqual([]);
    for (const name of all) expect(readFileSync(join(dir, name), 'utf8'), name).toBe(before[name]);
  });

  it('S4’s TLS leaf names its own environment’s host', () => {
    const dir = mkdtempSync(join(tmpdir(), 'soorma-stack-'));
    dirs.push(dir);
    stackInit({ dir });
    for (const env of ['e', 'e2']) {
      const pem = readFileSync(join(dir, `${env}-event-ingest-tls`), 'utf8');
      const cert = pem.slice(pem.indexOf('-----BEGIN CERTIFICATE-----'));
      const text = execFileSync('openssl', ['x509', '-noout', '-ext', 'subjectAltName'], {
        input: cert,
        encoding: 'utf8',
      });
      expect(text).toContain(`DNS:event-ingest.${env}.soorma.internal`);
    }
  });
});
