// SPDX-License-Identifier: FSL-1.1-ALv2
//
// parseRawNumbers, the one iterative parser (D-CG-ET-28, amending NP-ET-05;
// the user's conditions at the Group 7 stop): it gives JSON.parse's results,
// with each number as JSON.rawJSON of its exact source text, and survives any
// nesting a 256 KiB publish body can hold.
//
// - Every input is first accepted by JSON.parse: parseRawNumbers only ever
//   runs on such text, so a throw here would be a 500 at S4. Each must parse
// - The oracle is JSON.parse(text, rawReviver) on the same text: the same
//   JSON.stringify output, the same own keys in the same order at every
//   object, the same prototypes, and a raw value wherever the oracle has one
// - A fixed set covers own data properties (`__proto__`), duplicates,
//   integer-like keys, every escape and lone surrogates, number spellings,
//   and whitespace; a seeded generator adds shallow documents (no dependency)
// - Deep cases at publish's actual 256 KiB limit, arrays and objects, where
//   the oracle itself cannot run (its reviver recurses), compared by walking
//   with JSON.parse's structure (JSON.stringify recurses too, once a raw
//   value is present)
import { describe, expect, it } from 'vitest';
import { isRawJson, parseRawNumbers } from '../src/index.ts';

type Reviver = (key: string, value: unknown, context: { source?: string }) => unknown;
const rawJSON = (JSON as unknown as { rawJSON: (text: string) => unknown }).rawJSON;
const rawReviver: Reviver = (_key, value, context) =>
  typeof value === 'number' ? rawJSON(context.source!) : value;
const oracle = (text: string): unknown =>
  (JSON.parse as (text: string, reviver: Reviver) => unknown)(text, rawReviver);

/** Every object's own keys, in order, and its prototype; every raw value's place. */
function shape(root: unknown): string[] {
  const out: string[] = [];
  const pending: [unknown, string][] = [[root, '']];
  while (pending.length > 0) {
    const [v, at] = pending.pop()!;
    if (isRawJson(v)) out.push(`${at} raw ${v.rawJSON}`);
    else if (Array.isArray(v)) {
      out.push(`${at} array ${v.length} ${Object.getPrototypeOf(v) === Array.prototype}`);
      v.forEach((x, i) => pending.push([x, `${at}/${i}`]));
    } else if (typeof v === 'object' && v !== null) {
      const keys = Reflect.ownKeys(v).map(String);
      out.push(`${at} object [${keys.join('|')}] ${Object.getPrototypeOf(v) === Object.prototype}`);
      for (const k of keys) {
        const d = Object.getOwnPropertyDescriptor(v, k)!;
        out.push(`${at}/${k} ${'value' in d} ${d.writable} ${d.enumerable} ${d.configurable}`);
        pending.push([d.value, `${at}/${k}`]);
      }
    } else out.push(`${at} ${typeof v} ${JSON.stringify(v)}`);
  }
  return out;
}

function same(text: string): void {
  // The precondition: JSON.parse accepts it.
  expect(() => JSON.parse(text) as unknown, text).not.toThrow();
  const expected = oracle(text);
  let actual: unknown;
  expect(() => (actual = parseRawNumbers(text)), text).not.toThrow();
  expect(JSON.stringify(actual), text).toBe(JSON.stringify(expected));
  expect(shape(actual), text).toEqual(shape(expected));
}

