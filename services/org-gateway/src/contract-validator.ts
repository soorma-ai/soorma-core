// SPDX-License-Identifier: FSL-1.1-ALv2
//
// S1's request validation against the contract itself (NFR-OI-28): Ajv's
// JSON Schema 2020-12 build, strict, compiled once at start-up from
// @soorma/contract's documents, which ship in the image. The OpenAPI
// documents are loaded as JSON Schemas whose $defs are their
// components.schemas, as U1's own validator does.
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { Ajv2020, type ErrorObject, type ValidateFunction } from 'ajv/dist/2020.js';
import { parse as parseYaml } from 'yaml';
import type { FieldError } from './problems.ts';

const BASE = 'https://soorma.ai/contract/';
const require = createRequire(import.meta.url);

export type RequestSchema =
  'FirstAuthenticateRequest' | 'AuthenticateRequest' | 'ChangeMaterialRequest';

const MAX_ERRORS = 10;

function read(specifier: string): unknown {
  const path = require.resolve(`@soorma/contract/${specifier}`);
  const text = readFileSync(path, 'utf8');
  return specifier.endsWith('.json') ? (JSON.parse(text) as unknown) : (parseYaml(text) as unknown);
}

function toDefsRefs(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(toDefsRefs);
  if (typeof value !== 'object' || value === null) return value;
  const out: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(value)) {
    out[k] =
      k === '$ref' && typeof v === 'string'
        ? v.replace(/#\/components\/schemas\//, '#/$defs/')
        : toDefsRefs(v);
  }
  return out;
}

function schemasOf(document: unknown): unknown {
  const d = document as { components?: { schemas?: unknown } };
  return toDefsRefs(d.components?.schemas ?? {});
}

function escapePointer(segment: string): string {
  return segment.replace(/~/g, '~0').replace(/\//g, '~1');
}

function fieldErrors(errors: ErrorObject[]): FieldError[] {
  const out = new Map<string, FieldError>();
  for (const e of errors) {
    const params = e.params as { additionalProperty?: string; missingProperty?: string };
    const pointer =
      params.additionalProperty !== undefined
        ? `${e.instancePath}/${escapePointer(params.additionalProperty)}`
        : params.missingProperty !== undefined
          ? `${e.instancePath}/${escapePointer(params.missingProperty)}`
          : e.instancePath;
    if (!out.has(pointer)) out.set(pointer, { pointer, detail: e.message ?? 'invalid' });
    if (out.size >= MAX_ERRORS) break;
  }
  return [...out.values()];
}

export class ContractValidator {
  private readonly ajv: Ajv2020;
  private readonly validators: Record<RequestSchema, ValidateFunction>;

  constructor() {
    const ajv = new Ajv2020({ strict: true, allErrors: true });
    this.ajv = ajv;
    ajv.addSchema(read('envelope.schema.json') as object);
    ajv.addSchema(read('delivery.schema.json') as object);
    ajv.addSchema({
      $id: `${BASE}conventions/components.openapi.yaml`,
      $defs: schemasOf(read('conventions/components.openapi.yaml')),
    });
    ajv.addSchema({
      $id: `${BASE}org-gateway.openapi.yaml`,
      $defs: schemasOf(read('org-gateway.openapi.yaml')),
    });
    const compile = (name: RequestSchema): ValidateFunction => {
      const fn = ajv.getSchema(`${BASE}org-gateway.openapi.yaml#/$defs/${name}`);
      if (!fn) throw new Error(`no compiled schema for ${name}`);
      return fn;
    };
    this.validators = {
      FirstAuthenticateRequest: compile('FirstAuthenticateRequest'),
      AuthenticateRequest: compile('AuthenticateRequest'),
      ChangeMaterialRequest: compile('ChangeMaterialRequest'),
    };
  }

  /**
   * Any definition of the S1 document or the shared components, for checking
   * responses against the contract in tests (TC-OI-023).
   */
  conforms(document: 'org-gateway' | 'components', name: string, value: unknown): boolean {
    const id =
      document === 'org-gateway'
        ? `${BASE}org-gateway.openapi.yaml#/$defs/${name}`
        : `${BASE}conventions/components.openapi.yaml#/$defs/${name}`;
    const fn = this.ajv.getSchema(id);
    if (!fn) throw new Error(`no definition ${document}#${name}`);
    return fn(value) === true; // the contract's schemas are synchronous
  }

  /** The field errors, or none. A detail never echoes the value. */
  validate(schema: RequestSchema, value: unknown): FieldError[] {
    const fn = this.validators[schema];
    return fn(value) ? [] : fieldErrors(fn.errors ?? []);
  }
}
