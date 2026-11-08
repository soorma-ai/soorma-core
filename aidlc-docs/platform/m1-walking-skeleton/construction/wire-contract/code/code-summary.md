# Code Summary: U1 `wire-contract`

**Unit**: U1 `wire-contract` (soorma-core#4) · **Stage**: Code Generation, 2026-11-08
**Plan**: `construction/working/wire-contract-code-generation-plan.md` (revision 2, approved with
Q-CG-1 A; Q-CG-2 A answered during generation)
**Commits on `dev`**: Group 1 `2cdea76` (toolchain), Group 2 `b0c3411` (contract), Group 3
`d87bac6` (generation, checks, tests), Group 4 `882b0fe` (dependencies and CI), Group 5 (this
summary, documentation, coverage)

Application code is in the repository root, never under `aidlc-docs/`.

---

## Files

### Created

| Path | What it is |
|---|---|
| `.node-version`, `package.json`, `pnpm-workspace.yaml`, `pnpm-lock.yaml` | The pinned workspace (Node 26.13.0, pnpm 12.18.0); packages `contract` and `tools` |
| `tsconfig.base.json`, `eslint.config.js`, `.prettierrc.json`, `.prettierignore`, `.gitignore` | TypeScript 6.0 strict ESM, type-aware ESLint, Prettier |
| `REUSE.toml` | Licences of files that cannot carry a header (fixtures, the meta-schema) |
| `DEPENDENCIES.md` | The dependency register, with peer, override, and licence exceptions |
| `.github/workflows/ci.yml`, `.github/dependabot.yml` | CI, and Dependabot held to the 7-day cooldown |
| `contract/LICENSE`, `contract/README.md`, `contract/CHANGELOG.md`, `contract/package.json`, `contract/tsconfig.json` | The Apache 2.0 contract package |
| `contract/envelope.schema.json` | Envelope v1, the draft, `inbound`, the two `traceContext` definitions, `ContractVersion` |
| `contract/delivery.schema.json` | `Delivery` |
| `contract/conventions/components.openapi.yaml` | Shared components: `Problem`, `ProblemCode`, identifier definitions, the contract version parameter and headers, three security schemes |
| `contract/conventions/*.md` (8) | README, envelope, errors, credentials, identifiers, versioning, pre-release, adding an operation |
| `contract/generated/components.ts` | Generated types |
| `contract/fixtures/0.1.0/**` (62) | Valid and invalid samples for the envelope, draft, `inbound`, Delivery, and Problem |
| `contract/meta/openapi-3.1-schema-2026-08-03.json`, `contract/meta/SOURCE.md` | The pinned OpenAPI 3.1 schema and its record |
| `contract/scripts/generate-types.ts`, `contract/scripts/validator.ts` | The type generator (with the `transform` hook) and the strict validator |
| `contract/scripts/checks/*.ts` (9) | The contract checks, the compatibility test, the SPDX and meta-schema checks |
| `contract/test/**` (12) | 190 tests in 9 files, the golden test schema and copy, the type-level fixture |
| `tools/checks/*.ts` (7), `tools/test/**` (5), `tools/package.json`, `tools/tsconfig.json` | Repository checks and their 32 tests, with the lint fixture |

### Modified

| Path | Change |
|---|---|
| `.github/workflows/cla.yml` | Action pinned by commit SHA; write permissions moved from the workflow to its one job, with the reason in a comment. Behaviour unchanged (D-CG-07) |
| `README.md` | "Nothing is built yet" replaced; *What is here* and *Working on it* added. The licence section is unchanged |

---

## Decisions as Built

| ID | As built |
|---|---|
| D-CG-01 | `traceparent` ≤ 512; `clientContractVersion` ≤ 32 with the SemVer core pattern; `inbound.seal` 1 to 1024 |
| D-CG-02 | Two `if`/`then` rules: `delegated` requires `delegatingPrincipal`; `autonomous` forbids it with a `false` schema; any other mode is unconstrained |
| D-CG-03 | `$comment` in JSON schemas; comments in YAML, TypeScript, Markdown, and `tsconfig.json`; `license` in `package.json`; `REUSE.toml` for `contract/fixtures/**` and `contract/meta/**` |
| D-CG-04 | Golden test on `contract/test/golden/openness.openapi.yaml`; drift check on `contract/generated/` |
| D-CG-05 | The pattern check parses each pattern; a group under an **unbounded** quantifier must start, in every alternative, with a literal its body cannot match. **For U3's NFR Requirements**: Ajv becomes a runtime dependency there; the contract's patterns are linear in V8 under this rule, and U3 should confirm the runtime engine choice |
| D-CG-06 | The `tracestate` pattern checks the character set and list form; the 32-member limit and key syntax are listed as checked in code |
| D-CG-07 | See `cla.yml` above. CLA assistant v2.6.1 → `ca4a40a7d1004f18d9960b404b97e5f30a505a08` |
| D-CG-08 | `tools/` (FSL) and `contract/scripts/checks/` (Apache 2.0); every check a pure function |
| D-CG-09 | Node 26 runs the TypeScript scripts directly; one parameter property had to be rewritten as a field (not erasable syntax) |
| D-CG-10 | `pnpm run build` = generate, then typecheck both packages |
| D-CG-11 | No `packages/`; the root `LICENSE` is FSL-1.1-ALv2 |
| D-CG-12 | Q-CG-1 A: `dependabot.yml` for `npm` and `github-actions`, `cooldown` 7 days; `tools/checks/github-settings.ts` through `gh api` (`pnpm run check:github`) |
| D-CG-13 | `.node-version` `26.13.0`; `engines.node` `^26.13.0`; the configuration check compares them |
| D-CG-14 | Five commits on `dev`, then a PR to `main` left open for Build and Test |
| D-CG-15 | Schema layout from the Step 5 probe: `$id` `https://soorma.ai/contract/{file}`; each file's root is `$ref: '#/$defs/{Name}'`; every reference points into `$defs`; open objects say `additionalProperties: true`. Without it, openapi-typescript rendered `$defs` as a type member and gave open objects no index signature |
| D-CG-16 | **Flagged for review.** `pnpm audit` found GHSA-g3hv-75wg-m249 (moderate) in `minimatch` 10.2.6 through `eslint` and `typescript-eslint`; the fix is only in 11.0.1+. A pnpm override pins `minimatch@>=7 <11.0.1` to 11.0.3; recorded under Overrides in `DEPENDENCIES.md`; the register check requires a row for every override. Lint and the lint test pass, and the audit is clean |
| Q-CG-1 A | `pmOnFail: ignore`; `pnpm-lock.yaml` is one YAML document; the configuration check compares the running pnpm with `packageManager` |
| Q-CG-2 A | One licence exception: `lightningcss`, `lightningcss-*`, MPL-2.0, by name and licence |

### Found during generation, beyond the plan

- **Ajv 8 resolves the OpenAPI meta-schema's `$dynamicRef: "#meta"` incorrectly**, validating
  schema objects as parameter objects. After the digest check, the meta-schema validator replaces
  each such reference, in memory only, with the equivalent `$ref: "#/$defs/schema"`. Recorded in
  `contract/meta/SOURCE.md`
- **`pnpm licenses list` without `-r` lists only the root package's tree.** The licence check uses
  `-r`. It sees installed packages only, so each platform checks its own native packages (CI checks
  the Linux ones)
- **`typescript` is also a development dependency of `contract`**: the generator's hook builds
  `(string & {})` with TypeScript's node factory
- **ESLint, tests only**: `no-explicit-any`, `no-unsafe-member-access`, and
  `no-unsafe-assignment` are off for `**/test/**`, because tests mutate untyped JSON fixtures. The
  promise rules stay on everywhere
- **Strict mode and conditionals**: Ajv's `strictRequired` needs a property declared where it is
  required, so the `delegated` rule declares `delegatingPrincipal: true` beside `required`
- **The forwarded envelope's arrays are bounded**: the bounds check follows the one allowed
  request-to-received reference (`inbound.envelope`) and requires `maxItems` on every array it can
  reach (TC-WC-035 step 4); strings there stay unbounded (BR-ID-11)

---

## Dependencies (exact)

| Package | Version | Where |
|---|---|---|
| typescript | 6.0.3 | root, `contract` |
| @types/node | 26.6.6 | root |
| eslint | 10.14.0 | root |
| @eslint/js | 10.0.1 | root |
| typescript-eslint | 8.72.1 | root |
| prettier | 3.9.10 | root |
| vitest | 5.0.5 | root (5.1.0 was inside the cooldown) |
| ajv | 8.20.0 | `contract` |
| openapi-typescript | 7.13.0 | `contract` (peer exception for TypeScript 6) |
| yaml | 2.9.1 | `contract`, `tools` |

CI actions, each the latest release past the 7-day cooldown, pinned by commit SHA: checkout
v7.0.1, setup-node v7.1.0, pnpm/action-setup v6.1.0 (v6.1.1 was 5 days old), sbom-action v0.24.3,
upload-artifact v7.0.2, dependency-review-action v5.0.0.

---

## Test Cases

| TC | Automated in | Left for Build and Test |
|---|---|---|
| TC-WC-001, 006, 008, 016 to 019, 021 | `contract/test/envelope.test.ts` | — |
| TC-WC-007, 010, 012 to 015, 020, 022 | `contract/test/draft.test.ts` | — |
| TC-WC-002, 023 | `contract/test/delivery.test.ts` | — |
| TC-WC-024 | `contract/test/problem.test.ts` | — |
| TC-WC-004, 005, 018 to 020, 025 to 029 | `contract/test/conventions.test.ts` | — |
| TC-WC-009, 026, 027 | `contract/test/components.test.ts` | — |
| TC-WC-003, 032, 033 | `contract/test/generation.test.ts` | — |
| TC-WC-011, 034 to 037 | `contract/test/checks.test.ts` | — |
| TC-WC-030, 031 | `contract/test/compatibility.test.ts` | — |
| TC-WC-038 | `tools/test/dependencies.test.ts` | — |
| TC-WC-039 | `tools/test/configuration.test.ts` | Step 2: a frozen install refuses a changed manifest (pnpm's own behaviour) |
| TC-WC-040 | `tools/test/workflows.test.ts` (steps 1, 2, 3 by content, 4, 6) | Steps 3 to 5 on a real CI run: every step ran, dependency review ran, the SBOM artifact; `pnpm run check:github` |
| TC-WC-041 | `tools/test/lint.test.ts` | — |

## Local Smoke Run (Step 19)

All exit 0, on Node 26.13.0 and pnpm 12.18.0: `pnpm install --frozen-lockfile`; `pnpm run build`;
`pnpm run lint`; `pnpm run format:check`; `pnpm run check:generated`; `pnpm run check:contract`;
`pnpm run check:deps`; `pnpm run check:workflows`; `pnpm test` (**222 passed**: 190 contract, 32
tools); `pnpm audit --audit-level moderate` (no known vulnerabilities). `pnpm run check:github`
was not run: it is for Build and Test, after the lockfile reaches `main`.

---

## Security Compliance

| Rule | Status | Evidence |
|---|---|---|
| SECURITY-01, 02, 06, 07 | N/A | No store, network intermediary, IAM policy, or network configuration in U1 |
| SECURITY-03, 14 | N/A | No running component. The correlation id is in the contract (`Soorma-Request-Id`) |
| SECURITY-04 | N/A | No HTML served |
| SECURITY-05 | Compliant | Every request-side string and array bounded, checked (`checkBounds`); patterns anchored and linear-time (`checkPatterns`); closed draft and wrapper |
| SECURITY-08 | N/A | No endpoint in U1 |
| SECURITY-09 | Compliant | No sample application or default page; Node 26 LTS; errors convention forbids internal detail |
| SECURITY-10 | Compliant | Committed lockfile, frozen install, exact versions, cooldown, refused lifecycle scripts, audit in CI (clean, after D-CG-16), dependency review, Dependabot, CycloneDX SBOM, SHA-pinned actions |
| SECURITY-11 | Compliant | Linear-time patterns (D-CG-05); misuse cases in Functional Design; the closed draft |
| SECURITY-12 | N/A | No authentication in U1. No credential in source or configuration |
| SECURITY-13 | Compliant | Local references only; the meta-schema pinned by SHA-256 and cross-checked; read-only default CI permissions; `persist-credentials: false` |
| SECURITY-15 | Compliant | `no-floating-promises` and `no-misused-promises` as errors, proven by the lint test; scripts set `process.exitCode` on failure |

## Invariant Compliance

| Code | Status |
|---|---|
| I1 to I6, I10 | Compliant for U1's part; runtime verification by the units named in `invariant-coverage-matrix.md` |
| I7 | Compliant: versioned contract, change classification, fixture corpus, compatibility test |
| I8 | Compliant: packaging table re-checked; nothing commercial in any form |
| I9 | Compliant: no tenant schema, name, or constant; fixtures labelled |
| I11 | N/A: Construction is where technology is selected |

No blocking security or invariant finding.
