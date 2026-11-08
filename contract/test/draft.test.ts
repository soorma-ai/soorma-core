// SPDX-License-Identifier: Apache-2.0
// The draft and forwarded context: TC-WC-007, 010, 012 to 015, 020, 022.
import { describe, expect, it } from 'vitest';
import { component, copy, errors, samples, schemaDef, valid } from './helpers.ts';
import type { ContractSchema } from '../scripts/validator.ts';

const STAMPED: Record<string, unknown> = {
  envelopeVersion: 1,
  scope: { organization: 'o1', project: 'p1', environment: 'e1' },
  originMode: 'autonomous',
  delegatingPrincipal: { organization: 'o1', principal: 'h@example.com' },
  actorChain: [{ agent: 'agent-a', instance: 'host-1' }],
  reBroadening: [{ hop: 0 }],
};

describe('TC-WC-007: the draft schema does not admit platform-stamped fields', () => {
  it.each(Object.keys(STAMPED))(
    'refuses %s through its own prohibition, not additionalProperties',
    (field) => {
      const d = copy(samples.draft);
      d[field] = STAMPED[field];
      const found = errors('Draft', d);
      expect(found).toContainEqual(
        expect.objectContaining({ path: `/${field}`, keyword: 'false schema' }),
      );
      expect(found.some((e) => e.keyword === 'additionalProperties')).toBe(false);
    },
  );
});

describe('TC-WC-010: the client contract version is distinct from the envelope version', () => {
  it('declares them as two properties of different types', () => {
    const draftProps = schemaDef('envelope.schema.json', 'Draft').properties as Record<
      string,
      unknown
    >;
    expect(draftProps.clientContractVersion).toEqual({ $ref: '#/$defs/ContractVersion' });
    expect(schemaDef('envelope.schema.json', 'ContractVersion')).toMatchObject({ type: 'string' });
    const envelopeProps = schemaDef('envelope.schema.json', 'Envelope').properties as Record<
      string,
      unknown
    >;
    expect(envelopeProps.envelopeVersion).toMatchObject({ type: 'integer', minimum: 1 });
  });

  it('requires clientContractVersion and refuses envelopeVersion in a draft', () => {
    const missing = copy(samples.draft);
    delete missing.clientContractVersion;
    expect(valid('Draft', missing)).toBe(false);
    const withEnvelopeVersion = copy(samples.draft);
    withEnvelopeVersion.envelopeVersion = 1;
    expect(errors('Draft', withEnvelopeVersion)).toContainEqual(
      expect.objectContaining({ path: '/envelopeVersion', keyword: 'false schema' }),
    );
  });
});

describe('TC-WC-012: a stamped field takes precedence over an unknown field', () => {
  it('reports the stamped field and the unknown field separately', () => {
    const d = copy(samples.draft);
    d.scope = STAMPED.scope;
    d['x-future'] = 1;
    const found = errors('Draft', d);
    expect(found).toContainEqual(
      expect.objectContaining({ path: '/scope', keyword: 'false schema' }),
    );
    expect(found).toContainEqual(
      expect.objectContaining({
        path: '',
        keyword: 'additionalProperties',
        params: { additionalProperty: 'x-future' },
      }),
    );
  });
});

describe('TC-WC-013: the draft is closed at its top level', () => {
  it.each([
    ['x-future', 1],
    ['priority', 'high'],
  ])('refuses %s, naming it', (field, value) => {
    const d = copy(samples.draft);
    d[field] = value;
    expect(errors('Draft', d)).toContainEqual(
      expect.objectContaining({
        keyword: 'additionalProperties',
        params: { additionalProperty: field },
      }),
    );
  });

  it('accepts the sample and forwarding drafts', () => {
    expect(valid('Draft', samples.draft)).toBe(true);
    expect(valid('Draft', samples.forwarding)).toBe(true);
  });
});

describe('TC-WC-014: a draft missing or malforming a required field fails', () => {
  it.each(['clientContractVersion', 'traceContext'])('without %s', (field) => {
    const d = copy(samples.draft);
    delete d[field];
    expect(errors('Draft', d)).toContainEqual(
      expect.objectContaining({ params: { missingProperty: field } }),
    );
  });

  it.each([1, 'v0.1'])('clientContractVersion %s', (value) => {
    const d = copy(samples.draft);
    d.clientContractVersion = value;
    expect(errors('Draft', d).some((e) => e.path === '/clientContractVersion')).toBe(true);
  });
});