const FIXED: string[] = [
  // Own data properties: __proto__ is an ordinary key, never the prototype.
  '{"__proto__":{"polluted":1}}',
  '{"a":1,"__proto__":[1,2],"b":2}',
  '{"__proto__":1,"__proto__":2}',
  '{"constructor":{"prototype":{"x":1}},"toString":1,"hasOwnProperty":2}',
  // Duplicates: first position, last value.
  '{"k":1,"j":2,"k":3}',
  '{"k":{"a":1},"j":[],"k":[1,2,3]}',
  '{"a":1,"a":2,"a":3}',
  // Integer-like keys come out in the engine's order.
  '{"b":1,"2":2,"1":3,"0":4,"-1":5,"01":6,"1.5":7,"4294967294":8,"4294967295":9,"a":10}',
  '{"10":1,"9":2,"x":3,"9":4}',
  // Every escape, and lone surrogates, escaped and raw.
  '"\\"\\\\\\/\\b\\f\\n\\r\\t"',
  '{"s":"\\u0000\\u001f\\u00e9\\u20AC\\uD83D\\uDE00\\ud800\\uDFFF\\uDC00\\uD800x"}',
  `{"raw":"${'\ud800'}","pair":"${'😀'}","bmp":"é€"}`,
  '{"\\u006b\\u0065\\u0079":1,"key":2}',
  '["\\/","/","\\u002F"]',
  // Number spellings, each kept as written.
  '[-0,0,-0.0,1E400,-1E400,1e-7,1E-7,1e+7,1E+0,12345678901234567890,-12345678901234567890]',
  '[0.10000000000000000555,6.02214076e23,1.5E+3,123.456e-789,9007199254740993,2e308]',
  '{"n":-0,"m":1E400,"o":{"p":[1e-7,[12345678901234567890]]}}',
  // Scalars at the root, and empties.
  '1',
  '-0',
  '"s"',
  'null',
  'true',
  'false',
  '{}',
  '[]',
  '[[],{},[[]],{"a":{}}]',
  // Whitespace variants.
  ' \t\r\n{ \t\r\n"a" \t\r\n: \t\r\n[ \t\r\n1 \t\r\n, \t\r\n2 \t\r\n] \t\r\n} \t\r\n',
  '[\r\n  1,\r\n  {\r\n    "x" : null\r\n  }\r\n]',
  '\n\n\n"x"\n\n\n',
];

describe('parseRawNumbers gives JSON.parse’s results (the fixed set)', () => {
  it.each(FIXED.map((t) => [t]))('%s', (text) => same(text));

  it('never sets a prototype, and keeps __proto__ as an own data property', () => {
    const v = parseRawNumbers('{"__proto__":{"polluted":1}}') as Record<string, unknown>;
    expect(Object.getPrototypeOf(v)).toBe(Object.prototype);
    expect(Object.hasOwn(v, '__proto__')).toBe(true);
    expect(({} as Record<string, unknown>).polluted).toBeUndefined();
  });

  it('each number is JSON.rawJSON of its exact source text', () => {
    const v = parseRawNumbers('[-0,1E400,1e-7,12345678901234567890]') as unknown[];
    expect(v.map((x) => (isRawJson(x) ? x.rawJSON : 'not raw'))).toEqual([
      '-0',
      '1E400',
      '1e-7',
      '12345678901234567890',
    ]);
    expect(JSON.stringify(v)).toBe('[-0,1E400,1e-7,12345678901234567890]');
  });
});

