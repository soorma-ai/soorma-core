// SPDX-License-Identifier: Apache-2.0
//
// The compatibility test (I7; NFR-WC-01, 02; BR-VER-05).
//
// Every fixture of every contract version present is validated against the
// current schemas. A change in a fixture's outcome is classified:
//   - an earlier valid fixture that now fails is a BREAKING change
//   - an earlier invalid fixture that now passes is a WIDENING, compatible
// Either fails the test unless contract/CHANGELOG.md classifies that fixture's
// change, and the classification must match the outcome.
//
// The CHANGELOG form, one line per fixture under its version heading:
//   - fixture `0.1.0/envelope/invalid/chain-33-entries.json`: compatible
//   - fixture `0.1.0/envelope/valid/sample.json`: breaking
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { contractRoot, listFiles, type Finding } from './model.ts';
import { SURFACES, type ContractSchema } from '../validator.ts';

export interface Fixture {
  /**
   * `{version}/{schema}/{valid|invalid}/{name}.json`, or, for a surface document's
   * definition, `{version}/{surface}/{Definition}/{valid|invalid}/{name}.json`;
   * relative to contract/fixtures/.
   */
  path: string;
  version: string;
  schema: ContractSchema;
  expectedValid: boolean;
  data: unknown;
}

export type Classification = 'breaking' | 'compatible';

const SCHEMA_DIRS: Record<string, ContractSchema> = {
  envelope: 'Envelope',
  draft: 'Draft',
  inbound: 'Inbound',
  delivery: 'Delivery',
  problem: 'Problem',
};

/** Reads every fixture under contract/fixtures/. */
export function loadFixtures(root: string = contractRoot): Fixture[] {
  return listFiles(join(root, 'fixtures'))
    .filter((p) => p.endsWith('.json'))
    .map((path) => {
      const parts = path.split('/');
      const surface = SURFACES.find((s) => s === parts[1]);
      const [version, dir, kind] =
        surface && parts.length === 5 ? [parts[0], parts[2], parts[3]] : parts;
      const schema: ContractSchema | undefined = surface
        ? parts.length === 5 && dir
          ? `${surface}#${dir}`
          : undefined
        : SCHEMA_DIRS[dir ?? ''];
      if (!version || !schema || (kind !== 'valid' && kind !== 'invalid')) {
        throw new Error(
          `fixture ${path} is not at {version}/{envelope|draft|inbound|delivery|problem}/{valid|invalid}/ or {version}/{surface}/{Definition}/{valid|invalid}/`,
        );
      }
      const data = JSON.parse(readFileSync(join(root, 'fixtures', path), 'utf8')) as unknown;
      return { path, version, schema, expectedValid: kind === 'valid', data };
    });
}

/** The fixture classifications recorded in CHANGELOG.md. Examples in fenced code blocks are ignored. */
export function parseClassifications(changelog: string): Map<string, Classification> {
  const out = new Map<string, Classification>();
  const prose = changelog.replace(/^```[\s\S]*?^```/gm, '');
  for (const m of prose.matchAll(/^- fixture `([^`]+)`: (breaking|compatible)\b/gm)) {
    out.set(m[1] as string, m[2] as Classification);
  }
  return out;
}

export function compatFindings(
  fixtures: Fixture[],
  validate: (schema: ContractSchema, value: unknown) => boolean,
  classifications: Map<string, Classification>,
): Finding[] {
  const findings: Finding[] = [];
  for (const f of fixtures) {
    const valid = validate(f.schema, f.data);
    if (valid === f.expectedValid) continue;
    const outcome: Classification = f.expectedValid ? 'breaking' : 'compatible';
    const what = f.expectedValid
      ? `breaking change: this ${f.version} valid fixture now fails`
      : `widening: this ${f.version} invalid fixture now passes`;
    const recorded = classifications.get(f.path);
    if (recorded === undefined) {
      findings.push({
        check: 'compatibility',
        location: `fixtures/${f.path}`,
        message: `${what}, and CHANGELOG.md does not classify it`,
      });
    } else if (recorded !== outcome) {
      findings.push({
        check: 'compatibility',
        location: `fixtures/${f.path}`,
        message: `${what}, but CHANGELOG.md classifies it as ${recorded}; it must be ${outcome}`,
      });
    }
  }
  return findings;
}

export function readChangelog(root: string = contractRoot): string {
  return readFileSync(join(root, 'CHANGELOG.md'), 'utf8');
}
