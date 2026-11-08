// SPDX-License-Identifier: Apache-2.0
// The Delivery: TC-WC-002, 023.
import { describe, expect, it } from 'vitest';
import { copy, errors, samples, schemaDef, valid } from './helpers.ts';

describe('TC-WC-002: a Delivery validates', () => {
  it('accepts the sample delivery', () => {
    expect(valid('Delivery', samples.delivery)).toBe(true);
  });

  it.each([[[1, 'two']], ['text'], [3], [true], [null]])('accepts a payload of %j', (payload) => {
    const d = copy(samples.delivery);
    d.payload = payload;
    expect(valid('Delivery', d)).toBe(true);
  });

  it('references the envelope definition, and types the seal as a string', () => {
    const props = schemaDef('delivery.schema.json', 'Delivery').properties as Record<
      string,
      unknown
    >;
    expect(props.envelope).toEqual({ $ref: 'envelope.schema.json#/$defs/Envelope' });
    expect(props.seal).toMatchObject({ type: 'string' });
  });
});

describe('TC-WC-023: a Delivery missing a field fails; a Delivery is open', () => {
  it.each(['envelope', 'seal', 'payload'])('refuses a Delivery without %s', (field) => {
    const d = copy(samples.delivery);
    delete d[field];
    expect(errors('Delivery', d)).toContainEqual(
      expect.objectContaining({ params: { missingProperty: field } }),
    );
  });

  it('refuses an envelope missing actorChain', () => {
    const d = copy(samples.delivery);
    delete d.envelope.actorChain;
    expect(errors('Delivery', d)).toContainEqual(
      expect.objectContaining({ path: '/envelope', params: { missingProperty: 'actorChain' } }),
    );
  });

  it('accepts an unknown top-level field', () => {
    const d = copy(samples.delivery);
    d['x-future'] = 1;
    expect(valid('Delivery', d)).toBe(true);
  });
});
