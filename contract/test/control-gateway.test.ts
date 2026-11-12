// SPDX-License-Identifier: Apache-2.0
// S2 control-gateway's operations in the contract: TC-EHA-024; and U4's
// additions to the shared contract (unknown_permission, unknown_principal;
// Functional Design §13).
import { describe, expect, it } from 'vitest';
import { parse } from 'yaml';
import { loadFixtures } from '../scripts/checks/compat.ts';
import { walkJson } from '../scripts/checks/model.ts';
import { receivedSide, requestSide } from '../scripts/checks/sides.ts';
import { component, contractFile, convention, valid } from './helpers.ts';

type Json = Record<string, any>;

const doc = parse(contractFile('control-gateway.openapi.yaml')) as Json;
const errors = convention('errors.md');
const VERSION_PARAM =
  'conventions/components.openapi.yaml#/components/parameters/SoormaContractVersion';

const operations: Record<string, { path: string; security: unknown; success: string }> = {
  issueEnvironmentCredential: {
    path: '/environment-credentials',
    security: [{ signIn: [] }],
    success: '200',
  },
  renewEnvironmentCredential: {
    path: '/environment-credentials/current/renewal',
    security: [{ environmentCredential: [] }],
    success: '200',
  },
  endEnvironmentCredential: {
    path: '/environment-credentials/current/end',
    security: [{ environmentCredential: [] }],
    success: '204',
  },
  grantToHuman: { path: '/grants', security: [{ environmentCredential: [] }], success: '200' },
};

function operation(id: string): Json {
  return doc.paths[operations[id]!.path].post as Json;
}

function response(op: Json, status: string): Json {
  const r = op.responses[status] as Json;
  return typeof r.$ref === 'string'
    ? (doc.components.responses[r.$ref.split('/').pop()!] as Json)
    : r;
}

describe('TC-EHA-024: S2 operations are defined in the contract and validated against it', () => {
  it('defines exactly the four operations, and the two of U5, each a POST with its operationId', () => {
    const found: string[] = [];
    for (const [path, item] of Object.entries(doc.paths as Json)) {
      for (const [method, op] of Object.entries(item as Json)) {
        expect(method).toBe('post');
        found.push(`${(op as Json).operationId} ${path}`);
      }
    }
    expect(found.sort()).toEqual(
      [
        ...Object.entries(operations).map(([id, { path }]) => `${id} ${path}`),
        // U5's two (D-CG-AR-15), checked in control-gateway-registration.test.ts
        'issueRegistrationSecret /registration-secrets',
        'registerAgent /registrations',
      ].sort(),
    );
  });

  it.each(Object.keys(operations))('%s names exactly one security scheme', (id) => {
    expect(operation(id).security).toEqual(operations[id]!.security);
  });

  it.each(Object.keys(operations))('%s answers its success status (D-EHA-25)', (id) => {
    const statuses = Object.keys(operation(id).responses as Json).filter((s) => s.startsWith('2'));
    expect(statuses).toEqual([operations[id]!.success]);
  });

  it('only grantToHuman takes a body (D-EHA-24)', () => {
    for (const id of Object.keys(operations))
      expect('requestBody' in operation(id), id).toBe(id === 'grantToHuman');
  });

  it('declares no document-wide security', () => {
    expect(doc).not.toHaveProperty('security');
  });

  it.each(Object.keys(operations))('%s takes Soorma-Contract-Version by reference', (id) => {
    expect(operation(id).parameters).toEqual([{ $ref: VERSION_PARAM }]);
  });

  it('carries no envelope: no draft, inbound, envelope, or Delivery anywhere', () => {
    walkJson(doc, '', (key, value) => {
      if (key === '$ref' && typeof value === 'string')
        expect(value).not.toMatch(/(Draft|Inbound|Envelope|Delivery)$/);
    });
  });

  it('every response carries Soorma-Contract-Version and Soorma-Request-Id', () => {
    for (const id of Object.keys(operations)) {
      const op = operation(id);
      for (const status of Object.keys(op.responses as Json)) {
        const headers = Object.keys((response(op, status).headers ?? {}) as Json);
        expect(headers, `${id} ${status}`).toEqual(
          expect.arrayContaining(['Soorma-Contract-Version', 'Soorma-Request-Id']),
        );
      }
    }
  });

  it('a 401 carries WWW-Authenticate, a 403 never does, and a 503 carries Retry-After', () => {
    for (const id of Object.keys(operations)) {
      const op = operation(id);
      for (const status of Object.keys(op.responses as Json)) {
        const headers = Object.keys((response(op, status).headers ?? {}) as Json);
        if (status === '401') expect(headers).toContain('WWW-Authenticate');
        else expect(headers, `${id} ${status}`).not.toContain('WWW-Authenticate');
        if (status === '503') expect(headers).toContain('Retry-After');
      }
    }
  });

  it('only issuance and grantToHuman can answer 403', () => {
    for (const id of Object.keys(operations))
      expect('403' in (operation(id).responses as Json), id).toBe(
        id === 'issueEnvironmentCredential' || id === 'grantToHuman',
      );
  });

  it('classifies every control-gateway definition, and closes every request-side object', () => {
    const schemas = doc.components.schemas as Json;
    for (const [name, schema] of Object.entries(schemas)) {
      const at = `control-gateway.openapi.yaml#/components/schemas/${name}`;
      const isRequest = requestSide.includes(at);
      expect(isRequest !== receivedSide.includes(at), name).toBe(true);
      if ((schema as Json).type === 'object')
        expect((schema as Json).additionalProperties, name).toBe(!isRequest);
    }
  });

  it('has valid and invalid fixtures for each request body and response body', () => {
    const fixtures = loadFixtures();
    for (const name of ['GrantRequest', 'EnvironmentCredentialResponse', 'Grant']) {
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

  it('bounds a grant: 1 to 32 unique permissions, each a PermissionIdentifier', () => {
    const target = { organization: 'o1', principal: 'h@example.com' };
    const many = (n: number) => Array.from({ length: n }, (_, i) => `x:p${i}`);
    expect(valid('control-gateway#GrantRequest', { target, permissions: many(32) })).toBe(true);
    expect(valid('control-gateway#GrantRequest', { target, permissions: many(33) })).toBe(false);
    expect(valid('control-gateway#GrantRequest', { target, permissions: [] })).toBe(false);
  });
});

describe("TC-EHA-024: U4's two codes are in the shared contract (Functional Design §13)", () => {
  it('ProblemCode lists unknown_permission and unknown_principal', () => {
    const { anyOf } = component('schemas', 'ProblemCode') as { anyOf: { enum: string[] }[] };
    const codes = anyOf[0]!.enum;
    expect(codes).toEqual(expect.arrayContaining(['unknown_permission', 'unknown_principal']));
  });

  it('errors.md gives both 400, with their pointers', () => {
    expect(errors).toMatch(/\| `unknown_permission` +\| 400 /);
    expect(errors).toMatch(/\| `unknown_principal` +\| 400 /);
  });
});
