<!-- SPDX-License-Identifier: Apache-2.0 -->

# Identifiers and Times

## Comparison

Every identifier is **case-sensitive and compared exactly**: no normalization, trimming, or
case-folding. An identifier is unique within its scope (an environment for agents and
credentials; an organization for human principals): global uniqueness is composed with scope,
never allocated. An identifier is always a value, never interpolated into a query, path, or log
without encoding.

**An agent instance identifier is the agent's own assertion**, made at bootstrap: the platform
records it and never enforces it unique. Two live credentials of one agent may assert the same
instance identifier, as when a restarted instance bootstraps again under its old name while its
earlier credential runs out.

## Syntax per kind (request inputs only)

The shared definitions are in [`components.openapi.yaml`](components.openapi.yaml).

| Kind                                                       | Definition                 | Pattern          | Length   |
| ---------------------------------------------------------- | -------------------------- | ---------------- | -------- |
| Organization, project, environment                         | `ConfiguredIdentifier`     | strict           | 1 to 64  |
| Logical agent                                              | `LogicalAgentIdentifier`   | strict           | 1 to 64  |
| Registration, credential, grant, secret, request reference | `PlatformReference`        | strict           | 1 to 64  |
| Agent instance                                             | `InstanceIdentifier`       | strict, plus `:` | 1 to 128 |
| Human principal                                            | `HumanPrincipalIdentifier` | human            | 1 to 256 |
| Permission                                                 | `PermissionIdentifier`     | permission       | 1 to 128 |

| Pattern          | Regular expression                         |
| ---------------- | ------------------------------------------ |
| strict           | `^[A-Za-z0-9][A-Za-z0-9._~-]*$`            |
| strict, plus `:` | `^[A-Za-z0-9][A-Za-z0-9._~:-]*$`           |
| human            | ``^[A-Za-z0-9!#$%&'*+/=?^_`{\|}~.@:-]+$``  |
| permission       | `^[a-z][a-z0-9._-]*(:[a-z][a-z0-9._-]*)+$` |

In the human pattern, `\|` is the table's escape for the `|` character: the pattern itself
contains a single `|` (the vertical bar of `issuer|subject`).

A human principal identifier admits email addresses and external-subject forms (`issuer|subject`).
**Human principal identifiers are ASCII-only in this contract version**: internationalized email
addresses are not accepted. This is a delivery limit, and widening the pattern later is
compatible.

Every pattern is anchored and in the portable, linear-time subset (no lookaround, backreferences,
or named groups), and no `format` keyword is used anywhere in the contract.

## Received identifiers are opaque

**Identifier patterns and lengths constrain only what the platform accepts.** Wherever an
identifier is received (in the envelope, the Delivery, or a response), it is a plain string.
**Do not validate the syntax of a received identifier.** So **widening a pattern or a length later
is compatible**: no consumer can be broken by an identifier it did not expect. The envelope as a
whole stays bounded (16 KiB on its JCS serialization).

## Times

Times are **RFC 3339 in UTC, with a `Z` suffix**.
