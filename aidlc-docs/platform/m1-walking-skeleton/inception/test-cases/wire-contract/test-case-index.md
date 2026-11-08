# Test Case Index: wire-contract

Unit abbreviation: WC = wire-contract

Canonical source: [test-specs-narrative.md](test-specs-narrative.md). 41 test cases, comprehensive scope: 11 from the inception pass (2026-11-02), and 30 added by the construction pass (2026-11-08).

| Test Case ID | Title | Source | Scope | Priority |
|---|---|---|---|---|
| TC-WC-001 | A well-formed envelope validates against the envelope schema | wire-contract / M1-FR-02 | happy-path | High |
| TC-WC-002 | A Delivery validates against the Delivery schema | wire-contract / M1-FR-02 | happy-path | High |
| TC-WC-003 | Types are generated from the schema, never hand-written | wire-contract / M1-FR-02 | happy-path | High |
| TC-WC-004 | The contract declares its pre-release status | wire-contract / M1-FR-02 | happy-path | High |
| TC-WC-005 | The contract states that bootstrap and renewal carry no envelope | wire-contract / M1-FR-02 (GAP-INT-008, U1's inherited gaps) | happy-path | Medium |
| TC-WC-006 | An envelope missing a required field fails validation | wire-contract / M1-FR-02 | negative | High |
| TC-WC-007 | The draft schema does not admit platform-stamped fields | wire-contract / M1-FR-02 | negative | High |
| TC-WC-008 | Unknown fields are permitted by the envelope schema | wire-contract / M1-FR-02 | edge-boundary | Medium |
| TC-WC-009 | Every surface document references the one envelope definition | wire-contract / M1-FR-02 | edge-boundary | Medium |
| TC-WC-010 | The client contract version is distinct from the envelope version | wire-contract / M1-FR-02 | edge-boundary | Medium |
| TC-WC-011 | Contract files carry the Apache 2.0 licence | wire-contract / M1-FR-02 | edge-boundary | Medium |
| TC-WC-012 | A stamped field takes precedence over an unknown field in a draft | wire-contract / M1-FR-02 (BR-DR-10) | negative | High |
| TC-WC-013 | The draft is closed at its top level | wire-contract / M1-FR-02 (BR-DR-01) | negative | High |
| TC-WC-014 | A draft missing a required field fails validation | wire-contract / M1-FR-02 (BR-DR-05, 06) | negative | High |
| TC-WC-015 | The forwarded context is a closed wrapper around an open envelope | wire-contract / M1-FR-02 (BR-DR-07, 08) | edge-boundary | High |
| TC-WC-016 | The delegating principal is present exactly when origin is delegated | wire-contract / M1-FR-02 (BR-ENV-02) | negative | High |
| TC-WC-017 | An unknown origin mode is not a schema error | wire-contract / M1-FR-02 (BR-ENV-06) | edge-boundary | High |
| TC-WC-018 | The actor chain holds 1 to 32 entries | wire-contract / M1-FR-02 (BR-ENV-04) | edge-boundary | High |
| TC-WC-019 | Re-broadening records are well-formed, and their cross-field rules are listed as checks in code | wire-contract / M1-FR-02 (BR-ENV-03) | negative | Medium |
| TC-WC-020 | Trace context is validated for well-formedness only | wire-contract / M1-TECH-05 (BR-TC-01 to 04) | edge-boundary | High |
| TC-WC-021 | Received identifiers are plain strings, with no pattern or length | wire-contract / M1-FR-02 (BR-ID-11) | edge-boundary | High |
| TC-WC-022 | Request-side identifiers follow their kind's pattern and length | wire-contract / M1-FR-02 (BR-ID-01 to 06, 12) | edge-boundary | High |
| TC-WC-023 | A Delivery missing a field fails, and a Delivery is open to unknown fields | wire-contract / M1-FR-02 (BR-DL-01) | negative | Medium |
| TC-WC-024 | Errors follow the Problem definition | wire-contract / M1-FR-02 (D-WC-09) | happy-path | Medium |
| TC-WC-025 | The conventions publish the error codes, their disclosure, and the check order | wire-contract / M1-FR-02 (D-WC-10; BR-ERR) | happy-path | Medium |
| TC-WC-026 | The conventions define credential presentation and the security schemes | wire-contract / M1-FR-02 (D-WC-07; BR-CR) | happy-path | Medium |
| TC-WC-027 | The shared headers are defined once | wire-contract / M1-FR-02 (D-WC-08, D-WC-16) | happy-path | Medium |
| TC-WC-028 | The conventions publish the versioning rules | wire-contract / M1-NFR-04 (BR-VER) | happy-path | Medium |
| TC-WC-029 | The conventions carry the remaining pre-release and trust statements | wire-contract / M1-FR-02 (BR-PR-04 to 08) | happy-path | Medium |
| TC-WC-030 | The fixture corpus and changelog establish the 0.1.0 baseline | wire-contract / M1-NFR-04 (NFR-WC-01, 02, 03) | happy-path | High |
| TC-WC-031 | The compatibility test detects a breaking change | wire-contract / M1-NFR-04 (NFR-WC-01) | negative | High |
| TC-WC-032 | The generated types keep the contract's openness (golden output) | wire-contract / M1-FR-02 (M1-TECH-02; BR-LG-06) | happy-path | High |
| TC-WC-033 | Generation is deterministic, and the build fails on drift | wire-contract / M1-FR-02 (M1-TECH-02; BR-LG-05) | negative | High |
| TC-WC-034 | Open enumerations are written in exactly one shape | wire-contract / M1-FR-02 (BR-ENV-06; NFR-WC-06) | negative | Medium |
| TC-WC-035 | Validation cost is bounded on every request-side value | wire-contract / M1-NFR-06 (SECURITY-05; NFR-WC-07) | negative | High |
| TC-WC-036 | Patterns are portable and linear-time, and no `format` is used | wire-contract / M1-NFR-06 (SECURITY-05, 11; NFR-WC-08, 09) | negative | High |
| TC-WC-037 | Schemas compile strictly, and every reference is local | wire-contract / M1-NFR-06 (SECURITY-13; NFR-WC-10, 11) | negative | High |
| TC-WC-038 | Every dependency is registered and licence-checked | wire-contract / M1-TECH-04 (NFR-WC-13, 14) | negative | Medium |
| TC-WC-039 | Installs are reproducible, and the toolchain is pinned | wire-contract / M1-TECH-04 (NFR-WC-12, 15, 16, 19) | negative | Medium |
| TC-WC-040 | CI runs pinned, least-privilege, and scans every build | wire-contract / M1-TECH-04 (NFR-WC-17, 18, 20) | negative | Medium |
| TC-WC-041 | Type-aware lint catches unhandled promises | wire-contract / M1-NFR-06 (SECURITY-15; NFR-WC-23) | negative | Low |
