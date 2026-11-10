# Business Rules: U3 `authority-evaluation`

**Unit**: U3 `authority-evaluation` (soorma-core#6). Data face, environment level. Modules
only: no edge surface, no deployable
**Built against**: PF @ `prd-platform-foundations-v1.3` (the main source), ID @ `prd-identity-v1.0`
**Decisions from**: the Functional Design plan, Q1 to Q6 and proposals P-01 to P-11, answered
2026-11-10 (recorded verbatim in `audit.md`)
**Entities**: [domain-entities.md](domain-entities.md). **Logic**:
[business-logic-model.md](business-logic-model.md)
**Inherited rules**: U1's envelope, draft, forwarded-context, trace-context, versioning and
error rules (`construction/wire-contract/functional-design/business-rules.md`: BR-ENV, BR-DR,
BR-FC, BR-TC, BR-VER, BR-ERR). U3 implements the ones naming U3. This document adds what U1
left to U3, and does not restate U1's rules except where U3 changes them (amendment A6)
**Specification gaps**: GAP-AE-001 (Open, soorma-prd#30; worked around, D-AE-01). Inherited:
GAP-INT-007 (Open, soorma-prd#25; reject and stamp); GAP-INT-004 (Resolved; built as PF
FR-017 states)

Module names are the Application Design's: P1 `perimeter`, P2 `envelope`, P3 `authority`,
P11 `policy-decision`, and `seams/policy-decision`.

---

## 1. Decisions

| ID | Decision | Source | Class |
|---|---|---|---|
| **D-AE-01** | **An `autonomous` origin, stamped or propagated, requires the presenter's registration to declare autonomy.** An agent that has not declared autonomy and forwards an autonomous envelope is refused `forbidden` (O12 as written). **Work-around for GAP-AE-001** (Open, soorma-prd#30); allowing the case later is additive. Published as pre-release statement 9 (§13) | Q1 A; PF O12 | **Specification gap**, worked around |
| **D-AE-02** | **`seams/policy-decision` has both halves PF §12 states**: `grantedSet(principal, environment)` and `contains(effectiveSet, requiredSet)`. P3 asks the seam for each term's granted set, **composes the effective set in core**, then asks containment. Composition never crosses the seam. P11's default reads grants through a port (`GrantSource`) that U5 (agent standing sets) and U4 (human grants) fill. U3 tests it with an in-memory source. **An upstream agent's term is its standing set**, read now (recorded at Q2; reading it as of its hop cannot differ in M1, where no operation changes a standing set) | Q2 A; PF §12 | Technology |
| **D-AE-03** | **P3 refuses a human-only permission to an agent, whatever its standing set** (defence in depth). The class (`grant:human`, `human:manage`, `agent:delegate`) has **one definition**, exported by `packages/authority`, and used by P3 and by U5's registration check. While U5's check holds, no outcome changes | Q3 A; PF FR-016, §8b; ID FR-013 | Technology |
| **D-AE-04** | **One entry point** for an envelope-bearing request, `createEnvelopeAdmission(dependencies).admit(request)`, in `packages/authority`: S4 builds it once per instance with its dependencies, and calls `admit` per request (*Consistency fix from NFR Design (2026-11-10): formerly `admitEnvelopeRequest`*). It runs check-order steps 5 to 10 in order and returns the stamped, sealed envelope, or the first refusal. U7 calls it once per publish and per subscribe. P2's and P3's functions stay separate and are tested alone, but **the entry point is the only one a surface imports**. The order and the *one place* (I5) are structural | Q4 A; BR-ERR-07 | Technology |
| **D-AE-05** | **The stamped `traceContext` carries the forwarded envelope's unknown trace-context fields.** It is: the forwarded `traceContext`'s fields other than `traceparent` and `tracestate`; plus the draft's `traceparent`; plus the draft's `tracestate` **only if the draft carries one**. A forwarded `traceparent` or `tracestate` is never carried. **U1 amendment A6** (§13) | Q5 A, as corrected by the user; PF FR-005 (a) | Technology |
| **D-AE-06** | **Problem emission moves into P1** (`packages/perimeter`): the code table (status, title), the Problem body, and the response's headers, with U3's codes added. S1 imports it, keeping only a thin Fastify adapter; its own `problems.ts` is removed, with no change in behaviour. P1 also exports **one test assertion** for BR-ERR-08 that every edge runs on every Problem (S1 now; U6 and U7 at S3 and S4) | Q6 A; BR-ERR-08 | Technology |
| D-AE-07 | A verified `inbound` whose `originMode` is not `autonomous` (`delegated`, or a value this version does not know) is refused `forbidden`. It cannot occur in M1: only this environment's perimeter seals, and it stamps only `autonomous`. An unknown value is a denial, never a crash or a malformed-request error (PF FR-005 b) | P-01; O9 | Technology |
| D-AE-08 | `scope` is stamped from the **verified credential's claims**, never from deployment configuration. U3 also checks that it equals this environment's configured scope, and fails closed if not (D-AE-23) | P-02; PF §7b, FR-022, O11 | Technology |
| D-AE-09 | An upstream chain entry whose agent does not resolve in this environment has the **empty set** as its term, so the request is denied. A store failure while reading any term is `unavailable` (fail closed) | P-03; O9; L3 | Technology |
| D-AE-10 | Required authority is a **non-empty set** of permission identifiers; all must be contained. Publish requires `{event:publish}`; subscribe requires `{event:subscribe}`. An empty required set is a programming error, refused `internal_error`, never allowed | P-04; PF §8a, §8b *Exercised* | Technology |
| D-AE-11 | U3 returns **typed refusals**: a contract code and an **internal reason** (§10). The reason goes to the security log only, never into a response | P-05; BR-ERR-01; BR-FC-03; SECURITY-03 | Technology |
| D-AE-12 | **Version on a draft call** (step 5): a body that is not a JSON object is `malformed_request`; a missing or non-string `clientContractVersion` is `unsupported_contract_version`; a `Soorma-Contract-Version` header that differs from the draft's value, or is sent more than once, is `malformed_request` naming the header. Published in `versioning.md` and `errors.md` (§13) | P-06; BR-VER-02 | Technology |
| D-AE-13 | A forwarded chain of 32 entries is `chain_too_deep` (the new chain would be 33), at step 8, before origin and authority | P-07; PF FR-006, O7; BR-ENV-04 | Technology |
| D-AE-14 | Every unknown field in a forwarded envelope is preserved at every level U3 does not replace: the envelope, `scope`, each actor reference, each re-broadening record, `delegatingPrincipal`, and (D-AE-05) `traceContext` | P-08; PF FR-005 (a); BR-DR-08 | Technology |
| D-AE-15 | A forwarded envelope whose `reBroadening` names an index outside its chain, or names one twice, is `invalid_inbound_context` | P-09; BR-ENV-03 | Technology |
| D-AE-16 | L1 to L5 are verified by **table-driven tests** over the minimal model, with no new dependency | P-10; PF FR-019; M1-TECH-04 | Technology |
| D-AE-17 | `traceparent` and `tracestate` are validated as U1's conventions state, including the rules checked in code (version `ff`, all-zero ids, at most 32 list members, key syntax). Values are never interpreted | P-11; BR-TC-01 to 04 | Technology |
| D-AE-18 | **Step 6 precedence**: `stamped_field_set`, then `unknown_field`, then `malformed_request` for every other schema or trace-context failure. The refusal's `errors[]` lists every field failing with the winning code, ordered by pointer | This design; BR-DR-10 | Technology. **Not asked**: flagged for review |
| D-AE-19 | **A forwarded envelope over the envelope bound is `invalid_inbound_context`**, checked first in step 7, before the seal is computed. No genuine seal can cover one (BR-ENV-10), so it is a forwarded-context failure, and checking size first bounds the work | This design; BR-DR-09; SECURITY-05 | Technology. **Not asked**: flagged for review |
| D-AE-20 | **Forwarded re-broadening records never affect evaluation.** They are checked for index validity (D-AE-15) and carried, never read as authority. Re-broadening is local to its hop (PF §8b *Propagation*) | This design; PF FR-017 | Technology |
| D-AE-21 | One `grantedSet` read per **distinct** agent in the forwarded chain. Intersection is idempotent (L2), so a repeated agent, the presenter included, contributes its term once | This design; L2 | Technology |
| D-AE-22 | The envelope bound is measured in **UTF-8 bytes** of the RFC 8785 (JCS) serialization: at most 16384 | This design; BR-DR-09; BR-ENV-10 | Technology |
| D-AE-23 | A credential scope that differs from the configured scope is **`internal_error`**, logged as an invariant breach. It cannot occur after O4 (step 4), so it signals a defect, and a 500 does not misreport it as a client's fault | This design; D-AE-08 | Technology. **Not asked**: flagged for review |
| D-AE-24 | The presenter's registration not found is `forbidden` (reason `presenter_unresolved`); a failure reading it is `unavailable`. Not found cannot occur after step 3, where the credential verified against a live registration | This design; O9 | Technology |
| D-AE-25 | The server's contract version and the accepted set are defined **once, in P1**, beside the Problem table (`unsupported_contract_version` lists them). The entry point receives the accepted set as an input, so P2 and P3 do not depend on P1 | This design; D-AE-06 | Technology |
| D-AE-26 | **The security log** records, for every refusal: the code, the internal reason, the request id, the environment, and the presenter's agent and instance. **Never** the draft body, the seal, the forwarded envelope, or trace-context values | This design; SECURITY-03 | Technology |

---

## 2. Inputs and Ports (BR-IN)

| ID | Rule | Source |
|---|---|---|
| BR-IN-01 | The entry point's `admit(request)` (D-AE-04; *Consistency fix from NFR Design (2026-11-10): formerly `admitEnvelopeRequest`*) runs **only after** the surface has run steps 1 to 4 (body size, credential presentation and kind, verification and expiry, environment and revocation). Those are P1's at S3 and S4 (U6, U7). U3 never re-runs them and never runs without them | BR-ERR-07; O10 |
| BR-IN-02 | Its request inputs are: the parsed body (any JSON value); the `Soorma-Contract-Version` header values (zero or more); the **Checked Agent Context** (scope, agent, instance), from the verified credential; the **required authority**; and the request id | D-AE-04; D-AE-08 |
| BR-IN-03 | Its ports are: the **agent-facts source** (each agent's Registration View and standing set together; U5 fills it from P4 with one query), read once at the start of step 9 through one caching decorator; the **policy decision** (the seam; P11 by default, whose agent `GrantSource` is served from that read, and whose human `GrantSource` U4 fills). *Consistency fix from NFR Design (2026-11-10; the user's agent-facts design)*; the **Sealer** (seal and verify with this environment's sealing material; NFR Design); the **configured scope** (P9); the **accepted contract versions** (P1, D-AE-25); and the **security log** | D-AE-02; D-AE-25 |
| BR-IN-04 | Every input is treated as untrusted except the Checked Agent Context, which P1 produced from a verified credential. The body is validated before any field of it is read, except `clientContractVersion` at step 5 | SECURITY-05; O5 |

## 3. Contract Version on a Draft Call (BR-VR, step 5)

| ID | Rule | Source |
|---|---|---|
| BR-VR-01 | A body that is not a JSON object is `malformed_request`, with `errors[]` pointing at the root (`""`) | D-AE-12 |
| BR-VR-02 | `clientContractVersion` missing, or not a string: `unsupported_contract_version`, listing `supportedVersions`. *Declaring no version is not declaring an accepted one* (U2's rule, now for a draft call) | D-AE-12; BR-VER-04 |
| BR-VR-03 | A string not in the accepted set (`{0.1.0}`): `unsupported_contract_version`. Exact match; no ranges | BR-VER-03 |
| BR-VR-04 | Then the header: `Soorma-Contract-Version` sent more than once, or different from the draft's value, is `malformed_request`, with an `errors[]` entry naming the header. Not sending it is allowed | D-AE-12; BR-VER-02 |
| BR-VR-05 | Step 5 reads **only** `clientContractVersion`. No other body field is read before step 6 | BR-IN-04 |

## 4. Draft Validation (BR-DV, step 6)

| ID | Rule | Source |
|---|---|---|
| BR-DV-01 | The draft is validated against U1's `Draft` schema (`envelope.schema.json`), which includes `inbound.envelope` against the `Envelope` schema (open, so only requiredness and form), then against the rules checked in code (BR-TC; D-AE-17) | BR-DR-01 to 07; BR-TC |
| BR-DV-02 | **Precedence** (D-AE-18): a platform-stamped field at the draft's top level (`envelopeVersion`, `scope`, `originMode`, `delegatingPrincipal`, `actorChain`, `reBroadening`) is `stamped_field_set`, whatever else fails. Otherwise an undefined field at the top level or in the draft's `traceContext` is `unknown_field`. Otherwise any other failure is `malformed_request` | BR-DR-02, 10; D-AE-18 |
| BR-DV-03 | `errors[]` lists every field failing with the winning code, each with its JSON Pointer, ordered by pointer. A trace-context failure points at `/traceContext/traceparent` or `/traceContext/tracestate` | BR-ERR-01 |
| BR-DV-04 | **Origin mode in a draft is `stamped_field_set`**, at every hop, the autonomous first hop included (GAP-INT-007 work-around; BR-DR-03). **A re-broadening record in a draft is `stamped_field_set`** (PF FR-017: "a re-broadening field set by an agent is rejected") | BR-DR-03; PF FR-017; O5, O6 |
| BR-DV-05 | Nothing in a draft is overwritten. A draft that fails is refused; the envelope is never stamped from it | PF FR-002; O5 |

## 5. Forwarded Context (BR-FX, step 7; only when `inbound` is present)

Every failure here is **`invalid_inbound_context`**, one code for every cause (BR-FC-03).
The internal reason says which.

| ID | Rule | Internal reason | Source |
|---|---|---|---|
| BR-FX-01 | `inbound.envelope`'s JCS serialization exceeds 16384 UTF-8 bytes. Checked first, before the seal is computed | `inbound_too_large` | D-AE-19, 22 |
| BR-FX-02 | The seal does not verify over the JCS form of `inbound.envelope`, **as received** (unknown fields included), with this environment's sealing material. A seal from another environment fails here | `seal_failed` | BR-FC-01; D-WC-06 |
| BR-FX-03 | `envelopeVersion` is not `1` | `envelope_version` | BR-FC-03 |
| BR-FX-04 | `scope`'s organization, project, and environment are not all equal to this environment's (exact comparison; unknown fields in `scope` are not compared) | `scope_mismatch` | BR-FC-02; I1 |
| BR-FX-05 | A `reBroadening` record names a `hop` not less than the chain's length, or two records name the same `hop` | `rebroadening_index` | D-AE-15; BR-ENV-03 |
| BR-FX-06 | **A verified forwarded envelope gives no authority.** It contributes terms to the intersection (§8) and a chain prefix; the presenter still acts on its own credential | PF FR-002; BR-FC-06 | — |
| BR-FX-07 | `inbound.envelope` holds a **lone surrogate** in any string, so it has no RFC 8785 (JCS) form. Checked when its JCS form is computed, so before the bound (BR-FX-01) and the seal (BR-FX-02). *Consistency fix from NFR Requirements (2026-11-10; NFR-AE-04)* | `jcs_invalid` | RFC 8785 §3.2 (I-JSON); NFR-AE-04 |

## 6. Chain Depth (BR-CD, step 8)

| ID | Rule | Source |
|---|---|---|
| BR-CD-01 | The new chain's length is the forwarded chain's length plus one, or 1 with no `inbound`. A length over 32 is `chain_too_deep`. The chain is never truncated | D-AE-13; BR-ENV-04; O7 |
| BR-CD-02 | Chain depth is checked before origin and authority, so the loop guard fires without reading any registration or grant | BR-ERR-07 |

## 7. Origin (BR-OR, step 9, first half)

| ID | Situation | Outcome | Internal reason | Source |
|---|---|---|---|---|
| BR-OR-01 | No `inbound`; the presenter's registration declares autonomy | origin `autonomous` | — | PF §8b *Origin stamping*; FR-015 |
| BR-OR-02 | No `inbound`; autonomy **not** declared | `forbidden` | `o12_undeclared` | O12; PF FR-015; BR-FC-05 |
| BR-OR-03 | `inbound` with origin `autonomous`; autonomy declared | origin `autonomous`, **propagated unchanged** | — | PF FR-015; §8b |
| BR-OR-04 | `inbound` with origin `autonomous`; autonomy **not** declared | **`forbidden`** (GAP-AE-001 work-around, D-AE-01) | `o12_undeclared` | O12 as written; GAP-AE-001 |
| BR-OR-05 | `inbound` with origin `delegated`, or a value this version does not know | `forbidden` | `origin_unsupported` | D-AE-07; PF FR-005 b |
| BR-OR-06 | The presenter's registration not found; or the agent-facts read failing | `forbidden`; or `unavailable` | `presenter_unresolved`; `agent_facts_read_failed` (*Consistency fix from NFR Design (2026-11-10; the user's agent-facts design)*) | D-AE-24 |

**Autonomy declared** is the registration's boolean, **default no** (PF §7a). Origin is
never read from the draft (BR-DV-04), and **origin is computed in P3 only** (seam
containment: origin stamping, O12 included, stays in core).

## 8. Authority Evaluation (BR-AU, step 9, second half)

The terms, for a request needing the required set `R`:

| Term | Meaning | Read from |
|---|---|---|
| `S` | The presenter's standing set | `policy.grantedSet(presenter, E)` |
| `D` | The presenter's re-broadening declaration | The Registration View |
| `P` | The delegating principal's set. **In autonomous origin it imposes nothing** (the case table's first column reads *yes*) | None in M1 (BR-OR-05) |
| `U1 … Un` | One per distinct agent in the forwarded chain: its standing set | `policy.grantedSet(agent, E)` (D-AE-02, 21) |

```text
upstream   U  =  U1 ∩ … ∩ Un            (imposes nothing when n = 0)
without       N  =  S ∩ P ∩ U
with          W  =  S ∩ P ∩ (U ∪ D)

allowed       =  R contains no human-only permission, and contains(W, R)
load-bearing  =  allowed, and not contains(N, R)
```

| ID | Rule | Source |
|---|---|---|
| BR-AU-01 | **Effective authority is computed in exactly one place: P3's `evaluateAgent`.** No other module, surface, or seam computes an intersection or a union of permission sets | I5; M1-FR-08; PF §12 *Seam containment* |
| BR-AU-02 | `N` and `W` are composed **in core**. The seam is asked only for granted sets and for containment, never for an effective set (D-AE-02) | PF §12: "decides containment, never composition" |
| BR-AU-03 | **Human-only class** (D-AE-03): if `R` contains `grant:human`, `human:manage`, or `agent:delegate`, the request is `forbidden` (reason `human_only_permission`), before containment is asked. The terms are already read, at the start of step 9 (*Consistency fix from NFR Design (2026-11-10; the user's agent-facts design)*: formerly "before any term is read"). Matched literally, never by pattern | PF §8b; ID FR-013; ID OB-16 |
| BR-AU-04 | **Re-broadening at the declaring hop**: `W = S ∩ P ∩ (U ∪ D)`. It recovers only what **upstream agents** narrowed away, never what `P` lacked, and never more than `S` (the formula intersects with `S` even if `D` were wider, D-AE-03's defence-in-depth reading) | PF FR-017; §8b |
| BR-AU-05 | **Exercised only when load-bearing**: allowed with re-broadening and not without it. Only then is the record stamped (BR-ST-04) | PF §8b *Exercised*, *Record* |
| BR-AU-06 | **Local to its hop**: later hops compute their own `U` from the chain's standing sets, ignoring every re-broadening record (D-AE-20) | PF §8b *Propagation* |
| BR-AU-07 | **First hop**: with no upstream term, `U` imposes nothing, so `W = N = S ∩ P` and re-broadening is never load-bearing | PF §8b case table, row 1 |
| BR-AU-08 | **Deny by default**: an empty or unknown set contains nothing; a principal with no grants in E has the empty set; an unresolved upstream agent has the empty set (D-AE-09) | O9; PF FR-018; L3 |
| BR-AU-09 | **The agent-facts read is all-or-nothing**: a failure is `unavailable` (reason `agent_facts_read_failed`), and nothing from it is used. A failure reading a human's grants (U4) is `unavailable` too. Never allow on a failed read. *Consistency fix from NFR Design (2026-11-10; the user's agent-facts design)* | D-AE-09; fail closed |
| BR-AU-10 | A denial is `forbidden` (reason `authority_denied`, or `upstream_unresolved` when an upstream agent did not resolve). Nothing beyond the code is returned | BR-ERR-01 |

**The case table, checked by a test for every row** (PF §8b; for `p` in `S`; outside `S`
every row denies):

| `p` in `P` | `p` in every upstream term | `p` in `D` | Outcome | Record |
|---|---|---|---|---|
| yes | yes | either | allow, without re-broadening | no |
| yes | no | yes | **allow, by re-broadening** | **yes** |
| yes | no | no | deny | no |
| no | either | either | deny | no |

## 9. Stamping and Sealing (BR-ST, step 10)

| ID | Rule | Source |
|---|---|---|
| BR-ST-01 | **Without `inbound`**: `envelopeVersion` `1`; `scope` = the Checked Agent Context's scope (`organization`, `project`, `environment`); `originMode` `autonomous`; no `delegatingPrincipal`; `actorChain` = `[{ agent, instance }]` for this hop; no `reBroadening`; `traceContext` = the draft's | PF §7b; BR-FC-05; D-AE-08 |
| BR-ST-02 | **With a verified `inbound`**, start from `inbound.envelope` **as received**, every unknown field included (D-AE-14), and set: `envelopeVersion` `1`; `scope` kept (equal to this environment's, with its unknown fields); `originMode` and `delegatingPrincipal` kept, unchanged; `actorChain` = the forwarded entries as received, then `{ agent, instance }` for this hop | BR-FC-04; PF FR-006, FR-015 |
| BR-ST-03 | **`traceContext`** (D-AE-05, amendment A6): the forwarded `traceContext`'s fields other than `traceparent` and `tracestate`, then the draft's `traceparent`, then the draft's `tracestate` only if the draft carries one. A forwarded `tracestate` is never carried when the draft omits one | D-AE-05; PF FR-005 a |
| BR-ST-04 | **`reBroadening`** = the forwarded records as received, then `{ hop: n }` when re-broadening was load-bearing at this hop, where `n` is this hop's zero-based index in the new chain. Absent when there is no record | PF §7b, §8b; BR-ENV-03 |
| BR-ST-05 | This hop's actor reference is `{ agent, instance }` from the Checked Agent Context: the logical agent the credential is bound to, and the instance it asserts. The instance is **recorded, not verified** | PF §7a *Agent Credential*; I10 |
| BR-ST-06 | **The envelope bound**: the new envelope's JCS serialization over 16384 UTF-8 bytes is `envelope_too_large` (reason `envelope_bound`). Nothing is truncated or dropped to fit | BR-ENV-10; D-AE-22 |
| BR-ST-07 | **Sealed**: the seal is computed over the new envelope's JCS form with this environment's sealing material, and returned **beside** the envelope. The algorithm, key identification, and rotation are NFR Design's | BR-ENV-08; D-WC-06 |
| BR-ST-08 | The result is returned to the surface with the outcome: origin, whether re-broadening was load-bearing, and the chain, for U7's attribution record (P7). U3 writes no record | PF FR-025 (U7) |

## 10. Refusals and the Check Order (BR-RF)

The entry point's `admit(request)` returns the **first** refusal, in this order (BR-ERR-07, steps 5 to
10). *Consistency fix from NFR Design (2026-11-10): formerly `admitEnvelopeRequest`*:

| Step | Check | Contract code | Internal reasons |
|---|---|---|---|
| 5 | Contract version | `malformed_request` (body not an object; header), `unsupported_contract_version` | `body_not_object`, `version_missing`, `version_not_accepted`, `version_header_mismatch` |
| 6 | Draft schema; trace context | `stamped_field_set`, `unknown_field`, `malformed_request` | `stamped_field`, `unknown_field`, `schema`, `trace_context` |
| 7 | Forwarded context | `invalid_inbound_context` | `jcs_invalid` (*consistency fix from NFR Requirements*), `inbound_too_large`, `seal_failed`, `envelope_version`, `scope_mismatch`, `rebroadening_index` |
| 8 | Chain depth | `chain_too_deep` | `chain_depth` |
| 9 | Origin, then authority | `forbidden`, `unavailable` | `o12_undeclared`, `origin_unsupported`, `presenter_unresolved`, `human_only_permission`, `upstream_unresolved`, `authority_denied`; `agent_facts_read_failed` |
| 10 | The envelope to be stamped | `envelope_too_large` | `envelope_bound` |
| — | An invariant breach | `internal_error` | `credential_scope_mismatch` (D-AE-23), `empty_required_set` (D-AE-10) |

| ID | Rule | Source |
|---|---|---|
| BR-RF-01 | **Specific for validation, generic for trust.** Steps 5 and 6 name the field or header. Steps 7 and 9 name nothing beyond the code. The internal reason never reaches a response | BR-ERR-01; D-AE-11 |
| BR-RF-02 | Every refusal is written to the security log (D-AE-26) | SECURITY-03 |
| BR-RF-03 | **No refusal code is returned that P1's table does not define.** A test checks every code U3 can return against P1's table | D-AE-06 |

## 11. The Policy-Decision Seam (BR-SEAM)

| ID | Rule | Source |
|---|---|---|
| BR-SEAM-01 | `seams/policy-decision` declares **types only**: `PermissionId`, `PermissionSet`, `PrincipalRef` (an agent or a human principal), `EnvironmentRef` (a scope), and `PolicyDecision` with `grantedSet(principal, environment)` and `contains(effectiveSet, requiredSet)`. Apache 2.0, **unpublished**, and no configuration selects an implementation (M1-FR-13) | D-AE-02; PF §12; M1-FR-13 |
| BR-SEAM-02 | **No seam operation returns an effective set.** `grantedSet` returns one principal's own granted set; `contains` answers yes or no | PF §12 *Seam containment* |
| BR-SEAM-03 | **P11's default**: flat, opaque identifiers with set semantics; **literal** containment (`requiredSet ⊆ effectiveSet`, exact string comparison, no wildcard or hierarchy); **deny by default**; environment-scoped: it answers only for the environment it was built for, and returns the empty set for any other | PF §8b *Core Baseline*; PF §12; ID OB-16 |
| BR-SEAM-04 | P11's `GrantSource` port: **an agent's granted set is its standing set**, served from the request's agent-facts read (*Consistency fix from NFR Design (2026-11-10; the user's agent-facts design)*); **a human's is the union of its grants in E** (U4 fills it, the held set). U3 builds the port and an in-memory source for its tests | D-AE-02; PF §7a; PF FR-018 |
| BR-SEAM-05 | The seam never decides: the intersection, origin stamping (O12 included), chain append and `maxChainDepth`, re-broadening, or the human-only class. They stay in P2 and P3 | PF §12; M1-FR-13 |

## 12. Problem Emission (BR-PE)

| ID | Rule | Source |
|---|---|---|
| BR-PE-01 | P1 holds the **one** Problem table: every code in `contract/conventions/errors.md`, with its status and generic title. U3 adds `unknown_field`, `stamped_field_set`, `invalid_inbound_context`, `chain_too_deep`, `envelope_too_large`, and `forbidden` (all already in the contract) | D-AE-06; BR-ERR |
| BR-PE-02 | P1's emission is **framework-neutral**: given a refusal and the request id, it returns the status, the headers (`Content-Type: application/problem+json; charset=utf-8`; `WWW-Authenticate: Bearer` on a 401 only; `Retry-After` on a 429 or 503), and the body. Each service keeps a thin adapter to its framework | D-AE-06 |
| BR-PE-03 | **BR-ERR-08**: every Problem carries `type` = `urn:soorma:problem:{code}`, `title`, `status`, `code`, and `instance` = `urn:soorma:request:{request id}`, equal to the response's `Soorma-Request-Id` | BR-ERR-08 |
| BR-PE-04 | `unsupported_contract_version` lists `supportedVersions`, from P1's accepted set (D-AE-25) | BR-VER-04 |
| BR-PE-05 | **S1 moves to P1's emission with no change in behaviour**: `services/org-gateway/src/problems.ts` is removed, and U2's tests pass unchanged except that S1's local `expectProblem` is replaced by P1's shared assertion, with no check dropped | D-AE-06 |
| BR-PE-06 | **The shared assertion** (a test-only export of P1, outside its runtime export) checks a response against BR-PE-02 and BR-PE-03, `Soorma-Contract-Version`, and the `Problem` schema. U3's tests run it over every code in the table; S1's edge tests run it on every Problem; U6 and U7 run it at S3 and S4 | D-AE-06; BR-ERR-08 |

---

## 13. Contract Changes

Made at U3's Code Generation, under contract `0.1.0` (unreleased: `contract-v0.1.0` is not
tagged), and recorded in `contract/CHANGELOG.md`.

