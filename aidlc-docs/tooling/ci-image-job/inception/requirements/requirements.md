# Requirements: CI's image job, faster (soorma-core#26)

## Intent Analysis

- **User request**: soorma-core#26, *CI: cut the image job's time (one export per image, images
  in parallel, skip aidlc-docs-only changes)*. The issue is the specification: its scope,
  constraints and *done when* are the requirements. This document records only what the issue
  left open, and the answers (audit.md, *Requirements Analysis: the user's answers*).
- **Request type**: Enhancement (CI tooling performance)
- **Scope**: Multiple components, all CI tooling: `.github/workflows/ci.yml`, `tools/checks/`,
  `tools/test/`, and the README's CI paragraph
- **Complexity**: Simple to moderate. Security tooling, so the constraints are strict
- **Depth**: Minimal

## The Measurement Behind the Scope

The issue attributes the image job's time to whole-image exports, run twice per image, one
image at a time. Measured locally on `soorma/event-ingest:local` (204 MB exported, 7,258
files):

| What | Time |
|---|---|
| Today's `run.ts secrets --image` | 2m02s (81 s user, 65 s system CPU) |
| `docker export` alone | 6.3 s |
| A plain read of the tar in Node | 0.1 s |
| Today's `walkTar` | 111 to 120 s |
| A linear `walkTar` (prototype) | 0.28 s, the same files, names, sizes and content SHA-256s |
| One pass: the linear reader, every secret pattern, the package reading | 0.22 s |

**Cause**: `tools/checks/tar.ts` runs `buffer = Buffer.concat([buffer, chunk])` on every chunk.
With the image's 150 MB Node binary, every 64 KiB chunk re-copies the growing buffer, so the
work is quadratic. This accounts for most of the ~77 s each of the 8 checks takes in CI.

**Before, in CI**:
- Run **43392989143** (`ae5f2f0`, push to `dev`): image job **16m00s**. Builds: S1 33 s, S2 to
  S4 10 s each. Eight export checks of 76 to 80 s each, 10m20s in total. Stack, smoke, outage,
  workspace build and e2e: 4m18s.
- Run **43395738837** (`0095523`, a commit touching only `aidlc-docs/`): image job **18m05s**,
  run in full.

## Functional Requirements

| ID | Requirement | Source |
|---|---|---|
| FR-01 | **A linear tar reader.** `walkTar`'s internals are replaced. Its signature and what it returns are unchanged: regular files only, in order; a GNU long name (`L`) applies to the next entry; a file over `TAR_CONTENT_LIMIT` (16 MiB) is listed with `content: undefined`. Each entry's bytes are copied at most once, and bytes never returned (oversized files, non-regular entries) are discarded as they arrive | Q1 B; the user's addition |
| FR-02 | **One export per image.** One `docker export` and one tar pass produce both the secret findings and the installed-package findings. The existing CLI forms keep working (`run.ts secrets --image`, `run.ts image-packages --image`), and naming both checks with one `--image` runs them in one pass. `ci.yml` uses the combined form | #26 scope 1 |
| FR-03 | **Skip the image job when every changed file is under `aidlc-docs/`.** A job-level condition from a changed-files step, not workflow-level `paths-ignore`, so the job reports *skipped*. Any other change runs everything, as today. Services are not selected by what changed | #26 scope 3 |
| FR-04 | **The `push: main` run** no longer runs the build, test and image jobs. It keeps a minimal job that only generates and keeps the SBOM for main's commit (FR-05) | #26 scope 4; the user's SBOM instruction |
| FR-05 | **The SBOM for main.** See *Decision: the SBOM and the `push: main` run* | The user's SBOM instruction |
| FR-06 | **Tests added, none changed.** (a) A combined pass over one tar stream, read once, finds a planted secret and a forbidden package. (b) A tar holding one entry well over 16 MiB, streamed in small chunks: the entry is listed with no content, the files after it are read correctly, and memory stays bounded. (c) A comparison of the new reader with the old one on a real exported image: run locally, numbers recorded, not run in CI | #26 constraints; the user's addition |

**Scope item 2 (the four images in parallel) is not done**, by the user's decision (Q1 B), for
two reasons:
1. The measurement shows it saves no time once the reader is fixed: about 6.5 to 7.5 min
   parallel against about 6.5 min serial.
2. Moving images between jobs would add a new gap: proving that the image the stack runs is
   the one that was scanned. In one job the stack runs the very image that was scanned.

**Revisit parallel legs when a fifth service is added.**

## Non-Functional Requirements (the issue's constraints)

| ID | Requirement | Source |
|---|---|---|
| NFR-01 | **Nothing checked today stops being checked**, for any change that can affect an image or the stack: the same secret patterns; all four images; the same `--forbid` and `--expect` lists (S1 expects `@soorma/org-identity`; S2 forbids `@soorma/org-identity`; S3 forbids `@soorma/org-identity,@soorma/identity-resolution,@soorma/authority`; S4 forbids `@soorma/org-identity,@soorma/identity-resolution,@soorma/agent-identity,@soorma/abuse-bound`); S3's and S4's no-migrations checks; S4's `JSON.rawJSON` self-check and its negative; the stack, smoke, outage and e2e; and the negative controls | #26; SECURITY-10, 13; NFR-WC-12, 17, 18, 20 |
| NFR-02 | **Actions pinned by commit SHA**, with the release tag in a comment. No new action is needed. Permissions stay `contents: read`. `check:workflows` passes | NFR-WC-20; SECURITY-10, 13 |
| NFR-03 | **No test or check changes what it asserts.** Tests may be added | #26 |
| NFR-04 | **Secrets never go in environment variables, source or IaC.** The changed-files step reads commit SHAs only, and passes them through `env:` rather than `${{ }}` in the script, so no expression is interpolated into shell | #26; SECURITY-12 |
| NFR-05 | **Fail closed.** A diff that can't be computed (a new branch, a force-push whose `before` is gone, a git error) or is empty runs the image job. A failing changed-files job fails the workflow; it never silently skips | SECURITY-15 |
| NFR-06 | **Measured before and after with run IDs**: the image job's time on a full run, and an `aidlc-docs/`-only commit showing it skipped | #26 done-when |

## Decision: the SBOM and the `push: main` run

**What the requirements ask of the SBOM:**
- **NFR-WC-18** (M1 `construction/wire-contract/nfr-requirements/nfr-requirements.md`): *an SBOM,
  CycloneDX JSON, on every build*, produced by Syft through `anchore/sbom-action` pinned by SHA,
  *kept as a build artifact*. Verification: *CI artifact present*.
- **SECURITY-10**: *projects MUST generate a Software Bill of Materials for production
  deployments*; pinned tool versions in CI.
- **NFR-WC-12, 17, 20; SECURITY-13**: nothing on the SBOM itself. They cover the frozen
  lockfile, vulnerability scanning (`pnpm audit`, dependency review, Dependabot), pinned actions
  and read-only permissions, and access-controlled pipeline definitions. This change keeps all
  of them.

**Does the PR run's SBOM meet them? Not fully.** The PR run builds GitHub's test merge commit
(`refs/pull/N/merge`). Its SBOM describes main's merged tree only if main hasn't moved since that
run, and it's filed under the PR run, not under main's commit SHA. Releases and any future
deployment point at main's commits; `contract-v0.1.0`, for example, is on `c1e3d7f`. An SBOM
for production deployments has to be findable for, and describe, that exact commit.

**Can main move between the PR run and the merge? Yes.** Most of main's history is dev→main PR
merges (#16 to #25), but **Dependabot opens its update PRs against `main`**:
`.github/dependabot.yml` sets no `target-branch`, and Dependabot's #15 was merged into main. A
Dependabot merge between a dev→main PR's last run and its merge changes the merged tree, and the
pull_request run is not re-run when only the base branch moves.

**Decision: keep a minimal `push: main` run that only generates and keeps the SBOM.** The build,
test, image and stack jobs no longer run on `push: main`. A new job, `sbom-main`, runs only on a
push to main. It checks out main's commit, sets up pnpm and Node, installs with the frozen
lockfile, builds, and runs the same pinned `anchore/sbom-action` and `actions/upload-artifact`
steps as the build job, with the same artifact name. It runs no checks, tests or images. About
one minute against today's ~16 to 18 min. The build job's SBOM steps are unchanged, so every
build (dev push, PR) still keeps its SBOM, and the existing workflow test's assertion that the
build job runs `anchore/sbom-action@` and `actions/upload-artifact@` still holds.

**Remaining risk, recorded:**
1. **Main's merged tree is not re-tested on main.** If main moves between a dev→main PR's last
   run and its merge (in practice, a Dependabot merge into main), the merged result's checks,
   tests, images and stack never run on that exact tree. The SBOM still does, so the supply-chain
   record stays exact. Mitigation, by practice: before merging a dev→main PR, if main has moved
   since the PR's last run, bring dev up to date with main first, so the PR runs again. A
   possible follow-up, outside #26: Dependabot `target-branch: dev`, so only dev→main PRs reach
   main.
2. **The `sbom-main` job can't run before merge.** It is first exercised by the merge of this
   PR. Its result (job green, artifact `sbom-cyclonedx` present on main's run) is the check for
   the review session after merging.
3. **Artifacts expire** after the repository's retention, 90 days (the maximum). This is
   unchanged from today.

## Extension Configuration

| Extension | Enabled | Decided At |
|---|---|---|
| Security Baseline | Yes | Requirements Analysis (Q2 A) |
| PR Checkpoint | No | Requirements Analysis (Q3 B): the dev→main PR is the review |
| QA Test Cases | No | Requirements Analysis (Q4 B) |
| JIRA Tickets (GitHub issues) | No | Requirements Analysis (Q5 B): #26 is the ticket |
| soorma Platform Invariants | Not offered | CI tooling is not platform-plane code |

## Security Compliance (Requirements Analysis)

| Rule | Status | Note |
|---|---|---|
| SECURITY-10 | Compliant | Lockfile, `pnpm audit`, dependency review and the pinned tools unchanged; the SBOM kept on every build and on main's commits |
| SECURITY-12 | Compliant | No credential added; the stack's throwaway secrets still come from `stack:init` on the runner |
| SECURITY-13 | Compliant | No new action; all pinned by SHA; definitions change only by PR |
| SECURITY-15 | Compliant | The skip fails closed (NFR-05) |
| SECURITY-01 to 09, 11, 14 | N/A | No data store, endpoint, network, IAM or runtime component changes |

## Done When (from #26, with this initiative's evidence)

- [ ] The image job measured before (runs 43392989143, 43395738837) and after (the push run of
      the code commit), with run IDs
- [ ] A commit touching only `aidlc-docs/` shows the image job skipped; a commit touching any
      other path runs it in full
- [ ] Planted-secret and forbidden-package negative controls still fail, shown by the checks' own
      tests: the existing ones unchanged, plus FR-06 (a)
- [ ] CI passes on the PR
