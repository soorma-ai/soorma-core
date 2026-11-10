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

A key named `__proto__`, as `JSON.parse` produces it, is an ordinary field.
