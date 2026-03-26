# Enrichment Delta — sdk-python

## Modified Test Cases
| TC ID | Change Summary | Reason | Source Artifact | Finding Reference |
|-------|---------------|--------|-----------------|-------------------|
| TC-SP-004 | Clarified wrapper precedence: explicit service identity overrides metadata defaults | Functional design introduced explicit-override rule for wrapper identity resolution | construction/sdk-python/functional-design/business-rules.md | BR-5 |
| TC-SP-005 | Replaced "CLI prompts for platform tenant" with env/default resolution behavior (no new prompt/flag) | User-approved Q5 decision selected existing env/default path instead of new CLI prompt | construction/plans/sdk-python-functional-design-plan.md | Q5 Answer: B |
| TC-SP-008 | Updated docs expectation from Section 2 to Section 1 in-place updates including init/per-call split and injection note | Clarification answer finalized docs scope to Section 1 updates | construction/plans/sdk-python-functional-design-clarification-questions.md | Q1 Answer: A |
| TC-SP-009 | Refined fallback expectation to env/default resolution model wording | Align with final functional design terminology and existing tenancy constant behavior | construction/sdk-python/functional-design/domain-entities.md | PlatformTenantIdentity |
| TC-SP-010 | Clarified negative case as payload-level non-forwarding of platform_tenant_id via publish path | Align with Event Service trust boundary model | construction/sdk-python/functional-design/business-rules.md | BR-6a |

## Added Test Cases
| TC ID | Title | Reason | Source Artifact | Finding Reference |
|-------|-------|--------|-----------------|-------------------|
| TC-SP-011 | EventClient publish sends X-Tenant-ID header | Construction functional design identified missing explicit verification for EventClient header projection required for Event Service middleware trust boundary | construction/sdk-python/functional-design/business-logic-model.md | Flow F: Event Client Alignment |

## Removed Test Cases
none
