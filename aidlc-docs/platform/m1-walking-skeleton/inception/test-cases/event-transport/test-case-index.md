# Test Case Index: event-transport

Unit abbreviation: ET = event-transport

Canonical source: [test-specs-narrative.md](test-specs-narrative.md). 24 test cases, comprehensive scope.

| Test Case ID | Title | Source | Scope | Priority |
|---|---|---|---|---|
| TC-ET-001 | A publishes, and B, subscribed, receives a Delivery | event-transport / M1-FR-11 | happy-path | High |
| TC-ET-002 | The delivered envelope carries scope, origin and a stamped chain | event-transport / M1-FR-01, M1-FR-08 | happy-path | High |
| TC-ET-003 | Trace context is carried as asserted | event-transport / M1-FR-01 | happy-path | Medium |
| TC-ET-004 | A publish is attributed | event-transport / M1-FR-12 | happy-path | Medium |
| TC-ET-005 | A triggered subscribe re-broadens at B's hop | event-transport / M1-FR-08 | happy-path | High |
| TC-ET-006 | A publish with a credential from another environment is denied | event-transport / M1-FR-09, M1-FR-10 | negative | High |
| TC-ET-007 | A draft setting a platform-stamped field is rejected at ingest | event-transport / M1-FR-01, M1-FR-09 | negative | High |
| TC-ET-008 | A draft asserting `autonomous` is rejected at ingest | event-transport / M1-FR-01 (GAP-INT-007) | negative | High |
| TC-ET-009 | An agent without declared autonomy is denied at publish and subscribe | event-transport / M1-FR-08 | negative | High |
| TC-ET-010 | A publish without `event:publish` is denied | event-transport / M1-FR-11 | negative | High |
| TC-ET-011 | A subscribe without `event:subscribe` is denied | event-transport / M1-FR-11 | negative | High |
| TC-ET-012 | Every human credential is refused at ingest | event-transport / M1-FR-09, M1-FR-11 | negative | High |
| TC-ET-013 | A delegation credential is refused | event-transport / M1-FR-09 | negative | High |
| TC-ET-014 | A revoked credential cannot publish | event-transport / M1-FR-07 | negative | High |
| TC-ET-015 | Nothing crosses environments | event-transport / M1-FR-10, M1-FR-11 | negative | High |
| TC-ET-016 | A stream ends within the bound after the subscriber's credential expires | event-transport / M1-FR-11 | edge-boundary | High |
| TC-ET-017 | A stream ends within the bound after revocation | event-transport / M1-FR-11, M1-FR-07 | edge-boundary | High |
| TC-ET-018 | A subscriber offline at publish time never receives the event | event-transport / M1-FR-11 (GAP-INT-003) | edge-boundary | Medium |
| TC-ET-019 | A forwarded chain at maxChainDepth cannot grow | event-transport / M1-FR-01 | edge-boundary | Medium |
| TC-ET-020 | A forwarded origin propagates unchanged | event-transport / M1-FR-08 | edge-boundary | Medium |
| TC-ET-021 | Ingest checks independently of the gateways | event-transport / M1-FR-09 | edge-boundary | High |
| TC-ET-022 | Publish, subscribe and delivery work while the organization level is down | event-transport / M1-FR-11 (M1-NFR-08) | edge-boundary | High |
| TC-ET-023 | Unknown fields survive to delivery | event-transport / M1-FR-01 | edge-boundary | Medium |
| TC-ET-024 | This unit's operations are defined in the contract and validated against it | event-transport / M1-FR-02 | happy-path | High |
