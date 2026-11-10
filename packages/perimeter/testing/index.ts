// SPDX-License-Identifier: FSL-1.1-ALv2
//
// @soorma/perimeter/testing: the shared Problem assertion (U3 BR-PE-06;
// D-AE-06; BR-ERR-08). Test-only by construction (D-CG-AE-03): this file is
// outside src/, so no build emits it, and its export carries only the
// `source` condition, so Vitest and the typecheck resolve it and Node cannot.
// Every edge runs it on every Problem it emits: S1 now; S2, S3, and S4 at U4,
// U6, and U7.
//
// It uses node:assert, so any test runner can call it, and validates the body
// against the contract's own `Problem` schema.
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { Ajv2020, type ValidateFunction } from 'ajv/dist/2020.js';
import { parse as parseYaml } from 'yaml';
import {
  CONTRACT_VERSION,
  isProblemCode,
  PROBLEM_TABLE,
  SUPPORTED_VERSIONS,
} from '../src/index.ts';

/** A response as a test sees it: header names in any case. */
export interface ProblemUnderTest {
  readonly status: number;
  readonly headers: Readonly<Record<string, unknown>>;
  readonly body: unknown;
}

const require = createRequire(import.meta.url);
const COMPONENTS = 'https://soorma.ai/contract/conventions/components.openapi.yaml';

let problemSchema: ValidateFunction | undefined;

function toDefsRefs(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(toDefsRefs);
  if (typeof value !== 'object' || value === null) return value;
  const out: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(value))
    out[k] =
      k === '$ref' && typeof v === 'string'
        ? v.replace(/#\/components\/schemas\//, '#/$defs/')
        : toDefsRefs(v);
  return out;
}

/** The contract's `Problem` schema, compiled once (Ajv 2020, strict). */
function problemValidator(): ValidateFunction {
  if (problemSchema) return problemSchema;
  const path = require.resolve('@soorma/contract/conventions/components.openapi.yaml');
  const document = parseYaml(readFileSync(path, 'utf8')) as {
    components: { schemas: Record<string, unknown> };
  };
  const ajv = new Ajv2020({ strict: true, allErrors: true });
  ajv.addSchema({ $id: COMPONENTS, $defs: toDefsRefs(document.components.schemas) as object });
  const fn = ajv.getSchema(`${COMPONENTS}#/$defs/Problem`);
  if (!fn) throw new Error('the contract defines no Problem schema');
  problemSchema = fn;
  return fn;
}

function header(response: ProblemUnderTest, name: string): string | undefined {
  const wanted = name.toLowerCase();
  for (const [k, v] of Object.entries(response.headers)) {
    if (k.toLowerCase() !== wanted) continue;
    if (typeof v === 'string' || typeof v === 'number') return String(v);
    if (Array.isArray(v)) return v.map((x) => String(x as string)).join(', ');
  }
  return undefined;
}

/**
 * Asserts a Problem response meets BR-PE-02 and BR-PE-03: the status; the
 * Soorma headers; the content type; type, title, status, code, and instance
 * in the urn:soorma: forms, instance matching Soorma-Request-Id;
 * WWW-Authenticate exactly on a 401; Retry-After exactly on a 429 or 503;
 * supportedVersions on unsupported_contract_version; and the Problem schema.
 */
export function assertProblem(
  response: ProblemUnderTest,
  expected: { status: number; code: string },
): void {
  const { status, code } = expected;
  assert.equal(response.status, status, 'status');
  assert.equal(
    header(response, 'Soorma-Contract-Version'),
    CONTRACT_VERSION,
    'Soorma-Contract-Version',
  );
  const requestId = header(response, 'Soorma-Request-Id');
  assert.ok(requestId !== undefined && requestId.length > 0, 'Soorma-Request-Id is present');
  assert.equal(
    header(response, 'Content-Type'),
    'application/problem+json; charset=utf-8',
    'Content-Type',
  );

  const body = response.body as Record<string, unknown>;
  assert.equal(typeof body, 'object', 'the body is an object');
  assert.equal(body.type, `urn:soorma:problem:${code}`, 'type');
  assert.equal(body.code, code, 'code');
  assert.equal(body.status, status, 'body status');
  assert.ok(typeof body.title === 'string' && body.title.length > 0, 'title');
  if (isProblemCode(code)) {
    assert.equal(PROBLEM_TABLE[code].status, status, 'the status is the table status');
    assert.equal(body.title, PROBLEM_TABLE[code].title, 'the title is the table title');
  }
  assert.equal(body.instance, `urn:soorma:request:${String(requestId)}`, 'instance');

  if (status === 401)
    assert.equal(header(response, 'WWW-Authenticate'), 'Bearer', 'WWW-Authenticate');
  else assert.equal(header(response, 'WWW-Authenticate'), undefined, 'no WWW-Authenticate');
  const retryAfter = header(response, 'Retry-After');
  if (status === 429 || status === 503)
    assert.ok(retryAfter !== undefined && /^[1-9][0-9]*$/.test(retryAfter), 'Retry-After');
  else assert.equal(retryAfter, undefined, 'no Retry-After');

  if (code === 'unsupported_contract_version')
    assert.deepEqual(body.supportedVersions, [...SUPPORTED_VERSIONS], 'supportedVersions');

  const validate = problemValidator();
  assert.ok(validate(body), `the Problem schema: ${JSON.stringify(validate.errors)}`);
}
