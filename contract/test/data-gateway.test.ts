// SPDX-License-Identifier: Apache-2.0
// S3 data-gateway's operations in the contract (U6 agent-credentials):
// TC-AC-021, 044, 045; Functional Design §13; D-AC-04, 05, 07, 24, 25.
import { describe, expect, it } from 'vitest';
import { parse } from 'yaml';
import { contractFindings } from '../scripts/checks/rules.ts';
import {
  compatFindings,
  loadFixtures,
  parseClassifications,
  readChangelog,
} from '../scripts/checks/compat.ts';
import {
  component,
  contract,
  contractFile,
  convention,
  fixture,
  valid,
  validator,
} from './helpers.ts';

type Json = Record<string, any>;

const doc = parse(contractFile('data-gateway.openapi.yaml')) as Json;
const control = parse(contractFile('control-gateway.openapi.yaml')) as Json;
const errors = convention('errors.md');
const errorsText = contractFile('conventions/errors.md');
const identifiers = convention('identifiers.md');
const changelog = contractFile('CHANGELOG.md');
const VERSION_PARAM =
  'conventions/components.openapi.yaml#/components/parameters/SoormaContractVersion';
const SHARED = 'conventions/components.openapi.yaml#/components/schemas/';

const BOOTSTRAP = '/agent-credentials';
const RENEWAL = '/agent-credentials/current/renewal';
const op = (path: string): Json => doc.paths[path].post as Json;
const response = (o: Json, status: string): Json => {
  const r = o.responses[status] as Json;
  return typeof r.$ref === 'string'
    ? (doc.components.responses[r.$ref.split('/').pop()!] as Json)
    : r;
};
const operationIds = (d: Json): string[] =>
  Object.values(d.paths as Json).flatMap((item) =>
    Object.values(item as Json).map((o) => (o as Json).operationId as string),
  );

describe('TC-AC-021: S3 operations are defined in the contract and validated against it', () => {
  it('holds exactly the two agent operations, each a POST', () => {
    expect(Object.keys(doc.paths as Json).sort()).toEqual([BOOTSTRAP, RENEWAL]);
    for (const path of [BOOTSTRAP, RENEWAL])
      expect(Object.keys(doc.paths[path] as Json)).toEqual(['post']);
    expect(op(BOOTSTRAP).operationId).toBe('exchangeBootstrap');
    expect(op(RENEWAL).operationId).toBe('renewAgentCredential');
  });

  it('bootstrap names no security scheme; renewal names agentCredential only', () => {
    expect(op(BOOTSTRAP).security).toBeUndefined();
    expect(doc.security).toBeUndefined();
    expect(op(RENEWAL).security).toEqual([{ agentCredential: [] }]);
    expect(doc.components.securitySchemes).toEqual({
      agentCredential: {
        $ref: 'conventions/components.openapi.yaml#/components/securitySchemes/agentCredential',
      },
    });
  });

  it('both take the version parameter; bootstrap a closed body, renewal none', () => {
    for (const path of [BOOTSTRAP, RENEWAL])
      expect(op(path).parameters).toEqual([{ $ref: VERSION_PARAM }]);
    expect(op(BOOTSTRAP).requestBody).toEqual({
      required: true,
      content: {
        'application/json': { schema: { $ref: '#/components/schemas/BootstrapRequest' } },
      },
    });
    expect(op(RENEWAL).requestBody).toBeUndefined();
    const body = doc.components.schemas.BootstrapRequest as Json;
    expect(body.additionalProperties).toBe(false);
    expect([...(body.required as string[])].sort()).toEqual(['agent', 'instance', 'secret']);
    expect(body.properties.agent).toEqual({ $ref: `${SHARED}LogicalAgentIdentifier` });
    expect(body.properties.instance).toEqual({ $ref: `${SHARED}InstanceIdentifier` });
  });

  it('neither carries an envelope, a draft, or forwarded context (GAP-INT-008)', () => {
    const refs: string[] = [];
    JSON.stringify(doc, (key, value: unknown) => {
      if (key === '$ref' && typeof value === 'string') refs.push(value);
      return value;
    });
    for (const ref of refs) expect(ref).not.toMatch(/Envelope|Draft|Inbound|envelope\.schema/);
    expect(Object.keys(doc.components.schemas.BootstrapRequest.properties as Json)).not.toContain(
      'envelope',
    );
    for (const path of [BOOTSTRAP, RENEWAL])
      expect(op(path).description).toContain('Carries no envelope.');
  });

  it('the material: at most 256 characters of the credential syntax, its prefix unchecked (D-AC-04)', () => {
    const ok = (secret: string) =>
      valid('data-gateway#BootstrapRequest', { agent: 'a', secret, instance: 'a-1' });
    expect(ok('soorma_rs_' + 'A'.repeat(246))).toBe(true);
    expect(ok('soorma_rs_' + 'A'.repeat(247))).toBe(false);
    expect(ok('soorma_em_AAAA')).toBe(true);
    expect(ok('no-prefix')).toBe(true);
    expect(ok('')).toBe(false);
    expect(ok('soorma_rs_ AAAA')).toBe(false);
  });

  it('statuses: bootstrap never answers 401; renewal never 403 or 429', () => {
    expect(Object.keys(op(BOOTSTRAP).responses as Json).sort()).toEqual([
      '200',
      '400',
      '403',
      '413',
      '429',
      '500',
      '503',
    ]);
    expect(Object.keys(op(RENEWAL).responses as Json).sort()).toEqual([
      '200',
      '400',
      '401',
      '413',
      '500',
      '503',
    ]);
  });

  it('every response carries the Soorma headers; 401 alone WWW-Authenticate; 429 and 503 Retry-After', () => {
    for (const path of [BOOTSTRAP, RENEWAL]) {
      const o = op(path);
      for (const status of Object.keys(o.responses as Json)) {
        const headers = Object.keys((response(o, status).headers ?? {}) as Json);
        expect(headers, `${path} ${status}`).toEqual(
          expect.arrayContaining(['Soorma-Contract-Version', 'Soorma-Request-Id']),
        );
        if (status === '401') expect(headers).toContain('WWW-Authenticate');
        else expect(headers).not.toContain('WWW-Authenticate');
        if (status === '429' || status === '503') expect(headers).toContain('Retry-After');
      }
    }
  });

  it('both 200s are the agent credential, not cacheable (D-AC-24)', () => {
    for (const path of [BOOTSTRAP, RENEWAL]) {
      const ok = op(path).responses['200'] as Json;
      expect(Object.keys(ok.headers as Json)).toContain('Cache-Control');
      expect(ok.content['application/json'].schema).toEqual({
        $ref: '#/components/schemas/AgentCredential',
      });
    }
    expect([...(doc.components.schemas.AgentCredential.required as string[])].sort()).toEqual([
      'agent',
      'credential',
      'environment',
      'expiresAt',
      'instance',
    ]);
  });

  it('a body violating the schema is refused by the validator', () => {
    expect(
      valid('data-gateway#BootstrapRequest', fixture('data-gateway/BootstrapRequest/valid/sample')),
    ).toBe(true);
    for (const name of ['extra-field', 'draft-envelope', 'no-instance', 'no-secret'])
      expect(
        valid(
          'data-gateway#BootstrapRequest',
          fixture(`data-gateway/BootstrapRequest/invalid/${name}`),
        ),
        name,
      ).toBe(false);
  });

  it('has valid and invalid fixtures for each body, and each validates as expected', () => {
    const fixtures = loadFixtures();
    for (const name of ['BootstrapRequest', 'AgentCredential']) {
      const of = fixtures.filter((f) => f.schema === `data-gateway#${name}`);
      expect(
        of.some((f) => f.expectedValid),
        name,
      ).toBe(true);
      expect(
        of.some((f) => !f.expectedValid),
        name,
      ).toBe(true);
      for (const f of of) expect(valid(f.schema, f.data), f.path).toBe(f.expectedValid);
    }
  });
});

