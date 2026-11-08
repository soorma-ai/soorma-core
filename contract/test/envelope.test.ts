// SPDX-License-Identifier: Apache-2.0
// The envelope schema: TC-WC-001, 006, 008, 016 to 019, 021.
import { describe, expect, it } from 'vitest';
import { walkSchema } from '../scripts/checks/model.ts';
import { copy, errors, samples, schemaDef, valid } from './helpers.ts';

const chain = (n: number): { agent: string; instance: string }[] =>
  Array.from({ length: n }, (_, i) => ({ agent: `agent-${i}`, instance: `host-${i}` }));

describe('TC-WC-001: a well-formed envelope validates', () => {
  it('accepts the sample, delegated, and re-broadened envelopes', () => {
    expect(valid('Envelope', samples.envelope)).toBe(true);
    expect(valid('Envelope', samples.delegated)).toBe(true);
    expect(valid('Envelope', samples.reBroadened)).toBe(true);
  });

  it('declares exactly the seven fields of PF §7b, and no seal', () => {
    const properties = Object.keys(
      schemaDef('envelope.schema.json', 'Envelope').properties as object,
    );
    expect(properties.sort()).toEqual(
      [
        'actorChain',
        'delegatingPrincipal',
        'envelopeVersion',
        'originMode',
        'reBroadening',
        'scope',
        'traceContext',
      ].sort(),
    );
  });
});

describe('TC-WC-006: an envelope missing a required field fails', () => {
  it.each(['envelopeVersion', 'scope', 'originMode', 'actorChain', 'traceContext'])(
    'without %s',
    (field) => {
      const e = copy(samples.envelope);
      delete e[field];
      expect(errors('Envelope', e)).toContainEqual(
        expect.objectContaining({
          path: '',
          keyword: 'required',
          params: { missingProperty: field },
        }),
      );
    },
  );

  it.each(['organization', 'project', 'environment'])('without scope.%s', (part) => {
    const e = copy(samples.envelope);
    delete e.scope[part];
    expect(errors('Envelope', e)).toContainEqual(
      expect.objectContaining({ path: '/scope', params: { missingProperty: part } }),
    );
  });

  it.each(['agent', 'instance'])('without actorChain[0].%s', (part) => {
    const e = copy(samples.envelope);
    delete e.actorChain[0][part];
    expect(errors('Envelope', e)).toContainEqual(
      expect.objectContaining({ path: '/actorChain/0', params: { missingProperty: part } }),
    );
  });
});

describe('TC-WC-008: the envelope is open at every level; the draft traceContext is closed', () => {
  it('accepts x-future at the top level, in scope, in an actor reference', () => {
    const top = copy(samples.envelope);
    top['x-future'] = { any: 'value' };
    expect(valid('Envelope', top)).toBe(true);
    const scope = copy(samples.envelope);
    scope.scope['x-future'] = 1;
    expect(valid('Envelope', scope)).toBe(true);
    const actor = copy(samples.envelope);
    actor.actorChain[0]['x-future'] = 1;
    expect(valid('Envelope', actor)).toBe(true);
  });

  it('accepts x-future in delegatingPrincipal, a re-broadening record, and traceContext', () => {
    const d = copy(samples.delegated);
    d.delegatingPrincipal['x-future'] = 1;
    expect(valid('Envelope', d)).toBe(true);
    const r = copy(samples.reBroadened);
    r.reBroadening[0]['x-future'] = 1;
    expect(valid('Envelope', r)).toBe(true);
    const t = copy(samples.envelope);
    t.traceContext['x-future'] = 1;
    expect(valid('Envelope', t)).toBe(true);
  });

  it("refuses x-future in a draft's traceContext, as an additional property", () => {
    const draft = copy(samples.draft);
    draft.traceContext['x-future'] = 1;
    expect(errors('Draft', draft)).toContainEqual(
      expect.objectContaining({
        path: '/traceContext',
        keyword: 'additionalProperties',
        params: { additionalProperty: 'x-future' },
      }),
    );
  });
});

