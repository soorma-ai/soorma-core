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

export class CanonicalizationError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'CanonicalizationError';
  }
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

function string(value: string): string {
  if (!value.isWellFormed())
    throw new CanonicalizationError('a string holds a lone surrogate, which has no JSON form');
  return JSON.stringify(value);
}

function number(value: number): string {
  if (!Number.isFinite(value))
    throw new CanonicalizationError('a non-finite number has no JSON form');
  return Object.is(value, -0) ? '0' : String(value);
}

function isPlainObject(value: object): value is Record<string, unknown> {
  const prototype = Object.getPrototypeOf(value) as unknown;
  return prototype === Object.prototype || prototype === null;
}

/** The RFC 8785 form of a JSON value. Throws CanonicalizationError if it has none. */
export function canonicalize(value: unknown): Canonical {
  const out: string[] = [];
  const stack: Frame[] = [];
  // The containers on the stack: a value that contains itself has no JSON form.
  const open = new Set<object>();

  const begin = (v: unknown): void => {
    switch (typeof v) {
      case 'string':
        out.push(string(v));
        return;
      case 'number':
        out.push(number(v));
        return;
      case 'boolean':
        out.push(v ? 'true' : 'false');
        return;
      case 'object':
        if (v === null) {
          out.push('null');
          return;
        }
        if (open.has(v)) throw new CanonicalizationError('a value contains itself');
        if (Array.isArray(v)) {
          open.add(v);
          out.push('[');
          stack.push({ kind: 'array', value: v as unknown[], index: 0 });
          return;
        }
        if (isPlainObject(v)) {
          open.add(v);
          out.push('{');
          stack.push({ kind: 'object', value: v, keys: Object.keys(v).sort(), index: 0 });
          return;
        }
        throw new CanonicalizationError('only plain objects and arrays have a JSON form');
      default:
        throw new CanonicalizationError(`a ${typeof v} has no JSON form`);
    }
  };

  begin(value);
  while (stack.length > 0) {
    const frame = stack[stack.length - 1]!;
    if (frame.kind === 'array') {
      if (frame.index < frame.value.length) {
        if (frame.index > 0) out.push(',');
        begin(frame.value[frame.index++]);
      } else {
        out.push(']');
        open.delete(frame.value);
        stack.pop();
      }
    } else if (frame.index < frame.keys.length) {
      if (frame.index > 0) out.push(',');
      const key = frame.keys[frame.index++]!;
      out.push(string(key), ':');
      begin(frame.value[key]);
    } else {
      out.push('}');
      open.delete(frame.value);
      stack.pop();
    }
  }

  const text = out.join('');
  return { text, bytes: Buffer.from(text, 'utf8') };
}