describe('TC-AC-044: each surface document holds one face only (I6)', () => {
  it("S3's document holds no control-face operation, and accepts only the agent credential", () => {
    expect(operationIds(doc).sort()).toEqual(['exchangeBootstrap', 'renewAgentCredential']);
    for (const item of Object.values(doc.paths as Json))
      for (const o of Object.values(item as Json)) {
        const schemes = JSON.stringify((o as Json).security ?? []);
        expect(schemes).not.toContain('environmentCredential');
        expect(schemes).not.toContain('signIn');
      }
  });

  it("S2's document holds no data-face operation, and accepts no agent credential", () => {
    const ids = operationIds(control);
    expect(ids).not.toContain('exchangeBootstrap');
    expect(ids).not.toContain('renewAgentCredential');
    for (const path of Object.keys(control.paths as Json))
      expect(path.startsWith('/agent-credentials')).toBe(false);
    expect(JSON.stringify(control.paths)).not.toContain('agentCredential');
  });
});

describe("TC-AC-045: the changed contract passes U1's checks, and every change is classified", () => {
  it('the structural checks and the compatibility check find nothing', () => {
    expect(contractFindings(contract)).toEqual([]);
    const classifications = parseClassifications(readChangelog());
    expect(compatFindings(loadFixtures(), validator.validate, classifications)).toEqual([]);
  });

  it('authentication_failed is in the shared contract, widened to an agent instance at bootstrap', () => {
    const { anyOf } = component('schemas', 'ProblemCode') as { anyOf: { enum: string[] }[] };
    expect(anyOf[0]!.enum).toContain('authentication_failed');
    const row = errorsText.split('\n').find((l) => l.startsWith('| `authentication_failed`'))!;
    expect(row).toMatch(/\| 403 /);
    expect(row).toContain('a human on sign-in, first authentication, or material change');
    expect(row).toContain('an agent instance at bootstrap');
    expect(row).toContain('One code for every cause');
  });

  it("errors.md states bootstrap's order: schema, then the bound, before any material", () => {
    const order = errors.slice(errors.indexOf('## Check order'));
    expect(order).toContain(
      'At bootstrap, the body schema (step 6) is checked before the abuse bound',
    );
    expect(order).toContain('before the material is');
  });

  it('identifiers.md: an instance identifier is asserted, recorded, never enforced unique', () => {
    expect(identifiers).toContain("An agent instance identifier is the agent's own assertion");
    expect(identifiers).toContain('never enforces it unique');
    expect(identifiers).not.toMatch(/an environment for agents, instances, and/);
  });

  it('CHANGELOG.md records the surface and each statement as compatible', () => {
    const section = changelog.slice(changelog.indexOf('### Added by U6 `agent-credentials`'));
    expect(section.length).toBeGreaterThan(0);
    for (const name of [
      'data-gateway.openapi.yaml',
      'exchangeBootstrap',
      'renewAgentCredential',
      'authentication_failed',
      'identifiers.md',
      'Revocation and Lifetimes',
    ])
      expect(section).toContain(name);
    expect(section).toContain('Compatible: new operations');
    expect(section).toContain('Compatible: the code set is open');
    expect(section).toContain('Compatible: a statement');
  });
});
