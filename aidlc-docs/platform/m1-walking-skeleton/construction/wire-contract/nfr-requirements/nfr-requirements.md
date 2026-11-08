# NFR Requirements: U1 `wire-contract`

**Unit**: U1 `wire-contract` (soorma-core#4). A contract unit with no face
**Built against**: PF @ `prd-platform-foundations-v1.3`, ID @ `prd-identity-v1.0`
**Decisions from**: the NFR Requirements plan, Q1 to Q13, answered 2026-11-08 (verbatim in
`audit.md`)
**Companion**: [tech-stack-decisions.md](tech-stack-decisions.md)
**Functional Design**: [../functional-design/business-rules.md](../functional-design/business-rules.md)

**Plane-face profile**: none. U1 has no face, so it cites neither PF §9 nor §10, nor ID §10
(nfr-requirements.md Step 1.5 does not apply). Its constraints are I7, PF §7 and §14, and
M1-TECH-02 to 04.

---

## 1. Categories That Do Not Apply

| Category | Status | Reason |
|---|---|---|
| Scalability | N/A | U1 has no deployable |
| Availability | N/A | Same |
| Runtime latency and throughput | N/A for U1 | U1 ships no request path. The per-request budget for validating a draft and verifying a seal belongs to U3 (data face, PF §9). U1 only guarantees the cost is **bounded** (NFR-WC-07) |
| Usability (end users) | N/A | No user interface. Developer usability of the contract is NFR-WC-10 |

---

## 2. Requirements

Each requirement has a verification target. Code Generation implements them, and Build and
Test runs them.

### Compatibility (I7)

| ID | Requirement | Source | Verification |
|---|---|---|---|
| NFR-WC-01 | **A versioned fixture corpus**, `contract/fixtures/{version}/`, holds valid and invalid samples for each schema: envelope, draft, `inbound`, Delivery, Problem. Every later contract version must still accept every earlier version's valid envelope and Delivery fixtures, and still reject the invalid ones, unless `contract/CHANGELOG.md` records the breaking change. In M1, `0.1.0` is the baseline | I7; BR-VER-05, 06; Q12 A | Compatibility test over every fixture version present |
| NFR-WC-02 | **Every contract change is recorded and classified** in `contract/CHANGELOG.md` under BR-VER-05. Envelope v1 takes no breaking change in M1 | BR-VER-05, 06; D-WC-03 | Review at each unit's Code Generation |
| NFR-WC-03 | **An automated OpenAPI diff is added once a second contract version exists**: the first change after `contract-v0.1.0` is tagged | Q12 A | Recorded obligation, carried to the first post-tag change |

### Generated Types (M1-TECH-02; BR-LG)

| ID | Requirement | Source | Verification |
|---|---|---|---|
| NFR-WC-04 | **Generation is deterministic.** Regenerating from unchanged schemas gives byte-identical output, on any OS. A build check regenerates the types and fails on any difference from the committed ones | BR-LG-03, 05 | CI generated-types diff check |
| NFR-WC-05 | **The generated types keep the contract's openness (BR-LG-06), proven by a golden-output test**: (a) an open enumeration is its known values plus `(string & {})`; (b) an open object has an index signature; (c) a received identifier is a plain `string`; (d) a platform-stamped field on the draft is `?: never`. The test compiles a type-level fixture, with `@ts-expect-error` lines for the forbidden cases, and compares the generated file with a committed golden copy | Q6 A (the user's condition); BR-LG-06; BR-ID-11; BR-DR-10 | Golden-output test |
| NFR-WC-06 | **Open enumerations are written in exactly one shape** in the schemas: `anyOf: [{ enum: [...] }, { type: string }]`. The generator recognises that shape (tech-stack-decisions T-07). A bare `enum` on a received field is not allowed | BR-ENV-06; T-07 | Contract check (Q7) |

### Schema Safety (SECURITY-05, SECURITY-13)

