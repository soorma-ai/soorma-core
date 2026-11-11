// SPDX-License-Identifier: FSL-1.1-ALv2
// P1's Problem table and emission: TC-AE-031 step 1; BR-PE-01 to 04, 06;
// D-AE-06, 25; BR-ERR-08; NFR-AE-21.
import { existsSync, readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { dirname, join } from 'node:path';
import { describe, expect, it } from 'vitest';
import { assertProblem } from '@soorma/perimeter/testing';
import {
  CONTRACT_VERSION,
  PROBLEM_TABLE,
  problemResponse,
  SUPPORTED_VERSIONS,
  type ProblemCode,
} from '../src/index.ts';

const require = createRequire(import.meta.url);

/** The code table in contract/conventions/errors.md: code to status. */
function conventionTable(): Map<string, number> {
  // errors.md is not a package export: it sits beside an exported convention.
  const components = require.resolve('@soorma/contract/conventions/components.openapi.yaml');
  const text = readFileSync(join(dirname(components), 'errors.md'), 'utf8');
  const rows = new Map<string, number>();
  for (const line of text.split('\n')) {
    const m = /^\| `([a-z_]+)`\s*\| (\d{3})\s*\|/.exec(line);
    if (m) rows.set(m[1]!, Number(m[2]));
  }
  return rows;
}

const codes = Object.keys(PROBLEM_TABLE) as ProblemCode[];

describe('BR-PE-01: P1 holds the one table, equal to the convention', () => {
  it('every code in errors.md, with its status, and nothing else', () => {
    const convention = conventionTable();
    expect(convention.size).toBeGreaterThanOrEqual(18);
    expect(new Map(codes.map((c) => [c, PROBLEM_TABLE[c].status]))).toEqual(convention);
  });

  it("includes U3's codes (business-rules §12)", () => {
    for (const code of [
      'unknown_field',
      'stamped_field_set',
      'invalid_inbound_context',
      'chain_too_deep',
      'envelope_too_large',
      'forbidden',
    ])
      expect(codes).toContain(code);
  });

  it('defines the contract version and the accepted set once (D-AE-25)', () => {
    expect(CONTRACT_VERSION).toBe('0.1.0');
    expect(SUPPORTED_VERSIONS).toEqual(['0.1.0']);
    expect(Object.isFrozen(SUPPORTED_VERSIONS)).toBe(true);
  });
});

describe('TC-AE-031 step 1: every code, emitted and asserted', () => {
  it.each(codes)('%s', (code) => {
    const response = problemResponse({ code }, 'r-1');
    expect(response.body.instance).toBe('urn:soorma:request:r-1');
    expect(response.body.type).toBe(`urn:soorma:problem:${code}`);
    assertProblem(response, { status: PROBLEM_TABLE[code].status, code });
  });

  it('carries field errors on a validation refusal, and Retry-After of 1 by default', () => {
    const r = problemResponse(
      { code: 'malformed_request', errors: [{ header: 'Soorma-Contract-Version' }] },
      'r-2',
    );
    expect(r.body.errors).toEqual([{ header: 'Soorma-Contract-Version' }]);
    expect(problemResponse({ code: 'unavailable' }, 'r-3').headers['Retry-After']).toBe('1');
    expect(
      problemResponse({ code: 'too_many_attempts', retryAfterSeconds: 42 }, 'r-4').headers[
        'Retry-After'
      ],
    ).toBe('42');
  });
});

describe('BR-PE-06: the shared assertion refuses a Problem that breaks the rules', () => {
  const good = problemResponse({ code: 'forbidden' }, 'r-5');
  const broken: [string, unknown][] = [
    ['a wrong instance', { ...good, body: { ...good.body, instance: 'urn:soorma:request:other' } }],
    ['a missing type', { ...good, body: { ...good.body, type: undefined } }],
    ['about:blank', { ...good, body: { ...good.body, type: 'about:blank' } }],
    [
      'a WWW-Authenticate on a 403',
      { ...good, headers: { ...good.headers, 'WWW-Authenticate': 'Bearer' } },
    ],
    [
      'no contract version',
      { ...good, headers: { ...good.headers, 'Soorma-Contract-Version': undefined } },
    ],
    [
      'a plain JSON content type',
      { ...good, headers: { ...good.headers, 'Content-Type': 'application/json' } },
    ],
    ['a non-integer status in the body', { ...good, body: { ...good.body, status: '403' } }],
  ];
  it.each(broken)('%s', (_, response) => {
    expect(() => assertProblem(response as never, { status: 403, code: 'forbidden' })).toThrow();
  });

  it('accepts header names in any case, as Fastify reports them', () => {
    const lower = Object.fromEntries(
      Object.entries(good.headers).map(([k, v]) => [k.toLowerCase(), v]),
    );
    assertProblem({ ...good, headers: lower }, { status: 403, code: 'forbidden' });
  });
});

describe('TC-AE-031 step 4: S1 emits through P1, so its own table is gone (BR-PE-05)', () => {
  it('services/org-gateway/src/problems.ts no longer exists', () => {
    const removed = new URL('../../../services/org-gateway/src/problems.ts', import.meta.url);
    expect(existsSync(removed)).toBe(false);
  });
});
