// SPDX-License-Identifier: Apache-2.0
//
// Loads the contract's schemas and documents for the contract checks, and walks
// schema objects. Every check is a pure function over a `Contract`, so a test can
// run it against the real files and against a mutated copy in memory.
import { readFileSync, readdirSync, statSync } from 'node:fs';
import { dirname, join, relative, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { parse as parseYaml } from 'yaml';

export const contractRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..', '..');

/** One contract document: a JSON Schema file or an OpenAPI document. */
export interface ContractDocument {
  /** Path relative to `contract/`, with `/` separators. */
  path: string;
  data: unknown;
}

export interface Contract {
  documents: ContractDocument[];
}

/** A finding: what is wrong, and where. */
export interface Finding {
  check: string;
  location: string;
  message: string;
}

const SKIPPED_DIRS = new Set(['node_modules', 'dist', 'fixtures', 'meta', 'generated', 'test']);

/** Every file under `contract/`, relative, with `/` separators. */
export function listFiles(
  root: string = contractRoot,
  // dist/ is the git-ignored output of tsconfig.build.json (D-CG-OI-02), not contract source.
  skip: Set<string> = new Set(['node_modules', 'dist']),
): string[] {
  const out: string[] = [];
  const walkDir = (dir: string): void => {
    for (const name of readdirSync(dir).sort()) {
      const full = join(dir, name);
      if (statSync(full).isDirectory()) {
        if (!skip.has(name)) walkDir(full);
      } else {
        out.push(relative(root, full).split('\\').join('/'));
      }
    }
  };
  walkDir(root);
  return out;
}

/** The contract's schemas (`*.schema.json`) and OpenAPI documents (`*.openapi.yaml`). */
export function loadContract(root: string = contractRoot): Contract {
  const documents = listFiles(root, SKIPPED_DIRS)
    .filter((p) => p.endsWith('.schema.json') || p.endsWith('.openapi.yaml'))
    .map((path) => {
      const text = readFileSync(join(root, path), 'utf8');
      return {
        path,
        data: path.endsWith('.json') ? (JSON.parse(text) as unknown) : (parseYaml(text) as unknown),
      };
    });
  return { documents };
}

/** A deep copy, for mutating in tests. */
export function cloneContract(contract: Contract): Contract {
  return structuredClone(contract);
}

export function documentAt(contract: Contract, path: string): ContractDocument {
  const doc = contract.documents.find((d) => d.path === path);
  if (!doc) throw new Error(`no contract document ${path}`);
  return doc;
}

export type JsonObject = Record<string, unknown>;

export function isObject(value: unknown): value is JsonObject {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function escapePointer(segment: string): string {
  return segment.replace(/~/g, '~0').replace(/\//g, '~1');
}

/** Resolves a JSON Pointer (`/a/b`) within a value. */
export function atPointer(value: unknown, pointer: string): unknown {
  if (pointer === '' || pointer === '/') return value;
  let current: unknown = value;
  for (const raw of pointer.replace(/^\//, '').split('/')) {
    const segment = raw.replace(/~1/g, '/').replace(/~0/g, '~');
    if (Array.isArray(current)) current = current[Number(segment)];
    else if (isObject(current)) current = current[segment];
    else return undefined;
  }
  return current;
}

const SUBSCHEMA_MAPS = ['properties', 'patternProperties', '$defs', 'dependentSchemas'];
const SUBSCHEMA_LISTS = ['allOf', 'anyOf', 'oneOf', 'prefixItems'];
const SUBSCHEMA_SINGLE = [
  'items',
  'additionalProperties',
  'not',
  'if',
  'then',
  'else',
  'contains',
  'propertyNames',
  'unevaluatedProperties',
  'unevaluatedItems',
];

/**
 * Visits a schema and its subschemas, depth first, without following `$ref`.
 * `pointer` is the location of each visited schema. When `intoDefs` is false,
 * nested `$defs` are not entered: each definition is visited on its own.
 */
export function walkSchema(
  schema: unknown,
  pointer: string,
  visit: (node: JsonObject, pointer: string) => void,
  intoDefs = false,
): void {
  if (!isObject(schema)) return;
  visit(schema, pointer);
  for (const key of SUBSCHEMA_MAPS) {
    if (key === '$defs' && !intoDefs) continue;
    const map = schema[key];
    if (isObject(map)) {
      for (const [name, sub] of Object.entries(map)) {
        walkSchema(sub, `${pointer}/${key}/${escapePointer(name)}`, visit, intoDefs);
      }
    }
  }
  for (const key of SUBSCHEMA_LISTS) {
    const list = schema[key];
    if (Array.isArray(list))
      list.forEach((sub, i) => walkSchema(sub, `${pointer}/${key}/${i}`, visit, intoDefs));
  }
  for (const key of SUBSCHEMA_SINGLE) {
    walkSchema(schema[key], `${pointer}/${key}`, visit, intoDefs);
  }
}

/** Visits every value in a JSON document, with its pointer: for checks over all keys. */
export function walkJson(
  value: unknown,
  pointer: string,
  visit: (key: string, value: unknown, pointer: string) => void,
): void {
  if (Array.isArray(value)) {
    value.forEach((v, i) => walkJson(v, `${pointer}/${i}`, visit));
  } else if (isObject(value)) {
    for (const [k, v] of Object.entries(value)) {
      const p = `${pointer}/${escapePointer(k)}`;
      visit(k, v, p);
      walkJson(v, p, visit);
    }
  }
}

/** `{document}#{pointer}`, the form every finding's location takes. */
export function loc(path: string, pointer: string): string {
  return `${path}#${pointer}`;
}
