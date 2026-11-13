# Build Instructions

M1 walking skeleton, soorma-core. Run on 2026-11-13 at `dev` = `4119ac0` (U7's code merged as
`c1e3d7f`; `contract-v0.1.0` tagged on it), plus this stage's measurement harnesses.

## Prerequisites

| Tool | Version | Notes |
|---|---|---|
| Node | 26.13.0 (`.node-version`; `engines` `^26.13.0`) | |
| pnpm | 12.18.0 (`packageManager`) | |
| Docker Engine | 26 or later (run: 29.5.3) | the images, the local stack, the test database |
| Docker Compose | 2.26.0 or later (run: 5.1.4) | |

No environment variable carries a product secret. The stack's secrets are generated into
`deploy/local/.secrets/` (git-ignored, mode 0600) and mounted as files. The one environment
variable that carries a password is `TEST_DATABASE_URL`, the throwaway test database's generated
superuser URL (U2's test harness, D-CG-OI-15); it exists only for the tests.

## Build Steps

### 1. Install dependencies

```bash
pnpm install --frozen-lockfile
```

### 2. The configuration, register, licence, and workflow checks

```bash
pnpm run check:deps
pnpm run check:workflows
```

### 3. Build every unit

```bash
pnpm run build   # generate the contract's types, typecheck every package, tsc -b
```

### 4. The static checks

```bash
pnpm run lint
pnpm run format:check
pnpm run check:code        # SQL through statement(), secret comparisons, injection tokens
pnpm run check:secrets     # the repository
pnpm run check:breached    # the breached list against its manifest
pnpm run check:generated   # the contract's generated types are current
pnpm run check:contract    # the contract documents and their compatibility classifications
pnpm audit --audit-level moderate
```

### 5. The four images, and their checks

```bash
docker build -f services/org-gateway/Dockerfile     -t soorma/org-gateway:local .
docker build -f services/control-gateway/Dockerfile -t soorma/control-gateway:local .
docker build -f services/data-gateway/Dockerfile    -t soorma/data-gateway:local .
docker build -f services/event-ingest/Dockerfile    -t soorma/event-ingest:local .

node tools/checks/run.ts secrets image-packages --image soorma/org-gateway:local --expect @soorma/org-identity
node tools/checks/run.ts secrets image-packages --image soorma/control-gateway:local --forbid @soorma/org-identity
node tools/checks/run.ts secrets image-packages --image soorma/data-gateway:local \
  --forbid @soorma/org-identity,@soorma/identity-resolution,@soorma/authority
node tools/checks/run.ts secrets image-packages --image soorma/event-ingest:local \
  --forbid @soorma/org-identity,@soorma/identity-resolution,@soorma/agent-identity,@soorma/abuse-bound
```

S3 and S4 ship no migrations (`docker export` of each image holds no `env-store/migrations/`), and
S4's `JSON.rawJSON` self-check passes in its image and refuses without it. The commands are CI's
image job (`.github/workflows/ci.yml`).

## Result (2026-11-13)

| Step | Result |
|---|---|
| Install (frozen lockfile) | Pass |
| `check:deps`, `check:workflows` | Pass |
| `build` (18 s) | Pass |
| `lint`, `format:check`, `check:code`, `check:secrets`, `check:breached`, `check:generated`, `check:contract` | Pass |
| `pnpm audit --audit-level moderate` | Pass: no known vulnerabilities |
| S1, S2, S3, S4 images: build, secret scan, installed packages | Pass, all four |
| S3 and S4 ship no migrations | Pass |
| S4's `JSON.rawJSON` self-check in the image; refused without it (`ConfigurationError`) | Pass |

**Build artifacts**: each package's `dist/`; `contract/generated/` and `contract/dist/`; the images
`soorma/{org-gateway,control-gateway,data-gateway,event-ingest}:local`. CI also produces a CycloneDX
SBOM (`sbom-cyclonedx`) for each run and for `main`'s commit.

## Troubleshooting

- **`pnpm install` refuses the lockfile**: a dependency changed without `pnpm-lock.yaml`. Never
  install without `--frozen-lockfile` here; add the dependency through the register (`DEPENDENCIES.md`)
  and the lockfile in one change.
- **`check:generated` fails**: run `pnpm run generate`, then review the generated diff.
- **An image check fails `--forbid`**: a production dependency reached a deployable it must not
  (U4 to U7's closure rules). Fix the manifest; never widen the forbid list.
