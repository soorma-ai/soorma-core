# soorma-core

The open-core substrate for governed agentic systems.

> **Status: M1, the walking skeleton, is complete** (November 2026). On a local stack, a human
> administrator signs in, registers two agents, and those agents exchange an event within one
> environment. The event carries scope, origin, and an actor chain that the platform stamps,
> not the agents. A credential from another environment is refused, and so is an agent's attempt
> to set a field the platform owns. The wire contract is published as
> [`contract-v0.1.0`](https://github.com/soorma-ai/soorma-core/tree/contract-v0.1.0/contract)
> (pre-release). Everything here is pre-release and runs on a local stack only. See
> [What is not built yet](#what-is-not-built-yet).

## What this is

soorma.ai is a platform on which developers across organizations build their own agentic
systems. It has two parts:

- **Harness**: the SDK a tenant embeds in each agent. Client-side, in the hot path, and
  advisory: it enforces nothing. It ships separately under Apache 2.0, in
  [soorma-sdk](https://github.com/soorma-ai/soorma-sdk).
- **Substrate**: this repository. The shared server-side planes that agents run against, and
  where enforcement lives: Event, Registry & Schema, Memory, Identity, Access Policy,
  Observability, Eval, and Workflow.

`soorma-core` is meant to be sufficient on its own for a developer or a small team working in a
single environment. Governing _many people_ doing that (approval routing, separation of duties,
retention policy, multi-tenant operation) belongs to the commercial platform above it.
[`CONTRIBUTING.md`](CONTRIBUTING.md) sets out where the line falls and the rules that decide it.

**Every rule is enforced at the platform's edge, on the raw request.** Nothing depends on a
client library: a tenant who never links the SDK gets exactly the same checks. M1 proves that
with raw HTTPS calls.

## What runs today

The local stack runs an **organization** (`o1`) with one project and two **environments**, `e`
and `e2`. The organization level is shared. Each environment has its own services, its own
PostgreSQL store, its own keys, and its own network. Nothing crosses from one environment to the
other.

| Service                                                    | Face                  | Who calls it | What it does                                                                                                                 | Local edge (`e` / `e2`)  |
| ---------------------------------------------------------- | --------------------- | ------------ | ---------------------------------------------------------------------------------------------------------------------------- | ------------------------ |
| [S1 `org-gateway`](services/org-gateway/README.md)         | Organization, control | Humans       | First authentication of a configured Admin, sign-in, renewal, logout, changing one's own secret or second factor             | `https://localhost:8441` |
| [S2 `control-gateway`](services/control-gateway/README.md) | Environment, control  | Humans       | Environment credentials from an S1 sign-in; grants to humans; registering logical agents; issuing their registration secrets | `8442` / `8443`          |
| [S3 `data-gateway`](services/data-gateway/README.md)       | Environment, data     | Agents       | Exchanging a registration secret for a short-lived agent credential (bootstrap), and renewing it                             | `8444` / `8445`          |
| [S4 `event-ingest`](services/event-ingest/README.md)       | Environment, data     | Agents       | Publishing an event, and subscribing to an environment's events over a server-sent event stream                              | `8446` / `8447`          |

Every edge serves TLS 1.3 on the host's loopback, with a certificate from a local CA that
`pnpm stack:init` creates. Each service's README covers its operations, configuration, secrets,
and operations notes.

### The M1 journey

One journey runs through all four services. It is M1's definition of done:

1. **The first Admin gets in.** H (`h@example.com`, named in the local stack's configuration)
   completes a one-time first authentication at S1, signs in, and exchanges the sign-in for an
   environment credential at `e`'s S2.
2. **H grants permissions and registers two agents.** H grants themselves `agent:register`,
   `event:publish`, and `event:subscribe`, then registers agents A and B. Each records H as its
   sponsor and a snapshot of what H held. H then issues a registration secret for each.
3. **Each agent instance bootstraps.** At `e`'s S3, it exchanges its secret for a short-lived
   agent credential, and renews it.
4. **B subscribes, A publishes, B receives.** At `e`'s S4, B opens a stream and A publishes. B's
   `Delivery` carries an envelope with `e`'s scope, origin `autonomous`, and the actor chain `[A]`,
   all stamped and sealed by S4.
5. **The boundary holds.** A credential from `e2` publishes nothing at `e`, and one from `e`
   nothing at `e2`. A
   draft that tries to set a platform-stamped field is refused, naming the field.

The executable version of this journey is
[`e2e/agent-registration.test.ts`](e2e/agent-registration.test.ts): raw HTTPS calls, one step
per test, each using the agents, secrets, and credentials the step before made. Read it beside
the service READMEs to see each request and response. Every operation is defined in the
[contract](contract/README.md).

## Getting started

### Prerequisites

- **Node 26.13.0** (`.node-version`) and **pnpm 12.18.0** (`packageManager` in `package.json`).
  Install pnpm without Corepack.
- **Docker Engine 26 or later** and **Docker Compose 2.26.0 or later**, for the test database
  and the local stack. `pnpm stack:up` checks both.
- The OpenSSL CLI, for the local stack's certificates.

### Build

```sh
pnpm install --frozen-lockfile
pnpm run build             # generate the contract's types, typecheck, compile
```

### Run the tests

**The unit and integration tests need a test database.** The tests that touch PostgreSQL fail
rather than skip without one:

```sh
pnpm db:test                  # starts a throwaway PostgreSQL 18 container, and prints two values
export TEST_DATABASE_URL=…    # copy both from its output
export TEST_DATABASE_CONTAINER=soorma-db-test
pnpm test
pnpm db:test:stop             # removes the container
```

`pnpm db:test` refuses to start a second container. If one is already running, run
`pnpm db:test:stop` first: the values are printed only when the container starts.

`pnpm test` skips the suites that need a running stack or a performance flag. They are below.

### Run the local stack

```sh
pnpm stack:init     # generates every secret into deploy/local/.secrets/ (git-ignored, mode 0600)
pnpm stack:up       # builds the four images, migrates the stores, starts S1, and S2 to S4 in e and e2
pnpm stack:smoke    # optional: the smoke test CI runs
pnpm stack:down -v  # stops the stack and removes its data
```

`stack:init` never overwrites a secret, so run it once. Secrets reach the containers as mounted
files, never as environment variables. The first Admin's single-use enrollment material is
written to `deploy/local/.secrets/handover/first-admin-1.txt`.
[S1's README](services/org-gateway/README.md#running-the-local-stack) explains the secrets, the
local CA, and how to call the stack with `curl`.

### Run the end-to-end proofs

**The e2e tests need a running stack, and a fresh one.** The first Admin's enrollment material
works once, so on a stack that a smoke or e2e run already used, the run fails at its first step
with a 403:

```sh
pnpm run build                                # the e2e tests import the built workspace
pnpm stack:down -v && pnpm stack:up           # fresh volumes, every time
pnpm test:e2e                                 # the M1 journey, then credential and event edge cases
pnpm stack:down -v
```

`pnpm stack:outage` demonstrates the environments working while the organization level is
stopped. It also needs a fresh stack.

### Checks and measurements

CI runs every check below on each push to `dev` and each pull request
([`.github/workflows/ci.yml`](.github/workflows/ci.yml)). It also builds and scans the four
images, then runs the smoke test, the outage demonstration, and the e2e proofs, each on a fresh
stack. The image job is skipped only when every changed path is under `aidlc-docs/`.

```sh
pnpm run lint
pnpm run format:check
pnpm run check:generated   # the committed contract types match the schemas
pnpm run check:contract    # contract rules, licences, meta-schema, compatibility
pnpm run check:deps        # the dependency register, licences, workspace configuration
pnpm run check:workflows   # SHA-pinned actions, read-only default permissions
pnpm run check:code        # SQL from sql.ts only, constant-time secret comparisons, injection tokens
pnpm run check:secrets     # no material, token, or private key in the tracked files
pnpm run check:breached    # the breached-secret list matches its manifest
pnpm audit --audit-level moderate
```

Latency is measured and reported, never gated in CI. In process: `pnpm bench:admit` and
`pnpm bench:revocation`, and, with the test database, `pnpm test:perf:s2` and
`pnpm test:perf:agent-facts`. On a fresh stack: `pnpm test:perf:stack`, then `pnpm test:perf`
(S1, which also needs the test database).
[`performance-test-instructions.md`](aidlc-docs/platform/m1-walking-skeleton/construction/build-and-test/performance-test-instructions.md)
gives each one's set-up, and M1's figures.

## Repository map

| Path                                 | What it is                                                                                                                                                                                       | Licence            |
| ------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------ |
| [`contract/`](contract/README.md)    | The wire contract: envelope and `Delivery` schemas, one OpenAPI document per service, the written conventions, generated TypeScript types, and compatibility fixtures. **Pre-release** (`0.y.z`) | Apache 2.0         |
| [`services/`](services/)             | The four deployables, S1 to S4 (above)                                                                                                                                                           | FSL-1.1-ALv2       |
| [`packages/`](packages/)             | The modules the services are built from (below)                                                                                                                                                  | FSL-1.1-ALv2       |
| [`seams/`](seams/)                   | Type definitions for the identity-resolution and policy-decision seams, where an alternative implementation can plug in                                                                          | Apache 2.0         |
| [`e2e/`](e2e/)                       | The end-to-end proofs on the local stack, by raw calls, and the stack latency harness                                                                                                            | FSL-1.1-ALv2       |
| [`deploy/`](deploy/)                 | The local stack (Docker Compose, its scripts, configuration, and local CA) and the monitoring files: alert rules and a dashboard                                                                 | FSL-1.1-ALv2       |
| [`tools/`](tools/)                   | The repository checks behind `pnpm run check:*`                                                                                                                                                  | FSL-1.1-ALv2       |
| [`data/breached/`](data/breached/)   | The breached-secret list, derived from SecLists, with its manifest                                                                                                                               | MIT (derived data) |
| [`aidlc-docs/`](aidlc-docs/)         | Requirements, design, and test records for each initiative (below)                                                                                                                               | FSL-1.1-ALv2       |
| [`DEPENDENCIES.md`](DEPENDENCIES.md) | Every dependency, and every exception to the dependency policy                                                                                                                                   | FSL-1.1-ALv2       |

### Packages

| Package                                                 | Used by                      | What it does                                                                                                                                                                    |
| ------------------------------------------------------- | ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [`service-kit`](packages/service-kit/README.md)         | all                          | The shared runtime: the store and migration runner, secret types and constant-time comparison, the HTTP adapter over TLS 1.3, contract validation, health, and the security log |
| [`perimeter`](packages/perimeter/README.md)             | all                          | The credential checks every edge shares, and the one place a refusal becomes an RFC 9457 Problem                                                                                |
| `config`                                                | all                          | Loads and validates `tenancy.yaml` and the secrets it names                                                                                                                     |
| `org-identity`                                          | S1                           | Human principals, authentication material, sign-ins, keys, TOTP, and the organization's store                                                                                   |
| `identity-resolution`                                   | S1                           | Resolves a human's secret, second factor, or enrollment material to a principal                                                                                                 |
| `abuse-bound`                                           | S1, S3                       | Bounds failed attempts per principal or agent, and records them                                                                                                                 |
| [`env-store`](packages/env-store/README.md)             | S2, S3, S4                   | An environment's store: one PostgreSQL per environment, its migrations, its transactions                                                                                        |
| [`registry`](packages/registry/README.md)               | S2, S3, S4                   | Grants to humans, accepted permission identifiers, agent registrations, and registration secrets                                                                                |
| [`credentials`](packages/credentials/README.md)         | S2, S3, S4                   | An environment's credentials, minted and verified with its own key ring; the revocation read and its cache                                                                      |
| [`attribution`](packages/attribution/README.md)         | S2, S3, S4                   | Attribution records: one per state-changing operation, in that operation's transaction                                                                                          |
| `agent-identity`                                        | S3                           | Verifies an agent's registration secret                                                                                                                                         |
| [`envelope`](packages/envelope/README.md)               | S2, S4 (through `authority`) | The envelope perimeter: validation, the seal, and the seal key ring                                                                                                             |
| [`authority`](packages/authority/README.md)             | S2, S4                       | Effective authority and origin, computed in one place; the envelope admission entry point                                                                                       |
| [`policy-decision`](packages/policy-decision/README.md) | S2, S4                       | The policy-decision seam's default implementation: literal containment, deny by default                                                                                         |
| [`jcs`](packages/jcs/README.md)                         | S2, S4                       | RFC 8785 canonical JSON, the one implementation in the repository                                                                                                               |

## Documentation map

**Using the platform**

- [The wire contract](contract/README.md), and its [conventions](contract/conventions/README.md):
  [credentials](contract/conventions/credentials.md), [the envelope](contract/conventions/envelope.md),
  [errors](contract/conventions/errors.md), [identifiers](contract/conventions/identifiers.md),
  [versioning](contract/conventions/versioning.md), and the [pre-release policy](contract/conventions/pre-release.md)
- [The handover to soorma-sdk](aidlc-docs/platform/m1-walking-skeleton/construction/build-and-test/soorma-sdk-handover.md):
  everything an agent-side client must do, collected in one place. Read it before writing a client
  in any language
- Each service's README: [S1](services/org-gateway/README.md), [S2](services/control-gateway/README.md),
  [S3](services/data-gateway/README.md), [S4](services/event-ingest/README.md)

**How M1 was designed and verified**

M1 was built with the AI-DLC workflow, and its records are in
[`aidlc-docs/platform/m1-walking-skeleton/`](aidlc-docs/platform/m1-walking-skeleton/):

- [Requirements](aidlc-docs/platform/m1-walking-skeleton/inception/requirements/requirements.md)
  and [user stories](aidlc-docs/platform/m1-walking-skeleton/inception/user-stories/)
- Application design: [components](aidlc-docs/platform/m1-walking-skeleton/inception/application-design/components.md),
  [services](aidlc-docs/platform/m1-walking-skeleton/inception/application-design/services.md),
  and the [units of work](aidlc-docs/platform/m1-walking-skeleton/inception/application-design/unit-of-work.md)
  the build was split into (U1 to U7)
- Per unit, in [`construction/`](aidlc-docs/platform/m1-walking-skeleton/construction/): functional
  design (business rules, domain entities), NFR requirements and design, infrastructure design,
  and a code summary. [`shared-infrastructure.md`](aidlc-docs/platform/m1-walking-skeleton/construction/shared-infrastructure.md)
  describes the local stack as a whole
- [Build and Test summary](aidlc-docs/platform/m1-walking-skeleton/construction/build-and-test/build-and-test-summary.md):
  what was proven and how, the latency figures, the accepted residuals, and the open
  specification questions

**Contributing**

- [`CONTRIBUTING.md`](CONTRIBUTING.md): the open-core line, and how changes are made
- [Adding an operation to the contract](contract/conventions/adding-an-operation.md)
- [`DEPENDENCIES.md`](DEPENDENCIES.md): the dependency policy

## What is not built yet

M1 is a walking skeleton: the thinnest end-to-end path, built to the specification's full
standard, with everything outside it absent rather than simplified.

- **Events are live only.** Nothing is stored, replayed, ordered, or acknowledged, and there are
  no topics: every subscriber in an environment receives everything published in it. Delivery
  guarantees await the Event plane's specification
- **One human.** The configured first Admin is the only principal. Registering further humans,
  delegation, and their lifecycle come later
- **No revocation writer.** Every request checks revocation, but nothing can revoke yet: tests
  seed it
- **No rotation or retirement** of registration secrets, and no removal of registrations
- **A local stack only.** No hosted deployment, no centralized logging, and nothing evaluates the
  alert rules. One S4 runs per environment, so throughput across instances is not demonstrated
- **Registry & Schema, Memory, Access Policy beyond the minimal model, Observability, Eval, and
  Workflow** are not started

Several specification questions found during the build are open with the product team, each
worked around and recorded. The
[Build and Test summary](aidlc-docs/platform/m1-walking-skeleton/construction/build-and-test/build-and-test-summary.md#open-obligations-from-aidlc-statemd)
lists them, and what was built in the meantime.

## Licence

**Source-available, not open source.** `soorma-core` is licensed under
[FSL-1.1-ALv2](LICENSE): you may do anything with it except offer a commercial product or service
that competes with soorma.ai. Internal use at any scale, research, and education are all
permitted.

**Each release becomes Apache 2.0 two years after it ships**, automatically, and not revocably by
soorma.ai. The harness SDKs, the seam interfaces, and the contract definitions are Apache 2.0 from
the start and permanently.

[`LICENSE`](LICENSE) is authoritative; the above is a summary.

## Background

This repository previously held an MIT-licensed implementation (477 commits and 17 releases
between December 2025 and April 2026), built to explore a distributed-cognition architecture. It
did that successfully, but it was not built to be an enterprise platform, and refactoring it
toward an architecture it was never shaped for would have cost more than starting again. It is
retired rather than evolved, and its full history is preserved intact in an archived repository.
**Nothing here is a continuation of that code.** The distributed-cognition thinking survives the
reset; the implementation does not. The repository was reset on 10 September 2026, and design
precedes code here.

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md). Contributions require a signed Contributor License
Agreement: [`CLA.md`](CLA.md) for individuals, [`CCLA.md`](CCLA.md) for organizations.

For anything security-sensitive, email founders@soorma.ai rather than opening a public issue.
