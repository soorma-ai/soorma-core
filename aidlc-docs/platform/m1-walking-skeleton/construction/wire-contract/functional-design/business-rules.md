# Business Rules: U1 `wire-contract`

**Unit**: U1 `wire-contract` (soorma-core#4)
**Built against**: PF @ `prd-platform-foundations-v1.3`, ID @ `prd-identity-v1.0`
**Decisions from**: the Functional Design plan, Q1 to Q12, answered 2026-11-08 (recorded
verbatim in `audit.md`)
**Entities**: [domain-entities.md](domain-entities.md)

**Amendments after approval** (recorded in `audit.md`, 2026-11-08, before the Construction
Design PR gate):
- **A1, `traceContext` openness.** The envelope's `traceContext` is **open**, and the
  draft's is **closed**: two definitions (BR-TC-05; BR-ENV-05; BR-DR-06). Closing the
  envelope's copy made every optional addition breaking, against PF FR-005 (a), BR-VER-05,
  and I7
- **A2, Problem is a received schema.** Its `type` and `instance` carry no pattern. The
  `urn:soorma:` forms stay published conventions, and that soorma-core emits them is
  verified by U3's perimeter tests (BR-ERR-08)
- **A3, Problem requiredness.** Following RFC 9457, the received Problem schema **requires
  no field**: a gateway's or proxy's problem usually carries `about:blank` with no `code` or
  `instance`. soorma-core **always emits** `type`, `title`, `status`, `code`, and `instance`,
  with the `urn:soorma:` forms: a published convention, verified by U3 (BR-ERR-08)

U1 states these rules **in the contract**: in the schemas, and in `contract/conventions/`.
The perimeter rules (who rejects what, and when) are **implemented** by the surface and
mechanism units named in each rule. U1's own verification is that the schemas and
conventions say exactly this.

---

## 1. Decisions

| ID | Decision | Source | Class |
|---|---|---|---|
| D-WC-01 | JSON field names are **camelCase** | Q1 A | Technology |
| D-WC-02 | The contract version is **SemVer with major version 0**, starting at `0.1.0`, tagged `contract-v0.1.0` on `main` after U7's Code Generation. The client contract version is the same string | Q2 A | Technology |
| D-WC-03 | **Pre-release covers the operations, delivery semantics, error codes, and credential presentation. Envelope v1 is held to PF §7 from the first commit**: M1 makes no breaking envelope change, and `envelopeVersion` stays `1` | Q3 A | Technology, consistent with PF FR-004 |
| D-WC-04 | `scope` is `{ organization, project, environment }` | Q4 A | **Technology** (user's classification; see below) |
| D-WC-05 | `maxChainDepth` = **32** | Q5 B | Technology (handed to Functional Design, coverage map) |
| D-WC-06 | **The perimeter seals every envelope it stamps, and verifies the seal of every forwarded envelope** | Q6 C | **Technology**: the mechanism. Verification itself is required by the PRDs (see below) |
| D-WC-07 | One credential per request in `Authorization: Bearer`, with a **typed prefix** that gives its kind without verification | Q7 A, plus the user's addition | Technology |
| D-WC-08 | A required `Soorma-Contract-Version` request header on every call without a draft; the server's version on every response | Q8 A | Technology |
| D-WC-09 | Errors are RFC 9457 Problem Details with a stable, open `code` | Q9 A | Technology |
| D-WC-10 | Specific for validation, generic for trust; `credential_expired` only after verification; `too_many_attempts` on the abuse-bounded surfaces | Q10 A, plus the user's addition | Technology |
| D-WC-11 | The draft is **closed at its top level**. `inbound` carries the forwarded envelope **open, as received** | Q11 A, as qualified | Technology |
| D-WC-12 | The proposed shapes are approved. **JSON-only payloads** in M1. Identifier syntax is **set per kind** (BR-ID) | Q12 C | Technology |
| D-WC-13 | Trace context is carried in the request **body**, as part of the draft | Plan, approved at Q12 | Technology |
| D-WC-14 | Which operations carry an envelope (BR-OP) | PF FR-001 v1.3; ID FR-022; GAP-INT-008 | Inherited; work-around |
| D-WC-15 | The contract's pre-release statements (BR-PR) | GAP-INT-003, 006, 007; A-4 | Inherited; work-arounds |
| D-WC-16 | Every response carries `Soorma-Request-Id`, also given in a Problem's `instance` (SECURITY-03 correlation) | This design | Technology. **Not asked**: flagged for review at this gate |

### D-WC-04: why `scope` is a technology decision

As the user recorded it (Q4): PF §7b's *environment identifier* is read as **the
environment's identity composed with its organization and project**. PF §17: "global
uniqueness is **composed with scope, never allocated**". ID §17 *Namespacing Rules*:
identifiers are "composed with" their organization or environment, and organization,
project, and environment identity are configured. The representation of that composed
identity is a technology choice.

### D-WC-06: the seal, and why verification is not open in the PRDs

**Derivation** (the user's, at Q6; recorded here as the basis of the decision):
1. PF FR-002 and O5 make the actor chain and origin **platform-stamped**. If the perimeter
   copied an unverified forwarded chain into the new envelope, the agent would in effect
   set them
2. PF §8b gives the setter of a propagated origin as "**Platform, from the inbound
   envelope**"
3. PF §17: the envelope is **not self-authenticating**
4. O10: no entry point treats another's traffic as pre-validated

**So the perimeter must verify** a forwarded envelope before it uses it. That is not a
specification gap, and none is raised. **How** it verifies is the technology decision
(I11): a **seal**.

**The seal's rules** (the user's constraints, plus the two choices left to AI-DLC):
- **Computed over the RFC 8785 (JCS) canonical form** of the envelope. *AI-DLC's choice*
  between the two forms the user allowed. JCS is chosen over "forwarded byte for byte",
  because a client in any language may parse and re-serialize the envelope, and the
  seal must survive that
- **Bound to the environment.** It is computed with that environment's own sealing
  material, which is never shared (PF §6; I1). A seal from another environment is refused
- **A failed seal is a rejection under O5**: `invalid_inbound_context` (BR-ERR)
- It travels **beside** the envelope, so envelope v1 keeps exactly seven fields (PF
  FR-001; D-WC-03)
- It needs **no lookup**, so it adds nothing like the hot-path reference PF FR-006
  rejected
- It gives **no authority**. It is not a credential, and acting still needs the
  presenter's own credential (PF FR-002: "never usable to act")
- It proves **that this environment stamped the envelope, unaltered**. It does **not**
  prove that the envelope was delivered to the forwarder, or that it is recent. That
  residual is accepted (Section 14)
- *AI-DLC's choice*: the `inbound` wrapper `{ envelope, seal }` is **closed**, and the
  envelope inside it is **open**, carried as received (D-WC-11)
- Algorithm, key identification, and rotation: **NFR Design** (U3, which stamps)

---

## 2. Envelope Rules (BR-ENV)

| ID | Rule | Source | Implemented by |
|---|---|---|---|
| BR-ENV-01 | The envelope has exactly the seven fields of PF §7b, with the requiredness in [domain-entities.md](domain-entities.md). `envelopeVersion`, `scope`, `originMode`, `actorChain`, and `traceContext` are required | PF FR-001, §7b | U1 schema |
| BR-ENV-02 | `delegatingPrincipal` is required when `originMode` is `delegated`. It is absent when `originMode` is `autonomous` | PF §7b | U1 schema (conditional) |
| BR-ENV-03 | `reBroadening`, when present, has at least one record. Each `hop` is a valid index into `actorChain`, and no `hop` appears twice | PF §7b, §8b | U1 schema (form); U3 (index validity) |
| BR-ENV-04 | `actorChain` has 1 to **32** entries, most recent last. A chain that would exceed 32 is rejected, never truncated | PF FR-006; D-WC-05 | U1 schema; U3 `stamp` |
| BR-ENV-05 | **Open to unknown fields at every level**: the envelope, `scope`, actor references, re-broadening records, the delegating principal reference, and `traceContext` (the envelope's definition; the draft's is closed, BR-DR-06; amendment A1). A consumer preserves and forwards them | PF FR-005 a; PF §14 | U1 schema |
| BR-ENV-06 | **Enumerated values are open strings**. `originMode`'s known values are `autonomous` and `delegated`. An unknown value is not a schema error. Generated types carry the known values plus "any other string" | PF FR-005 b | U1 schema; type generation |
| BR-ENV-07 | `envelopeVersion` is `1` throughout M1. A breaking envelope change requires a new envelope version and a supported transition (PF FR-004), which M1 does not build. So M1 makes no breaking envelope change | PF FR-004; D-WC-03 | U1 conventions |
| BR-ENV-08 | Every envelope the perimeter stamps is sealed, and the seal is delivered beside it | D-WC-06 | U3 `stamp`; U7 delivery |
| BR-ENV-09 | Sponsorship is **not** on the envelope. It is resolved from `actorChain[i].agent` through the registration | PF §7b *Recoverability* | — (by absence) |
| BR-ENV-10 | **The perimeter refuses to stamp an envelope whose JCS serialization would exceed the envelope bound (16 KiB, BR-DR-09)**, with `envelope_too_large`, as it does with `chain_too_deep`. It never truncates or drops fields (including unknown fields carried from `inbound`) to fit. So every envelope the platform stamps can be forwarded | SECURITY-05; PF FR-005 a | U3 `stamp` |

## 3. Draft Rules (BR-DR)

| ID | Rule | Source | Implemented by |
|---|---|---|---|
| BR-DR-01 | The draft's **top level is closed**: `clientContractVersion`, `traceContext`, and `inbound` only. Any other field is rejected with `unknown_field`, **except a platform-stamped field, which is `stamped_field_set` (BR-DR-10)** | D-WC-11; SECURITY-05 | U1 schema; U3 `validateDraft` |
| BR-DR-02 | A draft that sets any platform-stamped field is **rejected, never overwritten**: `scope`, `originMode`, `delegatingPrincipal`, `actorChain`, `reBroadening`. The code is `stamped_field_set`, with a pointer to the field | PF FR-002, O5, §11; *done when* 7 | U1 schema; U3 |
| BR-DR-03 | **Origin mode is never accepted from a draft**, including at an autonomous first hop. It is stamped from the registration's autonomy declaration (GAP-INT-007 work-around, soorma-prd#25). Accepting an asserted value later is additive | GAP-INT-007; M1-FR-01 | U1 schema; U3 |
| BR-DR-04 | A draft that sets `envelopeVersion` is rejected with `stamped_field_set`. `clientContractVersion` is expected instead | PF §11 | U1 schema; U3 |
| BR-DR-05 | `clientContractVersion` is required, and must be in the accepted set (BR-VER-03) | PF §7b, §14 | U1 schema; U3 |
| BR-DR-06 | `traceContext` is required and must be well-formed (BR-TC). **The draft's `traceContext` is closed**: `traceparent` and `tracestate` only. Any other field in it is rejected with `unknown_field` and a pointer (input strictness; BR-TC-05) | PF §7b; M1-TECH-05 | U1 schema; U3 |
| BR-DR-07 | `inbound`, when present, holds exactly `envelope` and `seal`, both required. The wrapper is closed | D-WC-06, D-WC-11 | U1 schema |
| BR-DR-08 | `inbound.envelope` is **open and carried as received**. Its unknown fields are preserved into the envelope the perimeter stamps for this hop | PF FR-005 a; PF §14 *Inbound context forwarding*; Q11 | U1 schema; U3 `stamp` |
| BR-DR-09 | `inbound.envelope` is at most **16 KiB**, measured on its RFC 8785 (JCS) serialization, the form the seal covers. This is **the envelope bound**; BR-ENV-10 applies the same bound when stamping | SECURITY-05 | U1 conventions; U3 |
| BR-DR-10 | **A stamped field takes precedence over `unknown_field`.** The draft schema forbids each platform-stamped field **by name**: `envelopeVersion`, `scope`, `originMode`, `delegatingPrincipal`, `actorChain`, and `reBroadening`. Such a field is always `stamped_field_set` with a pointer to it, never `unknown_field`, even when the draft also carries an unknown field. A draft carrying both is refused with `stamped_field_set` | PF FR-002, O5; *done when* 7; TC-WC-007 | U1 schema; U3 `validateDraft` |

## 4. Forwarded Context and Seal Rules (BR-FC)

| ID | Rule | Source | Implemented by |
|---|---|---|---|
| BR-FC-01 | Before a forwarded envelope is used, its seal is verified against the JCS form of `inbound.envelope`, with **this** environment's sealing material | D-WC-06; PF FR-002, §8b, §17; O10 | U3 |
| BR-FC-02 | `inbound.envelope.scope` must equal this environment's scope | I1; PF FR-021 | U3 |
| BR-FC-03 | A seal that fails, a seal from another environment, a scope mismatch, or an `envelopeVersion` other than `1` is rejected under O5 with **one** code, `invalid_inbound_context`. The response never says which | D-WC-06; I1; non-disclosure | U3 |
| BR-FC-04 | With a verified `inbound`, the new envelope takes: `scope` = this environment; `originMode` and `delegatingPrincipal` **unchanged** from `inbound`; `actorChain` = `inbound`'s chain plus this hop; `reBroadening` = `inbound`'s records, plus this hop's when load-bearing; `traceContext` from the draft; and `inbound`'s unknown fields | PF FR-006, FR-015, §8b; O6, O7 | U3 `resolveOrigin`, `stamp` |
| BR-FC-05 | Without `inbound`, origin is `autonomous` if the presenter's registration declares autonomy, and the request is **denied** (`forbidden`) if not | O12; PF §8b | U3 |
| BR-FC-06 | The seal is opaque to clients. A client forwards it unchanged and must not treat it as proof it can check | PF §17 | U1 conventions |

## 5. Trace Context Rules (BR-TC)

| ID | Rule | Source |
|---|---|---|
| BR-TC-01 | `traceparent` follows W3C Trace Context: `{version}-{trace-id}-{parent-id}-{flags}`, lowercase hex, with 2, 32, 16, and 2 digits. Version `ff` is invalid. An all-zero trace-id or parent-id is invalid | M1-TECH-05 |
| BR-TC-02 | For version `00`, `traceparent` is exactly 55 characters. A higher version may carry further `-`-separated fields after the flags, as W3C allows | W3C forward compatibility |
| BR-TC-03 | `tracestate` is optional: at most 512 characters, at most 32 list members, in W3C list-member syntax | W3C; SECURITY-05 |
| BR-TC-04 | The platform validates form only. It never interprets the values, and emits no spans | PF §7b; T-3 |
| BR-TC-05 | **Two definitions** (amendment A1), on BR-ID-11's principle: strict on what the platform accepts, tolerant of what it delivers. **In a draft**, `traceContext` is closed. **In an envelope**, it is open, like every other envelope object. W3C defines the `traceparent` and `tracestate` header strings, not this object, so the object is the contract's own and may gain optional fields compatibly (BR-VER-05). The stamped envelope takes `traceContext` from the draft (BR-FC-04), so in M1 it holds exactly what the draft's closed definition admits | PF FR-005 a; BR-VER-05; I7 |

## 6. Delivery Rules (BR-DL)

| ID | Rule | Source |
|---|---|---|
| BR-DL-01 | A Delivery is `{ envelope, seal, payload }`, all required, and open to unknown fields | D-WC-06; PF FR-005 |
| BR-DL-02 | `envelope` is a `$ref` to the envelope schema. No surface document carries a copy | PF FR-003 |
| BR-DL-03 | `payload` is any JSON value, opaque to the platform. The platform never inspects or classifies it | I9; D-WC-12 |
| BR-DL-04 | Its maximum size is bounded. **The value is set at U7's NFR Requirements**, and published in the conventions | SECURITY-05 |
| BR-DL-05 | Delivery semantics are **unspecified** at this contract version (BR-PR-02) | GAP-INT-003 |

## 7. Envelope-Bearing Operations (BR-OP)

| Operation | Surface | Envelope | Source |
|---|---|---|---|
| Publish | S4 | Draft in the request | PF FR-001 |
| Subscribe | S4 | Draft in the request; a Delivery per event on the stream | PF FR-001; Application Design |
| Bootstrap exchange | S3 | **None** | GAP-INT-008 work-around, soorma-prd#27 |
| Credential renewal | S3 | **None** | GAP-INT-008 work-around, soorma-prd#27 |
| Every human operation | S1, S2 | **None** | PF FR-001 v1.3; ID FR-022 |

| ID | Rule |
|---|---|
| BR-OP-01 | An operation not listed as envelope-bearing does not accept a draft. A body field named like a draft field has no envelope meaning there |
| BR-OP-02 | A surface unit adding an envelope-bearing operation adds a row here. That is a contract change, classified under BR-VER-05 |

## 8. Versioning Rules (BR-VER)

| ID | Rule | Source |
|---|---|---|
| BR-VER-01 | The contract version is SemVer `0.y.z`. M1's first published version is `0.1.0`, at the tag `contract-v0.1.0` | D-WC-02 |
| BR-VER-02 | A call **with** a draft declares its version in `clientContractVersion`. A call **without** one sends a required `Soorma-Contract-Version` header. On a call with a draft, the header may be sent, but then it must equal the draft's value | D-WC-08 |
| BR-VER-03 | The perimeter accepts every client contract version it has ever accepted, until a published deprecation window, longer than zero, elapses. Matching is exact; no ranges. **In M1 the accepted set is `{0.1.0}`, and the window is not exercised** | PF §14; coverage map *Handed to AI-DLC* |
| BR-VER-04 | A version not accepted is refused with `unsupported_contract_version`, listing `supportedVersions` | D-WC-10 |
| BR-VER-05 | **Every contract change is classified under PF §7b's compatibility policy**: adding an optional field is compatible; adding a required field, removing or renaming a field, or changing a meaning is breaking; widening a value set is compatible only because of BR-ENV-06; widening an identifier pattern or length is compatible only because of BR-ID-11. For a credential: a new kind or a new asserted attribute is compatible, and changing what it binds to is breaking (ID §7b) | PF §7b; ID §7b |
| BR-VER-06 | While the contract is pre-release, a breaking change **outside the envelope** ships as a new `0.y` version. **No breaking change to the envelope ships in M1** | D-WC-03 |
| BR-VER-07 | Every response carries `Soorma-Contract-Version`, set to the server's contract version | D-WC-08 |

## 9. Credential Presentation Rules (BR-CR)

| ID | Rule | Source |
|---|---|---|
| BR-CR-01 | A credential is presented only as `Authorization: Bearer {credential}`. One per request | D-WC-07 |
| BR-CR-02 | A credential presented anywhere else is refused with `credential_refused`: another header, a cookie, or a query parameter. **No cookies in M1** | D-WC-07; SECURITY-12 |
| BR-CR-03 | **The kind is readable from the typed prefix without verification**: `soorma_ac_` agent credential, `soorma_ec_` human environment credential, `soorma_si_` organization sign-in, `soorma_dc_` delegation credential (reserved). So S3 and S4 refuse human credentials by kind, with no organization-level material (P1 `classifyPresenter`) | D-WC-07; ID FR-023; M1-NFR-08 |
| BR-CR-04 | The prefix only selects how a credential is checked. **It never admits one.** A credential is accepted only after it verifies, and its verified kind must match its prefix; otherwise it is `credential_refused` | I2; D-WC-07 |
| BR-CR-05 | A credential is opaque to clients. **The whole credential, prefix included, is an RFC 6750 `b64token`**: letters, digits, `-`, `.`, `_`, `~`, `+`, `/`, then optional trailing `=`. It is at most 4096 characters. The syntax deliberately admits `.`, so NFR Design is free to choose the format (a JWT, for example). Every response that issues a credential states its expiry as an RFC 3339 time | D-WC-07; RFC 6750 §2.1 |
| BR-CR-06 | The `Soorma-Delegation` header is **reserved** for a delegation credential presented beside an agent credential. In M1 any request carrying it is refused with `credential_refused` | A-4; ID §14 |
| BR-CR-07 | The registration secret (`soorma_rs_`) and enrollment material (`soorma_em_`) are **material, not credentials**. They go in a request body, never in `Authorization`. Their typed prefixes let secret scanners find them, and keep them from being taken for credentials. At most 256 characters | PF §8b; ID FR-007; SECURITY-12 |
| BR-CR-08 | Each surface document names, per operation, exactly which security scheme it accepts: `agentCredential`, `environmentCredential`, or `signIn`. Bootstrap, sign-in, and first authentication name none | ID §8b matrix |
| BR-CR-09 | **No CORS in M1**: no browser origin is allowed. Allowing one later is an explicit list, never `*` | SECURITY-08 |

## 10. Error and Refusal Rules (BR-ERR)

Every error is RFC 9457 Problem Details (D-WC-09). Codes form an **open set**: a client
tolerates codes it does not know, and surface units may add codes.

| Code | Status | When | Detail returned |
|---|---|---|---|
| `malformed_request` | 400 | The body is not JSON, or fails the schema | `errors[]` with JSON Pointers |
| `unknown_field` | 400 | A field the closed draft does not define, **other than a platform-stamped field** | Pointer |
| `stamped_field_set` | 400 | A draft sets a platform-stamped field, `envelopeVersion` included (O5). **Takes precedence over `unknown_field`** (BR-DR-10) | Pointer to the field |
| `invalid_inbound_context` | 400 | The seal fails, is from another environment, the scope differs, or the envelope version is not accepted (O5) | **None**: one code for every cause |
| `chain_too_deep` | 400 | The chain would exceed 32 (O7) | None |
| `envelope_too_large` | 400 | The envelope to be stamped would exceed the envelope bound, 16 KiB in JCS form (BR-ENV-10) | None |
| `unsupported_contract_version` | 400 | The declared version is not accepted | `supportedVersions` |
| `credential_refused` | 401 | **Every credential failure except a verified expiry**: missing, malformed, unverifiable, revoked, ended, wrong environment, wrong kind for this surface, an extra credential, or the `Soorma-Delegation` header | **None** |
| `credential_expired` | 401 | The credential **verifies with this environment's material** and has expired | None. The caller renews or re-bootstraps |
| `forbidden` | 403 | Authority denied: O8, O9, and O12 | **None** |
| `payload_too_large` | 413 | The body exceeds the published size bound | None |
| `too_many_attempts` | 429 | The abuse bound on **bootstrap, sign-in, or first authentication** (P8) | `Retry-After` |
| `unavailable` | 503 | Revocation state cannot be read within the propagation bound (**fail closed**), or another dependency fails | `Retry-After` |
| `internal_error` | 500 | Anything unexpected | None |

| ID | Rule | Source |
|---|---|---|
| BR-ERR-01 | **Specific for validation, generic for trust.** A validation error names the field. A trust failure (credential, authority, forwarded context) names nothing beyond its code | D-WC-10 |
| BR-ERR-02 | `credential_expired` is returned **only after** the credential verifies with this environment's material. A credential that does not verify, whatever its expiry, is `credential_refused`. So expiry is never disclosed for a credential from another environment | D-WC-10; I1 |
| BR-ERR-03 | No response discloses another environment, or whether a principal or registration exists elsewhere (ID FR-014's non-disclosure, where it applies) | I1 |
| BR-ERR-04 | **On an abuse-bounded surface, `too_many_attempts` must not reveal whether its subject exists**: an unknown registration or principal is bounded and refused like a known one. *Carried to U2 and U6* | SECURITY-11; P8 |
| BR-ERR-05 | No response carries a stack trace, internal path, framework or version detail, or datastore detail | SECURITY-09, 15 |
| BR-ERR-06 | A 401 carries `WWW-Authenticate: Bearer`. A 429 and a 503 carry `Retry-After` | RFC 9110 |
| BR-ERR-07 | **Check order**, so a refusal is deterministic: (1) body size; (2) credential presentation and kind; (3) verification and expiry; (4) environment (O4) and revocation (O3); (5) contract version; (6) draft schema, with stamped fields before unknown fields (O5; BR-DR-10); (7) forwarded context (O5, O6); (8) chain depth (O7); (9) origin (O12) and authority (O8, O9); (10) the size of the envelope to be stamped (BR-ENV-10). The size check comes last because the envelope's final form, including any re-broadening record, is known only after authority is evaluated. An unauthenticated surface starts at (5), with its abuse bound before verifying material. A request is refused with the first check it fails. *U3, U6, and U7 implement it; U2 and U4 for human credentials* | Defense in depth; no oracle before authentication |
| BR-ERR-08 | **The Problem schema is a received schema** (amendments A2, A3). A client also receives problems a gateway or proxy emits, usually `about:blank` with no `code` or `instance`. So the schema **requires no field** (RFC 9457), `type` and `instance` are plain strings with no pattern, and a client accepts any value. **Emission requirements, published in the conventions**: every Problem soorma-core emits carries `type`, `title`, `status`, `code`, and `instance`; `type` is `urn:soorma:problem:{code}`; `instance` is `urn:soorma:request:{request id}`, equal to the response's `Soorma-Request-Id`. *Forward obligation, carried to U3* (soorma-core#6): the perimeter's tests verify each of these on every Problem soorma-core emits | BR-ID-11; RFC 9457 §3, §4.2.1 |

## 11. Identifier and Time Rules (BR-ID)

Set per kind (Q12; approved at the Functional Design review, 2026-11-08). Every identifier
is **case-sensitive and compared exactly**: no normalization, trimming, or case-folding.
The patterns govern **acceptance only** (BR-ID-11).

**The strict pattern**, used where the table below says *strict*:

```text
^[A-Za-z0-9][A-Za-z0-9._~-]*$
```

| ID | Kind | Pattern | Length | Note |
|---|---|---|---|---|
| BR-ID-01 | Configured: organization, project, environment | strict | 1 to 64 | |
| BR-ID-02 | Logical agent identifier | strict | 1 to 64 | Fits client-chosen and platform-allocated forms (U5 decides which) |
| BR-ID-03 | Platform references: registration, credential, grant, secret, request id | strict | 1 to 64 | A ULID or UUID fits |
| BR-ID-04 | **Instance identifier** (agent-asserted) | strict, plus `:` (see below) | 1 to 128 | Admits host names, pod names, UUIDs, and `host:pid` or `host:port` forms |
| BR-ID-05 | **Human principal identifier** | the human pattern (see below) | 1 to 256 | Email addresses (up to 254), and external-subject forms such as `issuer`, a vertical bar, and `subject` |
| BR-ID-06 | Permission identifier | the permission pattern (see below) | 1 to 128 | Widening the pattern later is compatible (GAP-INT-006) |

**Instance identifier** (BR-ID-04):

```text
^[A-Za-z0-9][A-Za-z0-9._~:-]*$
```

**Human principal identifier** (BR-ID-05). It allows RFC 5322 `atext`, plus `.`, `@`,
`:`, and `|`, so `@`, `+`, `:`, and `|` are all in. It excludes whitespace, control
characters, `"`, `(`, `)`, `,`, `;`, `<`, `>`, `[`, `\`, and `]`. It is **ASCII-only in
M1** (BR-ID-12):

```text
^[A-Za-z0-9!#$%&'*+/=?^_`{|}~.@:-]+$
```

**Permission identifier** (BR-ID-06), flat and opaque, matching every plane-declared
identifier:

```text
^[a-z][a-z0-9._-]*(:[a-z][a-z0-9._-]*)+$
```

| ID | Rule | Source |
|---|---|---|
| BR-ID-07 | Global uniqueness is **composed with scope, never allocated**. An identifier is unique within its scope: environment for agents, instances, and credentials; organization for human principals | PF §17; ID §17 |
| BR-ID-08 | Exact comparison is a **technology choice**: configured values are compared as configured. Human identifier normalization (for example, case-folding an email domain) is not specified by ID; exact comparison is the conservative reading and can be relaxed only additively | ID FR-001 |
| BR-ID-09 | An identifier is always a value, never interpolated into a query, path, or log without encoding (SECURITY-05). This matters most for the human pattern, which admits `'` and `/` | SECURITY-05 |
| BR-ID-10 | **Times** are RFC 3339 in UTC, with a `Z` suffix | — |
| BR-ID-11 | **Identifier patterns and lengths constrain only what the platform accepts.** They appear on request inputs only. **Consumers treat received identifiers as opaque strings and never validate their syntax.** In the envelope, the Delivery, and every response schema, an identifier is a plain string with no pattern or length constraint, and generated response types are plain strings. The envelope as a whole stays bounded (BR-ENV-10). So **widening a pattern or a length later is compatible** under BR-VER-05: no consumer can be broken by an identifier it did not expect | BR-VER-05; PF FR-005; I7 |
| BR-ID-12 | **Human principal identifiers are ASCII-only in M1.** Internationalized email addresses (RFC 6531, non-ASCII local parts or domains) are therefore **excluded**. This is a recorded delivery limit, not specified behaviour. Widening the pattern to admit them later is compatible (BR-ID-11) | ID FR-001; BR-ID-05 |

## 12. Pre-Release Statements (BR-PR)

The conventions carry these statements, verbatim in substance, under the contract version.

| ID | Statement | Source |
|---|---|---|
| BR-PR-01 | This contract is **pre-release** (`0.y.z`). The operations, error codes, and credential presentation may change between `0.y` versions. **Envelope v1 does not**: it follows PF §7 from this version on | D-WC-03 |
| BR-PR-02 | **Event delivery semantics are unspecified at this version.** Delivery reaches live subscribers only, with no durability, ordering, redelivery, or acknowledgement promised. Do not rely on observed behaviour | GAP-INT-003 (Awaiting PRD: Event, soorma-prd#13) |
| BR-PR-03 | **The bootstrap exchange and credential renewal carry no envelope** | GAP-INT-008 (soorma-prd#27) |
| BR-PR-04 | **The accepted permission identifiers may widen in a compatible version.** In this version, only the plane-declared identifiers are accepted | GAP-INT-006 (soorma-prd#24) |
| BR-PR-05 | **A draft never carries origin mode.** Accepting an asserted origin later would be additive | GAP-INT-007 (soorma-prd#25) |
| BR-PR-06 | **Delegation-credential presentation will be added without a breaking change.** The `Soorma-Delegation` header and the `soorma_dc_` prefix are reserved | A-4; ID §14 |
| BR-PR-07 | `maxChainDepth` is **32** for envelope v1 | D-WC-05 |
| BR-PR-08 | **The envelope bound is 16 KiB**, measured on the RFC 8785 (JCS) serialization. Received identifiers are opaque strings; do not validate their syntax | BR-ENV-10; BR-ID-11 |

## 13. Licence and Type-Generation Rules (BR-LG)

| ID | Rule | Source |
|---|---|---|
| BR-LG-01 | Everything under `contract/` is **Apache 2.0**: the schemas, the conventions, the surface documents, and the generated types. `contract/` has its own `LICENSE`. Each schema and document declares `SPDX-License-Identifier: Apache-2.0` | PF §22 |
| BR-LG-02 | `packages/` and `services/` are FSL-1.1-ALv2 | PF §22 |
| BR-LG-03 | TypeScript types are **generated** from the schema into `contract/generated/`, and never edited by hand | M1-TECH-02 |
| BR-LG-04 | No hand-written TypeScript declaration of a contract shape exists anywhere else in the repository | M1-TECH-02; TC-WC-003 |
| BR-LG-05 | A build check regenerates the types and fails if they differ from the committed ones | M1-TECH-02 |
| BR-LG-06 | Generated types keep the contract's openness: open objects admit extra keys, open enumerations admit any string, and received identifiers are plain strings | BR-ENV-05, 06; BR-ID-11 |
| BR-LG-07 | soorma-sdk generates its own types from the tagged schema. **No generated type is shared by hand** | M1-TECH-02 |

---

## 14. Misuse Cases (SECURITY-11)

| Misuse | Rule that defeats it |
|---|---|
| An agent forwards a made-up chain to attribute its action to another agent (I4) | BR-FC-01: the forged envelope has no valid seal |
| An agent forwards a genuine envelope from environment E2 into E | BR-FC-02, 03; the seal is bound to E2's material |
| An agent sets `originMode: autonomous` to skip O12 | BR-DR-02, 03 |
| A client renames a credential's prefix to reach a surface it should not | BR-CR-04: the prefix selects a check and never admits; the verified kind must match |
| A caller probes which credentials are revoked or belong elsewhere | BR-ERR-01, 02: one `credential_refused` for all of them |
| A caller probes which registrations or principals exist, through the abuse bound | BR-ERR-04 |
| A client pre-sets a field that a later version makes platform-stamped | BR-DR-01: the draft is closed |
| An oversized forwarded envelope or chain exhausts the perimeter | BR-DR-09, BR-ENV-04, BR-ENV-10, BR-DL-04 |

### Accepted residual: replayed or misdirected genuine envelopes

**An agent forwards a genuine, correctly sealed envelope from the same environment that
it was not delivered, or an old one.** The seal accepts it. **The seal proves that this
environment's perimeter stamped the envelope and that it is unaltered. It does not prove
that the envelope was delivered to the forwarder, or that it is recent.**

Accepted, because the damage is bounded:
- **The chain prefix is still true**: every hop in it acted, in this environment, as
  stamped. Nothing in it is invented
- **Authority only narrows**: the forwarded chain adds terms to the intersection, and
  re-broadening is capped by the forwarder's own standing set (PF §8b). Origin propagates
  unchanged, and an `autonomous` origin still requires the presenter's own declaration
  (O12)
- **What is not proven** is the causal link: that this hop was triggered by that event.
  An attribution record can therefore show a true prefix followed by the forwarder,
  where the forwarder was never actually triggered by it

Binding the seal to a recipient or a time would need the platform to track deliveries, or
a freshness window on the forwarded context. No PRD requires either. Neither is built in
M1.
