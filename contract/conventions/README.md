<!-- SPDX-License-Identifier: Apache-2.0 -->

# soorma Wire Contract Conventions

**Contract version**: `0.1.0` · **Status**: pre-release

This directory is the written half of the soorma wire contract. The machine-readable half is
[`../envelope.schema.json`](../envelope.schema.json), [`../delivery.schema.json`](../delivery.schema.json),
and the shared components in [`components.openapi.yaml`](components.openapi.yaml). Everything
here is readable without the code, so a raw caller that never links an SDK can build against it
and reaches identical enforcement: every rule is enforced by the platform's perimeter, and no rule
exists only in an SDK.

## Pre-release status

This contract is **pre-release** (`0.y.z`). **The operations, error codes, and credential
presentation may change between `0.y` versions.** **Envelope v1 does not**: it is held to the
envelope compatibility policy from this version on. **Event delivery semantics are unspecified
at this version.** See [pre-release.md](pre-release.md) for every pre-release statement.

## Contents

| Document                                         | Covers                                                                                                                               |
| ------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------ |
| [envelope.md](envelope.md)                       | The envelope, the draft, forwarded context, the seal, envelope-bearing operations, the envelope bound, and the rules checked in code |
| [errors.md](errors.md)                           | Problem Details, the error codes, what each discloses, and the check order                                                           |
| [credentials.md](credentials.md)                 | Credential presentation, typed prefixes, and the security schemes                                                                    |
| [identifiers.md](identifiers.md)                 | Identifier syntax per kind, exact comparison, and times                                                                              |
| [versioning.md](versioning.md)                   | Contract versions, the client contract version, and change classification                                                            |
| [pre-release.md](pre-release.md)                 | The pre-release statements                                                                                                           |
| [adding-an-operation.md](adding-an-operation.md) | How a surface document adds an operation                                                                                             |

The valid fixtures in [`../fixtures/`](../fixtures/) double as examples of every schema.

## Shared definitions

Defined once, in [`components.openapi.yaml`](components.openapi.yaml), and referenced by every
surface document, never copied: `Envelope`, `Draft`, `Inbound`, `Delivery`, `ContractVersion`,
`Problem`, the identifier definitions, the `Soorma-Contract-Version` parameter and header, the
`Soorma-Request-Id` and `Retry-After` headers, and the security schemes `agentCredential`,
`environmentCredential`, and `signIn`.
