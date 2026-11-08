<!-- SPDX-License-Identifier: Apache-2.0 -->

# soorma Wire Contract

**Contract version**: `0.1.0` · **Status**: pre-release · **Licence**: Apache 2.0 ([`LICENSE`](LICENSE))

The contract between soorma clients (the SDK, or any raw HTTP caller) and the soorma-core
platform. It is language-neutral: JSON Schema 2020-12 and OpenAPI 3.1, with written conventions.
Everything here is enforced by the platform's perimeter; nothing depends on a client library.

## Contents

| Path                                                                         | What it is                                                                                                        |
| ---------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| [`envelope.schema.json`](envelope.schema.json)                               | Envelope v1, the draft a client sends, and forwarded context (`inbound`)                                          |
| [`delivery.schema.json`](delivery.schema.json)                               | `Delivery`: one event on a subscriber's stream                                                                    |
| [`conventions/components.openapi.yaml`](conventions/components.openapi.yaml) | Shared components every surface document references: `Problem`, identifier definitions, headers, security schemes |
| [`conventions/`](conventions/README.md)                                      | The written conventions: start at its README                                                                      |
| [`generated/`](generated/)                                                   | TypeScript types generated from the schemas. Never edited by hand                                                 |
| [`fixtures/`](fixtures/)                                                     | Valid and invalid samples per contract version: the compatibility baseline, and examples                          |
| [`CHANGELOG.md`](CHANGELOG.md)                                               | Every contract change, classified as compatible or breaking                                                       |
| [`meta/`](meta/SOURCE.md)                                                    | The pinned OpenAPI 3.1 schema the documents are validated against                                                 |
| [`scripts/`](scripts/)                                                       | The type generator, the strict validator, and the contract checks                                                 |
| [`test/`](test/)                                                             | The contract's tests                                                                                              |

## Using it

**From another language**: take the schemas at a tag (`contract-v0.1.0` once published) and
generate your own types. Never share generated types by hand. Treat received identifiers as opaque
strings, keep unknown fields, and accept unknown enumeration values and error codes.

**In this repository**:

```sh
pnpm run generate          # regenerate contract/generated/ after changing a schema
pnpm run check:generated   # fail if the committed types differ from the schemas
pnpm run check:contract    # the contract rules, licences, meta-schema, and compatibility
```

## Changing it

Follow [`conventions/adding-an-operation.md`](conventions/adding-an-operation.md). Every change is
classified in [`CHANGELOG.md`](CHANGELOG.md), with new fixtures; an earlier fixture whose outcome
changes must be classified there too. **Envelope v1 takes no breaking change in this contract
version.**