| Change | Where | Classification |
|---|---|---|
| **U1 amendment A6, the stamped `traceContext`** (D-AE-05). It carries the forwarded envelope's unknown trace-context fields, plus the draft's `traceparent`, plus the draft's `tracestate` only if present. U1's BR-FC-04 and BR-TC-05 are reworded to match (U1 `business-rules.md`, *Amendment from U3*) | `conventions/envelope.md` (*Forwarded context and the seal*; the `traceContext` paragraph); the `EnvelopeTraceContext` description in `envelope.schema.json` | **A change within unreleased 0.1.0**, and compatible in kind: the envelope's `traceContext` is already open (A1); more is preserved, nothing is removed |
| **Version on a draft call** (D-AE-12): a missing `clientContractVersion` is `unsupported_contract_version`; a differing or repeated `Soorma-Contract-Version` header is `malformed_request` naming the header; a body that is not an object is `malformed_request` | `conventions/versioning.md` (*The client contract version*, *Accepted versions*); `conventions/errors.md` (*Check order*, step 5) | Compatible: a clarification of a refusal the contract left unstated |
| **Step 6 precedence** (D-AE-18): stamped fields, then unknown fields, then any other failure | `conventions/errors.md` (*Check order*, step 6) | Compatible: a clarification |
| **A forwarded envelope over the bound is `invalid_inbound_context`** (D-AE-19) | `conventions/envelope.md` (*The envelope bound*) | Compatible: a clarification |
| **Pre-release statement 9** (GAP-AE-001, D-AE-01): "**An agent whose registration does not declare autonomy is refused (`forbidden`) on any request whose origin is `autonomous`, including one forwarding an autonomous envelope.** Allowing it later would be additive" | `conventions/pre-release.md` | Compatible: states a work-around, as statement 5 does for GAP-INT-007 |