/** mulberry32: a small seeded generator, so a failure reproduces exactly. */
function seeded(seed: number): () => number {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/** A random shallow document, written as text with random spacing and spellings. */
function document(r: () => number, depth = 0): string {
  const pick = <T>(xs: readonly T[]): T => xs[Math.floor(r() * xs.length)]!;
  const ws = (): string => pick(['', '', ' ', '\n', '\t', '\r\n', '  ']);
  const KEYS = ['a', 'b', 'k', '0', '1', '2', '10', '01', '-1', '__proto__', 'é', 'x y', '\\u0041'];
  const STRINGS = [
    '',
    's',
    '\\n',
    '\\"',
    '\\\\',
    '\\/',
    '\\u00e9',
    '\\ud800',
    '\\uDC00',
    'é',
    '\\uD83D\\uDE00',
    '\ud800',
  ];
  const NUMBERS = [
    '0',
    '-0',
    '1',
    '-1',
    '1.5',
    '1E400',
    '1e-7',
    '-2.5E+3',
    '12345678901234567890',
    '0.1000000000000000055511151231257827',
    '6.02214076e23',
  ];
  const kind = depth >= 4 ? Math.floor(r() * 4) : Math.floor(r() * 6);
  switch (kind) {
    case 0:
      return pick(NUMBERS);
    case 1:
      return `"${pick(STRINGS)}${pick(STRINGS)}"`;
    case 2:
      return pick(['true', 'false', 'null']);
    case 3:
      return pick(NUMBERS);
    case 4: {
      const n = Math.floor(r() * 5);
      const items = Array.from({ length: n }, () => `${ws()}${document(r, depth + 1)}${ws()}`);
      return `[${items.join(',')}${n === 0 ? ws() : ''}]`;
    }
    default: {
      const n = Math.floor(r() * 6);
      const members = Array.from(
        { length: n },
        () => `${ws()}"${pick(KEYS)}"${ws()}:${ws()}${document(r, depth + 1)}${ws()}`,
      );
      return `{${members.join(',')}${n === 0 ? ws() : ''}}`;
    }
  }
}

describe('parseRawNumbers gives JSON.parse’s results (seeded shallow documents)', () => {
  it('2,000 generated documents from a fixed seed, each the same as the oracle', () => {
    const r = seeded(0x5eed_0007);
    for (let n = 0; n < 2000; n++) {
      const text = `${r() < 0.5 ? ' ' : ''}${document(r)}${r() < 0.5 ? '\n' : ''}`;
      same(text);
    }
  });
});

describe('parseRawNumbers survives the nesting a 256 KiB publish body holds', () => {
  const LIMIT = 262_144;

  it('arrays nested to 256 KiB, a raw number at the bottom', () => {
    const depth = (LIMIT - 1) / 2 - 0.5;
    const text = `${'['.repeat(depth)}7${']'.repeat(depth)}`;
    expect(text.length).toBe(LIMIT - 1);
    // The oracle's reviver recurses and cannot run here: the reviver path fails.
    expect(() => oracle(text)).toThrow(RangeError);
    const started = performance.now();
    const v = parseRawNumbers(text);
    const ms = performance.now() - started;
    // Compared by walking: JSON.stringify recurses once a raw value is present.
    let at: unknown = v;
    for (let d = 0; d < depth; d++) {
      expect(Array.isArray(at) && at.length === 1).toBe(true);
      at = (at as unknown[])[0];
    }
    expect(isRawJson(at) && at.rawJSON).toBe('7');
    // Recorded at Code Generation (D-CG-ET-28): one 256 KiB parse, in milliseconds.
    console.info(
      `parseRawNumbers: 256 KiB of nested arrays (${depth} levels) in ${ms.toFixed(1)} ms`,
    );
  });

  it('objects nested to 256 KiB, duplicates and __proto__ at every level', () => {
    const level = '{"__proto__":0,"a":0,"a":';
    const depth = Math.floor((LIMIT - 2) / (level.length + 1));
    const text = `${level.repeat(depth)}1E400${'}'.repeat(depth)}`;
    expect(text.length).toBeLessThanOrEqual(LIMIT);
    const started = performance.now();
    const v = parseRawNumbers(text);
    const ms = performance.now() - started;
    // The structure JSON.parse gives, without a reviver (which cannot run here).
    const plain = JSON.parse(text) as unknown;
    let a: unknown = v;
    let b: unknown = plain;
    for (let d = 0; d < depth; d++) {
      expect(Reflect.ownKeys(a as object)).toEqual(Reflect.ownKeys(b as object));
      expect(Object.getPrototypeOf(a)).toBe(Object.prototype);
      a = (a as Record<string, unknown>).a;
      b = (b as Record<string, unknown>).a;
    }
    expect(isRawJson(a) && a.rawJSON).toBe('1E400');
    console.info(
      `parseRawNumbers: 256 KiB of nested objects (${depth} levels) in ${ms.toFixed(1)} ms`,
    );
  });
});

describe('parseRawNumbers refuses what is not JSON (it runs only after JSON.parse accepted)', () => {
  it.each(['', '[', '{"a"}', '[1,]', '01', '"\u0001"', '1 2', '{"a":1,}', 'nul', '"\\'])(
    '%j',
    (text) => {
      expect(() => JSON.parse(text) as unknown).toThrow(SyntaxError);
      expect(() => parseRawNumbers(text)).toThrow(SyntaxError);
    },
  );
});
