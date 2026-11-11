# Code Summary: U3 `authority-evaluation`

**Unit**: U3 `authority-evaluation` (soorma-core#6). Data face, environment level. Modules only
**Built against**: PF @ `prd-platform-foundations-v1.3`, ID @ `prd-identity-v1.0`
**Plan**: `construction/working/authority-evaluation-code-generation-plan.md` (git-ignored),
Revision 2, approved 2026-11-10 with two amendments. Steps 0 to 23
**Generated**: 2026-11-10, on `dev`, in seven commit groups after a bookkeeping commit

## Commits

| Commit | Group | Contents |
|---|---|---|
| `4821788` | Step 0 | The plan-approval bookkeeping: `aidlc-state.md`, `audit.md` (amendment 2) |
| `8d90404` | 1 | **The guard on U2, alone, before any change**: the byte vectors, the seed fixture, the generator, the test, and the `associatedData` export (amendment 1) |
| `626ed4b` | 2 | `packages/jcs`; the five packages scaffolded; **the swap** in U2's `canonical.ts` |
| `ef7c392` | 3 | P1's Problem table and emission, and `./testing`; S1 moved to it; the §13 contract changes |
| `90dc1fd` | 4 | `seams/policy-decision`; P11; `sealKeys` in P9 |
| `6508782` | 5 | P2, `packages/envelope`; the dependency register |
| `b6a59c5` | 6 | P3, `packages/authority`, and the entry point; the benchmark |
| `e803e90` | 7 | Documentation, this summary, the matrices, `aidlc-state.md` |
| (Request Changes) | RC | The image, an unresolved upstream agent, and `errors[]` at most 10 (below) |

## Files

**Created**
- `packages/jcs/`: `src/index.ts` (`canonicalize`, `CanonicalizationError`), `test/canonicalize.test.ts`, `README.md`
- `seams/policy-decision/`: `src/index.ts` (types only)
- `packages/policy-decision/`: `src/index.ts` (`createPolicyDecision`, `GrantSource`, `inMemoryGrantSource`), `test/policy-decision.test.ts`, `README.md`
- `packages/envelope/`:
  - `src/`: `refusal.ts`, `version.ts`, `trace-context.ts`, `draft.ts`, `copy.ts`, `seal.ts`, `inbound.ts`, `chain.ts`, `stamp.ts`, `index.ts`
  - `test/`: `support.ts`, `version-and-draft.test.ts`, `patterns.test.ts`, `seal.test.ts`, `inbound-and-stamp.test.ts`
  - `README.md`: the seal, the key ring, the effective id rule, and the two-phase rotation
- `packages/authority/`:
  - `src/`: `origin.ts`, `evaluate.ts`, `human-only.ts`, `agent-facts.ts`, `admission.ts`, `index.ts`
  - `test/`: `support.ts`, `evaluate.test.ts`, `admission.test.ts`, `agent-facts.test.ts`, `structure.test.ts`, `depth.test.ts`
  - `bench/admit.bench.ts`
  - `README.md`: how S4 builds and calls the entry point, the ports, and NFR-AE-16
- `packages/perimeter/`: `src/problems.ts`, `testing/index.ts` (`assertProblem`), `test/problems.test.ts`, `README.md`
- `packages/org-identity/test/`: `canonical-vectors.test.ts`; `vectors/canonical-vectors.json`, `seed-fixture.json`, `generate.ts`

**Modified**
- `packages/org-identity/src/crypto/canonical.ts`: `canonicalJson` is a wrapper over `@soorma/jcs`
- `packages/org-identity/src/crypto/seed-cipher.ts`: `associatedData` exported, for the test only
- `packages/config/`: `schema/tenancy.schema.json` (optional `sealKeys`, `$defs/SealKeys`); `src/tenancy.ts` (`loadSealKeys`; seal-key checks as for the seed keys); `src/index.ts`; `test/tenancy.test.ts`
- `packages/perimeter/`: `src/index.ts`, `package.json` (`./testing`; development dependencies), `tsconfig.json`
- `services/org-gateway/`:
  - `src/problems.ts` **removed**
  - `src/http.ts`: `sendProblem` is now a Fastify adapter over `problemResponse`
  - `src/edge/edge-handlers.ts`, `src/internal/internal.module.ts`, `src/contract-validator.ts`: imports from P1
  - `test/edge.test.ts`: `assertProblem`
- `contract/`:
  - `conventions/envelope.md`, `errors.md`, `versioning.md`, `pre-release.md`: the §13 changes
  - `envelope.schema.json`: A6 in the `EnvelopeTraceContext` description
  - `generated/components.ts`: regenerated, with one doc comment changed
  - `CHANGELOG.md`, `test/conventions.test.ts`
- Root: `tsconfig.build.json` (five references), `package.json` (`bench:admit`), `DEPENDENCIES.md` (the Ajv and `yaml` rows), `pnpm-lock.yaml` (workspace links only), `README.md`

## The U2 swap, in NP-03's order

1. **Guard, committed alone** (`8d90404`). The guard was written once from the current code by
   `test/vectors/generate.ts`, which refuses to overwrite its own output. It covers:
   - `referenceJson`'s UTF-8 bytes for nine references. Together they cover `'`, `/`, `|`, `@`,
     `+`, `:`, `.`, the other specials the human pattern admits, a 1-character identifier, a
     256-character identifier, and a 64-character organization
   - each reference's **pseudonym** under a fixed log key
   - each reference's **P8 attempt slot** under a fixed counter secret (D-CG-AE-01)
   - the **seed associated data** for four `(reference, recordId)` pairs
   - a **seed encrypted by the current `encryptSeed`**, its decryption, and a decryption that
     must fail when the associated data is tampered with

   All 16 tests passed on the current code.
2. **The swap** (`626ed4b`). `canonicalJson` is now `checkNumbers(value)` (U2's safe-integer
   rule, iterative), then `canonicalize(value).text`. The `Canonical` type is unchanged.
3. **Result**: `git diff 8d90404` of the guard's files is empty. **All 16 guard tests pass
   unchanged**, and so does every U2 test. Stop condition 1 did not fire.

## Decisions as Built

| ID | As built |
|---|---|
| D-CG-AE-01 | The slot is asserted with P8's real `slotOf`, which the P10 test reaches **by relative path** (`../../abuse-bound/src/abuse-bound.ts`): P8 depends on P10, so P10 cannot import it as a package. The generator computes the slot by `slotOf`'s documented formula, because P8's import of P10's index pulls in NestJS decorators that Node's type stripping cannot run. The test, asserting with the real function, proved on the current code that the two agree |
| D-CG-AE-02 | The seam package is **`@soorma/policy-decision-seam`**, after U2's `@soorma/identity-resolution-seam`. `REUSE.toml` needed no change: the seam's files carry Apache-2.0 SPDX headers, as `seams/identity-resolution` does |
| D-CG-AE-03 | As planned. `assertProblem` is **stricter than S1's former helper**: the title must be the table's title, and `Retry-After` must be absent outside 429 and 503 |
| D-CG-AE-04 | As planned. `Retry-After` is `max(1, ceil(n))`, identical to S1's for the integer values S1 passes |
| D-CG-AE-05 | As planned. **`admit` returns P1's `Refusal` shape without the internal reason**, which goes only to the security log, so S4 passes it straight to `problemResponse` |
| D-CG-AE-06 | As planned, with Q-CG-AE-1 A: `sealKeys` ids are `$defs/KeyId`. A duplicate id and an unknown `current` are refused at load, **as the seed keys are**, in `readTenancy`. `loadSealKeys` reads the secrets |
| D-CG-AE-07 | As planned |
| D-CG-AE-08 | **Vitest 5.0.5's benchmark API is on the test context** (`test(name, async ({ bench }) => bench(name, fn).run())`). Vitest 5 does not export the earlier top-level `bench`. `pnpm bench:admit` runs `vitest bench --run --reporter=verbose packages/authority/bench`, and the case prints and annotates p50, p99, and the sample count. **There is no assertion on time** |
| D-CG-AE-09 | As planned: the gate passed before each of the seven groups |

**Other details settled during generation** (each technology; none a specification gap):
- **No `clock` dependency on `createEnvelopeAdmission`.** The plan listed one among its
  dependencies, but `admit` reads no time: the clock belongs to `createCachingAgentFacts`, which
  S4 builds once per instance.
- **`tracestate` member count**: empty list members are not counted (W3C).
- **`packages/envelope` has `yaml` as a development dependency**, for the worst-case pattern
  test, which reads the OpenAPI documents. `yaml` is already registered at 2.9.1. Its row gains
  the workspace, so no new dependency is added.
- **`packages/authority`'s `tsconfig.json` sets `experimentalDecorators`.** Its tests import P1
  (TC-AE-031 step 2), and P1's index reaches P10's decorators. Its `src/` uses none.
- **`contract/generated/components.ts` was regenerated.** One doc comment changed, A6's wording
  of `EnvelopeTraceContext`. No type changed, so stop condition 6 did not fire.

## Request Changes (2026-11-11)

The user asked for three fixes after the first completion message.

1. **The image.** soorma-core#17's image check failed: `services/org-gateway/Dockerfile` did not
   copy `packages/jcs`, which U2's `org-identity` now depends on (TS6053). The Dockerfile now
   copies `packages/jcs`'s manifest files in the install layer and `packages/jcs/src/` in the
   source layer, and the image builds locally. **D-CG-AE-09's gate now also runs the image
   build for any group whose changes reach S1's dependencies.** Group 2 reached them and the
   gate did not build the image, so the defect reached CI.
2. **An unresolved upstream agent, as the logic model says** (§3 step 7). Its term is the empty
   set, exactly as a registered agent with no grants, and evaluation continues:
   `W = S ∩ P ∩ (U ∪ D)`. The request is denied `upstream_unresolved` only when `W` does not
   contain `R` and an upstream agent did not resolve. When the presenter's declaration covers
   `R`, the request is allowed, re-broadening is load-bearing, and the stamped envelope carries
   `{ hop: n }`. D-AE-09's wording ("so the request is denied") is a consistency fix: denied
   unless the presenter's re-broadening covers `R`. Tests: TC-AE-016 step 2, in
   `evaluate.test.ts` and through `admit`; TC-AE-021 step 2 now states that B declares nothing.
   **The first build departed from the approved logic model, and that was stop condition 2**
   ("a design rule cannot be built as written; never adapt silently"). Generation should have
   stopped and asked, and did not: it read D-AE-09's wording over §3 and listed the choice as
   settled during generation.
3. **`errors[]` at most 10** (D-AE-18 consistency fix; BR-DV-03). P2's `MAX_ERRORS` is 10, S1's
   value. The winning code is picked from every failure, then the first 10 by pointer are kept.
   `errors.md` step 6 and the U3 changelog line say "at most 10". TC-AE-029 step 5 tests 15
   unknown fields, 12 malformed fields, and 12 malformed fields with one unknown field sorting
   after them, which still wins.

## Q-CG Answers

| ID | Answer |
|---|---|
| Q-CG-AE-1 | A: `KeyId`, U2's shape exactly. The effective id rule, `^[a-z0-9][a-z0-9-]{0,15}$`, is in `packages/envelope/README.md` |

## Versions and Vectors

- No new dependency. Ajv 8.20.0 and `yaml` 2.9.1 are at their registered versions.
- **The seal vector, computed independently with the OpenSSL CLI**:
  - key `606162…7f`, over the committed fixed envelope's JCS bytes
  - seal: `v1.k1.Q-eQiLOVy1XmferS0WCQbbFVGda03VvikJg38YuL1-c`
  - the same MAC without the label: `UifXYKcmHAqY-IC8K5ZKPX0bjn2H3ZPUwfB1j43fDVA`
- RFC 8785's §3.2.2 and §3.2.3 examples and its Appendix B numbers pass.
- The worst-case pattern test walks **11 patterns** in the contract. Every match finishes within
  100 ms, so stop condition 4 did not fire.

## Local Run (Step 21, 2026-11-10; again after the Request Changes, 2026-11-11)

| Check | Result |
|---|---|
| `pnpm install --frozen-lockfile` | Pass |
| `build` (generate, typecheck, `tsc -b`) | Pass |
| `lint`, `format:check` | Pass |
| `check:generated`, `check:contract` | Pass |
| `check:deps`, `check:workflows`, `check:code`, `check:secrets`, `check:breached` | Pass |
| `pnpm audit --audit-level moderate` | No known vulnerabilities |
| `pnpm test` (with `db:test`) | **771 passed, 2 skipped** (U2's perf cases, which run at Build and Test), in 45 files; 766 before the Request Changes |
| `docker build -f services/org-gateway/Dockerfile .` | Pass (after the Request Changes) |
| `pnpm bench:admit` | Runs. p50 0.279 ms, p99 0.590 ms, 7033 samples. **For proof that it runs only**: Build and Test records the numbers |

Per package: `jcs` 44; `envelope` 113; `authority` 88; `policy-decision` 9; `perimeter` 44;
`config` 27; `org-identity` 99; `org-gateway` 46 (2 skipped); `contract` 228.

## Coverage

- **L1**: all 38 applicable rows are `Implemented`. The inherited BR-ERR-08 and D-CG-05 are
  `Implemented`. Four rows rest on GAP-AE-001's work-around (soorma-prd#30, Open), and L1-27 on
  GAP-INT-007's (soorma-prd#25, Open).
- **Invariants**: I1 to I10 are `Implemented`, and I11 is N/A. The I8 packaging table was
  re-checked against the packages as built.
- **Test cases**: TC-AE-001 to 039 are automated and pass. **TC-AE-040 is reported only**, by
  `pnpm bench:admit` at Build and Test, and is not a gate.
