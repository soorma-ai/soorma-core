# Specification Gaps: U3 `authority-evaluation`

Gaps found while building U3 (soorma-core#6), classified with `prd-gap-classification.md`.
The register of every gap in this initiative is in `aidlc-state.md`, *PRD Specification
Gaps*. Intake-time gaps are in `inception/prd-intake/specification-gaps.md`.

| ID | Status | Raised against | Resolved by | Issue |
|---|---|---|---|---|
| [GAP-AE-001](#gap-ae-001-origin-for-a-forwarded-autonomous-envelope-when-the-presenter-has-not-declared-autonomy) | **Open**; worked around in M1 (deny) | PF @ `prd-platform-foundations-v1.3` | — | (pending; opened after this entry is committed) |

---

## GAP-AE-001: Origin for a forwarded autonomous envelope when the presenter has not declared autonomy

**Raised**: 2026-11-10T06:40:00Z
**Stage**: Functional Design, U3 `authority-evaluation` (plan Q1; found at the L1 Domain
Coverage Gate's first pass, 2026-11-09)
**Raised against**: PF, soorma-prd/aiprd-docs/platform-foundations/requirements/prd.md @ `prd-platform-foundations-v1.3`
**PRD section**: PF §8b *Perimeter obligations* (O12) and the paragraph *O12 closes what O6
cannot see*; PF FR-015; PF §8b *Origin stamping*; PF §8b *Declared autonomy against
forwarded context*; PF §11 *Harness Surface*, row *Forward inbound context*. Also PF §9
*Failure Modes* and PF §17 *Policy Grammar and Authority Evaluation*, which repeat FR-015's
wording. All present verbatim since `prd-platform-foundations-v1.0`
**Owner**: platform-foundations
**Unit**: U3 (origin resolution); U7 (publish and subscribe at S4, which call U3)
**Issue**: (pending; opened after this entry is committed)
**Resolved by**: —

### What the build needs

An agent C whose registration does **not** declare autonomy is triggered by an event from
agent A. A declared autonomy, so A's envelope has origin `autonomous`. C publishes, and
forwards A's sealed envelope as inbound context. The perimeter must either **allow** C
(propagating `autonomous`, effective authority `standing(C) ∩ standing(A)`) or **deny** it
(`forbidden`, under O12). U3's origin resolution needs one answer, and the answer is
observable at the edge.

### What the PRD says

- **O12** (§8b *Perimeter obligations*): "**Autonomous origin is denied unless the
  presenting credential's registration declares autonomy.** Applies to authority-bearing
  requests under O8; **not** to the bootstrap exchange or renewal, where no agent has
  inbound context". As written, it applies to every authority-bearing request whose origin
  is `autonomous`, propagated or not. **C is denied**
- **The paragraph after O1 to O12**: "O6 rejects an agent that *asserts* autonomy. It
  cannot detect one that forwards nothing … O6 governs a claim; **O12 governs an
  absence**". This places O12's purpose in the no-context case
- **FR-015**: "Origin is stamped by the platform wherever it is derivable — `delegated` from
  an authenticated caller's credential, or **propagated unchanged** from an inbound
  envelope … **With no forwarded context**, an agent whose registration does **not**
  declare autonomy is **denied**; one that does runs on its standing set". Read this way,
  the denial applies only with no forwarded context. **Nothing denies C**, and its origin
  is `autonomous`, propagated unchanged
- **§8b *Origin stamping***: "Triggered by an inbound event | Propagated **unchanged**; the
  chain grows". The O12 row is "No inbound context, **autonomy not declared** | None —
  denied | O12". It agrees with FR-015
- **§8b *Declared autonomy against forwarded context***: both rows with context forwarded
  give origin **`delegated`**, with effective authority "standing ∩ delegating principal ∩
  chain":

  | Autonomy declared | Context forwarded | Origin | Effective authority |
  |---|---|---|---|
  | No | Yes | `delegated` | standing ∩ delegating principal ∩ chain |
  | Yes | Yes | `delegated` | standing ∩ delegating principal ∩ chain |

  For an **autonomous** inbound envelope, this **contradicts FR-015's "propagated
  unchanged"** and the *Origin stamping* row above: the inbound origin is `autonomous`, and
  no delegating principal exists to stamp or intersect. The table does not cover a
  forwarded autonomous chain except by giving it an origin it does not have
- **§11 *Forward inbound context***: "Omission is not detectable, so it is made harmless
  instead: **with no forwarded context**, an agent that has not declared autonomy is denied
  (O12)". §9 *Failure Modes* ("No forwarded context, autonomy not declared | Denied | O12")
  and §17 ("with no forwarded inbound context, an agent that has not declared autonomy is
  denied") say the same

### Why this is specification, not technology

It is an **authority rule with an unspecified case**, and **PRD sections that cannot all be
satisfied** for it: O12's text denies C; FR-015, §8b *Origin stamping*, §9, §11 and §17
scope the denial to the no-context case and so allow C; the *Declared autonomy against
forwarded context* table assigns an origin (`delegated`) that contradicts FR-015 for this
input. The outcome is observable (allow, or `forbidden`), and tenants will build agents
against it. Two competent engineers would answer differently, and neither answer is free:
one is required, and the PRD does not say which.

### Options considered

1. **Deny: O12 as written.** O12 governs every authority-bearing request whose origin is
   `autonomous`, whether stamped at this hop or propagated. An agent that has not declared
   autonomy acts only in a delegated chain. *Consequences*: under M1, where every chain is
   autonomous (A-5), such an agent cannot act at all. FR-015, §8b *Origin stamping*, §9,
   §11 and §17 need O12's wider scope stated, and the *Declared autonomy against forwarded
   context* table needs a row for a forwarded autonomous chain (origin propagated; denied
   when autonomy is not declared)
2. **Allow: O12 governs an absence.** O12 applies only where no context is forwarded. C
   acts on `standing(C) ∩ standing(A)`, never wider than its own standing set.
   *Consequences*: a genuine sealed envelope can be forwarded by an agent it was not
   delivered to (U1's accepted residual, `construction/wire-contract/functional-design/business-rules.md`
   §14). So C could act autonomously by forwarding **any** sealed autonomous envelope it
   obtains in its environment, and its own declaration would no longer decide whether it
   may act without a delegation. O12's text needs narrowing to "with no forwarded context",
   and the table needs a row for a forwarded autonomous chain (origin propagated; allowed)
3. **Whichever is chosen**, the *Declared autonomy against forwarded context* table's two
   forwarded rows read as written only for a **delegated** inbound chain. Under FR-015 the
   origin is propagated, not set to `delegated`, so the table needs its origin column for
   forwarded rows to read *propagated* (or to split by inbound origin)

**Related**: [soorma-prd#25](https://github.com/soorma-ai/soorma-prd/issues/25) (GAP-INT-007)
concerns the same §8b *Origin stamping* table: who sets origin at an autonomous first hop
with **no** inbound context. This gap is the **forwarded** case. An amendment to the table
can settle both.

### Routing

**Chosen**: A, raise against soorma-prd, with the work-around below (the user,
2026-11-10, plan Q1).

### M1 work-around

M1 builds **option 1, deny**: an `autonomous` origin, stamped or propagated, requires the
presenter's registration to declare autonomy; otherwise the request is `forbidden` (O12),
with the internal reason `o12_undeclared` in the security log only. It is O12's text, it
fails closed, and it matches U1's accepted residual, which already assumes it ("an
`autonomous` origin still requires the presenter's own declaration (O12)"). Moving to
option 2 later **allows** requests M1 refuses, which is additive. Moving from option 2 to
option 1 would refuse requests tenants had relied on. So option 1 is the safe interim, and
it is recorded as a work-around, not as the specified behaviour.

### Blocked

**No *done when* item**, given the work-around: both M1 demo agents declare autonomy (A-5),
and US-09's journey is the same under either reading. It governs U3's origin resolution and
every publish or subscribe at S4 (U7) by an agent that has not declared autonomy and
forwards an autonomous envelope.

**Status**: `Open`. Raised against PF @ `prd-platform-foundations-v1.3`, and worked around in
M1 (deny)
