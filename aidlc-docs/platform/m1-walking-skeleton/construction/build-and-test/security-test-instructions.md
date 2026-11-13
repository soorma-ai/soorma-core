# Security Test Instructions

The security baseline (SECURITY-01 to 15) across the seven units, checked at this stage, with the
commands that check it and the user's M1 decisions restated.

## Run

```bash
pnpm run check:secrets                         # the repository: no secret, key, or token
pnpm run check:code                            # SQL only through statement(); secret comparisons
                                               # constant-time; no injection tokens
pnpm audit --audit-level moderate              # dependency vulnerabilities
node tools/checks/run.ts secrets image-packages --image <each image> [--expect|--forbid …]
pnpm test                                      # the perimeter, refusal, privilege, and log tests
pnpm stack:smoke                               # TLS 1.3 everywhere; roles; no identifier or secret in logs
pnpm test:e2e                                  # every refusal holds for a raw call
```

CI also runs `actions/dependency-review-action` (moderate and above fail) on pull requests, and
produces a CycloneDX SBOM.

## Results (2026-11-13)

| Check | Result |
|---|---|
| Repository secret scan | Pass |
| Each image's file system scanned for secrets (four images) | Pass |
| Installed packages per image (S1 holds `org-identity`; S2 to S4 their forbid lists; S3, S4 no migrations) | Pass |
| `check:code` (SQL, comparisons, injection) | Pass |
| `pnpm audit --audit-level moderate` | Pass: no known vulnerabilities |
| Privilege tests per role (`soorma_env_app`, `_data`, `_ingest`, migrator; the org roles) | Pass |
| Raw-call refusals on the stack (TC-AR-043, TC-ET-040, TC-ET-006, 007, 009, 090; TC-AC-013) | Pass |
| No identifier or secret in any service's logs (smoke; TC-OI-049, TC-EHA-053) | Pass |
| Refusal timing, known vs unknown principal (TC-OI-062) | No difference: p = 0.82 |

## SECURITY-01 to 15, across the units

| Rule | Status | Notes |
|---|---|---|
| SECURITY-01 | **In transit: compliant. At rest: not applicable in M1, by the user's decision** | TLS 1.3 on every edge and internal call; every store over TLS, `verify-full`. No token or secret value is stored (digests and seeds only) |
| SECURITY-02 | N/A in M1 | No load balancer or API gateway in the local stack |
| SECURITY-03 | **Compliant, except the centralized log service: not applicable in M1, by the user's decision** | JSON logs with request ids and fixed event names; pseudonyms, never identifiers or secrets |
| SECURITY-04 | N/A | No HTML anywhere |
| SECURITY-05 | Compliant | Every body validated against the contract; closed drafts; bounded strings; body limits at every edge (S4's step-1 limits: 64 KiB subscribe, 256 KiB publish) |
| SECURITY-06 | Compliant | One database role per deployable, each with only its statements' privileges; no `DELETE` where records are append-only |
| SECURITY-07 | Compliant | Edges on host loopback only; stores unpublished; one network per environment |
| SECURITY-08 | Compliant | Every operation authenticated by the credential of its face; authority by the one evaluator; no CORS |
| SECURITY-09 | Compliant | Distroless, non-root, read-only images by digest; no default credentials; Problems carry no internals |
| SECURITY-10 | Compliant | Exact versions past the cooldown; frozen lockfile; images and actions pinned; Dependabot; SBOM |
| SECURITY-11 | Compliant, with the accepted residuals below | S1's abuse bound; S2's throttle; S3's bootstrap bound; S4's stream cap and limits |
| SECURITY-12 | Compliant | Argon2id; breached-list check; P (second factor) available; credentials short-lived; ending is a logout; secrets as mounted files only |
| SECURITY-13 | Compliant | Checksummed migrations; append-only attribution records; pinned images and actions |
| SECURITY-14 | **Not applicable in M1, by the user's decision** | Alert rules and the dashboard defined as files and validated (`deploy/monitoring/`); nothing evaluates them in M1 |
| SECURITY-15 | Compliant | Fail closed: unreadable revocation past the bound denies; the organization-level outage is 503 per operation (`stack:outage`: 40 of 40 in four runs; one earlier run failed at its set-up, from this session's own `down -v`, recorded in integration-test-instructions.md) |

**The user's M1 decisions, restated**: SECURITY-01 at rest, SECURITY-03's centralized log service,
and SECURITY-14 are not applicable in M1, because M1 is a local stack with no hosted deployment.
Each is carried to the first hosted deployment.

**No blocking security finding.**
