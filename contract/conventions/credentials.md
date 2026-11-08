<!-- SPDX-License-Identifier: Apache-2.0 -->

# Credentials

## Presentation

- **A credential is presented only as `Authorization: Bearer {credential}`. One per request**
- A credential presented anywhere else is refused with `credential_refused`: in another header,
  a cookie, or a query parameter. **No cookies** are used in this contract version
- **No CORS**: no browser origin is allowed. Allowing one later will be an explicit list, never
  `*`

## Typed prefixes

**A credential's kind is readable from its typed prefix, without verifying it:**

| Kind                         | Prefix       | Presented at                                      |
| ---------------------------- | ------------ | ------------------------------------------------- |
| Agent credential             | `soorma_ac_` | S3 renewal; S4 publish and subscribe              |
| Human environment credential | `soorma_ec_` | S2, in its own environment only                   |
| Organization sign-in         | `soorma_si_` | S1; and S2's environment credential issuance only |
| Delegation credential        | `soorma_dc_` | **Reserved.** No path in this version issues one  |

**The prefix selects how a credential is checked. It never admits one.** A credential is accepted
only after it verifies, and its verified kind must match its prefix; otherwise it is
`credential_refused`.

## Syntax

A credential is opaque to clients. **The whole credential, prefix included, is an RFC 6750
`b64token`**: letters, digits, `-`, `.`, `_`, `~`, `+`, `/`, then optional trailing `=`. **It is
at most 4096 characters.** Every response that issues a credential states its expiry as an RFC
3339 time.

## Material is not a credential

The **registration secret** (`soorma_rs_`) and **enrollment material** (`soorma_em_`) are
material, not credentials. **They go in a request body, never in `Authorization`.** Each is at
most 256 characters. Their typed prefixes let secret scanners find them, and keep them from being
taken for credentials.

## Reserved: delegation

**The `Soorma-Delegation` header is reserved** for a delegation credential presented beside an
agent credential. In this contract version, any request carrying it is refused with
`credential_refused`. Delegation-credential presentation will be added without a breaking change.

## Security schemes

Defined in [`components.openapi.yaml`](components.openapi.yaml), each HTTP bearer:
`agentCredential`, `environmentCredential`, and `signIn`. Each surface document names, per
operation, exactly which one it accepts. Bootstrap, sign-in, and first authentication name none.
