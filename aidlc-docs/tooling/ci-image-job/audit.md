# AI-DLC Audit Log: tooling/ci-image-job (soorma-core#26)

## Initial User Request
**Timestamp**: 2026-11-13T08:50:17Z
**User Input**: "Task: soorma-core#26, making CI's image job faster. Read the issue in full first. It's the specification, including the constraints and \"done when\".

How to run it:

AI-DLC at minimal depth, as its own small initiative, aidlc-docs/tooling/ci-image-job/, separate from platform/m1-walking-skeleton:
Workspace detection.
Requirements at minimal depth: the issue is the requirements, so ask only what it leaves open.
Skip user stories, application design and units: this is one unit.
Code Generation Part 1, a plan, then stop for my approval before you edit anything.
Git: work on dev, and bring it up to origin/dev first; the latest U7 close-out commit is ae5f2f0. Commits end with the Co-Authored-By line. PR from dev to main, with Closes #26 and the Claude Code line in the body.
Hard constraints, restated:

Nothing checked today may stop being checked, for any change that can affect an image or the stack: the same patterns, image coverage, forbid and expect lists, and negative controls.
Actions stay pinned by commit SHA. Permissions stay read-only. check:workflows passes.
Don't change what any test or check asserts; adding tests is fine.
Secrets never go in environment variables, source, or IaC.
The plan must show:

how one tar pass produces both sets of findings;
the job layout: the four images in parallel, then the stack once;
how each parallel leg's image reaches the stack job, built from the commit under test;
the changed-files condition for skipping, with the exact paths;
the decision on the main push run, and why;
how you'll measure before and after, with run IDs.
Gate: the repo's usual local gate, then push and wait for green. Show the skip working with an aidlc-docs/-only commit, and the full run with any other commit. Then open the PR and stop when it needs merging. I merge from my review session."
**AI Response**: "Read soorma-core#26 in full (title: CI: cut the image job's time (one export per image, images in parallel, skip aidlc-docs-only changes); no comments). Started a new AI-DLC initiative at aidlc-docs/tooling/ci-image-job/, separate from platform/m1-walking-skeleton, as the user instructed and as recorded in that initiative's state (\"#26 runs before Build and Test, in its own session and its own initiative\")."
**Context**: INCEPTION - Workspace Detection, initiative start

---

