# Specification Gaps: U4 `env-human-access`

Gaps found while building U4 (soorma-core#7), classified with `prd-gap-classification.md`.
The register of every gap in this initiative is in `aidlc-state.md`, *PRD Specification
Gaps*. Intake-time gaps are in `inception/prd-intake/specification-gaps.md`.

| ID | Status | Raised against | Resolved by | Issue |
|---|---|---|---|---|
| [GAP-EHA-001](#gap-eha-001-whether-ending-a-sign-in-refuses-the-environment-credentials-issued-from-it) | **Resolved — clarified, no PRD change** (R2, renewal only) | ID @ `prd-identity-v1.0` | The user's decision, 2026-11-11 (Functional Design plan Q1 D) | — (not raised) |

---

## GAP-EHA-001: Whether ending a sign-in refuses the environment credentials issued from it

**Raised**: 2026-11-11T03:44:48Z
**Stage**: Functional Design, U4 `env-human-access` (plan Q1). Carried from U2's Functional
Design as forward obligation 1 (soorma-core#7), and found at U4's L1 Domain Coverage Gate's
first pass
**Raised against**: ID, soorma-prd/aiprd-docs/identity/requirements/prd.md @ `prd-identity-v1.0`
**PRD section**: ID FR-010; ID FR-003; ID FR-011; ID §7a (*Human Environment Credential*,
*Organization Sign-In*); ID §8b, the human-credential table
**Owner**: identity
**Unit**: U4 (issuance, renewal, and O3 for the environment credential at S2)
**Issue**: none. Resolved here under prd-gap-classification.md Step 3 option B (plan option D)
**Resolved by**: the user's decision, 2026-11-11T03:59:19Z, recorded verbatim in `audit.md`
(*Functional Design: answers (env-human-access)*)

### What the build needs

H signs in, obtains a credential for E from that sign-in, then ends the sign-in at S1 (the
logout, ID FR-011). H then presents the environment credential at E before it expires. E's
perimeter must either refuse it at once (**R1, cascade**) or accept it until its own expiry,
while refusing any renewal or new issuance from the ended sign-in (**R2, renewal only**). The
answer decides what a logout stops, and whether E consults the organization level on every
request.

### What the PRD says

- **FR-010**: "Short-lived and renewable; **renewal** never widens authority and **never
  outlives** revocation, **its sign-in**, or the principal's `active` state". The clause's
  subject is renewal
- **§7a**: the Human Environment Credential records *issued-from (the sign-in)*; its states are
  "issued → expired / revoked". The Organization Sign-In's are "`live → ended`"
- **§8b**, the human-credential table: for the environment credential, "O1–O3 apply; O3 also
  refuses once the principal is suspended or deactivated". No sign-in condition
- **FR-003**: deactivation "ends the sign-in, revokes every environment credential" and
  delegation credentials, listed as **separate** effects
- **FR-011**: a human may end "their own sign-in **or** environment credential": **two acts**

### Why it was classified as specification

A credential-lifecycle rule with an unspecified case: FR-010's clause can be read as bounding
the credential's whole life, or only its renewal. The answer decides what SECURITY-12's
"invalidated on logout" means for a human in an environment.

### Options considered

- **R1, cascade**: a credential whose sign-in has ended is refused on its next use. Every S2
  operation presenting an environment credential would call `signInStatus`
- **R2, renewal only**: an ended sign-in bars renewal and any new issuance; the credential
  lives to its own expiry, never later than its sign-in's; a full logout is ending both

### Resolution

**R2**, by the user's decision. **The PRD supports only R2**, because R1 contradicts it:

| Citation | What it says | Why R1 contradicts it |
|---|---|---|
| ID **FR-009** | The organization level "sits outside every environment, and **is on no per-request path**" | R1 calls `signInStatus` on every S2 request |
| ID **§9** *Failure Modes*, row *Organization level unavailable* | "**Off the per-request path**, but the source of freshness" | As above |
| ID **§10** *NFR Profile*, row *The organization level* | "Its outage stops **new sign-ins and organization operations** at once" | Under R1, its outage also stops every control operation in E |
| ID **§18** *Glossary*, *Organization level* | "Where organization-scoped human records and material live, outside every environment, **on no per-request path**" | As FR-009 |
| U2 **BR-INT-08** (`construction/org-identity/functional-design/business-rules.md`) | "**None of these is on a per-request path.**" | The plan's note that BR-INT-08 allowed R1 misread it |

Read with **FR-003** and **FR-011** (two separate acts), the build is:

1. **The organization level is consulted at issuance and renewal only** (`signInStatus`)
2. **An ended sign-in bars renewal and any new issuance**
3. **The credential lives to its own expiry**, capped by its sign-in's current expiry (D-EHA-02,
   U2 amendment A7)
4. **A full logout is ending both**, per FR-011

**SECURITY-12's reading** (the user's): **ending the environment credential is its own
logout.** Ending the sign-in ends the session at the organization level and bars renewal and
new credentials; ending the environment credential ends the session in E.

**Divergence from the PRD of record**: none known. The PRD is not amended. If the product team
reads FR-010 as R1, the build diverges at this point. Recorded in
`functional-design/business-rules.md` (D-EHA-01) and in the L1 matrix (L1-05, L1-09).

**Status**: Resolved — clarified, no PRD change
