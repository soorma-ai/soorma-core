<!-- SPDX-License-Identifier: Apache-2.0 -->

# Credentials

## Presentation

- **A credential is presented only as `Authorization: Bearer {credential}`. One per request**
- A credential presented anywhere else is refused with `credential_refused`: in another header,
  a cookie, or a query parameter. **No cookies** are used in this contract version
- **An operation that names no security scheme accepts no credential.** A presented
  `Authorization` header there is refused with `malformed_request`, with an `errors[]` entry
  naming the header (see [`errors.md`](errors.md))
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

## Revocation and Lifetimes

- **Revocation reaches every request within 60 seconds.** This is the platform's propagation
  bound, set by the platform and not configurable per tenant. Past it, a surface that cannot read
  revocation state denies the request with `unavailable`: it never accepts one on stale state
- **An agent credential is valid for at most 15 minutes** from its bootstrap or its latest
  renewal, and **renewal never extends it past 24 hours** from its bootstrap. **Both are upper
  bounds only**: a shorter lifetime is always compatible, and either may change without a
  breaking change
- **A client therefore**:
  1. **Schedules renewal from the response's `expiresAt`**, the authority for every
     credential's expiry
  2. **Bootstraps again when renewal answers `credential_expired`** at the end of the
     credential's lifetime
  3. **Never hard-codes either lifetime**

## Reserved: delegation

**The `Soorma-Delegation` header is reserved** for a delegation credential presented beside an
agent credential. In this contract version, any request carrying it is refused: with
`credential_refused` on an operation that names a security scheme, and with
`malformed_request` naming the header on one that names none. Delegation-credential
presentation will be added without a breaking change.

## Security schemes

Defined in [`components.openapi.yaml`](components.openapi.yaml), each HTTP bearer:
`agentCredential`, `environmentCredential`, and `signIn`. Each surface document names, per
operation, exactly which one it accepts. Bootstrap, sign-in, and first authentication name none.
