// SPDX-License-Identifier: Apache-2.0
//
// The contract checks (NFR-WC-06 to 11, 21; TC-WC-009, 011, 021, 034 to 037).
// Each is a pure function returning findings with a location.
import { isOpenEnum } from '../generate-types.ts';
import { patternProblems } from './regex.ts';
import {
  atPointer,
  documentAt,
  isObject,
  loc,
  walkJson,
  walkSchema,
  type Contract,
  type Finding,
  type JsonObject,
} from './model.ts';
import { aliases, receivedSide, requestSide, requestToReceivedRefs } from './sides.ts';

const COMPONENTS = 'conventions/components.openapi.yaml';

function splitLocation(location: string): { path: string; pointer: string } {
  const i = location.indexOf('#');
  return { path: location.slice(0, i), pointer: location.slice(i + 1) };
}

function definitionAt(contract: Contract, location: string): unknown {
  const { path, pointer } = splitLocation(location);
  const doc = contract.documents.find((d) => d.path === path);
  return doc ? atPointer(doc.data, pointer) : undefined;
}

/** Every definition: `$defs` entries of schema files, `components.schemas` of OpenAPI documents. */
export function definitions(contract: Contract): string[] {
  const out: string[] = [];
  for (const doc of contract.documents) {
    if (!isObject(doc.data)) continue;
    const defs = doc.path.endsWith('.schema.json')
      ? doc.data.$defs
      : isObject(doc.data.components)
        ? doc.data.components.schemas
        : undefined;
    const prefix = doc.path.endsWith('.schema.json') ? '/$defs' : '/components/schemas';
    if (isObject(defs))
      for (const name of Object.keys(defs)) out.push(loc(doc.path, `${prefix}/${name}`));
  }
  return out;
}

/** Resolves a `$ref` found in `fromPath` to `{path}#{pointer}`, relative to `contract/`. */
export function resolveRef(fromPath: string, ref: string): string | undefined {
  if (/^[a-zA-Z][a-zA-Z0-9+.-]*:/.test(ref)) return undefined;
  const hash = ref.indexOf('#');
  const file = hash === -1 ? ref : ref.slice(0, hash);
  const pointer = hash === -1 ? '' : ref.slice(hash + 1);
  if (file === '') return loc(fromPath, pointer);
  const parts = fromPath.split('/').slice(0, -1);
  for (const segment of file.split('/')) {
    if (segment === '..') {
      if (parts.length === 0) return undefined;
      parts.pop();
    } else if (segment !== '.' && segment !== '') {
      parts.push(segment);
    }
  }
  return loc(parts.join('/'), pointer);
}

/** Every definition is classified in exactly one list of sides.ts, and every listed one exists. */
export function checkClassification(contract: Contract): Finding[] {
  const findings: Finding[] = [];
  const lists = [...requestSide, ...receivedSide, ...aliases];
  for (const def of definitions(contract)) {
    const count = lists.filter((l) => l === def).length;
    if (count !== 1) {
      findings.push({
        check: 'classification',
        location: def,
        message:
          count === 0
            ? 'not classified as request-side or received-side in sides.ts'
            : 'classified more than once',
      });
    }
  }
  for (const listed of lists) {
    if (definitionAt(contract, listed) === undefined) {
      findings.push({
        check: 'classification',
        location: listed,
        message: 'listed in sides.ts but not defined',
      });
    }
  }
  return findings;
}

/** NFR-WC-06: open enumerations take one shape; a bare `enum` appears only on the request side. */
export function checkOpenEnums(contract: Contract): Finding[] {
  const findings: Finding[] = [];
  for (const def of definitions(contract)) {
    if (requestSide.includes(def)) continue;
    const { path, pointer } = splitLocation(def);
    walkSchema(definitionAt(contract, def), pointer, (node, p) => {
      if (!('enum' in node)) return;
      const parentPointer = p.endsWith('/anyOf/0') ? p.slice(0, -'/anyOf/0'.length) : undefined;
      const parent =
        parentPointer === undefined ? undefined : definitionAt(contract, loc(path, parentPointer));
      if (!isOpenEnum(parent)) {
        findings.push({
          check: 'open-enum',
          location: loc(path, p),
          message:
            'an enumeration on a received definition must be the open shape anyOf: [{ enum: [...] }, { type: string }]',
        });
      }
    });
  }
  return findings;
}

function hasType(node: JsonObject, type: string): boolean {
  return node.type === type || (Array.isArray(node.type) && node.type.includes(type));
}

