// SPDX-License-Identifier: Apache-2.0
// The shared components: TC-WC-009, 026, 027.
import { describe, expect, it } from 'vitest';
import { cloneContract, type Contract } from '../scripts/checks/model.ts';
import { checkShared } from '../scripts/checks/rules.ts';
import { component, componentsSection, contract, valid } from './helpers.ts';

function withSurface(document: unknown): Contract {
  const c = cloneContract(contract);
  c.documents.push({ path: 'event-ingest.openapi.yaml', data: document });
  return c;
}

const surface = (components: Record<string, unknown>): unknown => ({
  openapi: '3.1.1',
  info: { title: 'S4', version: '0.1.0' },
  paths: {},
  components,
});

describe('TC-WC-009: every surface document references the one envelope definition', () => {
  it('the shared components reference the schema files, never copies', () => {
    expect(component('schemas', 'Envelope')).toEqual({
      $ref: '../envelope.schema.json#/$defs/Envelope',
    });
    expect(component('schemas', 'Draft')).toEqual({ $ref: '../envelope.schema.json#/$defs/Draft' });
    expect(component('schemas', 'Delivery')).toEqual({
      $ref: '../delivery.schema.json#/$defs/Delivery',
    });
    expect(checkShared(contract)).toEqual([]);
  });

  it('accepts a surface document that references the shared definitions', () => {
    const doc = surface({
      schemas: {
        Draft: { $ref: 'envelope.schema.json#/$defs/Draft' },
        Delivery: { $ref: 'delivery.schema.json#/$defs/Delivery' },
        Problem: { $ref: 'conventions/components.openapi.yaml#/components/schemas/Problem' },
      },
      headers: {
        'Soorma-Request-Id': {
          $ref: 'conventions/components.openapi.yaml#/components/headers/Soorma-Request-Id',
        },
      },
    });
    expect(checkShared(withSurface(doc))).toEqual([]);
  });

  it('refuses an inline copy of the envelope, the draft, or the Problem', () => {
    const doc = surface({
      schemas: {
        PublishRequest: {
          type: 'object',
          properties: { clientContractVersion: { type: 'string' } },
        },
        Event: { type: 'object', properties: { actorChain: {}, originMode: {} } },
        Problem: { type: 'object', properties: { type: {}, title: {}, status: {}, instance: {} } },
      },
    });
    const messages = checkShared(withSurface(doc)).map((f) => `${f.location} ${f.message}`);
    expect(messages.some((m) => m.includes('PublishRequest') && m.includes('a draft'))).toBe(true);
    expect(messages.some((m) => m.includes('Event') && m.includes('an envelope'))).toBe(true);
    expect(
      messages.some((m) => m.includes('/components/schemas/Problem') && m.includes('a Problem')),
    ).toBe(true);
  });

  it('refuses a redefined shared header or security scheme', () => {
    const doc = surface({
      headers: { 'Soorma-Contract-Version': { schema: { type: 'string' } } },
      securitySchemes: { agentCredential: { type: 'http', scheme: 'bearer' } },
    });
    const locations = checkShared(withSurface(doc)).map((f) => f.location);
    expect(locations).toContain(
      'event-ingest.openapi.yaml#/components/headers/Soorma-Contract-Version',
    );
    expect(locations).toContain(
      'event-ingest.openapi.yaml#/components/securitySchemes/agentCredential',
    );
  });
});

describe('TC-WC-026: the security schemes', () => {
  it('defines exactly three, each HTTP bearer, with its prefix', () => {
    const schemes = componentsSection('securitySchemes');
    expect(Object.keys(schemes).sort()).toEqual([
      'agentCredential',
      'environmentCredential',
      'signIn',
    ]);
    const prefixes: Record<string, string> = {
      agentCredential: 'soorma_ac_',
      environmentCredential: 'soorma_ec_',
      signIn: 'soorma_si_',
    };
    for (const [name, scheme] of Object.entries(schemes)) {
      expect(scheme).toMatchObject({ type: 'http', scheme: 'bearer' });
      expect(String(scheme.description)).toContain(prefixes[name]);
    }
  });
});

describe('TC-WC-027: the shared headers are defined once', () => {
  it('defines Soorma-Contract-Version, Soorma-Request-Id, and Retry-After in the shared components', () => {
    expect(Object.keys(componentsSection('headers')).sort()).toEqual([
      'Retry-After',
      'Soorma-Contract-Version',
      'Soorma-Request-Id',
    ]);
    expect(component('parameters', 'SoormaContractVersion')).toMatchObject({
      name: 'Soorma-Contract-Version',
      in: 'header',
      required: true,
    });
  });

  it('states the rule for a call with both a draft and the header', () => {
    expect(String(component('parameters', 'SoormaContractVersion').description)).toContain(
      "must then equal the draft's clientContractVersion",
    );
  });

  it('accepts 0.1.0 and refuses v0.1.0 as a contract version', () => {
    expect(component('headers', 'Soorma-Contract-Version').schema).toEqual({
      $ref: '#/components/schemas/ContractVersion',
    });
    expect(valid('ContractVersion', '0.1.0')).toBe(true);
    expect(valid('ContractVersion', 'v0.1.0')).toBe(false);
  });

  it('types Soorma-Request-Id as a plain string, and ties it to the Problem instance', () => {
    const header = component('headers', 'Soorma-Request-Id');
    expect(header.schema).toEqual({ type: 'string' });
    expect(String(header.description)).toContain("Equal to the request id in a Problem's instance");
  });
});
