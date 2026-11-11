// SPDX-License-Identifier: FSL-1.1-ALv2
//
// Request validation against the contract itself (U2 NFR-OI-28), generalised
// for every service (U4 NP-EHA-12, 15): each service names its own OpenAPI
// document and the request schemas it validates. Ajv's JSON Schema 2020-12
// build, strict, compiled once at start-up from @soorma/contract's documents,
// which ship in the image. The OpenAPI documents are loaded as JSON Schemas
// whose $defs are their components.schemas, as U1's own validator does.
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { Ajv2020, type ErrorObject, type ValidateFunction } from 'ajv/dist/2020.js';
import { parse as parseYaml } from 'yaml';
import type { FieldError } from './problems.ts';

const BASE = 'https://soorma.ai/contract/';
const require = createRequire(import.meta.url);

export interface ContractValidatorOptions<Schema extends string> {
  /** The service's OpenAPI document, relative to @soorma/contract: `org-gateway.openapi.yaml`. */
  document: string;
  /** The request schemas it validates, compiled once here. */
  schemas: readonly Schema[];
}

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

export class ContractValidator<Schema extends string> {
  private readonly ajv: Ajv2020;
  private readonly document: string;
  private readonly validators: Map<Schema, ValidateFunction>;

  constructor(options: ContractValidatorOptions<Schema>) {
    const ajv = new Ajv2020({ strict: true, allErrors: true });
    this.ajv = ajv;
    this.document = options.document;
    ajv.addSchema(read('envelope.schema.json') as object);
    ajv.addSchema(read('delivery.schema.json') as object);
    ajv.addSchema({
      $id: `${BASE}conventions/components.openapi.yaml`,
      $defs: schemasOf(read('conventions/components.openapi.yaml')),
    });
    ajv.addSchema({
      $id: `${BASE}${options.document}`,
      $defs: schemasOf(read(options.document)),
    });
    this.validators = new Map();
    for (const name of options.schemas) {
      const fn = ajv.getSchema(`${BASE}${options.document}#/$defs/${name}`);
      if (!fn) throw new Error(`no compiled schema for ${name}`);
      this.validators.set(name, fn);
    }
  }

  /**
   * Any definition of the service's document or the shared components, for
   * checking responses against the contract in tests.
   */
  conforms(document: 'service' | 'components', name: string, value: unknown): boolean {
    const id =
      document === 'service'
        ? `${BASE}${this.document}#/$defs/${name}`
        : `${BASE}conventions/components.openapi.yaml#/$defs/${name}`;
    const fn = this.ajv.getSchema(id);
    if (!fn) throw new Error(`no definition ${document}#${name}`);
    return fn(value) === true; // the contract's schemas are synchronous
  }

  /** The field errors, or none. A detail never echoes the value. */
  validate(schema: Schema, value: unknown): FieldError[] {
    const fn = this.validators.get(schema);
    if (!fn) throw new Error(`no compiled schema for ${schema}`);
    return fn(value) ? [] : fieldErrors(fn.errors ?? []);
  }
}