## 14. Application Design Corrections

Recorded as notes on the Application Design documents, as U1 did (component-methods.md):

| Document | Correction | Decision |
|---|---|---|
| `components.md`, P3 and P11; *Seam Interfaces* | The policy-decision seam has **both** halves (`grantedSet`, `contains`), not containment only. The human-only class is **defined in P3** (`packages/authority`) and used by P4's registration check | D-AE-02, D-AE-03 |
| `component-methods.md`, P2, P3, P11 | `createEnvelopeAdmission(dependencies).admit(request)` is the surface's one entry point (P3; *Consistency fix from NFR Design (2026-11-10): formerly `admitEnvelopeRequest`*); `contains` takes a required **set**; P11 gains `grantedSet` | D-AE-04, D-AE-02, D-AE-10 |

## 15. Misuse Cases (SECURITY-11)

| Misuse | Rule that defeats it |
|---|---|
| An agent that has not declared autonomy forwards a sealed autonomous envelope it obtained, to act without a delegation | BR-OR-04 (GAP-AE-001 work-around) |
| An agent forwards nothing to act autonomously without having declared it (escalation by omission) | BR-OR-02 (O12) |
| An agent sets `originMode` or a re-broadening record in its draft | BR-DV-04: `stamped_field_set` |
| An agent forwards a doctored envelope: a forged chain, a removed upstream hop, an added re-broadening record | BR-FX-02: the seal fails |
| An agent forwards a genuine envelope from another environment | BR-FX-02, 04 |
| An agent forwards a genuine envelope naming high-authority upstream agents, to widen | BR-AU: upstream terms only narrow (L4); re-broadening is capped by `S` |
| An agent relies on an upstream hop's re-broadening record | BR-AU-06, D-AE-20: records never grant |
| A registration whose declaration exceeds its standing set slips past U5 | BR-AU-04: `W` is intersected with `S` |
| A registration holding a human-only permission slips past U5 | BR-AU-03: refused at evaluation |
| A forwarded `delegated` or unknown origin, to reach an unevaluated path | BR-OR-05: `forbidden` |
| An oversized forwarded envelope, to make the perimeter compute a seal over it | BR-FX-01: size first |
| A loop of agents re-triggering each other | BR-CD-01: `chain_too_deep` before any read |
| A caller probing which forwarded-context or authority check failed | BR-RF-01: one code; reasons only in the security log |
| A store outage, hoping evaluation fails open | BR-AU-09, BR-OR-06: `unavailable` |
| A replacement policy implementation returning a wider effective set | BR-SEAM-02: no seam operation returns one; composition is in core |

