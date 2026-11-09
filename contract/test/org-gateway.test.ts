// SPDX-License-Identifier: Apache-2.0
// S1 org-gateway's operations in the contract: TC-OI-022 (step 1), 023, 025; and
// U2's additions to the shared contract (business-rules §10; amendment A5).
import { describe, expect, it } from 'vitest';
import { parse } from 'yaml';
import { loadFixtures } from '../scripts/checks/compat.ts';
import { walkJson } from '../scripts/checks/model.ts';
import { receivedSide, requestSide } from '../scripts/checks/sides.ts';
import { component, contractFile, convention, valid } from './helpers.ts';

type Json = Record<string, any>;

const doc = parse(contractFile('org-gateway.openapi.yaml')) as Json;
const errors = convention('errors.md');
const VERSION_PARAM =
  'conventions/components.openapi.yaml#/components/parameters/SoormaContractVersion';

const operations: Record<string, { path: string; security: unknown }> = {
  firstAuthenticate: { path: '/first-authentication', security: undefined },
  authenticate: { path: '/sign-ins', security: undefined },
  renewSignIn: { path: '/sign-ins/current/renewal', security: [{ signIn: [] }] },
  endSignIn: { path: '/sign-ins/current/end', security: [{ signIn: [] }] },
  changeMaterial: { path: '/material-changes', security: undefined },
};

function operation(id: string): Json {
  const { path } = operations[id]!;
  return doc.paths[path].post as Json;
}

/** Resolves a response, following one local `$ref` into components.responses. */
function response(op: Json, status: string): Json {
  const r = op.responses[status] as Json;
  return typeof r.$ref === 'string'
    ? (doc.components.responses[r.$ref.split('/').pop()!] as Json)
    : r;
}

