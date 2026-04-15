# Test Case Index

Unit abbreviation: UCH = uow-cutover-hardening

| Test Case ID | Title | Source | Scope | Priority |
|---|---|---|---|---|
| TC-UCH-001 | JWT-only ingress after release cutover | uow-cutover-hardening / FR-11 | happy-path | High |
| TC-UCH-002 | Header-only request denied post-cutover | uow-cutover-hardening / FR-11 | happy-path-negative | High |
| TC-UCH-003 | Structured telemetry emitted for denied legacy access | uow-cutover-hardening / FR-13 | happy-path-negative | High |
| TC-UCH-004 | Trusted-caller self-issue succeeds with canonical tenant contract | uow-cutover-hardening / FR-11 | happy-path | High |
| TC-UCH-005 | Issue-for-other without override authority is denied | uow-cutover-hardening / FR-11 | happy-path-negative | High |
| TC-UCH-006 | Legacy tenant alias payload is rejected | uow-cutover-hardening / FR-11 | happy-path-negative | High |
| TC-UCH-007 | Unknown kid or invalid signature is denied fail-closed | uow-cutover-hardening / FR-11 | happy-path-negative | High |
| TC-UCH-008 | Unallowlisted delegated issuer is denied before trust retrieval | uow-cutover-hardening / FR-11 | happy-path-negative | High |
| TC-UCH-009 | Unknown kid denial emits alert-ready centralized signal | uow-cutover-hardening / FR-13 | happy-path-negative | Medium |