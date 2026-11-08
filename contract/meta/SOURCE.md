<!-- SPDX-License-Identifier: Apache-2.0 -->

# Pinned OpenAPI 3.1 Schema

The contract checks validate every OpenAPI document under `contract/` against this committed copy
of the official OpenAPI 3.1 schema, offline. Nothing is fetched at check time (NFR-WC-11;
SECURITY-13).

| Field | Value |
|---|---|
| File | `openapi-3.1-schema-2026-08-03.json` |
| Source | https://spec.openapis.org/oas/3.1/schema/2026-08-03 |
| `$id` | `https://spec.openapis.org/oas/3.1/schema/2026-08-03` |
| Version | The latest dated OpenAPI 3.1 schema published at the time of pinning |
| Licence | Apache-2.0, OpenAPI Initiative (declared for this directory in `REUSE.toml`) |
| Retrieved | 2026-11-08 |
| Cross-checked | Its git blob hash, `1c2e54d1023c6c59dca977218aa715ba6e9fac46`, matches `oas/3.1/schema/2026-08-03` in the `OAI/spec.openapis.org` repository |
| SHA-256 | `59f106413cb48c31299f96f024c938d3628aed6cd02cd14bcfb2fcaae7a130b6` |

The checks recompute the file's SHA-256 on every run and fail if it differs from the value above.
To move to a newer schema: add the new file, update this table, and remove the old file, in one
reviewed change.

## Why its validator is not strict

The contract has two Ajv instances:

- **The contract's own** instance compiles the contract's schemas with `strict: true`
  (NFR-WC-10), and no `format` is used in them (NFR-WC-09)
- **This meta-schema's** instance runs with **`strict: false` and `validateFormats: false`**.
  The meta-schema is third-party and is not written to Ajv's strict rules, so strict mode can
  refuse to compile it for reasons unrelated to our documents. It also uses `format` as an
  annotation, the JSON Schema 2020-12 default, and the contract does not depend on
  `ajv-formats`

Relaxing this instance relaxes nothing on the contract's own schemas: it only decides whether
each OpenAPI document is a well-formed OpenAPI 3.1 document.

## One in-memory rewrite

The meta-schema refers to schema objects through `$dynamicRef: "#meta"`. In this standalone file
the only `meta` dynamic anchor is `$defs/schema`, so each such reference resolves to
`$defs/schema`. Ajv 8 resolves it to the wrong schema, and then validates schema objects as if
they were parameter objects. So, after the digest check, the checks replace each
`$dynamicRef: "#meta"` with the equivalent `$ref: "#/$defs/schema"` **in memory**
(`withStaticMetaRefs` in `scripts/checks/meta.ts`). The file on disk is never changed.

`$defs/schema` accepts any object or boolean: this meta-schema checks that a document is
well-formed OpenAPI, not the JSON Schema inside it. The contract's schemas themselves are
compiled by the strict instance.