| ID | Requirement | Source | Verification |
|---|---|---|---|
| NFR-WC-07 | **Validation cost is bounded.** Every request-side string has a `maxLength`, and every array a `maxItems`. The envelope is bounded at 16 KiB (BR-ENV-10). On the received side, identifiers carry no length (BR-ID-11), and the bound is the envelope and body size. Validators are compiled once, at start-up, never per request | SECURITY-05; BR-ID-11 | Contract check: every request-side string or array is bounded |
| NFR-WC-08 | **Every `pattern` is in the portable, linear-time subset** (the RE2-compatible subset): anchored, with no lookaround, no backreferences, and no named groups. That keeps patterns portable to any SDK language's validator, and makes catastrophic backtracking (ReDoS) impossible. A rule a pattern cannot express (a `traceparent` version of `ff`; an all-zero trace or parent id; calendar validity of a time) is **checked in code by the receiving unit**, and listed in the conventions | SECURITY-05, 11; BR-TC-01; Q5 | Contract check over every `pattern` |
| NFR-WC-09 | **No `format` keyword anywhere in the contract.** Structured strings (times, versions, identifiers) use in-schema `pattern`s. JSON Schema 2020-12 treats `format` as an annotation by default, so another language's validator may not assert it, while every validator asserts `pattern`. No `ajv-formats` dependency | Q5 (decision left to AI-DLC; T-05) | Contract check: no `format` keyword |
| NFR-WC-10 | **Every schema compiles under Ajv strict mode** in 2020-12 mode, with no warnings. No Ajv-specific keyword is used, so any 2020-12 validator can use the schemas (soorma-sdk) | Q5 A; M1-TECH-02 | Schema compilation test |
| NFR-WC-11 | **All references resolve locally.** Every `$ref` is relative, within `contract/`. No remote `$ref`, and no validator is configured to load schemas over the network. The OpenAPI 3.1 schema used to validate the surface documents is **a copy committed to the repository at a pinned version**, with its source and SHA-256 recorded | SECURITY-13; Q7 A | Contract check: no absolute or remote `$ref`; the meta-schema digest matches the record |

### Supply Chain (M1-TECH-04; SECURITY-10)

