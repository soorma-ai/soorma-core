<!-- SPDX-License-Identifier: Apache-2.0 -->

# Pre-Release Statements

These hold for contract version `0.1.0`.

1. **This contract is pre-release (`0.y.z`).** The operations, error codes, and credential
   presentation may change between `0.y` versions. **Envelope v1 does not**: it follows the
   envelope compatibility policy from this version on
2. **Event delivery semantics are unspecified at this version.** Delivery reaches **live
   subscribers only**, with **no durability, ordering, redelivery, or acknowledgement** promised.
   Do not rely on observed behaviour
3. **The bootstrap exchange and credential renewal carry no envelope**
4. **The accepted permission identifiers may widen in a compatible version.** In this version,
   only the plane-declared identifiers are accepted
5. **A draft never carries origin mode.** Accepting an asserted origin later would be additive
6. **Delegation-credential presentation will be added without a breaking change.** The
   `Soorma-Delegation` header and the `soorma_dc_` prefix are reserved
7. **`maxChainDepth` is 32 for envelope v1**
8. **The envelope bound is 16 KiB**, measured on the RFC 8785 (JCS) serialization, both for a
   forwarded envelope and for one the platform would stamp (`envelope_too_large`). **Received
   identifiers are opaque strings; do not validate their syntax**

**The Delivery payload bound is not set in this version of the conventions.** It is set by the
event transport unit, and published with it.
