# Test Specifications (Narrative): wire-contract

**Unit**: `wire-contract` (U1: the wire contract's cross-surface parts, with no face)  
**Unit abbreviation**: WC = wire-contract  
**Scope**: comprehensive (happy path, negative, edge and boundary), as recorded in `aidlc-state.md`  
**Derived from**: `aidlc-docs/platform/m1-walking-skeleton/inception/application-design/unit-of-work.md` and `aidlc-docs/platform/m1-walking-skeleton/inception/requirements/requirements.md` only  
**Generated**: inception pass, 2026-11-02. IDs are permanent

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

---

### TC-WC-001 — A well-formed envelope validates against the envelope schema

**Context**: M1-FR-02 requires one versioned contract defined in a language-neutral schema. The envelope schema is the definition every surface and the SDK share, so a correct envelope must validate against it.

**Scenario**: A reviewer validates a sample envelope carrying all seven fields against the published schema.

**Preconditions**:
- `contract/envelope.schema.json` exists (JSON Schema 2020-12)
- A sample envelope with all seven fields, with required fields present and conditional fields where their condition holds

**Steps**:
1. Load `contract/envelope.schema.json` into a JSON Schema 2020-12 validator
2. Validate the sample envelope

**Expected outcome**: Validation passes with no errors.

**Scope**: happy-path · **Priority**: High  
**Source**: wire-contract / M1-FR-02  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/wire-contract/`  
**Technical references**: `inception/application-design/components.md`, `inception/application-design/unit-of-work.md`

---

### TC-WC-002 — A Delivery validates against the Delivery schema

**Context**: U1 builds the named `Delivery` schema: a stamped envelope plus an opaque payload. It is how a subscriber types each delivered event, since the stream itself is typed only as `text/event-stream`.

**Scenario**: A reviewer validates a sample delivery against `delivery.schema.json`.

**Preconditions**:
- `contract/delivery.schema.json` exists and references `envelope.schema.json`
- A sample delivery: a valid stamped envelope, and an arbitrary JSON payload

**Steps**:
1. Load both schemas into one validator, so references resolve
2. Validate the sample delivery

**Expected outcome**: Validation passes, and the envelope part is validated through the referenced envelope schema, not a copy.

**Scope**: happy-path · **Priority**: High  
**Source**: wire-contract / M1-FR-02  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/wire-contract/`  
**Technical references**: `inception/application-design/components.md`, `inception/application-design/unit-of-work.md`

---

### TC-WC-003 — Types are generated from the schema, never hand-written

**Context**: M1-FR-02 (with M1-TECH-02) requires TypeScript types to be generated from the language-neutral schema, so the SDK never becomes the contract.

**Scenario**: A developer changes a schema description and regenerates types.

**Preconditions**:
- The type-generation pipeline is set up in U1

**Steps**:
1. Add a documentation-only change to `envelope.schema.json`
2. Run the generation pipeline
3. Search the repository for TypeScript type declarations of envelope or delivery shapes outside `contract/generated/`

**Expected outcome**: Generated types are refreshed under `contract/generated/`. No hand-written declaration of a contract shape exists elsewhere.

**Scope**: happy-path · **Priority**: High  
**Source**: wire-contract / M1-FR-02  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/wire-contract/`  
**Technical references**: `inception/application-design/components.md`, `inception/application-design/unit-of-work.md`

---

### TC-WC-004 — The contract declares its pre-release status

**Context**: M1-FR-02 requires the M1 contract to be published as pre-release, because delivery semantics are unspecified (GAP-INT-003).

**Scenario**: A reviewer reads the contract's conventions.

**Preconditions**:
- `contract/conventions/` exists

**Steps**:
1. Open the contract conventions
2. Find the contract version and its status

**Expected outcome**: The version is marked pre-release. The contract also states that event delivery semantics are unspecified at this version.

**Scope**: happy-path · **Priority**: High  
**Source**: wire-contract / M1-FR-02  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/wire-contract/`  
**Technical references**: `inception/application-design/components.md`, `inception/application-design/unit-of-work.md`

---

### TC-WC-005 — The contract states that bootstrap and renewal carry no envelope

**Context**: U1's inherited gap GAP-INT-008 is worked around by stating, in the contract, that neither the bootstrap exchange nor renewal carries an envelope.

**Scenario**: A reviewer reads the conventions for which operations carry an envelope.

**Preconditions**:
- `contract/conventions/` exists

**Steps**:
1. Open the contract conventions
2. Find the statement of which calls carry an envelope

**Expected outcome**: Bootstrap and renewal are named as carrying no envelope. Direct human operations are also stated to carry none.

**Scope**: happy-path · **Priority**: Medium  
**Source**: wire-contract / M1-FR-02 (GAP-INT-008, U1's inherited gaps)  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/wire-contract/`  
**Technical references**: `inception/application-design/components.md`, `inception/application-design/unit-of-work.md`

---

### TC-WC-006 — An envelope missing a required field fails validation

**Context**: A contract that accepted an incomplete envelope would let consumers rely on fields that may be absent.

**Scenario**: A reviewer validates envelopes, each with one required field removed.

**Preconditions**:
- `contract/envelope.schema.json`
- A valid sample envelope

**Steps**:
1. For each required field (envelope version, scope, origin mode, actor chain, trace context), remove it from a copy of the sample
2. Validate each copy

**Expected outcome**: Every copy fails validation, and the error names the missing field.

**Scope**: negative · **Priority**: High  
**Source**: wire-contract / M1-FR-02  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/wire-contract/`  
**Technical references**: `inception/application-design/components.md`, `inception/application-design/unit-of-work.md`

---

### TC-WC-007 — The draft schema does not admit platform-stamped fields

**Context**: The draft an agent sends must never carry a platform-stamped field (M1-FR-01). The contract's draft shape should make this visible to every generated client.

**Scenario**: A reviewer validates drafts that each carry one platform-stamped field.

**Preconditions**:
- The draft definition in `contract/envelope.schema.json`

**Steps**:
1. Take a valid draft (client contract version, trace context, and optional forwarded context)
2. For each of envelope version, scope, origin mode, delegating principal, actor chain, and re-broadening record, add the field to a copy
3. Validate each copy against the draft definition

**Expected outcome**: Every copy fails validation as a draft.

**Scope**: negative · **Priority**: High  
**Source**: wire-contract / M1-FR-02  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/wire-contract/`  
**Technical references**: `inception/application-design/components.md`, `inception/application-design/unit-of-work.md`

---

### TC-WC-008 — Unknown fields are permitted by the envelope schema

**Context**: Consumers must preserve and forward unknown fields (M1-FR-01). A schema that forbade additional properties would make every future field a breaking change.

**Scenario**: A reviewer validates an envelope carrying an extra, unknown field.

**Preconditions**:
- A valid sample envelope

**Steps**:
1. Add a field `x-future` with any value
2. Validate the envelope

**Expected outcome**: Validation passes.

**Scope**: edge-boundary · **Priority**: Medium  
**Source**: wire-contract / M1-FR-02  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/wire-contract/`  
**Technical references**: `inception/application-design/components.md`, `inception/application-design/unit-of-work.md`

---

### TC-WC-009 — Every surface document references the one envelope definition

**Context**: One versioned contract covers every entry point. Copies of the envelope definition per surface would drift.

**Scenario**: A reviewer inspects every OpenAPI document present for envelope definitions.

**Preconditions**:
- `contract/` with at least one surface OpenAPI document

**Steps**:
1. List every schema definition named or shaped as an envelope or draft in `contract/*.openapi.yaml`
2. Check each one's origin

**Expected outcome**: Each is a `$ref` to `envelope.schema.json` (or to `delivery.schema.json`). None is an inline copy.

**Scope**: edge-boundary · **Priority**: Medium  
**Source**: wire-contract / M1-FR-02  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/wire-contract/`  
**Technical references**: `inception/application-design/components.md`, `inception/application-design/unit-of-work.md`

---

### TC-WC-010 — The client contract version is distinct from the envelope version

**Context**: A draft declares the client contract version, which is distinct from the envelope version (M1-FR-01). The schema must keep the two separate, so they can evolve independently.

**Scenario**: A reviewer inspects the draft and envelope definitions.

**Preconditions**:
- `contract/envelope.schema.json`

**Steps**:
1. Locate the client contract version in the draft definition
2. Locate the envelope version in the envelope definition

**Expected outcome**: They are two different properties. The draft requires the client contract version and does not admit the envelope version.

**Scope**: edge-boundary · **Priority**: Medium  
**Source**: wire-contract / M1-FR-02  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/wire-contract/`  
**Technical references**: `inception/application-design/components.md`, `inception/application-design/unit-of-work.md`

---

### TC-WC-011 — Contract files carry the Apache 2.0 licence

**Context**: The envelope's machine-readable definition is licensed Apache 2.0 (M1-FR-02, PF §22), separately from the FSL substrate.

**Scenario**: A reviewer checks the licence of `contract/`.

**Preconditions**:
- The repository layout from U1

**Steps**:
1. Open the licence file in `contract/`
2. Open the licence file in `packages/`

**Expected outcome**: `contract/` is Apache 2.0, and `packages/` is FSL-1.1-ALv2.

**Scope**: edge-boundary · **Priority**: Medium  
**Source**: wire-contract / M1-FR-02  
**Construction artifacts**: `aidlc-docs/platform/m1-walking-skeleton/construction/wire-contract/`  
**Technical references**: `inception/application-design/components.md`, `inception/application-design/unit-of-work.md`

---