## Workspace Detection
**Timestamp**: 2026-11-13T08:50:17Z
**User Input**: (none; informational stage)
**AI Response**: "Workspace detection findings:
- TARGET_REPO_ROOT: soorma-core (the code changed is soorma-core's CI workflow and tools/checks; soorma-aidlc is the tooling repo and holds no artifact for this initiative).
- INITIATIVE_ROOT: aidlc-docs/tooling/ci-image-job/ (named by the user). No aidlc-state.md existed: a new initiative.
- aidlc-docs/.gitignore: already present, every Session-class pattern from the template present; left unchanged.
- Slice brief or PRD: none for this work. soorma-prd/backlog/ holds only m1-walking-skeleton.md, which does not name #26. PRD Intake: not applicable; issue #26 is the specification.
- Existing code: yes (brownfield). TypeScript on Node 26.13, pnpm 12.18 workspace; GitHub Actions CI (.github/workflows/ci.yml). The code this initiative touches is small and was read in full: ci.yml, tools/checks/{run,secrets,image-packages,tar,workflows}.ts, tools/test/{image-packages,workflows}.test.ts, deploy/local/scripts/stack-up.ts and its test, the compose build sections, .dockerignore. Reverse Engineering skipped: the change is confined to CI tooling already read, and the M1 initiative's artifacts describe the rest.
- Git: on dev, equal to origin/dev at 0095523 (one docs-only commit past ae5f2f0, the U7 close-out: it records #26 before Build and Test). Working tree clean.
- Baseline seen: run 43392989143 (ae5f2f0, push to dev), image job 16m00s; 8 export checks of about 77 s each (about 10m20s); builds 33 s for S1, 10 s each for S2 to S4 (shared cache); everything after the checks 4m18s. Run 43395738837 (0095523, an aidlc-docs-only commit) is running the whole image job today.
- Next: Requirements Analysis at minimal depth."
**Context**: INCEPTION - Workspace Detection complete

---
## Requirements Analysis: measurement and clarifying questions
**Timestamp**: 2026-11-13T08:57:20Z
**User Input**: (none since the initial request)
**AI Response**: "Requirements depth: minimal (issue #26 is the specification). Before writing questions, measured where the image check's time goes, locally on soorma/event-ingest:local (204 MB exported, 7,258 files): today's run.ts secrets --image 2m02s (81 s user, 65 s system CPU); docker export alone 6.3 s; a plain read of the tar 0.1 s; today's walkTar 111 to 120 s. Cause: tools/checks/tar.ts concatenates its whole buffer on every chunk (Buffer.concat([buffer, chunk])), quadratic with the image's 150 MB Node binary. A linear prototype (scratchpad only; no repository file edited) gave the same 7,258 files, names, sizes and content SHA-256s in 0.28 s; one pass of the prototype, every secret pattern and the package reading took 0.22 s. Consequence: with the reader fixed, the parallel layout no longer saves time (estimates: parallel about 6.5 to 7.5 min, serial about 6.5 min, against 16m00s on run 43392989143). Facts for the push: main decision: the 'protect main' ruleset requires a pull request (rules: deletion, non_fast_forward, pull_request) and no status checks; main's last ten first-parent commits are all dev to main PR merges (#16 to #25); no badge reads main's runs. Created inception/requirements/requirement-verification-questions.md: Q1 scope (A: the whole issue plus the tar reader fix, recommended; B: the tar fix, one pass, the skip and the push: main decision in one serial job; C: the issue as written without the tar fix); Q2 to Q5 the extension opt-ins (Security Baseline recommended Yes; PR Checkpoint, QA Test Cases, JIRA/GitHub issues recommended No). Platform Invariants not offered: CI tooling is not platform-plane code. Stopped at the question gate."
**Context**: INCEPTION - Requirements Analysis, question gate

---
## Requirements Analysis: the user's answers
**Timestamp**: 2026-11-13T09:25:55Z
**User Input**: "Answers to the requirements questions:

Q1: B. The linear walkTar, one pass per image, the aidlc-docs/-only skip, and the push: main decision, all in one serial image job. Scope item 2 is not done:
your measurement shows it saves no time once the reader is fixed;
moving images between jobs would add a new gap, proving the image the stack runs is the one that was scanned.
Record that reason in requirements.md. Revisit parallel legs when a fifth service is added.
Q2: A. Q3: B. Q4: B. Q5: B.
Two more things the plan must cover:

The SBOM. Dropping push: main means no SBOM is generated for commits on main.
Check what NFR-WC-12, 17, 18, 20 and SECURITY-10, 13 require of the SBOM.
Then either show that the PR run's SBOM meets it, or keep a minimal push: main run that only generates and keeps the SBOM.
Record the decision and the remaining risk, including that main can move between the PR run and the merge. Today only dev→main PRs reach main.
The linear reader.
It replaces walkTar's internals without changing what it returns, and its existing tests stay unchanged.
Add a test that reads a tar holding one entry well over 16 MiB, streamed in small chunks. It asserts the entry is listed with no content, that the files after it are read correctly, and that memory stays bounded.
Add a comparison test showing the new reader gives the same files as the old one on a real exported image. Run it locally and record the numbers; it doesn't need to be a CI test.
Log these answers in audit.md word for word, then write requirements.md and the plan, and stop for approval as you said."
**AI Response**: "Answers recorded, keyed by question ID (requirement-verification-questions.md):
- Q1: B (the linear walkTar, one pass per image, the aidlc-docs/-only skip and the push: main decision, in one serial image job; scope item 2 not done, for the user's two reasons: no time saved once the reader is fixed, and moving images between jobs adds a gap in proving the stack runs the scanned image; revisit parallel legs when a fifth service is added).
- Q2: A (Security Baseline enabled: all SECURITY rules blocking).
- Q3: B (PR Checkpoint review gates skipped; the dev to main PR is the review).
- Q4: B (QA Test Cases not generated).
- Q5: B (no tickets; #26 is the ticket).
No question Deferred. Two additions recorded as requirements: the SBOM decision for main (check NFR-WC-12, 17, 18, 20 and SECURITY-10, 13; show the PR run's SBOM meets them or keep a minimal SBOM-only push: main run; record the decision and residual risk, including main moving between the PR run and the merge), and the linear reader's tests (the existing tests unchanged; a new test with one entry well over 16 MiB streamed in small chunks, asserting it is listed with no content, the files after it read correctly, and memory bounded; a local comparison against the old reader on a real exported image, numbers recorded, not a CI test). Security Baseline rules loaded now."
**Context**: INCEPTION - Requirements Analysis, answers received

---
## Requirements Analysis complete; Code Generation Part 1: the plan, and the approval prompt
**Timestamp**: 2026-11-13T09:31:13Z
**User Input**: (none since the answers)
**AI Response**: "Checked the SBOM requirements: NFR-WC-18 (M1 wire-contract nfr-requirements.md) requires a CycloneDX JSON SBOM on every build, by anchore/sbom-action pinned by SHA, kept as a build artifact (verification: CI artifact present); SECURITY-10 requires an SBOM for production deployments; NFR-WC-12, 17, 20 and SECURITY-13 say nothing of the SBOM itself (lockfile, vulnerability scanning, pinned actions and permissions, access-controlled pipelines). Found: Dependabot opens its PRs against main (dependabot.yml has no target-branch; Dependabot's #15 was merged into main), so main can move between a dev to main PR's run and its merge; artifact retention is 90 days (the maximum). Decision recorded in requirements.md: the PR run's SBOM does not fully meet SECURITY-10 (it describes GitHub's test merge commit, filed under the PR run, and diverges if main moved); keep a minimal push: main run, job sbom-main, that only installs, builds, and generates and keeps the SBOM with the same pinned steps; build, changes and image-and-stack skip a push to main. Remaining risk recorded (main's merged tree untested if main moved, mitigation by practice, possible follow-up Dependabot target-branch: dev; sbom-main first exercised by this PR's merge; 90-day expiry unchanged). Wrote inception/requirements/requirements.md (FR-01 to 06, NFR-01 to 06, the reason scope item 2 is not done, extension configuration, security compliance) and construction/working/ci-image-job-code-generation-plan.md (sections 1 to 7 covering the one-pass scan, the serial job layout, how images reach the stack (no transfer), the exact changed-files condition, the push: main and SBOM decision, the measurement with run IDs 43392989143, 43395738837 (aidlc-docs-only commit, image job 18m05s, run in full) and runs A, B, C; Steps 1 to 17; stop conditions 1 to 5). One addition flagged for approval: imageScanFindings fails when docker export exits non-zero (today a truncated export fails open). Approval prompt presented; stopped before editing anything outside aidlc-docs/."
**Context**: CONSTRUCTION - Code Generation Part 1, awaiting approval

---
## Code Generation Part 1: the user's approval
**Timestamp**: 2026-11-13T09:38:09Z
**User Input**: "Approved: the requirements and the plan, including the guard on docker export's exit code. Start Code Generation Part 2.

One condition, on Step 6's memory test:

Run it 20 times locally before the first commit, and record the highest arrayBuffers growth you see.
If any run comes within 1 MiB of the 4 MiB bound, stop and show me the numbers. Don't loosen the bound and don't add retries.
Noted, no action needed here:

Your correction is right: Dependabot targets main.
From now on, my pre-merge check confirms main hasn't moved since the PR's last CI run, and re-runs the checks if it has.
Changing Dependabot's target-branch to dev is a follow-up, not part of #26. List it in the code summary's follow-ups.
Then continue as planned. Show Run A in full and Run B with the image job skipped, open the PR from dev to main with Closes #26, and stop when it needs merging."
**AI Response**: "Requirements and the Code Generation plan APPROVED, including the docker export exit-code guard. Condition recorded on Step 6: the memory test run 20 times locally before the first commit, the highest arrayBuffers growth recorded; any run at or above 3 MiB (within 1 MiB of the 4 MiB bound) stops the work with the numbers shown; the bound is not loosened and no retry is added. Recorded: the user's pre-merge check now confirms main has not moved since the PR's last CI run, and re-runs the checks if it has; Dependabot target-branch: dev listed as a follow-up in the code summary, not part of #26. Starting Code Generation Part 2."
**Context**: CONSTRUCTION - Code Generation Part 1 approved; Part 2 starts

---
## Code Generation Part 2: Steps 1 to 13, and the local gate
**Timestamp**: 2026-11-13T11:48:12Z
**User Input**: "retry" (after a re-run of gate steps printed rc=127: zsh does not word-split a quoted command held in a variable; the steps had not run)
**AI Response**: "The retry was the bash re-run that had already passed: lint, format:check, build, check:secrets, check:workflows, check:code, and pnpm test (1,707 passed, 30 skipped) on the final tree, against a fresh pnpm db:test database. Steps 1 to 13 done (plan checkboxes marked): tools/checks/tar.ts linear walkTar; tools/checks/image-scan.ts (scanTar, imageScanFindings with the docker export exit-code guard); imageFindings and imagePackageFindings moved there from secrets.ts and image-packages.ts; run.ts one scan per --image; tools/test/image-scan.test.ts and tools/test/tar-compare.test.ts added; no existing test file modified; ci.yml (changes job, image-and-stack needs and if with four combined checks, build skipped on push to main, sbom-main); README's CI paragraph. Full gate passed (install, check:deps, check:workflows, build, lint after one fix to the new test (an async generator with no await, now a sync generator through Readable.from), format:check, check:code, check:secrets, check:breached, check:generated, check:contract, pnpm test, pnpm audit: no known vulnerabilities). The user's condition on Step 6: 20 runs of the memory test on the final version, peak arrayBuffers growth 0.008 MiB in every run (maximum 0.008 MiB, bound 4 MiB, stop line 3 MiB): no stop; no retries; the bound unchanged. Images rebuilt; CI's four combined commands passed in 7 to 8 s each (S4's single secrets form took 2m02s before); both single forms still work; a throwaway negative-control image (runtime ed25519 key, @soorma/org-identity package.json on S2) gave both findings from one export and exit 1, then was removed; a fake docker export exiting 1 after a partial tar failed the check (not scanned). The skip script from ci.yml, run in a throwaway repository, skipped only the two aidlc-docs-only cases (push and PR), and ran for code, mixed, empty, zero base, missing base, a rename out, a quoted path and an aidlc-docs-old/ lookalike. The reader comparison on the four images: identical in every case (S1 7,202 files, 0.35 s against 115.01 s; S2 7,261, 0.30 s against 116.08 s; S3 7,222, 0.27 s against 117.27 s; S4 7,258, 0.34 s against 115.48 s). Code summary written: construction/ci-image-job/code/code-summary.md. Next: commit 1, push, Run A."
**Context**: CONSTRUCTION - Code Generation Part 2, before commit 1

---
## Code Generation Part 2: the user's command-level checks, and the ci.yml header
**Timestamp**: 2026-11-13T11:51:48Z
**User Input**: "Progress reviewed. The code checks out: the linear reader keeps its contract, one export feeds both checks, the exit-code guard works, the skip script's 11 cases all decided correctly, and the memory runs are fine.

Before commit 1, run the CLI against the real images. The gate so far skipped images.

The four commands exactly as ci.yml has them, against the four local images. Each exits 0. Record each one's wall time.
The negative controls, at the command level, with their exit codes:
A planted secret. Build a throwaway image FROM soorma/event-ingest:local that adds a private key generated at runtime. Never write the key into the repo. Run S4's combined command: the secret is reported, exit 1. Then delete the image and the key.
A forbidden package. Run S1's combined command with --forbid @soorma/org-identity instead of --expect: exit 1.
An expected package missing. Run S2's combined command with --expect @soorma/org-identity: exit 1.
A failed export. Use a nonexistent image reference: exit non-zero. Then show a truncated export failing through the exit-code guard, for example by killing docker export partway. If that isn't practical, say so and explain why the guard is still covered.
Fix the ci.yml header comment. main is reached through pull requests whose run tested the merge result as of that run. main can move before the merge; point to the remaining risk recorded in aidlc-docs/tooling/ci-image-job/.
Record the commands, times and exit codes in the code summary. Then finish Step 12 (the comparison) and continue: commit 1, Run A in full, commit 2 (aidlc-docs/ only) with Run B skipped, then the PR. Stop when it needs merging."
**AI Response**: "This message arrived after commit 1 (4acb2f0) had been pushed; its push run 43419983338 was in progress. Said so plainly. The skip script was tested on 10 cases, not 11 (code summary lists them). Done now, all recorded in the code summary: the four commands extracted from ci.yml and run exactly: exit 0 each, wall times 7.03 s (S1), 6.92 s (S2), 7.49 s (S3), 7.47 s (S4). Negative controls: a planted secret (throwaway image FROM soorma/event-ingest:local, runtime ed25519 key in the session scratchpad, never in the repository; S4's exact command): 'holds a private key', exit 1; the image, the key and its build directory deleted. S1 with --forbid @soorma/org-identity: 'holds @soorma/org-identity', exit 1. S2 with --expect @soorma/org-identity: 'does not hold @soorma/org-identity', exit 1. A nonexistent image reference: 'docker create' failed, exit 1. A truncated export, practical and done: docker export killed (SIGTERM) about 1 s into S4's ~6 s export: 'docker export of soorma/event-ingest:local failed (exit 143): not scanned', exit 1, the container still removed. Step 12 had already been done before this message (identical on all four images). ci.yml's header comment and sbom-main's comment corrected: main is reached through pull requests whose run tested the merge result as of that run; main can move before the merge (Dependabot targets main); the remaining risk pointed to requirements.md. check:workflows, prettier, and workflows.test.ts (8 passed) pass. Plan: let run 43419983338 finish (it measures the same code), then commit the header fix and the records as a follow-up code commit; its full push run is Run A; then commit 2 (aidlc-docs only) for Run B skipped; then the PR."
**Context**: CONSTRUCTION - Code Generation Part 2, between commit 1 and Run A

---
## Code Generation Part 2: Run A
**Timestamp**: 2026-11-13T12:02:14Z
**User Input**: (none)
**AI Response**: "Run 43419983338 (commit 1, 4acb2f0) green: image job 6m36s; one combined check 2 to 3 s per image. Commit 1b (b09821a: the ci.yml header and sbom-main comment fix, with the command-level records) pushed. Run A = 43420953285 (b09821a), green: Build, check, and test 3m36s; Changed files 7 s (images=true, code changed); image job 5m36s against 16m00s (43392989143) and 18m05s (43395738837); combined checks about 1 s each; builds S1 27 s, S2 to S4 7 s; sbom-main and dependency review skipped. Next: commit 2, aidlc-docs only, for Run B."
**Context**: CONSTRUCTION - Code Generation Part 2, Step 14 done

---
## Build and Test: Run B, and PR #27
**Timestamp**: 2026-11-13T12:06:15Z
**User Input**: (none)
**AI Response**: "Run B = 43421826526 (cafdd99, aidlc-docs only), green: the changes job listed only the three aidlc-docs/tooling/ci-image-job/ files for b09821a..cafdd99 and output images=false; the image job reported skipped; the build job ran. Opened PR #27 (dev to main), body with the measurements and run IDs, the SBOM decision and remaining risk, why scope item 2 is not done, Closes #26, and the Claude Code line. Wrote construction/build-and-test/build-and-test-summary.md (minimal): done-when 1 to 3 met; 4 (CI passes on the PR) is checked before the merge; specification gaps 0 Open, 0 Awaiting PRD; Proves not applicable (no slice brief); sbom-main's first run is after the merge. This commit is aidlc-docs only: its push run should skip the image job; the PR's run is full (the PR's diff includes code). Then stop: #27 needs merging, from the user's review session."
**Context**: CONSTRUCTION - Build and Test

---
