# Code Summary: U2 `org-identity`

**Unit**: U2 `org-identity` (soorma-core#5). Control face, organization level
**Built against**: ID @ `prd-identity-v1.0`, PF @ `prd-platform-foundations-v1.3`
**Plan**: `construction/working/org-identity-code-generation-plan.md` (revision 3; Q-CG-1 A,
Q-CG-2 A, Q-CG-3 B)
**Generated**: 2026-11-08 to 2026-11-09, in seven commit groups on `dev`, each after the
pre-commit gate (D-CG-OI-14)

| Group | Steps | Commit |
|---|---|---|
| 1. The contract | 1 to 4 | `4089286` |
| 2. Workspace and dependencies | 5 to 7 | `5ebcb9b` |
| 3. Domain modules | 8 to 14 | `42a293f` |
| 4. The service | 15 to 18 | `dfa6c97` |
| 5. Deployment | 19 to 22 | `032b718` |
| 6. Checks and CI | 23 to 25 | `787b3be` |
| 7. Documentation and completion | 26 to 29 | this commit |

---

## Files

175 files added and 31 modified outside `aidlc-docs/`.

### Created

| Area | Files |
|---|---|
| Contract | `contract/org-gateway.openapi.yaml`; `contract/generated/org-gateway.ts`; `contract/fixtures/0.1.0/org-gateway/**` (6 definitions, valid and invalid); 8 new `fixtures/0.1.0/problem/` fixtures; `contract/tsconfig.build.json`; `contract/test/org-gateway.test.ts` |
| `packages/config` (P9) | `schema/tenancy.schema.json`; `src/tenancy.ts` (`loadOrganization`, `loadMigrator`, `loadSettings`, `listSecrets`) |
| `packages/org-identity` (P10) | `src/crypto/` (secret types and `secretEqual`, canonical JSON, the hashing semaphore, the Argon2id hasher, the key ring, the sign-in token, TOTP, the seed cipher, the log pseudonym, signed internal requests); `src/policy/` (the K policy, the breached list); `src/store/` (the store, the migration runner); `src/domain/` (the flows, the ports, the pruner); `src/sql.ts`; `src/clock.ts`; `src/lifetimes.ts`; `src/errors.ts`; `migrations/0001_init.sql`; the test-database harness (`test/harness/`) |
| `packages/abuse-bound` (P8) | `src/abuse-bound.ts`, `src/failed-attempt-writer.ts`, `src/sql.ts` |
| `seams/identity-resolution`, `packages/identity-resolution` (P6) | The seam's types (Apache 2.0); `src/resolver.ts`, `src/sql.ts` |
| `packages/perimeter` (P1) | `src/presenter.ts` |
| `services/org-gateway` (S1) | `src/main.ts`, `migrate.ts`, `healthcheck.ts`, `apps.ts`, `http.ts`, `problems.ts`, `security-log.ts`, `contract-validator.ts`, `runtime.ts`, `health.ts`, `clock.module.ts`, `edge/`, `internal/`; `Dockerfile`; `README.md`; `test/` and `test/perf/` |
| Deployment | `deploy/local/compose.yaml`, `config/tenancy.yaml`, `db/roles.sql`, `db/pg_hba.conf`, `db/init/10-soorma-roles.sh`, `scripts/stack-init.ts`, `stack-certs.ts`, `db-test.ts`, `smoke.ts`; `deploy/monitoring/alerts.yaml`, `dashboard.yaml`, and their schemas; `deploy/test/stack-init.test.ts` |
| Data | `data/breached/top-1m.sha256-64.bin` (binary, 999,996 prefixes) and `MANIFEST.md` |
| Tools | `tools/checks/code.ts` (`sql`, `compare`, `inject`), `secrets.ts`, `breached.ts`; `tools/breached/derive.ts`; tests |
| Repository | `tsconfig.build.json` (the solution), `vitest.config.js`, `.dockerignore`, `.gitattributes`, `seams/LICENSE` |

### Modified

- `contract/conventions/errors.md`, `credentials.md`, `components.openapi.yaml`: amendment A4,
  U2's four codes, `ProblemFieldError.header` and `.reason`, `SecretRejectedReason`, the two
  principal-reference definitions; `contract/CHANGELOG.md`
- U1's contract tooling, extended to surface documents: `scripts/validator.ts`,
  `scripts/checks/compat.ts`, `sides.ts`, `model.ts`, `scripts/generate-types.ts`; U1's tests
  for TC-WC-024 step 10, TC-WC-025 step 7, TC-WC-026, and the type-level fixture
- `tools/checks/workspace.ts`, `configuration.ts`, `run.ts`: `pnpm-workspace` globs,
  `workspace:*` dependencies, the new checks
- `package.json`, `pnpm-workspace.yaml`, `pnpm-lock.yaml`, `DEPENDENCIES.md`, `REUSE.toml`,
  `.gitignore`, `.prettierignore`, `eslint.config.js`, `README.md`
- `.github/workflows/ci.yml`, `.github/dependabot.yml`

---

## Decisions as Built

D-CG-OI-01 to 15 are built as the plan states them, with these specifics:

| Decision | As built |
|---|---|
| D-CG-OI-01 | Packages as planned. The seam is `@soorma/identity-resolution-seam`, because two directories are named `identity-resolution` |
| D-CG-OI-02 | Every imported package exports `source` → `src/index.ts`, `types` → `dist/index.d.ts`, `default` → `dist/index.js`. **Vitest takes the `source` condition through `ssr.resolve.conditions`** (Vite 8.3.5): `resolve.conditions` alone fails to resolve the package. The cross-package proof passes under typecheck, Vitest, `tsc -b`, and `node` on `dist/`. `erasableSyntaxOnly` stays on |
| D-CG-OI-05 | `SecretBytes`, `Verifier`, `SecretText`, `TotpCode`. The `compare` check flagged `material !== undefined` on a `SecretText \| undefined`; the code was changed to test the configuration entry instead, so the check stays strict |
| D-CG-OI-09 | **Q-CG-3 B**: SecLists `Passwords/Common-Credentials/xato-net-10-million-passwords-1000000.txt` at `00f80ec` (2026-10-31), unchanged since `c205c36`. Source SHA-256 `424a3e03…0caf51` (matched by an independent download); derived SHA-256 `17b8378e…5bd9dd` |
| D-CG-OI-10 | `node:26.13.0@sha256:6d2c7d5d…` (pushed 2026-10-29, from `docker-library/repo-info` `7d6f332`: the tag's current digest was pushed 2026-11-06, inside the cooldown); `gcr.io/distroless/nodejs26-debian13:nonroot@sha256:9b945e92…` (uploaded 2026-10-31T23:45Z; Node v26.13.0); `postgres:18.4@sha256:a02db8ca…` (pushed 2026-08-06; 18.6 is inside the cooldown, and there is no 18.5) |
| D-CG-OI-14 | Each group committed only after the gate passed; the gate gained `check:code`, `check:secrets`, `check:breached`, and `check:workflows` as they were built |
| D-CG-OI-15 | As amended: `roles.sql` is idempotent and race-safe, its database grants take `soorma.target_database`; `failed_attempts.id` is the one identity column, and its sequence is granted |

### Found during generation, beyond the plan (technology decisions; flagged for review)

1. **U1's contract tooling extended to surface documents.** The validator, fixture loader, and
   type generator handled only the shared components. They now load `org-gateway.openapi.yaml`
   under its own `$id`; fixtures live at `{version}/{surface}/{Definition}/{valid|invalid}/`;
   `generated/org-gateway.ts` is generated and drift-checked
2. **P10 declares ports** (`AttemptBound`, `FailureRecorder`) that `@soorma/abuse-bound`
   satisfies structurally, because `abuse-bound` builds on `org-identity`
3. **A missing `Soorma-Contract-Version`** is `unsupported_contract_version` with
   `supportedVersions`
4. **An unknown path or method is a bare 404** with the Soorma headers and no body: the contract
   defines no 404 Problem, and no error code was added
5. **`fastify` 5.12.7** is a direct dependency of the service (the version
   `@nestjs/platform-fastify` pins; published 2026-10-13, MIT), with its register row
6. **The internal listener refuses a request that declares a body.** Fastify does not read a
   GET body, so one sent anyway could not be hashed as received (P-06 `bsh`)
7. **Enrollment material contains `soorma`**, so reusing it as K is refused as `context_word`
   before the `reused` check
8. **Argon2id parameters are injectable for tests.** Production (`productionHasher`) always uses
   NFR-OI-11's, asserted by a test. Flow tests use 1 MiB and one pass; TC-OI-029 uses a recording
   double that records the real parameters; TC-OI-043 and TC-OI-062 hash with the real ones
9. **The derivation script and the breached check** are at `tools/breached/derive.ts` and
   `tools/checks/breached.ts`, so lint and typecheck cover them
10. **`db:test` was built in Group 3**, not Group 5, so the gate could run the database tests
    from Group 3 on
11. **`pg_hba.conf`** has one non-network line: the superuser over the container's own Unix
    socket, by peer, which the image's initialisation and healthcheck need. Every network line
    is `hostssl` with SCRAM
12. **The secrets check's key pattern** requires a key's base64 body and END line: jose's
    PEM-parsing code holds the header string alone
13. **Unused dependencies removed**: the NestJS peers from `abuse-bound`, `identity-resolution`,
    and `perimeter`, and `pg` from `abuse-bound`, which reaches the store through `org-identity`
14. **Secrets delivery (Q-CG-4 B, the user's answer, at the Code Generation review)**: Compose
    `file:` secrets keep the host file's owner and mode on Linux, and Compose refuses
    `environment:` secrets in a read-only service (probed on the GitHub runner). So
    `org-secrets-init` (root; only `CHOWN`, `DAC_OVERRIDE`, `FOWNER`; no network; read-only;
    exits) copies this level's secrets into the `org-secrets` volume, one subdirectory per
    service, owner and mode 0400; each service mounts only its own subpath, read-only. One
    volume and one init container per level. `stack:up` refuses Docker Engine below 26 and
    Compose below 2.26.0. shared-infrastructure.md (*Secrets*) and Infrastructure Design §3, §7
    amended
15. **Two contract behaviours written down** (the user's request): a missing
    `Soorma-Contract-Version` is `unsupported_contract_version` at check-order step 5
    (`versioning.md`, `errors.md`); an unknown path is a bare 404 in 0.1.0 (`errors.md`)

---

## Dependencies (exact)

| Dependency | Version | Where | Kind |
|---|---|---|---|
| `@nestjs/common` | 12.3.2 | `org-identity`, `org-gateway` | Runtime |
| `@nestjs/core`, `@nestjs/platform-fastify` | 12.3.2 | `org-gateway` | Runtime |
| `fastify` | 5.12.7 | `org-gateway` | Runtime |
| `reflect-metadata` | 0.2.2 | `org-identity`, `org-gateway` | Runtime |
| `rxjs` | 7.8.2 | `org-identity`, `org-gateway` | Runtime |
| `jose` | 6.2.14 | `org-identity` | Runtime |
| `pg` | 8.23.1 | `org-identity` | Runtime |
| `ajv` | 8.20.0 | `config`, `org-gateway` (runtime); `contract` (development) | |
| `yaml` | 2.9.1 | `config`, `org-gateway` (runtime); `contract`, `tools` (development) | |
| `@types/pg` | 8.23.1 | `org-identity` | Development |
| `typescript` | 6.0.3 | root, `contract`, `tools` | Development |

Every version was published on or before 2026-11-01. No lifecycle script; licences pass;
`pnpm audit` clean.

---

## Test Cases

452 tests pass in CI's configuration (31 files), with 2 gated performance cases.

| Test file | Test cases |
|---|---|
| `contract/test/org-gateway.test.ts`, `problem.test.ts`, `conventions.test.ts` | TC-OI-022 (step 1), 023, 025; TC-WC-024 step 10, 025 step 7, 026 |
| `packages/config/test/tenancy.test.ts` | TC-OI-019, 048 |
| `packages/org-identity/test/crypto.test.ts` | TC-OI-003 (token), 039, 043, 044, 052 (step 3), 054 |
| `packages/org-identity/test/secret-policy.test.ts`, `tools/test/breached.test.ts` | TC-OI-012, 013, 042, 058 |
| `packages/org-identity/test/store.test.ts` | TC-OI-022, 051 |
| `packages/org-identity/test/domain.test.ts` | TC-OI-001, 002, 004 to 011, 014 to 018, 021, 028, 034 to 038, 040, 041, 053 |
| `packages/abuse-bound/test/abuse-bound.test.ts` | TC-OI-011, 028, 030 to 033, 050 |
| `packages/identity-resolution/test/resolver.test.ts` | TC-OI-029 (resolution), 060 |
| `packages/perimeter/test/presenter.test.ts` | TC-OI-024, 026, 027 |
| `services/org-gateway/test/edge.test.ts` | TC-OI-002 to 007, 010, 011, 014, 016, 020, 023, 024, 026, 027, 042, 047, 052, 055 |
| `services/org-gateway/test/internal.test.ts` | TC-OI-045, 046, 047 |
| `services/org-gateway/test/logs-and-timing.test.ts` | TC-OI-025, 029, 048, 049, 061; NFR-OI-11 wiring |
| `services/org-gateway/test/tls.test.ts`, `deploy/test/stack-init.test.ts` | TC-OI-056 (in process and certificates), 057 |
| `services/org-gateway/test/monitoring.test.ts` | TC-OI-049 (the monitoring files) |
| `tools/test/code-checks.test.ts` | TC-OI-057 (patterns); D-CG-OI-03 to 05 |
| `pnpm stack:smoke` (CI's stack job) | TC-OI-056, 057 (the stack) |
| `services/org-gateway/test/perf/` (`pnpm test:perf`, Build and Test only) | TC-OI-059, 062 |

---

## Local Smoke Run (Step 27, 2026-11-09)

Against a fresh test database and a fresh stack:

| Command | Result |
|---|---|
| `pnpm install --frozen-lockfile` | Pass |
| `build`, `lint`, `format:check` | Pass |
| `check:deps`, `check:workflows`, `check:code`, `check:secrets`, `check:breached`, `check:generated`, `check:contract` | Pass |
| `pnpm test` (with `db:test`) | Pass: 452 tests, 2 gated |
| `pnpm audit --audit-level moderate` | Pass |
| The image build, and the secret check over its file system | Pass |
| `stack:init`, `stack:up`, `stack:smoke` | Pass: 18 smoke checks; 22 after Q-CG-4 B (the init container, and each service's own secrets: owner, mode 0400, read-only) |

### For Build and Test

- **TC-OI-059 and TC-OI-062** run there (`pnpm test:perf`). On this workstation, Argon2id at
  64 MiB measured 171 ms at Step 9 and about 710 ms later in the session (8 MiB: 90 ms; low
  power mode off; heavy swap history), which puts NFR-OI-19's 500 ms p95 for `authenticate`
  at risk on this machine as it was. TC-OI-062 steps a test clock 16 minutes between attempts,
  so the abuse bound never refuses during its 200 + 200 samples
- **CI's first run on Linux**: Compose's `uid`, `gid`, and `mode` on file secrets were verified
  on Docker Desktop (Compose v5.1.4); the stack job is their first run on the GitHub runner

---

## Security Compliance (SECURITY-01 to 15)

| Rule | Status | Note |
|---|---|---|
| SECURITY-01 | **In transit: compliant. At rest: not applicable in M1, by the user's decision** | TLS 1.3 on every listener and to PostgreSQL (`verify-full`); seeds AES-256-GCM; K Argon2id |
| SECURITY-02 | N/A in M1 | No gateway or load balancer in the local stack |
| SECURITY-03 | **Compliant, except the centralized log service: not applicable in M1, by the user's decision** | JSON logs, request ids, fixed events, pseudonyms only; TC-OI-049 and the smoke test find no identifier or secret |
| SECURITY-04 | N/A | No HTML |
| SECURITY-05 | Compliant | Every input validated against the contract (strict Ajv), closed bodies, bounded strings, 16 KiB |
| SECURITY-06 | Compliant | Least-privilege database roles; the app role has no DDL and no `DELETE` on principals or material |
| SECURITY-07 | Compliant | Edge on host loopback only; internal and database ports unpublished; one network per environment |
| SECURITY-08 | Compliant | No CORS; the internal interface requires a signed request per call |
| SECURITY-09 | Compliant | Distroless, non-root, read-only; no default credentials; Problems carry no internal detail |
| SECURITY-10 | Compliant | Exact versions past the cooldown; images by digest; Dependabot for npm, actions, docker, compose |
| SECURITY-11 | Compliant, with the accepted residuals | The abuse bound, the hashing semaphore, the decoy; residuals: allowance exhaustion, the unknown-identifier flood |
| SECURITY-12 | Compliant | No credential in source; secrets generated into git-ignored files; the `secrets` check over the repository and the image |
| SECURITY-13 | Compliant | Pinned images and actions; explicit Dockerfile copies; the frozen lockfile |
| SECURITY-14 | **Not applicable in M1, by the user's decision** | Alert rules and the dashboard defined as files and tested; nothing evaluates them |
| SECURITY-15 | Compliant | Fail closed: configuration, key material, the breached list, and `synchronous_commit` stop start-up; store and hashing failures are 503 |

## Invariant Compliance (I1 to I11)

I1 to I10 **Implemented**; I11 N/A (Construction makes technology selections by design). The
invariant matrix records each risk and what closes it; the I8 packaging table was re-checked:
nothing commercial was built.

## L1 Coverage

All 32 applicable L1 rows `Implemented`; 11 N/A; 0 Missing
(`functional-design/l1-coverage-matrix.md`).