/** NFR-WC-07: every request-side string has a maxLength and every array a maxItems. */
export function checkBounds(contract: Contract): Finding[] {
  const findings: Finding[] = [];
  for (const def of requestSide) {
    const { path, pointer } = splitLocation(def);
    walkSchema(definitionAt(contract, def), pointer, (node, p) => {
      const at = loc(path, p);
      if (
        hasType(node, 'string') &&
        !('const' in node) &&
        !('enum' in node) &&
        typeof node.maxLength !== 'number'
      ) {
        findings.push({
          check: 'bounds',
          location: at,
          message: 'request-side string has no maxLength',
        });
      }
      if (hasType(node, 'array') && typeof node.maxItems !== 'number') {
        findings.push({
          check: 'bounds',
          location: at,
          message: 'request-side array has no maxItems',
        });
      }
      if (typeof node.$ref === 'string') {
        const target = resolveRef(path, node.$ref);
        if (target && receivedSide.includes(target)) {
          if (requestToReceivedRefs.includes(at)) {
            findings.push(...forwardedArrayBounds(contract, target, new Set()));
          } else {
            findings.push({
              check: 'bounds',
              location: at,
              message: `request-side definition references the received-side ${target}, which is unbounded`,
            });
          }
        }
      }
    });
  }
  return findings;
}

/**
 * A received definition accepted as request input (the forwarded envelope):
 * every array reachable from it has a maxItems. Its strings stay unbounded
 * (BR-ID-11); the 16 KiB envelope bound covers them, checked in code.
 */
function forwardedArrayBounds(contract: Contract, def: string, seen: Set<string>): Finding[] {
  if (seen.has(def)) return [];
  seen.add(def);
  const findings: Finding[] = [];
  const { path, pointer } = splitLocation(def);
  walkSchema(definitionAt(contract, def), pointer, (node, p) => {
    if (hasType(node, 'array') && typeof node.maxItems !== 'number') {
      findings.push({
        check: 'bounds',
        location: loc(path, p),
        message: 'array in the forwarded envelope has no maxItems',
      });
    }
    if (typeof node.$ref === 'string') {
      const target = resolveRef(path, node.$ref);
      if (target) findings.push(...forwardedArrayBounds(contract, target, seen));
    }
  });
  return findings;
}

/** BR-ID-11: received definitions carry no pattern and no maximum length. */
export function checkReceived(contract: Contract): Finding[] {
  const findings: Finding[] = [];
  for (const def of receivedSide) {
    const { path, pointer } = splitLocation(def);
    walkSchema(definitionAt(contract, def), pointer, (node, p) => {
      const at = loc(path, p);
      if ('pattern' in node)
        findings.push({ check: 'received', location: at, message: 'received value has a pattern' });
      if ('maxLength' in node)
        findings.push({
          check: 'received',
          location: at,
          message: 'received value has a maxLength',
        });
      if (typeof node.minLength === 'number' && node.minLength > 1) {
        findings.push({
          check: 'received',
          location: at,
          message: 'received value has a minLength above 1',
        });
      }
    });
  }
  return findings;
}

function isKeyword(pointer: string): boolean {
  const segments = pointer.split('/');
  const parent = segments[segments.length - 2];
  return parent !== 'properties' && parent !== '$defs' && parent !== 'schemas';
}

/** NFR-WC-08: every pattern is anchored, in the RE2 subset, and linear-time under backtracking. */
export function checkPatterns(contract: Contract): Finding[] {
  const findings: Finding[] = [];
  for (const doc of contract.documents) {
    walkJson(doc.data, '', (key, value, p) => {
      if (key !== 'pattern' || !isKeyword(p) || typeof value !== 'string') return;
      for (const message of patternProblems(value)) {
        findings.push({ check: 'pattern', location: loc(doc.path, p), message });
      }
    });
  }
  return findings;
}

/** NFR-WC-09: no `format` keyword anywhere in the contract. */
export function checkNoFormat(contract: Contract): Finding[] {
  const findings: Finding[] = [];
  for (const doc of contract.documents) {
    walkJson(doc.data, '', (key, _value, p) => {
      if (key === 'format' && isKeyword(p)) {
        findings.push({
          check: 'format',
          location: loc(doc.path, p),
          message: 'the format keyword is not used in the contract',
        });
      }
    });
  }
  return findings;
}

