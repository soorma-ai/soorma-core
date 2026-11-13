<!-- SPDX-License-Identifier: FSL-1.1-ALv2 -->

# `@soorma/jcs`

RFC 8785, the JSON Canonicalization Scheme. This is **the one implementation in this
repository**: the envelope's bound and seal (`@soorma/envelope`) use it, and so do U2's keyed
hashes (`@soorma/org-identity`'s `canonicalJson`).

```ts
const { text, bytes } = canonicalize(value); // bytes: the UTF-8 encoding, computed once
```

It follows RFC 8785:

- Object keys are sorted by UTF-16 code units.
- Numbers are serialized as ECMAScript's `Number.prototype.toString`, with `-0` as `0`.
- Strings are escaped as `JSON.stringify` escapes them.

It is iterative, with no recursion, so nesting depth is bounded by memory, not by the call stack.

## What it refuses

It throws `CanonicalizationError`, never producing output, for a value that has no RFC 8785 form:

- a string or key holding a **lone surrogate** (RFC 8785 requires I-JSON)
- a non-finite number
- `undefined`, a function, a symbol, or a bigint
- an object that is not plain: a `Date` or a `Map`, for example
- a value that contains itself
- **a raw JSON value** (`JSON.rawJSON`), in the default mode (U7 D-CG-ET-16): it is a frozen
  object with a null prototype, which would otherwise be written as `{"rawJSON":"…"}`

Every refusal carries `pointer`, the JSON Pointer (RFC 6901) of the refused value.

A key named `__proto__`, as `JSON.parse` produces it, is an ordinary field.

## Raw numbers and the source mode (U7)

A publish's payload carries its numbers exactly as written (U7 NFR Design NP-ET-05):

```ts
const payload = parseRawNumbers(text); // every number a JSON.rawJSON value of its source text
const { bytes } = canonicalize(payload, { numbers: 'source' }); // the payload bound's measure
JSON.stringify(payload); // numbers written as their source text
```

- `parseRawNumbers` uses ES2025's `JSON.rawJSON` and the reviver's source text, which Node 26
  provides. TypeScript does not declare them yet, so `src/raw-json.ts` is the one place their
  types are declared. **There is no fallback**: without `JSON.rawJSON` it throws, and S4 refuses
  to start (`hasRawJson` is its check)
- `{ numbers: 'source' }` writes each raw number's text unchanged and refuses a plain number, a
  raw value that is not a number, and a lone surrogate. Everything else is RFC 8785. It measures
  the payload only; the envelope and the seal use the default mode
