# Test Case Index

Unit abbreviation: USJI = uow-sdk-jwt-integration

| Test Case ID | Title | Source | Scope | Priority |
|---|---|---|---|---|
| TC-USJI-001 | Wrapper calls remain signature-compatible with internal JWT injection | uow-sdk-jwt-integration / FR-12 | happy-path | High |
| TC-USJI-002 | SDK sends canonical JWT-authenticated outbound request | uow-sdk-jwt-integration / FR-11 | happy-path | High |
| TC-USJI-003 | Invalid JWT is denied fail-closed with typed safe error | uow-sdk-jwt-integration / NFR-8 | happy-path-negative | High |
| TC-USJI-004 | JWT plus matching compatibility alias succeeds | uow-sdk-jwt-integration / FR-11 | happy-path | High |
| TC-USJI-005 | JWT plus mismatching alias tenant is denied | uow-sdk-jwt-integration / FR-11 | happy-path-negative | High |
| TC-USJI-006 | Unknown kid or invalid signature is denied under verifier policy | uow-sdk-jwt-integration / NFR-9 | happy-path-negative | High |
| TC-USJI-007 | soorma dev bootstrap returns deterministic outcomes and blocks protected drift | uow-sdk-jwt-integration / FR-12 | happy-path-negative | High |