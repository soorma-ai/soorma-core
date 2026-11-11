// SPDX-License-Identifier: FSL-1.1-ALv2
// RFC 8785 (JCS): TC-AE-036 steps 1, 2; TC-AE-037 (depth, in the
// canonicalizer); NFR-AE-04, 19; NP-03.
import { describe, expect, it } from 'vitest';
import { CanonicalizationError, canonicalize } from '../src/index.ts';

const text = (value: unknown): string => canonicalize(value).text;

/** A double from its IEEE 754 bit pattern, as RFC 8785 Appendix B lists them. */
function fromHex(hex: string): number {
  const view = new DataView(new ArrayBuffer(8));
  view.setBigUint64(0, BigInt(`0x${hex}`));
  return view.getFloat64(0);
}

describe('TC-AE-036 step 1: RFC 8785 examples and committed vectors', () => {
  it('§3.2.2: the sample input', () => {
    const input = JSON.parse(
      '{"numbers":[333333333.33333329,1E30,4.50,2e-3,0.000000000000000000000000001],' +
        '"string":"\\u20ac$\\u000F\\u000aA\'\\u0042\\u0022\\u005c\\\\\\"\\/",' +
        '"literals":[null,true,false]}',
    ) as unknown;
    expect(text(input)).toBe(
      '{"literals":[null,true,false],"numbers":[333333333.3333333,1e+30,4.5,0.002,1e-27],' +
        '"string":"€$\\u000f\\nA\'B\\"\\\\\\\\\\"/"}',
    );
  });

  it('§3.2.3: keys sorted by UTF-16 code units', () => {
    const input = {
      '€': 'Euro Sign',
      '\r': 'Carriage Return',
      דּ: 'Hebrew Letter Dalet With Dagesh',
      '1': 'One',
      '😀': 'Emoji: Grinning Face',
      '\u0080': 'Control',
      ö: 'Latin Small Letter O With Diaeresis',
    };
    expect(text(input)).toBe(
      '{"\\r":"Carriage Return","1":"One","\u0080":"Control",' +
        '"ö":"Latin Small Letter O With Diaeresis","€":"Euro Sign",' +
        '"😀":"Emoji: Grinning Face","דּ":"Hebrew Letter Dalet With Dagesh"}',
    );
  });

  it.each([
    ['0000000000000000', '0'],
    ['8000000000000000', '0'],
    ['0000000000000001', '5e-324'],
    ['8000000000000001', '-5e-324'],
    ['7fefffffffffffff', '1.7976931348623157e+308'],
    ['ffefffffffffffff', '-1.7976931348623157e+308'],
    ['4340000000000000', '9007199254740992'],
    ['c340000000000000', '-9007199254740992'],
    ['4430000000000000', '295147905179352830000'],
    ['44b52d02c7e14af5', '9.999999999999997e+22'],
    ['44b52d02c7e14af6', '1e+23'],
    ['44b52d02c7e14af7', '1.0000000000000001e+23'],
    ['444b1ae4d6e2ef4e', '999999999999999700000'],
    ['444b1ae4d6e2ef4f', '999999999999999900000'],
    ['444b1ae4d6e2ef50', '1e+21'],
    ['3eb0c6f7a0b5ed8c', '9.999999999999997e-7'],
    ['3eb0c6f7a0b5ed8d', '0.000001'],
    ['41b3de4355555553', '333333333.3333332'],
    ['41b3de4355555554', '333333333.33333325'],
    ['41b3de4355555555', '333333333.3333333'],
    ['41b3de4355555556', '333333333.3333334'],
    ['41b3de4355555557', '333333333.33333343'],
    ['becbf647612f3696', '-0.0000033333333333333333'],
    ['43143ff3c1cb0959', '1424953923781206.2'],
  ])('Appendix B: %s serializes as %s', (hex, expected) => {
    expect(text(fromHex(hex))).toBe(expected);
  });

  it('committed number vectors: -0, exponents, integers, fractions', () => {
    expect(text([-0, 1e21, 1e-7, 1.5e300, 100, 0.1, -1.25])).toBe(
      '[0,1e+21,1e-7,1.5e+300,100,0.1,-1.25]',
    );
  });

  it('committed string vectors: escapes, controls, and astral characters', () => {
    expect(text('a"b\\c\b\f\n\r\t\u0000\u001f\u007f/é😀')).toBe(
      '"a\\"b\\\\c\\b\\f\\n\\r\\t\\u0000\\u001f\u007f/é😀"',
    );
    expect(text({ b: [], a: {}, c: [{}] })).toBe('{"a":{},"b":[],"c":[{}]}');
  });

  it('returns the UTF-8 bytes of the text', () => {
    const { text: t, bytes } = canonicalize({ x: 'é😀' });
    expect(bytes.equals(Buffer.from(t, 'utf8'))).toBe(true);
    expect(bytes.length).toBe(14);
  });

  it('copies a __proto__ key as a field (an own property from JSON.parse)', () => {
    expect(text(JSON.parse('{"__proto__":{"a":1},"b":2}'))).toBe('{"__proto__":{"a":1},"b":2}');
  });
});

describe('TC-AE-036 step 2: values with no RFC 8785 form are refused', () => {
  it.each([
    ['a lone high surrogate in a value', { a: 'x\ud800' }],
    ['a lone low surrogate in a value', ['\udc00y']],
    ['a lone surrogate in a key', { '\ud800': 1 }],
    ['NaN', NaN],
    ['Infinity', [Infinity]],
    ['undefined', { a: undefined }],
    ['a function', [() => 1]],
    ['a bigint', 1n],
    ['a symbol', Symbol('s')],
    ['a Date', new Date(0)],
    ['a Map', new Map()],
  ])('%s', (_, value) => {
    expect(() => canonicalize(value)).toThrow(CanonicalizationError);
  });

  it('a value that contains itself', () => {
    const a: unknown[] = [];
    a.push(a);
    expect(() => canonicalize(a)).toThrow(CanonicalizationError);
  });

  it('a value reached twice, but not inside itself, is serialized twice', () => {
    const shared = { k: 1 };
    expect(text([shared, shared])).toBe('[{"k":1},{"k":1}]');
  });
});

describe('TC-AE-037: depth bounded by memory, not the call stack (NFR-AE-19)', () => {
  it('a 100,000-deep array and object, with no RangeError', () => {
    const depth = 100_000;
    const arrays = JSON.parse(`${'['.repeat(depth)}${']'.repeat(depth)}`) as unknown;
    expect(canonicalize(arrays).bytes.length).toBe(2 * depth);
    let object: unknown = 1;
    for (let i = 0; i < depth; i++) object = { a: object };
    expect(canonicalize(object).text.startsWith('{"a":{"a":')).toBe(true);
  });
});
