<!-- SPDX-License-Identifier: Apache-2.0 -->

# Contract Changelog

Every change to the soorma wire contract is recorded here and classified under the compatibility
policy in [conventions/versioning.md](conventions/versioning.md).

## How changes are classified

| Change                                                                                      | Classification                                                           |
| ------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------ |
| Add an optional field, an operation, an error code, or a credential kind                    | Compatible                                                               |
| Widen a value set, or an identifier pattern or length                                       | Compatible                                                               |
| Add a required field; remove, rename, or re-mean a field; change what a credential binds to | Breaking. **No breaking change to envelope v1** in this contract version |
| Lower `maxChainDepth`, or change the actor chain's order or minimum length                  | Never within envelope v1                                                 |

## Fixture classifications

The compatibility test validates every fixture of every version in [`fixtures/`](fixtures/)
against the current schemas:

- **An earlier valid fixture that now fails is a breaking change**
- **An earlier invalid fixture that now passes is a widening**, which is compatible

Either outcome fails the test unless this changelog classifies that fixture's change, and the
classification must match the outcome. Record it under the version that makes the change, one line
per fixture, in exactly this form:

```text
- fixture `0.1.0/envelope/invalid/chain-33-entries.json`: compatible
- fixture `0.1.0/envelope/valid/sample.json`: breaking
```

## Obligations carried forward

- **An automated OpenAPI diff is added with the first change after `contract-v0.1.0` is tagged**,
  once a second contract version exists to compare against (NFR-WC-03)

## 0.1.0 (unreleased; to be tagged `contract-v0.1.0` after the surface units)

The baseline. Every element is new, so each is classified **compatible (initial)**. The fixtures
in `fixtures/0.1.0/` are the baseline every later version is tested against.

| Element                                                                                                                              | Classification       |
| ------------------------------------------------------------------------------------------------------------------------------------ | -------------------- |
| Envelope v1: seven fields, open at every level; `originMode` an open enumeration; `actorChain` 1 to 32 entries                       | Compatible (initial) |
| The draft: closed; platform-stamped fields forbidden by name; `clientContractVersion` and `traceContext` required                    | Compatible (initial) |
| Forwarded context (`inbound`): a closed wrapper around an open envelope, with its seal                                               | Compatible (initial) |
| Two `traceContext` definitions: closed in a draft, open in an envelope                                                               | Compatible (initial) |
| The Delivery: `{ envelope, seal, payload }`, open                                                                                    | Compatible (initial) |
| Problem Details: no required field; an open `code` set of fourteen codes                                                             | Compatible (initial) |
| Identifier definitions for request inputs, per kind                                                                                  | Compatible (initial) |
| The `Soorma-Contract-Version` parameter and header; the `Soorma-Request-Id` and `Retry-After` headers                                | Compatible (initial) |
| Security schemes `agentCredential`, `environmentCredential`, `signIn`; typed prefixes; `Soorma-Delegation` and `soorma_dc_` reserved | Compatible (initial) |
| The conventions: envelope-bearing operations, errors and check order, credentials, identifiers, versioning, pre-release statements   | Compatible (initial) |

### Added by U2 `org-identity` (S1 `org-gateway`), within unreleased 0.1.0

| Change                                                                                                                                                                                                                                | Classification                                                                                                                                                  |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| New document `org-gateway.openapi.yaml`: `firstAuthenticate`, `authenticate`, `renewSignIn`, `endSignIn`, `changeMaterial`; request bodies closed, responses open                                                                     | Compatible: new operations                                                                                                                                      |
| New error code `authentication_failed` (403): every failure to authenticate a human, one code for every cause                                                                                                                         | Compatible: the code set is open                                                                                                                                |
| New error code `second_factor_enrollment_required` (403)                                                                                                                                                                              | Compatible: the code set is open                                                                                                                                |
| New error code `second_factor_not_confirmed` (403)                                                                                                                                                                                    | Compatible: the code set is open                                                                                                                                |
| New error code `secret_rejected` (400), with one `errors[]` entry carrying `pointer` and `reason`                                                                                                                                     | Compatible: the code set is open                                                                                                                                |
| `ProblemFieldError.reason`, optional, typed as the new open enumeration `SecretRejectedReason` (`too_short`, `too_long`, `disallowed_character`, `breached`, `reused`, `context_word`)                                                | Compatible: an optional member of an open object; an open value set                                                                                             |
| `too_many_attempts`: its _When_ widens to material change                                                                                                                                                                             | Compatible: a wider _When_ for an existing code                                                                                                                 |
| The 403 refusals carry no `WWW-Authenticate`                                                                                                                                                                                          | Compatible                                                                                                                                                      |
| New shared definitions `HumanPrincipalReferenceInput` (request side) and `HumanPrincipalReference` (received side)                                                                                                                    | Compatible: additions                                                                                                                                           |
| **Amendment A4**: on an operation that names no security scheme, a presented `Authorization` or `Soorma-Delegation` header is `malformed_request` (400) naming the header; `credential_refused` is scoped to operations that name one | A change within unreleased 0.1.0: `contract-v0.1.0` is not tagged, so no client depends on the earlier text. Released, it would be breaking (a changed meaning) |
| **Amendment A4**: `ProblemFieldError.header`, optional, names a request header                                                                                                                                                        | Compatible: an optional member of an open object                                                                                                                |
| The fixtures in `fixtures/0.1.0/org-gateway/` and the new `fixtures/0.1.0/problem/` fixtures                                                                                                                                          | Compatible (initial): part of the 0.1.0 baseline                                                                                                                |

No fixture classifications: no fixture's outcome has changed.
