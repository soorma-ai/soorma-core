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

**The CLI against the real images, as the user listed** (after commit 1 had been pushed; recorded before the follow-up commit). The four commands were extracted from `ci.yml` and run exactly as written. Wall times are from `/usr/bin/time -p`:

| Command (from `ci.yml`) | Exit | Wall time |
|---|---|---|
| `node tools/checks/run.ts secrets image-packages --image soorma/org-gateway:local --expect @soorma/org-identity` | 0 | 7.03 s |
| `node tools/checks/run.ts secrets image-packages --image soorma/control-gateway:local --forbid @soorma/org-identity` | 0 | 6.92 s |
| `node tools/checks/run.ts secrets image-packages --image soorma/data-gateway:local --forbid @soorma/org-identity,@soorma/identity-resolution,@soorma/authority` | 0 | 7.49 s |
| `node tools/checks/run.ts secrets image-packages --image soorma/event-ingest:local --forbid @soorma/org-identity,@soorma/identity-resolution,@soorma/agent-identity,@soorma/abuse-bound` | 0 | 7.47 s |

**The negative controls**, run at the command level:

| Control | Command | Output | Exit |
|---|---|---|---|
| A planted secret | A throwaway image `FROM soorma/event-ingest:local` adding `/app/planted.pem`, an ed25519 key generated at run time in the session scratchpad, outside the repository; S4's exact command against it | `secrets: soorma/neg-secret:throwaway:/app/planted.pem: holds a private key` | 1 |
| A forbidden package | S1's command with `--forbid @soorma/org-identity` instead of `--expect` | `image-packages: soorma/org-gateway:local: holds @soorma/org-identity` | 1 |
| An expected package missing | S2's command with `--expect @soorma/org-identity` | `image-packages: soorma/control-gateway:local: does not hold @soorma/org-identity` | 1 |
| A failed export: no such image | `--image soorma/no-such-image:none` | `Command failed: docker create soorma/no-such-image:none` | 1 |
| A failed export: truncated | S4's exact command, with `docker export` killed (SIGTERM) about 1 s into its ~6 s export | `docker export of soorma/event-ingest:local failed (exit 143): not scanned` | 1 |

After the planted-secret control, the throwaway image, the key and its build directory were deleted, and no key file entered the repository. After the truncated export, `docker rm` still ran: no container of the image was left.

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
| 43419983338 | `4acb2f0` (commit 1, push to `dev`) | full run, with this change | **green**. Image job **6m36s** (11:48:37 to 11:55:13 UTC). Builds: S1 33 s, S2 to S4 11 s each. One combined check per image, **2 to 3 s each** (S1 3 s, S2 3 s, S3 3 s, S4 2 s; before, two checks of about 77 s each). No-migrations checks 2 s each; S4 self-check 1 s; stack onward 4m48s. `changes` 4 s (decided to run); `sbom-main` and dependency review skipped |
| **Run A: 43420953285** | `b09821a` (commit 1b, the `ci.yml` header fix; push to `dev`) | full run, on the final code | **green**. Image job **5m36s** (11:56:00 to 12:01:36 UTC), against 16m00s (43392989143) and 18m05s (43395738837). Builds: S1 27 s, S2 to S4 7 s each. One combined check per image, **about 1 s each** (S1, S2, S3, S4). No-migrations checks 1 s each; stack onward about 4m17s. Workflow wall time 5m47s. `changes` decided to run (code changed); `sbom-main` and dependency review skipped |
| **Run B: 43421826526** | `cafdd99` (commit 2, `aidlc-docs/` only; push to `dev`) | the image job skipped | **green**. `changes` listed only `aidlc-docs/tooling/ci-image-job/{aidlc-state.md, audit.md, construction/ci-image-job/code/code-summary.md}` for `b09821a..cafdd99`, then `images=false`. The image job was reported **skipped**; the build job ran (2m38s) |
| **Run C: 43422377131** | `8e47393` (PR #27, `pull_request`) | full, on the final head | **green**. Image job 6m25s; build, changes and dependency review passed; `sbom-main` skipped. Commit `8e47393`'s own push run, 43422367762, skipped the image job |
| **43458369029** | `596376c` (#27's merge commit; push to `main`) | main keeps only the SBOM | **green**. Only *SBOM for main's commit* ran; build, changes, image and dependency review were skipped. Artifact `sbom-cyclonedx` kept, 35,083 bytes, expires 2027-02-11 |

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
3. ~~**`sbom-main`'s first run**~~ **Done.** It ran on #27's merge: run 43458369029
   (`596376c`) was green, with only *SBOM for main's commit* running and the
   `sbom-cyclonedx` artifact kept (35,083 bytes). Verified by the user after the merge, and
   on GitHub at close-out.
