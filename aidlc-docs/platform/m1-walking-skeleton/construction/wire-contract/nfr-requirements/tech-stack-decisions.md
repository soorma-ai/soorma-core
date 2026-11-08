# Tech Stack Decisions: U1 `wire-contract`

**Unit**: U1 `wire-contract` (soorma-core#4)
**Scope**: the **workspace toolchain**. U1 creates the first `package.json`, the lockfile, and
CI, and **every later unit inherits these choices**. A later unit adds its own runtime
libraries (NestJS adapters, datastore drivers, the JCS and sealing libraries) at its own NFR
Requirements, under the same register (NFR-WC-13).
**Versions**: checked on the npm registry and nodejs.org, 2026-11-08. Exact versions are
pinned at Code Generation, subject to the 7-day cooldown (NFR-WC-15).

---

## Decisions

| ID | Area | Choice | Version line | Kind | Rationale | Serves |
|---|---|---|---|---|---|---|
| T-01 | Runtime | **Node.js 26 LTS** (*Lithium*) | 26.x, pinned exactly (26.13.0 current) | Runtime | Active LTS since October 2026, supported into 2029: the longest runway for M1 | Q1 A; M1-TECH-01, 04 |
| T-02 | Package manager | **pnpm 12 workspaces**, pinned with `packageManager`, enforced by pnpm itself. **No Corepack** (Node 25+ does not bundle it). CI installs pnpm with `pnpm/action-setup` pinned by SHA. No Nx or Turborepo | 12.x (12.18.0 current) | Tool | Strict isolation (no phantom dependencies); lifecycle scripts blocked by default; `minimumReleaseAge`; one lockfile | Q2 A, with the user's correction; M1-TECH-04 |
| T-03 | Language | **TypeScript 6.0.x**, `strict` | 6.0 (6.0.3 current) | Development | The last JavaScript-based compiler: proven with NestJS decorators, and supported by typescript-eslint (`typescript` `<6.1.0`). TypeScript 7 has no JavaScript API yet. Moving to 7 later is a tooling change, not a contract change | Q3 A; M1-TECH-01 |
| T-04 | Module system | **ESM** throughout (`"type": "module"`; `module` and `moduleResolution` `nodenext`) | — | — | Settled by fact: `@nestjs/core` 12 is published as ESM | M1-TECH-01 |
| T-05 | Schema validator | **Ajv 8**, 2020-12 mode (`ajv/dist/2020`), `strict: true`, compiled once at start-up. **Formats: none.** The contract uses in-schema `pattern`s, never `format`, so there is **no `ajv-formats`** | 8.x (8.20.0 current; 4 dependencies) | Development in U1; **runtime from U3** | Compiled validators suit the per-request path. `format` is annotation-only by default in 2020-12, so patterns are what every validator asserts, including soorma-sdk's (NFR-WC-09) | Q5 A, and the format decision Q5 left to AI-DLC; SECURITY-05 |
| T-06 | YAML | **`yaml`** | 2.x (2.9.1 current; no dependencies) | Development | Loads the OpenAPI documents for the contract checks and type generation | Q7 A |
| T-07 | Type generation | **openapi-typescript**, run through its Node API by one generator script, `contract/scripts/generate-types` | 7.x (7.13.0 current) | Development | One generator, one output style. A shared document, `contract/conventions/components.openapi.yaml`, references the envelope, Delivery, and Problem schemas, so shared and surface types come from one run. **See the two recorded conditions below** | Q6 A; M1-TECH-02 |
| T-08 | Contract checks | **In-house tests** (Vitest): each OpenAPI document validated by Ajv against a **committed copy of the official OpenAPI 3.1 schema, at a pinned version, with its source and SHA-256 recorded**; then the contract rules asserted in code | — | — | No dependency beyond T-05 and T-06; no remote fetch | Q7 A; NFR-WC-11 |
| T-09 | Tests | **Vitest 5** | 5.x (5.1.0 current; needs `vite`) | Development | ESM-native. NestJS tests from U2 onward run decorators through an SWC transform (`unplugin-swc`, `@swc/core`), which U2 adds and registers | Q4 A |
| T-10 | Lint | **ESLint 10** with **typescript-eslint 8**, type-aware: `no-floating-promises` and `no-misused-promises` on | ESLint 10.x (10.14.0); typescript-eslint 8.x (8.72.1) | Development | SECURITY-15 (no unhandled rejections), caught at compile time | Q8 A |
| T-11 | Format | **Prettier 3** | 3.x (3.9.10 current) | Development | One format, enforced in CI | Q8 A |
| T-12 | Scanning | `pnpm audit` (fails at moderate and above); GitHub **dependency-review** action on pull requests; **Dependabot** alerts | — | CI | Blocks known-vulnerable dependencies at install and at review | Q9 A; SECURITY-10 |
| T-13 | SBOM | **Syft**, through `anchore/sbom-action` pinned by SHA; CycloneDX JSON; kept as a build artifact on every build | — | CI | No SBOM tool in the dependency tree | Q9 A; SECURITY-10 |
| T-14 | CI | **GitHub Actions** on soorma-core. One workflow: frozen-lockfile install; build; typecheck; lint; format check; tests (contract checks, golden output, compatibility); generated-types diff; licence check; register check; audit; SBOM. Actions pinned by SHA; `permissions: contents: read` by default | — | CI | Dependency discipline "from the first commit" (M1-TECH-04) | Q11 A; NFR-WC-20 |
| T-15 | Dependency policy | `DEPENDENCIES.md` register; exact versions; 7-day `minimumReleaseAge`; lifecycle-script allowlist, empty in U1; licence allowlist by scope (NFR-WC-14), checked in CI | — | Policy | Each dependency justified and reviewable | Q10 A, Q13 A |
| T-16 | Compatibility | Versioned fixture corpus and `contract/CHANGELOG.md`. An automated OpenAPI diff is added after `contract-v0.1.0` | — | Test | One version exists in M1 | Q12 A; NFR-WC-01 to 03 |

---

## Recorded Conditions on T-07 (openapi-typescript)

**Probe run 2026-11-08**, in an isolated scratchpad, with openapi-typescript 7.13.0,
TypeScript 6.0.3, and Node 24. The probe schema had an open enumeration, open objects,
plain identifier strings, and a closed draft with stamped fields forbidden by name.

| BR-LG-06 property | Default output | With the generator script's `transform` hook |
|---|---|---|
| Open enumeration | `("autonomous" \| "delegated") \| string`: **collapses to `string`. Fails** | `"autonomous" \| "delegated" \| (string & {})`. **Passes** |
| Open object | Index signature `[key: string]: unknown`. Passes | Same |
| Received identifier | `string`. Passes | Same |
| Stamped field on the draft | `scope?: never`. Passes | Same |

A type-level fixture typechecked under `strict`: an unknown origin mode is accepted, a
number is rejected, and a draft carrying `scope` is rejected.

**Condition 1, the post-processing step (as Q6 asked to be recorded).** The generator
script passes a `transform` hook to openapi-typescript's Node API. It matches **exactly** the
open-enum shape `anyOf: [{ enum: [...] }, { type: string }]` (NFR-WC-06) and emits the known
values plus `(string & {})`. This is a hook in the generator's own API, not text editing of
its output. The golden-output test (NFR-WC-05) proves it on every build. **Fallback**: if a
later openapi-typescript release breaks the hook, the shared schemas switch to option C (a
small in-house generator for the envelope, Delivery, and Problem), and openapi-typescript
stays for the surface documents.

**Condition 2, a peer-range exception.** openapi-typescript 7.13.0 declares
`typescript ^5.x`. T-03 is TypeScript 6.0. npm refused to resolve the install without an
override. **With the override, generation worked, and its output typechecked with
TypeScript 6.0.3.** The workspace records it as a pnpm `peerDependencyRules` exception,
scoped to `openapi-typescript>typescript`, listed in the register, and re-proved by the
golden-output test. Note also that 7.13.0 dates from February 2026, with no release since.
That maintenance risk is the reason the fallback above is recorded now.

---

## Deferred to Later Units (not decided here)

| Selection | Decided at |
|---|---|
| NestJS packages, HTTP adapter, SWC transform for tests | U2 NFR Requirements (first service) |
| RFC 8785 (JCS) library; seal algorithm and keys | U3 NFR Requirements and NFR Design |
| Datastores, internal broker, credential format, K hashing | Per the execution plan, U2 to U7 |
| Payload size bound value | U7 NFR Requirements (BR-DL-04) |

## Local Environment Note

The workstation used in this session has Node 24.0.1 and no pnpm. Code Generation for U1
needs **Node 26** and **pnpm 12** locally. The build instructions will say how to install
them (Build and Test).

## Stages for U1 After This One

| Stage | Decision | Reason |
|---|---|---|
| NFR Design | **Skip** | No runtime patterns: no service, store, cache, or logging path in U1 |
| Infrastructure Design | **Skip** | Nothing deployed. CI is designed here (T-14) and generated at Code Generation |
| QA construction enrichment | **Run** next | After the last design stage (qa-test-cases.md §2.6) |
| Construction Design PR gate | **Run** after enrichment | pr-checkpoint.md Section 5 |
| Code Generation | **Run** after the gate | Always |
