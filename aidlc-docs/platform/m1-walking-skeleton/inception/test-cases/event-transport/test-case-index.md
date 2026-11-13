# Test Case Index: event-transport

Unit abbreviation: ET = event-transport

Canonical source: [test-specs-narrative.md](test-specs-narrative.md). 93 test cases, comprehensive scope (TC-ET-001 to 024 at inception; TC-ET-025 to 092 added at the construction pass, 2026-11-13; TC-ET-093 added at Code Generation, D-CG-ET-16).

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
| TC-ET-025 | The draft's contract version is checked at both operations | event-transport / M1-FR-01, M1-FR-02 | negative | High |
| TC-ET-026 | A forward that is not load-bearing records no hop | event-transport / M1-FR-08, M1-FR-12 | edge-boundary | Medium |
| TC-ET-027 | A forwarded envelope is never a credential | event-transport / M1-FR-09 | negative | High |
| TC-ET-028 | Revocation reaches a publish within the bound, at either granularity | event-transport / M1-FR-07 | edge-boundary | High |
| TC-ET-029 | Unreadable revocation state: served within the bound, then denied | event-transport / M1-FR-07 | edge-boundary | High |
| TC-ET-030 | One bound, one constant, no configuration key | event-transport / M1-FR-07, M1-NFR-01 | happy-path | High |
| TC-ET-031 | Neither granularity of revocation is told apart | event-transport / M1-FR-07 | negative | High |
| TC-ET-032 | S4's caches never answer across environments | event-transport / M1-FR-10 | edge-boundary | High |
| TC-ET-033 | S4 learns its environment from configuration only | event-transport / M1-FR-10 | edge-boundary | Medium |
| TC-ET-034 | A record alone recovers scope, actor, chain, origin, and sponsor | event-transport / M1-FR-12 | happy-path | High |
| TC-ET-035 | A record that cannot be written: nothing delivered, no stream | event-transport / M1-FR-12 (GAP-ET-001) | negative | High |
| TC-ET-036 | S4's latency on the running stack, reported | event-transport / M1-NFR-01 | edge-boundary | Low |
| TC-ET-037 | A publish leaves its record and nothing of the event | event-transport / M1-FR-11 (GAP-INT-003) | edge-boundary | Medium |
| TC-ET-038 | S4's contract document holds data-face operations only | event-transport / M1-FR-02, M1-NFR-03 | happy-path | Medium |
| TC-ET-039 | Nothing of E2 is read, written, delivered, or superseded at E | event-transport / M1-FR-10, M1-FR-11 | negative | High |
| TC-ET-040 | Every refusal holds for a raw call to the stack | event-transport / M1-FR-09, M1-FR-02 | negative | High |
| TC-ET-041 | The same credential from another address is the same agent | event-transport / M1-FR-09 | edge-boundary | Medium |
| TC-ET-042 | P7 is closed both ways | event-transport / M1-FR-12 | negative | High |
| TC-ET-043 | S4 imports only the allowlisted names of P2 and P3 | event-transport / M1-FR-08 | negative | High |
| TC-ET-044 | A forwarding hop never gains authority beyond the intersection | event-transport / M1-FR-08 | negative | High |
| TC-ET-045 | The completed contract passes U1's compatibility check | event-transport / M1-FR-02, M1-NFR-04 | happy-path | High |
| TC-ET-046 | No topic administration, durability, or seeding path in core | event-transport / M1-FR-11 | edge-boundary | Medium |
| TC-ET-047 | S4 never reads a payload beyond its bound and well-formedness | event-transport / M1-FR-01 | edge-boundary | Medium |
| TC-ET-048 | Two instances asserting one name each hold their own stream | event-transport / M1-FR-11 | edge-boundary | Medium |
| TC-ET-049 | The payload bound at its edge, with a large number | event-transport / M1-FR-11 | edge-boundary | High |
| TC-ET-050 | Step-1 limits at both edges of both operations | event-transport / M1-FR-09 | edge-boundary | High |
| TC-ET-051 | The guaranteed maximum-size forwarding draft passes step 1 | event-transport / M1-FR-01 | edge-boundary | High |
| TC-ET-052 | Maximum nesting at each operation's limit | event-transport / M1-FR-09 | edge-boundary | Medium |
| TC-ET-053 | The contract's statements on payloads and streams | event-transport / M1-FR-02 | happy-path | Medium |
| TC-ET-054 | A heartbeat after 15 seconds of silence | event-transport / M1-FR-11 | edge-boundary | Low |
| TC-ET-055 | The open-stream cap | event-transport / M1-FR-11 | edge-boundary | High |
| TC-ET-056 | A full send buffer ends the stream with overflow | event-transport / M1-FR-11 | edge-boundary | High |
| TC-ET-057 | A stream that cannot take its end is closed after the grace | event-transport / M1-FR-11 | edge-boundary | Medium |
| TC-ET-058 | The stream's encoding | event-transport / M1-FR-02 | happy-path | Medium |
| TC-ET-059 | The stream route outlives the server's ordinary timeouts | event-transport / M1-FR-11 | edge-boundary | Medium |
| TC-ET-060 | Shutdown ends every stream within 5 seconds | event-transport / M1-FR-11 | edge-boundary | Medium |
| TC-ET-061 | The throttle at S4, and a stream holds no permit | event-transport / M1-FR-11 | edge-boundary | High |
| TC-ET-062 | Superseding across two instances on one channel | event-transport / M1-FR-11 | edge-boundary | High |
| TC-ET-063 | Superseding on one instance | event-transport / M1-FR-11 | edge-boundary | High |
| TC-ET-064 | Two racing subscribes leave exactly one stream | event-transport / M1-FR-11 | edge-boundary | Medium |
| TC-ET-065 | The Compose model: one S4 per environment, no replicas | event-transport / M1-NFR-05 | happy-path | High |
| TC-ET-066 | With the store down, steps 1 to 3 answer exactly | event-transport / M1-FR-09 | negative | High |
| TC-ET-067 | TLS 1.3 at S4's edge and to its store | event-transport / M1-NFR-06 | negative | Medium |
| TC-ET-068 | S4's logs carry no secret, token, seal, envelope, payload, trace value, or human | event-transport / M1-NFR-06 | negative | High |
| TC-ET-069 | S4's events and alert rules, the overlap pinned | event-transport / M1-NFR-06 | happy-path | Medium |
| TC-ET-070 | service-kit's route body limits are additive | event-transport / M1-NFR-06 | happy-path | Medium |
| TC-ET-071 | An integer above 2^53 is delivered unchanged | event-transport / M1-FR-11 | happy-path | High |
| TC-ET-072 | A long decimal and an exponent form are delivered exactly | event-transport / M1-FR-11 | happy-path | High |
| TC-ET-073 | A lone surrogate in a payload is refused with a pointer | event-transport / M1-FR-01 | negative | High |
| TC-ET-074 | `packages/jcs`'s source mode, and its default unchanged | event-transport / M1-FR-01 | happy-path | High |
| TC-ET-075 | S4 refuses to start without `JSON.rawJSON` | event-transport / M1-NFR-06 | negative | High |
| TC-ET-076 | Duplicate payload member names keep the last value | event-transport / M1-FR-11 | edge-boundary | Low |
| TC-ET-077 | The Body Form on `admit` | event-transport / M1-FR-01 | happy-path | High |
| TC-ET-078 | The verify-only key ring | event-transport / M1-FR-07 | happy-path | High |
| TC-ET-079 | A stream's headers, and its deliveries in order | event-transport / M1-FR-11 | happy-path | Medium |
| TC-ET-080 | One frame per publish, the same for every stream | event-transport / M1-FR-11 | edge-boundary | Low |
| TC-ET-081 | Migrations `0005` and `0006` | event-transport / M1-FR-12 | happy-path | Medium |
| TC-ET-082 | `soorma_env_ingest`'s privileges, with the real statements | event-transport / M1-NFR-06 | negative | High |
| TC-ET-083 | S4's dependency closure and image packages | event-transport / M1-NFR-08 | negative | High |
| TC-ET-084 | `stack:init` writes each environment's seal key, never overwriting it | event-transport / M1-NFR-05 | happy-path | High |
| TC-ET-085 | The smoke test at S3's depth | event-transport / M1-NFR-05 | happy-path | High |
| TC-ET-086 | U5's backup round trip with S4 | event-transport / M1-NFR-05 | edge-boundary | Medium |
| TC-ET-087 | S4's README Operations match the code | event-transport / M1-NFR-05 | happy-path | Low |
| TC-ET-088 | S4's memory, measured against its limit | event-transport / M1-NFR-05 | edge-boundary | High |
| TC-ET-089 | `loadEventIngest` refuses a shared secret or another role | event-transport / M1-FR-10 | negative | High |
| TC-ET-090 | An envelope sealed in E2 is refused when forwarded in E | event-transport / M1-FR-10 | negative | High |
| TC-ET-091 | `humanGrants` grants nothing at S4 | event-transport / M1-FR-08 | edge-boundary | Low |
| TC-ET-092 | Neither operation returns its own hop's envelope | event-transport / M1-FR-11 | happy-path | Medium |
| TC-ET-093 | A raw value nested in an object or an array is refused in default mode | event-transport / M1-FR-01 | negative | High |
