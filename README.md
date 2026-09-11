# soorma-core

The open-core substrate for governed agentic systems.

> **Nothing is built yet.** This repository was reset on 10 September 2026 and
> starts from an empty tree. Design precedes code here — see
> [Background](#background).

## What this is

soorma.ai is a platform on which developers across organizations build their own
agentic systems. It has two parts:

- **Harness** — the SDK a tenant embeds in each agent. Client-side, in the hot
  path, and advisory: it enforces nothing. Ships separately, under Apache 2.0.
- **Substrate** — this repository. The shared server-side planes that agents run
  against, and where enforcement lives: Event, Registry & Schema, Memory,
  Identity, Access Policy, Observability, Eval, and Workflow.

`soorma-core` is meant to be sufficient on its own for a developer or a small
team working in a single environment. Governing *many people* doing that —
approval routing, separation of duties, retention policy, multi-tenant
operation — belongs to the commercial platform above it.
[`CONTRIBUTING.md`](CONTRIBUTING.md) sets out where the line falls and the rules
that decide it.

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
