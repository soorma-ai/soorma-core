// SPDX-License-Identifier: Apache-2.0
//
// Shared test helpers: the contract's strict validator, the Common Fixtures
// samples (test-specs-narrative.md), and readers for the schemas and conventions.
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import {
  contractRoot,
  documentAt,
  loadContract,
  type JsonObject,
} from '../scripts/checks/model.ts';
import { createValidator, type ContractSchema } from '../scripts/validator.ts';

export const contract = loadContract();
export const validator = createValidator(contract);

/** A fixture from fixtures/0.1.0/, parsed. Labelled test data, never a tenant identifier (I9). */
export function fixture(path: string): JsonObject {
  return JSON.parse(
    readFileSync(join(contractRoot, 'fixtures', '0.1.0', `${path}.json`), 'utf8'),
  ) as JsonObject;
}

export const samples = {
  envelope: fixture('envelope/valid/sample'),
  delegated: fixture('envelope/valid/delegated'),
  reBroadened: fixture('envelope/valid/re-broadened'),
  draft: fixture('draft/valid/sample'),
  forwarding: fixture('draft/valid/forwarding'),
  delivery: fixture('delivery/valid/sample'),
  problem: fixture('problem/valid/validation'),
};

/** A deep copy, typed loosely so a test can change any field. */
export function copy(value: JsonObject): Record<string, any> {
  return structuredClone(value) as Record<string, any>;
}

export function valid(schema: ContractSchema, value: unknown): boolean {
  return validator.validate(schema, value);
}

export interface SchemaError {
  path: string;
  keyword: string;
  params: Record<string, unknown>;
}

/** Every error validating `value` (the validator reports all errors). */
export function errors(schema: ContractSchema, value: unknown): SchemaError[] {
  const fn = validator.validator(schema);
  fn(value);
  return (fn.errors ?? []).map((e) => ({
    path: e.instancePath,
    keyword: e.keyword,
    params: e.params as Record<string, unknown>,
  }));
}

/** A JSON Schema definition from envelope.schema.json or delivery.schema.json. */
export function schemaDef(
  file: 'envelope.schema.json' | 'delivery.schema.json',
  name: string,
): JsonObject {
  const data = documentAt(contract, file).data as { $defs: Record<string, JsonObject> };
  const def = data.$defs[name];
  if (!def) throw new Error(`no $defs/${name} in ${file}`);
  return def;
}

/** A component from the shared components document. */
export function component(section: string, name: string): JsonObject {
  const data = documentAt(contract, 'conventions/components.openapi.yaml').data as {
    components: Record<string, Record<string, JsonObject>>;
  };
  const entry = data.components[section]?.[name];
  if (!entry) throw new Error(`no components/${section}/${name}`);
  return entry;
}

export function componentsSection(section: string): Record<string, JsonObject> {
  const data = documentAt(contract, 'conventions/components.openapi.yaml').data as {
    components: Record<string, Record<string, JsonObject>>;
  };
  return data.components[section] ?? {};
}

/** A written convention, with Markdown emphasis removed and whitespace collapsed, for statement checks. */
export function convention(name: string): string {
  return readFileSync(join(contractRoot, 'conventions', name), 'utf8')
    .replace(/\*\*/g, '')
    .replace(/\s+/g, ' ');
}

export function contractFile(path: string): string {
  return readFileSync(join(contractRoot, path), 'utf8');
}
