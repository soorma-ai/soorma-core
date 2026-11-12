// SPDX-License-Identifier: Apache-2.0
//
// The contract's own validator: Ajv 8 in JSON Schema 2020-12 mode, strict, with
// every contract schema loaded and compiled once (NFR-WC-10; T-05). No format
// validation is configured, because the contract uses none (NFR-WC-09), and no
// schema is ever loaded over the network (NFR-WC-11).
//
// The shared components document is OpenAPI, not a JSON Schema file. To compile
// its schemas, it is loaded as a JSON Schema whose `$defs` are its
// `components.schemas`, under the document's own `$id`, with its internal
// references (`#/components/schemas/X`) pointed at `#/$defs/X`. That is an
// in-memory view for validation only; the document is never changed. Each surface
// document (`{surface}.openapi.yaml`, such as org-gateway) is loaded the same way,
// under its own `$id`, so its request and response definitions are validated by
// the same strict validator, and its references into the shared components resolve.
import { Ajv2020, type ValidateFunction } from 'ajv/dist/2020.js';
import { isObject, loadContract, type Contract } from './checks/model.ts';

const BASE = 'https://soorma.ai/contract/';
export const COMPONENTS_ID = `${BASE}conventions/components.openapi.yaml`;

/** The definitions a contract value can be validated against. */
export type ContractSchema =
  | 'Envelope'
  | 'Draft'
  | 'Inbound'
  | 'Delivery'
  | 'Problem'
  | 'ContractVersion'
  | 'ConfiguredIdentifier'
  | 'LogicalAgentIdentifier'
  | 'PlatformReference'
  | 'InstanceIdentifier'
  | 'HumanPrincipalIdentifier'
  | 'PermissionIdentifier'
  | 'HumanPrincipalReferenceInput'
  | 'HumanPrincipalReference'
  | SurfaceSchema;

/** The surface documents whose definitions can be validated. */
export const SURFACES = ['org-gateway', 'control-gateway', 'data-gateway'] as const;
export type Surface = (typeof SURFACES)[number];

/** A definition in a surface document's `components.schemas`, as `{surface}#{name}`. */
export type SurfaceSchema = `${Surface}#${string}`;

const LOCATIONS: Record<Exclude<ContractSchema, SurfaceSchema>, string> = {
  Envelope: `${BASE}envelope.schema.json#/$defs/Envelope`,
  Draft: `${BASE}envelope.schema.json#/$defs/Draft`,
  Inbound: `${BASE}envelope.schema.json#/$defs/Inbound`,
  ContractVersion: `${BASE}envelope.schema.json#/$defs/ContractVersion`,
  Delivery: `${BASE}delivery.schema.json#/$defs/Delivery`,
  Problem: `${COMPONENTS_ID}#/$defs/Problem`,
  ConfiguredIdentifier: `${COMPONENTS_ID}#/$defs/ConfiguredIdentifier`,
  LogicalAgentIdentifier: `${COMPONENTS_ID}#/$defs/LogicalAgentIdentifier`,
  PlatformReference: `${COMPONENTS_ID}#/$defs/PlatformReference`,
  InstanceIdentifier: `${COMPONENTS_ID}#/$defs/InstanceIdentifier`,
  HumanPrincipalIdentifier: `${COMPONENTS_ID}#/$defs/HumanPrincipalIdentifier`,
  PermissionIdentifier: `${COMPONENTS_ID}#/$defs/PermissionIdentifier`,
  HumanPrincipalReferenceInput: `${COMPONENTS_ID}#/$defs/HumanPrincipalReferenceInput`,
  HumanPrincipalReference: `${COMPONENTS_ID}#/$defs/HumanPrincipalReference`,
};

function isSurfaceSchema(schema: ContractSchema): schema is SurfaceSchema {
  return schema.includes('#');
}

function location(schema: ContractSchema): string {
  if (!isSurfaceSchema(schema)) return LOCATIONS[schema];
  const [surface, name] = schema.split('#') as [string, string];
  return `${BASE}${surface}.openapi.yaml#/$defs/${name}`;
}

const SURFACE_PATHS: ReadonlySet<string> = new Set(SURFACES.map((s) => `${s}.openapi.yaml`));

function toDefsRefs(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(toDefsRefs);
  if (!isObject(value)) return value;
  const out: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(value)) {
    out[k] =
      k === '$ref' && typeof v === 'string'
        ? v.replace(/#\/components\/schemas\//, '#/$defs/')
        : toDefsRefs(v);
  }
  return out;
}

export interface ContractValidator {
  ajv: Ajv2020;
  validator: (schema: ContractSchema) => ValidateFunction;
  validate: (schema: ContractSchema, value: unknown) => boolean;
}

/** Builds the strict validator over a contract (the files on disk by default, or a mutated copy). */
export function createValidator(contract: Contract = loadContract()): ContractValidator {
  const ajv = new Ajv2020({ strict: true, allErrors: true });
  for (const doc of contract.documents) {
    if (doc.path.endsWith('.schema.json')) {
      ajv.addSchema(doc.data as object);
    } else if (doc.path === 'conventions/components.openapi.yaml' && isObject(doc.data)) {
      const components = isObject(doc.data.components) ? doc.data.components : {};
      ajv.addSchema({ $id: COMPONENTS_ID, $defs: toDefsRefs(components.schemas) });
    } else if (SURFACE_PATHS.has(doc.path) && isObject(doc.data)) {
      const components = isObject(doc.data.components) ? doc.data.components : {};
      ajv.addSchema({ $id: `${BASE}${doc.path}`, $defs: toDefsRefs(components.schemas) });
    }
  }
  const cache = new Map<ContractSchema, ValidateFunction>();
  const validator = (schema: ContractSchema): ValidateFunction => {
    let fn = cache.get(schema);
    if (!fn) {
      fn = ajv.getSchema(location(schema));
      if (!fn) throw new Error(`no compiled schema for ${schema}`);
      cache.set(schema, fn);
    }
    return fn;
  };
  return { ajv, validator, validate: (schema, value) => validator(schema)(value) };
}
