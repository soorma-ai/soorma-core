// SPDX-License-Identifier: Apache-2.0
// The fixture corpus and the compatibility test: TC-WC-030, 031.
import { describe, expect, it } from 'vitest';
import {
  compatFindings,
  loadFixtures,
  parseClassifications,
  readChangelog,
  type Classification,
} from '../scripts/checks/compat.ts';
import { cloneContract, documentAt, type Contract } from '../scripts/checks/model.ts';
import { createValidator } from '../scripts/validator.ts';
import { contract, validator } from './helpers.ts';

type Defs = Record<string, Record<string, any>>;

const fixtures = loadFixtures();
const changelog = readChangelog();

function mutateEnvelope(change: (defs: Defs) => void): Contract {
  const c = cloneContract(contract);
  change((documentAt(c, 'envelope.schema.json').data as { $defs: Defs }).$defs);
  return c;
}

function run(
  c: Contract,
  classifications: Map<string, Classification> = parseClassifications(changelog),
): string[] {
  return compatFindings(fixtures, createValidator(c).validate, classifications).map(
    (f) => `${f.location}: ${f.message}`,
  );
}

/** The fixtures whose outcome changes under a contract, all classified one way. */
function classifyAll(c: Contract, as: Classification): Map<string, Classification> {
  const { validate } = createValidator(c);
  return new Map(
    fixtures.filter((f) => validate(f.schema, f.data) !== f.expectedValid).map((f) => [f.path, as]),
  );
}

const requireTracestate = (d: Defs): void => {
  d.EnvelopeTraceContext!.required = ['traceparent', 'tracestate'];
};
const widenChain = (d: Defs): void => {
  d.Envelope!.properties.actorChain.maxItems = 64;
};

describe('TC-WC-030: the fixture corpus and changelog establish the 0.1.0 baseline', () => {
  it('has valid and invalid fixtures for each of the five schemas', () => {
    for (const schema of ['Envelope', 'Draft', 'Inbound', 'Delivery', 'Problem']) {
      expect(
        fixtures.some((f) => f.version === '0.1.0' && f.schema === schema && f.expectedValid),
      ).toBe(true);
      expect(
        fixtures.some((f) => f.version === '0.1.0' && f.schema === schema && !f.expectedValid),
      ).toBe(true);
    }
  });

  it('passes: every valid fixture validates, every invalid one fails, so nothing needs classifying', () => {
    for (const f of fixtures)
      expect(validator.validate(f.schema, f.data), f.path).toBe(f.expectedValid);
    expect(run(contract)).toEqual([]);
  });

  it('records the 0.1.0 baseline, the classification rule and form, and the NFR-WC-03 obligation', () => {
    expect(changelog).toContain('## 0.1.0');
    expect(changelog).toContain('Compatible (initial)');
    expect(changelog).toContain('An earlier valid fixture that now fails is a breaking change');
    expect(changelog).toContain('An earlier invalid fixture that now passes is a widening');
    expect(changelog).toContain('- fixture `0.1.0/envelope/valid/sample.json`: breaking');
    expect(changelog).toContain(
      'An automated OpenAPI diff is added with the first change after `contract-v0.1.0` is tagged',
    );
    expect(parseClassifications(changelog).size).toBe(0);
  });
});

describe('TC-WC-031: the compatibility test detects every unclassified outcome change', () => {
  it.each([
    ['tracestate required', requireTracestate],
    [
      'actorChain renamed to chain',
      (d: Defs) => {
        d.Envelope!.properties.chain = d.Envelope!.properties.actorChain;
        delete d.Envelope!.properties.actorChain;
        d.Envelope!.required = (d.Envelope!.required as string[]).map((r) =>
          r === 'actorChain' ? 'chain' : r,
        );
      },
    ],
    [
      'actorChain maxItems lowered to 16',
      (d: Defs) => (d.Envelope!.properties.actorChain.maxItems = 16),
    ],
    [
      'the envelope closed to unknown fields',
      (d: Defs) => (d.Envelope!.additionalProperties = false),
    ],
  ])('steps 1 to 4: fails on a breaking change (%s), naming the fixture', (_name, change) => {
    const findings = run(mutateEnvelope(change));
    expect(findings.length).toBeGreaterThan(0);
    expect(
      findings.every((f) => f.includes('breaking change') && f.includes('does not classify it')),
    ).toBe(true);
    expect(findings.some((f) => f.startsWith('fixtures/0.1.0/'))).toBe(true);
  });

  it('step 5: fails on an unclassified widening, naming the fixture', () => {
    const findings = run(mutateEnvelope(widenChain));
    expect(findings).toContain(
      'fixtures/0.1.0/envelope/invalid/chain-33-entries.json: widening: this 0.1.0 invalid fixture now passes, and CHANGELOG.md does not classify it',
    );
  });

  it('step 6: passes with the widening classified compatible, and fails with it classified breaking', () => {
    const c = mutateEnvelope(widenChain);
    expect(run(c, classifyAll(c, 'compatible'))).toEqual([]);
    const wrong = run(c, classifyAll(c, 'breaking'));
    expect(wrong.length).toBeGreaterThan(0);
    expect(wrong.every((f) => f.includes('it must be compatible'))).toBe(true);
  });

  it('step 7: passes with the breaking change classified breaking, and fails with it classified compatible', () => {
    const c = mutateEnvelope(requireTracestate);
    expect(run(c, classifyAll(c, 'breaking'))).toEqual([]);
    const wrong = run(c, classifyAll(c, 'compatible'));
    expect(wrong.length).toBeGreaterThan(0);
    expect(wrong.every((f) => f.includes('it must be breaking'))).toBe(true);
  });

  it('reads classifications in the recorded form, and ignores the examples in code blocks', () => {
    const text = [
      '## 0.2.0',
      '- fixture `0.1.0/envelope/invalid/chain-33-entries.json`: compatible',
      '```text',
      '- fixture `0.1.0/envelope/valid/sample.json`: breaking',
      '```',
    ].join('\n');
    expect([...parseClassifications(text)]).toEqual([
      ['0.1.0/envelope/invalid/chain-33-entries.json', 'compatible'],
    ]);
  });
});
