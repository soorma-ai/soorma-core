<!-- SPDX-License-Identifier: Apache-2.0 -->

# Errors

Every error is **RFC 9457 Problem Details**, served as `application/problem+json`, with a stable,
machine-readable `code`. The `Problem` schema is in [`components.openapi.yaml`](components.openapi.yaml).

## Error codes

**The code set is open.** A client tolerates codes it does not know, and a surface may add codes.

| Code                                | Status | When                                                                                                                                                                                                                                                        | Detail returned                                                                                                                                                                 |
| ----------------------------------- | ------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `malformed_request`                 | 400    | The body is not JSON, or fails the schema; or the operation names no security scheme and an `Authorization` or `Soorma-Delegation` header is present                                                                                                        | `errors[]`, each with a JSON Pointer (`pointer`) or a request header name (`header`), never a header value                                                                      |
| `unknown_field`                     | 400    | A field the closed draft does not define, other than a platform-stamped field                                                                                                                                                                               | A pointer to the field                                                                                                                                                          |
| `stamped_field_set`                 | 400    | A draft sets a platform-stamped field, `envelopeVersion` included. Takes precedence over `unknown_field`                                                                                                                                                    | A pointer to the field                                                                                                                                                          |
| `invalid_inbound_context`           | 400    | The seal fails, is from another environment, the scope differs, the envelope version is not accepted, or the forwarded envelope exceeds the envelope bound                                                                                                  | **None**: one code for every cause                                                                                                                                              |
| `chain_too_deep`                    | 400    | The actor chain would exceed `maxChainDepth` (32)                                                                                                                                                                                                           | None                                                                                                                                                                            |
| `envelope_too_large`                | 400    | The envelope to be stamped would exceed the envelope bound, 16 KiB on its JCS serialization                                                                                                                                                                 | None                                                                                                                                                                            |
| `unsupported_contract_version`      | 400    | The declared contract version is not accepted                                                                                                                                                                                                               | `supportedVersions`                                                                                                                                                             |
| `secret_rejected`                   | 400    | A new secret fails the secret policy, after the presented material verified                                                                                                                                                                                 | `errors[]` with exactly one entry: the field's `pointer`, and its `reason`, an open set (`too_short`, `too_long`, `disallowed_character`, `breached`, `reused`, `context_word`) |
| `unknown_permission`                | 400    | A grant names a well-formed permission identifier that this environment does not accept (only the plane-declared identifiers are accepted in this contract version)                                                                                         | `errors[]`, a `pointer` to each such identifier, at most 10                                                                                                                     |
| `unknown_principal`                 | 400    | A grant names a human principal that does not exist in the environment's organization, or of another organization; reported only to a caller holding `grant:human`                                                                                          | `errors[]` with one entry: the `pointer` `/target`                                                                                                                              |
| `human_only_permission`             | 400    | A registration's standing set contains a human-only permission (`grant:human`, `human:manage`, `agent:delegate`), whatever the sponsor holds                                                                                                                | `errors[]`, a `pointer` to each such entry, at most 10                                                                                                                          |
| `declaration_outside_standing`      | 400    | A registration's re-broadening declaration names a permission its standing set does not contain                                                                                                                                                             | `errors[]`, a `pointer` to each such entry, at most 10                                                                                                                          |
| `unknown_registration`              | 400    | A registration secret is requested for a logical agent not registered in this environment; reported only to a caller holding `agent:register`                                                                                                               | `errors[]` with one entry: the `pointer` `/registration`                                                                                                                        |
| `credential_refused`                | 401    | On an operation that names a security scheme: every credential failure except a verified expiry: missing, malformed, unverifiable, revoked, ended, wrong environment, wrong kind for this surface, an extra credential, or the `Soorma-Delegation` header   | **None**                                                                                                                                                                        |
| `credential_expired`                | 401    | The credential verifies with this environment's material, and has expired                                                                                                                                                                                   | None                                                                                                                                                                            |
| `forbidden`                         | 403    | Authority denied                                                                                                                                                                                                                                            | **None**                                                                                                                                                                        |
| `exceeds_sponsor_ceiling`           | 403    | A registration's standing set names a permission the sponsor does not hold in this environment; decided after the sponsor's own authority to register                                                                                                       | `errors[]`, a `pointer` to each standing entry not held, at most 10. It names only the caller's own requested entries                                                           |
| `authentication_failed`             | 403    | Every failure to authenticate a human on sign-in, first authentication, or material change: an unknown principal or organization, wrong material, a used enrollment material, or a principal in the wrong state for the operation. One code for every cause | **None**                                                                                                                                                                        |
| `second_factor_enrollment_required` | 403    | The organization requires a second factor, none is enrolled, and the presented secret verified (sign-in, renewal)                                                                                                                                           | None beyond the code: the second factor must be enrolled first                                                                                                                  |
| `second_factor_not_confirmed`       | 403    | A second-factor confirmation fails after the current material verified                                                                                                                                                                                      | **None**                                                                                                                                                                        |
| `registration_exists`               | 409    | A registration names a logical agent identifier already registered in this environment; decided after authority and the sponsor ceiling                                                                                                                     | `errors[]` with one entry: the `pointer` `/agent`                                                                                                                               |
| `secret_limit_reached`              | 409    | The registration already has the maximum number of active registration secrets (10); reported only to a caller who may issue for it                                                                                                                         | None                                                                                                                                                                            |
| `payload_too_large`                 | 413    | The body exceeds the published size bound                                                                                                                                                                                                                   | None                                                                                                                                                                            |
| `too_many_attempts`                 | 429    | The abuse bound on bootstrap, sign-in, first authentication, or material change                                                                                                                                                                             | `Retry-After`                                                                                                                                                                   |
| `unavailable`                       | 503    | Revocation state cannot be read within the propagation bound (the request fails closed), or another dependency fails                                                                                                                                        | `Retry-After`                                                                                                                                                                   |
| `internal_error`                    | 500    | Anything unexpected                                                                                                                                                                                                                                         | None                                                                                                                                                                            |