| ID | Requirement | Source | Verification |
|---|---|---|---|
| NFR-WC-12 | **One committed lockfile** (`pnpm-lock.yaml`); CI installs with the frozen lockfile. Exact versions only (`save-exact`) | M1-TECH-04; SECURITY-10 | CI install step |
| NFR-WC-13 | **A dependency register**, `DEPENDENCIES.md`: one row per direct dependency, with purpose, runtime or development, licence, transitive count, and any exception (cooldown, peer range, licence) | Q13 A | CI checks that every direct dependency has a row |
| NFR-WC-14 | **Licence allowlist, by scope.** Direct and runtime dependencies (including runtime transitive dependencies): MIT, Apache-2.0, BSD-2-Clause, BSD-3-Clause, ISC, 0BSD. Development-only transitive dependencies may also use BlueOak-1.0.0, Python-2.0, CC0-1.0, and CC-BY-4.0. Anything else needs a recorded exception in the register | Q13 A, as scoped by the user | CI licence check over the resolved tree |
| NFR-WC-15 | **Release cooldown of 7 days** (`minimumReleaseAge`). An exception for an urgent security fix is recorded in the register | Q10 A | Configuration check in CI |
| NFR-WC-16 | **Dependency lifecycle scripts are blocked**, with an explicit allowlist that is **empty in U1**. Adding to it is recorded in the register | M1-TECH-04 | Configuration check |
| NFR-WC-17 | **Vulnerability scanning**: `pnpm audit` fails the build at moderate severity and above; GitHub's dependency-review action blocks a pull request that adds a vulnerable dependency; Dependabot alerts are on | Q9 A | CI |
| NFR-WC-18 | **An SBOM, CycloneDX JSON, on every build**, produced by Syft through `anchore/sbom-action` pinned by commit SHA, and kept as a build artifact | Q9 A; SECURITY-10 | CI artifact present |
| NFR-WC-19 | **A pinned toolchain.** Node pinned exactly in `.node-version` (`26.13.0`); `engines.node` is `^26.13.0`, and a configuration check verifies the two agree (amended at the Code Generation plan review, 2026-11-08). pnpm pinned by the `packageManager` field and installed exactly in CI by `pnpm/action-setup`. **A mismatched pnpm version is caught by the configuration check** (`check:deps`, run locally and in CI). **pnpm's own refusal is turned off** (`pmOnFail: ignore`), because with it on, pnpm 12 writes a two-document lockfile that GitHub's dependency graph cannot read, which would blind NFR-WC-17 (Q-CG-1 A; amended at the Code Generation plan review, 2026-11-08). **No Corepack**: Node 25 and later no longer bundle it. CI installs pnpm with `pnpm/action-setup` pinned by SHA | Q1 A; Q2 A (the user's Corepack correction) | CI uses the pinned versions; the configuration check fails on a pnpm version other than `packageManager`'s, locally and in CI |
| NFR-WC-20 | **CI integrity**: every GitHub Action pinned by commit SHA; workflow `permissions` default to `contents: read`, widened per job only where needed and recorded | SECURITY-10, 13; Q11 A | Workflow check (no unpinned `uses:`) |

### Licence and Maintainability

| ID | Requirement | Source | Verification |
|---|---|---|---|
| NFR-WC-21 | `contract/` is Apache 2.0, with its own `LICENSE`. Every schema and document declares `SPDX-License-Identifier: Apache-2.0`. Generated types are Apache 2.0 too. `packages/` and `services/` are FSL-1.1-ALv2 | PF §22; BR-LG-01, 02 | TC-WC-011; a contract check for the SPDX identifier |
| NFR-WC-22 | **The conventions are readable without the code**: `contract/conventions/` documents every BR-PR statement, the error codes, the security schemes, the identifier syntax, and the checks done in code (NFR-WC-08). The valid fixtures double as examples for raw callers | PF FR-023 (raw callers); I7 | Review at Code Generation |
| NFR-WC-23 | **Code quality**: ESLint with type-aware rules, `no-floating-promises` and `no-misused-promises` included (SECURITY-15), and Prettier, both enforced in CI. TypeScript `strict` | Q8 A; SECURITY-15 | CI lint and typecheck |

---

## 3. Security Compliance at NFR Requirements

| Rule | Status | Note |
|---|---|---|
| SECURITY-01, 02, 06, 07 | N/A | No store, network, or IAM in U1 |
| SECURITY-03 | N/A for U1 | No running component. The correlation id is in the contract (D-WC-16) |
| SECURITY-04 | N/A | No HTML served |
| SECURITY-05 | Compliant | NFR-WC-07 to 10 |
| SECURITY-08 | N/A for U1 | No endpoint |
| SECURITY-09 | Compliant | No sample application or default page; pinned, current toolchain (Node 26 LTS) |
| SECURITY-10 | Compliant | NFR-WC-12 to 20 |
| SECURITY-11 | Compliant | Linear-time patterns (NFR-WC-08); misuse cases in Functional Design |
| SECURITY-12 | N/A for U1 | No authentication in U1 |
| SECURITY-13 | Compliant | Local references and a pinned meta-schema (NFR-WC-11); pinned actions and least-privilege CI (NFR-WC-20) |
| SECURITY-14 | N/A for U1 | No running component |
| SECURITY-15 | Compliant | Type-aware promise rules (NFR-WC-23) |

**Security findings**: none blocking.

## 4. Invariant Compliance at NFR Requirements

| Code | Status | Note |
|---|---|---|
| I1 to I6, I9, I10 | No change | As in [invariant-coverage-matrix.md](../functional-design/invariant-coverage-matrix.md). This stage adds no runtime path |
| I7 | Covered, strengthened | NFR-WC-01 to 06, 10 |
| I8 | Covered | NFR-WC-21; every dependency is open source under the allowlist, and nothing commercial is added |
| I11 | N/A | Construction is where technology is selected; every choice here is AI-DLC's (I11) |

**Invariant findings**: none blocking.
