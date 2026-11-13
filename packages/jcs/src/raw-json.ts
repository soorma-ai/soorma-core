// SPDX-License-Identifier: FSL-1.1-ALv2
//
// Raw JSON numbers (U7 NP-ET-05; the user's design at NFR Design Q4): a
// publish's payload carries every number by its source text, so a 64-bit
// integer, a long decimal, or an exponent form reaches subscribers exactly as
// written. Built on ES2025's JSON.rawJSON and JSON.isRawJSON, which Node 26
// provides.
//
// - TypeScript 6.0.3's lib and @types/node 26.6.6 declare neither, so this
//   module is the one place they are declared. It declares their types only:
//   nothing here implements them, and nothing falls back to a parse that
//   converts numbers. S4 checks they work before it starts (D-CG-ET-10)
// - A raw value is a frozen object with a null prototype and one member,
//   `rawJSON`, holding the text. Only parseRawNumbers makes them here, and
//   only for numbers
// - **One parser, iterative** (D-CG-ET-28, amending NP-ET-05): JSON.parse
//   with a reviver recurses, and overflows the stack between 2,000 and 4,000
//   levels of nesting on Node 26, well inside what a 64 KiB payload can
//   nest. parseRawNumbers therefore parses with an explicit stack, with no
//   reviver path for any input, and gives JSON.parse's results: members
//   created as own data properties (so `__proto__` is an ordinary key), a
//   duplicate key in its first position with its last value, integer-like
//   keys in the engine's order, every string exactly as JSON.parse decodes
//   it (a lone surrogate included), and each number as JSON.rawJSON of its
//   exact source text

/** A JSON number carried as its exact source text (a JSON.rawJSON value). */
export interface RawJsonNumber {
  readonly rawJSON: string;
}

/** What Node 26's JSON provides beyond TypeScript's declaration of it. */
interface Es2025Json {
  rawJSON?: (text: string) => RawJsonNumber;
  isRawJSON?: (value: unknown) => boolean;
}

const json = JSON as unknown as Es2025Json;

/** True when this runtime provides JSON.rawJSON and JSON.isRawJSON. */
export function hasRawJson(): boolean {
  return typeof json.rawJSON === 'function' && typeof json.isRawJSON === 'function';
}

/**
 * True for a JSON.rawJSON value. Where the runtime has no JSON.isRawJSON, no
 * raw value can exist, so the answer is false.
 */
export function isRawJson(value: unknown): value is RawJsonNumber {
  return typeof json.isRawJSON === 'function' && json.isRawJSON(value);
}

/** An open container on the parser's stack. */
type Frame =
  | { readonly kind: 'array'; readonly value: unknown[] }
  | { readonly kind: 'object'; readonly value: Record<string, unknown>; key: string };

/** RFC 8259's number grammar, matched at a position (sticky): linear, no backtracking. */
const NUMBER = /-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?/y;

/** As JSON.parse's CreateDataProperty: never an assignment, so never a setter or a prototype. */
function define(target: Record<string, unknown>, key: string, value: unknown): void {
  Object.defineProperty(target, key, {
    value,
    writable: true,
    enumerable: true,
    configurable: true,
  });
}

/**
 * Parses JSON text, carrying every number by its source text. Strings,
 * booleans, null, arrays, and objects are JSON.parse's; a duplicate member
 * name keeps its first position and its last value. Any nesting the input
 * holds is parsed, with an explicit stack. Throws a SyntaxError for text
 * that is not JSON, and an Error where the runtime cannot carry source text:
 * never a fallback.
 */
export function parseRawNumbers(text: string): unknown {
  const rawJSON = json.rawJSON;
  if (typeof rawJSON !== 'function') throw new Error('JSON.rawJSON is not available');
  const length = text.length;
  const stack: Frame[] = [];
  let i = 0;

  const fail = (what: string): never => {
    throw new SyntaxError(`${what} at position ${i}`);
  };
  const space = (): void => {
    for (;;) {
      const c = text.charCodeAt(i);
      // space, tab, line feed, carriage return
      if (c === 0x20 || c === 0x09 || c === 0x0a || c === 0x0d) i += 1;
      else return;
    }
  };
  /** A string token at i: decoded exactly as JSON.parse decodes it. */
  const string = (): string => {
    if (text.charCodeAt(i) !== 0x22) fail('expected a string');
    let j = i + 1;
    let escaped = false;
    for (;;) {
      if (j >= length) fail('unterminated string');
      const c = text.charCodeAt(j);
      if (c === 0x22) break;
      if (c < 0x20) fail('control character in a string');
      if (c === 0x5c) {
        escaped = true;
        j += 2;
      } else j += 1;
    }
    const token = text.slice(i, j + 1);
    i = j + 1;
    return escaped ? (JSON.parse(token) as string) : token.slice(1, -1);
  };
  const literal = (word: string, value: unknown): unknown => {
    if (!text.startsWith(word, i)) fail('unexpected token');
    i += word.length;
    return value;
  };
  /** A member's key and its colon; the frame's key becomes it. */
  const key = (frame: Frame & { kind: 'object' }): void => {
    space();
    frame.key = string();
    space();
    if (text.charCodeAt(i) !== 0x3a) fail("expected ':'");
    i += 1;
  };

  let value: unknown;
  read: for (;;) {
    // Read one value, or open a container and read its first member.
    space();
    const c = text.charCodeAt(i);
    if (c === 0x7b) {
      i += 1;
      space();
      if (text.charCodeAt(i) === 0x7d) {
        i += 1;
        value = {};
      } else {
        const frame: Frame = { kind: 'object', value: {}, key: '' };
        stack.push(frame);
        key(frame);
        continue read;
      }
    } else if (c === 0x5b) {
      i += 1;
      space();
      if (text.charCodeAt(i) === 0x5d) {
        i += 1;
        value = [];
      } else {
        stack.push({ kind: 'array', value: [] });
        continue read;
      }
    } else if (c === 0x22) {
      value = string();
    } else if (c === 0x74) {
      value = literal('true', true);
    } else if (c === 0x66) {
      value = literal('false', false);
    } else if (c === 0x6e) {
      value = literal('null', null);
    } else {
      NUMBER.lastIndex = i;
      const m = NUMBER.exec(text);
      if (!m) fail('unexpected token');
      i = NUMBER.lastIndex;
      value = rawJSON(m![0]);
    }

    // Place the value, closing every container that ends after it.
    for (;;) {
      const top = stack.at(-1);
      if (!top) break read;
      if (top.kind === 'array') top.value.push(value);
      else define(top.value, top.key, value);
      space();
      const next = text.charCodeAt(i);
      i += 1;
      if (next === 0x2c) {
        if (top.kind === 'object') key(top);
        continue read;
      }
      if (next !== (top.kind === 'array' ? 0x5d : 0x7d)) {
        i -= 1;
        fail('expected a comma or the end of the container');
      }
      stack.pop();
      value = top.value;
    }
  }
  space();
  if (i !== length) fail('unexpected text after the value');
  return value;
}
