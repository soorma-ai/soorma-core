# Domain Entities
## Unit: U6 - sdk/python

## Overview
Functional entities used by SDK two-tier tenancy behavior.

## Entity: PlatformTenantIdentity
- Purpose: stable platform/developer tenancy identity for low-level client lifetime.
- Fields:
  - `platform_tenant_id: str`
- Source:
  - constructor value or env/default fallback behavior.
- Mapped header:
  - `X-Tenant-ID`

## Entity: ServiceIdentity
- Purpose: per-request end-tenant and user context.
- Fields:
  - `service_tenant_id: str`
  - `service_user_id: str`
- Source:
  - explicit wrapper/client method arguments, or wrapper-bound event metadata defaults.
- Mapped headers:
  - `X-Service-Tenant-ID`
  - `X-User-ID`

## Entity: IdentityHeaders
- Purpose: canonical HTTP projection of multi-tenancy identity.
- Structure:
  - `X-Tenant-ID: platform_tenant_id`
  - `X-Service-Tenant-ID: service_tenant_id`
  - `X-User-ID: service_user_id`
- Producer:
  - internal helper in each low-level client.

## Entity: EventPublishHeaders
- Purpose: HTTP header projection for SDK EventClient -> Event Service publish calls.
- Structure:
  - `X-Tenant-ID: platform_tenant_id`
- Notes:
  - `tenant_id` and `user_id` remain event envelope metadata for service-tenant/service-user context.
  - `platform_tenant_id` is not set in envelope by SDK; Event Service injects it.

## Entity: RegistryIdentityModel
- Purpose: represent RegistryClient's separate tenancy model.
- Fields:
  - `developer_tenant_id: str` (platform/developer scope)
- Headers:
  - `X-Tenant-ID`
- Notes:
  - Registry does not use `X-Service-Tenant-ID` or `X-User-ID`.
  - Included for scope clarity; not a U6 refactor target.

## Entity: LowLevelClientConfig
- Purpose: constructor-time configuration for service clients.
- Fields:
  - `base_url: str`
  - `timeout: float`
  - `platform_tenant_id: str`

## Entity: WrapperIdentityContext
- Purpose: wrapper-side identity defaults in handler execution path.
- Fields:
  - `tenant_id` (legacy envelope field; interpreted as service tenant)
  - `user_id` (legacy envelope field; interpreted as service user)
- Behavior:
  - used only as fallback when explicit values are omitted.

## Entity: ParameterNamingModel
- Purpose: semantic clarity and alignment with backend three-dimension model.
- Canonical names:
  - `platform_tenant_id` (init-time)
  - `service_tenant_id` (per-call)
  - `service_user_id` (per-call)
- Deprecated/removed names in this unit:
  - `tenant_id` (in low-level client method signatures)
  - `user_id` (in low-level client method signatures)

## Entity: ValidationContract
- Purpose: define required identity conditions before request dispatch.
- Rules by client/use case:
  - MemoryServiceClient / TrackerServiceClient:
    - non-empty `service_tenant_id` required
    - non-empty `service_user_id` required
    - fail fast in SDK layer for missing required service identity
  - EventClient (publish path):
    - does not require service identity in HTTP headers
    - requires platform tenant header path (`X-Tenant-ID`) for Event Service middleware trust boundary
    - `tenant_id` and `user_id` remain envelope metadata fields (not publish headers)
  - RegistryClient:
    - validates/uses platform/developer tenant identity only (`X-Tenant-ID`)
    - does not use service tenant/user identity fields

## Entity: RefactorImpactSet
- Purpose: identify call-site categories requiring coordinated updates.
- Categories:
  - SDK internal imports and delegations
  - examples using low-level clients
  - test driver clients using low-level clients
  - unit and integration tests
  - architecture documentation references
