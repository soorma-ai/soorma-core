# Build and Test Summary: soorma-core#26 (unit `ci-image-job`)

Minimal depth: one unit of CI tooling. The full evidence is in
`construction/ci-image-job/code/code-summary.md`.

## How to Build and Test

The repository's usual gate, unchanged. CI runs the same steps:

- `pnpm install --frozen-lockfile`, `check:deps`, `check:workflows`, `build`, `lint`,
  `format:check`, `check:code`, `check:secrets`, `check:breached`, `check:generated`,
  `check:contract`
- `pnpm test`, with `pnpm db:test`'s `TEST_DATABASE_URL` and `TEST_DATABASE_CONTAINER`
- `pnpm audit --audit-level moderate`
- The image checks, one export each:
  `node tools/checks/run.ts secrets image-packages --image <ref> --forbid|--expect <names>`
  (CI's four commands, in `.github/workflows/ci.yml`)
- The reader comparison, locally only:
  `SOORMA_TAR_COMPARE=<images> pnpm vitest run tools/test/tar-compare.test.ts --silent=false`

## Results

| What | Result |
|---|---|
| Local gate | passed (`pnpm test`: 1,707 passed, 30 skipped; `pnpm audit`: no known vulnerabilities) |
| Memory test, 20 runs | peak growth 0.008 MiB every run (bound 4 MiB; stop line 3 MiB) |
| Reader comparison, four images | identical; 0.27 to 0.35 s against 115 to 117 s |
| CLI on the four images | exit 0, 6.9 to 7.5 s each |
| Negative controls (secret, forbidden, expected missing, no image, truncated export) | each exit 1 |
| Run A **43420953285** (`b09821a`, full) | green; image job **5m36s** (before: 16m00s, 43392989143) |
| Run B **43421826526** (`cafdd99`, `aidlc-docs/` only) | green; image job **skipped** (`images=false`) |
| Run C **43422377131** (PR #27, `8e47393`) | green; image job 6m25s |
| Merge | **#27 merged** 2026-11-13T16:00:53Z as `596376c`; #26 closed automatically |
| main's push run **43458369029** (`596376c`) | green; only `sbom-main` ran; `sbom-cyclonedx` kept (35,083 bytes) |

## Done When (#26)

- [x] The image job measured before and after, with run IDs (above)
- [x] A commit touching only `aidlc-docs/` skips the image job (Run B); a commit touching any
      other path runs it in full (Run A)
- [x] Planted-secret and forbidden-package negative controls fail: by the checks' own tests (the
      existing ones unchanged, plus `tools/test/image-scan.test.ts`) and at the command level
- [x] CI passes on the PR: run 43422377131

## Open Obligations

- Specification gaps: **0 Open, 0 Awaiting PRD** (no PRD; #26 is the specification)
- Slice brief *Proves*: not applicable (no slice brief)
- None. `sbom-main`'s first run on main was green, with the artifact kept (43458369029)
- Follow-ups (not #26): Dependabot `target-branch: dev`; parallel image legs when a fifth
  service is added
