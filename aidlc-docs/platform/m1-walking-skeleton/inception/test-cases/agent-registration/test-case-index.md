# Test Case Index: agent-registration

Unit abbreviation: AR = agent-registration

Canonical source: [test-specs-narrative.md](test-specs-narrative.md). 22 test cases, comprehensive scope.

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