describe('TC-OI-023: S1 operations are defined in the contract and validated against it', () => {
  it('defines exactly the five operations, each a POST with its operationId', () => {
    const found: string[] = [];
    for (const [path, item] of Object.entries(doc.paths as Json)) {
      for (const [method, op] of Object.entries(item as Json)) {
        expect(method).toBe('post');
        found.push(`${(op as Json).operationId} ${path}`);
      }
    }
    expect(found.sort()).toEqual(
      Object.entries(operations)
        .map(([id, { path }]) => `${id} ${path}`)
        .sort(),
    );
  });

  it.each(Object.keys(operations))('%s names its security scheme, or none', (id) => {
    expect(operation(id).security).toEqual(operations[id]!.security);
  });

  it('declares no document-wide security, so an unlisted operation names none', () => {
    expect(doc).not.toHaveProperty('security');
  });

  it.each(Object.keys(operations))('%s takes Soorma-Contract-Version by reference', (id) => {
    expect(operation(id).parameters).toEqual([{ $ref: VERSION_PARAM }]);
  });

  it('carries no envelope: no draft, inbound, envelope, or Delivery anywhere (L1-25)', () => {
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

  it('a 401 carries WWW-Authenticate, a 403 never does, and a 429 and a 503 carry Retry-After', () => {
    for (const id of Object.keys(operations)) {
      const op = operation(id);
      for (const status of Object.keys(op.responses as Json)) {
        const headers = Object.keys((response(op, status).headers ?? {}) as Json);
        if (status === '401') expect(headers).toContain('WWW-Authenticate');
        else expect(headers, `${id} ${status}`).not.toContain('WWW-Authenticate');
        if (status === '429' || status === '503') expect(headers).toContain('Retry-After');
      }
    }
  });

  it('only the operations naming a security scheme can answer 401', () => {
    for (const id of Object.keys(operations)) {
      const has401 = '401' in (operation(id).responses as Json);
      expect(has401, id).toBe(operations[id]!.security !== undefined);
    }
  });

  it('classifies every org-gateway definition, and closes every request-side object', () => {
    const schemas = doc.components.schemas as Json;
    for (const [name, schema] of Object.entries(schemas)) {
      const at = `org-gateway.openapi.yaml#/components/schemas/${name}`;
      const isRequest = requestSide.includes(at);
      expect(isRequest !== receivedSide.includes(at), name).toBe(true);
      if ((schema as Json).type === 'object')
        expect((schema as Json).additionalProperties, name).toBe(!isRequest);
    }
  });

  it('has valid and invalid fixtures for each request body and response body', () => {
    const fixtures = loadFixtures();
    for (const name of [
      'FirstAuthenticateRequest',
      'AuthenticateRequest',
      'ChangeMaterialRequest',
      'SignInResponse',
      'FirstAuthenticateResponse',
      'ChangeMaterialResponse',
    ]) {
      const of = fixtures.filter((f) => f.schema === `org-gateway#${name}`);
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

  it('bounds K at 1 to 1024 code points raw, and enrollment material at 256 with its prefix', () => {
    const k = (s: string): boolean =>
      valid('org-gateway#AuthenticateRequest', {
        principal: { organization: 'o1', principal: 'h@example.com' },
        secret: s,
      });
    expect(k('😀'.repeat(1024))).toBe(true);
    expect(k('😀'.repeat(1025))).toBe(false);
    expect(k('')).toBe(false);
    expect(valid('org-gateway#EnrollmentMaterial', `soorma_em_${'a'.repeat(246)}`)).toBe(true);
    expect(valid('org-gateway#EnrollmentMaterial', `soorma_em_${'a'.repeat(247)}`)).toBe(false);
    expect(valid('org-gateway#EnrollmentMaterial', 'soorma_si_abc')).toBe(false);
  });
});

describe('TC-OI-025: material of a class core does not accept is rejected', () => {
  it('accepts only totp as a second-factor type, and no external material', () => {
    expect(valid('org-gateway#AuthenticatorTypeInput', 'totp')).toBe(true);
    expect(valid('org-gateway#AuthenticatorTypeInput', 'webauthn')).toBe(false);
    expect(
      valid('org-gateway#AuthenticateRequest', {
        principal: { organization: 'o1', principal: 'h@example.com' },
        secret: 'x',
        external: { issuer: 'idp', assertion: 'a' },
      }),
    ).toBe(false);
  });
});

describe('TC-OI-022 step 1: no S1 operation removes a principal', () => {
  it('has no DELETE, and no path naming a principal', () => {
    for (const [path, item] of Object.entries(doc.paths as Json)) {
      expect(Object.keys(item as Json)).not.toContain('delete');
      expect(path).not.toMatch(/principal/i);
    }
  });
});

describe("U2's additions to the shared contract (business-rules §10; A5)", () => {
  it.each([
    ['authentication_failed', 403],
    ['second_factor_enrollment_required', 403],
    ['second_factor_not_confirmed', 403],
    ['secret_rejected', 400],
  ])('lists %s with status %i, in ProblemCode and errors.md', (code, status) => {
    expect(errors).toMatch(new RegExp(`\\| \`${code}\` \\| ${status} \\|`));
    const [known] = component('schemas', 'ProblemCode').anyOf as [{ enum: string[] }];
    expect(known.enum).toContain(code);
  });

  it('gives no detail for authentication_failed and second_factor_not_confirmed', () => {
    expect(errors).toMatch(/\| `authentication_failed` \| 403 \| [^|]+ \| None \|/);
    expect(errors).toMatch(/\| `second_factor_not_confirmed` \| 403 \| [^|]+ \| None \|/);
  });

  it('widens too_many_attempts to material change, and states the 403s carry no WWW-Authenticate', () => {
    expect(errors).toMatch(
      /\| `too_many_attempts` \| 429 \| The abuse bound on bootstrap, sign-in, first authentication, or material change \|/,
    );
    expect(errors).toContain('A 403 carries no `WWW-Authenticate`');
  });

  it('types ProblemFieldError.reason as the open enumeration SecretRejectedReason', () => {
    expect(component('schemas', 'SecretRejectedReason')).toEqual({
      description: expect.any(String),
      anyOf: [
        {
          enum: [
            'too_short',
            'too_long',
            'disallowed_character',
            'breached',
            'reused',
            'context_word',
          ],
        },
        { type: 'string' },
      ],
    });
    const problem = (reason: unknown): boolean =>
      valid('Problem', {
        code: 'secret_rejected',
        status: 400,
        errors: [{ pointer: '/newSecret', reason }],
      });
    expect(problem('context_word')).toBe(true);
    expect(problem('a_future_reason')).toBe(true);
    expect(problem(3)).toBe(false);
  });

  it('defines HumanPrincipalReferenceInput closed and patterned, and HumanPrincipalReference open', () => {
    const p = { organization: 'o1', principal: 'h@example.com' };
    expect(valid('HumanPrincipalReferenceInput', p)).toBe(true);
    expect(valid('HumanPrincipalReferenceInput', { ...p, x: 1 })).toBe(false);
    expect(valid('HumanPrincipalReferenceInput', { ...p, organization: '-o' })).toBe(false);
    expect(valid('HumanPrincipalReference', { ...p, x: 1 })).toBe(true);
    expect(valid('HumanPrincipalReference', { organization: '-o', principal: 'hé' })).toBe(true);
  });
});
