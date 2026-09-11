# Contributing to Soorma Core

Thanks for your interest in the project. `soorma-core` is the open-core
substrate of the soorma.ai platform: the shared server-side planes that agents
run against. It is source-available under
[FSL-1.1-ALv2](LICENSE), with each release converting to Apache 2.0 two years
after it ships. The client harness SDKs ship separately, under Apache 2.0.

**Before anything else:** this repository is design-first and currently empty.
Code lands against a settled plane design, not ahead of one. Until the first
plane is designed and built, the most useful contributions are questions and
design discussion in issues rather than pull requests.

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

The CLA lets the project license future versions under different terms. It does
**not** let us withdraw your contribution from the licence it was submitted
under: work contributed while `soorma-core` is under FSL-1.1-ALv2 stays
available under FSL-1.1-ALv2 permanently, including that licence's automatic
conversion to Apache 2.0. See [`CLA.md`](CLA.md) for the reasoning.

### Third-party material

If a contribution contains anything you did not write yourself — vendored code,
a snippet from another project, generated output carrying its own terms — say so
in the pull request description and identify the source and its licence, and
mark it in the source file itself.

Material under terms that cannot be redistributed under this project's outbound
licensing cannot be accepted. Note that the bar here is **stricter than a
permissive project's**: because `soorma-core` is source-available rather than
open source, some material that would be unproblematic in an MIT or Apache
project cannot be taken in — copyleft code in particular. If you are unsure
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
retention policy, and multi-tenant operation.

**This matters more than it might appear, and the licence does not soften it.**
A core assignment is one-way: tenants build against what core provides, and it
cannot later be withdrawn from them whatever the licence says. The source-available
licence restricts what others may *sell*; it does nothing to make a placement
decision reversible. If you are planning something substantial near this
boundary, please open an issue to discuss placement before writing code — it may
well belong here, but that is worth settling first.

Two related conventions:

- Where the platform must defer a decision it cannot make alone — whether a
  principal may act, whether a promotion is approved, how an identity resolves —
  core defines the interface and ships a simple working default. **Seam
  interfaces and the machine-readable contract definitions are Apache 2.0 and
  permanent**, so anyone may build an implementation against them. Whether a
  particular commercial offering built behind a seam is a Competing Use is a
  question for the licence text, not for this file.
- Event schemas and contracts stay maximally permissive, because
  interoperability depends on them.

## Getting set up

There is nothing to set up yet. Developer setup, architecture, and pattern
documentation arrive alongside the first plane implementation; this section will
point at them when they exist.

In the meantime, open an issue. Design questions are more useful right now than
anything else.

## Making a change

1. **Open an issue first** for anything beyond a small fix — particularly
   anything touching the open-core boundary above, event schemas, or identity.
2. **Branch from `dev`.** Pull requests target `dev`, not `main`.
3. **Include tests.** New behaviour needs coverage; changed behaviour needs its
   tests updated.
4. **Keep event and schema changes backward compatible**, or state the migration
   explicitly in the pull request. In an event-driven system the schema is the
   API, and a silent break surfaces in someone else's agent. A deployed SDK
   cannot be force-upgraded, because tenants host their own agent compute.
5. **Update the docs** that your change makes wrong.

## Reporting bugs

Open an issue with the version, what you expected, what happened, and the
smallest reproduction you can manage. For anything security-sensitive, do not
open a public issue — email founders@soorma.ai instead.
