# Code Summary: unit `ci-image-job` (soorma-core#26)

Requirements: `inception/requirements/requirements.md`. Scope per Q1 B: the linear tar reader,
one export and one pass per image, the `aidlc-docs/`-only skip, and the `push: main` decision,
in one serial image job. Scope item 2 (parallel legs) is not done; revisit when a fifth service
is added.

## Files

**Modified**
- `tools/checks/tar.ts`: `walkTar`'s internals are now linear (FR-01). It queues chunks rather
  than concatenating them, copies a returned entry once, and drops bytes it never returns. The
  signature, `TarFile`, `TAR_CONTENT_LIMIT` and the results are unchanged.
- `tools/checks/secrets.ts`, `tools/checks/image-packages.ts`: `imageFindings` and
  `imagePackageFindings` moved to `image-scan.ts`, since only `run.ts` called them.
  `SECRET_PATTERNS`, `textFindings`, `tarFindings`, `heldPackages` and `packageFindings` are
  unchanged.
- `tools/checks/run.ts`: one export and pass per `--image` invocation, for every image check
  named. Each check's findings print as before. The existing forms and their edge findings
  (`needs --image <ref>`, `names no package to check`) are unchanged.
- `.github/workflows/ci.yml`:
  - a new `changes` job (the skip condition);
  - `image-and-stack` gains `needs: changes` and `if`, and its eight export checks become four
    combined ones with the same lists;
  - `build` skips a push to main;
  - a new `sbom-main` job (the SBOM for main's commit).

  No new action, no `permissions` key, and every `uses:` is an existing SHA pin.
- `README.md`: the CI paragraph (it said "the S1 and S2 images").

**Created**
- `tools/checks/image-scan.ts`: `scanTar`, one walk for both checks; and
  `imageScanFindings`: docker create, one docker export, docker rm. It fails when
  `docker export` exits non-zero (the approved guard).
- `tools/test/image-scan.test.ts`:
  - the one-pass test: one read of the stream, a planted secret, a forbidden package and a
    missing expected one;
  - a clean image;
  - the 64 MiB entry streamed in 4,093-byte chunks, with memory bounded under 4 MiB.
- `tools/test/tar-compare.test.ts`: the old reader (from git at `0095523`) against the new one
  on real exported images. Skipped unless `SOORMA_TAR_COMPARE` is set, so it doesn't run in CI.

**No existing test file is modified** (`git diff --name-only -- '*.test.ts'` is empty).

## Local Evidence (before the first commit)

**The gate**: `pnpm install --frozen-lockfile`, `check:deps`, `check:workflows`, `build`,
`lint`, `format:check`, `check:code`, `check:secrets`, `check:breached`, `check:generated`,
`check:contract`, `pnpm test` (1,707 passed, 30 skipped, against `pnpm db:test`'s database) and
`pnpm audit --audit-level moderate` (no known vulnerabilities). All pass. Lint first failed on
the new test (an async generator with no `await`), which now uses a sync generator through
`Readable.from`. The affected steps and `pnpm test` were re-run on the final tree and pass.

**The memory test, 20 runs** (the user's condition; stop at or above 3 MiB): run 20 times on
the final version, each in a fresh vitest process. Peak `arrayBuffers` growth was 0.008 MiB in
every run, so the **maximum was 0.008 MiB** against the 4 MiB bound. No failures, no retries.
An earlier 20 runs, on the version before the lint fix, gave the same 0.008 MiB.

**The images**, rebuilt from the working tree. CI's four combined commands, with its exact
lists:

| Image | Command | Result | Time |
|---|---|---|---|
| S1 `soorma/org-gateway:local` | `secrets image-packages --expect @soorma/org-identity` | Passed | 7 s |
| S2 `soorma/control-gateway:local` | `secrets image-packages --forbid @soorma/org-identity` | Passed | 7 s |
| S3 `soorma/data-gateway:local` | `secrets image-packages --forbid @soorma/org-identity,@soorma/identity-resolution,@soorma/authority` | Passed | 7 s |
| S4 `soorma/event-ingest:local` | `secrets image-packages --forbid @soorma/org-identity,@soorma/identity-resolution,@soorma/agent-identity,@soorma/abuse-bound` | Passed | 8 s |

For comparison, the single `secrets --image` form on S4 took **2m02s** locally before the
change. Both single forms still work, at 7 s and 8 s on S4.

**The negative control**: a throwaway image `FROM soorma/control-gateway:local`, with an
ed25519 key generated at run time at `/app/leak.pem` and
`/app/node_modules/@soorma/org-identity/package.json`. The S2 combined command gave
`holds a private key` and `holds @soorma/org-identity`, two findings from one export, with
**exit 1**. The image and its build context were removed afterwards.

**The export guard**: a fake `docker` on `PATH` wrote a valid partial tar, then exited 1. The
combined command failed with `docker export of any failed (exit 1): not scanned`, exit 1.

**The skip condition**: the `changes` step's script, taken from `ci.yml`, was run in a
throwaway git repository:

| Case | Result |
|---|---|
| push, `aidlc-docs/` only | skip |
| pull request, `aidlc-docs/` only | skip |
| push, `tools/` changed | run |
| push of two commits, docs then code | run |
| empty diff | run |
| new branch (zero base) | run |
| base missing (force-push) | run |
| rename out of `aidlc-docs/` | run |
| quoted path under `aidlc-docs/` | run (conservative) |
| `aidlc-docs-old/` (prefix lookalike) | run |

**The reader comparison** (FR-06 c), on the four rebuilt images:

Run: `SOORMA_TAR_COMPARE=<the four images> pnpm vitest run tools/test/tar-compare.test.ts --silent=false`, 4 passed. Each image was exported once, then read by both readers; the old reader came from `git show 0095523:tools/checks/tar.ts`. The comparison covers every regular file's name, size and content SHA-256, in order.

| Image | Files | Linear reader | Old reader | Identical |
|---|---|---|---|---|
| S1 `soorma/org-gateway:local` | 7,202 | 0.35 s | 115.01 s | yes |
| S2 `soorma/control-gateway:local` | 7,261 | 0.30 s | 116.08 s | yes |
| S3 `soorma/data-gateway:local` | 7,222 | 0.27 s | 117.27 s | yes |
| S4 `soorma/event-ingest:local` | 7,258 | 0.34 s | 115.48 s | yes |

## CI Evidence

| Run | Commit | What it shows | Result |
|---|---|---|---|
| 43392989143 | `ae5f2f0` (before) | full run | image job 16m00s; 8 export checks of 76 to 80 s |
| 43395738837 | `0095523` (before; `aidlc-docs/` only) | ran in full | image job 18m05s |
| Run A (pending) | commit 1 | the full run, with this change | recorded in the next commit |

## Security Compliance

| Rule | Status | Note |
|---|---|---|
| SECURITY-10 | Compliant | Lockfile, `pnpm audit`, dependency review and pins unchanged; SBOM on every build and on main's commits (`sbom-main`) |
| SECURITY-12 | Compliant | No secret in env, source or IaC. The changed-files step passes commit SHAs through `env:`. The test key and the negative control's key are generated at run time |
| SECURITY-13 | Compliant | No new action; every `uses:` pinned by SHA; workflow changes reach main only by PR |
| SECURITY-15 | Compliant | The skip fails closed (every case but `aidlc-docs/`-only runs the job); a failed export fails the check |
| SECURITY-01 to 09, 11, 14 | N/A | No data store, endpoint, network, IAM or runtime component changes |

## Follow-ups (not part of #26)

1. **Dependabot `target-branch: dev`**, so only dev→main PRs reach main (requirements.md,
   remaining risk 1). Until then, the user's pre-merge check confirms main hasn't moved since
   the PR's last CI run, and re-runs the checks if it has.
2. **Parallel image legs**: revisit when a fifth service is added (Q1 B).
3. **`sbom-main`'s first run** happens on this PR's merge: the job should be green with the
   `sbom-cyclonedx` artifact present. This is checked in the review session after merging.
