# CLA adoption notes

Maintainer's record of how [`CLA.md`](../CLA.md) and [`CCLA.md`](../CCLA.md) were
adapted from the [Project Harmony](https://www.harmonyagreements.org/) templates.
Not part of either agreement; kept so the reasoning survives rather than being
re-derived later.

Contributor-facing rationale — why a CLA at all, and what the outbound licence
clause does and does not permit — lives in `CLA.md` itself under "About this
agreement".

## Individual agreement (`CLA.md`)

### Choices made when adapting the template

| Template field or option | Choice |
| :--- | :--- |
| `[PROJECT_NAME]` | Split in two: the **project** is named as "the Soorma Core project", and the grantee is **Amit Bhadoria** as a natural person. See "Who the grantee is" below. |
| `[SUBMISSION_INSTRUCTIONS]` | `CONTRIBUTING.md`, which describes the pull-request comment flow. |
| `[NONOWNER_INSTRUCTIONS]` | `CONTRIBUTING.md` § Third-party material. |
| §2.2 `[or Your Affiliates]` | **Removed.** Affiliate patent grants belong in the entity agreement; the bracketed phrase is not meaningful for an individual. |
| §2.3 Outbound License | **Option Five selected**, Options One to Four deleted. This is the only option permitting proprietary and source-available outbound licensing, and is the reason for adopting a CLA at all. |
| Media licence sentence | **Omitted.** It grants the additional ability to use different licences for non-software portions; Option Five already permits any licence for the whole Contribution, so the sentence adds nothing. |
| §6.1 `[JURISDICTION]` | **The State of California, United States of America.** Harmony has no forum-selection clause; counsel may wish to add one naming Santa Clara County. |
| Signature blocks | Replaced with the electronic signing method used by the CLA workflow. |
| Harmony attribution | Retained, as required by CC BY 3.0. |

### Who the grantee is

The project is maintained by an individual, and there is no incorporated entity.
Only a legal person — natural or juridical — can receive a copyright or patent
licence, so the grantee is **Amit Bhadoria** as a natural person. An individual
can hold these rights and sublicense them exactly as a company could, so nothing
about the licensing strategy changes.

Note the deliberate separation: "Soorma Core" names the **project**, while the
grant runs to a **person**. Harmony's template conflates the two, which is
harmless when a company runs a project but wrong here. No trading name is
claimed or implied by this Agreement, and none is needed: naming a project is
not conducting business under that name.

**On incorporating later.** Section 6.3 already permits assignment, provided the
assignee agrees in writing to be bound. Rights received under this Agreement can
therefore transfer to a company if one is ever formed, without asking any
contributor to re-sign — usually as part of the founder IP assignment executed at
incorporation. It must actually be done rather than assumed, but nothing needs
doing now.

**One related loose end outside this document:** `LICENSE` reads
"Copyright (c) 2025 Soorma AI", which names no legal person. The copyright is not
endangered — it arises on authorship — but the notice should name the actual
holder.

### Status

Reviewed and approved by the maintainer on 6 September 2026, and in effect.
Independent legal review was considered and deliberately not sought: it is not a
condition of validity, the template is adopted substantially unmodified, and the
point at which advice would matter most is if the relicensing option is ever
exercised.

Settled: governing law (California), grantee (Amit Bhadoria as an individual),
the corporate counterpart ([`CCLA.md`](CCLA.md)), and the signing
workflow (enabled).

Optional, if ever revisited: Harmony omits a forum-selection clause, so venue is
unspecified; and comment-based assent has not been tested against California
law.

## Entity agreement (`CCLA.md`)

### Choices made when adapting the template

| Template field or option | Choice |
| :--- | :--- |
| `[PROJECT_NAME]` | Project named as "the Soorma Core project"; grantee is **Amit Bhadoria** as a natural person. See [`CLA.md`](../CLA.md) adoption notes. |
| `[SUBMISSION_INSTRUCTIONS]` | Email to founders@soorma.ai. **Unlike the individual agreement, this cannot be signed by pull-request comment** — it requires signature by someone authorised to bind the company. |
| `[NONOWNER_INSTRUCTIONS]` | `CONTRIBUTING.md` § Third-party material. |
| §2.2 `[or Your Affiliates]` | **Retained**, brackets removed. Affiliate patent coverage is the substantive reason an entity agreement exists, and this is the one place it differs deliberately from the individual agreement, where the phrase was removed. |
| §2.3 Outbound License | **Option Five selected**, Options One to Four deleted — same choice as the individual agreement, and for the same reason. |
| Media licence sentence | **Omitted**, as in the individual agreement; Option Five already permits any licence for the whole Contribution. |
| §6.1 `[JURISDICTION]` | **The State of California, United States of America**, matching the individual agreement. |
| Signature blocks | Kept, reformatted as tables, with Entity and Date rows added. Both parties sign; the template's Title field is retained because the signatory must be authorised to bind the company. |
| Schedule A | **Added — not part of the Harmony template.** See below. |
| Harmony attribution | Retained, as required by CC BY 3.0. |

### Why Schedule A was added

Harmony's entity template does not say *which people's* commits are covered by a
company's signature, but the CLA tooling has to answer exactly that: when a pull
request arrives from an individual, the check must determine whether they are
covered by their employer's agreement. Without a maintained list there is no
link between a GitHub account and the entity that signed.

Schedule A is therefore an addition rather than an adaptation, and counsel should
confirm the wording. Operationally, names on it are added to the `allowlist` in
`.github/workflows/cla.yml`, or recorded in the signature file, so the bot does
not ask employees to sign individually for work their employer has already
covered.

### Known friction, accepted

Some corporate legal departments decline to contract with a natural person and
will want an incorporated counterparty. Company contributions are welcome and
this agreement is live, but that objection is not a reason to incorporate: where
it arises, the contribution is simply forgone.

### Outstanding before first use

1. **Our address**, supplied when a copy is countersigned.
2. **A countersigning process** — who signs on Our behalf, and where executed
   copies are retained. This is manual, with no tooling behind it, so it needs
   an owner.
