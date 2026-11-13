// SPDX-License-Identifier: FSL-1.1-ALv2
// Raw JSON numbers and the source mode (U7 NP-ET-05; D-CG-ET-16): TC-ET-074,
// TC-ET-093, and the parse behind TC-ET-071, 072, 076. U3's canonicalize
// tests are unchanged.
import { describe, expect, it } from 'vitest';
import {
  CanonicalizationError,
  canonicalize,
  hasRawJson,
  isRawJson,
  parseRawNumbers,
} from '../src/index.ts';

/** A raw JSON number, made the way the payload parse makes them. */
const raw = (text: string): unknown => (parseRawNumbers(`[${text}]`) as unknown[])[0];

function refused(run: () => unknown): CanonicalizationError {
  try {
    run();
  } catch (e) {
    expect(e).toBeInstanceOf(CanonicalizationError);
    return e as CanonicalizationError;
  }
  throw new Error('expected a CanonicalizationError');
}

describe('parseRawNumbers (TC-ET-071, 072, 076 at the parse)', () => {
  it('this runtime provides JSON.rawJSON and JSON.isRawJSON', () => {
    expect(hasRawJson()).toBe(true);
  });

  it('carries an integer above 2^53 by its source text (TC-ET-071)', () => {
    const v = parseRawNumbers('{"id":12345678901234567890}') as { id: unknown };
    expect(isRawJson(v.id)).toBe(true);
    expect(JSON.stringify(v)).toBe('{"id":12345678901234567890}');
  });

  it('carries a long decimal, exponent forms, and -0 exactly (TC-ET-072)', () => {
    const text = '[0.10000000000000000555,6.02214076e23,1E+400,-0]';
    expect(JSON.stringify(parseRawNumbers(text))).toBe(text);
  });

  it('keeps the last of duplicate member names (TC-ET-076)', () => {
    expect(JSON.stringify(parseRawNumbers('{"k":1,"k":2}'))).toBe('{"k":2}');
  });

  it('leaves strings, booleans, null, arrays, and objects as JSON parses them', () => {
    const text = '{"s":"a\\u00e9","b":true,"n":null,"a":[[]],"o":{}}';
    expect(parseRawNumbers(text)).toEqual(JSON.parse(text));
  });

  it('refuses text that is not JSON', () => {
    expect(() => parseRawNumbers('{"a":')).toThrow(SyntaxError);
  });
});

describe('TC-ET-074: the source mode, and the default mode otherwise unchanged', () => {
  it('writes a raw number as its source text, unchanged', () => {
    const v = parseRawNumbers('{"b":[1E+400,-0],"a":12345678901234567890}');
    expect(canonicalize(v, { numbers: 'source' }).text).toBe(
      '{"a":12345678901234567890,"b":[1E+400,-0]}',
    );
  });

  it('measures by the source text: the bytes are what a bound counts', () => {
    const v = parseRawNumbers('{"n":' + '9'.repeat(60_000) + '}');
    expect(canonicalize(v, { numbers: 'source' }).bytes.length).toBe(60_006);
  });

  it('refuses a plain number in source mode, with its pointer', () => {
    expect(refused(() => canonicalize({ a: [1] }, { numbers: 'source' })).pointer).toBe('/a/0');
  });

  it('refuses a raw value that is not a number', () => {
    const notNumber = (JSON as unknown as { rawJSON: (t: string) => unknown }).rawJSON('"x"');
    expect(refused(() => canonicalize({ s: notNumber }, { numbers: 'source' })).pointer).toBe('/s');
  });

  it('refuses a lone surrogate in source mode, with its pointer (TC-ET-073 at the measure)', () => {
    const v = parseRawNumbers('{"a":"\\ud800"}');
    expect(refused(() => canonicalize(v, { numbers: 'source' })).pointer).toBe('/a');
  });

  it('refuses a raw value at the root in the default mode (D-CG-ET-16)', () => {
    expect(refused(() => canonicalize(raw('1'))).pointer).toBe('');
  });

  it('writes plain values in the default mode exactly as before', () => {
    expect(canonicalize({ b: [1e30, -0], a: 'x' }).text).toBe('{"a":"x","b":[1e+30,0]}');
  });
});

describe('TC-ET-093: a raw value nested in an object or an array is refused in default mode', () => {
  it('nested in objects: the pointer names it', () => {
    const v = { a: { b: raw('12345678901234567890') } };
    expect(refused(() => canonicalize(v)).pointer).toBe('/a/b');
  });

  it('nested in arrays: the pointer names it', () => {
    const v = [1, [2, raw('3')]];
    expect(refused(() => canonicalize(v)).pointer).toBe('/1/1');
  });

  it('the same values with every number raw canonicalize in source mode', () => {
    expect(
      canonicalize({ a: { b: raw('12345678901234567890') } }, { numbers: 'source' }).text,
    ).toBe('{"a":{"b":12345678901234567890}}');
    expect(canonicalize([raw('1'), [raw('2'), raw('3')]], { numbers: 'source' }).text).toBe(
      '[1,[2,3]]',
    );
  });

  it('a pointer escapes ~ and / (RFC 6901)', () => {
    expect(refused(() => canonicalize({ 'a/b': { '~c': raw('1') } })).pointer).toBe('/a~1b/~0c');
  });
});
