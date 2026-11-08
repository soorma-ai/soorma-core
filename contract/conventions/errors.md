<!-- SPDX-License-Identifier: Apache-2.0 -->

# Errors

Every error is **RFC 9457 Problem Details**, served as `application/problem+json`, with a stable,
machine-readable `code`. The `Problem` schema is in [`components.openapi.yaml`](components.openapi.yaml).

## Error codes

**The code set is open.** A client tolerates codes it does not know, and a surface may add codes.

| Code                           | Status | When                                                                                                                                                                                                        | Detail returned                      |
| ------------------------------ | ------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------ |
| `malformed_request`            | 400    | The body is not JSON, or fails the schema                                                                                                                                                                   | `errors[]`, each with a JSON Pointer |
| `unknown_field`                | 400    | A field the closed draft does not define, other than a platform-stamped field                                                                                                                               | A pointer to the field               |
| `stamped_field_set`            | 400    | A draft sets a platform-stamped field, `envelopeVersion` included. Takes precedence over `unknown_field`                                                                                                    | A pointer to the field               |
| `invalid_inbound_context`      | 400    | The seal fails, is from another environment, the scope differs, or the envelope version is not accepted                                                                                                     | **None**: one code for every cause   |
| `chain_too_deep`               | 400    | The actor chain would exceed `maxChainDepth` (32)                                                                                                                                                           | None                                 |
| `envelope_too_large`           | 400    | The envelope to be stamped would exceed the envelope bound, 16 KiB on its JCS serialization                                                                                                                 | None                                 |
| `unsupported_contract_version` | 400    | The declared contract version is not accepted                                                                                                                                                               | `supportedVersions`                  |
| `credential_refused`           | 401    | Every credential failure except a verified expiry: missing, malformed, unverifiable, revoked, ended, wrong environment, wrong kind for this surface, an extra credential, or the `Soorma-Delegation` header | **None**                             |
| `credential_expired`           | 401    | The credential verifies with this environment's material, and has expired                                                                                                                                   | None                                 |
| `forbidden`                    | 403    | Authority denied                                                                                                                                                                                            | **None**                             |
| `payload_too_large`            | 413    | The body exceeds the published size bound                                                                                                                                                                   | None                                 |
| `too_many_attempts`            | 429    | The abuse bound on bootstrap, sign-in, or first authentication                                                                                                                                              | `Retry-After`                        |
| `unavailable`                  | 503    | Revocation state cannot be read within the propagation bound (the request fails closed), or another dependency fails                                                                                        | `Retry-After`                        |
| `internal_error`               | 500    | Anything unexpected                                                                                                                                                                                         | None                                 |

## Disclosure

- **Specific for validation, generic for trust.** A validation error names the field. A trust
  failure (credential, authority, forwarded context) names nothing beyond its code. Only the
  validation codes carry a pointer
- **`credential_expired` is returned only after the credential verifies with this environment's
  material.** A credential that does not verify, whatever its expiry, is `credential_refused`. So
  expiry is never disclosed for a credential from another environment
- No response discloses another environment, or whether a principal or registration exists
  elsewhere
- **`too_many_attempts` does not reveal whether its subject exists**: an unknown registration or
  principal is bounded and refused like a known one
- **No response carries a stack trace**, internal path, framework or version detail, or datastore
  detail

## Response headers

- A **401** carries `WWW-Authenticate: Bearer`
- A **429** and a **503** carry `Retry-After`
- Every response carries `Soorma-Contract-Version` (the server's contract version) and
  `Soorma-Request-Id`

## Check order

A request is refused with the first check it fails, so a refusal is deterministic:

1. Body size: `payload_too_large`
2. Credential presentation and kind: `credential_refused`
3. Credential verification, then expiry: `credential_refused`, then `credential_expired`
4. Environment, and revocation state: `credential_refused`; `unavailable` if unreadable
5. Contract version: `unsupported_contract_version`
6. Draft schema, **stamped fields before unknown fields**: `malformed_request`,
   `stamped_field_set`, `unknown_field`
7. Forwarded context: seal, scope, envelope version: `invalid_inbound_context`
8. Chain depth: `chain_too_deep`
9. Origin, then authority: `forbidden`
10. **The size of the envelope to be stamped, last**: `envelope_too_large`. Last, because the
    envelope's final form, including any re-broadening record, is known only after authority

An unauthenticated surface (bootstrap, sign-in, first authentication) starts at step 5, and
applies its abuse bound before verifying any presented material.

## What soorma-core emits, and what a client accepts

**Every Problem soorma-core emits carries `type`, `title`, `status`, `code`, and `instance`**:

- `type` is `urn:soorma:problem:{code}`, where `{code}` equals `code`
- `instance` is `urn:soorma:request:{request id}`, equal to the response's `Soorma-Request-Id`

**A client accepts any problem.** A gateway or proxy may emit one with `type: about:blank` and no
`code` or `instance`. The `Problem` schema therefore requires no field and constrains no value's
form; a client must not reject a problem for a missing field or an unfamiliar `type`.
