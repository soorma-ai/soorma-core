// SPDX-License-Identifier: Apache-2.0
//
// Validates every OpenAPI document against the pinned OpenAPI 3.1 schema, offline,
// and checks the pinned file's SHA-256 against its record (NFR-WC-11; T-08).
//
// This Ajv instance is deliberately NOT strict (strict: false, validateFormats:
// false). The meta-schema is third-party and not written to Ajv's strict rules,
// and it uses `format` as an annotation. See contract/meta/SOURCE.md. The
// contract's own schemas are compiled by a separate, strict instance.
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { Ajv2020 } from 'ajv/dist/2020.js';
import { contractRoot, loc, type Contract, type Finding } from './model.ts';

export const metaSchemaFile = 'meta/openapi-3.1-schema-2026-08-03.json';
export const metaSourceFile = 'meta/SOURCE.md';

/** The SHA-256 recorded in SOURCE.md. */
export function recordedDigest(sourceText: string): string | undefined {
  return /\| SHA-256 \| `([0-9a-f]{64})` \|/.exec(sourceText)?.[1];
}

export function digestFindings(metaBytes: Buffer, sourceText: string): Finding[] {
  const actual = createHash('sha256').update(metaBytes).digest('hex');
  const recorded = recordedDigest(sourceText);
  if (recorded === actual) return [];
  return [
    {
      check: 'meta-schema',
      location: metaSchemaFile,
      message: recorded
        ? `SHA-256 ${actual} does not match the ${recorded} recorded in ${metaSourceFile}`
        : `no SHA-256 recorded in ${metaSourceFile}`,
    },
  ];
}

/**
 * The pinned meta-schema with each `$dynamicRef: "#meta"` replaced by
 * `$ref: "#/$defs/schema"`, in memory only. In this standalone file the only
 * `meta` dynamic anchor is `$defs/schema`, so the two are equivalent; Ajv 8
 * resolves the dynamic reference to the wrong schema, and then validates schema
 * objects as if they were parameters. The file on disk, whose digest is checked,
 * is never changed. See contract/meta/SOURCE.md.
 */
export function withStaticMetaRefs(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(withStaticMetaRefs);
  if (typeof value !== 'object' || value === null) return value;
  const out: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(value)) {
    if (k === '$dynamicRef' && v === '#meta') out.$ref = '#/$defs/schema';
    else out[k] = withStaticMetaRefs(v);
  }
  return out;
}

/** Validates each OpenAPI document of the contract against the meta-schema. */
export function openApiFindings(contract: Contract, metaSchema: object): Finding[] {
  const ajv = new Ajv2020({ strict: false, validateFormats: false, allErrors: true });
  const validate = ajv.compile(withStaticMetaRefs(metaSchema) as object);
  const findings: Finding[] = [];
  for (const doc of contract.documents) {
    if (!doc.path.endsWith('.openapi.yaml')) continue;
    if (!validate(doc.data)) {
      for (const e of validate.errors ?? []) {
        findings.push({
          check: 'openapi',
          location: loc(doc.path, e.instancePath),
          message: e.message ?? e.keyword,
        });
      }
    }
  }
  return findings;
}

/** Both meta-schema checks, over the files on disk. */
export function metaFindingsOnDisk(contract: Contract, root: string = contractRoot): Finding[] {
  const bytes = readFileSync(join(root, metaSchemaFile));
  const digest = digestFindings(bytes, readFileSync(join(root, metaSourceFile), 'utf8'));
  if (digest.length > 0) return digest;
  return openApiFindings(contract, JSON.parse(bytes.toString('utf8')) as object);
}
