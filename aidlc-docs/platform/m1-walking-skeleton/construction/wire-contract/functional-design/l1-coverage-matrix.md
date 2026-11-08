# L1 Coverage Matrix: U1 `wire-contract`

**Sources** (registered in `aidlc-state.md` `## PRD Intake`, each read at its tag):
- PF: soorma-prd/aiprd-docs/platform-foundations/requirements/prd.md @ `prd-platform-foundations-v1.3`
- ID: soorma-prd/aiprd-docs/identity/requirements/prd.md @ `prd-identity-v1.0`

**Status values**: `Covered` (design traced; implementation and verification targets set) ·
`N/A` (with a reason) · `Missing` (blocking). Code Generation moves rows to `Implemented`;
Build and Test moves them to `Verified`.

**Verification targets**: `TC-WC-001` to `011` are the inception specs. Rows marked
*enrichment* get a new test case, `TC-WC-012` onwards, at the QA construction enrichment
after the last U1 design stage. Rows owned by a later unit are verified there, and listed
here so the trace is unbroken.

---

## Applicable to U1

| # | L1 requirement | Design coverage | Implementation target | Verification target | Status |
|---|---|---|---|---|---|
| L1-01 | PF FR-001: seven envelope fields on every event and agent-originated call; **none on a direct human operation** | BR-ENV-01; BR-OP | `contract/envelope.schema.json`; `contract/conventions/` (envelope-bearing operations) | TC-WC-001, TC-WC-005, TC-WC-006 | Covered |
| L1-02 | PF FR-002: stamped/asserted partition; a draft with a stamped field is **rejected, not overwritten**; never usable to act | BR-DR-01, 02, 04, 10 (stamped takes precedence over unknown); BR-FC (the seal gives no authority) | Draft definition in `envelope.schema.json` (closed; each stamped field forbidden by name) | TC-WC-007; *enrichment*: a draft with a stamped and an unknown field gives `stamped_field_set`; U3 `validateDraft` tests; *done when* 7 e2e (U7) | Covered |
| L1-03 | PF FR-003: one envelope definition across every organization, project, and environment | BR-DL-02; business-logic-model §3 | One `envelope.schema.json`, referenced by `$ref` everywhere | TC-WC-009 | Covered |
| L1-04 | PF FR-004 and PF §7b *Compatibility Policy*: change classification; a breaking change needs a new envelope version (transition machinery out of M1) | BR-ENV-07; BR-VER-05, 06; D-WC-03 | `contract/conventions/` (versioning and compatibility); compatibility test | *enrichment*: a previous-version fixture validates against the current schema | Covered |
| L1-05 | PF FR-005 (a): unknown fields preserved and forwarded | BR-ENV-05; BR-DR-08; BR-FC-04 | Envelope schema open at every level; `inbound.envelope` open | TC-WC-008; *enrichment*: unknown field inside `inbound` accepted; U3 test that it is carried into the stamped envelope | Covered |
| L1-06 | PF FR-005 (b): an unknown enumerated value is not fatal | BR-ENV-06; BR-LG-06 | `originMode` an open string; generated union with "any string" | *enrichment*: an envelope with an unknown `originMode` validates | Covered |
| L1-07 | PF FR-006: full chain, ordered, most recent last, minimum 1, perimeter-appended, `maxChainDepth` rejects | BR-ENV-04; D-WC-05 (32); BR-FC-04; BR-ENV-10 (the envelope bound, `envelope_too_large`) | `actorChain` `minItems` 1, `maxItems` 32; conventions constants | *enrichment*: 0 and 33 entries fail, 32 passes; U3 append test; U3 `envelope_too_large` test | Covered |
| L1-08 | PF §7b *Envelope Fields*: requiredness and setter per field; `delegatingPrincipal` and `reBroadening` conditional | BR-ENV-01 to 03; domain-entities *Envelope* | Envelope schema, with the conditional rules | TC-WC-001, TC-WC-006; *enrichment*: `delegated` without `delegatingPrincipal` fails | Covered |
| L1-09 | PF §7b: the draft declares the **client contract version**, distinct from the envelope version | BR-DR-04, 05; BR-VER-02 | Draft definition | TC-WC-010 | Covered |
| L1-10 | PF §7b *Recoverability*: scope, actor, chain, and origin from the envelope at 0 hops; sponsorship in 2, not on the envelope | Scope composed (D-WC-04); `actorChain[i].agent`; BR-ENV-09; BR-FC-01 (a forwarded chain prefix cannot be invented or altered; delivery and recency are not proven, an accepted residual) | Envelope schema | U7 *done when* 4 e2e; U3 reconstruction test (I4) | Covered |
| L1-11 | PF §11 *What the SDK may not populate*: stamped fields rejected; `envelopeVersion` rejected, client contract version expected | BR-DR-02, 04 | Draft definition | TC-WC-007 | Covered |
| L1-12 | PF §11 *Forward inbound context*: origin from forwarded context, chain appended, `maxChainDepth`, O12 for omission | BR-DR-07, 08; BR-FC-01 to 05; D-WC-06 | `inbound` definition; `Delivery.seal` | *enrichment*: `inbound` shape; U3 seal-verification tests; U7 US-09 e2e | Covered |
| L1-13 | PF §14 *Harness Surface Register*: every client contract version ever accepted is accepted until a published window; the chain may gain fields but not change order or minimum length | BR-VER-03; BR-ENV-05; business-logic-model §4 | Conventions (versioning); actor reference open | *enrichment*: an unaccepted version gives `unsupported_contract_version` (U3, U6) | Covered |
| L1-14 | PF §17 *Envelope*: assertions, not proof; consumers never treat contents as self-authenticating | BR-FC-06; D-WC-06 | Conventions statement | Review at Code Generation | Covered |
| L1-15 | PF §17 *Namespacing Rules*: identifiers unique within an environment, composed with scope, never allocated; environment identity configured | D-WC-04; BR-ID-01 to 03, 07, 11 | `scope` object; identifier patterns on request inputs only; plain strings where received | *enrichment*: identifier pattern and length tests; the envelope schema has no identifier pattern | Covered |
| L1-16 | PF §17 *Compatibility Rules*: additive is compatible; the two consumer obligations | BR-VER-05; BR-ENV-05, 06 | Conventions | As L1-04 to L1-06 | Covered |
| L1-17 | PF §22: the envelope's machine-readable definition, and the contract definitions, are Apache 2.0 | BR-LG-01, 02 | `contract/LICENSE`; SPDX identifiers | TC-WC-011 | Covered |
| L1-18 | PF FR-023: a raw caller who never links the SDK reaches identical enforcement | BR-CR (plain HTTP bearer); BR-FC-06 (the seal is forwarded opaquely); BR-OP | Every rule stated as perimeter-enforced; no SDK-only field | e2e raw calls (U5, U6, U7) | Covered |
| L1-19 | ID §7b *Envelope Fields*: **no new envelope field**; the delegating principal is an opaque organization-scoped identifier, never proof | D-WC-06 (the seal sits beside the envelope); domain-entities *Delegating Principal Reference* | Envelope schema (seven fields) | TC-WC-001; *enrichment*: the envelope schema has seven defined properties | Covered |
| L1-20 | ID §7b obligations: an environment credential only in its environment; a sign-in only at the organization level or issuance; a delegation credential only beside its agent's; a human's credential never beside an agent's | BR-CR-01 to 04, 06, 08 | Security schemes; typed prefixes; reserved `Soorma-Delegation` | Presenter-matrix tests in U2, U4, U6, U7 | Covered |
| L1-21 | ID §7b *Compatibility Policy*: a new material class or asserted attribute is compatible; changing what a credential binds to is breaking | BR-VER-05 | Conventions | Review at Code Generation | Covered |
| L1-22 | ID §14: delegation-credential presentation is additive only | BR-CR-06; BR-PR-06 | Reserved header and prefix | U7: the header is refused in M1 | Covered |
| L1-23 | ID §17 *Credentials* and *Namespacing Rules*: human identifiers unique within the organization; credential identifiers composed with the environment | BR-ID-05, 07, 12 (ASCII-only in M1, a recorded delivery limit); BR-CR-05 (RFC 6750 `b64token`); domain-entities *Credential Presentation* | Identifier patterns; `delegatingPrincipal` `{ organization, principal }` | *enrichment*: human identifier pattern tests | Covered |
| L1-24 | ID FR-022: a direct human operation carries no envelope | BR-OP | Conventions table | TC-WC-005 | Covered |
| L1-25 | GAP-INT-008 work-around: bootstrap and renewal carry no envelope | BR-OP; BR-PR-03 | Conventions | TC-WC-005 | Covered |
| L1-26 | GAP-INT-003 work-around: pre-release; delivery semantics unspecified | BR-PR-01, 02; BR-DL-05 | Conventions | TC-WC-004 | Covered |
| L1-27 | GAP-INT-007 work-around: origin mode never accepted from a draft | BR-DR-03; BR-PR-05 | Draft definition | TC-WC-007 | Covered |
| L1-28 | GAP-INT-006 work-around: the accepted permission identifiers may widen compatibly | BR-PR-04; BR-ID-06 | Conventions; permission pattern | Review at Code Generation; U4 and U5 test the accepted set | Covered |
| L1-29 | M1-TECH-05: W3C Trace Context, well-formedness only | BR-TC-01 to 04 | `traceContext` definition | *enrichment*: valid and invalid `traceparent` cases | Covered |
| L1-30 | PF FR-012, PF §17 *Revocation Behaviour*: past the bound with state unreadable, deny | BR-ERR (`unavailable`, fail closed) | Problem codes in the conventions | U6 and U7 fail-closed tests | Covered |
| L1-31 | PF FR-027, ID FR-008: abuse-bounded unauthenticated surfaces | BR-ERR (`too_many_attempts`); BR-ERR-04 | Problem codes in the conventions | U2 and U6 bound tests | Covered |
| L1-32 | M1-TECH-02: language-neutral schema; types generated, never hand-written or shared by hand | BR-LG-03 to 07 | `contract/generated/`; build check | TC-WC-003 | Covered |

## Not Applicable to U1

| L1 source | Reason |
|---|---|
| PF §6; ID §6 *Tenancy and Isolation* | Records and deployments, owned by the surface units. U1 contributes only the `scope` shape (L1-15) |
| PF §7a; ID §7a *Platform-Owned Records* | Stored records, owned by U2, U4, U5, and U6. The contract carries none of their internals |
| PF §8a; ID §8a *Operations* | Each operation and its authority is added by its surface unit |
| PF §8b *Evaluation Mechanism* (intersection, sponsorship, re-broadening composition) | Computed by U3. U1 only defines the record shapes (L1-08, L1-12) |
| PF §9, §10; ID §9, §10 *Faces* | U1 has no face. Each surface unit carries its face's NFR profile |
| PF FR-025 attribution content | Recorded by P7 (U4 onwards). The contract has no attribution read surface in M1 |

## Summary

| Covered | N/A | Missing |
|---|---|---|
| 32 | 6 source groups | **0** |
