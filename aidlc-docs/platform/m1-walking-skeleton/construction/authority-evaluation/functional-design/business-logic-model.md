# Business Logic Model: U3 `authority-evaluation`

**Unit**: U3 `authority-evaluation` (soorma-core#6). Data face, environment level. Modules only
**Rules**: [business-rules.md](business-rules.md). **Entities**: [domain-entities.md](domain-entities.md)

Module names are the Application Design's: P1 `perimeter`, P2 `envelope`, P3 `authority`,
P11 `policy-decision`, and `seams/policy-decision`.

---

## 1. Where U3 Sits

| Steps | What | Who |
|---|---|---|
| 1 to 4 | Body size; credential presentation and kind; verification and expiry; environment and revocation | P1 at S3, S4 (U6, U7) |
| **5 to 10** | **Contract version; draft schema; forwarded context; chain depth; origin and authority; the envelope bound, the stamp, and the seal** | **`createEnvelopeAdmission(dependencies).admit(request)` (U3)** (*Consistency fix from NFR Design (2026-11-10): formerly `admitEnvelopeRequest`*) |
| after | Publish or subscribe; attribution record; Problem on a refusal | S4 (U7), P7, P1 |

**Module dependencies** (no cycle): S4 → P1, P3. P3 → P2, `seams/policy-decision`.
P11 → `seams/policy-decision`. S4 wires P11 into P3. **No surface imports P2.** P2 and P3
do not depend on P1 (D-AE-25).

## 2. The Pipeline (`createEnvelopeAdmission(dependencies).admit(request)`)

*Consistency fix from NFR Design (2026-11-10): the entry point's name, formerly `admitEnvelopeRequest`.*

A request is refused at the first step it fails. Steps 5 to 8 read nothing from storage.

| # | Step | Module | Reads | Refusals |
|---|---|---|---|---|
| 5 | Contract version (BR-VR) | P2 `checkVersion` | the body's `clientContractVersion`; the header values; the accepted set | `malformed_request`, `unsupported_contract_version` |
| 6 | Draft schema and trace context (BR-DV) | P2 `validateDraft` | the body | `stamped_field_set`, then `unknown_field`, then `malformed_request` |
| 7 | Forwarded context, if `inbound` (BR-FX) | P2 `verifyInbound` | the Sealer; the configured scope | `invalid_inbound_context` |
| 8 | Chain depth (BR-CD) | P2 `checkChainDepth` | — | `chain_too_deep` |
| 9 | **Agent facts**: one batched, all-or-nothing read for the presenter and every distinct upstream agent (*Consistency fix from NFR Design (2026-11-10)*) | the entry point | the agent-facts port, through its caching decorator | `unavailable` |
| 9a | Origin (BR-OR) | P3 `resolveOrigin` | the presenter's Registration View, from that read | `forbidden` |
| 9b | Authority (BR-AU) | P3 `evaluateAgent` | the seam: `grantedSet` for the presenter and each distinct upstream agent, **served from that read**; `contains` | `forbidden` |
| 10 | Stamp, bound, seal (BR-ST) | P2 `stamp` | the Sealer | `envelope_too_large` |

Before step 5, the entry point checks that the Checked Agent Context's scope equals the
configured scope (D-AE-23; `internal_error` if not) and that the required set is non-empty
(D-AE-10). Neither can fail in a correct build. Every refusal is written to the security
log with its internal reason (D-AE-26).

## 3. The Evaluation (P3 `evaluateAgent`)

```text
input:  presenter, required set R, declaration D, forwarded chain (possibly none), E

1. if R contains a human-only permission         -> deny (human_only_permission)
2. S  := grantedSet(presenter, E)
3. for each distinct agent a in the forwarded chain:
       Ua := grantedSet(a, E)                       (empty if a does not resolve)
   U  := intersection of every Ua                   (absent if there are none)
4. P  := absent                                     (autonomous origin; the only M1 origin)
5. N  := S ∩ P ∩ U                                  (absent terms impose nothing)
   W  := S ∩ P ∩ (U ∪ D)                            (with U absent: W = S ∩ P)
6. allowed      := contains(W, R)
   loadBearing  := allowed and not contains(N, R)
7. if not allowed -> deny (upstream_unresolved if any upstream agent did not resolve,
                           else authority_denied)
   else          -> allow, loadBearing
```

Steps 2 and 3 are served from the agent-facts read at the start of step 9: they never reach the store, and a read failure there has already refused the request `unavailable` (BR-AU-09). *Consistency fix from NFR Design (2026-11-10)*. `S`, `U`, `N` and `W` never leave P3.

**Re-broadening at each case-table row** (TC-AE-022): with `S = {p}`, one upstream agent
with term `U1`, and declaration `D`:

| Row | `U1` | `D` | `N` | `W` | Outcome | Record |
|---|---|---|---|---|---|---|
| 1 | `{p}` | `{}` or `{p}` | `{p}` | `{p}` | allow | no |
| 2 | `{}` | `{p}` | `{}` | `{p}` | **allow, by re-broadening** | **yes** |
| 3 | `{}` | `{}` | `{}` | `{}` | deny | no |
| 4 | — | — | — | — | Delegated origin only (`p` not in `P`); not reachable in M1, where `P` imposes nothing. Tested in P3 with a constructed `P` term | — |

## 4. Stamping (P2 `stamp`)

```text
if no inbound:
    envelope := { envelopeVersion: 1, scope: context.scope, originMode: autonomous,
                  actorChain: [ { agent, instance } ], traceContext: draft.traceContext }
else:
    envelope := copy of inbound.envelope, as received (every unknown field kept)
    envelope.envelopeVersion := 1
    envelope.actorChain      := inbound chain entries as received, then { agent, instance }
    if loadBearing:
        envelope.reBroadening := (inbound records as received), then { hop: len(chain) - 1 }
    trace := inbound traceContext without traceparent and tracestate
    trace.traceparent := draft.traceContext.traceparent
    if draft.traceContext has tracestate:
        trace.tracestate := draft.traceContext.tracestate
    envelope.traceContext := trace
    (scope, originMode, delegatingPrincipal: kept as received)

if byteLength(utf8(JCS(envelope))) > 16384 -> refuse envelope_too_large
seal := Sealer.seal(JCS(envelope))
return { envelope, seal }
```

## 5. Worked Examples

All in one environment E. A and B declare autonomy (A-5). Standing sets: A `{event:publish}`,
B `{event:subscribe}`.

### US-08: A publishes, first hop

| Step | Result |
|---|---|
| 5, 6 | Draft `{ clientContractVersion: 0.1.0, traceContext: { traceparent } }`: valid |
| 7, 8 | No `inbound`; chain length 1 |
| 9a | No `inbound`, A declares autonomy: `autonomous` (BR-OR-01) |
| 9b | `R = {event:publish}`, `S = {event:publish}`, no upstream: `W = N = S`; allowed; not load-bearing |
| 10 | `{ envelopeVersion: 1, scope: E, originMode: autonomous, actorChain: [A's instance], traceContext: A's }`, sealed |

B's subscribe is the same with `R = {event:subscribe}`.

### US-09: what B receives

B's Delivery carries A's stamped envelope and its seal: scope E, origin `autonomous`, chain
`[A's instance]`, trace context as A asserted it, no `delegatingPrincipal`. Every field was
written by the perimeter from A's credential and registration, and A's draft could set
none of them (US-11).

### US-11: a draft that sets a stamped field

A draft with `originMode: autonomous` and an extra field `foo`: refused at step 6 with
`stamped_field_set`, pointer `/originMode` (stamped before unknown, BR-DV-02). Nothing is
stamped.

### A constructed chain: re-broadening is load-bearing, then local

Agents X, Y, Z declare autonomy. `standing(X) = {a}`; `standing(Y) = {a, b}`, declaration
`{b}`; `standing(Z) = {a, b}`, no declaration.

| Hop | Presenter | `R` | Upstream terms | `N` | `W` | Outcome | Envelope after |
|---|---|---|---|---|---|---|---|
| 0 | X | `{a}` | — | `{a}` | `{a}` | allow | chain `[X]` |
| 1 | Y, forwarding X's | `{b}` | `{a}` | `{a}` | `{a, b}` | **allow, load-bearing** | chain `[X, Y]`, `reBroadening [{hop: 1}]` |
| 2 | Z, forwarding Y's | `{b}` | `{a}` ∩ `{a, b}` = `{a}` | `{a}` | `{a}` | **deny**: Y's record grants Z nothing (BR-AU-06) | — |

### A constructed chain: GAP-AE-001's work-around

C has **not** declared autonomy; `standing(C) ⊇ {event:publish}`. C publishes, forwarding
A's sealed autonomous envelope. Steps 5 to 8 pass. Step 9a: `inbound` is autonomous and C
has not declared autonomy, so the request is refused `forbidden`, reason `o12_undeclared`
(BR-OR-04). Under GAP-AE-001's other reading it would be allowed on `standing(C) ∩
standing(A)`; M1 builds the deny reading until soorma-prd#30 is resolved.

### Chain depth

A forwarded chain of 31 entries: the new chain has 32, accepted. A forwarded chain of 32:
`chain_too_deep` at step 8, with no registration read (TC-AE-017).

## 6. Problem Emission (P1)

| From | Through | To |
|---|---|---|
| A refusal (code, reason, errors) | P1's table: status, title, headers, body (BR-PE-02, 03) | The service's adapter writes the response; the reason goes to the security log only |

S1 uses it now, in place of `services/org-gateway/src/problems.ts`. S2, S3 and S4 use it
when built. Every edge's tests run P1's shared assertion on every Problem (BR-PE-06).
