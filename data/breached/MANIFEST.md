<!-- SPDX-License-Identifier: FSL-1.1-ALv2 -->

# Breached-Secret List

The list K is checked against (BR-K-05; NFR-OI-13). Derived by
`node tools/breached/derive.ts` from the pinned source below, which is never committed.
`pnpm run check:breached` checks the derived file's SHA-256 against this manifest, and S1
refuses to start if it differs.

| Field | Value |
| --- | --- |
| Source repository | https://github.com/danielmiessler/SecLists |
| Pinned commit | `00f80ec9cc39bed63ee40cf6805a6b1b77e87644` (2026-10-31) |
| Path | `Passwords/Common-Credentials/xato-net-10-million-passwords-1000000.txt` |
| Unchanged since | `c205c36a445bff37f8e58a9ec829105cd4975c58` (2025-05-08), the file's only commit, which moved it into `Common-Credentials`. SecLists removed `10-million-password-list-top-1000000.txt` as its duplicate (`4ff3ff8`) |
| Licence | MIT (Copyright (c) 2018 Daniel Miessler), checked at the pinned commit |
| Source SHA-256 | `424a3e03a17df0a2bc2b3ca749d81b04e79d59cb7aeec8876a5a3f308d0caf51` |
| Source size | 8557632 bytes; 999999 non-empty lines; 999996 distinct entries after NFKC |
| Derivation | Each entry NFKC-normalized, hashed with SHA-256 over its UTF-8, truncated to the first 64 bits; distinct values sorted ascending; written big-endian, 8 bytes each |
| Derived file | `top-1m.sha256-64.bin` (999996 prefixes, 7999968 bytes) |
| Derived file SHA-256 | `17b8378e40ebae08c3712545831b847be93f4831f25c3dcf3364a2164f5bd9dd` |
