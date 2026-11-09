<!-- SPDX-License-Identifier: Apache-2.0 -->

# Versioning

## Contract version

The contract version is **SemVer `0.y.z`** while the contract is pre-release. **The first published
version is `0.1.0`, at the git tag `contract-v0.1.0`** on soorma-core's `main`. It versions the
whole contract: the envelope and Delivery schemas, these conventions, and the surface documents.

The **envelope version** (`envelopeVersion`, an integer, `1`) is the envelope's own version. It
is distinct from the contract version.

## The client contract version

A client declares the contract version it was built against:

- **A call with a draft** declares it in the draft's `clientContractVersion`
- **A call without a draft** sends the required `Soorma-Contract-Version` request header
- On a call with a draft, the header may be sent, but then it must equal the draft's value

Every response carries `Soorma-Contract-Version`, set to the server's contract version.

## Accepted versions

- **The accepted set in this version is `{0.1.0}`**
- Matching is **exact; no ranges**
- **A version once accepted stays accepted until a published deprecation window, longer than
  zero, elapses.** The window is not exercised in this version
- A version not accepted is refused with `unsupported_contract_version`, listing
  `supportedVersions`
- **A call without a draft that sends no `Soorma-Contract-Version` header is refused the same
  way**: `unsupported_contract_version`, listing `supportedVersions`, at step 5 of the check
  order ([errors.md](errors.md)). Declaring no version is not declaring an accepted one

## Change classification

Every contract change is classified, and recorded in [`../CHANGELOG.md`](../CHANGELOG.md).

| Change                                                                                      | Envelope v1                                                         | Anything else in the contract                       |
| ------------------------------------------------------------------------------------------- | ------------------------------------------------------------------- | --------------------------------------------------- |
| Add an optional field, a new operation, a new error code, or a new credential kind          | Compatible                                                          | Compatible, in the current `0.y` line or the next   |
| Widen a value set                                                                           | Compatible, because enumerated values are open strings              | Compatible                                          |
| **Widen an identifier pattern or length**                                                   | **Compatible**, because received identifiers are opaque             | **Compatible**                                      |
| Add a required field; remove, rename, or re-mean a field; change what a credential binds to | **Not in this contract version: no breaking change to envelope v1** | **Breaking**: a new `0.y` version while pre-release |
| Lower `maxChainDepth`, or change the actor chain's order or minimum length                  | **Never within envelope v1**                                        | —                                                   |

For credentials: a new kind, or a new asserted attribute, is compatible; changing what a
credential binds to is breaking.

## Fixture classification

The compatibility test validates every version's fixtures (`../fixtures/{version}/`) against the
current schemas:

- **An earlier valid fixture that now fails is a breaking change**
- **An earlier invalid fixture that now passes is a widening**, compatible under the
  classification above

Either outcome fails the test unless `CHANGELOG.md` classifies that fixture's change, and the
classification must match the outcome. The form is given in the changelog.
