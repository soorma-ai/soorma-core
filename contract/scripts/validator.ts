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
// in-memory view for validation only; the document is never changed.
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
  | 'PermissionIdentifier';

const LOCATIONS: Record<ContractSchema, string> = {
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
};

function toDefsRefs(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(toDefsRefs);
  if (!isObject(value)) return value;
  const out: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(value)) {
    out[k] =
      k === '$ref' && typeof v === 'string'
        ? v.replace(/^#\/components\/schemas\//, '#/$defs/')
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
    }
  }
  const cache = new Map<ContractSchema, ValidateFunction>();
  const validator = (schema: ContractSchema): ValidateFunction => {
    let fn = cache.get(schema);
    if (!fn) {
      fn = ajv.getSchema(LOCATIONS[schema]);
      if (!fn) throw new Error(`no compiled schema for ${schema}`);
      cache.set(schema, fn);
    }
    return fn;
  };
  return { ajv, validator, validate: (schema, value) => validator(schema)(value) };
}
