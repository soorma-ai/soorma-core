# Test Case Index: agent-registration

Unit abbreviation: AR = agent-registration

Canonical source: [test-specs-narrative.md](test-specs-narrative.md). 72 test cases, comprehensive scope (TC-AR-001 to 022 at inception; TC-AR-023 to 072 added at the construction pass, 2026-11-11).

| Test Case ID | Title | Source | Scope | Priority |
|---|---|---|---|---|
| TC-AR-001 | A logical agent is registered with all eight attributes, sponsored by H | agent-registration / M1-FR-03 | happy-path | High |
| TC-AR-002 | The ceiling snapshot records the sponsor's held set | agent-registration / M1-FR-03 | happy-path | High |
| TC-AR-003 | Autonomy declared defaults to no | agent-registration / M1-FR-03 | happy-path | Medium |
| TC-AR-004 | A re-broadening declaration within the standing set is accepted | agent-registration / M1-FR-03 | happy-path | High |
| TC-AR-005 | An empty re-broadening declaration is accepted | agent-registration / M1-FR-03 | happy-path | Medium |
| TC-AR-006 | A registration secret is issued, with its issuer recorded | agent-registration / M1-FR-04 | happy-path | High |
| TC-AR-007 | Registration and issuance are attributed to H | agent-registration / M1-FR-12 | happy-path | Medium |
| TC-AR-008 | Two agents are registered, each with its own sponsor and snapshot | agent-registration / M1-FR-03 | happy-path | High |
| TC-AR-009 | A standing set exceeding what the sponsor holds is rejected | agent-registration / M1-FR-03 | negative | High |
| TC-AR-010 | A standing set containing `grant:human` is rejected, although H holds it | agent-registration / M1-FR-03 | negative | High |
| TC-AR-011 | Standing sets containing `human:manage` or `agent:delegate` are rejected | agent-registration / M1-FR-03 | negative | High |
| TC-AR-012 | A declaration exceeding the standing set is rejected | agent-registration / M1-FR-03 | negative | High |
| TC-AR-013 | A standing set with a non-plane-declared identifier is rejected | agent-registration / M1-FR-15, M1-FR-03 | negative | High |
| TC-AR-014 | Registration without `agent:register` is denied | agent-registration / M1-FR-08 | negative | High |
| TC-AR-015 | Secret issuance without `agent:register` is denied | agent-registration / M1-FR-04 | negative | High |
| TC-AR-016 | Registration by an agent is refused | agent-registration / M1-FR-03 | negative | High |
| TC-AR-017 | A secret for an unknown registration is rejected | agent-registration / M1-FR-04 | negative | Medium |
| TC-AR-018 | A standing set equal to the held set is accepted | agent-registration / M1-FR-03 | edge-boundary | Medium |
| TC-AR-019 | The snapshot is unaffected by later grants to the sponsor | agent-registration / M1-FR-03 | edge-boundary | High |
| TC-AR-020 | A secret is returned only once | agent-registration / M1-FR-04 | edge-boundary | High |
| TC-AR-021 | An unresolvable sponsor held set rejects the registration | agent-registration / M1-FR-03 | edge-boundary | Medium |
| TC-AR-022 | This unit's operations are defined in the contract and validated against it | agent-registration / M1-FR-02 | happy-path | High |
| TC-AR-023 | A taken identifier is `registration_exists`, decided only after authority and the ceiling | agent-registration / M1-FR-03 (D-AR-02) | negative | High |
| TC-AR-024 | Two concurrent registrations of one identifier write one row and one attribution record | agent-registration / M1-FR-03 (D-AR-26) | edge-boundary | High |
| TC-AR-025 | The same identifier in E and E2 is two independent registrations | agent-registration / M1-FR-03 (I1) | edge-boundary | High |
| TC-AR-026 | A body naming a sponsor is `malformed_request` | agent-registration / M1-FR-03 (D-AR-09) | negative | High |
| TC-AR-027 | The app role holds only `SELECT` and `INSERT` on registrations and secrets | agent-registration / NFR-AR-23 (D-AR-15) | negative | High |
| TC-AR-028 | No code path updates or deletes a registration or a secret | agent-registration / M1-FR-03 (PF FR-013) | negative | Medium |
| TC-AR-029 | `exceeds_sponsor_ceiling` points at each standing entry not held | agent-registration / M1-FR-03 (D-AR-03) | negative | High |
| TC-AR-030 | `human_only_permission` points at each human-only entry, after `unknown_permission` | agent-registration / M1-FR-03 | negative | High |
| TC-AR-031 | S2 and P4 import no evaluator or human-only class but P3's | agent-registration / M1-FR-08 (I5) | negative | High |
| TC-AR-032 | The agent-facts source reads one statement, in E only, without snapshot or sponsor | agent-registration / M1-FR-08 (D-AR-19) | happy-path | High |
| TC-AR-033 | Who may issue a secret: the sponsor, or an Admin holding `agent:register` | agent-registration / M1-FR-04 (D-AR-01) | negative | High |
| TC-AR-034 | A registration holds several active secrets | agent-registration / M1-FR-04 (D-AR-04) | happy-path | Medium |
| TC-AR-035 | An unaccepted identifier in the declaration is `unknown_permission` | agent-registration / M1-FR-15 | negative | Medium |
| TC-AR-036 | No secret value or digest reaches a log, a record, or a Problem; issuance is not cacheable | agent-registration / M1-FR-04 (SECURITY-03, 12) | negative | High |
| TC-AR-037 | A self-grant of `agent:register` is usable on the next registration | agent-registration / M1-FR-03 (PF §10) | happy-path | High |
| TC-AR-038 | Each operation reads the held set once; U4's evaluator tests are unchanged | agent-registration / M1-FR-08 (D-AR-07) | happy-path | High |
| TC-AR-039 | A principal of E reaches nothing of E2's, on every U5 access path | agent-registration / M1-FR-03 (I1) | negative | High |
| TC-AR-040 | Scope, actor, and sponsor are recoverable from the records alone | agent-registration / M1-FR-12 (I4) | happy-path | High |
| TC-AR-041 | A failed attribution write leaves no registration and no secret | agent-registration / M1-FR-12 (D-AR-18) | negative | High |
| TC-AR-042 | Wrong presenters are refused on both operations | agent-registration / M1-FR-03 (ID §8b) | negative | High |
| TC-AR-043 | Every rejection holds for a raw call | agent-registration / M1-FR-02 (I2) | negative | High |
| TC-AR-044 | The same credential from another source address registers with the same sponsor | agent-registration / M1-FR-03 (I3) | negative | Medium |
| TC-AR-045 | The contract changes are compatible and recorded | agent-registration / M1-FR-02 (I7) | happy-path | High |
| TC-AR-046 | Nothing unassigned or commercial lands in core; the cap is a security bound | agent-registration / I8 (NFR-AR-24) | negative | High |
| TC-AR-047 | No tenant identifiers or deployment topology in U5's code | agent-registration / I9, I10 | negative | Medium |
| TC-AR-048 | A secret's value has the specified format, and values are distinct | agent-registration / NFR-AR-01 | happy-path | High |
| TC-AR-049 | The digest matches its test vector, and the store holds only it | agent-registration / NFR-AR-02 | happy-path | High |
| TC-AR-050 | Each malformed value is refused by the parser | agent-registration / NFR-AR-03 | negative | High |
| TC-AR-051 | The 10th secret is issued; an 11th is `secret_limit_reached`, shown only to a permitted caller | agent-registration / NFR-AR-06 | edge-boundary | High |
| TC-AR-052 | The cap holds under concurrent issuances | agent-registration / NFR-AR-07 | edge-boundary | High |
| TC-AR-053 | Issuances for different registrations do not wait on each other; the lock key is derived as specified | agent-registration / NFR-AR-07 | edge-boundary | Medium |
| TC-AR-054 | Success is reported only after commit | agent-registration / NFR-AR-08 (PF §10) | negative | High |
| TC-AR-055 | S2's README documents backup and restore | agent-registration / NFR-AR-09 | happy-path | Medium |
| TC-AR-056 | The backup path is git-ignored, and the dump and its directory have restrictive modes | agent-registration / NFR-AR-09 | negative | High |
| TC-AR-057 | The backup and restore services mount only `backup/`, and hold no password | agent-registration / NFR-AR-09, 10 | negative | High |
| TC-AR-058 | A restore round trip preserves everything, applies no migration, and keeps the grants | agent-registration / NFR-AR-10 | happy-path | High |
| TC-AR-059 | Backup and restore on the stack | agent-registration / NFR-AR-10 | happy-path | High |
| TC-AR-060 | Every backup passes the archive validity check; damaged archives fail it | agent-registration / NFR-AR-09 | negative | High |
| TC-AR-061 | The Build and Test summary states U5's residuals | agent-registration / NFR-AR-11, 13 | happy-path | Medium |
| TC-AR-062 | S2's throttle covers both operations | agent-registration / NFR-AR-12 | negative | Medium |
| TC-AR-063 | The body bound admits a maximal registration and refuses one byte more than 16 KiB | agent-registration / NFR-AR-14 | edge-boundary | Medium |
| TC-AR-064 | The p95 of both operations is reported | agent-registration / NFR-AR-15 | happy-path | Low |
| TC-AR-065 | U3's admission benchmark is re-run with P4's agent-facts source | agent-registration / NFR-AR-16 | happy-path | Low |
| TC-AR-066 | Each flow emits its security event, with no identifier or secret | agent-registration / NFR-AR-18 | happy-path | Medium |
| TC-AR-067 | The new alert rules validate and name only defined events | agent-registration / NFR-AR-19 | happy-path | Low |
| TC-AR-068 | U5 adds no dependency | agent-registration / NFR-AR-20 | happy-path | Medium |
| TC-AR-069 | Timestamps come from the injected clock | agent-registration / NFR-AR-22 | happy-path | Low |
| TC-AR-070 | The store refuses rows breaking its constraints | agent-registration / NFR Design (NP-AR-01) | negative | High |
| TC-AR-071 | U2's code checks pass over U5's code | agent-registration / NFR-AR-05 | negative | High |
| TC-AR-072 | Only the registrations primary-key violation maps to `registration_exists` | agent-registration / NFR Design (NP-AR-06) | negative | Medium |
