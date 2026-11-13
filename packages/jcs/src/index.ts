// SPDX-License-Identifier: FSL-1.1-ALv2
//
// @soorma/jcs: RFC 8785, the JSON Canonicalization Scheme, as the one
// implementation in this repository (U3 NFR Design NP-03; NFR-AE-04).
//
// - Iterative: an explicit stack of frames, never recursion, so nesting depth
//   is bounded by memory, not by the call stack (NFR-AE-19)
// - Object keys sorted by UTF-16 code units (Array.prototype.sort with no
//   comparator), as RFC 8785 §3.2.3 specifies
// - Numbers as ECMAScript's Number.prototype.toString, which RFC 8785 §3.2.2.3
//   adopts; -0 serializes as 0. A non-finite number has no JSON form
// - Strings as JSON.stringify escapes them (RFC 8785 §3.2.2.2), after
//   refusing a lone surrogate: RFC 8785 requires I-JSON (RFC 7493), which
//   forbids one, so such a value has no canonical form
// - JSON values only: null, booleans, numbers, strings, arrays, and plain
//   objects (prototype Object.prototype or null). Anything else is refused
//
// canonicalize returns the text and its UTF-8 bytes: the bytes are what a
// size bound measures and what a MAC covers, so a caller computes them once.
//
// U7 additions (NP-ET-05; D-CG-ET-16), each additive:
// - CanonicalizationError carries the JSON Pointer of the value it refuses
// - `{ numbers: 'source' }`: numbers must be raw JSON values (raw-json.ts)
//   and are written as their source text, unchanged; a plain number is
//   refused. Used only to measure a publish's payload against its bound
// - The default mode refuses a raw JSON value. A raw value is a frozen,
//   null-prototype object, which the plain-object rule would otherwise accept
//   and write as {"rawJSON":"…"}. Every other input is as before
import { isRawJson } from './raw-json.ts';

export { hasRawJson, isRawJson, parseRawNumbers, type RawJsonNumber } from './raw-json.ts';

export class CanonicalizationError extends Error {
  /** The JSON Pointer (RFC 6901) of the refused value: '' for the root. */
  readonly pointer: string;

  constructor(message: string, pointer = '') {
    super(message);
    this.name = 'CanonicalizationError';
    this.pointer = pointer;
  }
}

/** How numbers are written: as ECMAScript does (RFC 8785), or by their source text. */
export interface CanonicalizeOptions {
  readonly numbers?: 'value' | 'source';
}

export interface Canonical {
  /** The RFC 8785 serialization. */
  readonly text: string;
  /** Its UTF-8 encoding: `bytes.length` is the size a bound measures. */
  readonly bytes: Buffer;
}

type Frame =
  | { readonly kind: 'array'; readonly value: readonly unknown[]; index: number }
  | {
      readonly kind: 'object';
      readonly value: Readonly<Record<string, unknown>>;
      readonly keys: string[];
      index: number;
    };

/** A refused value's pointer, computed only when a refusal is thrown. */
type Pointer = () => string;

function string(value: string, pointer: Pointer): string {
  if (!value.isWellFormed())
    throw new CanonicalizationError(
      'a string holds a lone surrogate, which has no JSON form',
      pointer(),
    );
  return JSON.stringify(value);
}

function number(value: number, pointer: Pointer): string {
  if (!Number.isFinite(value))
    throw new CanonicalizationError('a non-finite number has no JSON form', pointer());
  return Object.is(value, -0) ? '0' : String(value);
}

/** RFC 8259's number grammar: what a raw value's text must be. */
const JSON_NUMBER = /^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?$/;

/** RFC 6901: '~' as '~0', '/' as '~1'. */
function token(key: string | number): string {
  return String(key).replaceAll('~', '~0').replaceAll('/', '~1');
}

function isPlainObject(value: object): value is Record<string, unknown> {
  const prototype = Object.getPrototypeOf(value) as unknown;
  return prototype === Object.prototype || prototype === null;
}

/**
 * The RFC 8785 form of a JSON value. Throws CanonicalizationError, with the
 * refused value's pointer, if it has none.
 */
export function canonicalize(value: unknown, options: CanonicalizeOptions = {}): Canonical {
  const source = options.numbers === 'source';
  const out: string[] = [];
  const stack: Frame[] = [];
  // The pointer tokens of the containers on the stack.
  const path: string[] = [];
  // The containers on the stack: a value that contains itself has no JSON form.
  const open = new Set<object>();
  // Built only when a refusal is thrown: joining the path for every value
  // would make deep input quadratic (TC-AE-037).
  const at =
    (key?: string | number): Pointer =>
    () =>
      key === undefined && path.length === 0
        ? ''
        : '/' + [...path, ...(key === undefined ? [] : [token(key)])].join('/');

  const begin = (v: unknown, key?: string | number): void => {
    const pointer = at(key);
    switch (typeof v) {
      case 'string':
        out.push(string(v, pointer));
        return;
      case 'number':
        if (source)
          throw new CanonicalizationError(
            'in source mode, every number is a raw JSON value',
            pointer(),
          );
        out.push(number(v, pointer));
        return;
      case 'boolean':
        out.push(v ? 'true' : 'false');
        return;
      case 'object':
        if (v === null) {
          out.push('null');
          return;
        }
        if (isRawJson(v)) {
          if (!source)
            throw new CanonicalizationError(
              'a raw JSON value has no canonical form in the default mode',
              pointer(),
            );
          if (!JSON_NUMBER.test(v.rawJSON))
            throw new CanonicalizationError('a raw JSON value that is not a number', pointer());
          out.push(v.rawJSON);
          return;
        }
        if (open.has(v)) throw new CanonicalizationError('a value contains itself', pointer());
        if (Array.isArray(v)) {
          open.add(v);
          out.push('[');
          if (key !== undefined) path.push(token(key));
          stack.push({ kind: 'array', value: v as unknown[], index: 0 });
          return;
        }
        if (isPlainObject(v)) {
          open.add(v);
          out.push('{');
          if (key !== undefined) path.push(token(key));
          stack.push({ kind: 'object', value: v, keys: Object.keys(v).sort(), index: 0 });
          return;
        }
        throw new CanonicalizationError(
          'only plain objects and arrays have a JSON form',
          pointer(),
        );
      default:
        throw new CanonicalizationError(`a ${typeof v} has no JSON form`, pointer());
    }
  };

  begin(value);
  while (stack.length > 0) {
    const frame = stack[stack.length - 1]!;
    if (frame.kind === 'array') {
      if (frame.index < frame.value.length) {
        if (frame.index > 0) out.push(',');
        const index = frame.index++;
        begin(frame.value[index], index);
      } else {
        out.push(']');
        open.delete(frame.value);
        stack.pop();
        if (stack.length > 0) path.pop();
      }
    } else if (frame.index < frame.keys.length) {
      if (frame.index > 0) out.push(',');
      const key = frame.keys[frame.index++]!;
      out.push(string(key, at(key)), ':');
      begin(frame.value[key], key);
    } else {
      out.push('}');
      open.delete(frame.value);
      stack.pop();
      if (stack.length > 0) path.pop();
    }
  }

  const text = out.join('');
  return { text, bytes: Buffer.from(text, 'utf8') };
}