The accepted residual of U1 (a genuine envelope forwarded by an agent it was not delivered
to, or an old one) stands as U1 recorded it. D-AE-01 keeps its stated bound: an
`autonomous` origin still requires the presenter's own declaration.

## 16. Forward Obligations

Posted on each unit's issue when this stage is approved.

**To U4 `env-human-access` (soorma-core#7)**
- Add `evaluateHuman` in P3 (`packages/authority`), using the same seam: `grantedSet(human,
  E)` then `contains`. No second place computes authority (BR-AU-01)
- Fill P11's `GrantSource` for a human: the union of its grants in E (the held set)
- S2 emits Problems through P1 (BR-PE) and runs the shared assertion on every Problem

**To U5 `agent-registration` (soorma-core#8)**
- Fill the **agent-facts port** from P4 **with one query**: for a list of agents, each
  one's Registration View (autonomy declared, default no; re-broadening declaration) and
  standing set together, or not found. *Revised at U3's NFR Design (2026-11-10): one port
  replaces the separate Registration View source and agent `GrantSource`*
- The registration check imports the human-only class from `packages/authority`
  (D-AE-03), never a copy
- Registrations are never deleted, so an upstream agent in a sealed chain always resolves
  (D-AE-09)

**To U6 `agent-credentials` (soorma-core#9)**
- **The agent credential asserts** organization, project, environment, logical agent, and
  instance (D-AE-08). P1's `checkAgentRequest` returns them as the Checked Agent Context
- S3 emits Problems through P1 and runs the shared assertion on every Problem (BR-PE-06)

**To U7 `event-transport` (soorma-core#10)**
- S4 runs steps 1 to 4, then builds the entry point once per instance with
  `createEnvelopeAdmission(dependencies)`, then calls its `admit(request)` **once** per publish and per
  subscribe (*Consistency fix from NFR Design (2026-11-10): formerly `admitEnvelopeRequest`*), with required authority `{event:publish}` or `{event:subscribe}`, the
  `Soorma-Contract-Version` header values, and the request id. **S4 does not import P2 or
  P3's internals** (D-AE-04)
- Turn each refusal into a Problem through P1, and run the shared assertion on every Problem
- **S4's published body size limit (check-order step 1) must admit a draft that forwards an
  envelope at the full envelope bound**, so that "every envelope the platform stamps can be
  forwarded" (BR-ENV-10) holds. Such a draft carries the forwarded envelope (up to 16384
  bytes in JCS form), the seal (up to 1024 characters), the draft's `traceContext`
  (`traceparent` and `tracestate`, up to 512 each), `clientContractVersion`, and the JSON
  wrapping, and **a client may serialize less compactly than JCS**. U7 sets the number at
  its NFR Requirements with this sum as the floor, and **a test sends a maximum-size
  forwarding draft through step 1** (the user's addition at this stage's approval,
  2026-11-10)
- Deliver the seal beside the envelope in each Delivery (BR-ENV-08)
- Write the attribution record (P7) from the returned outcome (BR-ST-08)
- Provide the security log, and the sealing material to the entry point: **provisioned at
  U7's Infrastructure Design** (S4 is the deployable that holds it), in the form U3's NFR
  Design sets

**To U3's own NFR Requirements and NFR Design**
- The Ajv runtime regex engine (D-CG-05, from U1)
- The latency budget for steps 5 to 10 on the per-request hot path (PF §9 NFR profile)
- Whether `grantedSet` reads are cached, and for how long (no operation changes a standing
  set in M1)
- The seal's algorithm, key identification, and rotation (U1 D-WC-06); the JCS
  implementation. Where each environment's sealing material is provisioned is U7's
  Infrastructure Design: U3 has no deployable

## 17. Specification Gaps

| ID | Status | Rule affected | Issue |
|---|---|---|---|
| GAP-AE-001 | **Open**; worked around (deny) | BR-OR-04; D-AE-01; pre-release statement 9 | [soorma-prd#30](https://github.com/soorma-ai/soorma-prd/issues/30) |
| GAP-INT-007 (inherited) | Open; worked around (reject and stamp) | BR-DV-04 | [soorma-prd#25](https://github.com/soorma-ai/soorma-prd/issues/25) |

Full entry: [../prd-gaps/specification-gaps.md](../prd-gaps/specification-gaps.md).
