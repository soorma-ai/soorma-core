// SPDX-License-Identifier: FSL-1.1-ALv2
//
// Raw JSON numbers (U7 NP-ET-05; the user's design at NFR Design Q4): a
// publish's payload carries every number by its source text, so a 64-bit
// integer, a long decimal, or an exponent form reaches subscribers exactly as
// written. Built on ES2025's JSON.rawJSON, JSON.isRawJSON, and the reviver's
// source-text context, which Node 26 provides.
//
// - TypeScript 6.0.3's lib and @types/node 26.6.6 declare none of them, so
//   this module is the one place they are declared. It declares their types
//   only: nothing here implements them, and nothing falls back to a parse
//   that converts numbers. S4 checks they work before it starts (D-CG-ET-10)
// - A raw value is a frozen object with a null prototype and one member,
//   `rawJSON`, holding the text. Only parseRawNumbers makes them here, and
//   only for numbers

/** A JSON number carried as its exact source text (a JSON.rawJSON value). */
export interface RawJsonNumber {
  readonly rawJSON: string;
}

/** The reviver's third argument: the source text of a primitive value. */
interface ReviverContext {
  readonly source?: string;
}

/** What Node 26's JSON provides beyond TypeScript's declaration of it. */
interface Es2025Json {
  rawJSON?: (text: string) => RawJsonNumber;
  isRawJSON?: (value: unknown) => boolean;
  parse(
    text: string,
    reviver: (this: unknown, key: string, value: unknown, context: ReviverContext) => unknown,
  ): unknown;
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

/**
 * Parses JSON text, carrying every number by its source text. Strings,
 * booleans, null, arrays, and objects are JSON's parse; a duplicate member
 * name keeps the last value. Throws a SyntaxError for text that is not JSON,
 * and an Error where the runtime cannot carry source text: never a fallback.
 */
export function parseRawNumbers(text: string): unknown {
  const rawJSON = json.rawJSON;
  if (typeof rawJSON !== 'function') throw new Error('JSON.rawJSON is not available');
  return json.parse(text, (_key, value, context) => {
    if (typeof value !== 'number') return value;
    if (context.source === undefined) throw new Error('the reviver has no source text');
    return rawJSON(context.source);
  });
}
