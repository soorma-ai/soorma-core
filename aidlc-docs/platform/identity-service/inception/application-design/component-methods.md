# Component Methods

## Signature Conventions
- Internal method contracts are JWT-centric with adapter translation during coexistence.
- Route handlers and DI call sites remain stable through shared dependency abstractions.
- Detailed business rules are deferred to Functional Design in Construction.

## TenantOnboardingComponent
- create_tenant_domain(request, actor_context) -> TenantDomainResult
- bootstrap_admin_principal(tenant_id, principal_request, actor_context) -> PrincipalResult
- bootstrap_machine_principals(tenant_id, principal_requests, actor_context) -> list[PrincipalResult]
- initialize_tenant_policy(tenant_id, policy_request, actor_context) -> PolicyResult

## PrincipalManagementComponent
- create_principal(tenant_id, principal_request, auth_context) -> PrincipalResult
- update_principal(tenant_id, principal_id, update_request, auth_context) -> PrincipalResult
- deactivate_principal(tenant_id, principal_id, auth_context) -> PrincipalResult
- assign_roles(tenant_id, principal_id, roles, auth_context) -> RoleAssignmentResult
- validate_principal_state(tenant_id, principal_id, auth_context) -> PrincipalStateResult

## TokenIssuanceComponent
- issue_token(tenant_id, principal_id, token_request, auth_context) -> TokenIssueResult
- build_claim_set(tenant_id, principal, token_policy, delegated_context) -> ClaimSet
- apply_token_policy(tenant_id, principal, token_request) -> PolicyDecision
- get_signing_metadata(tenant_id) -> SigningMetadata

## DelegatedTrustComponent
- register_issuer(tenant_id, issuer_request, auth_context) -> IssuerResult
- update_issuer(tenant_id, issuer_id, issuer_request, auth_context) -> IssuerResult
- revoke_issuer(tenant_id, issuer_id, auth_context) -> IssuerResult
- validate_delegated_assertion(tenant_id, assertion, auth_context) -> DelegatedValidationResult
- evaluate_issuer_trust(tenant_id, issuer_identity, assertion_context) -> TrustDecision

## ClaimContextPolicyComponent
- validate_mandatory_claims(claims, route_policy) -> ValidationResult
- evaluate_delegated_context_claims(claims, route_policy, trust_decision) -> ValidationResult
- normalize_external_principal(tenant_id, external_identity, mapping_policy) -> CanonicalPrincipal
- resolve_effective_access_context(claims, route_policy) -> AccessContext

## AuditTelemetryComponent
- record_identity_event(event_type, tenant_id, actor, payload, correlation_id) -> None
- record_auth_decision(tenant_id, principal, decision, reason, correlation_id) -> None
- record_trust_change(tenant_id, issuer_id, change_type, actor, correlation_id) -> None

## ProviderFacadeComponent
- create_principal_via_provider(tenant_id, principal_request, auth_context) -> PrincipalResult
- issue_token_via_provider(tenant_id, principal, token_request, auth_context) -> TokenIssueResult
- validate_assertion_via_provider(tenant_id, assertion, auth_context) -> DelegatedValidationResult

## CompatibilityAdapterComponent
- resolve_auth_context_from_request(request) -> AuthContext
- translate_legacy_context_to_auth_context(legacy_context) -> AuthContext
- inject_auth_context_into_request_state(request, auth_context) -> None
- is_legacy_path_enabled(config) -> bool