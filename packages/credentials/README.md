<!-- SPDX-License-Identifier: FSL-1.1-ALv2 -->

# `@soorma/credentials` (P5)

An environment's own credentials, minted and verified with its own key ring, and their records.
In M1 this is the **human environment credential** that S2 issues.

## The key ring

`loadEnvironmentKeyRing(keys)` builds one signing key and a set of verify keys, each Ed25519,
each identified by its RFC 7638 thumbprint (`kid`), from the environment's configuration. It is
held in memory: no key is written to the store, and nothing is published, because only the
environment's own S2 instances verify its credentials. Start-up fails on a key that is not an
Ed25519 PKCS #8 private key, a signing key missing from the verify keys, or one key listed twice.

## The token

`soorma_ec_` followed by a JWS (compact serialization) with `typ: soorma-ec+jwt` and `alg:
Ed25519`, fixed in code. Every claim is required:

| Claim        | Meaning                                                                     |
| ------------ | --------------------------------------------------------------------------- |
| `env`        | `{ organization, project, environment }`, compared field by field           |
| `sub`        | The principal identifier, in `env.organization`                             |
| `cid`        | The credential record's id                                                  |
| `jti`        | This token's id. Renewal mints a new `jti` for the same `cid`               |
| `iat`, `exp` | Seconds since the epoch. No leeway on `exp`; `iat` at most 30 seconds ahead |

`mintEnvironmentCredential` signs with the current signing key only.
`verifyEnvironmentCredential` checks, in order, the prefix, the header, the `kid`, the
signature, the claims, `exp`, `iat`, and `env`, and returns a refusal rather than throwing.
Another environment's credential fails at its `kid` or signature, before its expiry is read.

## The record governs liveness

The last check is the caller's: `readCredential` and `checkCredentialRecord` (O3) read the
record by `cid`, **uncached**, and require it to exist, be `live`, and match the token's `sub`
and `env`. Tokens are not tracked one by one: `endCredential` ends the record, which refuses
every token minted for it. `renewCredential` and `endCredential` are conditional updates on
`state = 'live'`, so a renewal racing an end commits exactly one outcome. Writes run over the
caller's transaction, with the attribution record.
