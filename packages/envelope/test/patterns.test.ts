// SPDX-License-Identifier: FSL-1.1-ALv2
// TC-AE-038: every contract pattern finishes on its worst-case input (NP-06;
// NFR-AE-01, 02; T-AE-01). Ajv runs on V8's default RegExp. U1's pattern
// check (D-CG-05) is the CI gate that proves each pattern linear; this test
// times each one against crafted worst cases, with a generous fixed limit of
// 100 ms: catastrophic backtracking takes seconds, so it is caught without
// timing flakiness.
//
// The patterns are found by walking the contract's schemas and OpenAPI
// documents, not listed by hand, so a pattern added later is picked up.
// For each, the worst cases are: a repeated unit at the pattern's maximum
// length, then a character that fails the match at the end. The units are
// every printable ASCII character, and each pair of the pattern's own literal
// characters with a letter or digit, which drives a group under a quantifier.
import { readdirSync, readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { dirname, join } from 'node:path';
import { performance } from 'node:perf_hooks';
import { describe, expect, it } from 'vitest';
import { parse as parseYaml } from 'yaml';

const LIMIT_MS = 100;
const DEFAULT_MAX = 1024;

const require = createRequire(import.meta.url);
const root = dirname(require.resolve('@soorma/contract/envelope.schema.json'));

interface Found {
  where: string;
  pattern: string;
  maxLength: number;
}

function documents(): [string, unknown][] {
  const out: [string, unknown][] = [];
  for (const dir of ['', 'conventions'])
    for (const f of readdirSync(join(root, dir))) {
      const path = join(root, dir, f);
      if (f.endsWith('.schema.json'))
        out.push([join(dir, f), JSON.parse(readFileSync(path, 'utf8'))]);
      else if (f.endsWith('.openapi.yaml'))
        out.push([join(dir, f), parseYaml(readFileSync(path, 'utf8'))]);
    }
  return out;
}

function patterns(): Found[] {
  const found: Found[] = [];
  for (const [file, doc] of documents()) {
    const pending: [string, unknown][] = [[file, doc]];
    while (pending.length > 0) {
      const [where, node] = pending.pop()!;
      if (typeof node !== 'object' || node === null) continue;
      const n = node as Record<string, unknown>;
      if (typeof n.pattern === 'string')
        found.push({
          where,
          pattern: n.pattern,
          maxLength: typeof n.maxLength === 'number' ? n.maxLength : DEFAULT_MAX,
        });
      for (const [k, v] of Object.entries(n)) pending.push([`${where}/${k}`, v]);
    }
  }
  return found;
}

function units(pattern: string): string[] {
  const printable = Array.from({ length: 95 }, (_, i) => String.fromCharCode(32 + i));
  const literals = [...new Set(pattern.replace(/\\./g, '').split(''))].filter((c) =>
    /[!-~]/.test(c),
  );
  const pairs = literals.flatMap((c) => ['a', '0', 'f'].flatMap((x) => [`${x}${c}`, `${c}${x}`]));
  return [...printable, ...pairs, 'a=b,', 'a=b ,', '00-', 'aa.'];
}

const found = patterns();

describe('TC-AE-038: every contract pattern, timed on its worst cases', () => {
  it('finds the patterns by walking the contract', () => {
    expect(found.length).toBeGreaterThanOrEqual(10);
    expect(found.some((f) => f.where.includes('DraftTraceContext'))).toBe(true);
  });

  it.each(found.map((f) => [`${f.where} (max ${f.maxLength})`, f] as const))('%s', (_, f) => {
    const re = new RegExp(f.pattern, 'u');
    let slowest = 0;
    for (const unit of units(f.pattern))
      for (const tail of ['\u0000', '!', ' ', 'é']) {
        const body = unit.repeat(Math.ceil(f.maxLength / unit.length)).slice(0, f.maxLength - 1);
        const input = body + tail;
        const start = performance.now();
        re.test(input);
        slowest = Math.max(slowest, performance.now() - start);
      }
    expect(slowest).toBeLessThan(LIMIT_MS);
  });
});
