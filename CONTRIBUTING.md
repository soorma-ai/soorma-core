# Contributing to Soorma Core

Thanks for your interest in the project. `soorma-core` is the open foundation of
the soorma.ai platform: the client harness SDK that agents embed, and the
server-side planes they run against. It is MIT licensed.

## Before you start

### Contributor License Agreement

All contributors must sign a Contributor License Agreement before their first
contribution can be merged. There are two routes:

- **Contributing on your own behalf** — sign [`CLA.md`](CLA.md). When you open a
  pull request a bot will comment with instructions; signing is a single comment
  on the pull request and is only required once.
- **Contributing on behalf of your employer**, or where your employer holds
  rights in work you do — your company signs [`CCLA.md`](CCLA.md) instead. This
  one cannot be signed by comment: it needs signature by someone authorised to
  bind the company. Email founders@soorma.ai to start that, and list the
  employees who will be contributing so their pull requests are recognised as
  covered.

If you are employed and unsure which applies, check with your employer before
signing the individual agreement — many employment contracts assign copyright in
work related to the employer's business.

The CLA lets the project license future versions under different terms if that
ever becomes necessary. It does not let us withdraw your contribution from the
licence it was submitted under: work contributed while `soorma-core` is MIT
stays available under MIT permanently. There is no present intention to move away
from MIT — see [`CLA.md`](CLA.md) for the reasoning and for the alternative the
project would adopt if that changed.

### Third-party material

If a contribution contains anything you did not write yourself — vendored code,
a snippet from another project, generated output carrying its own terms — say so
in the pull request description and identify the source and its licence, and
mark it in the source file itself.

Material under terms incompatible with MIT cannot be accepted. If you are unsure
whether something qualifies, ask in the pull request rather than omitting it; a
disclosed dependency is a conversation, an undisclosed one is a licensing defect
that is expensive to unwind later.

This is the process referred to by the Contributor License Agreement, which asks
you to confirm you own the copyright in what you submit.

### What belongs in `soorma-core`

The project deliberately draws a line between the open core and the commercial
platform built above it. The rule is:

> **The open core provides the mechanism and the complete record. Multi-actor
> control over that mechanism belongs to the commercial platform.**

In practice, `soorma-core` should be fully functional for an individual
developer or a small team working in a single environment: agents communicating,
memory with curation and promotion, traces, evaluations, workflow state,
identity, and policy. What it does not carry is what an organisation needs to
govern many people doing those things — approval routing, separation of duties,
audit trails, retention policy, and multi-tenant operation.

**This matters more than it might appear.** MIT is irreversible: a governance
capability merged into `soorma-core` cannot later be moved to the commercial
platform. If you are planning something substantial in this area, please open an
issue to discuss placement before writing code — it may belong here, but that is
worth settling first.

Two related conventions:

- Where the platform must defer a decision it cannot make alone — whether a
  principal may act, whether a promotion is approved, how an identity resolves —
  core defines the interface and ships a simple default. Those seams are open
  and anyone may implement against them.
- Event schemas and contracts stay maximally permissive, because
  interoperability depends on them.

## Getting set up

- [`docs/DEVELOPER_GUIDE.md`](docs/DEVELOPER_GUIDE.md) — local environment, running
  services, and the SDK
- [`ARCHITECTURE.md`](ARCHITECTURE.md) — platform services and how they fit together
- [`docs/ARCHITECTURE_PATTERNS.md`](docs/ARCHITECTURE_PATTERNS.md) — agent patterns
  and when to use each
- [`docs/CONTRIBUTING_REFERENCE.md`](docs/CONTRIBUTING_REFERENCE.md) — coding
  conventions and repository detail

## Making a change

1. **Open an issue first** for anything beyond a small fix — particularly
   anything touching the open-core boundary above, event schemas, or identity.
2. **Branch from `dev`.** Pull requests target `dev`, not `main`.
3. **Include tests.** New behaviour needs coverage; changed behaviour needs its
   tests updated.
4. **Keep event and schema changes backward compatible**, or state the migration
   explicitly in the pull request. In an event-driven system the schema is the
   API, and a silent break surfaces in someone else's agent.
5. **Update the docs** that your change makes wrong, including `CHANGELOG.md`.

## Reporting bugs

Open an issue with the version, what you expected, what happened, and the
smallest reproduction you can manage. For anything security-sensitive, do not
open a public issue — email founders@soorma.ai instead.
