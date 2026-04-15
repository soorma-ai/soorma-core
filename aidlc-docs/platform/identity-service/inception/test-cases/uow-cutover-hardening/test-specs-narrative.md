# Test Specs Narrative - uow-cutover-hardening

### TC-UCH-001 - JWT-only ingress after release cutover
Context: Validates release-boundary cutover behavior after legacy header-auth removal and confirms the secured path no longer depends on a runtime mode toggle.
Scenario: A secured non-public request uses a valid JWT after the cutover release has been deployed.
Steps: 1) Deploy the cutover release into the target environment 2) Send a JWT-authenticated request to a secured endpoint 3) Observe ingress auth handling
Expected: Request succeeds on the JWT-only path with no legacy-header fallback and no runtime auth-mode toggle involved.
Scope: happy-path
Priority: High
Source: uow-cutover-hardening / FR-11
Construction artifacts: aidlc-docs/platform/identity-service/construction/uow-cutover-hardening/
Technical references: business-logic-model.md BLM-1, BLM-2; business-rules.md BR-01, BR-02

### TC-UCH-002 - Header-only request denied post-cutover
Context: Ensures the legacy auth path is fully removed from active request handling after the cutover release.
Scenario: A secured request provides legacy headers without a JWT after cutover.
Steps: 1) Deploy the cutover release 2) Send a header-only request to a secured non-public endpoint 3) Inspect the response behavior
Expected: Access is denied fail-closed with a safe non-leaking error envelope and no header-auth compatibility path is exercised.
Scope: happy-path-negative
Priority: High
Source: uow-cutover-hardening / FR-11
Construction artifacts: aidlc-docs/platform/identity-service/construction/uow-cutover-hardening/
Technical references: business-logic-model.md BLM-1, BLM-8; business-rules.md BR-18, BR-24, BR-25

### TC-UCH-003 - Structured telemetry emitted for denied legacy access
Context: Validates observability hardening for denied legacy/header-only access attempts and confirms the denial event is suitable for centralized alerting.
Scenario: A header-only request is denied after cutover.
Steps: 1) Trigger a denied legacy/header-only request 2) Inspect the centralized log/metric/trace sink for emitted security telemetry
Expected: A structured denial event is emitted with correlation context and deny reason, without raw token or secret leakage.
Scope: happy-path-negative
Priority: High
Source: uow-cutover-hardening / FR-13
Construction artifacts: aidlc-docs/platform/identity-service/construction/uow-cutover-hardening/
Technical references: business-rules.md BR-18, BR-19; nfr-design-patterns.md ND-2, ND-4

### TC-UCH-004 - Trusted-caller self-issue succeeds with canonical tenant contract
Context: Validates the remaining secured exception path where token issuance is allowed for a trusted caller issuing for itself under the canonical `tenant_id` contract.
Scenario: A trusted caller requests a token for itself using canonical tenant fields.
Steps: 1) Authenticate as an approved trusted caller 2) Submit a self-issue request using `tenant_id` only 3) Observe issuance authorization and result
Expected: Token issuance succeeds when tenant checks pass and the request uses the canonical tenant contract only.
Scope: happy-path
Priority: High
Source: uow-cutover-hardening / FR-11
Construction artifacts: aidlc-docs/platform/identity-service/construction/uow-cutover-hardening/code/
Technical references: business-logic-model.md BLM-3, BLM-5; business-rules.md BR-03, BR-05, BR-10

### TC-UCH-005 - Issue-for-other without override authority is denied
Context: Covers the hardening rule that request payload fields cannot grant issue-for-other authority and that cross-principal issuance remains deny-by-default.
Scenario: A trusted caller requests a token for another principal without valid override authority.
Steps: 1) Authenticate as a trusted caller lacking override rights 2) Submit an issue-for-other request with a target principal and optional payload-based override hints 3) Observe the authorization decision
Expected: Issuance is denied fail-closed because override authority is not present in caller auth context, regardless of payload assertions.
Scope: happy-path-negative
Priority: High
Source: uow-cutover-hardening / FR-11
Construction artifacts: aidlc-docs/platform/identity-service/construction/uow-cutover-hardening/code/
Technical references: business-logic-model.md BLM-3, BLM-4; business-rules.md BR-06, BR-07, BR-08, BR-24

### TC-UCH-006 - Legacy tenant alias payload is rejected
Context: Validates immediate convergence to the canonical `tenant_id` contract and rejection of active dual-name compatibility.
Scenario: A request uses `platform_tenant_id` or `tenant_domain_id` instead of canonical `tenant_id`.
Steps: 1) Submit a request on an active cutover path using a legacy tenant alias field 2) Inspect validation outcome
Expected: The request is rejected with explicit validation failure because only canonical `tenant_id` is accepted on active interfaces.
Scope: happy-path-negative
Priority: High
Source: uow-cutover-hardening / FR-11
Construction artifacts: aidlc-docs/platform/identity-service/construction/uow-cutover-hardening/code/
Technical references: business-logic-model.md BLM-5; business-rules.md BR-10, BR-11

### TC-UCH-007 - Unknown kid or invalid signature is denied fail-closed
Context: Verifies the hardened verifier policy requiring deterministic denial when key resolution or signature validation fails.
Scenario: A secured request presents a JWT with an unknown `kid` or invalid signature.
Steps: 1) Send a JWT referencing an unknown `kid` or containing an invalid signature 2) Observe verification result and response handling
Expected: Verification is denied fail-closed with a typed safe error path and no permissive alternate-key fallback.
Scope: happy-path-negative
Priority: High
Source: uow-cutover-hardening / FR-11
Construction artifacts: aidlc-docs/platform/identity-service/construction/uow-cutover-hardening/code/
Technical references: business-rules.md BR-15, BR-17, BR-24, BR-25; nfr-design-patterns.md ND-1, ND-2

### TC-UCH-008 - Unallowlisted delegated issuer is denied before trust retrieval
Context: Ensures delegated issuer OIDC/JWKS validation is bounded to approved trust sources and network egress controls.
Scenario: A delegated token references an issuer that is not on the approved allowlist.
Steps: 1) Submit a delegated-token validation request using an unapproved issuer 2) Observe trust-evaluation and outbound retrieval behavior
Expected: Validation is denied fail-closed and runtime trust retrieval is not permitted for the unallowlisted issuer.
Scope: happy-path-negative
Priority: High
Source: uow-cutover-hardening / FR-11
Construction artifacts: aidlc-docs/platform/identity-service/construction/uow-cutover-hardening/code/
Technical references: business-logic-model.md BLM-10; nfr-design-patterns.md ND-7; infrastructure-design.md Section 4

### TC-UCH-009 - Unknown kid denial emits centralized alert-ready security signal
Context: Extends observability coverage to verifier-failure cases that must drive centralized monitoring and alerting contracts.
Scenario: An unknown `kid` verification failure occurs on a secured path.
Steps: 1) Trigger a request that produces an unknown `kid` denial 2) Inspect centralized observability outputs for emitted signal families
Expected: Structured telemetry and alert-ready signal data are emitted for the verifier failure using the centralized observability stack.
Scope: happy-path-negative
Priority: Medium
Source: uow-cutover-hardening / FR-13
Construction artifacts: aidlc-docs/platform/identity-service/construction/uow-cutover-hardening/code/
Technical references: nfr-design-patterns.md ND-2, ND-4; infrastructure-design.md Section 5