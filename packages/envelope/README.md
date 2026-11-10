<!-- SPDX-License-Identifier: FSL-1.1-ALv2 -->

# `@soorma/envelope` (P2)

The envelope perimeter: check-order steps 5 to 8 and 10, the seal, and the key ring.

**No surface imports this package.** A surface (S4, at U7) calls the one entry point,
`createEnvelopeAdmission(dependencies).admit(request)` in `@soorma/authority`. That entry point
runs steps 5 to 10 in order, step 9 being P3's. The functions here are exported for the entry
point and for their own tests. The package imports no framework.

| Step | Function                          | Refusals                                                                                                                    |
| ---- | --------------------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| 5    | `checkVersion`                    | `malformed_request` (body not an object; a repeated or different `Soorma-Contract-Version`), `unsupported_contract_version` |
| 6    | `createDraftValidator().validate` | `stamped_field_set`, then `unknown_field`, then `malformed_request`                                                         |
| 7    | `verifyInbound`                   | `invalid_inbound_context`, one code for every cause                                                                         |
| 8    | `checkChainDepth`                 | `chain_too_deep` (`maxChainDepth` 32)                                                                                       |
| 10   | `stamp`                           | `envelope_too_large` (16384 bytes of the RFC 8785 form)                                                                     |

Each function returns a refusal and never throws one. A refusal carries an internal reason,
which goes only to the security log.

## The seal

```text
v1.{kid}.{mac}
mac = base64url( HMAC-SHA-256( key, "soorma.envelope-seal.v1" || 0x00 || JCS(envelope) ) )
```

- The `mac` is exactly 43 base64url characters, with no padding. The whole seal is at most 63
  characters.
- The label and the zero byte separate this use of the key from any other.
- Sealing uses the ring's **current** key.
- Verification:
  1. Parse the seal strictly.
  2. Check the `kid` is in the ring.
  3. Check the MAC decodes to 32 bytes and re-encodes to the same text.
  4. Recompute the MAC.
  5. Compare with `timingSafeEqual`.

  Checks 1 to 3 run before any MAC is computed. Any failure is `invalid_inbound_context`
  (`seal_failed`).

- The seal proves to this environment that it stamped the envelope, unaltered. It proves nothing
  to anyone else, and nothing about who forwarded it or when.

## The key ring

Each environment has its own ring, configured in that environment's part of `tenancy.yaml` in
U2's seed-key shape:

```yaml
sealKeys:
  current: k1
  keys:
    - { id: k1, secret: env-e-seal-k1 }
```

- **Each entry names its secret.** A file name is never derived from an id.
- Each secret is base64url text of 256 random bits, as `pnpm stack:init` writes symmetric keys.
- P9's `loadSealKeys` reads each key through the same path as the seed keys,
  `SecretReader.key(secret, true)`.
- `loadSealKeyRing` then checks the ids. **Any problem stops start-up.**
- The ring's secrets are mounted only into that environment's S4.

**The effective id rule is `^[a-z0-9][a-z0-9-]{0,15}$`.** P9's schema gives ids U2's `KeyId`
pattern, `^[a-z0-9][a-z0-9-]*$` with up to 32 characters. The seal's `kid` pattern is
`^[A-Za-z0-9][A-Za-z0-9_-]{0,15}$`, which `loadSealKeyRing` also checks. An id must pass both:
lowercase letters, digits, and `-`, at most 16 characters, starting with a letter or digit.

## Rotating a seal key

S4 may run several instances, so rotation is **two-phase**. Making a key current before every
instance holds it would make fresh seals fail on the instances that do not.

1. **Add** the new key on every instance. Generate its secret (base64url, 256 random bits), mount
   it, and add `{ id, secret }` to `sealKeys.keys`, leaving `current` unchanged. Restart every
   instance. Each now verifies seals under both keys, and still seals with the old one.
2. **Switch**: once every instance holds the new key, set `current` to its id and restart. New
   seals use the new key, and seals under the old key still verify.
3. **Remove**: after the overlap you choose, remove the old entry and its secret, and restart.
   An envelope sealed under the old key and forwarded after this is `invalid_inbound_context`.

There is no automatic rotation in M1.