describe('TC-WC-015: the forwarded context is a closed wrapper around an open envelope', () => {
  it('accepts the forwarding draft, and unknown fields inside the forwarded envelope', () => {
    expect(valid('Draft', samples.forwarding)).toBe(true);
    const top = copy(samples.forwarding);
    top.inbound.envelope['x-future'] = 1;
    expect(valid('Draft', top)).toBe(true);
    const scope = copy(samples.forwarding);
    scope.inbound.envelope.scope['x-future'] = 1;
    expect(valid('Draft', scope)).toBe(true);
  });

  it('refuses an unknown field on the wrapper, a missing part, or a non-string seal', () => {
    const extra = copy(samples.forwarding);
    extra.inbound['x-future'] = 1;
    expect(errors('Draft', extra)).toContainEqual(
      expect.objectContaining({ path: '/inbound', params: { additionalProperty: 'x-future' } }),
    );
    for (const part of ['seal', 'envelope']) {
      const missing = copy(samples.forwarding);
      delete missing.inbound[part];
      expect(errors('Draft', missing)).toContainEqual(
        expect.objectContaining({ path: '/inbound', params: { missingProperty: part } }),
      );
    }
    const numeric = copy(samples.forwarding);
    numeric.inbound.seal = 1;
    expect(errors('Draft', numeric).some((e) => e.path === '/inbound/seal')).toBe(true);
  });

  it('bounds the seal in inbound, and leaves it a plain string in the Delivery', () => {
    expect(schemaDef('envelope.schema.json', 'Inbound').properties).toMatchObject({
      seal: { type: 'string', maxLength: 1024 },
    });
    const seal = (
      schemaDef('delivery.schema.json', 'Delivery').properties as Record<
        string,
        Record<string, unknown>
      >
    ).seal;
    expect(seal).toMatchObject({ type: 'string' });
    expect(seal).not.toHaveProperty('maxLength');
  });
});

describe('TC-WC-020: trace context is validated for well-formedness only', () => {
  const withTrace = (traceContext: Record<string, unknown>): Record<string, unknown> => ({
    ...samples.draft,
    traceContext,
  });
  const tp = '00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01';

  it('accepts version 00 and a higher version with an extra field', () => {
    expect(valid('Draft', samples.draft)).toBe(true);
    expect(
      valid(
        'Draft',
        withTrace({ traceparent: '01-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01-extra' }),
      ),
    ).toBe(true);
  });

  it.each([
    ['uppercase hex', '00-4BF92F3577B34DA6A3CE929D0E0E4736-00F067AA0BA902B7-01'],
    ['a 31-digit trace id', '00-4bf92f3577b34da6a3ce929d0e0e473-00f067aa0ba902b7-01'],
    ['a 15-digit parent id', '00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b-01'],
    ['no flags', '00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7'],
    ['version 00 with an extra field', `${tp}-extra`],
  ])('refuses %s', (_name, traceparent) => {
    expect(valid('Draft', withTrace({ traceparent }))).toBe(false);
  });

  it('requires traceparent', () => {
    expect(valid('Draft', withTrace({}))).toBe(false);
  });

  it('accepts a 512-character tracestate and refuses 513', () => {
    expect(valid('Draft', withTrace({ traceparent: tp, tracestate: `k=${'v'.repeat(510)}` }))).toBe(
      true,
    );
    expect(valid('Draft', withTrace({ traceparent: tp, tracestate: `k=${'v'.repeat(511)}` }))).toBe(
      false,
    );
  });
});

describe('TC-WC-022: request-side identifiers follow their kind', () => {
  const ulid = '01J9Z3K8M4N5P6Q7R8S9T0V1W2';
  const cases: [ContractSchema, unknown[], unknown[]][] = [
    [
      'ConfiguredIdentifier',
      ['o1', 'agent.a_1~x-2', ulid, 'a'.repeat(64)],
      ['', '-leading', 'has space', 'a:b', 'a/b', 'a'.repeat(65)],
    ],
    ['LogicalAgentIdentifier', ['agent.a_1~x-2', 'a'.repeat(64)], ['', 'a'.repeat(65), 'a:b']],
    ['PlatformReference', [ulid, 'a'.repeat(64)], ['', 'a'.repeat(65), 'a/b']],
    [
      'InstanceIdentifier',
      ['host-1', 'host-1:4100', '3f2c6b8e-1d4a-4c2b-9e7f-0a1b2c3d4e5f', 'a'.repeat(128)],
      [':leading', 'has space', 'a'.repeat(129)],
    ],
    [
      'HumanPrincipalIdentifier',
      [
        'h@example.com',
        'first.last+tag@example.co',
        'issuer|subject',
        'urn:x:y',
        "o'brien@example.com",
        'a'.repeat(256),
      ],
      [
        '',
        'a b@example.com',
        '<h@example.com>',
        'a,b',
        'a;b',
        'a"b',
        'a\\b',
        'ü@example.com',
        'a'.repeat(257),
      ],
    ],
    [
      'PermissionIdentifier',
      ['agent:register', 'event:publish'],
      ['agent', 'Agent:register', 'agent:', ':register', 'agent:Register', `a:${'b'.repeat(127)}`],
    ],
  ];

  it.each(cases)('%s', (schema, accept, reject) => {
    for (const value of accept)
      expect(valid(schema, value), `${schema} should accept ${String(value)}`).toBe(true);
    for (const value of reject)
      expect(valid(schema, value), `${schema} should refuse ${String(value)}`).toBe(false);
  });

  it('is case-sensitive and never normalizes: no pattern is case-insensitive, no definition trims', () => {
    for (const name of [
      'ConfiguredIdentifier',
      'LogicalAgentIdentifier',
      'PlatformReference',
      'InstanceIdentifier',
      'HumanPrincipalIdentifier',
      'PermissionIdentifier',
    ]) {
      const def = component('schemas', name);
      expect(Object.keys(def).sort()).toEqual([
        'description',
        'maxLength',
        'minLength',
        'pattern',
        'type',
      ]);
      expect(String(def.pattern)).not.toMatch(/\(\?i/);
    }
    expect(valid('ConfiguredIdentifier', ' o1')).toBe(false);
  });
});
