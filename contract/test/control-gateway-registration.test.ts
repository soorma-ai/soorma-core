// SPDX-License-Identifier: Apache-2.0
// S2's registration operations in the contract (U5 agent-registration):
// TC-AR-022, 045; Functional Design §13.
import { describe, expect, it } from 'vitest';
import { parse } from 'yaml';
import { loadFixtures } from '../scripts/checks/compat.ts';
import { component, contractFile, convention, valid } from './helpers.ts';

type Json = Record<string, any>;

const doc = parse(contractFile('control-gateway.openapi.yaml')) as Json;
const errors = convention('errors.md');
const changelog = contractFile('CHANGELOG.md');
const VERSION_PARAM =
  'conventions/components.openapi.yaml#/components/parameters/SoormaContractVersion';

const operations: Record<string, { path: string; request: string; response: string }> = {
  registerAgent: {
    path: '/registrations',
    request: 'RegistrationRequest',
    response: 'Registration',
  },
  issueRegistrationSecret: {
    path: '/registration-secrets',
    request: 'RegistrationSecretRequest',
    response: 'RegistrationSecret',
  },
};

const operation = (id: string): Json => doc.paths[operations[id]!.path].post as Json;
const response = (op: Json, status: string): Json => {
  const r = op.responses[status] as Json;
  return typeof r.$ref === 'string'
    ? (doc.components.responses[r.$ref.split('/').pop()!] as Json)
    : r;
};

describe('TC-AR-022: the registration operations are defined in the contract', () => {
  it.each(Object.keys(operations))(
    '%s: a POST naming environmentCredential only, the version parameter, a body, and 200',
    (id) => {
      const op = operation(id);
      expect(op.operationId).toBe(id);
      expect(op.security).toEqual([{ environmentCredential: [] }]);
      expect(op.parameters).toEqual([{ $ref: VERSION_PARAM }]);
      expect(op.requestBody.content['application/json'].schema).toEqual({
        $ref: `#/components/schemas/${operations[id]!.request}`,
      });
      const statuses = Object.keys(op.responses as Json);
      expect(statuses.filter((s) => s.startsWith('2'))).toEqual(['200']);
      expect(statuses.sort()).toEqual(['200', '400', '401', '403', '409', '413', '500', '503']);
      expect(op.responses['200'].content['application/json'].schema).toEqual({
        $ref: `#/components/schemas/${operations[id]!.response}`,
      });
    },
  );

  it.each(Object.keys(operations))('%s: every response carries the Soorma headers', (id) => {
    const op = operation(id);
    for (const status of Object.keys(op.responses as Json)) {
      const headers = Object.keys((response(op, status).headers ?? {}) as Json);
      expect(headers, `${id} ${status}`).toEqual(
        expect.arrayContaining(['Soorma-Contract-Version', 'Soorma-Request-Id']),
      );
      if (status === '401') expect(headers).toContain('WWW-Authenticate');
      else expect(headers).not.toContain('WWW-Authenticate');
      if (status === '503') expect(headers).toContain('Retry-After');
    }
  });

  it('the secret response is not cacheable; the registration response needs no such header', () => {
    expect(
      Object.keys(operation('issueRegistrationSecret').responses['200'].headers as Json),
    ).toContain('Cache-Control');
    expect(Object.keys(operation('registerAgent').responses['200'].headers as Json)).not.toContain(
      'Cache-Control',
    );
  });

  it('no operation in the document accepts an agent credential (I6)', () => {
    for (const item of Object.values(doc.paths as Json))
      for (const op of Object.values(item as Json))
        expect(JSON.stringify((op as Json).security)).not.toContain('agentCredential');
  });

  it('has valid and invalid fixtures for each new body, and each validates as expected', () => {
    const fixtures = loadFixtures();
    for (const name of [
      'RegistrationRequest',
      'RegistrationSecretRequest',
      'Registration',
      'RegistrationSecret',
    ]) {
      const of = fixtures.filter((f) => f.schema === `control-gateway#${name}`);
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

  it('bounds a registration: at most 32 unique entries in each set, a closed body', () => {
    const many = (n: number) => Array.from({ length: n }, (_, i) => `x:p${i}`);
    const ok = (body: Json) => valid('control-gateway#RegistrationRequest', body);
    expect(
      ok({ agent: 'a', standingPermissions: many(32), reBroadeningDeclaration: many(32) }),
    ).toBe(true);
    expect(ok({ agent: 'a', standingPermissions: many(33) })).toBe(false);
    expect(ok({ agent: 'a', standingPermissions: [], reBroadeningDeclaration: many(33) })).toBe(
      false,
    );
    expect(ok({ agent: 'x'.repeat(64), standingPermissions: [] })).toBe(true);
    expect(ok({ agent: 'x'.repeat(65), standingPermissions: [] })).toBe(false);
  });
});

describe('TC-AR-045: the six codes are in the shared contract, and the changes are recorded', () => {
  const codes: [string, number][] = [
    ['human_only_permission', 400],
    ['declaration_outside_standing', 400],
    ['unknown_registration', 400],
    ['exceeds_sponsor_ceiling', 403],
    ['registration_exists', 409],
    ['secret_limit_reached', 409],
  ];

  it('ProblemCode lists them', () => {
    const { anyOf } = component('schemas', 'ProblemCode') as { anyOf: { enum: string[] }[] };
    expect(anyOf[0]!.enum).toEqual(expect.arrayContaining(codes.map(([c]) => c)));
  });

  it.each(codes)('errors.md lists %s with status %i', (code, status) => {
    expect(errors).toMatch(new RegExp(`\\| \`${code}\` +\\| ${status} `));
  });

  it('errors.md states the check order for both operations, and the disclosure', () => {
    const order = errors.slice(errors.indexOf('## Check order'));
    for (const code of codes.map(([c]) => c)) expect(order).toContain(`\`${code}\``);
    expect(errors).toContain('whether a logical agent identifier is taken is learnable');
  });

  it('CHANGELOG.md records both operations and the six codes as compatible', () => {
    const section = changelog.slice(changelog.indexOf('### Added by U5 `agent-registration`'));
    expect(section.length).toBeGreaterThan(0);
    for (const name of ['registerAgent', 'issueRegistrationSecret', ...codes.map(([c]) => c)])
      expect(section).toContain(name);
    expect(section).toContain('Compatible: new operations');
    expect(section).toContain('Compatible: the code set is open');
  });
});
