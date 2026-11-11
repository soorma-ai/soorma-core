# soorma-core

The open-core substrate for governed agentic systems.

> **Early construction.** This repository was reset on 10 September 2026 and
> started from an empty tree. Design precedes code here — see
> [Background](#background). Built so far: the wire contract, and the
> organization level's control face (`org-gateway`, S1) with its local stack.
> The environment-level services follow.

## What this is

soorma.ai is a platform on which developers across organizations build their own
agentic systems. It has two parts:

- **Harness** — the SDK a tenant embeds in each agent. Client-side, in the hot
  path, and advisory: it enforces nothing. Ships separately, under Apache 2.0.
- **Substrate** — this repository. The shared server-side planes that agents run
  against, and where enforcement lives: Event, Registry & Schema, Memory,
  Identity, Access Policy, Observability, Eval, and Workflow.

`soorma-core` is meant to be sufficient on its own for a developer or a small
team working in a single environment. Governing _many people_ doing that —
approval routing, separation of duties, retention policy, multi-tenant
operation — belongs to the commercial platform above it.
[`CONTRIBUTING.md`](CONTRIBUTING.md) sets out where the line falls and the rules
that decide it.

## What is here

| Path                                             | What it is                                                                                                                                                                                                                                                                                                                                                                                                                                       | Licence            |
| ------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------ |
| [`contract/`](contract/)                         | The wire contract: the envelope and `Delivery` schemas, the shared OpenAPI components, the written conventions, generated TypeScript types, and the compatibility fixtures. **Pre-release** (`0.y.z`)                                                                                                                                                                                                                                            | Apache 2.0         |
| [`services/org-gateway/`](services/org-gateway/) | S1, the organization level's control face: human principals, their material, and the organization sign-in. See its [README](services/org-gateway/README.md)                                                                                                                                                                                                                                                                                      | FSL-1.1-ALv2       |
| [`packages/`](packages/)                         | The organization level's modules: `org-identity`, `abuse-bound`, `identity-resolution`, `perimeter` (also the one Problem table), `config`. The envelope perimeter and authority evaluation, which the event transport (S4) will host: [`envelope`](packages/envelope/README.md), [`authority`](packages/authority/README.md) (the entry point, `createEnvelopeAdmission(dependencies).admit(request)`), `policy-decision`, and `jcs` (RFC 8785) | FSL-1.1-ALv2       |
| [`seams/`](seams/)                               | Type definitions for the identity-resolution and policy-decision seams                                                                                                                                                                                                                                                                                                                                                                           | Apache 2.0         |
| [`deploy/`](deploy/)                             | The local stack (Docker Compose, `stack:init`, the local CA) and the monitoring files                                                                                                                                                                                                                                                                                                                                                            | FSL-1.1-ALv2       |
| [`data/breached/`](data/breached/)               | The breached-secret list, derived from SecLists, with its manifest                                                                                                                                                                                                                                                                                                                                                                               | MIT (derived data) |
| [`tools/`](tools/)                               | Repository checks: the dependency register, licences, workspace configuration, workflow integrity, SQL, secret comparisons, injection tokens, and secret patterns                                                                                                                                                                                                                                                                                | FSL-1.1-ALv2       |
| [`DEPENDENCIES.md`](DEPENDENCIES.md)             | Every dependency, and every exception to the dependency policy                                                                                                                                                                                                                                                                                                                                                                                   | FSL-1.1-ALv2       |

## Working on it

The toolchain is pinned: **Node 26.13.0** (`.node-version`) and **pnpm 12.18.0**
(`packageManager` in `package.json`). Install pnpm without Corepack.

```sh
pnpm install --frozen-lockfile
pnpm run build             # generate the contract types, then typecheck
pnpm run lint
pnpm run format:check
pnpm test
pnpm run check:generated   # the committed types match the schemas
pnpm run check:contract    # contract rules, licences, meta-schema, compatibility
pnpm run check:deps        # register, licences, workspace configuration, pnpm version
pnpm run check:workflows   # SHA-pinned actions, read-only default permissions
pnpm run check:code        # SQL from sql.ts only, constant-time secret comparisons, injection tokens
pnpm run check:secrets     # no material, token, or private key in the tracked files
pnpm run check:breached    # the breached list matches its manifest
pnpm audit --audit-level moderate
pnpm run bench:admit       # the envelope admission latency, reported (never a gate)
```

The database tests need PostgreSQL: `pnpm db:test` starts a throwaway, pinned container and
prints a `TEST_DATABASE_URL` to export before `pnpm test` (`pnpm db:test:stop` removes it).
Without it, the database tests fail rather than skip. To run the organization level locally,
see [`services/org-gateway/README.md`](services/org-gateway/README.md); the local stack needs
Docker Engine 26 and Docker Compose 2.26.0 or later, which `pnpm stack:up` checks.

CI ([`.github/workflows/ci.yml`](.github/workflows/ci.yml)) runs all of these
on every push and pull request, against a PostgreSQL service container; builds
the S1 image, scans its file system for secrets, and runs the stack smoke test;
keeps a CycloneDX SBOM of each build; and reviews dependency changes on pull
requests.

## Licence

**Source-available, not open source.** `soorma-core` is licensed under
[FSL-1.1-ALv2](LICENSE): you may do anything with it except offer a commercial
product or service that competes with soorma.ai. Internal use at any scale,
research, and education are all permitted.

**Each release becomes Apache 2.0 two years after it ships** — automatically,
and not revocably by soorma.ai. The harness SDKs, the seam interfaces, and the
contract definitions are Apache 2.0 from the start and permanently.

[`LICENSE`](LICENSE) is authoritative; the above is a summary.

## Background

This repository previously held an MIT-licensed implementation — 477 commits and
17 releases between December 2025 and April 2026 — built to explore a
distributed-cognition architecture. It did that successfully, but it was not
built to be an enterprise platform, and refactoring it toward an architecture it
was never shaped for would have cost more than starting again. It is retired
rather than evolved, and its full history is preserved intact in an archived
repository. **Nothing here is a continuation of that code.** The
distributed-cognition thinking survives the reset; the implementation does not.

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md). Contributions require a signed
Contributor License Agreement — [`CLA.md`](CLA.md) for individuals,
[`CCLA.md`](CCLA.md) for organizations.

For anything security-sensitive, email founders@soorma.ai rather than opening a
public issue.
