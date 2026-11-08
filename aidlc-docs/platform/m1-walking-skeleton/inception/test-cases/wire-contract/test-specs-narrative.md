# Test Specifications (Narrative): wire-contract

**Unit**: `wire-contract` (U1: the wire contract's cross-surface parts, with no face)  
**Unit abbreviation**: WC = wire-contract  
**Scope**: comprehensive (happy path, negative, edge and boundary), as recorded in `aidlc-state.md`  
**Derived from**: `aidlc-docs/platform/m1-walking-skeleton/inception/application-design/unit-of-work.md` and `aidlc-docs/platform/m1-walking-skeleton/inception/requirements/requirements.md` only  
**Generated**: inception pass, 2026-11-02. IDs are permanent  
**Enriched**: construction pass, 2026-11-08, from `construction/wire-contract/functional-design/` and `construction/wire-contract/nfr-requirements/` (NFR Design and Infrastructure Design were skipped for U1). TC-WC-001 to 011 refined in place; TC-WC-012 to 041 added. The pass's change log is a session artifact (git-ignored); its outcome is recorded in `audit.md`

## Common Fixtures

Every test case below runs against the **local stack** (M1-NFR-05) unless it says
otherwise. The fixture names are used throughout this file:

| Name | Meaning |
|---|---|
| **O** | The organization configured in the deployment's configuration |
| **E**, **E2** | Two environments of O, each its own deployment with its own store and minting material (`unit-of-work.md`, Code Organization) |
| **H** | The human principal named as E's first Admin in configuration |
| **K**, **P** | H's memorized secret, and possession-based authenticator, respectively |
| **sign-in** | An organization sign-in issued to H by the organization level |
| **env credential (E)** | A human environment credential issued by E |
| **A**, **B** | Two logical agents registered in E by H, each with autonomy declared unless a case says otherwise |
| **agent credential (E)** | A short-lived credential issued by E's bootstrap exchange to an instance of A or B |
| **the bound** | The published revocation propagation bound (M1-FR-07). Its value is set at NFR Requirements |
| **raw call** | An HTTP request made without the SDK, conforming to the wire contract |
| **test-only revocation seeding** | The path, not compiled into the product, that writes agent revocation state (M1-FR-07) |

Values not yet fixed (bounds, lifetimes, `maxChainDepth`) are referred to by name. Their
numbers come from the unit's NFR Requirements and Functional Design, and the construction
pass of this extension records them.

### Construction pass: U1's fixtures and fixed values

**U1 has no deployable.** Its test cases run in the repository's own test suite and in CI,
not against the local stack. They use a JSON Schema 2020-12 validator configured as the
contract is built: Ajv 8 in 2020-12 mode, `strict: true`, with every schema under
`contract/` loaded so local `$ref`s resolve. Where a case says *with all errors*, the
validator reports every error, not only the first.

| Value | Fixed at | Source |
|---|---|---|
| Contract version | `0.1.0` (SemVer, major version 0); accepted set `{0.1.0}` | D-WC-02; BR-VER-01, 03 |
| `envelopeVersion` | `1` | D-WC-03; BR-ENV-07 |
| `maxChainDepth` | **32** | D-WC-05 |
| The envelope bound | **16 KiB**, measured on the RFC 8785 (JCS) serialization | BR-DR-09; BR-ENV-10 |
| Credential length | at most 4096 characters; registration secret and enrollment material at most 256 | BR-CR-05, 07 |
| `tracestate` | at most 512 characters, at most 32 list members | BR-TC-03 |
| Delivery payload bound | **Not fixed in U1**: set at U7's NFR Requirements (BR-DL-04) | BR-DL-04 |

Sample documents used by U1's cases (field names are camelCase, D-WC-01):

| Name | Content |
|---|---|
| **sample envelope** | `envelopeVersion: 1`; `scope: { organization: "o1", project: "p1", environment: "e1" }`; `originMode: "autonomous"`; `actorChain: [{ agent: "agent-a", instance: "host-1:4100" }]`; `traceContext: { traceparent: "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01" }` |
| **delegated envelope** | The sample envelope with `originMode: "delegated"` and `delegatingPrincipal: { organization: "o1", principal: "h@example.com" }` |
| **re-broadened envelope** | The sample envelope with a two-entry `actorChain` and `reBroadening: [{ hop: 1 }]` |
| **sample draft** | `clientContractVersion: "0.1.0"`; `traceContext` as in the sample envelope |
| **forwarding draft** | The sample draft plus `inbound: { envelope: <sample envelope>, seal: "s1" }` |
| **sample delivery** | `{ envelope: <sample envelope>, seal: "s1", payload: { "k": "v" } }` |

The fixture values are labelled test data. None is a tenant identifier (I9).

---

### TC-WC-001 — A well-formed envelope validates against the envelope schema

**Context**: M1-FR-02 requires one versioned contract defined in a language-neutral schema. The envelope schema is the definition every surface and the SDK share, so a correct envelope must validate against it. Envelope v1 has **exactly the seven fields** of PF §7b; the seal travels beside it, never inside (BR-ENV-01; D-WC-06).

**Scenario**: A reviewer validates the sample envelopes, each with its required fields and the conditional fields where their condition holds, and checks that the schema defines no eighth field.

**Preconditions**:
- `contract/envelope.schema.json` exists (JSON Schema 2020-12)
- The sample envelope, the delegated envelope, and the re-broadened envelope (Common Fixtures)

**Steps**:
1. Load `contract/envelope.schema.json` into a JSON Schema 2020-12 validator
2. Validate the sample envelope (`originMode: "autonomous"`, no `delegatingPrincipal`, no `reBroadening`)
3. Validate the delegated envelope
4. Validate the re-broadened envelope
5. List the properties the envelope definition declares

**Expected outcome**: Steps 2 to 4 pass with no errors. The declared properties are exactly `envelopeVersion`, `scope`, `originMode`, `delegatingPrincipal`, `actorChain`, `reBroadening`, and `traceContext`: no `seal`, and no other field.

**Scope**: happy-path · **Priority**: High  
**Source**: wire-contract / M1-FR-02  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/wire-contract/`  
**Technical references**: `inception/application-design/components.md`, `inception/application-design/unit-of-work.md`, `construction/wire-contract/functional-design/domain-entities.md` (*Envelope*), `construction/wire-contract/functional-design/business-rules.md` (BR-ENV-01, D-WC-06)

---

### TC-WC-002 — A Delivery validates against the Delivery schema

**Context**: U1 builds the named `Delivery` schema: a stamped envelope, the seal over it, and an opaque payload. It is how a subscriber types each delivered event, since the stream itself is typed only as `text/event-stream`. The payload is any JSON value, never inspected (BR-DL-01 to 03; I9).

**Scenario**: A reviewer validates sample deliveries carrying different kinds of JSON payload against `delivery.schema.json`.

**Preconditions**:
- `contract/delivery.schema.json` exists and references `envelope.schema.json`
- The sample delivery (Common Fixtures)

**Steps**:
1. Load both schemas into one validator, so references resolve
2. Validate the sample delivery
3. Validate copies of the sample delivery whose `payload` is, in turn, an array, a string, a number, `true`, and `null`
4. Inspect the Delivery definition's `envelope` property

**Expected outcome**: Steps 2 and 3 pass. The `envelope` property is a `$ref` to `envelope.schema.json`, not a copy, so the envelope part is validated through the referenced schema. `seal` is a string.

**Scope**: happy-path · **Priority**: High  
**Source**: wire-contract / M1-FR-02  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/wire-contract/`  
**Technical references**: `inception/application-design/components.md`, `inception/application-design/unit-of-work.md`, `construction/wire-contract/functional-design/business-rules.md` (BR-DL-01 to 03)

---

### TC-WC-003 — Types are generated from the schema, never hand-written

**Context**: M1-FR-02 (with M1-TECH-02) requires TypeScript types to be generated from the language-neutral schema, so the SDK never becomes the contract. One generator script runs openapi-typescript through its Node API (tech-stack-decisions T-07; BR-LG-03, 04).

**Scenario**: A developer changes a schema description and regenerates types.

**Preconditions**:
- The type-generation pipeline is set up in U1: the generator script `contract/scripts/generate-types`, writing to `contract/generated/`

**Steps**:
1. Add a documentation-only change (a `description`) to `envelope.schema.json`
2. Run the generator script
3. Search the repository for TypeScript type declarations of envelope, draft, Delivery, or Problem shapes outside `contract/generated/`

**Expected outcome**: Generated types are refreshed under `contract/generated/`, and the description appears there as a comment. No hand-written declaration of a contract shape exists elsewhere.

**Scope**: happy-path · **Priority**: High  
**Source**: wire-contract / M1-FR-02  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/wire-contract/`  
**Technical references**: `inception/application-design/components.md`, `inception/application-design/unit-of-work.md`, `construction/wire-contract/functional-design/business-rules.md` (BR-LG-03, 04), `construction/wire-contract/nfr-requirements/tech-stack-decisions.md` (T-07)

---

### TC-WC-004 — The contract declares its pre-release status

**Context**: M1-FR-02 requires the M1 contract to be published as pre-release, because delivery semantics are unspecified (GAP-INT-003). The pre-release status covers the operations, error codes, and credential presentation, but **not envelope v1**, which follows PF §7 from the first version (D-WC-03; BR-PR-01, 02).

**Scenario**: A reviewer reads the contract's conventions.

**Preconditions**:
- `contract/conventions/` exists

**Steps**:
1. Open the contract conventions
2. Find the contract version and its status
3. Find the statement of what the pre-release status covers
4. Find the statement on event delivery semantics

**Expected outcome**: The version is `0.1.0` and is marked pre-release. The conventions say that operations, error codes, and credential presentation may change between `0.y` versions, and that envelope v1 does not. They state that event delivery semantics are unspecified at this version: live subscribers only, with no durability, ordering, redelivery, or acknowledgement promised.

**Scope**: happy-path · **Priority**: High  
**Source**: wire-contract / M1-FR-02  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/wire-contract/`  
**Technical references**: `inception/application-design/components.md`, `inception/application-design/unit-of-work.md`, `construction/wire-contract/functional-design/business-rules.md` (D-WC-03, BR-PR-01, 02)

---

### TC-WC-005 — The contract states that bootstrap and renewal carry no envelope

**Context**: U1's inherited gap GAP-INT-008 is worked around by stating, in the contract, that neither the bootstrap exchange nor renewal carries an envelope. The conventions' table of envelope-bearing operations is how a surface unit knows whether an operation takes a draft (BR-OP; BR-PR-03).

**Scenario**: A reviewer reads the conventions for which operations carry an envelope.

**Preconditions**:
- `contract/conventions/` exists

**Steps**:
1. Open the contract conventions
2. Find the table of envelope-bearing operations
3. Find the rule for an operation the table does not list

**Expected outcome**: Publish and subscribe (S4) carry a draft, and subscribe delivers a Delivery per event. Bootstrap and renewal (S3) are named as carrying no envelope. Direct human operations (S1, S2) are also stated to carry none. An operation not listed does not accept a draft, and a surface unit that adds an envelope-bearing operation adds a row, classified as a contract change (BR-OP-01, 02).

**Scope**: happy-path · **Priority**: Medium  
**Source**: wire-contract / M1-FR-02 (GAP-INT-008, U1's inherited gaps)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/wire-contract/`  
**Technical references**: `inception/application-design/components.md`, `inception/application-design/unit-of-work.md`, `construction/wire-contract/functional-design/business-rules.md` (BR-OP, BR-PR-03)

---

### TC-WC-006 — An envelope missing a required field fails validation

**Context**: A contract that accepted an incomplete envelope would let consumers rely on fields that may be absent. Five fields are required unconditionally (BR-ENV-01).

**Scenario**: A reviewer validates envelopes, each with one required field removed.

**Preconditions**:
- `contract/envelope.schema.json`
- The sample envelope

**Steps**:
1. For each required field (`envelopeVersion`, `scope`, `originMode`, `actorChain`, `traceContext`), remove it from a copy of the sample
2. Validate each copy
3. For each part of `scope` (`organization`, `project`, `environment`), and each part of the actor reference (`agent`, `instance`), remove it from a copy of the sample and validate it

**Expected outcome**: Every copy fails validation, and the error names the missing field.

**Scope**: negative · **Priority**: High  
**Source**: wire-contract / M1-FR-02  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/wire-contract/`  
**Technical references**: `inception/application-design/components.md`, `inception/application-design/unit-of-work.md`, `construction/wire-contract/functional-design/domain-entities.md` (*Envelope*, *Scope*, *Actor Reference*)

---

### TC-WC-007 — The draft schema does not admit platform-stamped fields

**Context**: The draft an agent sends must never carry a platform-stamped field (M1-FR-01). A draft that sets one is **rejected, never overwritten**, with `stamped_field_set` and a pointer to the field. So the draft schema forbids each stamped field **by name**, and the failure is distinguishable from an unknown field (BR-DR-02, 04, 10).

**Scenario**: A reviewer validates drafts that each carry one platform-stamped field.

**Preconditions**:
- The draft definition in `contract/envelope.schema.json`
- The sample draft

**Steps**:
1. Take the sample draft (`clientContractVersion`, `traceContext`, and no `inbound`)
2. For each of `envelopeVersion`, `scope`, `originMode`, `delegatingPrincipal`, `actorChain`, and `reBroadening`, add the field to a copy, with a well-formed value
3. Validate each copy against the draft definition
4. Inspect each failure's location and schema keyword

**Expected outcome**: Every copy fails validation as a draft. Each failure points at the stamped field itself (for example `/originMode`), through that field's own prohibition, **not** through the draft's rule against additional properties.

**Scope**: negative · **Priority**: High  
**Source**: wire-contract / M1-FR-02  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/wire-contract/`  
**Technical references**: `inception/application-design/components.md`, `inception/application-design/unit-of-work.md`, `construction/wire-contract/functional-design/business-rules.md` (BR-DR-02, 03, 04, 10)

---

### TC-WC-008 — Unknown fields are permitted by the envelope schema

**Context**: Consumers must preserve and forward unknown fields (M1-FR-01). A schema that forbade additional properties would make every future field a breaking change. The envelope is open **at every level**, its `traceContext` included. The draft's `traceContext` is a separate, closed definition: strict on input (BR-ENV-05; BR-DR-06; BR-TC-05; amendment A1).

**Scenario**: A reviewer validates envelopes carrying an extra, unknown field at each level, and a draft carrying one in its `traceContext`.

**Preconditions**:
- The sample envelope, the delegated envelope, and the re-broadened envelope
- The sample draft

**Steps**:
1. Add a field `x-future` with any value at the top level of the sample envelope, and validate it
2. Add `x-future` inside `scope`, and inside an `actorChain` entry, validating each copy
3. Add `x-future` inside the delegated envelope's `delegatingPrincipal`, and validate it
4. Add `x-future` inside a record of the re-broadened envelope's `reBroadening`, and validate it
5. Add `x-future` inside the envelope's `traceContext`, and validate it
6. Add `x-future` inside the sample draft's `traceContext`, and validate it against the draft definition

**Expected outcome**: Steps 1 to 5 validate: every envelope object is open, `traceContext` included. Step 6 fails with an additional-property error at `/traceContext/x-future`: the draft's `traceContext` is closed.

**Scope**: edge-boundary · **Priority**: Medium  
**Source**: wire-contract / M1-FR-02  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/wire-contract/`  
**Technical references**: `inception/application-design/components.md`, `inception/application-design/unit-of-work.md`, `construction/wire-contract/functional-design/business-rules.md` (BR-ENV-05, BR-DR-06, BR-TC-05; amendment A1), `construction/wire-contract/functional-design/domain-entities.md` (*Entity Map*, *Trace Context*)

---

### TC-WC-009 — Every surface document references the one envelope definition

**Context**: One versioned contract covers every entry point. Copies of the envelope definition per surface would drift. U1 creates the shared document `contract/conventions/components.openapi.yaml`; each surface unit later adds its own document, and this check runs over every document present (BR-DL-02; business-logic-model §3).

**Scenario**: A reviewer inspects every OpenAPI document present for envelope, draft, Delivery, and Problem definitions, and for the shared headers and security schemes.

**Preconditions**:
- `contract/` with the shared components document, and any surface OpenAPI documents present

**Steps**:
1. List every schema definition named or shaped as an envelope, draft, Delivery, or Problem in `contract/conventions/components.openapi.yaml` and `contract/*.openapi.yaml`
2. Check each one's origin
3. In each surface document present, check that the security schemes and the `Soorma-Contract-Version`, `Soorma-Request-Id`, and `Retry-After` headers are referenced from the shared components, not redefined

**Expected outcome**: Each envelope or draft definition is a `$ref` to `envelope.schema.json`, each Delivery a `$ref` to `delivery.schema.json`, and none is an inline copy. Shared headers and security schemes are referenced, never copied. In U1, the check passes over the shared components document alone.

**Scope**: edge-boundary · **Priority**: Medium  
**Source**: wire-contract / M1-FR-02  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/wire-contract/`  
**Technical references**: `inception/application-design/components.md`, `inception/application-design/unit-of-work.md`, `construction/wire-contract/functional-design/business-logic-model.md` (§3), `construction/wire-contract/nfr-requirements/tech-stack-decisions.md` (T-07)

---

### TC-WC-010 — The client contract version is distinct from the envelope version

**Context**: A draft declares the client contract version, which is distinct from the envelope version (M1-FR-01). The schema must keep the two separate, so they can evolve independently: the contract version is a SemVer string, and the envelope version an integer (BR-DR-04, 05; domain-entities *Contract Version*).

**Scenario**: A reviewer inspects the draft and envelope definitions.

**Preconditions**:
- `contract/envelope.schema.json`

**Steps**:
1. Locate `clientContractVersion` in the draft definition
2. Locate `envelopeVersion` in the envelope definition
3. Validate a copy of the sample draft with `clientContractVersion` removed, and a copy with `envelopeVersion: 1` added

**Expected outcome**: They are two different properties: `clientContractVersion` is a string in SemVer form, `envelopeVersion` an integer of at least 1. The draft requires `clientContractVersion` and does not admit `envelopeVersion`: both copies in step 3 fail, the second at `/envelopeVersion` through that field's own prohibition.

**Scope**: edge-boundary · **Priority**: Medium  
**Source**: wire-contract / M1-FR-02  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/wire-contract/`  
**Technical references**: `inception/application-design/components.md`, `inception/application-design/unit-of-work.md`, `construction/wire-contract/functional-design/business-rules.md` (BR-DR-04, 05), `construction/wire-contract/functional-design/domain-entities.md` (*Contract Version and Client Contract Version*)

---

### TC-WC-011 — Contract files carry the Apache 2.0 licence

**Context**: The envelope's machine-readable definition is licensed Apache 2.0 (M1-FR-02, PF §22), separately from the FSL substrate. Every schema, document, and generated type under `contract/` declares it (BR-LG-01, 02; NFR-WC-21).

**Scenario**: A reviewer checks the licence of `contract/`, and the contract check verifies every file declares it.

**Preconditions**:
- The repository layout from U1

**Steps**:
1. Open the licence file in `contract/`
2. Open the licence file in `packages/`
3. Run the contract check for SPDX identifiers over every schema, document, and generated file under `contract/`

**Expected outcome**: `contract/` is Apache 2.0, and `packages/` is FSL-1.1-ALv2. Every file under `contract/` (schemas, conventions, OpenAPI documents, and `contract/generated/`) declares `SPDX-License-Identifier: Apache-2.0`, and the check passes.

**Scope**: edge-boundary · **Priority**: Medium  
**Source**: wire-contract / M1-FR-02  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/wire-contract/`  
**Technical references**: `inception/application-design/components.md`, `inception/application-design/unit-of-work.md`, `construction/wire-contract/functional-design/business-rules.md` (BR-LG-01, 02), `construction/wire-contract/nfr-requirements/nfr-requirements.md` (NFR-WC-21)

---

### TC-WC-012 — A stamped field takes precedence over an unknown field in a draft

**Context**: A draft carrying both a platform-stamped field and an unknown field must be refused with `stamped_field_set`, never `unknown_field` (BR-DR-10; *done when* 7). U3's `validateDraft` maps schema errors to codes, so the schema must report the stamped field distinctly even when an unknown field is also present, and the conventions must state the precedence.

**Scenario**: A reviewer validates a draft that sets `scope` and also carries `x-future`, and checks the conventions.

**Preconditions**:
- The draft definition; the sample draft; the validator configured to report all errors

**Steps**:
1. Add `scope` (well-formed) and `x-future: 1` to a copy of the sample draft
2. Validate it, reporting all errors
3. Open the conventions' error codes

**Expected outcome**: Validation fails with an error at `/scope` from that field's own prohibition, and a separate additional-property error for `x-future`. The conventions state that a stamped field takes precedence over `unknown_field`, and that such a draft is refused with `stamped_field_set` and a pointer to the stamped field.

**Scope**: negative · **Priority**: High  
**Source**: wire-contract / M1-FR-02 (BR-DR-10)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/wire-contract/code/`  
**Technical references**: `construction/wire-contract/functional-design/business-rules.md` (BR-DR-01, 10; BR-ERR), `construction/wire-contract/functional-design/l1-coverage-matrix.md` (L1-02)

---

### TC-WC-013 — The draft is closed at its top level

**Context**: The draft's top level admits only `clientContractVersion`, `traceContext`, and `inbound` (BR-DR-01; D-WC-11). Closing it stops a client pre-setting a field that a later version makes platform-stamped (misuse table, business-rules Section 14).

**Scenario**: A reviewer validates a draft carrying a field the draft does not define.

**Preconditions**:
- The draft definition; the sample draft

**Steps**:
1. Add `x-future: 1` to a copy of the sample draft and validate it
2. Add `priority: "high"` to another copy and validate it
3. Validate the sample draft and the forwarding draft unchanged

**Expected outcome**: Steps 1 and 2 fail with an additional-property error naming the field. Step 3 passes for both.

**Scope**: negative · **Priority**: High  
**Source**: wire-contract / M1-FR-02 (BR-DR-01)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/wire-contract/code/`  
**Technical references**: `construction/wire-contract/functional-design/business-rules.md` (BR-DR-01; Section 14)

---

### TC-WC-014 — A draft missing a required field fails validation

**Context**: `clientContractVersion` and `traceContext` are required on every draft (BR-DR-05, 06). Without them the perimeter cannot apply the version rules or carry the trace.

**Scenario**: A reviewer validates drafts with each required field removed, or malformed.

**Preconditions**:
- The draft definition; the sample draft

**Steps**:
1. Remove `clientContractVersion` from a copy and validate it
2. Remove `traceContext` from a copy and validate it
3. Set `clientContractVersion` to `1` (a number), and in another copy to `"v0.1"`, and validate each

**Expected outcome**: Every copy fails, and the error names the field.

**Scope**: negative · **Priority**: High  
**Source**: wire-contract / M1-FR-02 (BR-DR-05, 06)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/wire-contract/code/`  
**Technical references**: `construction/wire-contract/functional-design/business-rules.md` (BR-DR-05, 06), `construction/wire-contract/functional-design/domain-entities.md` (*Draft*)

---

### TC-WC-015 — The forwarded context is a closed wrapper around an open envelope

**Context**: `inbound` holds exactly `envelope` and `seal`, both required, and the wrapper is closed. The envelope inside it is **open and carried as received**, so its unknown fields can be preserved into the next stamped envelope (BR-DR-07, 08; D-WC-06, 11; PF FR-005 a). The seal is a request-side string, so it is bounded (NFR-WC-07).

**Scenario**: A reviewer validates forwarding drafts with the wrapper and its envelope varied.

**Preconditions**:
- The draft definition; the forwarding draft

**Steps**:
1. Validate the forwarding draft
2. Add `x-future` inside `inbound.envelope`, at its top level and inside its `scope`, and validate each copy
3. Add `x-future` to the `inbound` wrapper itself and validate it
4. Remove `seal`, and in another copy `envelope`, from `inbound`, and validate each
5. Set `seal` to a number and validate it
6. Inspect the `seal` property in `inbound` and in the Delivery definition

**Expected outcome**: Steps 1 and 2 pass. Steps 3 to 5 fail, naming the field. `seal` is a string with a `maxLength` in `inbound`, and a plain string in the Delivery. The schema does not check the seal's value: verifying it is U3's.

**Scope**: edge-boundary · **Priority**: High  
**Source**: wire-contract / M1-FR-02 (BR-DR-07, 08)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/wire-contract/code/`  
**Technical references**: `construction/wire-contract/functional-design/business-rules.md` (D-WC-06, D-WC-11, BR-DR-07, 08), `construction/wire-contract/functional-design/l1-coverage-matrix.md` (L1-05, L1-12), `construction/wire-contract/nfr-requirements/nfr-requirements.md` (NFR-WC-07)

---

### TC-WC-016 — The delegating principal is present exactly when origin is delegated

**Context**: `delegatingPrincipal` is required when `originMode` is `delegated`, and absent when it is `autonomous` (BR-ENV-02; PF §7b). It is defined in envelope v1 so that delegation lands without a breaking change, though no M1 path stamps it.

**Scenario**: A reviewer validates envelopes that break the condition in each direction.

**Preconditions**:
- The sample envelope; the delegated envelope

**Steps**:
1. Remove `delegatingPrincipal` from a copy of the delegated envelope and validate it
2. Add a well-formed `delegatingPrincipal` to a copy of the sample (autonomous) envelope and validate it
3. Remove `principal`, and in another copy `organization`, from the delegated envelope's `delegatingPrincipal`, and validate each
4. Validate the delegated envelope unchanged

**Expected outcome**: Steps 1 to 3 fail. Step 4 passes.

**Scope**: negative · **Priority**: High  
**Source**: wire-contract / M1-FR-02 (BR-ENV-02)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/wire-contract/code/`  
**Technical references**: `construction/wire-contract/functional-design/business-rules.md` (BR-ENV-02), `construction/wire-contract/functional-design/domain-entities.md` (*Delegating Principal Reference*), `construction/wire-contract/functional-design/l1-coverage-matrix.md` (L1-08)

---

### TC-WC-017 — An unknown origin mode is not a schema error

**Context**: Enumerated values are open strings: a consumer must not fail on a value it does not know (BR-ENV-06; PF FR-005 b). `originMode`'s known values are `autonomous` and `delegated`, and the schema must still accept another string.

**Scenario**: A reviewer validates envelopes with origin modes outside the known set.

**Preconditions**:
- The sample envelope

**Steps**:
1. Set `originMode` to `"sponsored"` in a copy and validate it
2. Set `originMode` to `7`, and in another copy to `null`, and validate each

**Expected outcome**: Step 1 passes. Step 2 fails for both copies: the value is open, but it is still a string.

**Scope**: edge-boundary · **Priority**: High  
**Source**: wire-contract / M1-FR-02 (BR-ENV-06)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/wire-contract/code/`  
**Technical references**: `construction/wire-contract/functional-design/business-rules.md` (BR-ENV-06), `construction/wire-contract/functional-design/l1-coverage-matrix.md` (L1-06)

---

### TC-WC-018 — The actor chain holds 1 to 32 entries

**Context**: The actor chain is ordered, most recent last, with at least one entry, and `maxChainDepth` is **32** for envelope v1 (BR-ENV-04; D-WC-05). A chain that would exceed it is rejected, never truncated; that refusal (`chain_too_deep`) is U3's, and the schema bounds what it accepts.

**Scenario**: A reviewer validates envelopes at and beyond the chain bounds.

**Preconditions**:
- The sample envelope

**Steps**:
1. Set `actorChain` to an empty list and validate it
2. Set `actorChain` to 1 entry, then to 32 entries, and validate each
3. Set `actorChain` to 33 entries and validate it
4. Open the conventions and find `maxChainDepth`

**Expected outcome**: Steps 1 and 3 fail. Step 2 passes for both. The conventions state that `maxChainDepth` is 32 for envelope v1.

**Scope**: edge-boundary · **Priority**: High  
**Source**: wire-contract / M1-FR-02 (BR-ENV-04)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/wire-contract/code/`  
**Technical references**: `construction/wire-contract/functional-design/business-rules.md` (D-WC-05, BR-ENV-04, BR-PR-07), `construction/wire-contract/functional-design/l1-coverage-matrix.md` (L1-07)

---

### TC-WC-019 — Re-broadening records are well-formed, and their cross-field rules are listed as checks in code

**Context**: `reBroadening`, when present, has at least one record, each with a `hop` index (BR-ENV-03). That a `hop` is a valid index into `actorChain`, and that no `hop` appears twice, cannot be expressed by the schema; it is checked in code by the receiving unit (U3), and the conventions list it (NFR-WC-08).

**Scenario**: A reviewer validates malformed re-broadening records and checks the conventions.

**Preconditions**:
- The re-broadened envelope

**Steps**:
1. Set `reBroadening` to an empty list and validate it
2. Set a record's `hop` to `-1`, then to `1.5`, then to `"1"`, and validate each
3. Remove `hop` from a record and validate it
4. Open the conventions' list of rules checked in code

**Expected outcome**: Steps 1 to 3 fail. The conventions list "each `hop` is an index into `actorChain`" and "no `hop` appears twice" as checked in code by the receiving unit.

**Scope**: negative · **Priority**: Medium  
**Source**: wire-contract / M1-FR-02 (BR-ENV-03)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/wire-contract/code/`  
**Technical references**: `construction/wire-contract/functional-design/business-rules.md` (BR-ENV-03), `construction/wire-contract/functional-design/domain-entities.md` (*Re-broadening Record*), `construction/wire-contract/nfr-requirements/nfr-requirements.md` (NFR-WC-08)

---

### TC-WC-020 — Trace context is validated for well-formedness only

**Context**: `traceparent` follows W3C Trace Context, and `tracestate` is optional and bounded (M1-TECH-05; BR-TC-01 to 04). The schema checks the form with a linear-time pattern. A version of `ff`, and an all-zero trace id or parent id, are invalid but are checked in code by the receiving unit, and listed in the conventions (NFR-WC-08).

**Scenario**: A reviewer validates drafts with valid and invalid trace contexts.

**Preconditions**:
- The draft definition; the sample draft

**Steps**:
1. Validate the sample draft (version `00`, 55 characters)
2. Validate a copy whose `traceparent` has a higher version with an extra field after the flags, for example `01-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01-extra`
3. Validate copies whose `traceparent` has uppercase hex; a 31-digit trace id; a 15-digit parent id; a missing flags field; and version `00` with an extra field
4. Remove `traceparent` from a copy and validate it
5. Validate a copy with a `tracestate` of 512 characters, and one of 513
6. Open the conventions' list of rules checked in code

**Expected outcome**: Steps 1 and 2 pass, and the 512-character `tracestate` passes. Every copy in steps 3 and 4 fails, and the 513-character `tracestate` fails. The conventions list version `ff`, an all-zero trace id, an all-zero parent id, and the 32-member limit of `tracestate` (if the pattern does not enforce it) as checked in code, and state that the platform validates form only and emits no spans.

**Scope**: edge-boundary · **Priority**: High  
**Source**: wire-contract / M1-TECH-05 (BR-TC-01 to 04)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/wire-contract/code/`  
**Technical references**: `construction/wire-contract/functional-design/business-rules.md` (BR-TC), `construction/wire-contract/functional-design/l1-coverage-matrix.md` (L1-29), `construction/wire-contract/nfr-requirements/nfr-requirements.md` (NFR-WC-08)

---

### TC-WC-021 — Received identifiers are plain strings, with no pattern or length

**Context**: Identifier patterns and lengths constrain only what the platform **accepts**. Wherever an identifier is **received** (the envelope, the Delivery, a response), it is a plain string, and consumers never validate its syntax. That is what makes widening a pattern later compatible (BR-ID-11; BR-VER-05).

**Scenario**: A reviewer inspects the received-side schemas, and validates an envelope whose identifiers would fail the request-side patterns.

**Preconditions**:
- `envelope.schema.json`, `delivery.schema.json`, and the Problem definition

**Steps**:
1. List every identifier-bearing property in the envelope (`scope` parts, `actorChain[].agent`, `actorChain[].instance`, `delegatingPrincipal` parts) and the Delivery
2. Check each for `pattern`, `minLength` other than 1, and `maxLength`
3. Validate a copy of the sample envelope whose `scope.environment` is `"env with space"` and whose `actorChain[0].agent` is 300 characters long

**Expected outcome**: No received identifier property carries a pattern or a maximum length. Step 3 passes. (The envelope as a whole is still bounded: TC-WC-029.)

**Scope**: edge-boundary · **Priority**: High  
**Source**: wire-contract / M1-FR-02 (BR-ID-11)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/wire-contract/code/`  
**Technical references**: `construction/wire-contract/functional-design/business-rules.md` (BR-ID-11, BR-VER-05), `construction/wire-contract/functional-design/l1-coverage-matrix.md` (L1-15)

---

### TC-WC-022 — Request-side identifiers follow their kind's pattern and length

**Context**: Identifier syntax is set per kind (BR-ID-01 to 06, 12). The conventions publish one shared definition per kind, which every surface document references for its request inputs. Human principal identifiers admit email and external-subject forms, and are ASCII-only in M1.

**Scenario**: A reviewer validates sample values against each shared identifier definition.

**Preconditions**:
- The shared identifier definitions in `contract/conventions/` (configured, logical agent, platform reference, instance, human principal, permission)

**Steps**:
1. **Strict** (configured, logical agent, platform reference): accept `o1`, `agent.a_1~x-2`, a 26-character ULID, and a 64-character value; reject the empty string, `-leading`, `has space`, `a:b`, `a/b`, and a 65-character value
2. **Instance**: accept `host-1`, `host-1:4100`, a UUID, and a 128-character value; reject `:leading`, `has space`, and a 129-character value
3. **Human principal**: accept `h@example.com`, `first.last+tag@example.co`, `issuer|subject`, `urn:x:y`, `o'brien@example.com`, and a 256-character value; reject the empty string, `a b@example.com`, `<h@example.com>`, `a,b`, `a;b`, `a"b`, `a\b`, `ü@example.com`, and a 257-character value
4. **Permission**: accept `agent:register` and `event:publish`; reject `agent`, `Agent:register`, `agent:`, `:register`, `agent:Register`, and a 129-character value
5. Check that every pattern is case-sensitive and that no definition trims or normalizes

**Expected outcome**: Every value marked *accept* passes, and every value marked *reject* fails. The conventions state that identifiers are compared exactly, that human principal identifiers are ASCII-only in M1, and that widening a pattern later is compatible.

**Scope**: edge-boundary · **Priority**: High  
**Source**: wire-contract / M1-FR-02 (BR-ID-01 to 06, 12)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/wire-contract/code/`  
**Technical references**: `construction/wire-contract/functional-design/business-rules.md` (BR-ID), `construction/wire-contract/functional-design/l1-coverage-matrix.md` (L1-15, L1-23)

---

### TC-WC-023 — A Delivery missing a field fails, and a Delivery is open to unknown fields

**Context**: A Delivery is `{ envelope, seal, payload }`, all required, and open to unknown fields (BR-DL-01).

**Scenario**: A reviewer validates incomplete and extended deliveries.

**Preconditions**:
- `delivery.schema.json`; the sample delivery

**Steps**:
1. For each of `envelope`, `seal`, and `payload`, remove it from a copy and validate it
2. Replace `envelope` with a copy missing `actorChain` and validate it
3. Add `x-future` at the Delivery's top level and validate it

**Expected outcome**: Steps 1 and 2 fail, naming the field. Step 3 passes.

**Scope**: negative · **Priority**: Medium  
**Source**: wire-contract / M1-FR-02 (BR-DL-01)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/wire-contract/code/`  
**Technical references**: `construction/wire-contract/functional-design/business-rules.md` (BR-DL-01, 02), `construction/wire-contract/functional-design/domain-entities.md` (*Delivery*)

---

### TC-WC-024 — Errors follow the Problem definition

**Context**: Every error is RFC 9457 Problem Details, with a stable, open `code` (D-WC-09; D-WC-16). The Problem is a **received** schema: a client also receives problems that a gateway or proxy emits, usually `about:blank` with no `code` or `instance`. So, following RFC 9457, the schema requires no field, and `type` and `instance` carry no pattern. What soorma-core emits (all of `type`, `title`, `status`, `code`, and `instance`, with the `urn:soorma:` forms) is a published convention, verified by U3's perimeter tests (BR-ERR-08; amendments A2, A3).

**Scenario**: A reviewer validates sample problems against the shared Problem definition.

**Preconditions**:
- The Problem definition in the shared components, served as `application/problem+json`

**Steps**:
1. Validate a problem with `type: "urn:soorma:problem:unknown_field"`, `title`, `status: 400`, `code: "unknown_field"`, `instance: "urn:soorma:request:01J9Z3"`, and `errors: [{ pointer: "/x-future", detail: "..." }]`
2. Validate a problem with `code: "unsupported_contract_version"` and `supportedVersions: ["0.1.0"]`
3. Validate a problem with `code: "some_future_code"` and its matching `type`
4. Remove each of `type`, `title`, `status`, `code`, and `instance` from a copy of the first problem, and validate each
5. Validate a copy with `type: "about:blank"`, and one with `instance: "req-42"` (not a `urn:soorma:request:` URI)
6. Add `x-future` to a problem and validate it
7. Validate a copy whose `instance` is a 200-character string containing a space, and inspect the Problem definition for any `pattern`
8. Validate a gateway-style problem `{ "type": "about:blank", "title": "Bad Gateway", "status": 502 }`, and an empty object `{}`
9. Validate copies of the first problem with `status: "400"` (a string), and with `code: 7` (a number)

**Expected outcome**: Steps 1 to 8 pass: no field is required, the code set is open, the object is open, and no Problem property carries a pattern. Both copies in step 9 fail: the schema still checks the type of each field present.

**Scope**: happy-path · **Priority**: Medium  
**Source**: wire-contract / M1-FR-02 (D-WC-09)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/wire-contract/code/`  
**Technical references**: `construction/wire-contract/functional-design/domain-entities.md` (*Problem*), `construction/wire-contract/functional-design/business-rules.md` (D-WC-09, D-WC-16, BR-ERR-08; amendments A2, A3)

---

### TC-WC-025 — The conventions publish the error codes, their disclosure, and the check order

**Context**: The error model is "specific for validation, generic for trust" (D-WC-10). Surface units implement the refusals; U1 publishes the codes, what each discloses, and the order in which checks run, so a refusal is deterministic and no trust failure becomes an oracle (BR-ERR-01 to 07).

**Scenario**: A reviewer reads the conventions' error section against the business rules.

**Preconditions**:
- `contract/conventions/`

**Steps**:
1. Find the code table, and check each code's status and detail: `malformed_request`, `unknown_field`, `stamped_field_set`, `invalid_inbound_context`, `chain_too_deep`, `envelope_too_large`, `unsupported_contract_version` (400); `credential_refused`, `credential_expired` (401); `forbidden` (403); `payload_too_large` (413); `too_many_attempts` (429); `unavailable` (503); `internal_error` (500)
2. Find the rule for `credential_expired`
3. Find the rule for `too_many_attempts` on an unknown subject
4. Find the check order
5. Find the response headers on a 401, a 429, and a 503
6. Find the forms of a Problem's `type` and `instance`

**Expected outcome**: Every code is present with its status. Only validation codes carry a pointer; `invalid_inbound_context`, `credential_refused`, and `forbidden` carry no detail. `credential_expired` is returned only after the credential verifies with this environment's material. `too_many_attempts` does not reveal whether its subject exists. The check order is the ten steps of BR-ERR-07, with stamped fields before unknown fields, and the envelope size last. A 401 carries `WWW-Authenticate: Bearer`, and a 429 and a 503 carry `Retry-After`. The code set is stated to be open. No response carries a stack trace or internal detail. The conventions state that every Problem soorma-core emits carries `type`, `title`, `status`, `code`, and `instance`, with `type` as `urn:soorma:problem:{code}` and `instance` as `urn:soorma:request:{request id}` equal to `Soorma-Request-Id`; and that a client accepts any problem, `about:blank` with no `code` included (BR-ERR-08).

**Scope**: happy-path · **Priority**: Medium  
**Source**: wire-contract / M1-FR-02 (D-WC-10; BR-ERR)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/wire-contract/code/`  
**Technical references**: `construction/wire-contract/functional-design/business-rules.md` (Section 10), `construction/wire-contract/functional-design/business-logic-model.md` (§2)

---

### TC-WC-026 — The conventions define credential presentation and the security schemes

**Context**: One credential per request, in `Authorization: Bearer`, with a typed prefix that gives its kind without verification; the prefix never admits (D-WC-07; BR-CR-01 to 09). These rules let S3 and S4 refuse human credentials by kind.

**Scenario**: A reviewer reads the security schemes and the presentation rules.

**Preconditions**:
- The shared components document and `contract/conventions/`

**Steps**:
1. List the security schemes in the shared components
2. Find the typed prefixes, and the syntax and length of a credential
3. Find the rules for registration secrets and enrollment material
4. Find the rules for the `Soorma-Delegation` header, cookies, query parameters, and CORS

**Expected outcome**: Exactly three schemes exist, `agentCredential`, `environmentCredential`, and `signIn`, each HTTP bearer. The prefixes are `soorma_ac_`, `soorma_ec_`, `soorma_si_`, and `soorma_dc_` (reserved). A credential is an RFC 6750 `b64token`, prefix included, of at most 4096 characters. The prefix selects the check and never admits; the verified kind must match it. `soorma_rs_` and `soorma_em_` are material sent in a request body, at most 256 characters, never in `Authorization`. `Soorma-Delegation` is reserved and refused in M1. A credential anywhere but `Authorization` is refused. No cookies, and no CORS origin.

**Scope**: happy-path · **Priority**: Medium  
**Source**: wire-contract / M1-FR-02 (D-WC-07; BR-CR)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/wire-contract/code/`  
**Technical references**: `construction/wire-contract/functional-design/business-rules.md` (Section 9), `construction/wire-contract/functional-design/domain-entities.md` (*Credential Presentation*), `construction/wire-contract/functional-design/l1-coverage-matrix.md` (L1-20, L1-22)

---

### TC-WC-027 — The shared headers are defined once

**Context**: A call without a draft declares its contract version in `Soorma-Contract-Version`; every response carries the server's contract version and a `Soorma-Request-Id` (D-WC-08, D-WC-16; BR-VER-02, 07).

**Scenario**: A reviewer inspects the shared header definitions.

**Preconditions**:
- The shared components document

**Steps**:
1. Find the `Soorma-Contract-Version`, `Soorma-Request-Id`, and `Retry-After` header definitions
2. Find the rule for a call that sends both a draft and the header
3. Validate `0.1.0` and `v0.1.0` against the `Soorma-Contract-Version` header's schema
4. Inspect the `Soorma-Request-Id` header's schema

**Expected outcome**: Each header is defined once, in the shared components. `Soorma-Contract-Version` is required on calls without a draft, and present on every response; on a call with a draft, the header must equal the draft's value. `Soorma-Request-Id` is on every response, and equals the request id in a Problem's `instance`. `0.1.0` passes and `v0.1.0` fails. `Soorma-Request-Id` is a plain string with no pattern or length: it is only ever received (BR-ID-11).

**Scope**: happy-path · **Priority**: Medium  
**Source**: wire-contract / M1-FR-02 (D-WC-08, D-WC-16)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/wire-contract/code/`  
**Technical references**: `construction/wire-contract/functional-design/business-rules.md` (D-WC-08, D-WC-16, BR-VER-02, 07)

---

### TC-WC-028 — The conventions publish the versioning rules

**Context**: The perimeter accepts every client contract version it has ever accepted, matched exactly, until a published deprecation window elapses. In M1 the accepted set is `{0.1.0}` (BR-VER-01 to 06; PF §14).

**Scenario**: A reviewer reads the versioning section of the conventions.

**Preconditions**:
- `contract/conventions/`

**Steps**:
1. Find the contract version form and the first version
2. Find the accepted set and the matching rule
3. Find the refusal for a version not accepted
4. Find the change classification

**Expected outcome**: The version is SemVer `0.y.z`, first published as `0.1.0` at the tag `contract-v0.1.0`. The accepted set is `{0.1.0}`, matched exactly, with no ranges; a version once accepted stays accepted until a published window longer than zero. A version not accepted is refused with `unsupported_contract_version`, listing `supportedVersions`. The classification matches business-logic-model §4, including "no breaking change to envelope v1 in M1" and "widening an identifier pattern is compatible".

**Scope**: happy-path · **Priority**: Medium  
**Source**: wire-contract / M1-NFR-04 (BR-VER)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/wire-contract/code/`  
**Technical references**: `construction/wire-contract/functional-design/business-rules.md` (Section 8), `construction/wire-contract/functional-design/business-logic-model.md` (§4), `construction/wire-contract/functional-design/l1-coverage-matrix.md` (L1-04, L1-13)

---

### TC-WC-029 — The conventions carry the remaining pre-release and trust statements

**Context**: The conventions carry each pre-release statement in substance (BR-PR-04 to 08; TC-WC-004 and 005 cover BR-PR-01 to 03), and the statements that the envelope is an assertion and the seal opaque (PF §17; BR-FC-06).

**Scenario**: A reviewer reads the conventions for each statement.

**Preconditions**:
- `contract/conventions/`

**Steps**:
1. Find each statement listed in the expected outcome

**Expected outcome**: The conventions state that:
- the accepted permission identifiers may widen in a compatible version, and only the plane-declared identifiers are accepted now (BR-PR-04)
- a draft never carries origin mode, and accepting an asserted origin later would be additive (BR-PR-05)
- delegation-credential presentation will be added without a breaking change, and `Soorma-Delegation` and `soorma_dc_` are reserved (BR-PR-06)
- `maxChainDepth` is 32 for envelope v1 (BR-PR-07)
- the envelope bound is 16 KiB on the RFC 8785 (JCS) serialization, both for a forwarded envelope and for one the perimeter would stamp (`envelope_too_large`), and received identifiers are opaque (BR-PR-08; BR-ENV-10; BR-DR-09)
- the envelope carries assertions, not proof, and is never self-authenticating (PF §17)
- the seal is opaque: a client forwards it unchanged and must not treat it as proof it can check (BR-FC-06)
- the Delivery payload bound is set by U7 and published there (BR-DL-04)

**Scope**: happy-path · **Priority**: Medium  
**Source**: wire-contract / M1-FR-02 (BR-PR-04 to 08)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/wire-contract/code/`  
**Technical references**: `construction/wire-contract/functional-design/business-rules.md` (Sections 4, 6, 12), `construction/wire-contract/functional-design/l1-coverage-matrix.md` (L1-14, L1-26 to L1-28)

---

### TC-WC-030 — The fixture corpus and changelog establish the 0.1.0 baseline

**Context**: Compatibility (I7) is tested against a versioned fixture corpus: valid and invalid samples per schema, which every later version must still accept and reject, unless a breaking change is recorded (NFR-WC-01, 02). In M1, `0.1.0` is the baseline.

**Scenario**: The compatibility test runs over the corpus.

**Preconditions**:
- `contract/fixtures/0.1.0/`, with `valid/` and `invalid/` samples for the envelope, draft, `inbound`, Delivery, and Problem
- `contract/CHANGELOG.md`

**Steps**:
1. Check that each of the five schemas has at least one valid and one invalid fixture
2. Run the compatibility test
3. Open `contract/CHANGELOG.md`

**Expected outcome**: Every schema is represented. Every valid fixture passes, and every invalid fixture fails. The changelog has a `0.1.0` entry recording the baseline, with each change classified under BR-VER-05, and records that an automated OpenAPI diff is added once a second version exists (NFR-WC-03).

**Scope**: happy-path · **Priority**: High  
**Source**: wire-contract / M1-NFR-04 (NFR-WC-01, 02, 03)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/wire-contract/code/`  
**Technical references**: `construction/wire-contract/nfr-requirements/nfr-requirements.md` (NFR-WC-01 to 03), `construction/wire-contract/functional-design/business-logic-model.md` (§4)

---

### TC-WC-031 — The compatibility test detects a breaking change

**Context**: The compatibility test is only worth having if it fails when a change breaks an earlier version's fixtures (I7; NFR-WC-01).

**Scenario**: A developer makes breaking changes to a working copy of the schemas, and runs the compatibility test after each.

**Preconditions**:
- The corpus from TC-WC-030; a scratch working copy of the repository

**Steps**:
1. Make `tracestate` required in the envelope schema, and run the compatibility test; revert
2. Rename `actorChain` to `chain`, and run it; revert
3. Lower `actorChain`'s `maxItems` to 16, and run it; revert
4. Close the envelope to unknown fields, and run it; revert

**Expected outcome**: The test fails after every change, naming the fixture that broke. After each revert, it passes.

**Scope**: negative · **Priority**: High  
**Source**: wire-contract / M1-NFR-04 (NFR-WC-01)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/wire-contract/code/`  
**Technical references**: `construction/wire-contract/nfr-requirements/nfr-requirements.md` (NFR-WC-01), `construction/wire-contract/functional-design/business-logic-model.md` (§4)

---

### TC-WC-032 — The generated types keep the contract's openness (golden output)

**Context**: Generated types must not be stricter than the contract: an open enumeration admits any string, an open object admits extra keys, a received identifier is a plain string, and a stamped field cannot be set on a draft (BR-LG-06). openapi-typescript's default output collapses an open enumeration to `string`, so the generator script's `transform` hook produces the known values plus `(string & {})`; a golden-output test proves it on every build (NFR-WC-05; T-07 conditions 1 and 2).

**Scenario**: The golden-output test runs.

**Preconditions**:
- The generated types in `contract/generated/`; the committed golden copy; the type-level fixture

**Steps**:
1. Compare the generated file with the committed golden copy
2. Typecheck the type-level fixture under `strict`, in which:
   - an envelope with `originMode: "sponsored"` is assigned to the envelope type
   - an envelope with an extra key `x-future` is assigned to the envelope type
   - a 300-character string is assigned to an actor reference's `agent`
   - each of the following lines is marked `@ts-expect-error`: an `originMode` of `7`; a draft carrying `scope`; a draft carrying `envelopeVersion`
3. Inspect the generated `originMode` type

**Expected outcome**: The generated file is identical to the golden copy. The fixture typechecks: the three permitted assignments compile, and each `@ts-expect-error` line is a genuine error. `originMode` is `"autonomous" | "delegated" | (string & {})`. Open objects have an index signature, stamped fields on the draft type are `?: never`, and every member of the Problem type is optional (amendment A3).

**Scope**: happy-path · **Priority**: High  
**Source**: wire-contract / M1-FR-02 (M1-TECH-02; BR-LG-06)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/wire-contract/code/`  
**Technical references**: `construction/wire-contract/nfr-requirements/nfr-requirements.md` (NFR-WC-05), `construction/wire-contract/nfr-requirements/tech-stack-decisions.md` (T-07, recorded conditions)

---

### TC-WC-033 — Generation is deterministic, and the build fails on drift

**Context**: Regenerating from unchanged schemas gives byte-identical output, and a build check fails if the committed types differ from what the schemas generate (NFR-WC-04; BR-LG-05).

**Scenario**: A developer regenerates twice, then hand-edits a generated file.

**Preconditions**:
- A clean working copy

**Steps**:
1. Run the generator twice, and compare the output of the two runs byte for byte
2. Run the build's generated-types check
3. Hand-edit a type in `contract/generated/`, and run the check again
4. Change a schema without regenerating, and run the check again

**Expected outcome**: The two runs are identical, and step 2 passes. Steps 3 and 4 fail, naming the file that differs.

**Scope**: negative · **Priority**: High  
**Source**: wire-contract / M1-FR-02 (M1-TECH-02; BR-LG-05)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/wire-contract/code/`  
**Technical references**: `construction/wire-contract/nfr-requirements/nfr-requirements.md` (NFR-WC-04), `construction/wire-contract/functional-design/business-rules.md` (BR-LG-03 to 05)

---

### TC-WC-034 — Open enumerations are written in exactly one shape

**Context**: The generator recognises an open enumeration only in the shape `anyOf: [{ enum: [...] }, { type: string }]`. A bare `enum` on a received field would close it, contradicting PF FR-005 b, and would generate a closed type (NFR-WC-06).

**Scenario**: A developer writes an open enumeration in a different shape, and runs the contract checks.

**Preconditions**:
- A scratch working copy

**Steps**:
1. Run the contract checks on the unchanged schemas
2. Replace `originMode`'s definition with a bare `enum: ["autonomous", "delegated"]`, and run them; revert
3. Replace it with `anyOf: [{ type: string }, { enum: [...] }]` (the two branches swapped), and run them; revert

**Expected outcome**: Step 1 passes. Steps 2 and 3 fail, naming `originMode`.

**Scope**: negative · **Priority**: Medium  
**Source**: wire-contract / M1-FR-02 (BR-ENV-06; NFR-WC-06)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/wire-contract/code/`  
**Technical references**: `construction/wire-contract/nfr-requirements/nfr-requirements.md` (NFR-WC-06), `construction/wire-contract/nfr-requirements/tech-stack-decisions.md` (T-07)

---

### TC-WC-035 — Validation cost is bounded on every request-side value

**Context**: Every request-side string has a `maxLength`, and every request-side array a `maxItems`, so validating a request has bounded cost (NFR-WC-07; SECURITY-05). Received identifiers are exempt (BR-ID-11), because the envelope and body bounds cover them.

**Scenario**: A developer removes a bound from a request-side schema, and runs the contract checks.

**Preconditions**:
- A scratch working copy

**Steps**:
1. Run the contract checks on the unchanged schemas
2. Remove the `maxLength` of `inbound.seal`, and run them; revert
3. Remove the `maxLength` of `tracestate`, and run them; revert
4. Remove the `maxItems` of `actorChain`, and run them; revert
5. Remove the `maxLength` from a shared identifier definition, and run them; revert

**Expected outcome**: Step 1 passes. Steps 2 to 5 fail, each naming the unbounded property.

**Scope**: negative · **Priority**: High  
**Source**: wire-contract / M1-NFR-06 (SECURITY-05; NFR-WC-07)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/wire-contract/code/`  
**Technical references**: `construction/wire-contract/nfr-requirements/nfr-requirements.md` (NFR-WC-07)

---

### TC-WC-036 — Patterns are portable and linear-time, and no `format` is used

**Context**: Every `pattern` is in the RE2-compatible subset: anchored, with no lookaround, backreference, or named group. That keeps it portable to any SDK language's validator and rules out catastrophic backtracking. No `format` keyword is used, because JSON Schema 2020-12 treats it as an annotation by default (NFR-WC-08, 09; SECURITY-05, 11).

**Scenario**: A developer introduces each forbidden construct, and runs the contract checks.

**Preconditions**:
- A scratch working copy

**Steps**:
1. Run the contract checks on the unchanged schemas, and search `contract/` for the `format` keyword and for an `ajv-formats` dependency
2. Remove the leading `^` from the strict identifier pattern, and run them; revert
3. Add a lookahead (`(?!0+$)`) to the trace id part of the `traceparent` pattern, and run them; revert
4. Add a backreference, and in another change a named group, to any pattern, and run them; revert
5. Add `format: date-time` to any string, and run them; revert

**Expected outcome**: Step 1 passes, and finds no `format` and no `ajv-formats`. Steps 2 to 5 fail, each naming the schema location.

**Scope**: negative · **Priority**: High  
**Source**: wire-contract / M1-NFR-06 (SECURITY-05, 11; NFR-WC-08, 09)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/wire-contract/code/`  
**Technical references**: `construction/wire-contract/nfr-requirements/nfr-requirements.md` (NFR-WC-08, 09), `construction/wire-contract/nfr-requirements/tech-stack-decisions.md` (T-05)

---

### TC-WC-037 — Schemas compile strictly, and every reference is local

**Context**: Every schema compiles under Ajv strict mode in 2020-12 mode, with no Ajv-specific keyword, so any 2020-12 validator can use it. Every `$ref` is relative, within `contract/`, and the OpenAPI 3.1 schema used to validate the surface documents is a pinned, committed copy whose SHA-256 is recorded (NFR-WC-10, 11; SECURITY-13).

**Scenario**: The schema compilation and reference checks run, then a developer introduces a remote reference and alters the meta-schema.

**Preconditions**:
- The committed OpenAPI 3.1 meta-schema copy, with its source and SHA-256 recorded; a scratch working copy

**Steps**:
1. Compile every schema with Ajv in 2020-12 strict mode, and record any warnings
2. Validate every OpenAPI document under `contract/` against the committed OpenAPI 3.1 schema, with network access disabled
3. Recompute the meta-schema's SHA-256, and compare it with the record
4. Change a `$ref` to an `https://` URL, and run the checks; revert
5. Add an unknown keyword (for example `minimumLength: 1`, a misspelling of `minLength`) to a schema, and compile it; revert
6. Change one byte of the committed meta-schema, and run the checks; revert

**Expected outcome**: Steps 1 to 3 pass, with no warnings and no network access, and the digest matches. Steps 4 to 6 fail.

**Scope**: negative · **Priority**: High  
**Source**: wire-contract / M1-NFR-06 (SECURITY-13; NFR-WC-10, 11)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/wire-contract/code/`  
**Technical references**: `construction/wire-contract/nfr-requirements/nfr-requirements.md` (NFR-WC-10, 11), `construction/wire-contract/nfr-requirements/tech-stack-decisions.md` (T-05, T-08)

---

### TC-WC-038 — Every dependency is registered and licence-checked

**Context**: Every direct dependency has a row in `DEPENDENCIES.md`, and the resolved tree is checked against a licence allowlist by scope: MIT, Apache-2.0, BSD-2-Clause, BSD-3-Clause, ISC, and 0BSD for direct and runtime dependencies; development-only transitive dependencies may also use BlueOak-1.0.0, Python-2.0, CC0-1.0, and CC-BY-4.0; anything else needs a recorded exception (NFR-WC-13, 14; M1-TECH-04; I8).

**Scenario**: CI's register and licence checks run, then a developer adds dependencies that break each rule.

**Preconditions**:
- The workspace from U1; a scratch branch

**Steps**:
1. Run the register check and the licence check
2. Check that the register records the peer-range exception `openapi-typescript>typescript`
3. Add a direct development dependency without a register row, and run the register check; revert
4. Add a direct dependency under a licence outside the strict allowlist (for example BlueOak-1.0.0 or a copyleft licence), with a register row but no exception, and run the licence check; revert
5. Add an exception row for that dependency, and run the licence check again; revert

**Expected outcome**: Step 1 passes, and step 2 finds the exception. Steps 3 and 4 fail, naming the dependency. Step 5 passes: an exception is recorded, not implied.

**Scope**: negative · **Priority**: Medium  
**Source**: wire-contract / M1-TECH-04 (NFR-WC-13, 14)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/wire-contract/code/`  
**Technical references**: `construction/wire-contract/nfr-requirements/nfr-requirements.md` (NFR-WC-13, 14), `construction/wire-contract/nfr-requirements/tech-stack-decisions.md` (T-15)

---

### TC-WC-039 — Installs are reproducible, and the toolchain is pinned

**Context**: One committed lockfile, installed frozen; exact versions; a 7-day release cooldown; dependency lifecycle scripts blocked, with an allowlist that is empty in U1; Node pinned exactly; pnpm pinned with `packageManager` and enforced by pnpm, with no Corepack (NFR-WC-12, 15, 16, 19; M1-TECH-04).

**Scenario**: A reviewer inspects the workspace configuration, then breaks each rule on a scratch branch.

**Preconditions**:
- The workspace from U1; a scratch branch

**Steps**:
1. Check that `pnpm-lock.yaml` is committed; every version in `package.json` files is exact; `minimumReleaseAge` is 7 days; the lifecycle-script allowlist is empty; `.node-version` and `engines` pin Node 26 exactly; `packageManager` pins pnpm 12 exactly; and no step enables Corepack
2. Change a dependency's version in `package.json` without updating the lockfile, and run a frozen install; revert
3. Run an install with a different pnpm major than `packageManager` names
4. Add a dependency whose version is a range (`^x.y.z`), and run the configuration check; revert

**Expected outcome**: Every item in step 1 holds. Steps 2 to 4 are refused: the frozen install fails, pnpm refuses the mismatched version, and the configuration check rejects the range.

**Scope**: negative · **Priority**: Medium  
**Source**: wire-contract / M1-TECH-04 (NFR-WC-12, 15, 16, 19)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/wire-contract/code/`  
**Technical references**: `construction/wire-contract/nfr-requirements/nfr-requirements.md` (NFR-WC-12, 15, 16, 19), `construction/wire-contract/nfr-requirements/tech-stack-decisions.md` (T-01, T-02, T-15)

---

### TC-WC-040 — CI runs pinned, least-privilege, and scans every build

**Context**: Every GitHub Action is pinned by commit SHA; workflow permissions default to `contents: read`; `pnpm audit` fails at moderate severity and above; dependency review runs on pull requests; and every build keeps a CycloneDX SBOM produced by Syft (NFR-WC-17, 18, 20; T-12 to T-14; SECURITY-10).

**Scenario**: A reviewer inspects the workflow and a CI run.

**Preconditions**:
- `.github/workflows/` from U1; a completed CI run on a pull request

**Steps**:
1. Check every `uses:` line for a full 40-character commit SHA
2. Check the workflow's default `permissions`, and any per-job widening and its recorded reason
3. Check that the run executed each of: frozen install, build, typecheck, lint, format check, tests (contract checks, golden output, compatibility), generated-types diff, licence check, register check, audit, SBOM
4. Check the audit step's severity threshold, and that dependency review ran on the pull request
5. Download the run's SBOM artifact
6. On a scratch branch, change one `uses:` to a tag (for example `@v4`), and run the workflow check; revert

**Expected outcome**: Every `uses:` is SHA-pinned, and permissions default to `contents: read`. Every step in step 3 ran and passed. The audit threshold is moderate, and dependency review ran. The SBOM is CycloneDX JSON listing the workspace's dependencies. Step 6 fails.

**Scope**: negative · **Priority**: Medium  
**Source**: wire-contract / M1-TECH-04 (NFR-WC-17, 18, 20)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/wire-contract/code/`  
**Technical references**: `construction/wire-contract/nfr-requirements/nfr-requirements.md` (NFR-WC-17, 18, 20), `construction/wire-contract/nfr-requirements/tech-stack-decisions.md` (T-12 to T-14)

---

### TC-WC-041 — Type-aware lint catches unhandled promises

**Context**: ESLint with typescript-eslint, type-aware, has `no-floating-promises` and `no-misused-promises` on, so unhandled rejections are caught at compile time; TypeScript runs in `strict`; Prettier is enforced (NFR-WC-23; SECURITY-15).

**Scenario**: A developer adds code that leaves a promise unhandled, and runs lint.

**Preconditions**:
- A scratch branch with any TypeScript file in the workspace (for example a contract check)

**Steps**:
1. Run lint, typecheck, and the format check on the unchanged workspace
2. Add a call to an async function without `await`, `void`, or a handler, and run lint; revert
3. Pass an async function where a void callback is expected, and run lint; revert
4. Misformat a file, and run the format check; revert

**Expected outcome**: Step 1 passes. Steps 2 and 3 fail with the named rule. Step 4 fails.

**Scope**: negative · **Priority**: Low  
**Source**: wire-contract / M1-NFR-06 (SECURITY-15; NFR-WC-23)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/wire-contract/code/`  
**Technical references**: `construction/wire-contract/nfr-requirements/nfr-requirements.md` (NFR-WC-23), `construction/wire-contract/nfr-requirements/tech-stack-decisions.md` (T-10, T-11)

---
