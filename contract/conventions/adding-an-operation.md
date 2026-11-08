<!-- SPDX-License-Identifier: Apache-2.0 -->

# Adding an Operation

Each surface adds its operations to its own document, `contract/{surface}.openapi.yaml`:
`org-gateway` (S1), `control-gateway` (S2), `data-gateway` (S3), and `event-ingest` (S4). One
document belongs to one face: S1 and S2 are control-face, S3 and S4 data-face. The contract checks
enforce these steps.

1. **Reference the shared components; never copy them**: `Problem`, the security schemes, the
   identifier definitions, the `Soorma-Contract-Version` parameter and header, and the
   `Soorma-Request-Id` and `Retry-After` headers, all from
   [`components.openapi.yaml`](components.openapi.yaml)
2. **An envelope-bearing operation references the draft (and the Delivery, for a stream) by
   `$ref`.** Never inline the envelope, the draft, or the Delivery
3. **Name exactly one accepted security scheme**, or none for an unauthenticated surface
4. **Validate every input**: types, lengths, and patterns from the identifier definitions; request
   bodies closed (`additionalProperties: false`); every request-side string with a `maxLength` and
   every request-side array with a `maxItems`; patterns anchored and in the portable subset; no
   `format`
5. **Add any new error code** to `ProblemCode` and to [errors.md](errors.md)
6. **Add a row to the envelope-bearing operations table** in [envelope.md](envelope.md) if the
   operation carries an envelope
7. **Classify the change** under [versioning.md](versioning.md), record it in
   [`../CHANGELOG.md`](../CHANGELOG.md), add fixtures, and regenerate the types
   (`pnpm run generate`)
