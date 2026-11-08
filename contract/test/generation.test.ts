// SPDX-License-Identifier: Apache-2.0
// Type generation: TC-WC-003, 032, 033.
import {
  cpSync,
  mkdtempSync,
  readFileSync,
  readdirSync,
  rmSync,
  statSync,
  writeFileSync,
} from 'node:fs';
import { tmpdir } from 'node:os';
import { join, relative, resolve } from 'node:path';
import ts from 'typescript';
import { afterAll, describe, expect, it } from 'vitest';
import { contractRoot } from '../scripts/checks/model.ts';
import {
  componentsDocument,
  driftMessage,
  generate,
  generatedFile,
} from '../scripts/generate-types.ts';

const repoRoot = resolve(contractRoot, '..');
const SOURCE = 'contract/conventions/components.openapi.yaml';
const committed = readFileSync(generatedFile, 'utf8');

const scratch: string[] = [];
afterAll(() => {
  for (const dir of scratch) rmSync(dir, { recursive: true, force: true });
});

/** A scratch copy of the contract's schemas and documents, to change without touching the repository. */
function scratchContract(): string {
  const dir = mkdtempSync(join(tmpdir(), 'soorma-contract-'));
  scratch.push(dir);
  for (const path of ['envelope.schema.json', 'delivery.schema.json', 'conventions']) {
    cpSync(join(contractRoot, path), join(dir, path), { recursive: true });
  }
  return dir;
}

function tsFiles(dir: string): string[] {
  const out: string[] = [];
  for (const name of readdirSync(dir)) {
    if (name === 'node_modules' || name === '.git' || name === 'aidlc-docs') continue;
    const full = join(dir, name);
    if (statSync(full).isDirectory()) out.push(...tsFiles(full));
    else if (name.endsWith('.ts')) out.push(full);
  }
  return out;
}

describe('TC-WC-003: types are generated from the schema, never hand-written', () => {
  it('carries a changed description into the generated types', async () => {
    const dir = scratchContract();
    const file = join(dir, 'envelope.schema.json');
    const schema = JSON.parse(readFileSync(file, 'utf8')) as {
      $defs: Record<string, { description: string }>;
    };
    schema.$defs.Scope!.description = 'A changed description, for TC-WC-003.';
    writeFileSync(file, JSON.stringify(schema));
    const output = await generate(join(dir, 'conventions/components.openapi.yaml'), SOURCE);
    expect(output).toContain('/** @description A changed description, for TC-WC-003. */');
  });

  it('has no hand-written declaration of a contract shape outside contract/generated/', () => {
    const declaration = /\b(interface|type)\s+(Envelope|Draft|Inbound|Delivery|Problem)\b/;
    const offenders = tsFiles(repoRoot)
      .map((f) => relative(repoRoot, f))
      .filter((f) => !f.startsWith('contract/generated/') && !f.startsWith('contract/test/golden/'))
      .filter((f) => declaration.test(readFileSync(join(repoRoot, f), 'utf8')));
    expect(offenders).toEqual([]);
  });
});

describe('TC-WC-032: the generated types keep the contract openness (golden output)', () => {
  it('generates the golden test schema exactly as the committed golden copy', async () => {
    const golden = join(contractRoot, 'test/golden/openness.openapi.yaml');
    const output = await generate(golden, 'contract/test/golden/openness.openapi.yaml');
    expect(output).toBe(readFileSync(join(contractRoot, 'test/golden/openness.ts'), 'utf8'));
  });

  it('typechecks the type-level fixture under strict, with every @ts-expect-error a genuine error', () => {
    const configPath = join(contractRoot, 'tsconfig.json');
    const config = ts.getParsedCommandLineOfConfigFile(
      configPath,
      {},
      { ...ts.sys, onUnRecoverableConfigFileDiagnostic: () => undefined },
    );
    expect(config).toBeDefined();
    expect(config!.options.strict).toBe(true);
    const program = ts.createProgram(
      [join(contractRoot, 'test/types/openness.check.ts')],
      config!.options,
    );
    const diagnostics = ts
      .getPreEmitDiagnostics(program)
      .map((d) => ts.flattenDiagnosticMessageText(d.messageText, '\n'));
    expect(diagnostics).toEqual([]);
  });

  it('generates the contract open enumerations, open objects, stamped fields, and an all-optional Problem', () => {
    expect(committed).toContain('OriginMode: "autonomous" | "delegated" | (string & {});');
    expect(committed).toMatch(/ProblemCode: "malformed_request" \|[^;]*\| \(string & \{\}\);/);
    for (const field of [
      'envelopeVersion',
      'scope',
      'originMode',
      'delegatingPrincipal',
      'actorChain',
      'reBroadening',
    ]) {
      expect(committed).toMatch(new RegExp(`Draft: \\{[^}]*\\b${field}\\?: never;`));
    }
    const problem = /Problem: \{([\s\S]*?)\} & \{/.exec(committed)?.[1] ?? '';
    const members = problem.split('\n').filter((line) => /^\s+\w+\??:/.test(line));
    expect(members.length).toBe(7);
    for (const member of members) expect(member).toMatch(/^\s+\w+\?:/);
  });
});

describe('TC-WC-033: generation is deterministic, and the build fails on drift', () => {
  it('generates byte-identical output twice, equal to the committed file', async () => {
    const first = await generate(componentsDocument, SOURCE);
    const second = await generate(componentsDocument, SOURCE);
    expect(second).toBe(first);
    expect(driftMessage(committed, first)).toBeUndefined();
  });

  it('fails on a hand edit of the generated file', async () => {
    const output = await generate(componentsDocument, SOURCE);
    const edited = committed.replace(
      'ContractVersion: string;',
      'ContractVersion: `0.${number}.${number}`;',
    );
    expect(edited).not.toBe(committed);
    expect(driftMessage(edited, output)).toContain('contract/generated/components.ts differs');
  });

  it('fails when a schema changes without regenerating', async () => {
    const dir = scratchContract();
    const file = join(dir, 'envelope.schema.json');
    const schema = JSON.parse(readFileSync(file, 'utf8')) as {
      $defs: Record<string, { properties: Record<string, unknown> }>;
    };
    schema.$defs.Scope!.properties.region = { type: 'string' };
    writeFileSync(file, JSON.stringify(schema));
    const output = await generate(join(dir, 'conventions/components.openapi.yaml'), SOURCE);
    expect(driftMessage(committed, output)).toContain('contract/generated/components.ts differs');
  });
});