describe('TC-WC-016: the delegating principal is present exactly when origin is delegated', () => {
  it('requires it when delegated', () => {
    const d = copy(samples.delegated);
    delete d.delegatingPrincipal;
    expect(valid('Envelope', d)).toBe(false);
  });

  it('forbids it when autonomous', () => {
    const e = copy(samples.envelope);
    e.delegatingPrincipal = { organization: 'o1', principal: 'h@example.com' };
    expect(errors('Envelope', e)).toContainEqual(
      expect.objectContaining({ path: '/delegatingPrincipal', keyword: 'false schema' }),
    );
  });

  it.each(['principal', 'organization'])('requires delegatingPrincipal.%s', (part) => {
    const d = copy(samples.delegated);
    delete d.delegatingPrincipal[part];
    expect(valid('Envelope', d)).toBe(false);
  });

  it('accepts the delegated envelope unchanged', () => {
    expect(valid('Envelope', samples.delegated)).toBe(true);
  });

  it('leaves an unknown origin mode unconstrained (D-CG-02)', () => {
    const e = copy(samples.delegated);
    e.originMode = 'sponsored';
    expect(valid('Envelope', e)).toBe(true);
  });
});

describe('TC-WC-017: an unknown origin mode is not a schema error', () => {
  it('accepts another string', () => {
    const e = copy(samples.envelope);
    e.originMode = 'sponsored';
    expect(valid('Envelope', e)).toBe(true);
  });

  it.each([7, null])('refuses %s: open, but still a string', (value) => {
    const e = copy(samples.envelope);
    e.originMode = value;
    expect(valid('Envelope', e)).toBe(false);
  });
});

describe('TC-WC-018: the actor chain holds 1 to 32 entries', () => {
  it.each([
    [0, false],
    [1, true],
    [32, true],
    [33, false],
  ])('%i entries: valid is %s', (n, expected) => {
    const e = copy(samples.envelope);
    e.actorChain = chain(n);
    expect(valid('Envelope', e)).toBe(expected);
  });
});

describe('TC-WC-019: re-broadening records are well-formed', () => {
  it('refuses an empty list', () => {
    const r = copy(samples.reBroadened);
    r.reBroadening = [];
    expect(valid('Envelope', r)).toBe(false);
  });

  it.each([-1, 1.5, '1'])('refuses hop %s', (hop) => {
    const r = copy(samples.reBroadened);
    r.reBroadening = [{ hop }];
    expect(valid('Envelope', r)).toBe(false);
  });

  it('refuses a record without hop', () => {
    const r = copy(samples.reBroadened);
    r.reBroadening = [{}];
    expect(valid('Envelope', r)).toBe(false);
  });
});

describe('TC-WC-021: received identifiers are plain strings', () => {
  it('no identifier-bearing property of the envelope or Delivery carries a pattern, a maxLength, or a minLength above 1', () => {
    const definitions = [
      ['envelope.schema.json', 'Envelope'],
      ['envelope.schema.json', 'Scope'],
      ['envelope.schema.json', 'ActorReference'],
      ['envelope.schema.json', 'DelegatingPrincipalReference'],
      ['envelope.schema.json', 'ReceivedIdentifier'],
      ['delivery.schema.json', 'Delivery'],
    ] as const;
    for (const [file, name] of definitions) {
      walkSchema(schemaDef(file, name), '', (node, pointer) => {
        expect('pattern' in node, `${file} ${name}${pointer} has a pattern`).toBe(false);
        expect('maxLength' in node, `${file} ${name}${pointer} has a maxLength`).toBe(false);
        expect(typeof node.minLength === 'number' && node.minLength > 1).toBe(false);
      });
    }
  });

  it('accepts identifiers that would fail the request-side patterns', () => {
    const e = copy(samples.envelope);
    e.scope.environment = 'env with space';
    e.actorChain[0].agent = 'a'.repeat(300);
    expect(valid('Envelope', e)).toBe(true);
  });
});
