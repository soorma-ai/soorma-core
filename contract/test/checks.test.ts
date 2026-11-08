// SPDX-License-Identifier: Apache-2.0
// The contract checks, on the real contract and on mutated copies in memory:
// TC-WC-011, 034 to 037.
import { readFileSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { Ajv2020 } from 'ajv/dist/2020.js';
import { describe, expect, it } from 'vitest';
import {
  digestFindings,
  metaFindingsOnDisk,
  metaSchemaFile,
  metaSourceFile,
  openApiFindings,
} from '../scripts/checks/meta.ts';
import {
  cloneContract,
  contractRoot,
  documentAt,
  listFiles,
  loadContract,
  type Contract,
  type Finding,
} from '../scripts/checks/model.ts';
import {
  checkBounds,
  checkNoFormat,
  checkOpenEnums,
  checkPatterns,
  checkRefs,
  contractFindings,
} from '../scripts/checks/rules.ts';
import { parseReuse, spdxFindings, spdxFindingsOnDisk } from '../scripts/checks/spdx.ts';
import { contract } from './helpers.ts';

type Defs = Record<string, Record<string, any>>;

/** A mutated copy of the contract. */
function mutate(change: (envelope: Defs, components: Defs) => void): Contract {
  const c = cloneContract(contract);
  const envelope = (documentAt(c, 'envelope.schema.json').data as { $defs: Defs }).$defs;
  const components = (
    documentAt(c, 'conventions/components.openapi.yaml').data as { components: { schemas: Defs } }
  ).components.schemas;
  change(envelope, components);
  return c;
}

/** Adds every contract schema file to `ajv`, then compiles each file and each of its `$defs`. */
function compileEveryDefinition(ajv: Ajv2020, c: Contract): void {
  const files = c.documents.filter((d) => d.path.endsWith('.schema.json'));
  for (const doc of files) ajv.addSchema(doc.data as object);
  for (const doc of files) {
    const { $id, $defs } = doc.data as { $id: string; $defs: Record<string, unknown> };
    expect(ajv.getSchema($id)).toBeDefined();
    for (const name of Object.keys($defs))
      expect(ajv.getSchema(`${$id}#/$defs/${name}`)).toBeDefined();
  }
}

const locations = (findings: Finding[]): string =>
  findings.map((f) => `${f.location}: ${f.message}`).join('\n');

describe('the unchanged contract passes every check', () => {
  it('has no structural, SPDX, or meta-schema finding', () => {
    expect(contractFindings(loadContract())).toEqual([]);
    expect(spdxFindingsOnDisk()).toEqual([]);
    expect(metaFindingsOnDisk(contract)).toEqual([]);
  });
});

describe('TC-WC-011: contract files carry the Apache 2.0 licence', () => {
  it('contract/ has the Apache 2.0 licence, and the root LICENSE is FSL-1.1-ALv2', () => {
    expect(readFileSync(join(contractRoot, 'LICENSE'), 'utf8')).toContain(
      'Apache License\n                           Version 2.0, January 2004',
    );
    expect(readFileSync(resolve(contractRoot, '..', 'LICENSE'), 'utf8')).toContain('FSL-1.1-ALv2');
  });

  it('every file under contract/ declares Apache-2.0, directly or through REUSE.toml', () => {
    const files = listFiles();
    expect(files.some((f) => f.startsWith('generated/'))).toBe(true);
    expect(files.some((f) => f.startsWith('conventions/'))).toBe(true);
    expect(spdxFindingsOnDisk()).toEqual([]);
  });

  it('flags a file without the identifier, and a REUSE annotation under another licence', () => {
    const reuse = parseReuse(readFileSync(resolve(contractRoot, '..', 'REUSE.toml'), 'utf8'));
    expect(spdxFindings([{ path: 'conventions/new.md', text: '# New\n' }], reuse)).toHaveLength(1);
    expect(
      spdxFindings(
        [{ path: 'fixtures/0.1.0/x.json', text: '{}' }],
        [{ path: 'contract/fixtures/**', licence: 'MIT' }],
      ),
    ).toHaveLength(1);
    expect(spdxFindings([{ path: 'fixtures/0.1.0/x.json', text: '{}' }], reuse)).toEqual([]);
  });
});

describe('TC-WC-034: open enumerations take exactly one shape', () => {
  it('refuses a bare enum on originMode', () => {
    const findings = checkOpenEnums(
      mutate((e) => (e.OriginMode = { enum: ['autonomous', 'delegated'] })),
    );
    expect(locations(findings)).toContain('envelope.schema.json#/$defs/OriginMode');
  });

  it('refuses the two branches swapped', () => {
    const findings = checkOpenEnums(
      mutate(
        (e) =>
          (e.OriginMode = { anyOf: [{ type: 'string' }, { enum: ['autonomous', 'delegated'] }] }),
      ),
    );
    expect(locations(findings)).toContain('envelope.schema.json#/$defs/OriginMode');
  });
});

describe('TC-WC-035: validation cost is bounded on every request-side value', () => {
  it.each([
    [
      'inbound.seal',
      (e: Defs) => delete e.Inbound!.properties.seal.maxLength,
      '$defs/Inbound/properties/seal',
    ],
    [
      'tracestate',
      (e: Defs) => delete e.DraftTraceContext!.properties.tracestate.maxLength,
      '$defs/DraftTraceContext/properties/tracestate',
    ],
    [
      'actorChain',
      (e: Defs) => delete e.Envelope!.properties.actorChain.maxItems,
      '$defs/Envelope/properties/actorChain',
    ],
  ])('flags %s without its bound', (_name, change, where) => {
    expect(locations(checkBounds(mutate(change)))).toContain(where);
  });

  it('flags a shared identifier definition without maxLength', () => {
    const findings = checkBounds(mutate((_e, c) => delete c.ConfiguredIdentifier!.maxLength));
    expect(locations(findings)).toContain('components/schemas/ConfiguredIdentifier');
  });
});

describe('TC-WC-036: patterns are portable and linear-time, and no format is used', () => {
  it('finds no format keyword and no ajv-formats dependency', () => {
    expect(checkNoFormat(contract)).toEqual([]);
    expect(readFileSync(join(contractRoot, 'package.json'), 'utf8')).not.toContain('ajv-formats');
  });

  it('flags an unanchored pattern', () => {
    const findings = checkPatterns(
      mutate((_e, c) => (c.ConfiguredIdentifier!.pattern = '[A-Za-z0-9][A-Za-z0-9._~-]*$')),
    );
    expect(locations(findings)).toContain('components/schemas/ConfiguredIdentifier/pattern');
  });

  it('flags a lookahead in the traceparent pattern', () => {
    const findings = checkPatterns(
      mutate((e) => {
        const tp = e.DraftTraceContext!.properties.traceparent;
        tp.pattern = String(tp.pattern).replace('00-[0-9a-f]{32}', '00-(?!0+-)[0-9a-f]{32}');
      }),
    );
    expect(locations(findings)).toContain(
      'DraftTraceContext/properties/traceparent/pattern: lookaround is not allowed',
    );
  });

  it.each([
    ['a backreference', '^([a-z])\\1$'],
    ['a named group', '^(?<x>[a-z])$'],
  ])('flags %s', (_name, pattern) => {
    expect(
      checkPatterns(mutate((_e, c) => (c.PermissionIdentifier!.pattern = pattern))),
    ).not.toEqual([]);
  });

  it('flags format: date-time', () => {
    const findings = checkNoFormat(
      mutate((e) => (e.Inbound!.properties.seal.format = 'date-time')),
    );
    expect(locations(findings)).toContain('$defs/Inbound/properties/seal/format');
  });
});

describe('TC-WC-037: schemas compile strictly, and every reference is local', () => {
  it('compiles every contract schema in strict mode with no warnings', () => {
    const warnings: string[] = [];
    const ajv = new Ajv2020({
      strict: true,
      logger: {
        log: () => undefined,
        warn: (...a: unknown[]) => warnings.push(a.join(' ')),
        error: (...a: unknown[]) => warnings.push(a.join(' ')),
      },
    });
    compileEveryDefinition(ajv, contract);
    expect(warnings).toEqual([]);
  });

  it('validates the OpenAPI documents against the pinned meta-schema, and the digest matches', () => {
    expect(metaFindingsOnDisk(contract)).toEqual([]);
  });

  it('refuses a malformed OpenAPI document', () => {
    const c = cloneContract(contract);
    const doc = documentAt(c, 'conventions/components.openapi.yaml').data as {
      components: { parameters: Record<string, Record<string, unknown>> };
    };
    delete doc.components.parameters.SoormaContractVersion!.in;
    const meta = JSON.parse(readFileSync(join(contractRoot, metaSchemaFile), 'utf8')) as object;
    expect(openApiFindings(c, meta)).not.toEqual([]);
  });

  it('flags an https $ref', () => {
    const findings = checkRefs(
      mutate((e) => (e.Scope!.properties.organization = { $ref: 'https://example.com/id.json' })),
    );
    expect(locations(findings)).toContain('is not a relative reference inside contract/');
  });

  it('refuses an unknown keyword under strict compilation', () => {
    const c = mutate((e) => (e.Inbound!.properties.seal.minimumLength = 1));
    const ajv = new Ajv2020({ strict: true });
    expect(() => compileEveryDefinition(ajv, c)).toThrow(/unknown keyword/);
  });

  it('flags a meta-schema changed by one byte', () => {
    const bytes = readFileSync(join(contractRoot, metaSchemaFile));
    const changed = Buffer.from(bytes);
    changed[10] = changed[10]! ^ 1;
    const source = readFileSync(join(contractRoot, metaSourceFile), 'utf8');
    expect(digestFindings(bytes, source)).toEqual([]);
    expect(digestFindings(changed, source)).toHaveLength(1);
  });
});
