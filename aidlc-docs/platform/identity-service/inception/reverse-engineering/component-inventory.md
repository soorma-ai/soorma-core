# Component Inventory

## Application Packages
- `sdk/python/soorma` - SDK wrappers, clients, agent runtime primitives.
- `services/registry` - Tier 1 developer-tenant registry service.
- `services/memory` - Tier 2 memory service.
- `services/tracker` - Tier 2 tracking/observability service.
- `services/event-service` - Tier 2 event ingress/streaming service.
- `services/gateway` - gateway service layer.

## Infrastructure Packages
- `iac/` - infrastructure artifacts and deployment resources.

## Shared Packages
- `libs/soorma-common` - shared models/events.
- `libs/soorma-service-common` - tenancy dependencies and middleware.
- `libs/soorma-nats` - event transport adapters.

## Test/Example Packages
- `examples/` - runnable reference implementations and choreography demos.

## Total Count
- **Total Top-Level Components (primary domains)**: 12
- **Application/Service Domains**: 6
- **Shared Library Domains**: 3
- **Infrastructure Domain**: 1
- **Examples Domain**: 1
- **Documentation Domain**: 1