/** NFR-WC-11: every `$ref` is relative, stays inside contract/, and resolves. */
export function checkRefs(contract: Contract): Finding[] {
  const findings: Finding[] = [];
  for (const doc of contract.documents) {
    walkJson(doc.data, '', (key, value, p) => {
      if (key !== '$ref' || typeof value !== 'string') return;
      const at = loc(doc.path, p);
      const target = resolveRef(doc.path, value);
      if (!target) {
        findings.push({
          check: 'refs',
          location: at,
          message: `${value} is not a relative reference inside contract/`,
        });
      } else if (definitionAt(contract, target) === undefined) {
        findings.push({ check: 'refs', location: at, message: `${value} does not resolve` });
      }
    });
  }
  return findings;
}

const SHARED_SCHEMAS: Record<string, string> = {
  envelope: 'envelope.schema.json#/$defs/Envelope',
  draft: 'envelope.schema.json#/$defs/Draft',
  inbound: 'envelope.schema.json#/$defs/Inbound',
  delivery: 'delivery.schema.json#/$defs/Delivery',
  problem: `${COMPONENTS}#/components/schemas/Problem`,
};
const SHARED_HEADERS = ['Soorma-Contract-Version', 'Soorma-Request-Id', 'Retry-After'];
const SHARED_SCHEMES = ['agentCredential', 'environmentCredential', 'signIn'];

function looksLikeCopy(node: JsonObject): string | undefined {
  const props = isObject(node.properties) ? Object.keys(node.properties) : [];
  const has = (...names: string[]): boolean => names.every((n) => props.includes(n));
  if (has('actorChain', 'originMode')) return 'an envelope';
  if (has('clientContractVersion')) return 'a draft';
  if (has('envelope', 'seal', 'payload')) return 'a Delivery';
  if (has('envelope', 'seal')) return 'forwarded context';
  if (has('type', 'title', 'status', 'instance')) return 'a Problem';
  return undefined;
}

/** TC-WC-009: shared definitions, headers, and security schemes are referenced, never copied. */
export function checkShared(contract: Contract): Finding[] {
  const findings: Finding[] = [];
  const canonical = new Set(Object.values(SHARED_SCHEMAS));
  for (const doc of contract.documents) {
    if (!doc.path.endsWith('.openapi.yaml') || !isObject(doc.data)) continue;
    const components = isObject(doc.data.components) ? doc.data.components : {};
    walkJson(doc.data, '', (_key, value, p) => {
      if (!isObject(value)) return;
      const copy = looksLikeCopy(value);
      if (copy && !canonical.has(loc(doc.path, p))) {
        findings.push({
          check: 'shared',
          location: loc(doc.path, p),
          message: `an inline copy of ${copy}; reference the shared definition`,
        });
      }
    });
    if (doc.path === COMPONENTS) continue;
    const schemas = isObject(components.schemas) ? components.schemas : {};
    for (const [name, schema] of Object.entries(schemas)) {
      const shared = SHARED_SCHEMAS[name.toLowerCase()];
      if (!shared) continue;
      const target =
        isObject(schema) && typeof schema.$ref === 'string'
          ? resolveRef(doc.path, schema.$ref)
          : undefined;
      if (target !== shared || Object.keys(schema as JsonObject).length !== 1) {
        findings.push({
          check: 'shared',
          location: loc(doc.path, `/components/schemas/${name}`),
          message: `must be only a $ref to ${shared}`,
        });
      }
    }
    for (const [section, names] of [
      ['headers', SHARED_HEADERS],
      ['securitySchemes', SHARED_SCHEMES],
    ] as const) {
      const map = isObject(components[section]) ? components[section] : {};
      for (const name of names) {
        const entry = map[name];
        if (entry !== undefined && !(isObject(entry) && typeof entry.$ref === 'string')) {
          findings.push({
            check: 'shared',
            location: loc(doc.path, `/components/${section}/${name}`),
            message: `redefined; reference ${COMPONENTS} instead`,
          });
        }
      }
    }
  }
  return findings;
}

/** Every structural contract check. */
export function contractFindings(contract: Contract): Finding[] {
  documentAt(contract, COMPONENTS);
  return [
    ...checkClassification(contract),
    ...checkOpenEnums(contract),
    ...checkBounds(contract),
    ...checkReceived(contract),
    ...checkPatterns(contract),
    ...checkNoFormat(contract),
    ...checkRefs(contract),
    ...checkShared(contract),
  ];
}
