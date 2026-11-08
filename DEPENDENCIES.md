<!-- SPDX-License-Identifier: FSL-1.1-ALv2 -->

# Dependency Register

Every direct dependency of every workspace package, and every exception to the dependency
policy, is recorded here and reviewed with the change that adds it (NFR-WC-13). CI fails if a
direct dependency has no row (`pnpm run check:deps`).

**Policy** (NFR-WC-12 to 16):

- **Exact versions**, one committed `pnpm-lock.yaml`, installed with `--frozen-lockfile`
- **A 7-day release cooldown** (`minimumReleaseAge`). An exception for an urgent security fix is
  recorded below
- **Dependency lifecycle scripts are refused** (`strictDepBuilds`), and the allowlist
  (`allowBuilds`) is empty. Adding to it is recorded below
- **Licences, by scope**: direct and runtime dependencies (runtime transitive included) under MIT,
  Apache-2.0, BSD-2-Clause, BSD-3-Clause, ISC, or 0BSD. Development-only transitive dependencies
  may also use BlueOak-1.0.0, Python-2.0, CC0-1.0, or CC-BY-4.0. Anything else only through a
  licence exception below. The check reads the installed tree, so each platform checks its own
  native packages

## Direct dependencies

Transitive counts are from `pnpm-lock.yaml` when the row was written, and include peer
dependencies that pnpm resolves into the package's own tree.

| Dependency           | Workspace package   | Version | Kind                               | Purpose                                                                                                        | Licence    | Transitive | Exceptions                                                              |
| -------------------- | ------------------- | ------- | ---------------------------------- | -------------------------------------------------------------------------------------------------------------- | ---------- | ---------- | ----------------------------------------------------------------------- |
| `typescript`         | root, `contract`    | 6.0.3   | Development                        | The TypeScript compiler (T-03). `contract` also uses its node factory in the type generator's `transform` hook | Apache-2.0 | 0          | —                                                                       |
| `@types/node`        | root                | 26.6.6  | Development                        | Node 26 type declarations                                                                                      | MIT        | 1          | —                                                                       |
| `eslint`             | root                | 10.14.0 | Development                        | Lint (T-10)                                                                                                    | MIT        | 78         | —                                                                       |
| `@eslint/js`         | root                | 10.0.1  | Development                        | ESLint's recommended JavaScript rules                                                                          | MIT        | 78         | —                                                                       |
| `typescript-eslint`  | root                | 8.72.1  | Development                        | Type-aware lint, `no-floating-promises` and `no-misused-promises` (T-10; SECURITY-15)                          | MIT        | 95         | —                                                                       |
| `prettier`           | root                | 3.9.10  | Development                        | Formatting (T-11)                                                                                              | MIT        | 0          | —                                                                       |
| `vitest`             | root                | 5.0.5   | Development                        | Tests (T-09)                                                                                                   | MIT        | 62         | Brings `lightningcss` (MPL-2.0) through `vite`: licence exception below |
| `ajv`                | `contract`          | 8.20.0  | Development in U1; runtime from U3 | JSON Schema 2020-12 validation, strict, compiled once (T-05)                                                   | MIT        | 4          | —                                                                       |
| `yaml`               | `contract`, `tools` | 2.9.1   | Development                        | Reads the OpenAPI documents, `pnpm-workspace.yaml`, and the workflows (T-06)                                   | ISC        | 0          | —                                                                       |
| `openapi-typescript` | `contract`          | 7.13.0  | Development                        | Generates TypeScript types from the contract, through its Node API (T-07)                                      | MIT        | 32         | Peer exception below                                                    |

## Peer exceptions

| Rule                                 | Reason                                                                                                                                                                                                                                                                                                                                               | Proved by                                                                     |
| ------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------- |
| `openapi-typescript>typescript`: `6` | openapi-typescript 7.13.0 declares `typescript ^5.x`; the workspace uses TypeScript 6.0 (T-03). Generation works, and its output typechecks under 6.0. **Fallback**, if a later release breaks the `transform` hook: a small in-house generator for the envelope, Delivery, and Problem, keeping openapi-typescript for the surface documents (T-07) | The golden-output test and the type-level fixture (TC-WC-032), on every build |

## Overrides

Each forces a version outside a dependent's declared range. The register check fails on an
override with no row here. Remove a row, and its override, once the dependents declare a fixed
range.

| Override                          | Reason                                                                                                                                                                                                                                                                                                                                                          | Proved by                                                                           | Remove when                                             |
| --------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------- | ------------------------------------------------------- |
| `minimatch@>=7 <11.0.1`: `11.0.3` | GHSA-g3hv-75wg-m249 (moderate: denial of service through glob-part amplification), fixed only in 11.0.1 and later. `eslint` 10.14.0 declares `^10.2.6` and `@typescript-eslint/typescript-estree` 8.72.1 `^10.2.2`, so without the override `pnpm audit` fails CI (NFR-WC-17). Development only. 11.0.3 is the newest release past the 7-day cooldown (D-CG-16) | `pnpm run lint` and the lint test (TC-WC-041) pass on 11.0.3; `pnpm audit` is clean | `eslint` and `typescript-eslint` declare `minimatch` 11 |

## Licence exceptions

Each row names packages (exact names, or a prefix ending in `*`) and one licence, never a version.
A named package is accepted only while its licence equals the row's: a version bump needs no edit,
and a licence change fails the check.

| Packages                         | Licence | Scope            | Reason                                                                                                                                                                                                                                                                                                     |
| -------------------------------- | ------- | ---------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `lightningcss`, `lightningcss-*` | MPL-2.0 | Development only | `vitest` → `vite` depends on it; it cannot be left out while Vitest is used. Used unmodified, in tests only, and never bundled or distributed. MPL-2.0's copyleft applies only to modified MPL-covered files, and soorma-core modifies none. Covers `lightningcss` and its 11 platform packages (Q-CG-2 A) |

## Cooldown exceptions

None.

## Lifecycle-script allowlist

None. `allowBuilds` is empty.
