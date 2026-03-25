# Enrichment Delta — event-service

## Modified Test Cases
| TC ID | Change Summary | Reason | Source Artifact | Finding Reference |
|-------|---------------|--------|-----------------|-------------------|
| TC-ES-005 | Updated from strict passthrough wording to normalization-without-remapping behavior; inputs now include padded identities and expected trimmed output | U7 requires centralized sanitization while preserving identity semantics | construction/event-service/functional-design/business-logic-model.md | BR-U7-04, BR-U7-07 |
| TC-ES-006 | Updated route-shape assertion from http_request naming pattern to dependency-injected platform tenant resolution | Final U7 design selected DI boundary for auth transport abstraction | construction/event-service/functional-design/business-rules.md | BR-U7-02 |
| TC-ES-008 | Tightened expected outcome from "rejected or blocked" to explicit HTTP 422 with no publish | U7 fail-closed validation semantics require deterministic rejection | construction/event-service/nfr-requirements/nfr-requirements.md | NFR-ES-02, NFR-ES-05 |

## Added Test Cases
| TC ID | Title | Reason | Source Artifact | Finding Reference |
|-------|-------|--------|-----------------|-------------------|
| TC-ES-009 | Event Service rejects publish when tenant_id is missing after sanitization | tenant_id is now mandatory after sanitization and must fail closed when absent/empty | construction/event-service/functional-design/business-rules.md | BR-U7-05 |
| TC-ES-010 | Event Service rejects publish when user_id is missing after sanitization | user_id is now mandatory for all actors including machine actors | construction/event-service/nfr-requirements/nfr-requirements.md | NFR-ES-02 |

## Removed Test Cases
none