## Disclosure

- **Specific for validation, generic for trust.** A validation error names the field. A trust
  failure (credential, authority, forwarded context) names nothing beyond its code. Only the
  validation codes carry a pointer, or, for `malformed_request`, a header name
- **`credential_expired` is returned only after the credential verifies with this environment's
  material.** A credential that does not verify, whatever its expiry, is `credential_refused`. So
  expiry is never disclosed for a credential from another environment
- No response discloses another environment, or whether a principal or registration exists
  elsewhere
- **Within an environment, whether a logical agent identifier is taken is learnable by a holder of
  `agent:register`** (`registration_exists`, `unknown_registration`): identifiers are chosen by
  the client and never reused
- **`too_many_attempts` does not reveal whether its subject exists**: an unknown registration or
  principal is bounded and refused like a known one
- **No response carries a stack trace**, internal path, framework or version detail, or datastore
  detail

## Response headers

- A **401** carries `WWW-Authenticate: Bearer`
- A **403** carries no `WWW-Authenticate`: `authentication_failed`, `second_factor_enrollment_required`,
  and `second_factor_not_confirmed` refuse presented material, not a bearer credential
- A **429** and a **503** carry `Retry-After`
- Every response carries `Soorma-Contract-Version` (the server's contract version) and
  `Soorma-Request-Id`

## Check order

A request is refused with the first check it fails, so a refusal is deterministic:

1. Body size: `payload_too_large`
2. Credential presentation and kind: `credential_refused`
3. Credential verification, then expiry: `credential_refused`, then `credential_expired`
4. Environment, and revocation state: `credential_refused`; `unavailable` if unreadable
5. Contract version: `unsupported_contract_version`, for a version not accepted **and for a
   missing `Soorma-Contract-Version` header** on a call without a draft. **On a call with a
   draft**: a body that is not a JSON object is `malformed_request`; a missing or non-string
   `clientContractVersion` is `unsupported_contract_version`; then a `Soorma-Contract-Version`
   header sent more than once, or different from the draft's value, is `malformed_request`,
   naming the header
6. Request body or draft schema; for a grant, then the accepted permission identifiers
   (`unknown_permission`); for a registration, then the accepted identifiers in both sets
   (`unknown_permission`), the human-only class (`human_only_permission`), and the declaration
   within the standing set (`declaration_outside_standing`). Draft schema, **stamped fields before unknown fields**: `malformed_request`,
   `stamped_field_set`, `unknown_field`. **The precedence is fixed**: a platform-stamped field at
   the draft's top level is `stamped_field_set`, whatever else fails; otherwise a field the draft
   or its `traceContext` does not define is `unknown_field`; otherwise any other failure, a
   trace-context rule included, is `malformed_request`. The code is picked from every failure;
   `errors[]` then lists the fields failing with the winning code, ordered by pointer, **at most
   10**: the first 10 by pointer
7. Forwarded context: seal, scope, envelope version: `invalid_inbound_context`. **A forwarded
   envelope over the envelope bound is refused here, before its seal is computed**
8. Chain depth: `chain_too_deep`
9. Origin, then authority: `forbidden`. For a grant, then the target principal: `unknown_principal`. For a
   registration, then the sponsor ceiling (`exceeds_sponsor_ceiling`), and at the write a taken
   identifier (`registration_exists`). For a registration secret, then the registration
   (`unknown_registration`), then sponsor or Admin (`forbidden`), then the cap
   (`secret_limit_reached`)
10. **The size of the envelope to be stamped, last**: `envelope_too_large`. Last, because the
    envelope's final form, including any re-broadening record, is known only after authority

An unauthenticated surface (bootstrap, sign-in, first authentication, material change: an
operation that names no security scheme) runs step 1, then **refuses a presented
`Authorization` or `Soorma-Delegation` header with `malformed_request`**, naming the header,
then continues from step 5. It applies its abuse bound before verifying any presented
material. A `401` would be wrong there: it carries `WWW-Authenticate: Bearer`, and no bearer
credential can succeed on such an operation.

## Unknown paths

**In this contract version, a request to a path or method that no surface document defines is
answered `404` with no body: not a Problem.** The response still carries `Soorma-Contract-Version`
and `Soorma-Request-Id`. No error code is defined for it, and a client must not expect one.
Defining a Problem for it later would be an addition.

## What soorma-core emits, and what a client accepts

**Every Problem soorma-core emits carries `type`, `title`, `status`, `code`, and `instance`**:

- `type` is `urn:soorma:problem:{code}`, where `{code}` equals `code`
- `instance` is `urn:soorma:request:{request id}`, equal to the response's `Soorma-Request-Id`

**A client accepts any problem.** A gateway or proxy may emit one with `type: about:blank` and no
`code` or `instance`. The `Problem` schema therefore requires no field and constrains no value's
form; a client must not reject a problem for a missing field or an unfamiliar `type`.
